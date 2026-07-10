import json
import app
app.init_engine()
buses = app.engine.buses
print(f"Total buses instantiated: {len(buses)}")
for b_id, b in buses.items():
    print(f"Bus {b_id} on route {b.route.route_id}")
