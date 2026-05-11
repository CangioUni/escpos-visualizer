import socket
import time

data = bytearray()

data.extend(b'\x1b!\x00')
data.extend(b'123456789012345678901234567890123456789012345678\n') # 48 chars exactly
data.extend(b'1234567890123456789012345678901234567890123456789\n') # 49 chars (should wrap)
data.extend(b'Normal Text Line 1\n')
data.extend(b'\x1b!\x10') # Double height
data.extend(b'Double Height Line\n')
data.extend(b'\x1b!\x20') # Double width
data.extend(b'Double Width Line\n')
data.extend(b'\x1b!\x30') # Double height and width
data.extend(b'Double Both Line\n')
data.extend(b'\x1b!\x00')
data.extend(b'Normal Text Line 2\n')

# Cut commands
data.extend(b'\x1dV\x00') # GS V m=0

try:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect(('127.0.0.1', 9100))
    s.sendall(data)
    s.close()
    print("Sent test bill")
except Exception as e:
    print("Failed to send:", e)
