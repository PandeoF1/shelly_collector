#!/usr/bin/env /usr/bin/python3

from fastapi import FastAPI, WebSocket
import os, time
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS
import uvicorn
from dotenv import load_dotenv
import logging

load_dotenv()

WRITE_CLIENT = InfluxDBClient(
    url=os.environ["INFLUXDB_URL"],
    token=os.environ["INFLUXDB_TOKEN"],
    org=os.environ["INFLUXDB_ORG"],
)

WRITE_API = WRITE_CLIENT.write_api(write_options=SYNCHRONOUS)

app = FastAPI()
log = logging.getLogger(__name__)
log.setLevel(logging.INFO)

@app.get("/")
async def get():
    return "Hello World"

@app.websocket("/")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        component = {"name": ""}
        while True:
            data = await websocket.receive_json()
            log.info(data)
            if data["method"] == "NotifyFullStatus":
                if "wifi" in data["params"]:
                    component["name"] = data["params"]["wifi"]["sta_ip"]
                    log.info("%s: Connected" % component["name"])
            if data["method"] == "NotifyStatus":
                if "switch:0" in data["params"]:
                    if "apower" in data["params"]["switch:0"]:
                        log.info("%s: %s"% (component["name"], data["params"]["switch:0"]["apower"]))
                        point = (
                            Point("switch")
                            .field("apower", data["params"]["switch:0"]["apower"])
                            .tag("name", component["name"])
                            .time(time.time_ns(), WritePrecision.NS)
                        )
                        WRITE_API.write(
                            bucket=os.environ["INFLUXDB_BUCKET"],
                            org=os.environ["INFLUXDB_ORG"],
                            record=point,
                        )
    except Exception as e:
        log.error("%s: Disconnected (%s)" % (component["name"], e))
        return


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
