class Scheduler:
    def __init__(self):
        self.reallocations = 0
        self.total_runtime = 0.0

    def schedule(self, engine, current_time_mins):
        pass

class GreedyScheduler(Scheduler):
    def __init__(self):
        super().__init__()
        self.bus_cooldown = {} # bus_id -> next allowed reassignment time (mins)

    def schedule(self, engine, current_time_mins):
        from simulate import SHIFT_1_ARRIVAL
        # No scheduling needed after passengers stop arriving
        if current_time_mins >= SHIFT_1_ARRIVAL:
            return
        reassigned_buses = set()
        
        # 1. Collect current state and detect overloaded routes globally
        route_demand = {}
        route_capacity = {}
        
        for r_id, route in engine.routes.items():
            demand = sum(len(s.waiting_passengers) for s in route.stops)
            route_demand[r_id] = demand
            route_capacity[r_id] = 0
            
        for b in engine.buses.values():
            if b.state in ["SCHEDULED", "EN_ROUTE"] and b.route:
                route_capacity[b.route.route_id] += (b.capacity - b.occupancy)

        # Calculate deficit
        deficits = {r_id: route_demand[r_id] - route_capacity[r_id] for r_id in engine.routes}
        
        # Overloaded routes sorted by worst deficit first
        overloaded_routes = sorted([r for r in deficits if deficits[r] > 0], key=lambda r: deficits[r], reverse=True)
        
        # 2. For each overloaded route, find candidates
        for r_id in overloaded_routes:
            overloaded_route = engine.routes[r_id]
            overloaded_stop_names = {s.name.lower() for s in overloaded_route.stops}
            
            candidates = []
            for b in engine.buses.values():
                if b.bus_id in reassigned_buses:
                    continue
                if b.state != "EN_ROUTE" or not b.route:
                    continue
                if b.route.route_id == r_id:
                    continue # Already on this route
                
                # Hysteresis / Cooldown: 30 minutes between reassignments
                if self.bus_cooldown.get(b.bus_id, 0) > current_time_mins:
                    continue
                
                # Route-lock: a bus that is already acting as a helper for a
                # different route must finish its run before it can be moved again.
                # This prevents the R16 <-> R18 flapping pattern.
                if b.is_helper:
                    continue
                
                # We only want to cannibalize buses that are underutilized
                if b.occupancy > b.capacity // 2:
                    continue
                    
                # Check if the bus is currently AT or APPROACHING a shared stop
                current_stop = b.route.stops[b.current_stop_idx]
                shared_stop_name = current_stop.name.lower()
                
                # BUG FIX: Never reassign at the terminal stop.
                # Buses AT their final destination are empty/done -- they cannot
                # serve downstream stops on another route. Treating Acropolis (and
                # any other end-of-route stop) as a junction produces phantom moves.
                is_terminal = (b.current_stop_idx == len(b.route.stops) - 1)
                if is_terminal:
                    continue
                
                if shared_stop_name in overloaded_stop_names:
                    # Fix Junction Insertion Mismatch: check DOWNSTREAM demand
                    new_idx = next(i for i, s in enumerate(overloaded_route.stops) if s.name.lower() == shared_stop_name)
                    
                    downstream_demand_new = sum(len(s.waiting_passengers) for s in overloaded_route.stops[new_idx:])
                    downstream_demand_old = sum(len(s.waiting_passengers) for s in b.route.stops[b.current_stop_idx:])
                    
                    # Only reassign if new downstream demand is significantly higher than current downstream demand
                    if downstream_demand_new > downstream_demand_old + 10:
                        candidates.append((b, shared_stop_name, downstream_demand_new, new_idx))
                    
            if candidates:
                # 3. Score each candidate (most downstream demand it can serve)
                candidates.sort(key=lambda item: item[2], reverse=True)
                best_candidate, shared_stop_name, new_demand, new_idx = candidates[0]
                
                # 4. Assign best-scoring candidate bus to the overloaded route
                old_route = best_candidate.route
                best_candidate.route = overloaded_route
                best_candidate.current_stop_idx = new_idx
                best_candidate.is_helper = True
                
                reassigned_buses.add(best_candidate.bus_id)
                self.bus_cooldown[best_candidate.bus_id] = current_time_mins + 30 # 30-minute cooldown
                self.reallocations += 1
                
                hh = current_time_mins // 60
                mm = current_time_mins % 60
                print(f"[{hh:02d}:{mm:02d}] SCHEDULER: Reassigned Bus {best_candidate.bus_id} (Occ: {best_candidate.occupancy}/{best_candidate.capacity}) from {old_route.route_id} to {r_id} at shared junction '{shared_stop_name}'")
                
                
                # Decrease deficit for next iterations
                deficits[r_id] -= (best_candidate.capacity - best_candidate.occupancy)

class DPScheduler(Scheduler):
    def __init__(self):
        super().__init__()
        self.bus_cooldown = {}

    def schedule(self, engine, current_time_mins):
        from simulate import SHIFT_1_ARRIVAL
        # No scheduling needed after passengers stop arriving
        if current_time_mins >= SHIFT_1_ARRIVAL:
            return
        reassigned_buses = set()
        
        # 1. State collection (similar to Greedy, but we evaluate globally)
        route_demand = {}
        route_capacity = {}
        
        for r_id, route in engine.routes.items():
            demand = sum(len(s.waiting_passengers) for s in route.stops)
            route_demand[r_id] = demand
            route_capacity[r_id] = 0
            
        for b in engine.buses.values():
            if b.state in ["SCHEDULED", "EN_ROUTE"] and b.route:
                route_capacity[b.route.route_id] += (b.capacity - b.occupancy)

        deficits = {r_id: route_demand[r_id] - route_capacity[r_id] for r_id in engine.routes}
        overloaded_routes = [r for r in deficits if deficits[r] > 0]
        
        if not overloaded_routes:
            return
            
        # Build mapping of shared stops to overloaded routes
        # stop_name -> list of (route_id, new_idx, downstream_demand)
        overloaded_by_stop = {}
        for r_id in overloaded_routes:
            route = engine.routes[r_id]
            for i, s in enumerate(route.stops):
                stop_name = s.name.lower()
                downstream = sum(len(stop.waiting_passengers) for stop in route.stops[i:])
                if downstream > 0:
                    if stop_name not in overloaded_by_stop:
                        overloaded_by_stop[stop_name] = []
                    overloaded_by_stop[stop_name].append((r_id, i, downstream))
        
        # Gather all candidate buses
        candidates = []
        for b in engine.buses.values():
            if b.state != "EN_ROUTE" or not b.route:
                continue
            # Cooldown: 30 minutes between reassignments
            if self.bus_cooldown.get(b.bus_id, 0) > current_time_mins:
                continue
            
            # Route-lock: helpers cannot be reassigned again mid-route
            if b.is_helper:
                continue
            if b.occupancy > b.capacity // 2:
                continue
                
            current_stop = b.route.stops[b.current_stop_idx]
            shared_stop_name = current_stop.name.lower()
            
            # BUG FIX: Never reassign at the terminal stop.
            # Buses at the last stop of their route are done — they have no
            # remaining capacity to serve downstream stops on another route.
            is_terminal = (b.current_stop_idx == len(b.route.stops) - 1)
            if is_terminal:
                continue
            
            if shared_stop_name in overloaded_by_stop:
                current_downstream = sum(len(s.waiting_passengers) for s in b.route.stops[b.current_stop_idx:])
                candidates.append((b, shared_stop_name, current_downstream))
                
        if not candidates:
            return
            
        # DP Formulation: We want to assign candidate buses to overloaded routes to maximize total extra demand covered.
        # This is a Multiple Knapsack Problem.
        # State: (bus_index, route_deficit_tuple) -> max_extra_demand
        # To make it tractable, we discretize deficits. But since we just want a valid assignment that maximizes
        # downstream_demand, and buses have varying available capacity, we can use memoized recursion.
        
        # We simplify the state by sorting candidates by capacity available (largest first)
        candidates.sort(key=lambda x: x[0].capacity - x[0].occupancy, reverse=True)
        
        memo = {}
        best_assignment = {}
        
        def dp(bus_idx, current_deficits):
            state_key = (bus_idx, tuple(sorted(current_deficits.items())))
            if state_key in memo:
                return memo[state_key]
                
            if bus_idx >= len(candidates):
                return 0, {}
                
            bus, shared_stop_name, current_downstream = candidates[bus_idx]
            available_seats = bus.capacity - bus.occupancy
            
            # Option 1: Don't reassign this bus
            max_val, best_moves = dp(bus_idx + 1, current_deficits)
            
            # Option 2: Reassign to a valid target route
            valid_targets = overloaded_by_stop.get(shared_stop_name, [])
            for r_id, new_idx, target_downstream in valid_targets:
                if r_id == bus.route.route_id:
                    continue
                
                # Check if it helps significantly and deficit remains
                if target_downstream > current_downstream + 10 and current_deficits.get(r_id, 0) > 0:
                    # Value gained is the min of available seats, target downstream, or deficit
                    val = min(available_seats, target_downstream, current_deficits.get(r_id, 0))
                    
                    # Create new deficits
                    new_deficits = dict(current_deficits)
                    new_deficits[r_id] -= available_seats
                    
                    sub_val, sub_moves = dp(bus_idx + 1, new_deficits)
                    total_val = val + sub_val
                    
                    if total_val > max_val:
                        max_val = total_val
                        best_moves = dict(sub_moves)
                        best_moves[bus.bus_id] = (r_id, new_idx, shared_stop_name)
                        
            memo[state_key] = (max_val, best_moves)
            return max_val, best_moves
            
        # Execute DP
        max_val, best_moves = dp(0, deficits)
        
        # Apply the best moves
        for bus_id, (r_id, new_idx, shared_stop_name) in best_moves.items():
            best_candidate = engine.buses[bus_id]
            old_route = best_candidate.route
            
            best_candidate.route = engine.routes[r_id]
            best_candidate.current_stop_idx = new_idx
            best_candidate.is_helper = True
            
            self.bus_cooldown[bus_id] = current_time_mins + 30
            self.reallocations += 1
            
            hh = current_time_mins // 60
            mm = current_time_mins % 60
            print(f"[{hh:02d}:{mm:02d}] DP_SCHEDULER: Reassigned Bus {bus_id} (Occ: {best_candidate.occupancy}/{best_candidate.capacity}) from {old_route.route_id} to {r_id} at '{shared_stop_name}'")

