from scheduler import GreedyScheduler, DPScheduler

class MockStop:
    def __init__(self, name, waiting=0):
        self.name = name
        self.waiting_passengers = [1] * waiting

class MockRoute:
    def __init__(self, r_id, stops):
        self.route_id = r_id
        self.stops = stops

class MockBus:
    def __init__(self, bus_id, route, current_stop_idx):
        self.bus_id = bus_id
        self.route = route
        self.current_stop_idx = current_stop_idx
        self.capacity = 45
        self.occupancy = 0
        self.state = "EN_ROUTE"

class MockEngine:
    def __init__(self):
        self.routes = {}
        self.buses = {}

def run_test():
    # Setup Routes
    route_A = MockRoute("Route_A", [MockStop('StartA'), MockStop('JunctionX'), MockStop('EndA', 50)])
    route_B = MockRoute("Route_B", [MockStop('StartB'), MockStop('JunctionX'), MockStop('EndB', 40)])
    route_C = MockRoute("Route_C", [MockStop('StartC'), MockStop('JunctionX'), MockStop('EndC')]) # Bus 1 route (only shares with A)
    route_D = MockRoute("Route_D", [MockStop('StartD'), MockStop('JunctionX'), MockStop('EndD')]) # Bus 2 route (shares with A and B)
    
    # Setup Buses
    bus1 = MockBus("Bus_1", route_C, 1) # At JunctionX. Can ONLY go to A (because B doesn't share C's path conceptually, but wait... 
    # Let's make sure route_B does NOT share a stop with route_C.
    # We do this by renaming the junction for Bus 1 vs Bus 2.
    
    # Let's completely redefine for clarity:
    # Route A (needs 50) passes through Junction 1 and Junction 2.
    # Route B (needs 40) passes through Junction 2 only.
    
    route_A = MockRoute("Route_A", [MockStop('Junction1'), MockStop('Junction2'), MockStop('EndA', 50)])
    route_B = MockRoute("Route_B", [MockStop('Junction2'), MockStop('EndB', 40)])
    
    # Bus 1 is at Junction 1. It can ONLY reach Route A.
    bus1 = MockBus("Bus_1", MockRoute("R1", [MockStop('Junction1'), MockStop('End1')]), 0)
    
    # Bus 2 is at Junction 2. It can reach Route A AND Route B.
    # To force Greedy to pick Bus 2 for Route A, we make Route A the most overloaded (50 vs 40).
    # Greedy processes Route A first. It sees Bus 1 and Bus 2. 
    # Bus 1 provides 50 demand. Bus 2 provides 50 demand.
    # If Bus 2 is first in the list, Greedy takes Bus 2 for Route A.
    # Then Route B is processed. Bus 1 cannot reach Route B. Route B gets NOTHING.
    bus2 = MockBus("Bus_2", MockRoute("R2", [MockStop('Junction2'), MockStop('End2')]), 0)
    
    # Initialize Engine
    engine = MockEngine()
    engine.routes = {"Route_A": route_A, "Route_B": route_B, "R1": bus1.route, "R2": bus2.route}
    # Important: put bus2 first in dict so Greedy sees it first and stable sort keeps it first
    engine.buses = {"Bus_2": bus2, "Bus_1": bus1}
    
    print("--- Running Greedy Scheduler ---")
    greedy = GreedyScheduler()
    greedy.schedule(engine, 0)
    print(f"Greedy Reallocations: {greedy.reallocations}")
    
    # Reset Buses
    bus1.route = MockRoute("R1", [MockStop('Junction1'), MockStop('End1')])
    bus1.current_stop_idx = 0
    bus2.route = MockRoute("R2", [MockStop('Junction2'), MockStop('End2')])
    bus2.current_stop_idx = 0
    
    print("\n--- Running DP Scheduler ---")
    dp = DPScheduler()
    dp.schedule(engine, 0)
    print(f"DP Reallocations: {dp.reallocations}")

if __name__ == "__main__":
    run_test()
