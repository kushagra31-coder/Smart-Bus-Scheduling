import json
import app
app.init_engine()
with app.app.test_client() as client:
    resp = client.get('/topology')
    data = resp.json
    print(f"nodes: {len(data['nodes'])}")
    print(f"edges: {len(data['edges'])}")
    for e in data['edges']:
        if 'R16-S01' in e['source']:
            print(f"Found edge: {e}")
