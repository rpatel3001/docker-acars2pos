from re import compile, sub
from colorama import Fore

rgxs = [compile(r"([NS])[ 0]{0,2}(\d{1,2}\.\d{3}).?([WE])[0 ]{0,2}(\d{1,3}\.\d{3})"),
        compile(r"([NS])[ 0]{0,1}(\d{1,2})[ 0]{0,1}(\d{1,2}\.\d{1}).?([WE])[ 0]{0,2}(\d{1,3}?)[ 0]{0,1}(\d{1,2}\.\d{1})"),
        compile(r"([NS])[ 0]{0,1}(\d{1,2})[ 0]{0,3}(\d{0,2}\.\d{2}).?([WE])[ 0]{0,2}(\d{1,3})[ 0]{0,1}(\d{1,2}\.\d{2})"),
        compile(r"([NS])\s?(\d{2})(\d{2})(\d{2}).?([WE])\s?(\d{2,3})(\d{2})(\d{2})"),
        compile(r"([NS])[ 0]?([ 0\d]\d)(\d{3}).?([WE])([ 0\d][ 0\d]\d)(\d{3})"),
        compile(r"[0 ]{0,1}(\d{1,2})[0 ]{0,1}(\d{1,2}\.\d{1})([NS])[ 0]{0,2}(\d{1,3})[0 ]{0,1}(\d{1,2}\.\d{1})([WE])"),
        compile(r"[ 0]{0,1}(\d{1,2})[ 0]{0,1}(\d{1,2})([NS])[ 0]{0,2}(\d{1,3})[ 0]{0,1}(\d{1,2})([WE])"),
        compile(r"LAT ([NS]) [0 ]{0,1}(\d{1,2}):(\d{2}\.\d{1})  LONG [WE] [0 ]{0,1}(\d{1,2}):(\d{2}\.\d{1})")]

def decode(msg):
  if msg.get("vdl2"):
    dat = decodeVDLM2(msg["vdl2"])
  elif msg.get("hfdl"):
    dat = decodeHFDL(msg["hfdl"])
  else:
    dat = decodeACARS(msg)

  if dat and dat.get("msgtype") == "4N":
    rgx = compile(r"([NS])(\d{3})(\d{3}) ([WE])(\d{3})(\d{3})")
    raw = rgx.findall(dat["txt"])
    if len(raw) == 1:
      pos = dat["txt"]
      for pat in raw[0]:
        pos = sub(f"({pat})", Fore.GREEN + r"\1" + Fore.RESET, pos)
      print(f"matched message type {dat['msgtype']}")
      print(pos)
      raw = rgx.search(dat["txt"])
      dat["lat"] = (int(raw.group(2)) + int(raw.group(3))/600) * (-1 if raw.group(1) == "S" else 1)
      dat["lon"] = (int(raw.group(5)) + int(raw.group(6))/600) * (-1 if raw.group(4) == "W" else 1)

  if dat and not dat.get("lat"):
    dat["txt"] = dat.get("txt", "").upper().replace("\r", "").replace("\n", "")
    for i,rgx in enumerate(rgxs):
      raw = rgx.findall(dat["txt"])
      if len(raw) == 1:
        pos = dat["txt"]
        for pat in raw[0]:
          pos = sub(f"({pat})", Fore.RED + r"\1" + Fore.RESET, pos)
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
