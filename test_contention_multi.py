"""
Multi-Scenario Divergence Test
===============================
Tests Greedy vs DP across 5 distinct surge configurations:

  S1  R15/R16/R18 three-way junction surge  — "Van Mandal" & "Vikas Nagar" share all 3 routes
  S2  Asymmetric two-arm surge: R15 heavy, R16 medium, R18 empty
  S3  Competing targets: R01 and R13 BOTH heavily surged, only 1 spare bus available at junction
  S4  R08/R09 cluster surge  (2-way junction)
  S5  Full-network symmetric surge  (no spare capacity anywhere)

For every scenario the same random seed is used to isolate algorithm differences.
The key question: does DP ever make MORE reassignments or transport MORE passengers than Greedy?
"""

import copy
import json
import time
import random
from collections import defaultdict
from simulate import SimulationEngine, Passenger, SHIFT_1_ARRIVAL, SIM_START_MINS
from scheduler import GreedyScheduler, DPScheduler

# ─────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────

def reset_engine(engine):
    """Clear all waiting passengers and bus states."""
    for stop in engine.stops.values():
        stop.waiting_passengers = []
    for bus in engine.buses.values():
        bus.passengers = []
        bus.state = "IDLE"
        bus.is_helper = False
        bus.route = None
        bus.current_stop_idx = 0
        bus.time_to_next_stop = 0
        bus.start_time = -1
        bus.total_transported = 0
        bus.peak_occupancy = 0
    engine.total_generated = 0
    engine.total_transported = 0
    engine.total_capacity = 0
    engine.wait_times = []
    engine.faculty_transported = 0
    engine.students_transported = 0

def inject_surge(engine, surge_routes, pax_per_route):
    """Inject a fixed number of waiting passengers across all stops of specific routes."""
    gen = engine.total_generated
    for stop in engine.stops.values():
        if stop.route_id in surge_routes:
            count = pax_per_route.get(stop.route_id, 0)
            per_stop = max(1, count // 5)
            for _ in range(per_stop):
                stop.waiting_passengers.append(Passenger("student", gen))
                gen += 1
    engine.total_generated = gen

def run_one_scenario(engine_template, scheduler_class, surge_routes, pax_per_route, seed=42):
    """
    Run a single forward-pass simulation (just the scheduling tick, no full time loop).
    Returns (reallocations, transported, runtime_ms).
    """
    random.seed(seed)

    # Deep-copy the engine so both Greedy and DP start from identical state
    # We can't deepcopy easily, so we reset + reinject
    reset_engine(engine_template)
    inject_surge(engine_template, surge_routes, pax_per_route)

    # Schedule initial bus trips (replicate what assign_bus_trips does)
    engine_template.shift_1_scheduled = False
    engine_template.shift_2_scheduled = False
    engine_template.reallocations_log = []
    engine_template.assign_bus_trips(SHIFT_1_ARRIVAL, "Shift 1")

    scheduler = scheduler_class()
    t0 = time.perf_counter()

    # Run just the scheduling ticks (not the full sim, we want to measure one decision pass)
    for tick in range(SHIFT_1_ARRIVAL - SIM_START_MINS):
        current_time_mins = SIM_START_MINS + tick
        scheduler.schedule(engine_template, current_time_mins)

        # Move buses (so they reach junctions)
        for bus in engine_template.buses.values():
            if bus.state == "SCHEDULED" and current_time_mins >= bus.start_time:
                bus.state = "EN_ROUTE"
                bus.time_to_next_stop = 0
            if bus.state == "EN_ROUTE":
                if bus.time_to_next_stop > 0:
                    bus.time_to_next_stop -= 1
                if bus.time_to_next_stop == 0:
                    if bus.current_stop_idx == len(bus.route.stops) - 1:
                        current_stop = bus.route.stops[bus.current_stop_idx]
                        for p in bus.passengers:
                            p.wait_time = current_time_mins - p.arrival_time
                            engine_template.wait_times.append(p.wait_time)
                        engine_template.total_transported += bus.occupancy
                        bus.passengers = []
                        bus.state = "ARRIVED"
                    else:
                        current_stop = bus.route.stops[bus.current_stop_idx]
                        # Board passengers
                        to_board = current_stop.waiting_passengers[:bus.capacity - bus.occupancy]
                        boarded = len(to_board)
                        bus.passengers.extend(to_board)
                        current_stop.waiting_passengers = current_stop.waiting_passengers[boarded:]
                        bus.total_transported += boarded
                        bus.peak_occupancy = max(bus.peak_occupancy, bus.occupancy)
                        bus.current_stop_idx += 1
                        if bus.current_stop_idx < len(bus.route.stops):
                            bus.time_to_next_stop = bus.route.travel_times[bus.current_stop_idx - 1]

    elapsed_ms = (time.perf_counter() - t0) * 1000
    stranded = sum(len(s.waiting_passengers) for s in engine_template.stops.values())

    return scheduler.reallocations, engine_template.total_transported, stranded, elapsed_ms


# ---------------------------------------------------------
# Scenarios
# ---------------------------------------------------------

SCENARIOS = [
    {
        "name": "S1 - R15/R16/R18 symmetric 3-way surge",
        "desc": "Equal heavy demand on all three routes sharing Van Mandal & Vikas Nagar",
        "surge_routes": {"R15", "R16", "R18"},
        "pax_per_route": {"R15": 200, "R16": 200, "R18": 200},
    },
    {
        "name": "S2 - R15/R16/R18 asymmetric: R15 heavy, R16 medium, R18 empty",
        "desc": "R15 critically overloaded. Spare bus on R18 at shared junction -- Greedy should divert it to R15, missing R16",
        "surge_routes": {"R15", "R16"},
        "pax_per_route": {"R15": 300, "R16": 80},
    },
    {
        "name": "S3 - 3-way competing targets: R15=heavy, R16=heavy, R18=empty",
        "desc": "Both R15 and R16 need help. R18 has 1 spare bus at the shared Van Mandal junction.",
        "surge_routes": {"R15", "R16"},
        "pax_per_route": {"R15": 250, "R16": 250},
    },
    {
        "name": "S4 - R08/R09 two-way cluster surge",
        "desc": "2-route junction -- control scenario to verify Greedy and DP behave identically when no 3-way contention exists",
        "surge_routes": {"R08", "R09"},
        "pax_per_route": {"R08": 200, "R09": 200},
    },
    {
        "name": "S5 - Full 10-route saturation (no spare capacity)",
        "desc": "All routes equally surged. No spare buses for reallocation. Both schedulers should do 0 moves.",
        "surge_routes": {"R01", "R02", "R03", "R05", "R08", "R09", "R13", "R15", "R16", "R18"},
        "pax_per_route": {r: 300 for r in ["R01","R02","R03","R05","R08","R09","R13","R15","R16","R18"]},
    },
]


# ---------------------------------------------------------
# Main
# ---------------------------------------------------------

def main():
    print("Initializing engine template...")
    engine = SimulationEngine()
    engine.load_data()
    print(f"Loaded: {len(engine.routes)} routes, {len(engine.buses)} buses, {len(engine.stops)} stops\n")

    header = f"{'Scenario':<54} {'Sched':<7} {'Reallocations':>13} {'Transported':>12} {'Stranded':>10} {'Time (ms)':>10}"
    print(header)
    print("-" * len(header))

    results = []
    for scenario in SCENARIOS:
        for sched_class, sched_name in [(GreedyScheduler, "Greedy"), (DPScheduler, "DP")]:
            reallocations, transported, stranded, elapsed_ms = run_one_scenario(
                engine,
                sched_class,
                scenario["surge_routes"],
                scenario["pax_per_route"],
            )
            row = {
                "scenario": scenario["name"],
                "scheduler": sched_name,
                "reallocations": reallocations,
                "transported": transported,
                "stranded": stranded,
                "elapsed_ms": round(elapsed_ms, 2),
            }
            results.append(row)
            print(f"{scenario['name']:<54} {sched_name:<7} {reallocations:>13} {transported:>12} {stranded:>10} {elapsed_ms:>9.2f}ms")

    # Determine divergence
    print("\n--- DIVERGENCE ANALYSIS ---")
    for i in range(0, len(results), 2):
        greedy = results[i]
        dp = results[i+1]
        g_realloc, d_realloc = greedy["reallocations"], dp["reallocations"]
        g_trans, d_trans = greedy["transported"], dp["transported"]
        
        diverges = (g_realloc != d_realloc) or (g_trans != d_trans)
        verdict = ">>> DIVERGED <<<" if diverges else "same result"
        
        scenario_name = greedy["scenario"]
        if diverges:
            print(f"\n[{scenario_name}]")
            print(f"  Greedy: {g_realloc} reallocations, {g_trans} transported")
            print(f"  DP:     {d_realloc} reallocations, {d_trans} transported")
            print(f"  => {verdict}")
            if d_trans > g_trans:
                extra = d_trans - g_trans
                print(f"  DP transported {extra} more passengers. DP wins.")
            elif g_trans > d_trans:
                print(f"  Greedy transported more. DP is over-engineering.")
        else:
            print(f"[{scenario_name}] => {verdict} ({g_trans} transported, {g_realloc} reallocations)")

    # CSV export
    import csv
    with open("contention_results.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["scenario","scheduler","reallocations","transported","stranded","elapsed_ms"])
        w.writeheader()
        w.writerows(results)
    print("\n=> Saved contention_results.csv")

if __name__ == "__main__":
    main()
