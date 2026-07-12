import json
import time
import urllib.request
import urllib.error
import math
import os

# Calculate distance between two lat/lon points in km
def calc_dist(lat1, lon1, lat2, lon2):
    R = 6371
    dlat = math.radians(lat2-lat1)
    dlon = math.radians(lon2-lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1))*math.cos(math.radians(lat2))*math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c

def round_coords(geom, precision=5):
    return [[round(pt[0], precision), round(pt[1], precision)] for pt in geom]

def fetch_all():
    print("Loading data...")
    stops = json.load(open('data/stops.json'))
    geo = json.load(open('data/stops_geo.json'))
    
    ACTIVE_ROUTES = {"R15", "R16", "R18", "R08", "R09"}
    
    route_stops = {r: [] for r in ACTIVE_ROUTES}
    for s in stops:
        if s['route'] in ACTIVE_ROUTES:
            route_stops[s['route']].append(s)
            
    for r in route_stops:
        route_stops[r].sort(key=lambda x: x['order'])
        
    edges = set()
    for r, r_stops in route_stops.items():
        for i in range(len(r_stops)-1):
            s1_name = r_stops[i]['name']
            s2_name = r_stops[i+1]['name']
            
            if s1_name in geo and s2_name in geo:
                c1, c2 = geo[s1_name], geo[s2_name]
                if 'lat' not in c1 or 'lat' not in c2:
                    continue
                    
                d = calc_dist(c1['lat'], c1['lon'], c2['lat'], c2['lon'])
                
                # Retain every scheduled leg.  Some route records include distant
                # branch transitions; those still need a road geometry so a bus is
                # never rendered as a direct, off-road line on the dashboard.
                    
                s1_id = r_stops[i]['stopId']
                s2_id = r_stops[i+1]['stopId']
                edges.add((s1_id, c1['lat'], c1['lon'], s2_id, c2['lat'], c2['lon']))
                
        # Connect last stop to Acropolis (if not already Acropolis)
        last_stop = r_stops[-1]
        if "acropolis" not in last_stop['name'].lower():
            if last_stop['name'] in geo and "Acropolis Institutes" in geo:
                c1 = geo[last_stop['name']]
                c2 = geo["Acropolis Institutes"]
                edges.add((last_stop['stopId'], c1['lat'], c1['lon'], "ACROPOLIS", c2['lat'], c2['lon']))

    print(f"Found {len(edges)} valid edges to route.")
    
    try:
        with open('data/edge_geometries.json', 'r') as f:
            geometries = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        geometries = {}
    
    for i, (s1_id, lat1, lon1, s2_id, lat2, lon2) in enumerate(edges):
        edge_key = f"{s1_id}|{s2_id}"
        if edge_key in geometries:
            print(f"[{i+1}/{len(edges)}] Keeping existing road route for {edge_key}.")
            continue
        print(f"[{i+1}/{len(edges)}] Fetching route for {edge_key}...")
        
        # OSRM expects longitude,latitude
        url = f"http://router.project-osrm.org/route/v1/driving/{lon1},{lat1};{lon2},{lat2}?overview=full&geometries=geojson"
        
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'AcropolisTransitMap/1.0'})
            with urllib.request.urlopen(req, timeout=10) as response:
                if response.status == 200:
                    data = json.loads(response.read().decode('utf-8'))
                    if data['code'] == 'Ok':
                        geom = [[pt[1], pt[0]] for pt in data['routes'][0]['geometry']['coordinates']]
                        geometries[edge_key] = round_coords(geom, 5)
                    else:
                        print(f"  OSRM Warning for {edge_key}: {data['code']}. No geometry was saved.")
                else:
                    print(f"  OSRM Error {response.status} for {edge_key}. No geometry was saved.")
        except urllib.error.URLError as e:
            print(f"  Request failed for {edge_key}: {e}. No geometry was saved.")
        except Exception as e:
            print(f"  Request failed for {edge_key}: {e}. No geometry was saved.")
            
        time.sleep(1.5) # Be nice to OSRM public server
        
    with open('data/edge_geometries.json', 'w') as f:
        json.dump(geometries, f)
    print("Done! Saved to data/edge_geometries.json")

if __name__ == "__main__":
    fetch_all()
