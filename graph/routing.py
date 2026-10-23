import heapq, json, time
import geopandas as gpd
import networkx as nx
import osmnx as ox


def load():
    """Returns (G, fac). fac has columns: name, amenity, geometry, lon, lat, node."""
    G = ox.load_graphml("graph/kolkata.graphml")
    fac = gpd.read_file("graph/facilities.geojson")
    fac["lon"], fac["lat"] = fac.geometry.x, fac.geometry.y
    fac["node"] = ox.nearest_nodes(G, fac["lon"].values, fac["lat"].values)
    return G, fac


def nearest_facility(G, source, targets):
    """Dijkstra with early stop: the first facility node popped is the nearest.
    Returns (node, distance_m, path, explored_count) or None."""
    targets = set(targets)
    dist = {source: 0.0}
    prev = {}
    visited = set()
    pq = [(0.0, source)]
    while pq:
        d, u = heapq.heappop(pq)
        if u in visited:
            continue
        visited.add(u)
        if u in targets:
            path = [u]
            while path[-1] != source:
                path.append(prev[path[-1]])
            return u, d, path[::-1], len(visited)
        for v, edges in G[u].items():
            w = min(e.get("length", 1.0) for e in edges.values())
            nd = d + w
            if nd < dist.get(v, float("inf")):
                dist[v] = nd
                prev[v] = u
                heapq.heappush(pq, (nd, v))
    return None


if __name__ == "__main__":
    print("Loading road graph and facilities...")
    G, fac = load()
    print("Road graph:", len(G.nodes), "nodes")
    print("Facilities:", len(fac))
    print("Unique facility road nodes:", fac["node"].nunique())
    print()

    node_to_name = {r.node: (r["name"] or r["amenity"]) for _, r in fac.iterrows()}
    stations = json.load(open("data/stations.json"))

    for s in stations[::6]:
        src = ox.nearest_nodes(G, s["lon"], s["lat"])
        t0 = time.perf_counter()
        node, d, path, explored = nearest_facility(G, src, fac["node"])
        t_mine = (time.perf_counter() - t0) * 1000

        lengths = nx.single_source_dijkstra_path_length(G, src, weight="length")
        best = min(lengths[n] for n in set(fac["node"]) if n in lengths)
        ok = abs(best - d) < 1e-6
        print(f'{s["name"]:22} -> {node_to_name[node]}')
        print(f'   {d/1000:.2f} km | {len(path)} nodes | explored {explored} '
              f'| {t_mine:.1f} ms | matches NetworkX: {ok}')
