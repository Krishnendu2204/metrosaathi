import json, time, statistics, urllib.parse, urllib.request
from backend.route_api import compute, init

RUNS = 50
RTTS_MS = [0, 100, 300]     # simulated network round trips (modeled, not measured)
URL = "http://localhost:8000/route?station="

names = [s["name"] for s in json.load(open("data/stations.json"))]
queries = [names[i % len(names)] for i in range(RUNS)]


def p95(xs):
    return sorted(xs)[int(0.95 * (len(xs) - 1))]


print("Loading graph for the edge side...")
init()
compute(queries[0])                                   # warm-up

edge = []
for q in queries:
    t0 = time.perf_counter()
    compute(q)
    edge.append((time.perf_counter() - t0) * 1000)

print("Warming up backend (first call loads the graph, may take 30 s)...")
urllib.request.urlopen(URL + urllib.parse.quote(queries[0]), timeout=120).read()

cloud = []
for q in queries:
    t0 = time.perf_counter()
    urllib.request.urlopen(URL + urllib.parse.quote(q), timeout=30).read()
    cloud.append((time.perf_counter() - t0) * 1000)

print(f"\n{RUNS} requests each\n")
print(f"{'path':34} {'mean ms':>9} {'p95 ms':>9}")
print(f"{'EDGE (on-device)':34} {statistics.mean(edge):9.1f} {p95(edge):9.1f}")
for rtt in RTTS_MS:
    c = [x + rtt for x in cloud]
    print(f"{f'CLOUD (localhost + {rtt} ms RTT)':34} {statistics.mean(c):9.1f} {p95(c):9.1f}")
print("\nNetwork down: edge still works; cloud fails.")
