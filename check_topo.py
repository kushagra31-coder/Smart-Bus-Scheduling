import json
import urllib.request
req = urllib.request.Request('http://localhost:5000/topology', headers={'User-Agent':'test'})
data = json.loads(urllib.request.urlopen(req).read())
print(f"Topology returned {len(data['nodes'])} nodes and {len(data['edges'])} edges.")
r15_edges = [e for e in data['edges'] if e['source'].startswith('R15')]
print(f"R15 edges: {len(r15_edges)}")
