from re import search

def decode(msg):
  if msg.get("vdl2"):
    dat = decodeVDLM2(msg["vdl2"])
  elif msg.get("hfdl"):
    dat = decodeHFDL(msg["hfdl"])
  else:
    dat = decodeACARS(msg)

  if dat is None or dat.get("msgtype") is None:
    return dat

  if dat["msgtype"] == "10":
    if raw := search(r"([NS]) ?(\d{2}\.\d{3})[,\/]([WE]) ?(\d{2,3}\.\d{3})", dat["txt"]):
      print("matched type 10")
      print(dat["txt"])
      print()
      dat["lat"] = float(raw.group(2)) * (-1 if raw.group(1) == "S" else 1)
      dat["lon"] = float(raw.group(4)) * (-1 if raw.group(1) == "W" else 1)
  elif dat["msgtype"] == "4N":
    if raw := search(r"([NS])(\d{3})(\d{3}) ([WE])(\d{3})(\d{3})", dat["txt"]):
      print("matched type 4N")
      print(dat["txt"])
      print()
      dat["lat"] = (int(raw.group(2)) + int(raw.group(3))/600) * (-1 if raw.group(1) == "S" else 1)
      dat["lon"] = (int(raw.group(5)) + int(raw.group(6))/600) * (-1 if raw.group(4) == "W" else 1)
  elif dat["msgtype"] == "4T":
    if raw := search(r"(\d{2})(\d{2}\.\d{1})([NS])[ 0](\d{2})(\d{2}\.\d{1})([WE])", dat["txt"]):
      print("matched type 4T")
      print(dat["txt"])
      print()
      dat["lat"] = (int(raw.group(1)) + float(raw.group(2))/60) * (-1 if raw.group(3) == "S" else 1)
      dat["lon"] = (int(raw.group(4)) + float(raw.group(5))/60) * (-1 if raw.group(6) == "W" else 1)
  elif dat["msgtype"] == "21":
    if raw := search(r"([NS]) (\d{2}\.\d{3})([WE]) (\d{2}\.\d{3})", dat["txt"]):
      print("matched type 21")
      print(dat["txt"])
      print()
      dat["lat"] = float(raw.group(2)) * (-1 if raw.group(1) == "S" else 1)
      dat["lon"] = float(raw.group(4)) * (-1 if raw.group(3) == "W" else 1)
  elif dat["msgtype"] == "80" or dat["msgtype"] == "83":
    if raw := search(r"[NS](\d{2})(\d{2}\.\d{1})[WE](\d{3)(\d{2}}\.\d{1})", dat["txt"]):
      print("matched type 80/83")
      print(dat["txt"])
      print()
      dat["lat"] = (int(raw.group(2)) + float(raw.group(3))/60) * (-1 if raw.group(1) == "S" else 1)
      dat["lon"] = (int(raw.group(5)) + float(raw.group(6))/60) * (-1 if raw.group(4) == "W" else 1)
  elif dat["msgtype"] == "16":
    if raw := search(r"([NS]) (\d{2}\.\d{3})[ ,]([WE])\s{0,2}(\d{1,3}\.\d{3})", dat["txt"]):
      print("matched type 16 frac deg")
      print(dat["txt"])
      print()
      dat["lat"] = float(raw.group(2)) * (-1 if raw.group(1) == "S" else 1)
      dat["lon"] = float(raw.group(4)) * (-1 if raw.group(3) == "W" else 1)
    elif raw := search(r"([NS])(\d{2})(\d{2}\.\d{2}) ([WE])\s{0,2}(\d{1,3}) ?(\d{1,2}\.\d{2})", dat["txt"]):
      print("matched type 16 frac min")
      print(dat["txt"])
      print()
      dat["lat"] = (int(raw.group(2)) + float(raw.group(3))/60) * (-1 if raw.group(1) == "S" else 1)
      dat["lon"] = (int(raw.group(5)) + float(raw.group(6))/60) * (-1 if raw.group(4) == "W" else 1)
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
