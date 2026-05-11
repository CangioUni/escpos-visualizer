from app import parse_escpos
import json

data = bytearray()
data.extend(b'\x1b!\x10') # Double height
data.extend(b'Double Height\n')
data.extend(b'\x1b!\x20') # Double width
data.extend(b'Double Width\n')
data.extend(b'\x1b!\x30') # Double height and width
data.extend(b'Double Both\n')

# Cut commands
data.extend(b'\x1dV\x00') # GS V m=0
data.extend(b'\x1dV\x41\x00') # GS V m=65 n=0
data.extend(b'\x1bi') # ESC i
data.extend(b'\x1bm') # ESC m

print(json.dumps(parse_escpos(data), indent=2))
