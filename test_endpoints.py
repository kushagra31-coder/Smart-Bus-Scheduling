import time, json, urllib.request
time.sleep(2)
resp = urllib.request.urlopen('http://localhost:5000/')
print(f"GET / -> {resp.status}")
resp2 = urllib.request.urlopen('http://localhost:5000/explain')
print(f"GET /explain -> {resp2.status}")
resp3 = urllib.request.urlopen('http://localhost:5000/topology')
d = json.loads(resp3.read())
print(f"GET /topology -> {len(d['nodes'])} nodes, {len(d['edges'])} edges")
