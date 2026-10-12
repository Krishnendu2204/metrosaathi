import osmnx as ox

NAMES = ["Dakshineswar", "Baranagar", "Noapara",
         "Masterda Surya Sen", "Gitanjali", "Kavi Nazrul", "Shahid Khudiram"]

for n in NAMES:
    found = False
    for q in (f"{n} metro station, Kolkata",
              f"{n} metro, Kolkata, West Bengal, India",
              f"{n} station, Kolkata"):
        try:
            lat, lon = ox.geocode(q)
        except Exception:
            continue
        print(f"{n:22} lat={lat:.6f}, lon={lon:.6f}   <- query: {q}")
        found = True
        break
    if not found:
        print(f"{n:22} NOT FOUND (use Google Maps)")
