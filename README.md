# Acropolis Bus Scheduling — DAA Project Starter Package

This package contains everything needed to hand off to an AI coding assistant (e.g. Antigravity) to start building the project.

## Contents

```
PROJECT_CONTEXT.md   ← paste this into Antigravity first, as project context / system prompt material
README.md            ← this file
data/
  buses.json          69 real buses (bus number, driver, phone, assigned route)
  routes.json         25 real routes (stop sequence, assigned buses, arrival times)
  drivers.json        70 real drivers (name, phone, bus, route)
  stops.json          456 real stop entries, 398 unique stop names, with route + order
  schema.json         field reference for the four files above
```

## How to use this with Antigravity

1. Start a new project / workspace in Antigravity.
2. Drop the `data/` folder into the project as-is — this is your static dataset layer.
3. Paste `PROJECT_CONTEXT.md` into the chat/context so the AI understands: (a) this is a DAA project where the algorithm is the deliverable, not a bus app, (b) the data is real but incomplete (no capacity/occupancy/GPS — those must be simulated), (c) the build order is simulation → scheduler interface → greedy → metrics → alternatives → visualization, NOT UI-first.
4. Ask it to start with **Phase 1 only**: load `data/*.json`, build the simulation clock, passenger generation, bus movement, boarding, and occupancy tracking. No optimization algorithm yet.
5. Once Phase 1 runs and produces sensible occupancy/waiting numbers, move to Phase 2 (GreedyScheduler) using the shared-stop junction insight in §8 of `PROJECT_CONTEXT.md` to define which buses are valid reassignment candidates.

## Known data gaps to configure (not real, must be simulated)

- Bus seating capacity — suggest 40–52 seats per bus, configurable per bus if you want variety.
- Live passenger/faculty counts at each stop — generate via a random/Poisson arrival model, higher during peak windows.
- GPS positions / distances between stops / bus speed — either simulate abstractly (stop-index distance) or, if you want real geography, geocode the stop names separately (not included here).

## Data quality notes

- One bus number is illegible in the source PDF and recorded as `"G"` — treat as unknown/needs correction if you find the original number.
- A few stop timing cells were blank or garbled in the source table; these were left blank/approximate rather than invented.
- Several routes have multiple starting branches that merge into one trunk before reaching campus — see §6 of `PROJECT_CONTEXT.md`.
