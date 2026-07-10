# Greedy-Based Dynamic Campus Bus Scheduling and Resource Allocation System

**Project type: Design & Analysis of Algorithms (DAA) project.**
The bus transport system is only the real-world problem used to demonstrate and evaluate a scheduling algorithm — **the algorithm is the product**, not the bus app. Everything below should guide implementation with that priority.

Institution: Acropolis Institute of Technology & Research (AITR), Indore.
Real dataset: official transport schedule effective **01 Aug 2024** (may have minor 2025/2026 changes, not structurally different).

---

## 1. What this is NOT

- Not a bus management system.
- Not a GPS transport tracker.
- Not a UI showcase.

It IS a demonstration of **greedy algorithm design**, applied to real-time bus-to-route reallocation, with rigorous complexity analysis and comparison against alternative algorithms (DP, Branch & Bound, Genetic, Ant Colony, Integer Programming, RL).

---

## 2. Problem Statement

AITR runs ~69 buses across 25 routes into two shifts (Shift 1: 8:30am–2:40pm campus, Shift 2: 10:30am–5:00pm campus). During peak hours: some buses overcrowd, some run empty, faculty must always get a seat, and allocation is currently static despite demand changing minute to minute. The project designs a **greedy dynamic scheduling algorithm** that reallocates buses to routes in real time to minimize waiting time and overcrowding while respecting hard constraints (faculty always seated, capacity never exceeded, one route per bus at a time).

## 3. Why Greedy

Scheduling decisions must happen continuously (every simulated minute) as students arrive, buses move, and routes overload. A full re-optimization every cycle is too expensive. Greedy gives O(n+m) per-cycle decisions (n = buses, m = routes) — fast, simple, good-enough, real-time-capable — at the cost of guaranteed global optimality (this trade-off is exactly what the DAA analysis should measure).

## 4. Core Formulation

- **Input each cycle:** current bus positions/occupancy, current passenger demand (student + faculty) per stop/route, route topology.
- **Output each cycle:** updated bus→route assignments (reassign or continue).
- **Hard constraints:** faculty always seated; capacity never exceeded; a bus serves one route at a time.
- **Primary objective:** minimize average student waiting time.
- **Secondary objectives:** minimize overcrowding, maximize utilization, minimize unnecessary reallocations.

## 5. Greedy Algorithm Sketch

```
every scheduling cycle:
    collect current state
    detect overloaded routes                  # O(m)
    for each overloaded route:
        find candidate buses                    # operational, has free seats,
                                                 # not already reassigned this cycle,
                                                 # can reach the route (see §8 below)
        score each candidate                    # e.g. f(seats_available, distance/ETA,
                                                 #     current route's own demand)
        assign best-scoring candidate bus to route
    repeat
```

Complexity per cycle: analyze routes O(m) + candidate search O(n) + scoring O(n) + selection O(n) = **O(n+m)**, space **O(n)**.

Known limitation to discuss in the report: greedy is myopic — e.g. it may grab a nearby bus with only 5 free seats over a farther bus with 35, causing a second reassignment minutes later that a global optimizer would have avoided.

## 6. Dataset Reality Check (this is REAL data, not invented)

Parsed from the official Acropolis PDF (`Bus Route For Arrival 01 Aug 24`):

| Entity | Count | Source |
|---|---|---|
| Buses | 69 (bus numbers G1–G79, non-sequential; one bus number illegible in source, recorded as `"G"`) | real |
| Routes | 25 route clusters | real |
| Drivers | 70 (one driver, Reetooraj Solanki / G28, is listed on two route sheets — likely runs different shifts/legs) | real |
| Stops | 456 stop entries across all routes, 398 unique stop names | real |
| Shift timings per stop | present for most stops (Shift 1 / Shift 2 arrival time) | real, some gaps |
| Bus seating capacity | **not in source** | must be simulated (suggest 40–52 seats, configurable) |
| Live occupancy / passenger counts | **not in source** | must be simulated |
| GPS coordinates, distances, bus speed | **not in source** | must be simulated or geocoded separately if desired |

**Data quality caveats (already reflected in the JSON):**
- A handful of stop rows in the original PDF had blank/garbled times (e.g. "0:00", misaligned columns) — these are preserved as-is or nulled rather than guessed.
- Several routes are actually **2–4 feeder branches merging into one trunk route** before reaching campus (e.g. R01 has three separate "(Start)" branches — Treasure Fantasy, Reti Mandi, Nurani Nagar — that converge at Ranjeet Hanuman/Dravid Nagar/Usha Nagar/Mhow Naka). Model this as a graph with multiple origin nodes per route, not a single linear path.
- Route R16/R17 share bus G28 and driver Reetooraj Solanki — treat as one physical bus potentially serving two logical routes across the day.

## 7. Files in `/data`

- **`buses.json`** — busNumber, driver, phone, assignedRoute, capacity (null — simulate), status.
- **`routes.json`** — routeId, startStop, destination (always "Acropolis Institutes"), numStops, assignedBuses, arrivalTimes, stopSequence (ordered list of stop names).
- **`drivers.json`** — driver, phone, bus, route.
- **`stops.json`** — stopId (`{routeId}-S{nn}`), name, order (position within that route), route.
- **`schema.json`** — field-level schema reference for all four files above.

These are the ground-truth static tables. Simulated/dynamic layers (occupancy, live demand, bus position, event clock) sit on top and are **generated by the simulation engine**, not hardcoded.

## 8. Important modeling insight: shared stops = reassignment junctions

Cross-referencing `stops.json` by name shows **36 stop names appear on 2+ different routes** (excluding the shared "Acropolis Institutes" endpoint). Examples:

| Stop | Routes sharing it |
|---|---|
| Vikas Nagar | R15, R16, R17, R18, R19 |
| Kshipra | R16, R17, R19, R22, R23 |
| Van Mandal | R15, R16, R18, R19 |
| Dakachya | R15, R16, R17, R24 |
| Mhow Naka | R01, R05 |
| Khajrana Chouraha | R02, R13 |
| Bhanwarkua/Rajiv Gandhi/IT Park Chouraha cluster | R03, R05 |
| Dewas Naka | R08, R09 |

**These shared physical stops are the natural candidate points for the greedy algorithm's "can this bus reasonably reach the destination route?" feasibility check** — a bus can realistically be rerouted onto another route at a stop both routes pass through, rather than needing an arbitrary straight-line distance heuristic. This is a strong, real-data-backed way to define "candidate bus" in §5 instead of an invented distance formula.

## 9. Recommended Architecture

```
Transport Dataset (this package)
        ↓
Simulation Engine   (clock, passenger generation, bus movement, boarding, occupancy)
        ↓
Scheduler Interface  →  GreedyScheduler (Phase 2), DynamicProgrammingScheduler, GeneticScheduler, ...
        ↓
Metrics Collector   (avg/max wait, faculty wait, utilization, standing count, reallocations, runtime)
        ↓
Visualization
```

Keep the scheduler **pluggable**: define one interface, e.g. `Scheduler.schedule(state) -> assignments`, so Greedy, DP, Genetic, etc. can all be swapped in against the identical simulation and identical metrics — this turns the project into an algorithm evaluation platform rather than a single-algorithm demo.

## 10. Build Order (do NOT build UI first)

1. Data model (load these JSON files)
2. Simulation engine (clock, passenger generation, bus movement, boarding, occupancy) — **Phase 1, no algorithm yet**
3. Scheduler interface
4. GreedyScheduler — **Phase 2**
5. Metrics collector — **Phase 3**
6. Alternative schedulers for comparison — **Phase 4**
7. Visualization + final report — **Phase 5**

## 11. Evaluation Metrics to Record Every Run

Average waiting time, maximum waiting time, faculty waiting, students waiting, bus utilization %, passengers onboard, standing students, number of reallocations, algorithm execution time (wall-clock, per cycle and total).

## 12. Known Constraints — check every phase plan against these before approving it

1. **Multi-branch routes.** ~15 of the 25 routes have 2–4 buses assigned to one `routeId`, but that route's `stopSequence` contains multiple `(Start)` markers — each bus covers a different feeder branch merging onto a shared trunk before Acropolis, not the full stop list from index 0. Any simulation/scheduling logic that replays the entire `stopSequence` for every assigned bus is wrong. Always ask: "which branch does each bus start from?"
2. **Faculty vs. student passengers.** Generate both types from Phase 1 onward, even before priority logic exists — retrofitting this later is painful. The hard constraint "faculty always seated" can't be tested if only one generic passenger type is ever generated.
3. **Don't invent constants the data already answers.** The source PDF has real per-stop Shift 1/Shift 2 timestamps for most stops (dropped in the compact `stops.json` summary, but present in the original PDF text) — reconstruct real inter-stop travel time from those where available; use a flat default only for genuine gaps. Same principle applies to any other "we'll just assume X" placeholder — check against the source data first.
4. **Scheduler must stay pluggable.** Every phase's plan should still be feeding into (or building toward) a `Scheduler.schedule(state) -> assignments` interface, not hardcoding logic straight into the simulator.
5. **Metrics collection starts early.** Waiting time, utilization, reallocation count, and runtime should be logged from Phase 1 onward, even before an algorithm exists to evaluate — Phase 3's evaluation depends on this being in place already.
6. **No UI before Phase 5.** If a plan mentions frontend/visualization work before then, push back.

Use this list as a 1-minute self-check on every Antigravity phase plan — if it passes all six, approve it without further review.

## 13. Alternative Algorithms for Comparison Chapter

Dynamic Programming, Branch and Bound, Genetic Algorithm, Ant Colony Optimization, Integer Programming, Reinforcement Learning — compare on time complexity, space complexity, optimality, real-time suitability, practical feasibility.
