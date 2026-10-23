import sys, json, time, math
import paho.mqtt.client as mqtt
import osmnx as ox
from graph.routing import load, nearest_facility
from edge.buffer import Buffer

TRAIN_ID = sys.argv[1] if len(sys.argv) > 1 else "T101"
MAX_SPEED = 200.0      # m/s; anything faster than this is a GPS glitch


def haversine(a, b):
    R = 6371000
    lat1, lon1, lat2, lon2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = (math.sin((lat2 - lat1) / 2) ** 2
         + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2)
    return 2 * R * math.asin(math.sqrt(h))


# ---------- load everything once at startup (no network needed after this) ----------
print("Loading graph...")
G, fac = load()
GR = G.reverse(copy=True)   # reversed graph: finds who can reach the station fastest

stations = json.load(open("data/stations.json"))
st_nodes = ox.nearest_nodes(G, [s["lon"] for s in stations],
                            [s["lat"] for s in stations])
for s, n in zip(stations, st_nodes):
    s["node"] = n

facilities = {}
for kind in ("hospital", "fire_station"):
    names = {}
    for _, r in fac[fac["amenity"] == kind].iterrows():
        nm = r["name"]
        names[r["node"]] = nm if isinstance(nm, str) and nm else kind
    facilities[kind] = names
print({k: len(v) for k, v in facilities.items()}, "facility nodes ready")

# ---------- MQTT with offline buffer ----------
buf = Buffer()
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)


def flush():
    for row_id, topic, payload in buf.pending():
        client.publish(topic, payload, qos=1)
        buf.delete(row_id)
        print(f"[buffer] resent queued alert #{row_id}")


def on_connect(c, userdata, flags, rc, props=None):
    print("[mqtt] connected")
    c.subscribe(f"metro/train/{TRAIN_ID}/location")
    flush()


def on_disconnect(c, userdata, flags, rc, props=None):
    print("[mqtt] DISCONNECTED, working offline")


def send(topic, payload):
    if client.is_connected():
        client.publish(topic, payload, qos=1)
        print("[mqtt] alert published")
    else:
        buf.save(topic, payload)
        print("[buffer] broker unreachable, alert saved locally")


# ---------- GPS cleaning ----------
state = {"pos": None, "last": None, "recent": []}


def on_message(c, userdata, msg):
    d = json.loads(msg.payload)
    p = (d["lat"], d["lon"])
    now = d.get("ts", time.time())
    if state["last"]:
        lp, lt = state["last"]
        dt = max(now - lt, 1e-3)
        if haversine(lp, p) / dt > MAX_SPEED:
            print("[gps] rejected jump")
            return
    state["last"] = (p, now)
    state["recent"] = (state["recent"] + [p])[-3:]       # moving average of 3
    n = len(state["recent"])
    state["pos"] = (sum(x[0] for x in state["recent"]) / n,
                    sum(x[1] for x in state["recent"]) / n)


client.on_connect = on_connect
client.on_disconnect = on_disconnect
client.on_message = on_message
client.connect_async("localhost", 1883, keepalive=5)
client.loop_start()


# ---------- emergency handling ----------
def coords(path):
    return [[G.nodes[n]["y"], G.nodes[n]["x"]] for n in path]


def trigger():
    if not state["pos"]:
        print("No GPS fix yet. Is the simulator running?")
        return
    t0 = time.perf_counter()
    pos = state["pos"]
    st = min(stations, key=lambda s: haversine(pos, (s["lat"], s["lon"])))

    alert = {"id": TRAIN_ID, "ts": time.time(),
             "train": {"lat": pos[0], "lon": pos[1]},
             "station": {"name": st["name"], "lat": st["lat"], "lon": st["lon"]}}

    for kind, names in facilities.items():
        res = nearest_facility(GR, st["node"], names.keys())
        if not res:
            continue
        node, dist, path, explored = res
        alert[kind] = {"name": names[node],
                       "dist_m": round(dist),
                       "path": coords(path[::-1]),   # facility -> station (driving direction)
                       "explored": explored}

    alert["edge_ms"] = round((time.perf_counter() - t0) * 1000, 1)
    summary = ", ".join(f"{k}={alert[k]['name']} ({alert[k]['dist_m']/1000:.2f} km)"
                        for k in facilities if k in alert)
    print(f"EMERGENCY at {st['name']}: {summary} | computed on-device in {alert['edge_ms']} ms")
    send(f"metro/train/{TRAIN_ID}/emergency", json.dumps(alert))


print(f"Edge service for {TRAIN_ID} ready. Type 'e' + Enter for an emergency, 'q' to quit.")
while True:
    try:
        cmd = input().strip().lower()
    except EOFError:
        break
    if cmd == "e":
        trigger()
    elif cmd == "q":
        break
client.loop_stop()
