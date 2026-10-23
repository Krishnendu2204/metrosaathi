import asyncio, json, os
from contextlib import asynccontextmanager
import paho.mqtt.client as mqtt
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse

clients: set[WebSocket] = set()
latest: dict = {}          # last known position per train
alerts: list = []          # emergency history
loop = None


async def broadcast(data):
    for ws in list(clients):
        try:
            await ws.send_text(json.dumps(data))
        except Exception:
            clients.discard(ws)


def on_message(client, userdata, msg):
    data = json.loads(msg.payload)
    if msg.topic.endswith("/emergency"):
        data["type"] = "emergency"
        alerts.append(data)
    else:
        data["type"] = "location"
        latest[data["id"]] = data
    # MQTT runs in its own thread, so hand the work to the asyncio loop
    asyncio.run_coroutine_threadsafe(broadcast(data), loop)


@asynccontextmanager
async def lifespan(app):
    global loop
    loop = asyncio.get_running_loop()
    mq = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    mq.on_message = on_message
    mq.connect("localhost", 1883)
    mq.subscribe([("metro/train/+/location", 0), ("metro/train/+/emergency", 1)])
    mq.loop_start()
    yield
    mq.loop_stop()


app = FastAPI(lifespan=lifespan)


@app.get("/")
def index():
    return FileResponse("dashboard/index.html")


@app.get("/stations")
def stations():
    with open(os.path.join("data", "stations.json")) as f:
        return json.load(f)


@app.get("/trains")
def trains():
    return list(latest.values())


@app.get("/alerts")
def get_alerts():
    return alerts


@app.websocket("/live")
async def live(ws: WebSocket):
    await ws.accept()
    clients.add(ws)
    for d in latest.values():           # current state immediately
        await ws.send_text(json.dumps(d))
    if alerts:                          # show the most recent alert on page load
        await ws.send_text(json.dumps(alerts[-1]))
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        clients.discard(ws)
