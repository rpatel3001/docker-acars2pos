from re import compile, sub
from colorama import Fore
from haversine import haversine as gcdist
from os import getenv
from javascript import require

declib = require("@airframes/acars-decoder").MessageDecoder()

dlat = r"(?P<dlat>[NS])"
dlon = r"(?P<dlon>[WE])"

spdig2 = r"(?:\s|\d)\d"
spdig3 = r"(?:\s\s|\s\d|\d\d)\d"

ndig2 = r"(?:\d|\d\d)"
ndig3 = r"(?:\d|\d\d|\d\d\d)"

dig1 = r"\d"
dig2 = r"\d\d"
dig3 = r"\d\d\d"
dig4 = r"\d\d\d\d"

def name(n, rgx):
  return f"(?P<{n}>{rgx})"

def sd2(n):
  return name(n, spdig2)

def sd3(n):
  return name(n, spdig3)

def nd2(n):
  return name(n, ndig2)

def nd3(n):
  return name(n, ndig3)

def d1(n):
  return name(n, dig1)

def d2(n):
  return name(n, dig2)

def d3(n):
  return name(n, dig3)

def d4(n):
  return name(n, dig4)

def getLat(raw):
  lat =  float(raw.get("latdeg", 0))
  lat += float(raw.get("latdeg100", 0))/100
  lat += float(raw.get("latdeg1000", 0))/1000
  lat += float(raw.get("latdeg10000", 0))/10000
  lat += float(raw.get("latmin", 0))/60
  lat += float(raw.get("latmin10", 0))/600
  lat += float(raw.get("latmin100", 0))/6000
  lat += float(raw.get("latsec", 0))/3600
  lat *= -1 if raw.get("dlat") == "S" or raw.get("dlat") == "-" else 1
  return lat

def getLon(raw):
  lon =  float(raw.get("londeg", 0))
  lon += float(raw.get("londeg100", 0))/100
  lon += float(raw.get("londeg1000", 0))/1000
  lon += float(raw.get("londeg10000", 0))/10000
  lon += float(raw.get("lonmin", 0))/60
  lon += float(raw.get("lonmin10", 0))/600
  lon += float(raw.get("lonmin100", 0))/6000
  lon += float(raw.get("lonsec", 0))/3600
  lon *= -1 if raw.get("dlon") == "W" or raw.get("dlon") == "-" else 1
  return lon


rgxs = [
        compile(dlat + r"[ 0]{0,2}(\d{1,2}\.\d{3}).?" + dlon + r"[ 0]{0,2}(\d{1,3}\.\d{3})"), # thousandths of degrees
        compile(dlat + r"[ 0]{0,1}(\d{1,2})[ 0]{0,1}(\d{1,2}\.\d{1}).?" + dlon + r"[ 0]{0,2}(\d{1,3}?)[ 0]{0,1}(\d{1,2}\.\d{1})"), # tenths of minutes
        compile(dlat + r"[ 0]{0,1}(\d{1,2})[ 0]{0,3}(\d{0,2}\.\d{2}).?" + dlon +r"[ 0]{0,2}(\d{1,3})[ 0]{0,1}(\d{1,2}\.\d{2})"), # hundredths of minutes
        compile(dlat + r"\s?(\d{2})(\d{2})(\d{2}).?" + dlon + r"\s?(\d{2,3})(\d{2})(\d{2})"), # seconds
        compile(dlat + r"[ 0]?([ 0\d]\d)(\d{3}).?" + dlon + r"([ 0\d][ 0\d]\d)(\d{3})"), # tenths of minutes, no decimal
        compile(r"[ 0]{0,1}(\d{1,2})[ 0]{0,1}(\d{1,2}\.\d{1})" + dlat + r"[ 0]{0,2}(\d{1,3})[ 0]{0,1}(\d{1,2}\.\d{1})" + dlon), # tenths of minutes, direction after
        compile(r"[ 0]{0,1}(\d{1,2})[ 0]{0,1}(\d{1,2})" + dlat + r"[ 0]{0,2}(\d{1,3})[ 0]{0,1}(\d{1,2})" + dlon), # minutes, direction after
        compile(r"LAT " + dlat + r" [ 0]{0,1}(\d{1,2}):(\d{2}\.\d{1})  LONG " + dlon + r" [ 0]{0,1}(\d{1,2}):(\d{2}\.\d{1})"), # tenths of minuts, colon separator
        ]

msgrgx = {
         "10": [compile(dlat + d2("latdeg") + r"\." + d3("latdeg1000") + r"\/" + dlon + d3("londeg") + r"\." + d3("londeg1000")),
                compile(dlat + sd3("latdeg") + r"\." + d3("latdeg1000") + r"," + dlon + sd3("londeg") + r"\." + d3("londeg1000"))],
         "12": [compile(dlat + sd3("latdeg") + d2("latmin") + d2("latsec") + dlon + sd3("londeg") + d2("lonmin") + d2("lonsec")),
                compile(dlat + sd3("latdeg") + r"\." + d3("latdeg1000") + r"," + dlon + sd3("londeg") + r"\." + d3("londeg1000")),
                compile(dlat + d2("latdeg") + d2("latmin") + d1("latmin10") + dlon + d3("londeg") + d2("lonmin") + d1("lonmin10"))],
         "13": [compile(r"^\s*(?P<dlat>-?)" + nd2("latdeg") + r"\." + d3("latdeg1000") + r" " + r"(?P<dlon>-?)" + nd3("londeg") + r"\." + d3("londeg1000") + r"\s")],
         "14": [compile(dlat + sd2("latdeg") + d2("latmin") + d1("latmin10") + dlon + sd3("londeg") + d2("lonmin") + d1("lonmin10"))],
         "15": [compile(dlat + sd2("latdeg") + d2("latmin") + d1("latmin10") + dlon + sd3("londeg") + d2("lonmin") + d1("lonmin10")),
                compile(dlat + sd2("latdeg") + d2("latmin") + d2("latsec") + dlon + sd3("londeg") + d2("lonmin") + d2("lonsec"))],
         "16": [compile(r"^(?:[^,]*,){4}" + dlat + sd2("latdeg") + sd2("latmin") + r"\." + d2("latmin100") + r"\s" + dlon + sd3("londeg") + sd2("lonmin") + r"\." + d2("lonmin100")),
                compile(r"^(?:[^,]*,){4}" + dlat + r" " + nd2("latdeg") + r"\." + d3("latdeg1000") + r"[,\s]" + dlon + r" " + nd3("londeg") + r"\." + d3("londeg1000")),
                compile(r"^(?:[^,]*,){1}" + dlat + sd3("latdeg") + r"\." + d3("latdeg1000") + r"," + dlon + r" " + sd3("londeg") + r"\." + d3("londeg1000")),
                compile(r"^\/" + dlat + d3("latdeg") + r"\." + d2("latmin100") + r"\/" + dlon + d3("londeg") + r"\." + d2("lonmin100") + r"\/"),
                compile(dlat + nd2("latdeg") + d2("latmin") + d1("latmin10") + dlon + r" " + nd3("londeg") + d2("lonmin") + d1("lonmin10")),
                compile(dlat + d2("latdeg") + d2("latmin") + r"\." + d2("latmin100") + r" " + dlon + d3("londeg") + d2("lonmin") + r"\." + d2("lonmin100")),
                compile(dlat + d2("latdeg") + d2("latmin") + d2("latsec") + r" " + dlon + d3("londeg") + d2("lonmin") + d2("lonsec"))],
         "18": [compile(dlat + d2("latdeg") + r" " + d2("latmin") + r"\." + d1("latmin10") + r" " + dlon + d3("londeg") + r" " + d2("lonmin") + r"\." + d1("lonmin10"))],
         "1L": [compile(dlat + d2("latdeg") + d2("latmin") + d1("latmin10") + dlon + d3("londeg") + d2("lonmin") + d1("lonmin10"))],
         "20": [compile(dlat + d2("latdeg") + d2("latmin") + d1("latmin10") + dlon + d3("londeg") + d2("lonmin") + d1("lonmin10"))],
         "21": [compile(dlat + sd3("latdeg") + r"\." + d3("latdeg1000") + dlon + sd3("londeg") + r"\." + d3("londeg1000"))],
         "22": [compile(dlat + sd3("latdeg") + d2("latmin") + d2("latsec") + dlon + sd3("londeg") + d2("lonmin") + d2("lonsec"))],
         "30": [compile(dlat + r"\s?" + sd3("latdeg") + r"\." + d3("latdeg1000") + r"," + dlon + r"\s?" + sd3("londeg") + r"\." + d3("londeg1000")),
                compile(r"^(?:[^,]*,){5}" + dlat + sd3("latdeg") + r"\." + d3("latdeg1000") + r"," + dlon + sd3("londeg") + r"\." + d3("londeg1000") + r",")],
         "31": [compile(dlat + sd3("latdeg") + r"\." + d3("latdeg1000") + r"," + dlon + sd3("londeg") + r"\." + d3("londeg1000"))],
         "32": [compile(r"^(?:[^,]*,){5}" + dlat + r"\s" + nd2("latdeg") + r"\." + d3("latdeg1000") + r"\s" + dlon + r"\s" + nd3("londeg") + r"\." + d3("londeg1000") + r",")],
         "33": [compile(r"^(?:[^,]*,){2}" + r"(?P<dlat>-?)" + nd3("latdeg") + r"\." + d3("latdeg1000") + r"," + r"(?P<dlon>-?)" + nd3("londeg") + r"\." + d3("londeg1000") + r","),
                compile(r"^(?:[^,]*,){5}" + dlat + sd3("latdeg") + r"\." + d3("latdeg1000") + r"," + dlon + sd3("londeg") + r"\." + d3("londeg1000") + r",")],
         "36": [compile(r"^(?:[^,]*,){2}[\w-]+" + dlat + sd3("latdeg") + r"\." + d3("latdeg1000") + r"," + dlon + sd3("londeg") + r"\." + d3("londeg1000") + r","),
                compile(r"^(?:[^,]*,){4}" + dlat + sd3("latdeg") + r"\." + d3("latdeg1000") + r"," + dlon + sd3("londeg") + r"\." + d3("londeg1000") + r","),
                compile(r"^(?:[^,]*,){5}" + dlat + sd2("latdeg") + d2("latmin") + d1("latmin10") + r"," + dlon + nd3("londeg") + d2("lonmin") + d1("lonmin10") + r","),
                compile(r"^(?:[^,]*,){5}" + r"(?P<dlat>-?)" + d3("latdeg") + r"\." + d2("latdeg100") + r"," + r"(?P<dlon>-?)" + nd3("londeg") + r"\." + d2("londeg100") + r","),
                compile(r"^(?:[^,]*,){6}" + r"(?P<dlat>-?)" + nd2("latdeg") + r"\." + d2("latdeg100") + r"," + r"(?P<dlon>-?)" + nd3("londeg") + r"\." + d2("londeg100") + r",")],
         "37": [compile(dlat + d2("latdeg") + r" " + d2("latmin") + r"\." + d1("latmin10") + r"\s?" + dlon + d3("londeg") + r" " + d2("lonmin") + r"\." + d1("lonmin10"))],
         "39": [compile(r"^(?:[^,]*,){4}" + r"(?P<dlat>-?)" + nd2("latdeg") + r"\." + d2("latdeg100") + r"," + r"(?P<dlon>-?)" + nd3("londeg") + r"\." + d2("londeg100") + r",")],
         "41": [compile(dlat + sd3("latdeg") + r"\." + d3("latdeg1000") + r"," + dlon + sd3("londeg") + r"\." + d3("londeg1000"))],
         "43": [compile(dlat + sd3("latdeg") + r"\." + d3("latdeg1000") + r"," + dlon + sd3("londeg") + r"\." + d3("londeg1000")),
                compile(r"(?P<dlat>-?)" + nd2("latdeg") + r"\." + d3("latdeg1000") + r"," + r"(?P<dlon>-?)" + nd3("londeg") + r"\." + d3("londeg1000"))],
         "44": [compile(dlat + sd2("latdeg") + d2("latmin") + d1("latmin10") + r"\s?" + dlon + d3("londeg") + d2("lonmin") + d1("lonmin10")),
                compile(dlat + sd3("latdeg") + r"\." + d3("latdeg1000") + r"," + dlon + sd3("londeg") + r"\." + d3("londeg1000"))],
         "45": [compile(dlat + d2("latdeg") + d2("latmin") + d1("latmin10") + dlon + d3("londeg") + d2("lonmin") + d1("lonmin10"))],
         "4A": [compile(dlat + sd3("latdeg") + r"\." + d3("latdeg1000") + r"," + dlon + sd3("londeg") + r"\." + d3("londeg1000"))],
         "4N": [compile(dlat + d3("latdeg") + d2("latmin") + d1("latmin10") + r"\s?" + dlon + d3("londeg") + d2("lonmin") + d1("lonmin10"))],
         "4R": [compile(dlat + sd2("latdeg") + r" " + sd2("latmin") + r"\." + d2("latmin100") + r"\s?" + dlon + sd3("londeg") + r" " + sd2("lonmin") + r"\."+ d2("lonmin100"))],
         "4T": [compile(d2("latdeg") + d2("latmin") + r"\." + d1("latmin10") + dlat + d3("londeg") + d2("lonmin") + r"\." + d1("lonmin10") + dlon)],
         "57": [compile(dlat + d3("latdeg") + d2("latmin") + d2("latsec") + dlon + d3("londeg") + d2("lonmin") + d2("lonsec"))],
         "58": [compile(dlat + nd2("latdeg") + r"\." + d3("latdeg1000") + r"\/" + dlon + nd3("londeg") + r"\." + d3("londeg1000"))],
         "5U": [compile(dlat + d2("latdeg") + d2("latmin") + r"\." + d1("latmin10") + dlon + d3("londeg") + d2("lonmin") + r"\." + d1("lonmin10"))],
         "5Y": [compile(dlat + sd3("latdeg") + d2("latmin") + d2("latsec") + r"," + dlon + r"\s?" + sd3("londeg") + d2("lonmin") + d2("lonsec"))],
         "80": [compile(dlat + d2("latdeg") + d2("latmin") + d1("latmin10") + r",?" + dlon + d3("londeg") + d2("lonmin") + d1("lonmin10")),
                compile(dlat + d2("latdeg") + d2("latmin") + r"\." + d1("latmin10") + r"\s?" + dlon + d3("londeg") + d2("lonmin") + r"\." + d1("lonmin10"))],
         "83": [compile(dlat + d2("latdeg") + d2("latmin") + r"\." + d1("latmin10") + dlon + d3("londeg") + d2("lonmin") + r"\." + d1("lonmin10"))],
         "B0": [compile(dlat + sd2("latdeg") + d2("latmin") + d1("latmin10") + dlon + sd3("londeg") + d2("lonmin") + d1("lonmin10"))],
         "H1": [compile(r"^TRP.*\s" + r"(?P<dlat>-?)" + nd2("latdeg") + r"\." + d4("latdeg10000") + r"\s+" + r"(?P<dlon>-?)" + nd3("londeg") + r"\." + d4("londeg10000") + r"\s"),
                compile(r"^\(POS-.*-" + d2("latdeg") + d2("latmin") + dlat + d3("londeg") + d2("lonmin") + dlon + r"\/"),
                compile(r"^.*?" + dlat + d2("latdeg") + d2("latmin") + r"\." + d1("latmin10") + r"," + dlon + d3("londeg") + d2("lonmin") + r"\." + d1("lonmin10") + r","),
                compile(r"^.*?" + r"(?P<dlat>-?)" + d2("latdeg") + d2("latmin") + d2("latsec") + r",(?P<dlon>-?)" + d3("londeg") + d2("lonmin") + d2("lonsec") + r","),
                compile(dlat + sd3("latdeg") + sd2("latmin") + d1("latmin10") + dlon + sd3("londeg") + sd2("lonmin") + d1("lonmin10"))],
         }

_homelat = float(getenv("LAT", 0))
_homelon = float(getenv("LON", 0))
_maxdist = float(getenv("MAX_DIST", 0))
_distunit = getenv("DIST_UNIT", "nmi")
def checkpos(lat, lon):
  if abs(lat) > 90 or abs(lon) > 180:
    return False
  elif _homelat and _homelon and _maxdist:
    return _maxdist > gcdist((_homelat, _homelon), (lat, lon), unit=_distunit)
  else:
    return True

#nonaf = {}

def decode(msg):
  if msg.get("vdl2"):
    dat = decodeVDLM2(msg["vdl2"])
  elif msg.get("hfdl"):
    dat = decodeHFDL(msg["hfdl"])
  else:
    dat = decodeACARS(msg)

  if dat and dat.get("txt") and dat.get("msgtype"):
    try:
      res = declib.decode({"label": dat["msgtype"], "text": dat["txt"]})
    except:
      print("js bridge failed, killing script")
      exit()
    if res and res.decoded and res.raw:
#      print("airframes")
      dat["squawk"] += 100
      if res.raw.position:
#        print("airframes pos")
        dat["squawk"] += 100
        dat["lat"] = res.raw.position.latitude
        dat["lon"] = res.raw.position.longitude
      if res.raw.altitude:
        dat["alt"] = res.raw.altitude
      if res.raw.groundspeed:
        dat["spd"] = res.raw.groundspeed
      if res.raw.out_time or res.raw.on_time or res.raw.in_time:
        dat["ground"] = True
      if res.raw.off_time:
        dat["ground"] = False
#    else:
#      if res.decoder.decodeLevel in ["none"]: # , "partial"]:
#        nonaf[dat["msgtype"]] = nonaf.get(dat["msgtype"], 0) + 1
#        print(nonaf)

  if not dat or not dat.get("txt"): # or dat.get("lat"):
    return dat

  #dat["txt"] = dat.get("txt", "").upper().replace("\r", "").replace("\n", "")

  rgxl = msgrgx.get(dat.get("msgtype"))
  if rgxl and dat.get("msgtype"):
    for rgx in rgxl:
      raw = rgx.findall(dat["txt"])
      if len(raw) == 1:
        pos = rgx.sub(Fore.GREEN + r"\g<0>" + Fore.RESET, dat["txt"])
        print(f"matched message type {dat['msgtype']}")
        print(pos)
        raw = rgx.search(dat["txt"]).groupdict()
        print(raw)
        dat["lat"] = getLat(raw)
        dat["lon"] = getLon(raw)

      if dat.get("lat"):
        if dat["type"] == "hfdl" or checkpos(dat["lat"], dat["lon"]):
          dat["squawk"] += 10
          return dat
        else:
          print(Fore.RED + "failed distance check" + Fore.RESET)
          del dat["lat"]
          del dat["lon"]

  for k in msgrgx.keys():
    for rgx in msgrgx[k]:
      raw = rgx.findall(dat["txt"])
      if len(raw) == 1:
        pos = rgx.sub(Fore.GREEN + r"\g<0>" + Fore.RESET, dat["txt"])
        print(f"matched message type {dat.get('msgtype')} with regex for {k}")
        print(pos)
        raw = rgx.search(dat["txt"]).groupdict()
        print(raw)
        dat["lat"] = getLat(raw)
        dat["lon"] = getLon(raw)

      if dat.get("lat"):
        if dat["type"] == "hfdl" or checkpos(dat["lat"], dat["lon"]):
          dat["squawk"] += 20
          return dat
        else:
          print(Fore.RED + "failed distance check" + Fore.RESET)
          del dat["lat"]
          del dat["lon"]

  for i,rgx in enumerate(rgxs):
    raw = rgx.findall(dat["txt"])
    if len(raw) == 1:
      pos = rgx.sub(Fore.RED + r"\g<0>" + Fore.RESET, dat["txt"])
      print(f"regex {i} matched message type {dat['msgtype']}")
      print(pos)
      raw = rgx.search(dat["txt"])
      print(raw)
      if i == 0:
        dat["lat"] = float(raw[2]) * (-1 if raw[1] == "S" else 1)
        dat["lon"] = float(raw[4]) * (-1 if raw[3] == "W" else 1)
      elif i == 1 or i == 2 or i == 7:
        dat["lat"] = (int(raw[2]) + float(raw[3])/60) * (-1 if raw[1] == "S" else 1)
        dat["lon"] = (int(raw[5]) + float(raw[6])/60) * (-1 if raw[4] == "W" else 1)
      elif i == 3:
        dat["lat"] = (int(raw[2]) + int(raw[3])/60 + int(raw[4])/3600) * (-1 if raw[1] == "S" else 1)
        dat["lon"] = (int(raw[6]) + int(raw[7])/60 + int(raw[8])/3600) * (-1 if raw[5] == "W" else 1)
      elif i == 4:
        dat["lat"] = (int(raw[2]) + int(raw[3])/600) * (-1 if raw[1] == "S" else 1)
        dat["lon"] = (int(raw[5]) + int(raw[6])/600) * (-1 if raw[4] == "W" else 1)
      elif i == 5 or i == 6:
        dat["lat"] = (int(raw[1]) + float(raw[2])/60) * (-1 if raw[3] == "S" else 1)
        dat["lon"] = (int(raw[4]) + float(raw[5])/60) * (-1 if raw[6] == "W" else 1)

    if dat.get("lat"):
      if dat["type"] == "hfdl" or checkpos(dat["lat"], dat["lon"]):
        dat["squawk"] += 30
        return dat
      else:
        print(Fore.RED + "failed distance check" + Fore.RESET)
        del dat["lat"]
        del dat["lon"]

  return dat

def decodeACARS(msg):
  if msg.get("text") is None or msg["label"] == "SQ":
    return None
  dat = {}
  dat["squawk"] = 1000
  dat["type"] = "acars"
  dat["reg"] = msg["tail"]
  dat["time"] = int(msg["timestamp"])
  dat["flight"] = msg.get("flight", "")
  dat["txt"] = msg["text"]
  dat["msgtype"] = msg["label"]
  dat["freq"] = round(float(msg.get("freq", 0))*1000000)
  return dat

def decodeVDLM2(msg):
  if msg.get("avlc") is None:
    return None
  elif (msg["avlc"].get("acars") is None or msg["avlc"]["acars"].get("msg_text") is None) and (msg["avlc"].get("xid") is None or msg["avlc"]["xid"].get("vdl_params") is None):
    return None
  dat = {}
  dat["squawk"] = 3000
  dat["type"] = "vdlm2"
  dat["time"] = int(msg["t"]["sec"])
  dat["freq"] = int(msg.get("freq", 0))
  if msg["avlc"].get("acars"):
    dat["reg"] = msg["avlc"]["acars"].get("reg", "")
    dat["flight"] = msg["avlc"]["acars"].get("flight", "")
    dat["msgtype"] = msg["avlc"]["acars"].get("label", "")
    dat["txt"] = msg["avlc"]["acars"].get("msg_text", "")
  elif not (msg["avlc"].get("xid") is None or msg["avlc"]["xid"].get("vdl_params") is None):
    dat["squawk"] = 4000
    dat["msgtype"] = "xid"
    dat["xid"] = True
    dat["icao"] = msg["avlc"]["src"]["addr"]
    for p in msg["avlc"]["xid"]["vdl_params"]:
      if p["name"] == "ac_location":
        dat["lat"] = p["value"]["loc"]["lat"]
        dat["lon"] = p["value"]["loc"]["lon"]
        print(f"got VDLM2 with XID pos {dat['lat']} {dat['lon']}")
  return dat

acdb = {}
regdb = {}
def decodeHFDL(msg):
  if not msg.get("lpdu"):
    if not msg.get("spdu"):
      pprint(msg)
      print("hfdl bad top level key")
    return None
#  if not msg["lpdu"].get("hfnpdu"):
#    pprint(msg)
#    print("hfdl no keys")
#    return None
  dat = {}
  dat["squawk"] = 5000
  dat["type"] = "hfdl"
  dat["time"] = int(msg["t"]["sec"])
  dat["flight"] = msg["lpdu"].get("hfnpdu", {}).get("flight_id", "")
  dat["freq"] = int(msg.get("freq", 0))
  try:
    dat["lat"] = msg["lpdu"]["hfnpdu"]["pos"]["lat"]
    dat["lon"] = msg["lpdu"]["hfnpdu"]["pos"]["lon"]
    dat["msgtype"] = "hfdl"
    dat["squawk"] = 6000
    if dat["lat"] == 180 and dat["lon"] == 180:
      return None
  except:
    pass
  if msg["lpdu"].get("hfnpdu", {}).get("acars"):
    dat["reg"] = msg["lpdu"]["hfnpdu"]["acars"]["reg"]
    dat["flight"] = msg["lpdu"]["hfnpdu"]["acars"].get("flight", "")
    dat["txt"] = msg["lpdu"]["hfnpdu"]["acars"]["msg_text"]
    dat["msgtype"] = msg["lpdu"]["hfnpdu"]["acars"]["label"]

  dat["id"] = msg["lpdu"]["src"]["id"]
  dat["msgtype"] = msg["lpdu"]["type"]["id"]
  if dat["msgtype"] == 191 or dat["msgtype"] == 79:
#    pprint(msg["lpdu"]["ac_info"])
    dat["icao"] = msg["lpdu"]["ac_info"].get("icao", "")
    dat["reg"] = msg["lpdu"]["ac_info"].get("regnr", "")
    regdb[dat["flight"]] = {"icao": dat["icao"], "reg": dat["reg"]}
    print(f"hfdl logon req/res {dat['flight']} {regdb[dat['flight']]}")
  elif dat["msgtype"] == 159:
#    pprint(msg["lpdu"]["ac_info"])
    dat["id"] = msg["lpdu"]["assigned_ac_id"]
    dat["icao"] = msg["lpdu"]["ac_info"].get("icao", "")
    dat["reg"] = msg["lpdu"]["ac_info"].get("regnr", "")
    acdb[dat["id"]] = {"icao": dat["icao"], "reg": dat["reg"], "flight": dat["flight"]}
    print(f"hfdl logon confirm {dat['id']} {acdb[dat['id']]}")
  else:
    if acdb.get(dat["id"]):
#      print(f"hfdl ac in db: {dat['id']}")
      dat["reg"] = acdb[dat["id"]]["reg"]
      dat["icao"] = acdb[dat["id"]]["icao"]
    elif regdb.get(dat["flight"]):
#      print(f"hfdl ac in reg db: {dat['flight']}")
      dat["reg"] = regdb[dat["flight"]]["reg"]
      dat["icao"] = regdb[dat["flight"]]["icao"]
    else:
#      pprint(msg)
#      print(f"hfdl ac not in db: {dat['id']} {dat['flight']}")
      return None
  return dat
