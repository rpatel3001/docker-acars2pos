import fcntl
import locale
import os

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
