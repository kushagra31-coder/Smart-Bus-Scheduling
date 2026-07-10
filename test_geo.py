import urllib.request
import json

def geocode(name):
    query = f"{name}, Indore, India".replace(' ', '+')
    url = f"https://nominatim.openstreetmap.org/search?format=json&q={query}"
    req = urllib.request.Request(url, headers={'User-Agent': 'DAA_Bus_Sim/1.0 (test@test.com)'})
    try:
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())
            if data:
                return data[0]['lat'], data[0]['lon']
    except Exception as e:
        print(e)
    return None, None

print("Testing geocode for 'Treasure Fantasy':", geocode("Treasure Fantasy"))
print("Testing geocode for 'Hawa Bungla':", geocode("Hawa Bungla"))

print("Testing geocode for 'Treasure Fantasy':", geocode("Treasure Fantasy"))
print("Testing geocode for 'Hawa Bungla':", geocode("Hawa Bungla"))
