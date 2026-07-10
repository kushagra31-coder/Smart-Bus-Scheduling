import json
import pdfplumber
import re
from datetime import datetime

def parse_time(t_str):
    if not t_str or not isinstance(t_str, str): return None
    t_str = t_str.strip().replace('\n', '')
    if not re.match(r'^\d{1,2}:\d{2}$', t_str): return None
    if t_str == "0:00": return None
    try:
        return datetime.strptime(t_str, "%H:%M")
    except ValueError:
        return None

def main():
    pdf_path = "1783518086512_BusRoute_Aug'24 - Updated.pdf"
    
    with open('data/routes.json', 'r') as f:
        routes = json.load(f)
        
    with open('data/stops.json', 'r') as f:
        stops = json.load(f)

    # Group stops by route
    route_stops = {}
    for stop in stops:
        rid = stop['route']
        if rid not in route_stops:
            route_stops[rid] = []
        route_stops[rid].append(stop)
        
    # Sort stops by order
    for rid in route_stops:
        route_stops[rid].sort(key=lambda x: x['order'])

    inter_stop_times = {}

    with pdfplumber.open(pdf_path) as pdf:
        for page_idx, page in enumerate(pdf.pages):
            tables = page.extract_tables()
            if not tables: continue
            table = tables[0]
            
            # Extract stop names and times
            # Col 0: SN, Col 1: Stop Name, Col 2+: Times
            pdf_stops = []
            for row in table[1:]: # skip header
                if len(row) >= 2 and row[0] and row[0].strip().isdigit():
                    stop_name = row[1].replace('\n', ' ').strip()
                    times = [parse_time(c) for c in row[2:]]
                    pdf_stops.append({
                        'name': stop_name,
                        'times': times
                    })
            
            if not pdf_stops: continue
            
            # Find which route this matches by comparing the first few stops
            best_route_id = None
            best_match_count = 0
            for rid, r_stops in route_stops.items():
                match_count = sum(1 for p, r in zip(pdf_stops, r_stops) 
                                  if p['name'][:5].lower() in r['name'].lower() 
                                  or r['name'][:5].lower() in p['name'].lower())
                if match_count > best_match_count:
                    best_match_count = match_count
                    best_route_id = rid
                    
            if not best_route_id:
                print(f"Could not match page {page_idx+1} to a route")
                continue
                
            print(f"Page {page_idx+1} matched to Route {best_route_id}")
            
            r_stops = route_stops[best_route_id]
            num_stops = len(r_stops)
            deltas = [3] * (num_stops - 1) # Default 3 mins
            
            pdf_to_route_idx = {}
            for i, p_stop in enumerate(pdf_stops):
                for j, r_stop in enumerate(r_stops):
                    # basic string matching
                    if p_stop['name'][:10].lower() in r_stop['name'].lower() or r_stop['name'][:10].lower() in p_stop['name'].lower():
                        pdf_to_route_idx[i] = j
                        break
            
            # Calculate deltas
            for i in range(len(pdf_stops) - 1):
                p_idx_1 = i
                p_idx_2 = i + 1
                
                r_idx_1 = pdf_to_route_idx.get(p_idx_1)
                r_idx_2 = pdf_to_route_idx.get(p_idx_2)
                
                if r_idx_1 is not None and r_idx_2 is not None and r_idx_2 == r_idx_1 + 1:
                    times_1 = pdf_stops[p_idx_1]['times']
                    times_2 = pdf_stops[p_idx_2]['times']
                    
                    found_delta = False
                    for t1, t2 in zip(times_1, times_2):
                        if t1 and t2 and t2 > t1:
                            delta_mins = int((t2 - t1).total_seconds() / 60)
                            if 0 < delta_mins <= 30: # sanity check
                                deltas[r_idx_1] = delta_mins
                                found_delta = True
                                break
                    
            inter_stop_times[best_route_id] = deltas
            
    # Save the travel times
    with open('data/travel_times.json', 'w') as f:
        json.dump(inter_stop_times, f, indent=2)
        
    print("Saved travel times to data/travel_times.json")

if __name__ == "__main__":
    main()
