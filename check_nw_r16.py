import json
geo = json.load(open('data/stops_geo.json'))
routes = json.load(open('data/routes.json'))
r16_stops = next(r['stops'] for r in routes if r['routeId'] == 'R16')
for s in r16_stops:
    c = geo.get(s['name'])
    if c and c['lat'] > 22.74 and c['lon'] < 75.85:
        print(f"{s['name']}: {c}")
