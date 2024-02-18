import fcntl
import locale
import os
import socket
import traceback
from datetime import datetime
from json import loads
from math import pow
from os import getenv
from pprint import pprint
from re import findall, search, split, sub
from sys import stderr
from time import sleep

import requests
from bs4 import BeautifulSoup
from colorama import Fore, init
from icao_nnumber_converter_us import n_to_icao

enc = locale.getpreferredencoding(False)
def readlines_nb(f):
  fd = f.fileno()
  fl = fcntl.fcntl(fd, fcntl.F_GETFL)
  fcntl.fcntl(fd, fcntl.F_SETFL, fl | os.O_NONBLOCK)
  buf = bytearray()
  while True:
    try:
      block = os.read(fd, 8192)
    except BlockingIOError:
      yield ""
      continue
    if not block:
      if buf:
        yield buf.decode(enc)
        buf.clear()
      break
    buf.extend(block)
    while True:
      r = buf.find(b'\r')
      n = buf.find(b'\n')
      if r == -1 and n == -1: break
      if r == -1 or r > n:
        yield buf[:(n+1)].decode(enc)
        buf = buf[(n+1):]
      elif n == -1 or n > r:
        yield buf[:r].decode(enc) + '\n'
        if n == r+1:
          buf = buf[(r+2):]
        else:
          buf = buf[(r+1):]

ACARS_HOST = getenv("ACARS_HOST", "acars_router")
VDLM2_HOST = getenv("VDLM2_HOST", "acars_router")
HFDL_HOST = getenv("HFDL_HOST", "acars_router")
SBS_HOST = getenv("SBS_HOST", "ultrafeeder")

ACARS_PORT = int(getenv("ACARS_PORT", 15550))
VDLM2_PORT = int(getenv("VDLM2_PORT", 15555))
HFDL_PORT = int(getenv("HFDL_PORT", 15556))
SBS_PORT = int(getenv("SBS_PORT", 12000))

acarssock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
acarssock.connect((ACARS_HOST, ACARS_PORT))
acarsgen = readlines_nb(acarssock)

vdlm2sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
vdlm2sock.connect((VDLM2_HOST, VDLM2_PORT))
vdlm2gen = readlines_nb(vdlm2sock)

hfdlsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
hfdlsock.connect((HFDL_HOST, HFDL_PORT))
hfdlgen = readlines_nb(hfdlsock)

outsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
outsock.connect((SBS_HOST, SBS_PORT))

acdb = {}
regdb = {}
while True:
  try:
    sbs = {}

    raw = next(acarsgen).strip()
    if raw:
      sbs["type"] = "acars"
    else:
      raw = next(vdlm2gen).strip()
      if raw:
        sbs["type"] = "vdlm2"
      else:
        raw = next(hfdlgen).strip()
        if raw:
          sbs["type"] = "hfdl"
        else:
          sleep(1)
          continue

    data = loads(raw)
    if sbs["type"] == "vdlm2":
      data = data["vdl2"]
    elif sbs["type"] == "hfdl":
      data = loads(raw)["hfdl"]
    del data["app"]
#    pprint(data)

    if sbs["type"] == "acars":
      if data.get("text") is None or data["label"] == "SQ":
        continue
      else:
        sbs["reg"] = data["tail"]
        sbs["time"] = data["timestamp"]
        sbs["flight"] = data.get("flight", "")
        sbs["txt"] = data["text"]
        sbs["msgtype"] = data["label"]
    elif sbs["type"] == "vdlm2":
      if data.get("avlc") is None or data["avlc"].get("acars") is None or data["avlc"]["acars"].get("msg_text") is None:
        continue
      sbs["reg"] = data["avlc"]["acars"]["reg"]
      sbs["time"] = data["t"]["sec"] + data["t"]["usec"]/1e6
      sbs["flight"] = data["avlc"]["acars"]["flight"]
      sbs["txt"] = data["avlc"]["acars"]["msg_text"]
      sbs["msgtype"] = data["avlc"]["acars"]["label"]
    elif sbs["type"] == "hfdl":
      if not data.get("lpdu"):
        if not data.get("spdu"):
          pprint(data, stream=stderr)
          print("hfdl bad top level key", file=stderr)
        continue
#      if not data["lpdu"].get("hfnpdu"):
#        pprint(data, stream=stderr)
#        print("hfdl no keys", file=stderr)
#        continue
      sbs["time"] = data["t"]["sec"] + data["t"]["usec"]/1e6
      sbs["flight"] = data["lpdu"].get("hfnpdu", {}).get("flight_id", "")
      try:
        sbs["lat"] = data["lpdu"]["hfnpdu"]["pos"]["lat"]
        sbs["lon"] = data["lpdu"]["hfnpdu"]["pos"]["lon"]
        if sbs["lat"] == 180 and sbs["lon"] == 180:
          continue
      except:
        pass
      if data["lpdu"].get("hfnpdu", {}).get("acars"):
        sbs["reg"] = data["lpdu"]["hfnpdu"]["acars"]["reg"]
        sbs["flight"] = data["lpdu"]["hfnpdu"]["acars"].get("flight", "")
        sbs["txt"] = data["lpdu"]["hfnpdu"]["acars"]["msg_text"]
        sbs["msgtype"] = data["lpdu"]["hfnpdu"]["acars"]["label"]

      sbs["id"] = data["lpdu"]["src"]["id"]
      sbs["msgtype"] = data["lpdu"]["type"]["id"]
      if sbs["msgtype"] == 191 or sbs["msgtype"] == 79:
#        pprint(data["lpdu"]["ac_info"], stream=stderr)
        sbs["icao"] = data["lpdu"]["ac_info"].get("icao", "")
        sbs["reg"] = data["lpdu"]["ac_info"].get("regnr", "")
        regdb[sbs["flight"]] = {"icao": sbs["icao"], "reg": sbs["reg"]}
        print(f"hfdl logon req/res {sbs['flight']} {regdb[sbs['flight']]}", file=stderr)
      elif sbs["msgtype"] == 159:
#        pprint(data["lpdu"]["ac_info"], stream=stderr)
        sbs["id"] = data["lpdu"]["assigned_ac_id"]
        sbs["icao"] = data["lpdu"]["ac_info"].get("icao", "")
        sbs["reg"] = data["lpdu"]["ac_info"].get("regnr", "")
        acdb[sbs["id"]] = {"icao": sbs["icao"], "reg": sbs["reg"], "flight": sbs["flight"]}
        print(f"hfdl logon confirm {sbs['id']} {acdb[sbs['id']]}", file=stderr)
      else:
        if acdb.get(sbs["id"]):
#          print(f"hfdl ac in db: {sbs['id']}", file=stderr)
          sbs["reg"] = acdb[sbs["id"]]["reg"]
          sbs["icao"] = acdb[sbs["id"]]["icao"]
        elif regdb.get(sbs["flight"]):
#          print(f"hfdl ac in reg db: {sbs['flight']}", file=stderr)
          sbs["reg"] = regdb[sbs["flight"]]["reg"]
          sbs["icao"] = regdb[sbs["flight"]]["icao"]
        else:
#          pprint(data, stream=stderr)
#          print(f"hfdl ac not in db: {sbs['id']} {sbs['flight']}", file=stderr)
          continue
    else:
      continue

    if not sbs.get("txt") and not sbs.get("lat"):
      continue

    sbs["txt"] = sbs.get("txt", "").upper().replace("\r", "").replace("\n", "")

    if sbs.get("lat"):
        lat = sbs["lat"]
        lon = sbs["lon"]
    else:
#      pos = findall("[NS]\s*\d+\.?\d*\s*,?\s*[WE]\s*\d+\.?\d*", sbs["txt"])
      pos1 = findall("/?[N]?[\s\d\.]{4,15},?\s*/?[W-][\s\d\.]{4,15}", sbs["txt"])
      pos2a = findall("LAT", sbs["txt"])
      pos2b = findall("LON", sbs["txt"])
      if (len(pos1) == 1):
        txt = sub(r'(/?[N]?[\s\d\.]{4,15},?\s*/?[W-][\s\d\.]{4,15})', Fore.RED + r'\1' + Fore.RESET, sbs["txt"])

        pos = pos1[0]
        pos = sub(r'/', '', pos)
        pos = sub(r'\s', '', pos)
        pos = sub(r',', '', pos)
        pos = sub(r'\.', '', pos)
        pos = sub(r'-', 'W', pos)

        issouth = "S" in pos
        iswest = "W" in pos

        if "N" in pos or "S" in pos:
          if "W" not in pos and "E" not in pos:
            continue
        else:
          if "W" in pos or "E" in pos:
            continue

        print(txt, file=stderr)

        pos = split(r'[WE-]', pos[1:])

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
        print(txt, file=stderr)
      else:
        continue

    print(f'{sbs["type"]} {sbs["msgtype"]}', file=stderr)
#    print(pos, file=stderr)

    sbs["reg"] = sub(r'[^a-zA-Z0-9]', '', sbs["reg"]).upper()
    if not sbs.get("icao"):
      sbs["icao"] = n_to_icao(sbs["reg"])
#    if not sbs.get("icao"):
#      UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0"
#      URL = f"https://www.flightradar24.com/data/aircraft/{sbs['reg']}"
#      page = requests.get(URL, headers={"User-Agent": UA})
#      sbs["icao"] = BeautifulSoup(page.content, "html.parser").find(id="txt-mode-s").contents[0].strip()
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

    out = f'MSG,3,1,1,{sbs["icao"].upper()},1,{datetime.fromtimestamp(sbs["time"]):%Y/%m/%d,%T.%f},{datetime.now():%Y/%m/%d,%T.%f},{sbs["flight"]},,,,{lat},{lon},,{squawk},,,,\n'

    print(f'{Fore.BLUE}{out}{Fore.RESET}', file=stderr)
    outsock.sendall(out.encode(enc))
  except KeyboardInterrupt:
    print("Got ctrl-c, closing", file=stderr)
    acarssock.close()
    vdlm2sock.close()
    hfdlsock.close()
    outsock.close()
    break
  except BrokenPipeError:
    print("Reconnecting", file=stderr)
    acarssock.close()
    vdlm2sock.close()
    hfdlsock.close()
    outsock.close()
    acarssock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    acarssock.connect((ACARS_HOST, ACARS_PORT))
    acarsgen = readlines_nb(acarssock)
    vdlm2sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    vdlm2sock.connect((VDLM2_HOST, VDLM2_PORT))
    vdlm2gen = readlines_nb(vdlm2sock)
    hfdlsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    hfdlsock.connect((HFDL_HOST, HFDL_PORT))
    hfdlgen = readlines_nb(hfdlsock)
    outsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    outsock.connect((SBS_HOST, SBS_PORT))
  except BaseException:
    print("Other exception:", file=stderr)
    pprint(data, stream=stderr)
    print(traceback.format_exc(), file=stderr)
    pass

