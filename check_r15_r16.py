import json
import app
app.init_engine()
geo = json.load(open('data/stops_geo.json'))
for rid in ['R15', 'R16']:
    print(f'ROUTE {rid}:')
    for s in app.engine.routes[rid].stops:
        coords = geo.get(s.name)
        if coords:
            print(f'  {s.stop_id}: {s.name} -> {coords["lat"]}, {coords["lon"]}')
