import json
import math
import random
import time
import statistics
from collections import defaultdict
from scheduler import GreedyScheduler, DPScheduler

# --- CONFIGURATION ---
BUS_CAPACITY = 45
START_TIME_STR = "06:00"
END_TIME_STR = "11:00"
TICK_RATE_MINS = 1

FACULTY_RATIO = 0.10
TARGET_DEMAND_MULTIPLIER = 1.2
MIN_BUSES_PER_ROUTE = 2

def time_to_mins(t_str):
    h, m = map(int, t_str.split(':'))
    return h * 60 + m

SIM_START_MINS = time_to_mins(START_TIME_STR)
SIM_END_MINS = time_to_mins(END_TIME_STR)
TOTAL_TICKS = SIM_END_MINS - SIM_START_MINS

# Shift arrival times in minutes from midnight
SHIFT_1_ARRIVAL = time_to_mins("08:10")

class Passenger:
    def __init__(self, p_type, arrival_time):
        self.p_type = p_type # "faculty" or "student"
        self.arrival_time = arrival_time
        self.wait_time = 0

class Stop:
    def __init__(self, stop_id, name, order, route_id):
        self.stop_id = stop_id
        self.name = name
        self.order = order
        self.route_id = route_id
        self.waiting_passengers = []
        self.mins_to_destination = 0 # Will be populated later

class Route:
    def __init__(self, route_id, stops, travel_times, arrival_times, assigned_buses):
        self.route_id = route_id
        self.stops = sorted(stops, key=lambda s: s.order)
        self.travel_times = travel_times  # list of minutes between stops
        self.arrival_times = arrival_times # list of int minutes
        self.assigned_buses = assigned_buses
        self.total_travel_time = sum(travel_times)
        
        # Branch detection
        self.start_indices = []
        for i, s in enumerate(self.stops):
            if "(start)" in s.name.lower() or i == 0:
                if i not in self.start_indices:
                    self.start_indices.append(i)

class Bus:
    def __init__(self, bus_id, capacity):
        self.bus_id = bus_id
        self.capacity = capacity
        self.passengers = []
        self.route = None
        self.current_stop_idx = 0
        self.time_to_next_stop = 0
        self.travel_duration_mins = 0
        self.state = "IDLE" # IDLE, EN_ROUTE, ARRIVED
        self.start_time = -1 # When to start the trip
        self.is_helper = False
        self.last_stop_id = None
        # The physical stop a bus is currently travelling towards.  This remains
        # on the original route during a junction reassignment, allowing the map
        # to render the incoming leg on its actual road geometry.
        self.travel_target_stop_id = None
        
        # Stats
        self.total_transported = 0
        self.peak_occupancy = 0
        
    @property
    def occupancy(self):
        return len(self.passengers)

class SimulationEngine:
    def __init__(self, randomize=False):
        if not randomize:
            random.seed(42)
        else:
            random.seed()
            
        self.stops = {}
        self.routes = {}
        self.buses = {}
        
        self.total_capacity = 0
        self.total_generated = 0
        self.total_transported = 0
        self.wait_times = []
        
        # Stats specifically requested
        self.faculty_transported = 0
        self.students_transported = 0
        self.pre_dispatch_reallocations = 0
        
        self.scheduler = DPScheduler()
        
    def load_data(self):
        print("Loading data...")
        stops_data = json.load(open('data/stops.json'))
        routes_data = json.load(open('data/routes.json'))
        buses_data = json.load(open('data/buses.json'))
        try:
            travel_times_data = json.load(open('data/travel_times.json'))
        except FileNotFoundError:
            travel_times_data = {}
            
        # SCOPE REDUCTION: Only keep these 5 routes (mutually connected)
        ACTIVE_ROUTES = {"R15", "R16", "R18", "R08", "R09"}
        routes_data = [r for r in routes_data if r['routeId'] in ACTIVE_ROUTES]
        buses_data = [b for b in buses_data if b.get('assignedRoute') in ACTIVE_ROUTES]
        
        route_stops = {}
        for s in stops_data:
            if s['route'] in ACTIVE_ROUTES:
                self.stops[s['stopId']] = Stop(s['stopId'], s['name'], s['order'], s['route'])
                if s['route'] not in route_stops:
                    route_stops[s['route']] = []
                route_stops[s['route']].append(self.stops[s['stopId']])
                
        # Sort stops in each route by order
        for rid in route_stops:
            route_stops[rid].sort(key=lambda x: x.order)

        # Load Routes
        for r in routes_data:
            rid = r['routeId']
            r_stops = route_stops.get(rid, [])
            if not r_stops:
                continue
            
            # Parse arrival times
            arrival_times = [SHIFT_1_ARRIVAL]
            
            # Append Acropolis if not present
            if "acropolis" not in r_stops[-1].name.lower():
                acro_id = f"{rid}-ACRO"
                acro_stop = Stop(acro_id, "Acropolis Institutes", r_stops[-1].order + 1, rid)
                r_stops.append(acro_stop)
                self.stops[acro_id] = acro_stop
                
            travel_times = travel_times_data.get(rid, [3]*(len(r_stops)-1))
            
            # Ensure travel times matches stops - 1
            if len(travel_times) < len(r_stops) - 1:
                travel_times.extend([3] * (len(r_stops) - 1 - len(travel_times)))
            elif len(travel_times) > len(r_stops) - 1:
                travel_times = travel_times[:len(r_stops)-1]
                
            self.routes[rid] = Route(rid, r_stops, travel_times, arrival_times, r['assignedBuses'])
            
            # Back-calculate mins_to_destination for each stop for realistic passenger generation
            curr_dist = 0
            for i in range(len(r_stops)-1, -1, -1):
                r_stops[i].mins_to_destination = curr_dist
                if i > 0:
                    curr_dist += travel_times[i-1]

        # Load Buses
        for b in buses_data:
            bus_id = b['busNumber']
            cap = b['capacity'] if b['capacity'] is not None else BUS_CAPACITY
            bus = Bus(bus_id, cap)
            self.buses[bus_id] = bus
            self.total_capacity += cap
            
        self.daily_capacity = self.total_capacity

    def forecast_route_demand(self):
        """Return the deterministic morning demand forecast used by this simulation."""
        sequence = [2, 4, 7, 4, 1, 3, 5, 2, 6, 8]
        return {
            route_id: sum(
                sequence[stop.order % len(sequence)]
                for stop in route.stops
                if (
                    "acropolis" not in stop.name.lower()
                    and SIM_START_MINS <= SHIFT_1_ARRIVAL - stop.mins_to_destination - 15 < SHIFT_1_ARRIVAL
                )
            )
            for route_id, route in self.routes.items()
        }

    def rebalance_pre_dispatch(self):
        """Move only genuinely spare buses before departure to maximise seated passengers.

        A donor route must retain at least two buses and enough seats for its own
        forecast. This never exceeds a bus's stated capacity, so every boarded
        passenger has a seat.
        """
        forecast = self.forecast_route_demand()
        logs = []

        def assigned_capacity(route):
            return sum(self.buses[bus_id].capacity for bus_id in route.assigned_buses if bus_id in self.buses)

        while True:
            deficits = {
                route_id: forecast[route_id] - assigned_capacity(route)
                for route_id, route in self.routes.items()
            }
            targets = [route_id for route_id, deficit in deficits.items() if deficit > 0]
            if not targets:
                break

            target_id = max(targets, key=lambda route_id: deficits[route_id])
            donors = []
            for donor_id, donor_route in self.routes.items():
                if donor_id == target_id or len(donor_route.assigned_buses) <= MIN_BUSES_PER_ROUTE:
                    continue
                for bus_id in donor_route.assigned_buses:
                    bus = self.buses.get(bus_id)
                    if bus and assigned_capacity(donor_route) - bus.capacity >= forecast[donor_id]:
                        donors.append((assigned_capacity(donor_route) - forecast[donor_id], donor_id, bus_id))

            if not donors:
                break

            _, donor_id, bus_id = max(donors, key=lambda candidate: candidate[0])
            self.routes[donor_id].assigned_buses.remove(bus_id)
            self.routes[target_id].assigned_buses.append(bus_id)
            self.pre_dispatch_reallocations += 1
            message = (
                f"[PRE-DISPATCH] Reassigned Bus {bus_id} from {donor_id} to {target_id} "
                f"using forecast demand (seated capacity only)."
            )
            logs.append(message)
            print(message)

        return logs

    def assign_bus_trips(self, shift_arrival_time, shift_name):
        """Simple assignment: send buses to arrive near the shift arrival time."""
        # This is the Greedy strategy's pre-departure optimisation. Baseline
        # and DP remain unchanged so their comparison stays meaningful.
        if isinstance(self.scheduler, GreedyScheduler):
            pre_dispatch_logs = self.rebalance_pre_dispatch()
            if pre_dispatch_logs:
                self.reallocations_log.extend(pre_dispatch_logs)
        for rid, route in self.routes.items():
            buses_for_route = [self.buses[bid] for bid in route.assigned_buses if bid in self.buses]
            if not buses_for_route: continue
            
            # Calculate a representative start time (based on full route)
            target_arrival = shift_arrival_time
            base_start = target_arrival - route.total_travel_time
            
            # Distribute buses across start branches
            num_branches = len(route.start_indices)
            
            for i, bus in enumerate(reversed(buses_for_route)):
                if bus.state != "IDLE":
                    continue # Bus is busy
                
                start_idx = route.start_indices[i % num_branches]
                
                # If starting mid-route, total travel time is shorter
                branch_travel_time = sum(route.travel_times[start_idx:])
                branch_start_time = target_arrival - branch_travel_time
                
                bus.route = route
                bus.current_stop_idx = start_idx
                bus.last_stop_id = route.stops[start_idx].stop_id
                bus.travel_target_stop_id = None
                bus.travel_duration_mins = 0
                bus.passengers = []
                # Stagger buses on the same branch by 10 minutes
                bus_branch_order = i // num_branches
                bus.start_time = branch_start_time - (bus_branch_order * 10)
                
                if bus.start_time < SIM_START_MINS:
                    bus.start_time = SIM_START_MINS # clamp to sim start
                bus.state = "SCHEDULED"

    def generate_passengers(self, current_time_mins):
        total_stops = len([s for s in self.stops.values() if s.name.lower() != "acropolis institutes"])
        if total_stops == 0: return
        
        target_total_passengers = self.daily_capacity * TARGET_DEMAND_MULTIPLIER
        target_per_stop = target_total_passengers / total_stops
        std_dev = 20 # minutes
        
        multiplier = target_per_stop / (std_dev * math.sqrt(2 * math.pi) * 2)
        if current_time_mins >= SHIFT_1_ARRIVAL:
            return
            
        for stop in self.stops.values():
            if stop.name.lower() == "acropolis institutes":
                continue
                # Stagger buses on the same branch by 10 minutes
                bus_branch_order = i // num_branches
                bus.start_time = branch_start_time - (bus_branch_order * 10)
                
                if bus.start_time < SIM_START_MINS:
                    bus.start_time = SIM_START_MINS # clamp to sim start
                bus.state = "SCHEDULED"

    def generate_passengers(self, current_time_mins):
        total_stops = len([s for s in self.stops.values() if s.name.lower() != "acropolis institutes"])
        if total_stops == 0: return
        
        target_total_passengers = self.daily_capacity * TARGET_DEMAND_MULTIPLIER
        target_per_stop = target_total_passengers / total_stops
        std_dev = 20 # minutes
        
        multiplier = target_per_stop / (std_dev * math.sqrt(2 * math.pi) * 2)
        if current_time_mins >= SHIFT_1_ARRIVAL:
            return
            
        for stop in self.stops.values():
            if stop.name.lower() == "acropolis institutes":
                continue
                
            peak1 = SHIFT_1_ARRIVAL - stop.mins_to_destination - 15
            
            # Generate a fixed realistic count of passengers 15 minutes before the bus is scheduled to arrive
            # using a sequence like the user requested: 2, 4, 7, 4, 1
            if current_time_mins == peak1:
                generated = max(0, int(round(random.gauss(4.2, 2.0))))
                
                for _ in range(generated):
                    p_type = "faculty" if random.random() < FACULTY_RATIO else "student"
                    stop.waiting_passengers.append(Passenger(p_type, current_time_mins))
                    self.total_generated += 1

    def step(self, current_time_mins):
        hh = current_time_mins // 60
        mm = current_time_mins % 60
        time_str = f"[{hh:02d}:{mm:02d}]"
        
        # Schedule trips
        if current_time_mins == SIM_START_MINS and not getattr(self, 'shift_1_scheduled', False):
            self.assign_bus_trips(SHIFT_1_ARRIVAL, "Shift 1")
            self.shift_1_scheduled = True

        # Generate Passengers
        self.generate_passengers(current_time_mins)
        
        # Run Scheduler
        if self.scheduler:
            t0 = time.time()
            # Intercept print to capture reallocations
            import io
            import sys
            old_stdout = sys.stdout
            new_stdout = io.StringIO()
            sys.stdout = new_stdout
            
            self.scheduler.schedule(self, current_time_mins)
            
            sys.stdout = old_stdout
            logs = new_stdout.getvalue().strip().split('\n')
            if not hasattr(self, 'reallocations_log'):
                self.reallocations_log = []
            for log in logs:
                if log and "SCHEDULER" in log:
                    print(log) # Print it anyway
                    self.reallocations_log.append(log)
            
            self.scheduler.total_runtime += (time.time() - t0)
        
        # Move Buses
        for bus in self.buses.values():
            if bus.state == "SCHEDULED" and current_time_mins >= bus.start_time:
                bus.state = "EN_ROUTE"
                bus.time_to_next_stop = 0
                print(f"{time_str} Bus {bus.bus_id} starting route {bus.route.route_id} from {bus.route.stops[bus.current_stop_idx].name}")
            
            if bus.state == "EN_ROUTE":
                if bus.time_to_next_stop > 0:
                    bus.time_to_next_stop -= 1
                
                if bus.time_to_next_stop == 0:
                    current_stop = bus.route.stops[bus.current_stop_idx]
                    bus.last_stop_id = current_stop.stop_id
                    
                    if bus.current_stop_idx == len(bus.route.stops) - 1:
                        # Final destination
                        print(f"{time_str} Bus {bus.bus_id} arrived at DESTINATION {current_stop.name}. Unloading {bus.occupancy} pax.")
                        bus.state = "ARRIVED"
                        bus.passengers = []
                        bus.travel_target_stop_id = None
                        bus.travel_duration_mins = 0
                    else:
                        # Priority Boarding Logic
                        MAX_CAPACITY = bus.capacity + 3
                        # Priority Boarding Logic
                        boarded_this_stop = 0
                        faculty_overloaded = False
                        
                        # Separate faculty and students
                        faculty = [p for p in current_stop.waiting_passengers if p.p_type == "faculty"]
                        students = [p for p in current_stop.waiting_passengers if p.p_type == "student"]
                        
                        # Board faculty first (even if normal capacity is reached, up to MAX_CAPACITY)
                        available_for_faculty = max(0, MAX_CAPACITY - bus.occupancy)
                        faculty_to_board = faculty[:available_for_faculty]
                        if bus.occupancy + len(faculty_to_board) > bus.capacity:
                            faculty_overloaded = True
                            
                        bus.passengers.extend(faculty_to_board)
                        boarded_this_stop += len(faculty_to_board)
                        
                        for p in faculty_to_board:
                            p.wait_time = current_time_mins - p.arrival_time
                            self.wait_times.append(p.wait_time)
                            self.faculty_transported += 1
                            self.total_transported += 1
                            
                        # Recalculate available capacity for students (normal capacity)
                        normal_available_for_students = max(0, bus.capacity - bus.occupancy)
                        
                        # [COMM] Logic: Reserve seats for downstream if trailing bus is coming
                        downstream_demand = sum(len(s.waiting_passengers) for s in bus.route.stops[bus.current_stop_idx+1:])
                        reserved_seats = 0
                        trailing_capacity = 0
                        trailing_buses = []
                        
                        if downstream_demand > normal_available_for_students and len(students) > 0:
                            for other_bus in self.buses.values():
                                if other_bus.bus_id == bus.bus_id or other_bus.state not in ["SCHEDULED", "EN_ROUTE"] or not other_bus.route:
                                    continue
                                search_start = other_bus.current_stop_idx if other_bus.state == "EN_ROUTE" else 0
                                for s_idx in range(search_start, len(other_bus.route.stops)):
                                    if other_bus.route.stops[s_idx].name.lower() == current_stop.name.lower():
                                        cap = other_bus.capacity - other_bus.occupancy
                                        if cap > 0:
                                            trailing_capacity += cap
                                            trailing_buses.append(other_bus.bus_id)
                                        break
                                        
                            if trailing_capacity > 0:
                                reserved_seats = min(normal_available_for_students, downstream_demand, trailing_capacity, len(students))
                                if reserved_seats > 0:
                                    normal_available_for_students -= reserved_seats
                                    msg = f"[COMM] Bus {bus.bus_id} reserved {reserved_seats} seats for downstream, leaving students for {', '.join(trailing_buses)}"
                                    if not hasattr(self, 'reallocations_log'): self.reallocations_log = []
                                    self.reallocations_log.append(msg)
                                    print(f"{time_str} {msg}")

                        # Board students next up to normal capacity
                        students_to_board = students[:normal_available_for_students]
                        bus.passengers.extend(students_to_board)
                        boarded_this_stop += len(students_to_board)
                        
                        for p in students_to_board:
                            p.wait_time = current_time_mins - p.arrival_time
                            self.wait_times.append(p.wait_time)
                            self.students_transported += 1
                            self.total_transported += 1
                            
                        students_left = students[len(students_to_board):]
                        faculty_left = faculty[len(faculty_to_board):]
                        overload_count = 0
                        overload_reason = ""
                        
                        # [LAST RESORT OVERLOAD]
                        total_left = len(students_left) + len(faculty_left)
                        if 0 < len(students_left) <= 3 and len(faculty_left) == 0:
                            overload_available = max(0, MAX_CAPACITY - bus.occupancy)
                            if overload_available >= len(students_left):
                                is_stranded = True
                                if trailing_capacity > 0:
                                    is_stranded = False # Trailing bus is coming
                                else:
                                    # Re-check strictly for any incoming bus
                                    for other_bus in self.buses.values():
                                        if other_bus.bus_id == bus.bus_id or other_bus.state not in ["SCHEDULED", "EN_ROUTE"] or not other_bus.route: continue
                                        search_start = other_bus.current_stop_idx if other_bus.state == "EN_ROUTE" else 0
                                        for s_idx in range(search_start, len(other_bus.route.stops)):
                                            if other_bus.route.stops[s_idx].name.lower() == current_stop.name.lower():
                                                if (other_bus.capacity - other_bus.occupancy) > 0:
                                                    is_stranded = False
                                                break
                                        if not is_stranded: break
                                        
                                if is_stranded:
                                    overload_count = len(students_left)
                                    bus.passengers.extend(students_left)
                                    boarded_this_stop += overload_count
                                    for p in students_left:
                                        p.wait_time = current_time_mins - p.arrival_time
                                        self.wait_times.append(p.wait_time)
                                        self.students_transported += 1
                                        self.total_transported += 1
                                    students_left = []
                                    total_left = 0
                                    overload_reason = " (Overloaded to avoid stranding small group)"
                            else:
                                overload_reason = f" — {total_left} stranded (Bus hit absolute max 48 capacity)"
                        elif len(students_left) > 3:
                            if reserved_seats > 0:
                                overload_reason = f" — {total_left} left intentionally (Saved seats for downstream)"
                            else:
                                overload_reason = f" — {total_left} stranded (Group too large for 3-person overload limit)"
                        elif len(faculty_left) > 0:
                            overload_reason = f" — {total_left} stranded (Bus hit absolute max 48 capacity)"
                        elif reserved_seats > 0:
                            overload_reason = f" — {total_left} left intentionally (Saved seats for downstream)"
                        elif total_left > 0:
                            overload_reason = f" — {total_left} stranded"
                            
                        if faculty_overloaded and not overload_reason:
                            overload_reason = " (Faculty priority - forced overload)"
                            
                        current_stop.waiting_passengers = faculty_left + students_left
                        
                        bus.total_transported += boarded_this_stop
                        if bus.occupancy > bus.peak_occupancy:
                            bus.peak_occupancy = bus.occupancy
                            
                        if boarded_this_stop > 0 or total_left > 0:
                            msg = f"Bus {bus.bus_id} ({bus.occupancy}/{bus.capacity}) picked up {boarded_this_stop} pax at {current_stop.name}{overload_reason}"
                            print(f"{time_str} [BOARD] {msg}")
                            if not hasattr(self, 'reallocations_log'): self.reallocations_log = []
                            self.reallocations_log.append(f"[BOARD] {msg}")
                        # Set time to next stop
                        bus.time_to_next_stop = bus.route.travel_times[bus.current_stop_idx]
                        bus.travel_duration_mins = bus.time_to_next_stop
                        bus.current_stop_idx += 1
                        bus.travel_target_stop_id = bus.route.stops[bus.current_stop_idx].stop_id

    def run(self):
        print("Starting baseline simulation...")
        
        self.shift_1_scheduled = False
        self.reallocations_log = []

        for tick in range(TOTAL_TICKS):
            current_time_mins = SIM_START_MINS + tick
            self.step(current_time_mins)

        self.print_stats()

    def print_stats(self):
        print("\n=== SIMULATION STATS ===")
        print(f"Total Passengers Generated: {self.total_generated}")
        print(f"Total Passengers Transported: {self.total_transported} (Faculty: {self.faculty_transported}, Students: {self.students_transported})")
        
        left_behind = sum(len(s.waiting_passengers) for s in self.stops.values())
        print(f"Total Passengers Left at Stops: {left_behind}")
        if left_behind > 0:
            print("  (Note: Passengers are stranded only when groups exceed the 3-person overload limit,")
            print("         or when a bus reaches the absolute hard maximum capacity of 48 passengers.)")
        
        if self.wait_times:
            print(f"Average Wait Time (Transported): {statistics.mean(self.wait_times):.2f} mins")
            print(f"Median Wait Time (Transported): {statistics.median(self.wait_times):.2f} mins")
            
        if hasattr(self, 'scheduler') and self.scheduler:
            print(f"Total Reallocations by Scheduler: {self.scheduler.reallocations}")
            print(f"Scheduler Execution Time: {self.scheduler.total_runtime:.4f} seconds")
            
        print("\nBus Utilization:")
        total_potential_seats = self.daily_capacity # If every bus does 2 shifts
        # But wait, did every bus run? Let's sum the peak occupancy as a rough metric
        for bus in self.buses.values():
            print(f"Bus {bus.bus_id:4s} | Capacity: {bus.capacity} | Peak Occ: {bus.peak_occupancy:2d} | Total Moved: {bus.total_transported}")

if __name__ == "__main__":
    engine = SimulationEngine()
    engine.load_data()
    engine.run()
