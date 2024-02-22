import locale
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

import requests
from bs4 import BeautifulSoup
from colorama import Fore, init

from acars_decode import Decoder as AD
from util import *

def rx_thread(host, rxq):
  prctl.set_name(f"rx {host[0]}:{host[1]}")
  sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
  sock.connect(host)
  rdr = sock2lines(sock)
  print(f"Connected to JSON input at {host[0]}:{host[1]}")
  while True:
    msg = next(rdr).strip()
    if msg:
      rxq.put_nowait(msg)
    else:
      sleep(1)

def tx_thread(host, txq):
  prctl.set_name(f"tx {host[0]}:{host[1]}")
  sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
  sock.connect(host)
  print(f"Connected to SBS output at {host[0]}:{host[1]}")
  while True:
    msg = txq.get()
    sock.sendall(msg.encode(enc))

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
  Thread(name=f"rx {j[0]}:{j[1]}", target=thread_wrapper, args=(rx_thread, j, rxq)).start()

txqs = []
for i,s in enumerate(sbs_out):
  txqs.append(SimpleQueue())
  Thread(name=f"tx {s[0]}:{s[1]}", target=thread_wrapper, args=(tx_thread, s, txqs[-1])).start()

while True:
  try:
    raw = rxq.get()

    data = loads(raw)
    sbs = AD.decode(data)
    if sbs is None:
      continue

    if not sbs.get("txt") and not sbs.get("lat"):
      continue

    sbs["txt"] = sbs.get("txt", "").upper().replace("\r", "").replace("\n", "")

    if sbs.get("lat"):
        lat = sbs["lat"]
        lon = sbs["lon"]
    else:
      rgx1 = r"([NS][\s\d\.]{4,15},?\s*/?[WE][\s\d\.]{4,15})"
      rgx2 = r"([\s\d\.]{4,15}[NS],?\s*/?[\s\d\.]{4,15}[WE])"
#      pos = findall("[NS]\s*\d+\.?\d*\s*,?\s*[WE]\s*\d+\.?\d*", sbs["txt"])
      pos1 = findall(rgx1, sbs["txt"])
      pos1b = findall(rgx2, sbs["txt"])
      pos2a = findall("LAT", sbs["txt"])
      pos2b = findall("LON", sbs["txt"])
      if (len(pos1) == 1):
        txt = sub(rgx1, Fore.RED + r'\1' + Fore.RESET, sbs["txt"])

        pos = pos1[0]
        pos = sub(r'/', '', pos)
        pos = sub(r'\s', '', pos)
        pos = sub(r',', '', pos)
        pos = sub(r'\.', '', pos)
        pos = sub(r'-', 'W', pos)

        issouth = "S" in pos
        iswest = "W" in pos
        isnorth = "N" in pos
        iseast = "E" in pos

        if not(isnorth or issouth) and not(iswest or iseast):
          continue

        print(txt, file=stderr)

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

        pos = pos1b[0]
        pos = sub(r'/', '', pos)
        pos = sub(r'\s', '', pos)
        pos = sub(r',', '', pos)
        pos = sub(r'\.', '', pos)
        pos = sub(r'-', 'W', pos)

        issouth = "S" in pos
        iswest = "W" in pos
        isnorth = "N" in pos
        iseast = "E" in pos

        if not(isnorth or issouth) and not(iswest or iseast):
          continue

        print(txt, file=stderr)

        pos = split(r'[NS]', pos[1:])

        lat = pos[0].lstrip("0")
        lon = pos[1].lstrip("0")[:len(lat)]

        if lat and lon:
          lat = int(lat)/pow(10, len(lat)-2) * (-1 if issouth else 1)
          lon = int(lon)/pow(10, len(lon)-2) * (-1 if iswest else 1)
        else:
          continue
      elif len(pos2a) and len(pos2b):
        txt = sub(r'(LAT)', Fore.MAGENTA + r'\1' + Fore.RESET, sbs["txt"])
        txt = sub(r'(LON)', Fore.MAGENTA + r'\1' + Fore.RESET, txt)
        print(txt, file=stderr)
        continue
      else:
        continue

    print(f'{sbs["type"]} {sbs["msgtype"]}', file=stderr)
#    print(pos, file=stderr)

    sbs["reg"] = sub(r'[^a-zA-Z0-9-]', '', sbs["reg"]).upper()

    if not sbs.get("icao"):
      sbs["icao"] = reg2icao(sbs["reg"])
    if not sbs.get("icao"):
      print(f'{Fore.GREEN}xxxxxxx {sbs["reg"]}\t{sbs["icao"]}{Fore.RESET}', file=stderr)
      continue

    if sbs["type"] == "acars":
      squawk = "1111"
    elif sbs["type"] == "vdlm2":
      squawk = "2222"
    elif sbs["type"] == "hfdl":
      squawk = "3333"
    else:
      squawk = "0000"

    out = f'MSG,3,1,1,{sbs["icao"].upper()},1,{datetime.fromtimestamp(sbs["time"], tz=timezone.utc):%Y/%m/%d,%T},{datetime.now(timezone.utc):%Y/%m/%d,%T},{sbs["flight"]},,,,{lat},{lon},,{squawk},,,,'

    print(f'https://globe.adsbexchange.com/?icao={sbs["icao"]}&showTrace={datetime.fromtimestamp(sbs["time"], tz=timezone.utc):%Y-%m-%d}&timestamp={sbs["time"]}')
    print(f'{Fore.BLUE}{out}{Fore.RESET}\n', file=stderr)
    for q in txqs:
      q.put(out+"\r\n")
  except BaseException:
    print("Other exception:", file=stderr)
    pprint(data, stream=stderr)
    print(traceback.format_exc(), file=stderr)
    pass

