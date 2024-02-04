#!/usr/bin/env /usr/bin/python3

import os, time, sys, signal
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS
from dotenv import load_dotenv
import requests
import logging
from colorlog import ColoredFormatter
from requests.auth import HTTPDigestAuth

LOG_LEVEL = logging.DEBUG
LOGFORMAT = "  %(log_color)s%(levelname)-8s%(reset)s | %(log_color)s%(message)s%(reset)s"
logging.root.setLevel(LOG_LEVEL)
formatter = ColoredFormatter(LOGFORMAT)
stream = logging.StreamHandler()
stream.setLevel(LOG_LEVEL)
stream.setFormatter(formatter)
log = logging.getLogger('pythonConfig')
log.setLevel(LOG_LEVEL)
log.addHandler(stream)

load_dotenv()

WRITE_CLIENT = InfluxDBClient(
    url=os.environ["INFLUXDB_URL"],
    token=os.environ["INFLUXDB_TOKEN"],
    org=os.environ["INFLUXDB_ORG"],
)

WRITE_API = WRITE_CLIENT.write_api(write_options=SYNCHRONOUS)

def shelly_collector():
    if "SHELLY_GEN1" not in os.environ or "SHELLY_GEN2" not in os.environ:
        log.error("Please set the SHELLY_GEN1 and SHELLY_GEN2 environment variables")
        sys.exit(1)

    gen1 = os.environ["SHELLY_GEN1"].split(",")
    gen2 = os.environ["SHELLY_GEN2"].split(",")

    for shelly in gen1 + gen2:
        log.info(f'Shelly {shelly} added to monitoring')

    if (len(gen1) + len(gen2)) == 0:
        log.error("No Shellys to monitor")
        sys.exit(1)

    log.info("Starting Shelly collector")
    while True:
        try:
            for shelly in gen1:
                request = requests.get(f"http://{shelly}/meter/0", timeout=2, auth=(os.environ["SHELLY_USER"], os.environ["SHELLY_PASS"]) if os.environ["SHELLY_USER"] and os.environ["SHELLY_PASS"] else None)
                data = request.json()
                power = data["power"]
                total = data["total"]
                WRITE_API.write(
                    os.environ["INFLUXDB_BUCKET"],
                    os.environ["INFLUXDB_ORG"],
                    [
                        Point("switch")
                        .tag("shelly", shelly)
                        .field("power", power)
                        .field("total", total)
                        .time(time.time_ns(), WritePrecision.NS)
                    ],
                )
                log.info(f"Shelly {shelly} - Power: {power}, Total: {total}")
            for shelly in gen2:
                request = requests.get(f"http://{shelly}/rpc/Switch.GetStatus?id=0", timeout=2, auth=HTTPDigestAuth(username=os.environ["SHELLY_USER"],password=os.environ["SHELLY_PASS"]) if os.environ["SHELLY_USER"] and os.environ["SHELLY_PASS"] else None)
                data = request.json()
                power = data["apower"]
                total = data["aenergy"]["total"]
                temp = data["temperature"]["tC"]
                volt = data["voltage"]
                current = data["current"]
                WRITE_API.write(
                    os.environ["INFLUXDB_BUCKET"],
                    os.environ["INFLUXDB_ORG"],
                    [
                        Point("switch")
                        .tag("shelly", shelly)
                        .field("power", power)
                        .field("total", int(total))
                        .field("temp", temp)
                        .field("volt", volt)
                        .field("current", current)
                        .time(time.time_ns(), WritePrecision.NS)
                    ],
                )
                log.info(f"Shelly {shelly} - Power: {power}, Total: {total}, Temp: {temp}, Volt: {volt}, Current: {current}")
        except Exception as e:
            log.error(e)
        time.sleep(10)

#Handle ctrl c
def signal_handler(sig, frame):
    log.warning('You pressed Ctrl+C!')
    sys.exit(0)

if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal_handler)
    shelly_collector()
