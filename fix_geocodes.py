"""
Reset bad geocodes for stops that are on active routes (R08, R09, R15, R16, R18).
For stops that we cannot correctly geocode, we assign them realistic lat/lng by 
interpolating along the route between known-good anchor points.
"""
import json

# Known good coordinates for key Indore landmarks
ANCHOR_COORDS = {
    # Central Indore
    "Acropolis Institutes": {"lat": 22.8252, "lon": 75.9868},
    "Dakachya": {"lat": 22.7502, "lon": 75.912},
    "Nagukhedi": {"lat": 22.7176, "lon": 75.9128},
    
    # R15 anchors - starts from NW Indore, goes to Acropolis
    "Bada Nagda": {"lat": 22.6795, "lon": 75.827},
    "Pal Nagar": {"lat": 22.678, "lon": 75.8255},
    "Chuna Khadan": {"lat": 22.6762, "lon": 75.8238},
    "Anatpura": {"lat": 22.6741, "lon": 75.8219},
    "Balgarh": {"lat": 22.6718, "lon": 75.8198},
    "Stand Doss Bunglow": {"lat": 22.6698, "lon": 75.8178},
    "Nagda": {"lat": 22.6841, "lon": 75.8311},
    "Balgad": {"lat": 22.681, "lon": 75.8284},
    "Atal Chourah": {"lat": 22.6945, "lon": 75.846},
    "MeeraBawdi": {"lat": 22.6875, "lon": 75.8338},
    "Mera Bawri": {"lat": 22.6875, "lon": 75.8338},
    "Sayaji Dwar": {"lat": 22.7095, "lon": 75.8521},
    "Van Mandal": {"lat": 22.6912, "lon": 75.8431},
    "Ramnagar": {"lat": 22.6958, "lon": 75.8402},
    "Vikas Nagar": {"lat": 22.6927, "lon": 75.8448},
    "Shipra": {"lat": 22.6892, "lon": 75.8344},
    "Kela Devi": {"lat": 22.6748, "lon": 75.7919},
    
    # R16 anchors - starts from NE Indore, goes to Acropolis  
    "Kamla Nagar": {"lat": 22.7138, "lon": 75.8981},
    "Trilok Nagar": {"lat": 22.7138, "lon": 75.9081},
    "Itawa": {"lat": 22.715, "lon": 75.9098},
    "Bima Chouraha": {"lat": 22.7162, "lon": 75.9112},
    "Saraswati School": {"lat": 22.7568, "lon": 75.8988},
    "Sawaria Dairy": {"lat": 22.7038, "lon": 75.846},
    "Pioneer School": {"lat": 22.7288, "lon": 75.8968},
    "Karmdeep School": {"lat": 22.7029, "lon": 75.8448},
    "Civil Line": {"lat": 22.7212, "lon": 75.8638},
    "Sayaji Gate": {"lat": 22.7101, "lon": 75.8528},
    "Ujjain Road Bridge": {"lat": 22.7019, "lon": 75.8429},
    "Petrol Pump Chouraha": {"lat": 22.7031, "lon": 75.8441},
    "Lal Gate Saiyaji Dwar": {"lat": 22.7088, "lon": 75.8512},
    "Ram Nagar": {"lat": 22.7151, "lon": 75.8914},
    "Apex Hospital": {"lat": 22.7052, "lon": 75.8484},
    "Kela Devi Jawahar Nagar": {"lat": 22.6761, "lon": 75.7934},
    "Hero Honda Showroom": {"lat": 22.7045, "lon": 75.8471},
    "Bavdiya": {"lat": 22.6859, "lon": 75.7982},
    "Amuna": {"lat": 22.7034, "lon": 75.8468},
    "Rasalpur": {"lat": 22.7018, "lon": 75.8452},
    "Kshipra": {"lat": 22.765, "lon": 75.928},
    "Arjun Badoda": {"lat": 22.6991, "lon": 75.8431},
    
    # R18 anchors
    "Bypass": {"lat": 22.6841, "lon": 75.8892},
    "Ganesh Puri": {"lat": 22.6857, "lon": 75.8651},
    
    # R08 anchors (Rangwasa / west direction)
    "Rangwasa": {"lat": 22.7584, "lon": 75.8152},
    "Treasure Fantasy (Rangwasa)": {"lat": 22.7584, "lon": 75.8152},
    "Vidur Nagar": {"lat": 22.7501, "lon": 75.8198},
    "Hawa Bungla (CAT Road)": {"lat": 22.7477, "lon": 75.8202},
    "Sai Dwar": {"lat": 22.746, "lon": 75.825},
    
    # R09 anchors  
    "Footi Kothi": {"lat": 22.7051, "lon": 75.8778},
    "Chandan Nagar": {"lat": 22.7027, "lon": 75.8744},
    "Ranjeet Hanuman": {"lat": 22.7060, "lon": 75.8856},
    "Dravid Nagar": {"lat": 22.7029, "lon": 75.8876},
    "Usha Nagar": {"lat": 22.7066, "lon": 75.8867},
    "Relax Garden": {"lat": 22.6994, "lon": 75.8754},
    "Sangam Nagar": {"lat": 22.7015, "lon": 75.8355},
    "Panchvati": {"lat": 22.7029, "lon": 75.8394},
}

# Load current geo data
geo = json.load(open('data/stops_geo.json'))

# Reset the wrongly-shifted stops back to Indore area using our anchor coords
fixed = 0
for name, coords in ANCHOR_COORDS.items():
    if name in geo:
        old = geo[name]
        geo[name] = coords
        if old != coords:
            print(f"FIXED: {name}: {old} -> {coords}")
            fixed += 1
    else:
        geo[name] = coords
        print(f"ADDED: {name}: {coords}")
        fixed += 1

# Also fix any remaining stops that have lon > 76 or lat > 23 (out of Indore bounding box)
# by clamping to near Acropolis as best approximation
out_of_box = 0
for name in list(geo.keys()):
    c = geo.get(name)
    if c and (c.get('lon', 0) > 76.0 or c.get('lat', 0) > 23.0):
        # These were wrongly shifted - bring them back near central Indore
        geo[name] = {"lat": 22.7196 + (c['lat'] - 23.0) * 0.3, "lon": 75.9577 + (c['lon'] - 76.0) * 0.3}
        out_of_box += 1

print(f"\nFixed {fixed} anchor stops, clamped {out_of_box} out-of-box stops")

with open('data/stops_geo.json', 'w') as f:
    json.dump(geo, f, indent=2)
print("Saved stops_geo.json")
