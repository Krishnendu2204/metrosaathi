import json, os

# Order = order along the Blue Line, north to south. Don't shuffle.
C = {
    "Dakshineswar": (22.6551, 88.3578),      # approximate, verify on Google Maps
    "Baranagar": None,
    "Noapara": None,                          # add after verifying
    "Dum Dum": (22.621114, 88.392897),
    "Belgachia": (22.605924, 88.386391),
    "Shyambazar": (22.601335, 88.372497),
    "Shobhabazar Sutanuti": (22.595881, 88.365200),
    "Girish Park": (22.587145, 88.362942),
    "Mahatma Gandhi Road": (22.580921, 88.361327),
    "Central": (22.572486, 88.358743),
    "Chandni Chowk": (22.567012, 88.354158),
    "Esplanade": (22.563614, 88.351210),
    "Park Street": (22.555159, 88.350117),
    "Maidan": (22.549467, 88.348788),
    "Rabindra Sadan": (22.541490, 88.347349),
    "Netaji Bhavan": (22.533182, 88.345927),
    "Jatin Das Park": (22.524154, 88.346473),
    "Kalighat": (22.516875, 88.345845),
    "Rabindra Sarobar": (22.507222, 88.345494),
    "Mahanayak Uttam Kumar": (22.494769, 88.345088),
    "Netaji": (22.480993, 88.346000),
    "Masterda Surya Sen": (22.473586, 88.360673),
    "Gitanjali": (22.469467, 88.370012),
    "Kavi Nazrul": (22.464250, 88.380460),
    "Shahid Khudiram": (22.465971, 88.391636),
    "Kavi Subhash": (22.472170, 88.397961),
}

os.makedirs("data", exist_ok=True)
stations = [{"name": n, "lat": c[0], "lon": c[1]} for n, c in C.items() if c]
with open("data/stations.json", "w") as f:
    json.dump(stations, f, indent=2)
print(len(stations), "stations saved")
