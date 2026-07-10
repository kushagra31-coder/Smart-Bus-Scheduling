import json
geo = json.load(open("data/stops_geo.json"))
ok = [k for k,v in geo.items() if v.get("lat")]
critical = ["Van Mandal", "Vikas Nagar", "Dewas Naka", "Khajrana Chouraha", "IT Park Chouraha"]
print("Critical junctions:")
for c in critical:
    v = geo.get(c)
    if v and v.get("lat"):
        print("  OK  %s: (%.4f, %.4f)" % (c, v["lat"], v["lon"]))
    else:
        print("  MISSING  %s" % c)
print("Total: %d/%d geocoded" % (len(ok), len(geo)))
