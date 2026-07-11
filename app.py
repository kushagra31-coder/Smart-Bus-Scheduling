from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from simulate import SimulationEngine, SIM_START_MINS, TOTAL_TICKS, SHIFT_1_ARRIVAL
import networkx as nx

app = Flask(__name__, static_folder='static')
CORS(app)

engine = None
current_tick = 0
pos_cache = None

def init_engine():
    global engine, current_tick
    engine = SimulationEngine()
    engine.load_data()
    # Let's set it to Greedy for the visualizer by default, or read from request
    engine.scheduler = None 
    
    engine.shift_1_scheduled = False
    engine.reallocations_log = []
    current_tick = 0

@app.route('/')
def index():
    return app.send_static_file('index.html')

@app.route('/explain')
def explain():
    return app.send_static_file('explain.html')

@app.route('/reset', methods=['POST'])
def reset():
    data = request.json
    scheduler_type = data.get('scheduler', 'Greedy')
    init_engine()
    
    if scheduler_type == 'Greedy':
        from scheduler import GreedyScheduler
        engine.scheduler = GreedyScheduler()
    elif scheduler_type == 'DP':
        from scheduler import DPScheduler
        engine.scheduler = DPScheduler()
    else:
        engine.scheduler = None
        
    return jsonify({"status": "reset", "scheduler": scheduler_type})

@app.route('/topology', methods=['GET'])
def get_topology():
    if engine is None:
        init_engine()
        
    try:
        import json
        with open('data/stops_geo.json', 'r') as f:
            geo_data = json.load(f)
    except FileNotFoundError:
        geo_data = {}
        
    try:
        with open('data/edge_geometries.json', 'r') as f:
            edge_geoms = json.load(f)
    except FileNotFoundError:
        edge_geoms = {}
        
    nodes = []
    # Merge Acropolis for the frontend map as well, so it draws one giant star
    added_acro = False
    
    # Pre-compute Acropolis location if available
    acro_lat, acro_lon = None, None
    for name, coords in geo_data.items():
        if "acropolis" in name.lower() and coords.get('lat') is not None:
            acro_lat = coords['lat']
            acro_lon = coords['lon']
            break
            
    for stop_id, stop in engine.stops.items():
        if "acropolis" in stop.name.lower():
            if not added_acro and acro_lat is not None:
                nodes.append({
                    "id": "ACROPOLIS",
                    "name": "Acropolis Institutes (DESTINATION)",
                    "x": acro_lon, # Leaflet uses Lng for x
                    "y": acro_lat  # Leaflet uses Lat for y
                })
                added_acro = True
            continue
            
        coords = geo_data.get(stop.name)
        if coords and coords.get('lat') is not None:
            nodes.append({
                "id":       stop_id,
                "name":     stop.name,
                "x":        coords['lon'],
                "y":        coords['lat'],
                "route_id": stop.route_id
            })
            
    # We only include edges where BOTH nodes have valid geocoding
    valid_node_ids = {n['id'] for n in nodes}
    edges = []
    
    for route in engine.routes.values():
        for i in range(len(route.stops) - 1):
            s1 = "ACROPOLIS" if "acropolis" in route.stops[i].name.lower() else route.stops[i].stop_id
            s2 = "ACROPOLIS" if "acropolis" in route.stops[i+1].name.lower() else route.stops[i+1].stop_id
            if s1 in valid_node_ids and s2 in valid_node_ids:
                edge_id = f"{s1}|{s2}"
                if edge_geoms and edge_id not in edge_geoms:
                    # Skip branch jumps that were filtered out by fetch_geometries.py
                    continue
                geom = edge_geoms.get(edge_id)
                edges.append({"source": s1, "target": s2, "geometry": geom})
                
    return jsonify({"nodes": nodes, "edges": edges})

@app.route('/step', methods=['POST'])
def step_simulation():
    global current_tick
    
    if engine is None:
        init_engine()
        
    steps_to_take = request.json.get('steps', 1) if request.json else 1
    
    # The simulation ends when all buses have arrived (shift window closed).
    # Hard stop at SHIFT_1_ARRIVAL + 60 min grace period for last buses to reach Acropolis.
    SIM_HARD_STOP = SHIFT_1_ARRIVAL + 60  # 09:10 — all buses should have arrived by then
    
    for _ in range(steps_to_take):
        current_time_mins = SIM_START_MINS + current_tick
        if current_time_mins >= SIM_HARD_STOP:
            break
        if current_tick < TOTAL_TICKS:
            # Clear previous tick logs
            engine.reallocations_log = []
            engine.step(current_time_mins)
            current_tick += 1
            
    # Gather state
    nodes_state = []
    for stop_id, stop in engine.stops.items():
        nodes_state.append({
            "id": stop_id,
            "waiting": len(stop.waiting_passengers)
        })
        
    buses_state = []
    for bus in engine.buses.values():
        if bus.state in ["EN_ROUTE", "SCHEDULED", "ARRIVED"]:
            if bus.state == "EN_ROUTE":
                # Find the index of the stop we just left (to look up the correct travel time leg)
                prev_idx = next((i for i, s in enumerate(bus.route.stops) if s.stop_id == bus.last_stop_id), 0)
                total_time = bus.route.travel_times[prev_idx] if prev_idx < len(bus.route.travel_times) else 1
                if total_time <= 0: total_time = 1
                progress = 1.0 - (bus.time_to_next_stop / total_time)
                
                prev_stop_obj = engine.stops.get(bus.last_stop_id)
                target_stop_obj = bus.route.stops[bus.current_stop_idx]
            elif bus.state == "ARRIVED":
                # Show bus parked at Acropolis (last stop)
                progress = 1.0
                last_idx = len(bus.route.stops) - 1
                prev_stop_obj = bus.route.stops[max(0, last_idx - 1)]
                target_stop_obj = bus.route.stops[last_idx]
            else:  # SCHEDULED
                progress = 0.0
                prev_stop_obj = engine.stops.get(bus.last_stop_id) if bus.last_stop_id else bus.route.stops[bus.current_stop_idx]
                target_stop_obj = prev_stop_obj
            
            if prev_stop_obj is None: prev_stop_obj = bus.route.stops[0]
            if target_stop_obj is None: target_stop_obj = bus.route.stops[0]
            
            prev_stop_id = "ACROPOLIS" if "acropolis" in prev_stop_obj.name.lower() else prev_stop_obj.stop_id
            target_stop_id = "ACROPOLIS" if "acropolis" in target_stop_obj.name.lower() else target_stop_obj.stop_id
            
            buses_state.append({
                "id": bus.bus_id,
                "route": bus.route.route_id,
                "prev_stop": prev_stop_id,
                "target_stop": target_stop_id,
                "progress": progress,
                "occ": bus.occupancy,
                "cap": bus.capacity,
                "is_helper": bus.is_helper,
                "state": bus.state
            })
            
    current_time_mins = SIM_START_MINS + current_tick
    SIM_HARD_STOP = SHIFT_1_ARRIVAL + 60
    simulation_done = current_time_mins >= SIM_HARD_STOP
    
    # Freeze stranded count once shift is over — passengers still at stops are final
    stranded = sum(len(s.waiting_passengers) for s in engine.stops.values())
    
    return jsonify({
        "tick": current_tick,
        "time_mins": current_time_mins,
        "nodes": nodes_state,
        "buses": buses_state,
        "logs": engine.reallocations_log,
        "stranded": stranded,
        "transported": engine.total_transported,
        "done": simulation_done
    })

@app.route('/inject', methods=['POST'])
def inject():
    data = request.json
    stop_id = data.get('stop_id')
    students = data.get('students', 0)
    faculty = data.get('faculty', 0)
    
    if engine and stop_id in engine.stops:
        stop = engine.stops[stop_id]
        from simulate import Passenger
        # Instead of appending to the current count, the user requested:
        # "set/override the number of waiting students and faculty there"
        stop.waiting_passengers = []
        for _ in range(students):
            stop.waiting_passengers.append(Passenger("student", engine.total_generated))
            engine.total_generated += 1
        for _ in range(faculty):
            stop.waiting_passengers.append(Passenger("faculty", engine.total_generated))
            engine.total_generated += 1
            
        return jsonify({"status": "success", "stop": stop.name, "total_waiting": len(stop.waiting_passengers)})
    return jsonify({"error": "Stop not found"}), 404

if __name__ == '__main__':
    app.run(debug=True, port=5000)
