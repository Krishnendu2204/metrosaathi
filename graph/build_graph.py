import os
import osmnx as ox

PLACE = "Kolkata, West Bengal, India"
os.makedirs("graph", exist_ok=True)

print("Downloading road network (a few minutes)...")
G = ox.graph_from_place(PLACE, network_type="drive")
ox.save_graphml(G, "graph/kolkata.graphml")
print(len(G.nodes), "nodes,", len(G.edges), "edges")

print("Downloading hospitals and fire stations...")
tags = {"amenity": ["hospital", "fire_station"]}
fac = ox.features_from_place(PLACE, tags)
fac = fac[["name", "amenity", "geometry"]].copy()
fac["geometry"] = fac.geometry.centroid      # polygons -> single point
fac.to_file("graph/facilities.geojson", driver="GeoJSON")
print(len(fac), "facilities saved")
