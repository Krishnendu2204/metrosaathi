import osmnx as ox

stations = ox.features_from_place("Kolkata, West Bengal, India", {"station": "subway"})
stations = stations[stations.geometry.geom_type == "Point"].copy()
stations = stations[stations["name"].notna()]
stations["lon"] = stations.geometry.x
stations["lat"] = stations.geometry.y

for _, row in stations.sort_values("name").iterrows():
    print(f'{row["name"]:30} lat={row["lat"]:.6f}, lon={row["lon"]:.6f}')
