import fcntl
import locale
import os
import sqlite3 as sql

from icao_nnumber_converter_us import n_to_icao


enc = locale.getpreferredencoding(False)

def sock2lines(f):
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

_db = sql.connect("/opt/basestation/BaseStation.sqb")
_cur = _db.cursor()
def reg2icao(reg):
  icao = None
  res = _cur.execute("SELECT ModeS FROM Aircraft WHERE Registration == ?", (reg,)).fetchall()
  if len(res) > 0:
    icao = res[0][0]
  if icao is None:
    icao = n_to_icao(reg)
#if icao is None:
#  UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0"
#  URL = f"https://www.flightradar24.com/data/aircraft/{sbs['reg']}"
#  page = requests.get(URL, headers={"User-Agent": UA})
#  icao = BeautifulSoup(page.content, "html.parser").find(id="txt-mode-s").contents[0].strip()
  return icao

def icao2reg(icao):
  reg = ""
  res = _cur.execute("SELECT Registration FROM Aircraft WHERE ModeS == ?", (icao,)).fetchall()
  if len(res) > 0:
    reg = res[0][0]
  return reg
