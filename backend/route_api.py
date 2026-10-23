import json, time
import osmnx as ox
from fastapi import APIRouter, HTTPException
from graph.routing import load, nearest_facility

router = APIRouter()
_s = {}


def init():
    """Loads the graph once (the first call takes 10-30 s)."""
    if _s:
        return
    G, fac = load()
    stations = json.load(open("data/stations.json"))
    nodes = ox.nearest_nodes(G, [s["lon"] for s in stations],
                             [s["lat"] for s in stations])
    for s, n in zip(stations, nodes):
        s["node"] = n
    facilities = {}
    for kind in ("hospital", "fire_station"):
        names = {}
        for _, r in fac[fac["amenity"] == kind].iterrows():
            nm = r["name"]
            names[r["node"]] = nm if isinstance(nm, str) and nm else kind
        facilities[kind] = names
    _s.update(G=G, GR=G.reverse(copy=True), stations={s["name"]: s for s in stations},
              facilities=facilities)


def compute(station_name):
    """Same computation the edge service does for an emergency."""
    init()
    G, GR = _s["G"], _s["GR"]
    st = _s["stations"][station_name]
    out = {"station": station_name}
    for kind, names in _s["facilities"].items():
        res = nearest_facility(GR, st["node"], names.keys())
        if not res:
            continue
        node, dist, path, explored = res
        out[kind] = {"name": names[node], "dist_m": round(dist),
                     "path": [[G.nodes[n]["y"], G.nodes[n]["x"]] for n in path[::-1]],
                     "explored": explored}
    return out


@router.get("/route")
def route(station: str):
    init()
    if station not in _s["stations"]:
        raise HTTPException(404, "unknown station")
    t0 = time.perf_counter()
    out = compute(station)
    out["server_ms"] = round((time.perf_counter() - t0) * 1000, 1)
    return out
