import locale
import os
import socket
import traceback
from datetime import datetime, timezone
from json import loads
from math import pow
from os import getenv
from pprint import pprint
import prctl
from queue import SimpleQueue
from re import findall, search, split, sub
from sys import stderr
from threading import Thread, current_thread
from time import sleep
import math
import requests
from bs4 import BeautifulSoup
from colorama import Fore

from acars_decode import Decoder as AD
from util import *

def rx_thread(host, rxq):
  prctl.set_name(f"rx {host[0]}:{host[1]}")
  sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
  sock.connect(host)
  rdr = sock2lines(sock)
  print(f"Connected to JSON input at {host[0]}:{host[1]}")
  while True:
    msg = next(rdr)
    if msg is None:
      sleep(0.2)
      continue

    msg = msg.strip()
    if msg:
      rxq.put_nowait(msg)

def tx_thread(host, txq):
  prctl.set_name(f"tx {host[0]}:{host[1]}")
  sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
  sock.connect(host)
  print(f"Connected to SBS output at {host[0]}:{host[1]}")
  while True:
    msg = txq.get()
    sock.sendall(msg.encode(enc))

def generateBasestation(sbs, lat, lon):
  sbs_timestamp = f'{datetime.fromtimestamp(sbs["time"], tz=timezone.utc):%Y/%m/%d,%T}.{(math.modf(sbs["time"])[0] * 1000):03.0f}'
  sbs_callsign = sbs.get("flight", "")
  if sbs_callsign:
    sbs_callsign = sbs_callsign.ljust(8, ' ')
  if lat != None and lon != None:
    latstr = f'{lat:.6f}'
    lonstr = f'{lon:.6f}'
  else:
    latstr = ''
    lonstr = ''
  if sbs.get("ground"):
    ground = '-1'
  elif sbs.get("ground") == False or sbs.get("alt", 0) > 100 or sbs.get("spd", 0) > 100:
    ground = '0'
  else:
    ground = ''
  return f'MSG,3,1,1,{sbs["icao"].upper()},1,{sbs_timestamp},{sbs_timestamp},{sbs_callsign},{sbs.get("alt", "")},{sbs.get("spd", "")},,{latstr},{lonstr},,{sbs["squawk"]},,0,,{ground}'

# wrapper to catch exceptions and restart threads
def thread_wrapper(func, *args):
    slp = 10
    while True:
        try:
          print(f"[{current_thread().name}] starting thread")
          func(*args)
        except BrokenPipeError:
          print(f"[{current_thread().name}] pipe broken; restarting thread in {slp} seconds")
        except ConnectionRefusedError:
          print(f"[{current_thread().name}] connection refused; restarting thread in {slp} seconds")
        except StopIteration:
          print(f"[{current_thread().name}] lost connection; restarting thread in {slp} seconds")
        except BaseException as exc:
          print(traceback.format_exc())
          print(f"[{current_thread().name}] exception {type(exc).__name__}; restarting thread in {slp} seconds")
        else:
          print(f"[{current_thread().name}] thread function returned; restarting thread in {slp} seconds")
        sleep(slp)

json_in = getenv("JSON_IN", "acars_router:15550")
json_in = json_in.split(";")
json_in = [x.split(":") for x in json_in]
json_in = [(x,int(y)) for x,y in json_in]

sbs_out = getenv("SBS_OUT", "ultrafeeder:12000")
sbs_out = sbs_out.split(";")
sbs_out = [x.split(":") for x in sbs_out]
sbs_out = [(x,int(y)) for x,y in sbs_out]

rxq = SimpleQueue()
for i,j in enumerate(json_in):
  Thread(name=f"rx {j[0]}:{j[1]}", target=thread_wrapper, daemon=True, args=(rx_thread, j, rxq)).start()

txqs = []
for i,s in enumerate(sbs_out):
  txqs.append(SimpleQueue())
  Thread(name=f"tx {s[0]}:{s[1]}", target=thread_wrapper, daemon=True, args=(tx_thread, s, txqs[-1])).start()

if getenv("LOG_FILE") and not os.path.exists("/log"):
     os.makedirs("/log")

squawks = {}
while True:
  try:
    raw = rxq.get()

    data = loads(raw)
    sbs = AD.decode(data)
    if sbs is None:
      continue

    if sbs["msgtype"] not in squawks:
      squawks[sbs["msgtype"]] = {}
    if sbs["squawk"] not in squawks[sbs["msgtype"]]:
      squawks[sbs["msgtype"]][sbs["squawk"]] = 0
    squawks[sbs["msgtype"]][sbs["squawk"]] += 1


    totals = {"total": {"airframes": 0, "python": 0, "total": 0}}
    for k,v in squawks.items():
        totals[k] = {}
        totals[k]["airframes"] = 0
        totals[k]["python"] = 0
        totals[k]["total"] = 0
        for k2,v2 in v.items():
            totals[k]["total"] += v2
            totals[k]["airframes"] += v2 if str(k2)[1] != "0" else 0
            totals[k]["python"] += v2 if str(k2)[2] != "0" else 0
            totals["total"]["total"] += v2
            totals["total"]["airframes"] += v2 if str(k2)[1] != "0" else 0
            totals["total"]["python"] += v2 if str(k2)[2] != "0" else 0
    if totals["total"]["total"] / 10 == totals["total"]["total"] // 10:
        totsort = dict(sorted(totals.items(), key=lambda item: item[1]["total"]))
        pprint(totsort, sort_dicts=False)

    if not sbs.get("reg"):
      sbs["reg"] = icao2reg(sbs.get("icao", ""))

    sbs["reg"] = sub(r'[^a-zA-Z0-9-]', '', sbs["reg"]).upper()

    if not sbs.get("icao"):
      sbs["icao"] = reg2icao(sbs.get("reg", ""))
    if not sbs.get("icao"):
      print(f'{Fore.GREEN}xxxxxxx {sbs["reg"]}{Fore.RESET}', file=stderr)
      continue

    if sbs["type"] == "acars":
      if getenv("ACARS_FREQ_AS_ALT"):
        sbs["alt"] = f"{round(sbs['freq']/1000-100000):d}"
      if getenv("ACARS_FREQ_AS_SQUAWK"):
        squawk = f"{round(sbs['freq']/1000-100000):d}"
    elif sbs["type"] == "vdlm2":
      if getenv("VDLM2_FREQ_AS_ALT"):
        sbs["alt"] = f"{round(sbs['freq']/1000-100000):d}"
      if getenv("VDLM2_FREQ_AS_SQUAWK"):
        squawk = f"{round(sbs['freq']/1000-100000):d}"
    elif sbs["type"] == "hfdl":
      if getenv("HFDL_FREQ_AS_ALT"):
        sbs["alt"] = f"{round(sbs['freq']/1000):d}"
      if getenv("HFDL_FREQ_AS_SQUAWK"):
        squawk = f"{round(sbs['freq']/1000):d}"
    else:
      squawk = "9999"

    if sbs.get("lat"):
      lat = sbs["lat"]
      lon = sbs["lon"]
      if getenv("LOG_FILE") and sbs.get("msgtype") and sbs.get("type") != "hfdl":
        with open(f"/log/pos.log", "a", 1) as logfile:
          logfile.write(f'{sbs["type"]}\t{sbs.get("msgtype")}\thttps://globe.adsbexchange.com/?icao={sbs["icao"]}&showTrace={datetime.fromtimestamp(sbs["time"], tz=timezone.utc):%Y-%m-%d}&timestamp={sbs["time"]}\n')
          logfile.write(f'{sbs["lat"]}, {sbs["lon"]}\n')
          logfile.write(f'{sbs.get("txt")}\n\n')
    else:
      if s := getenv("SEND_ALL"):
        out = generateBasestation(sbs=sbs, lat=None, lon=None)
        if s == "log":
          print(f"sending nonpos {out}")
        for q in txqs:
          q.put(out+"\r\n")

      if not sbs.get("txt"):
        continue

      if getenv("LOG_FILE") and sbs.get("msgtype") and sbs.get("type") != "hfdl":
        with open(f"/log/nopos.log", "a", 1) as logfile:
          logfile.write(f'{sbs["type"]}\t{sbs.get("msgtype")}\thttps://globe.adsbexchange.com/?icao={sbs["icao"]}&showTrace={datetime.fromtimestamp(sbs["time"], tz=timezone.utc):%Y-%m-%d}&timestamp={sbs["time"]}\n')
          logfile.write(f'{sbs["txt"]}\n\n')

      rgx1 = r"([NS][\s\d\.]{4,15},?\s*/?[WE][\s\d\.]{4,15})"
      rgx2 = r"([\s\d\.]{4,15}[NS],?\s*/?[\s\d\.]{4,15}[WE])"
#      pos = findall("[NS]\s*\d+\.?\d*\s*,?\s*[WE]\s*\d+\.?\d*", sbs["txt"])
      pos1 = findall(rgx1, sbs["txt"])
      pos1b = findall(rgx2, sbs["txt"])
      pos2a = findall("LAT", sbs["txt"])
      pos2b = findall("LON", sbs["txt"])
      if (len(pos1) == 1):
        txt = sub(rgx1, Fore.RED + r'\1' + Fore.RESET, sbs["txt"])
        print(f"old regex 1 matched message type {sbs['msgtype']}")
        print(txt)

        pos = pos1[0]
        pos = sub(r'/', '', pos)
        pos = sub(r'\s', '', pos)
        pos = sub(r',', '', pos)
        pos = sub(r'\.', '', pos)

        issouth = "S" in pos
        iswest = "W" in pos
        isnorth = "N" in pos
        iseast = "E" in pos

        if not(isnorth or issouth) and not(iswest or iseast):
          continue

        pos = split(r'[WE]', pos[1:])

        lat = pos[0].lstrip("0")
        lon = pos[1].lstrip("0")[:len(lat)]

        if lat and lon:
          lat = int(lat)/pow(10, len(lat)-2) * (-1 if issouth else 1)
          lon = int(lon)/pow(10, len(lon)-2) * (-1 if iswest else 1)
        else:
          continue
      elif len(pos1b) == 1:
        txt = sub(rgx2, Fore.RED + r'\1' + Fore.RESET, sbs["txt"])
        print(f"old regex 2 matched message type {sbs['msgtype']}")
        print(txt)

        pos = pos1b[0]
        pos = sub(r'/', '', pos)
        pos = sub(r'\s', '', pos)
        pos = sub(r',', '', pos)
        pos = sub(r'\.', '', pos)

        issouth = "S" in pos
        iswest = "W" in pos
        isnorth = "N" in pos
        iseast = "E" in pos

        if not(isnorth or issouth) and not(iswest or iseast):
          continue

        pos = split(r'[NS]', pos[1:])

        lat = pos[0].lstrip("0")
        lon = pos[1].lstrip("0")[:len(lat)]

        if lat and lon:
          lat = int(lat)/pow(10, len(lat)-2) * (-1 if issouth else 1)
          lon = int(lon)/pow(10, len(lon)-2) * (-1 if iswest else 1)
        else:
          continue
      elif len(pos2a) and len(pos2b):
        txt = sub(r'(LAT)', Fore.RED + r'\1' + Fore.RESET, sbs["txt"])
        txt = sub(r'(LON)', Fore.RED + r'\1' + Fore.RESET, txt)
        print(f"old regex 3 matched message type {sbs['msgtype']}")
        print(txt)
        continue
      else:
        continue

    print(f'{sbs["type"]} {sbs.get("msgtype")}', file=stderr)
    out = generateBasestation(sbs=sbs, lat=lat, lon=lon)
    print(f'https://globe.adsbexchange.com/?icao={sbs["icao"]}&showTrace={datetime.fromtimestamp(sbs["time"], tz=timezone.utc):%Y-%m-%d}&timestamp={sbs["time"]}')
    print(f'{Fore.BLUE}{out}{Fore.RESET}\n', file=stderr)
    for q in txqs:
      q.put(out+"\r\n")
  except SystemExit:
    exit()
  except BaseException:
    print("Other exception:", file=stderr)
    pprint(data, stream=stderr)
    print(traceback.format_exc(), file=stderr)
    pass
