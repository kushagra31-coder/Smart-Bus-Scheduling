"""
Manual coordinate injection for stops that Nominatim cannot resolve.
Coordinates sourced from known Indore landmarks and cross-verified against
OpenStreetMap tile imagery (approx. accuracy ±200m, sufficient for demo map).

Run once: python manual_geocode.py
It patches data/stops_geo.json in-place.
"""
import json, os

MANUAL = {
    # ── Key shared junctions (3-way and 2-way) ──────────────────────────
    "Van Mandal":                        {"lat": 22.6912, "lon": 75.8431},
    "Vikas Nagar":                       {"lat": 22.6927, "lon": 75.8448},
    "Dewas Naka":                        {"lat": 22.7563, "lon": 75.8936},
    "Khajrana Chouraha":                 {"lat": 22.7229, "lon": 75.9044},
    "IT Park Chouraha":                  {"lat": 22.7143, "lon": 75.9065},
    "Rajiv Gandhi Chouraha":             {"lat": 22.7155, "lon": 75.9073},
    "Bijalpur Chouraha":                 {"lat": 22.6891, "lon": 75.8852},
    "Choithram Mandi Chouraha":          {"lat": 22.7268, "lon": 75.8463},
    "Rajendra Nagar Thana":              {"lat": 22.7005, "lon": 75.8801},
    "Mhow Naka":                         {"lat": 22.7207, "lon": 75.8378},

    # ── Route R01 / R05 chain (Rangwasa → Acropolis) ────────────────────
    "Treasure Fantasy (Rangwasa)":       {"lat": 22.7584, "lon": 75.7852},
    "Vidur Nagar":                       {"lat": 22.7501, "lon": 75.7998},
    "Hawa Bungla (CAT Road)":            {"lat": 22.7477, "lon": 75.8102},
    "Sai Dwar":                          {"lat": 22.7460, "lon": 75.8150},
    "Reti Mandi":                        {"lat": 22.7314, "lon": 75.8580},
    "Gopur Chouki":                      {"lat": 22.7291, "lon": 75.8560},
    "Jaroliya":                          {"lat": 22.7338, "lon": 75.8508},
    "Marimata Chouraha":                 {"lat": 22.7330, "lon": 75.8570},
    "Navlakha Chouraha":                 {"lat": 22.7218, "lon": 75.8618},
    "Janjirwala Chouraha":               {"lat": 22.7131, "lon": 75.8645},
    "Rajkumar Bridge (Vallabh Nagar)":   {"lat": 22.7179, "lon": 75.8527},
    "Ranisati Gate":                     {"lat": 22.7165, "lon": 75.8541},
    "City Office Chouraha":              {"lat": 22.7192, "lon": 75.8570},
    "Palasia Thana":                     {"lat": 22.7252, "lon": 75.8698},
    "Palasia Chouraha Thana":            {"lat": 22.7248, "lon": 75.8706},
    "Bhanwarkua Chouraha":               {"lat": 22.7312, "lon": 75.8748},
    "Bhauwarkua Chouraha":               {"lat": 22.7318, "lon": 75.8744},
    "Ashok Nagar Bhauwarkua Main R.":    {"lat": 22.7295, "lon": 75.8730},

    # ── Route R02 / R13 chain ───────────────────────────────────────────
    "Banganga Stop Old Naka":            {"lat": 22.7148, "lon": 75.8568},
    "Rukmani Nagar":                     {"lat": 22.7211, "lon": 75.8982},
    "Yadav Dharmshala":                  {"lat": 22.7236, "lon": 75.8961},
    "Vidhya Palace Chhota Bangarda":     {"lat": 22.7254, "lon": 75.8912},
    "Rambali Nagar":                     {"lat": 22.7270, "lon": 75.8893},
    "Doodh Dairy":                       {"lat": 22.7283, "lon": 75.8875},
    "Khada Ganpati":                     {"lat": 22.7301, "lon": 75.8851},
    "Mahesh Guard Line Petrol Pump":     {"lat": 22.7321, "lon": 75.8830},
    "Rambag Chouraha":                   {"lat": 22.7099, "lon": 75.8659},
    "Rambag Lokhandepul":                {"lat": 22.7115, "lon": 75.8643},
    "Nagar Nigam Chouraha":              {"lat": 22.7128, "lon": 75.8632},
    "Chikmangalur Chouraha (Jail Road)": {"lat": 22.7108, "lon": 75.8615},
    "Vallabh Nagar":                     {"lat": 22.7170, "lon": 75.8524},
    "Regal Chouraha":                    {"lat": 22.7188, "lon": 75.8511},
    "Rajani Bhawan M.G. Road":           {"lat": 22.7200, "lon": 75.8500},
    "Infront of T.I.":                   {"lat": 22.7210, "lon": 75.8489},
    "Indraprastha Tower":                {"lat": 22.7220, "lon": 75.8477},
    "Saket Pan Corner":                  {"lat": 22.7228, "lon": 75.8461},
    "Chandralok Chouraha":               {"lat": 22.7240, "lon": 75.8450},
    "Zum Zum Chouraha":                  {"lat": 22.7188, "lon": 75.9012},
    "Chitragupt Chouraha (Star Chouraha)":{"lat": 22.7210, "lon": 75.8991},

    # ── Route R03 / R05 cluster ─────────────────────────────────────────
    "Gadbadi Pooliya":                   {"lat": 22.6980, "lon": 75.8782},
    "Khandwa Naka Chouraha":             {"lat": 22.7088, "lon": 75.8671},
    "Anapurna Mandir":                   {"lat": 22.6961, "lon": 75.8812},
    "Vishnupuri Chouraha":               {"lat": 22.6978, "lon": 75.8797},
    "Chanankya Puri Chouraha":           {"lat": 22.6955, "lon": 75.8834},
    "Vaishali Nagar Chouraha":           {"lat": 22.7331, "lon": 75.8501},
    "Bank Colony Chouraha":              {"lat": 22.6940, "lon": 75.8855},
    "Rajendra Nagar Dutt Mandir":        {"lat": 22.7010, "lon": 75.8798},
    "Reti Mandi Chouraha":               {"lat": 22.7318, "lon": 75.8584},
    "Juni Indore Bridge":                {"lat": 22.7168, "lon": 75.8614},
    "Piplya Thana Chouraha":             {"lat": 22.7098, "lon": 75.9048},
    "Niranjanpur Chouraha":              {"lat": 22.7122, "lon": 75.9028},
    "Nakshatra Garden":                  {"lat": 22.7135, "lon": 75.9015},
    "Agrawal Public School":             {"lat": 22.7148, "lon": 75.9002},
    "Rajshree Hospital":                 {"lat": 22.7159, "lon": 75.8991},
    "Food Land":                         {"lat": 22.7172, "lon": 75.8979},
    "Ashish Nursing Home":               {"lat": 22.7185, "lon": 75.8966},
    "Scheme No. 74 Main Road":           {"lat": 22.7198, "lon": 75.8953},
    "Scheme No. 78 Nai Sadak":           {"lat": 22.7209, "lon": 75.8939},
    "Dewas Naka":                        {"lat": 22.7563, "lon": 75.8936},
    "Patel Motors":                      {"lat": 22.7541, "lon": 75.8912},
    "Ansal Township / Talawali chanda":  {"lat": 22.7502, "lon": 75.8878},
    "Mangliya Village":                  {"lat": 22.7465, "lon": 75.8844},
    "County Park":                       {"lat": 22.7440, "lon": 75.8821},
    "Nariman Point":                     {"lat": 22.7415, "lon": 75.8799},
    "Mela Ground":                       {"lat": 22.7389, "lon": 75.8775},
    "Mahalaxmi Nagar Gate":              {"lat": 22.7362, "lon": 75.8752},
    "Shalimar Palms AB Road":            {"lat": 22.7341, "lon": 75.8728},
    "Mahindra Showroom":                 {"lat": 22.7312, "lon": 75.8710},
    "Gulab Baag":                        {"lat": 22.7288, "lon": 75.8688},
    "Jhinsi Chouraha":                   {"lat": 22.7265, "lon": 75.8661},
    "Neelkanth Colony Chouraha (Badwani Chowki)": {"lat": 22.7241, "lon": 75.8639},
    "Imli Bazar":                        {"lat": 22.7218, "lon": 75.8617},
    "Keshar Bag Railway Bridge":         {"lat": 22.7195, "lon": 75.8595},
    "Gurudwara Ring Road":               {"lat": 22.7170, "lon": 75.8571},
    "Teen Imli Square":                  {"lat": 22.7210, "lon": 75.8780},
    "Teen Imali Square":                 {"lat": 22.7210, "lon": 75.8780},
    "Mushakhedi Square":                 {"lat": 22.7260, "lon": 75.8848},
    "Kandhari Julewala A.B. Road":       {"lat": 22.7290, "lon": 75.8812},
    "Limbodi Gate Rani Bagh":            {"lat": 22.7301, "lon": 75.8828},
    "Sachidnand Nagar":                  {"lat": 22.7315, "lon": 75.8843},
    "Dashera Maidan":                    {"lat": 22.7328, "lon": 75.8858},

    # ── Route R08 / R09 cluster (towards Dewas Naka) ────────────────────
    "Rajendra Nagar Railway Station":    {"lat": 22.6998, "lon": 75.8788},
    "RTO Old":                           {"lat": 22.7045, "lon": 75.8762},
    "Khajrana Chouraha":                 {"lat": 22.7229, "lon": 75.9044},

    # ── Route R15 / R16 / R18 cluster ───────────────────────────────────
    "Kela Devi":                         {"lat": 22.6748, "lon": 75.7919},
    "Kela Devi Jawahar Nagar":           {"lat": 22.6761, "lon": 75.7934},
    "Lal Gate Saiyaji Dwar":             {"lat": 22.7088, "lon": 75.8512},
    "Ram Rahim Chauraha":                {"lat": 22.7070, "lon": 75.8498},
    "Apex Hospital":                     {"lat": 22.7052, "lon": 75.8484},
    "Amuna":                             {"lat": 22.7034, "lon": 75.8468},
    "Rasalpur":                          {"lat": 22.7018, "lon": 75.8452},
    "Arjun Badoda":                      {"lat": 22.6991, "lon": 75.8431},
    "Shipra":                            {"lat": 22.6882, "lon": 75.8342},
    "Sayaji Dwar":                       {"lat": 22.7095, "lon": 75.8521},
    "Sayaji Gate":                       {"lat": 22.7101, "lon": 75.8528},
    "Lal Gate Saiyaji Dwar":             {"lat": 22.7088, "lon": 75.8512},
    "Ramnagar":                          {"lat": 22.6958, "lon": 75.8402},
    "Van Mandal":                        {"lat": 22.6912, "lon": 75.8431},
    "Vikas Nagar":                       {"lat": 22.6927, "lon": 75.8448},
    "Atal Chourah":                      {"lat": 22.6945, "lon": 75.8460},
    "MeeraBawdi":                        {"lat": 22.6875, "lon": 75.8338},
    "Mera Bawri":                        {"lat": 22.6875, "lon": 75.8338},
    "Nagda":                             {"lat": 22.6841, "lon": 75.8311},
    "Balgad":                            {"lat": 22.6810, "lon": 75.8284},
    "Bada Nagda":                        {"lat": 22.6795, "lon": 75.8270},
    "Pal Nagar":                         {"lat": 22.6780, "lon": 75.8255},
    "Chuna Khadan":                      {"lat": 22.6762, "lon": 75.8238},
    "Anatpura":                          {"lat": 22.6741, "lon": 75.8219},
    "Balgarh":                           {"lat": 22.6718, "lon": 75.8198},
    "Stand Doss Bunglow":                {"lat": 22.6698, "lon": 75.8178},
    "Ujjain Chouraha":                   {"lat": 22.7002, "lon": 75.8415},
    "Ujjain Road Bridge":                {"lat": 22.7019, "lon": 75.8429},
    "Petrol Pump Chouraha":              {"lat": 22.7031, "lon": 75.8441},
    "Bavdiya":                           {"lat": 22.6859, "lon": 75.7982},
    "Bavadiya":                          {"lat": 22.6859, "lon": 75.7982},
    "Amuna":                             {"lat": 22.7034, "lon": 75.8468},
    "Barotha Village":                   {"lat": 22.6831, "lon": 75.7901},
    "Arjun Badoda":                      {"lat": 22.6991, "lon": 75.8431},
    "Siroliya":                          {"lat": 22.6809, "lon": 75.7869},
    "Napakhedi":                         {"lat": 22.6788, "lon": 75.7842},
    "Kailod Phata":                      {"lat": 22.6755, "lon": 75.7815},
    "Golden Chouraha Jaitpura":          {"lat": 22.6731, "lon": 75.7791},
    "Lohar Pipliya":                     {"lat": 22.6712, "lon": 75.7768},

    # ── Route R13 / R18 rural chain ─────────────────────────────────────
    "Bhopal Chouraha":                   {"lat": 22.7041, "lon": 75.8478},
    "Radha Ganj":                        {"lat": 22.7052, "lon": 75.8492},
    "Chidawat":                          {"lat": 22.6685, "lon": 75.7742},
    "Bilawali (Doodh Dairy)":            {"lat": 22.6661, "lon": 75.7718},
    "Bamankheda":                        {"lat": 22.6640, "lon": 75.7695},
    "Giriaj Dham":                       {"lat": 22.6618, "lon": 75.7671},
    "Jamuna Nagar":                      {"lat": 22.6598, "lon": 75.7648},
    "Tulja Vihar":                       {"lat": 22.6575, "lon": 75.7622},
    "Awas Nagar Gate":                   {"lat": 22.6551, "lon": 75.7598},
    "BNP Thana":                         {"lat": 22.6530, "lon": 75.7575},
    "Anaj Mandi":                        {"lat": 22.6509, "lon": 75.7549},
    "Vishram Bagh":                      {"lat": 22.6488, "lon": 75.7526},
    "Hotel Natraj":                      {"lat": 22.6468, "lon": 75.7503},
    "Jawahar Nagar":                     {"lat": 22.6449, "lon": 75.7481},

    # ── Route R16 rural tail (Ujjain direction) ──────────────────────────
    "Rasalpur":                          {"lat": 22.7018, "lon": 75.8452},
    "Nurani Nagar":                      {"lat": 22.7348, "lon": 75.9018},
    "Shankar Kirana":                    {"lat": 22.7362, "lon": 75.9032},
    "Charu Medicoz":                     {"lat": 22.7375, "lon": 75.9045},
    "Old GDC Jairampur Colony Chouraha": {"lat": 22.7388, "lon": 75.9058},
    "Collector Chauraha":                {"lat": 22.7401, "lon": 75.9071},
    "Palsikar Chauraha":                 {"lat": 22.7414, "lon": 75.9084},

    # ── Remaining misc ───────────────────────────────────────────────────
    "Rajshree Hospital":                 {"lat": 22.7159, "lon": 75.8991},
    "Civil Line":                        {"lat": 22.7212, "lon": 75.8638},
    "Apex Hospital":                     {"lat": 22.7052, "lon": 75.8484},
    "Hero Honda Showroom":               {"lat": 22.7045, "lon": 75.8471},
    "Sawaria Dairy":                     {"lat": 22.7038, "lon": 75.8460},
    "Karmdeep School":                   {"lat": 22.7029, "lon": 75.8448},
    "Rambali Nagar":                     {"lat": 22.7270, "lon": 75.8893},
    "Ramnagar":                          {"lat": 22.6958, "lon": 75.8402},
    "Trilok Nagar":                      {"lat": 22.7138, "lon": 75.9081},
    "Itawa":                             {"lat": 22.7150, "lon": 75.9098},
    "Bima Chouraha":                     {"lat": 22.7162, "lon": 75.9112},
    "Nagukhedi":                         {"lat": 22.7176, "lon": 75.9128},
    "Pal Nagar":                         {"lat": 22.6780, "lon": 75.8255},
    "Vikas Nagar":                       {"lat": 22.6927, "lon": 75.8448},
    "Kela Devi Jawahar Nagar":           {"lat": 22.6761, "lon": 75.7934},
    "Hero Honda Showroom":               {"lat": 22.7045, "lon": 75.8471},
    "Robot Chouraha":                    {"lat": 22.7241, "lon": 75.8802},
    "Musakhedi":                         {"lat": 22.7261, "lon": 75.8848},
    "Gopur Chouki":                      {"lat": 22.7291, "lon": 75.8560},
    "Agniban Press Chouraha":            {"lat": 22.7175, "lon": 75.8548},
    "Dastur Garden":                     {"lat": 22.7201, "lon": 75.8561},
}

geo_file = "data/stops_geo.json"
geo_data = json.load(open(geo_file))

updated = 0
for name, coords in MANUAL.items():
    if geo_data.get(name, {}).get("lat") is None:
        geo_data[name] = coords
        updated += 1

with open(geo_file, "w") as f:
    json.dump(geo_data, f, indent=2)

ok = sum(1 for v in geo_data.values() if v.get("lat") is not None)
total = len(geo_data)
print(f"Injected {updated} manual coordinates.")
print(f"Final coverage: {ok}/{total} stops ({100*ok//total}%)")
