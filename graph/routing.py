import heapq
import json
import time
from collections import defaultdict

import geopandas as gpd
import networkx as nx
import osmnx as ox


def load():
    G = ox.load_graphml("graph/kolkata.graphml")

    fac = gpd.read_file("graph/facilities.geojson")

    # Extract facility coordinates.
    fac["lon"] = fac.geometry.x
    fac["lat"] = fac.geometry.y

    # Snap every facility to its nearest road node.
    fac["node"] = ox.nearest_nodes(
        G,
        fac["lon"].values,
        fac["lat"].values
    )

    return G, fac


def nearest_facility(G, source, targets):
    """Find the nearest reachable target using Dijkstra with early stopping."""

    targets = set(targets)

    dist = {source: 0.0}
    prev = {}
    visited = set()

    pq = [(0.0, source)]

    while pq:
        d, u = heapq.heappop(pq)

        # Ignore nodes already processed.
        if u in visited:
            continue

        visited.add(u)

        # The first target removed from the priority queue
        # has the shortest distance.
        if u in targets:
            path = [u]

            while path[-1] != source:
                path.append(prev[path[-1]])

            return u, d, path[::-1], len(visited)

        # Explore neighbouring road nodes.
        for v, edges in G[u].items():

            # Multiple road edges may connect the same nodes.
            w = min(
                float(e.get("length", 1.0))
                for e in edges.values()
            )

            nd = d + w

            if nd < dist.get(v, float("inf")):
                dist[v] = nd
                prev[v] = u

                heapq.heappush(pq, (nd, v))

    return None


def build_node_to_facilities(fac):
    """Keep every facility associated with each snapped road node."""

    node_to_facilities = defaultdict(list)

    for _, r in fac.iterrows():

        name = r.get("name")

        if name is None or not str(name).strip():
            name = r.get("amenity", "Unknown facility")

        node_to_facilities[r["node"]].append({
            "name": str(name),
            "amenity": str(r.get("amenity", "unknown")),
            "lat": float(r["lat"]),
            "lon": float(r["lon"]),
        })

    return node_to_facilities


if __name__ == "__main__":

    print("Loading road graph and facilities...")

    G, fac = load()

    # Unlike a normal dictionary, this preserves multiple facilities
    # that snap to the same road node.
    node_to_facilities = build_node_to_facilities(fac)

    targets = set(fac["node"])

    with open("data/stations.json") as f:
        stations = json.load(f)

    print(f"Road graph: {len(G.nodes)} nodes")
    print(f"Facilities: {len(fac)}")
    print(f"Unique facility road nodes: {len(targets)}")
    print()

    for s in stations[::6]:

        src = ox.nearest_nodes(
            G,
            s["lon"],
            s["lat"]
        )

        # Run our Dijkstra implementation.
        t0 = time.perf_counter()

        result = nearest_facility(G, src, targets)

        t_mine = (time.perf_counter() - t0) * 1000

        if result is None:
            print(f'{s["name"]}: No reachable facility found.')
            continue

        node, d, path, explored = result

        # Get every facility associated with the selected road node.
        facilities = node_to_facilities[node]

        # Validate against NetworkX using the same edge-weight
        # semantics as our custom implementation.
        lengths = nx.single_source_dijkstra_path_length(
            G,
            src,
            weight="length"
        )

        best = min(
            lengths[n]
            for n in targets
            if n in lengths
        )

        ok = abs(best - d) < 1e-6

        print(f'{s["name"]:22} -> {facilities[0]["name"]}')

        # Show other facilities sharing the same road node.
        if len(facilities) > 1:
            print(f"   Other facilities at this node: {len(facilities) - 1}")

            for facility in facilities[1:]:
                print(f'      - {facility["name"]}')

        print(
            f"   {d / 1000:.2f} km"
            f" | {len(path)} nodes"
            f" | explored {explored}"
            f" | {t_mine:.2f} ms"
            f" | matches NetworkX: {ok}"
        )
