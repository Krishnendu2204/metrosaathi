#Line Definition
import json, os

HERE = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(HERE, "..", "data", "stations.json")) as f:
    STATIONS = [(s["name"], s["lat"], s["lon"]) for s in json.load(f)]

#Distance Helper
import math

def haversine(a, b):
    R = 6371000  # earth radius in meters
    lat1, lon1, lat2, lon2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    dlat, dlon = lat2 - lat1, lon2 - lon1
    h = math.sin(dlat/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin(dlon/2)**2
    return 2 * R * math.asin(math.sqrt(h))

POINTS = [(lat, lon) for _, lat, lon in STATIONS]

cum = [0.0]
for i in range(1, len(POINTS)):
    cum.append(cum[-1] + haversine(POINTS[i-1], POINTS[i]))
TOTAL = cum[-1]

def position_at(d):
    d = max(0, min(d, TOTAL))
    for i in range(1, len(cum)):
        if d <= cum[i]:
            seg_len = cum[i] - cum[i-1]
            t = (d - cum[i-1]) / seg_len
            a, b = POINTS[i-1], POINTS[i]
            return a[0] + (b[0]-a[0])*t, a[1] + (b[1]-a[1])*t
    return POINTS[-1]

#Train Class
import random

class Train:
    def __init__(self, train_id, start_dist, direction=1, speed=15):
        self.id = train_id
        self.dist = start_dist
        self.dir = direction        # +1 forward, -1 backward
        self.speed = speed          # m/s (15 m/s = 54 km/h)

    def step(self, dt=1.0):
        self.dist += self.dir * self.speed * dt
        if self.dist >= TOTAL:
            self.dist, self.dir = TOTAL, -1
        elif self.dist <= 0:
            self.dist, self.dir = 0, 1

    def message(self):
        lat, lon = position_at(self.dist)
        # tiny noise to mimic real GPS
        lat += random.uniform(-0.00001, 0.00001)
        lon += random.uniform(-0.00001, 0.00001)
        return {
            "id": self.id,
            "lat": round(lat, 6),
            "lon": round(lon, 6),
            "speed_kmh": round(self.speed * 3.6, 1),
            "ts": time.time(),
        }


#Publish
import json, time
import paho.mqtt.client as mqtt

trains = [
    Train("T101", start_dist=0,           direction=1,  speed=15),
    Train("T102", start_dist=TOTAL * 0.5, direction=-1, speed=13),
    Train("T103", start_dist=TOTAL * 0.8, direction=1,  speed=16),
]

client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.connect("localhost", 1883)
client.loop_start()

print(f"Line length: {TOTAL/1000:.1f} km. Publishing... Ctrl+C to stop.")
while True:
    for t in trains:
        t.step(1.0)
        client.publish(f"metro/train/{t.id}/location", json.dumps(t.message()))
    time.sleep(1)

