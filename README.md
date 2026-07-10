# Acropolis Bus Scheduling System — DAA Project

A dynamic bus scheduling and reallocation simulation built for Acropolis Institute, Indore. This project compares three different scheduling algorithms (Greedy, Dynamic Programming, and a Baseline with no scheduler) to solve the problem of surge demand and stranded passengers at shared route junctions during the morning shift.

## Features

- **Live Dispatch Dashboard**: An interactive Leaflet map simulating the bus network.
- **Three Algorithms**: Compare O(n log n) Greedy vs O(2ⁿ) DP vs O(1) Baseline.
- **Dynamic Reallocation**: Watch buses get intelligently diverted from under-utilized routes to overloaded routes at shared junctions in real-time.
- **Demand Injection**: Manually inject surge demand at any stop and watch the scheduler adapt.

---

## 🛠️ Installation & Setup

### Prerequisites
You need **Python 3.8+** installed on your system.

### Step 1: Clone the repository
```bash
git clone https://github.com/your-username/acropolis-bus-scheduler.git
cd acropolis-bus-scheduler
```

### Step 2: Install dependencies
The project requires `Flask` for the backend server and `networkx` for graph routing (if needed for DP).
```bash
pip install Flask networkx flask-cors
```

### Step 3: Run the simulation
Start the Flask development server:
```bash
python app.py
```

### Step 4: Open in browser
Open your web browser and navigate to:
```
http://127.0.0.1:5000/
```

- **Live Simulation:** `http://127.0.0.1:5000/`
- **Algorithm Analysis:** `http://127.0.0.1:5000/explain`

---

## 📂 Core Project Files

This repository has been cleaned up. The main files driving the simulation are:

- **`app.py`**: The Flask backend server that serves the UI and processes simulation ticks via API endpoints.
- **`simulate.py`**: The core simulation engine. Manages time, passenger generation, bus movement, boarding/alighting logic, and tracking stranded passenger metrics.
- **`scheduler.py`**: Contains the implementations for the `GreedyScheduler` and `DPScheduler`. This is where the core DAA algorithms live.
- **`static/`**:
  - `index.html`: The main operations dashboard UI.
  - `explain.html`: The algorithm analysis and comparison page.
  - `main.js`: Frontend logic for fetching topology, managing Leaflet maps, and stepping through the simulation.
- **`data/`**: JSON files containing the real-world route data, bus assignments, and geocoded stop coordinates for Indore.
