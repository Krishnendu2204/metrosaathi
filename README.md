# MetroSaathi

Real-time metro tracking and emergency response prototype for the Kolkata Blue Line (Line 1).

Simulated trains publish GPS positions over MQTT and appear live on a map. When a train has an emergency, an **edge service** (the program that would run on the train-side device) cleans the GPS data, finds the nearest metro station, and runs a hand-written **Dijkstra** on a locally cached OpenStreetMap road graph to find the nearest hospital and fire station. No cloud is needed for that computation. If the broker is unreachable, the alert is buffered in SQLite and resent on reconnect.

> **Scope:** this is a prototype. Trains are simulated; no real metro or GPS hardware is used yet.


Demo video: [link here](https://example.com)

## Architecture

```
TRAIN SIDE (edge)                      CONTROL ROOM
┌──────────────────────────┐           ┌───────────────────────────┐
│ GPS (simulator)          │           │ Mosquitto (MQTT broker)   │
│   ↓                      │           │        ↓                  │
│ GPS filter               │   MQTT    │ FastAPI backend           │
│   ↓                      │ ────────► │        ↓ WebSocket        │
│ Emergency trigger        │           │ Leaflet dashboard         │
│   ↓                      │           │ (trains, alerts, routes)  │
│ Dijkstra on cached graph │           └───────────────────────────┘
│   ↓                      │
│ SQLite offline buffer    │
└──────────────────────────┘
```

## Features

- **Live tracking:** 3 simulated trains move along 25 Blue Line stations (distance-based motion, reversing at the terminals) and stream positions every second.
- **Emergency routing:** custom Dijkstra with a binary heap and early stopping, run on the reversed road graph so the route follows the ambulance's driving direction (facility to station), respecting one-way streets.
- **Edge computing:** the road graph, stations and facilities are loaded locally; routing needs no network.
- **GPS filtering:** rejects impossible position jumps and smooths with a 3-point moving average.
- **Offline buffering:** alerts are stored in SQLite when the broker is down and resent on reconnect (MQTT QoS 1).
- **Reconnect handling:** backend, simulator and edge service recover after a broker restart.

## Tech stack

Python, MQTT (Mosquitto, paho-mqtt), FastAPI, WebSocket, OSMnx, NetworkX, GeoPandas, SQLite, Leaflet.js, OpenStreetMap

## Results

Measured on a laptop (not a Raspberry Pi), 50 requests each:

| Path | Mean | p95 |
|---|---|---|
| Edge (on-device) | 22.6 ms | 68.2 ms |
| Cloud, localhost (0 ms RTT) | 24.5 ms | 71.4 ms |
| Cloud + 100 ms RTT (simulated) | 124.5 ms | 171.4 ms |
| Cloud + 300 ms RTT (simulated) | 324.5 ms | 371.4 ms |

- The 100 and 300 ms rows are **modeled**: the measured localhost time plus an assumed network round trip.
- At 0 ms RTT the two paths are nearly equal, since both run the same algorithm. The edge advantage is that its time does not depend on the network, and that it **still works with no connection**.
- Road graph: 41,512 nodes, 105,545 edges. Facilities: 217 hospitals and fire stations (198 unique road nodes).
- Dijkstra explores a few hundred nodes per query instead of the whole graph, and results match NetworkX's shortest path on every tested station.

## Run it

Requires Ubuntu (or similar), Python 3.11+ and Mosquitto.

```bash
sudo apt install -y mosquitto mosquitto-clients
sudo systemctl enable --now mosquitto

git clone git@github.com:YOUR_USERNAME/metrosaathi.git
cd metrosaathi
python3 -m venv .venv && source .venv/bin/activate
pip install paho-mqtt fastapi "uvicorn[standard]" networkx osmnx geopandas scikit-learn

python graph/make_stations.py     # writes data/stations.json
python graph/build_graph.py       # downloads the road graph (a few minutes, needs internet)
python graph/routing.py           # optional: validates Dijkstra against NetworkX
```

Then, in separate terminals (venv active in each):

```bash
python simulator/train_sim.py     # fake trains publishing to MQTT
uvicorn backend.main:app --reload # backend + dashboard
python -m edge.main T101          # edge service; type 'e' + Enter for an emergency
```

Open http://localhost:8000.

**Offline demo:** `sudo systemctl stop mosquitto`, press `e` in the edge terminal (the route is still computed and the alert is buffered), then `sudo systemctl start mosquitto` and watch the alert get resent.

**Benchmark:** with uvicorn running, `python -m bench.latency`.

## Project structure

```
backend/     FastAPI app, MQTT subscriber, WebSocket, /route endpoint
bench/       edge vs cloud latency benchmark
dashboard/   Leaflet map (index.html)
data/        stations.json (Blue Line stations, in order)
edge/        edge service and SQLite offline buffer
graph/       road graph download, Dijkstra, station tools
simulator/   fake train publisher
```

## Limitations

- Trains and GPS are simulated; no real hardware yet.
- Baranagar and Noapara stations are missing, so the northern end of the line is approximate.
- OSM lists only 5 fire stations in the area, so the nearest fire station is often far away.
- Edge timings come from a laptop; a Raspberry Pi would be slower.
- Underground GPS loss (tunnels) is not modeled.
- The emergency trigger is a key press, not a real sensor.

## Next steps

- Dashboard button that triggers an emergency through MQTT
- Real GPS (NEO-6M) on a Raspberry Pi, with on-device benchmarks
- Docker Compose for one-command startup
- Add the missing stations and more fire stations
