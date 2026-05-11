from app import parse_escpos
import json

data = bytearray()
data.extend(b'\x1dV\x00') # GS V m=0
data.extend(b'Test') # Should be "Test"

print(json.dumps(parse_escpos(data), indent=2))
