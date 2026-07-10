import json
stops = json.load(open('data/stops.json'))
routes = {'R15', 'R16', 'R18', 'R08', 'R09'}
active_stops = [s for s in stops if s['route'] in routes]
from collections import defaultdict
route_stops = defaultdict(list)
for s in active_stops:
    route_stops[s['route']].append(s)

geo = json.load(open('data/stops_geo.json'))

for r, s_list in route_stops.items():
    s_list.sort(key=lambda x: x['order'])
    start = s_list[0]
    end = s_list[-1]
    c_start = geo.get(start['name'])
    c_end = geo.get(end['name'])
    print(f'Route {r} START: {start["name"]} ({c_start["lat"]}, {c_start["lon"]})')
    print(f'Route {r} END: {end["name"]} ({c_end["lat"]}, {c_end["lon"]})')
