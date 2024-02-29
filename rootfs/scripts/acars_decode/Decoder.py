from re import compile, sub
from colorama import Fore


dlat = r"(?P<dlat>[NS])"
dlon = r"(?P<dlon>[WE])"

spdig2 = r"(?:\s|\d)\d"
spdig3 = r"(?:\s\s|\s\d|\d\d)\d"

dig1 = r"\d"
dig2 = r"\d\d"
dig3 = r"\d\d\d"


def name(n, rgx):
  return f"(?P<{n}>{rgx})"

def sd2(n):
  return name(n, spdig2)

def sd3(n):
  return name(n, spdig3)

def d1(n):
  return name(n, dig1)

def d2(n):
  return name(n, dig2)

def d3(n):
  return name(n, dig3)


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
         "10": [compile(dlat + " " + sd2("latdeg") + "\." + d3("latdeg1000") + "\/" + dlon + sd3("londeg") + "\." + d3("londeg1000"))],
         "14": [compile(dlat + sd2("latdeg") + d2("latmin") + d1("latmin10") + dlon + sd3("londeg") + d2("lonmin") + d1("lonmin10"))],
         "15": [compile(dlat + sd2("latdeg") + d2("latmin") + d1("latmin10") + dlon + sd3("londeg") + d2("lonmin") + d1("lonmin10")),
                compile(dlat + sd2("latdeg") + d2("latmin") + d2("latsec") + dlon + sd3("londeg") + d2("lonmin") + d2("lonsec"))],
         "4T": [compile(d2("latdeg") + d2("latmin") + r"\." + d1("latmin10") + dlat + d3("londeg") + d2("lonmin") + r"\." + d1("lonmin10") + dlon)],
         }

def decode(msg):
  if msg.get("vdl2"):
    dat = decodeVDLM2(msg["vdl2"])
  elif msg.get("hfdl"):
    dat = decodeHFDL(msg["hfdl"])
  else:
    dat = decodeACARS(msg)

  if not dat:
    return None

  dat["txt"] = dat.get("txt", "").upper().replace("\r", "").replace("\n", "")

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
        dat["lat"] =  float(raw.get("latdeg", 0))
        dat["lat"] += float(raw.get("lat1000", 0))/1000
        dat["lat"] += float(raw.get("latmin", 0))/60
        dat["lat"] += float(raw.get("latmin10", 0))/600
        dat["lat"] += float(raw.get("latmin100", 0))/6000
        dat["lat"] += float(raw.get("latsec", 0))/3600
        dat["lat"] *= -1 if raw.get("dlat") == "S" else 1

        dat["lon"] =  float(raw.get("londeg", 0))
        dat["lon"] += float(raw.get("lon1000", 0))/1000
        dat["lon"] += float(raw.get("lonmin", 0))/60
        dat["lon"] += float(raw.get("lonmin10", 0))/600
        dat["lon"] += float(raw.get("lonmin100", 0))/6000
        dat["lon"] += float(raw.get("lonsec", 0))/3600
        dat["lon"] *= -1 if raw.get("dlon") == "W" else 1

      if dat.get("lat") and abs(dat["lat"]) <= 90 and abs(dat["lon"]) <= 180 :
        break

  if not dat.get("lat"):
    for i,rgx in enumerate(rgxs):
      raw = rgx.findall(dat["txt"])
      if len(raw) == 1:
        pos = rgx.sub(Fore.RED + r"\g<0>" + Fore.RESET, dat["txt"])
        print(f"regex {i} matched message type {dat['msgtype']}")
        print(pos)

        raw = rgx.search(dat["txt"])
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

      if dat.get("lat") and abs(dat["lat"]) <= 90 and abs(dat["lon"]) <= 180 :
        break

  return dat

def decodeACARS(msg):
  if msg.get("text") is None or msg["label"] == "SQ":
    return None
  dat = {}
  dat["type"] = "acars"
  dat["reg"] = msg["tail"]
  dat["time"] = int(msg["timestamp"])
  dat["flight"] = msg.get("flight", "")
  dat["txt"] = msg["text"]
  dat["msgtype"] = msg["label"]
  return dat

def decodeVDLM2(msg):
  if msg.get("avlc") is None:
    return None
  elif (msg["avlc"].get("acars") is None or msg["avlc"]["acars"].get("msg_text") is None) and (msg["avlc"].get("xid") is None or msg["avlc"]["xid"].get("vdl_params") is None):
    return None
  dat = {}
  dat["type"] = "vdlm2"
  dat["time"] = int(msg["t"]["sec"])
  if not (msg["avlc"].get("acars") is None or msg["avlc"]["acars"].get("msg_text") is None):
    dat["reg"] = msg["avlc"]["acars"]["reg"]
    dat["flight"] = msg["avlc"]["acars"]["flight"]
    dat["msgtype"] = msg["avlc"]["acars"]["label"]
    dat["txt"] = msg["avlc"]["acars"]["msg_text"]
  elif not (msg["avlc"].get("xid") is None or msg["avlc"]["xid"].get("vdl_params") is None):
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
  dat["type"] = "hfdl"
  dat["time"] = int(msg["t"]["sec"])
  dat["flight"] = msg["lpdu"].get("hfnpdu", {}).get("flight_id", "")
  try:
    dat["lat"] = msg["lpdu"]["hfnpdu"]["pos"]["lat"]
    dat["lon"] = msg["lpdu"]["hfnpdu"]["pos"]["lon"]
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
