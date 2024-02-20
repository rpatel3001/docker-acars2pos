def decode(msg):
  if msg.get("vdl2"):
    dat = decodeVDLM2(msg["vdl2"])
  elif msg.get("hfdl"):
    dat = decodeHFDL(msg["hfdl"])
  else:
    dat = decodeACARS(msg)
  return dat

def decodeACARS(msg):
  if msg.get("text") is None or msg["label"] == "SQ":
    return None
  dat = {}
  dat["type"] = "acars"
  dat["reg"] = msg["tail"]
  dat["time"] = msg["timestamp"]
  dat["flight"] = msg.get("flight", "")
  dat["txt"] = msg["text"]
  dat["msgtype"] = msg["label"]
  return dat

def decodeVDLM2(msg):
  if msg.get("avlc") is None or msg["avlc"].get("acars") is None or msg["avlc"]["acars"].get("msg_text") is None:
    return None
  dat = {}
  dat["type"] = "vdlm2"
  dat["reg"] = msg["avlc"]["acars"]["reg"]
  dat["time"] = msg["t"]["sec"] + msg["t"]["usec"]/1e6
  dat["flight"] = msg["avlc"]["acars"]["flight"]
  dat["txt"] = msg["avlc"]["acars"]["msg_text"]
  dat["msgtype"] = msg["avlc"]["acars"]["label"]
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
  dat["time"] = msg["t"]["sec"] + msg["t"]["usec"]/1e6
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
