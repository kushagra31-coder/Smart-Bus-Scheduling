import json
stops = json.load(open('data/stops.json'))
r15 = [s for s in stops if s['route'] == 'R15']
r15.sort(key=lambda x: x['order'])
for s in r15:
    print(f"{s['stopId']}: {s['name']}")
