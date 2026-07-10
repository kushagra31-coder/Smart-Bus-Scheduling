import json
geo = json.load(open('data/stops_geo.json'))
stops = json.load(open('data/stops.json'))
r15 = [s for s in stops if s['route'] == 'R15']
for s in r15[:5]:
    c = geo.get(s['name'])
    print(f"{s['name']}: {c['lat']}, {c['lon']}")
