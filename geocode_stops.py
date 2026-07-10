"""
Improved geocoder: tries multiple search strategies per stop name.
  1. "{name}, Indore, Madhya Pradesh, India"
  2. "{name}, Indore"
  3. Falls back to a bounding-box biased search
Stops that still fail are logged explicitly and excluded.
"""
import json, time, urllib.request, urllib.parse, os, sys

INDORE_BBOX = "75.6,22.5,76.1,22.9"  # minLon,minLat,maxLon,maxLat

def nominatim(query, viewbox=None):
    params = {
        "format": "json",
        "q": query,
        "limit": "3",
        "countrycodes": "in",
    }
    if viewbox:
        params["viewbox"] = viewbox
        params["bounded"] = "1"
    url = "https://nominatim.openstreetmap.org/search?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "DAA_BusSim/3.0 (student-project)"})
    try:
        with urllib.request.urlopen(req, timeout=8) as r:
            data = json.loads(r.read())
            # Prefer results inside Indore bounding box
            for item in data:
                lat, lon = float(item["lat"]), float(item["lon"])
                if 22.5 <= lat <= 22.9 and 75.6 <= lon <= 76.1:
                    return lat, lon
            # Accept any result if nothing in bbox
            if data:
                return float(data[0]["lat"]), float(data[0]["lon"])
    except Exception:
        pass
    return None, None

def geocode_stop(name):
    strategies = [
        f"{name}, Indore, Madhya Pradesh, India",
        f"{name}, Indore",
        name,
    ]
    for query in strategies:
        lat, lon = nominatim(query, viewbox=INDORE_BBOX)
        if lat:
            return lat, lon
        time.sleep(0.5)
    return None, None

def main():
    stops_data = json.load(open("data/stops.json"))
    ACTIVE = {"R01","R02","R03","R05","R08","R09","R13","R15","R16","R18"}
    geo_file = "data/stops_geo.json"
    geo_data = json.load(open(geo_file)) if os.path.exists(geo_file) else {}

    # Only re-query FAILED stops
    active_names = {s["name"] for s in stops_data if s["route"] in ACTIVE}
    to_retry = [n for n in active_names if geo_data.get(n, {}).get("lat") is None]
    
    print(f"Re-querying {len(to_retry)} previously-failed stops with enhanced strategy...")
    newly_ok = 0
    for i, name in enumerate(sorted(to_retry), 1):
        sys.stdout.write(f"\r[{i}/{len(to_retry)}] {name[:55]:<55} ")
        sys.stdout.flush()
        lat, lon = geocode_stop(name)
        time.sleep(1)  # Rate-limit
        if lat:
            geo_data[name] = {"lat": lat, "lon": lon}
            newly_ok += 1
            sys.stdout.write("OK\n")
        else:
            geo_data[name] = {"lat": None, "lon": None}
            sys.stdout.write("FAILED\n")
        sys.stdout.flush()

    with open(geo_file, "w") as f:
        json.dump(geo_data, f, indent=2)

    ok_total = sum(1 for v in geo_data.values() if v.get("lat") is not None)
    fail_total = sum(1 for v in geo_data.values() if v.get("lat") is None)
    print(f"\nDone. Newly resolved: {newly_ok}. Total OK: {ok_total}/{ok_total+fail_total} ({100*ok_total//(ok_total+fail_total)}%)")

    if fail_total:
        print("\n--- STILL FAILED (explicit list) ---")
        for n, v in sorted(geo_data.items()):
            if v.get("lat") is None:
                print(f"  EXCLUDED: {n}")

if __name__ == "__main__":
    main()
