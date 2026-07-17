# Acropolis Bus Scheduling Simulation

A dynamic, map-based simulation engine designed to solve the "Last Bus" and "Shared Junction" transit problems during morning university commutes. This project implements and compares a **Greedy Scheduler**, **Dynamic Programming (DP)**, and a **Baseline Control** to minimize stranded passengers using real-time inter-bus communication and dynamic reallocation.

## 🚀 Project Execution Details

### 1. Prerequisites
- **Python 3.8+**
- Required Libraries: `flask`
- A modern web browser (Chrome, Edge, Firefox)

### 2. Installation & Running Locally
1. Clone this repository to your local machine:
   ```bash
   git clone https://github.com/your-username/acropolis-bus-scheduler.git
   cd acropolis-bus-scheduler
   ```
2. Install the required Python packages:
   ```bash
   pip install flask
   ```
3. Start the simulation server:
   ```bash
   python app.py
   ```
4. Open your web browser and navigate to:
   **http://localhost:5000**

### 3. Executing the Simulation
- **The Dashboard:** Upon loading, you will see a live map of the transit routes.
- **Select Algorithm:** On the left panel, choose between `Greedy`, `Dynamic Programming`, or `Baseline`.
- **Run/Pause:** Click the `Run` button to start the clock. The buses will dispatch, passengers will generate, and you can monitor real-time decisions in the Dispatch Log on the right.
- **Randomized Testing:** Click the `Randomized Students` button to generate completely unpredictable Gaussian distributions of crowds at the stops, stress-testing the algorithms.

---

## 🧠 Algorithmic Implementation & Results

### The "Last Bus" & "Shared Junction" Problem
When multiple routes share a junction (e.g., Van Mandal), the first bus to arrive greedily absorbs all waiting passengers. This leaves the bus completely full, stranding passengers at its unique downstream stops, while a trailing bus on a different route might drive past completely empty.

### Inter-Bus Communication `[COMM]`
To solve this, our algorithms implement a communication layer. When a bus arrives at a junction, it calculates its downstream capacity needs. It then scans the network schedule for trailing buses. If a trailing bus has capacity, the current bus intentionally reserves seats for its downstream stops, leaving the current crowd for the trailing bus to pick up.

### Performance Comparison (Stress-Tested up to 480+ Passengers)

| Metric | Baseline | Greedy Scheduler | DP Scheduler |
| :--- | :---: | :---: | :---: |
| **Strategy** | Fixed Routes | Dynamic `[COMM]` + Reallocation | Mathematical Snapshot |
| **Average Transport Rate** | ~85% | **94.1%** | 92.7% |
| **Average Stranded Rate** | ~15% | **5.9%** | 7.3% |
| **Dynamic Reallocations** | 0 | **2 - 3 per run** | 1 per run |

**Conclusion:** The **Greedy Scheduler** drastically outperforms Dynamic Programming in this real-time environment. Because DP is overly cautious about maintaining mathematical global perfection, it fails to make aggressive interventions during unexpected crowd surges. The Greedy algorithm actively communicates across routes and aggressively shifts 2-3 buses per run, resulting in a significantly lower stranded passenger rate.

## 👥 Priority Boarding
The simulation strictly enforces **Faculty Priority Boarding**, ensuring that faculty members are boarded first at all stops. The system also utilizes a "Last-Resort Overload" buffer (+3 capacity) to prevent stranding tiny groups if no trailing bus is coming.
