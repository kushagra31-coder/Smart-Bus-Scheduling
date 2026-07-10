import json
import math

def haversine(lat1, lon1, lat2, lon2):
    R = 6371  # km
    dLat = math.radians(lat2 - lat1)
    dLon = math.radians(lon2 - lon1)
    lat1 = math.radians(lat1)
    lat2 = math.radians(lat2)
    a = math.sin(dLat/2) * math.sin(dLat/2) + math.sin(dLon/2) * math.sin(dLon/2) * math.cos(lat1) * math.cos(lat2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c

stops = json.load(open('data/stops.json'))
geo = json.load(open('data/stops_geo.json'))
ACTIVE = {'R01','R02','R03','R05','R08','R09','R13','R15','R16','R18'}

route_stops = {r: [] for r in ACTIVE}
for s in stops:
    if s['route'] in ACTIVE:
        route_stops[s['route']].append(s)

for r, s_list in route_stops.items():
    s_list.sort(key=lambda x: x['order'])

print('--- Long Segments (>10km) ---')
outliers = set()
for r, s_list in route_stops.items():
    for i in range(len(s_list)-1):
        s1 = s_list[i]
        s2 = s_list[i+1]
        c1 = geo.get(s1['name'])
        c2 = geo.get(s2['name'])
        if c1 and c2 and c1.get('lat') is not None and c2.get('lat') is not None:
            d = haversine(c1['lat'], c1['lon'], c2['lat'], c2['lon'])
            if d > 10:
                print(f"Route {r}: {s1['name']} ({c1['lat']:.4f}, {c1['lon']:.4f}) -> {s2['name']} ({c2['lat']:.4f}, {c2['lon']:.4f}) : {d:.1f} km")
                if not (22.5 <= c1['lat'] <= 22.9 and 75.6 <= c1['lon'] <= 76.1):
                    outliers.add(s1['name'])
                if not (22.5 <= c2['lat'] <= 22.9 and 75.6 <= c2['lon'] <= 76.1):
                    outliers.add(s2['name'])

print('\n--- Stops Outside Indore Region (lat 22.5-22.9, lon 75.6-76.1) ---')
for name, c in geo.items():
    if c.get('lat') is not None:
        if not (22.5 <= c['lat'] <= 22.9 and 75.6 <= c['lon'] <= 76.1):
            print(f"{name}: ({c['lat']:.4f}, {c['lon']:.4f})")
