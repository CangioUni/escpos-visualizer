import socket
import threading
import io
import base64
from flask import Flask, render_template
from flask_socketio import SocketIO
from PIL import Image

app = Flask(__name__)
# 'threading' mode + simple-websocket is the stable path for Python 3.13
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

def parse_escpos(data):
    lines = []
    current_line = {"type": "text", "content": "", "bold": False, "align": "left", "dh": False, "dw": False}
    i = 0
    
    while i < len(data):
        char = data[i]

        # DLE EOT (Real-time status request) - responded to by socket handler, skip here
        if char == 0x10 and i + 2 < len(data) and data[i+1] == 0x04:
            i += 3
            continue

        # GS v 0 (Raster bit image)
        if char == 0x1D and i + 7 < len(data) and data[i+1] == 0x76 and data[i+2] == 0x30:
            width_bytes = data[i+4] + (data[i+5] * 256)
            height_dots = data[i+6] + (data[i+7] * 256)
            data_size = width_bytes * height_dots
            i += 8
            
            img_data = data[i : i + data_size]
            if len(img_data) == data_size:
                try:
                    img = Image.frombytes('1', (width_bytes * 8, height_dots), img_data, 'raw', '1;I')
                    buf = io.BytesIO()
                    img.save(buf, format='PNG')
                    b64_str = base64.b64encode(buf.getvalue()).decode('utf-8')
                    lines.append({"type": "image", "content": b64_str, "align": current_line["align"]})
                except Exception as e:
                    print(f"Bitmap error: {e}")
                i += data_size
            continue

        # GS V (Cut)
        elif char == 0x1D and i + 1 < len(data) and data[i+1] == 0x56:
            if current_line["content"]:
                lines.append(dict(current_line))
                current_line["content"] = ""

            m = data[i+2] if i + 2 < len(data) else 0
            if m == 0 or m == 1 or m == 48 or m == 49:
                i += 3
            elif m == 65 or m == 66:
                i += 4
            else:
                i += 2

            lines.append({"type": "cut"})
            continue

        # ESC commands
        elif char == 0x1B:
            i += 1
            if i < len(data):
                cmd = data[i]
                if cmd == 0x21: # ESC ! n
                    n = data[i+1]
                    current_line["bold"] = bool(n & 8)
                    current_line["dh"] = bool(n & 16)
                    current_line["dw"] = bool(n & 32)
                    i += 1
                elif cmd == 0x61: # ESC a n
                    n = data[i+1]
                    align_map = {0: "left", 1: "center", 2: "right"}
                    current_line["align"] = align_map.get(n, "left")
                    i += 1
                elif cmd == 0x69 or cmd == 0x6D: # ESC i or ESC m (Cut)
                    if current_line["content"]:
                        lines.append(dict(current_line))
                        current_line["content"] = ""
                    lines.append({"type": "cut"})
        elif char == 0x0A: # LF
            if current_line["content"]:
                lines.append(dict(current_line))
                current_line["content"] = ""
        else:
            if 32 <= char <= 126 or char > 128:
                current_line["content"] += chr(char)
        i += 1
    
    if current_line["content"]:
        lines.append(current_line)
    return lines

# Response byte for all real-time status requests (DLE EOT n):
# 0x12 = paper present, printer online, no errors ("paper ok")
_PAPER_OK_STATUS = bytes([0x12])

def start_printer_server():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    # Listens on all interfaces for printer data
    server.bind(('0.0.0.0', 9100))
    server.listen(5)
    print("Printer Socket: 0.0.0.0:9100")
    
    while True:
        client, _ = server.accept()
        try:
            raw_data = bytearray()
            pending = bytearray()  # buffer for partial DLE EOT sequences spanning chunks
            while True:
                chunk = client.recv(4096)
                if not chunk:
                    break

                buf = pending + bytearray(chunk)
                pending = bytearray()
                i = 0

                while i < len(buf):
                    if buf[i] == 0x10:  # DLE — potential real-time status request
                        if i + 1 >= len(buf):
                            pending.extend(buf[i:])
                            break
                        if buf[i + 1] == 0x04:  # EOT
                            if i + 2 >= len(buf):
                                pending.extend(buf[i:])
                                break
                            # Respond with "paper ok" status regardless of n (1-4)
                            client.send(_PAPER_OK_STATUS)
                            i += 3  # skip DLE EOT n
                        else:
                            raw_data.append(buf[i])
                            i += 1
                    else:
                        raw_data.append(buf[i])
                        i += 1

            # Any incomplete DLE sequence at EOF is treated as regular data
            raw_data.extend(pending)

            if raw_data:
                parsed_bill = parse_escpos(raw_data)
                socketio.emit('new_bill', {'bill': parsed_bill, 'raw': raw_data.hex()})
        except Exception as e:
            print(f"Socket error: {e}")
        finally:
            client.close()

@app.route('/')
def index():
    return render_template('index.html')

if __name__ == '__main__':
    threading.Thread(target=start_printer_server, daemon=True).start()
    # Host 0.0.0.0 makes the web UI accessible on your network
    socketio.run(app, host='0.0.0.0', port=5050, debug=False, allow_unsafe_werkzeug=True)