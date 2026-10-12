import asyncio, json
import os
from contextlib import asynccontextmanager
import paho.mqtt.client as mqtt
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse

clients: set[WebSocket] = set()
latest: dict = {}          # last known position per train
loop = None

async def broadcast(data):
    for ws in list(clients):
        try:
            await ws.send_text(json.dumps(data))
        except Exception:
            clients.discard(ws)

def on_message(client, userdata, msg):
    data = json.loads(msg.payload)
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
    mq.subscribe("metro/train/+/location")
    mq.loop_start()
    yield
    mq.loop_stop()

app = FastAPI(lifespan=lifespan)
@app.get("/stations")
def stations():
    with open(os.path.join("data", "stations.json")) as f:
        return json.load(f)


@app.get("/")
def index():
    return FileResponse("dashboard/index.html")

@app.get("/trains")
def trains():
    return list(latest.values())

@app.websocket("/live")
async def live(ws: WebSocket):
    await ws.accept()
    clients.add(ws)
    for d in latest.values():          # send current state immediately
        await ws.send_text(json.dumps(d))
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        clients.discard(ws)
