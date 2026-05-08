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
    current_line = {"type": "text", "content": "", "bold": False, "align": "left", "size": 1}
    i = 0
    
    while i < len(data):
        char = data[i]
        
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

        # ESC commands
        elif char == 0x1B:
            i += 1
            if i < len(data):
                cmd = data[i]
                if cmd == 0x21: # ESC ! n
                    n = data[i+1]
                    current_line["bold"] = bool(n & 8)
                    current_line["size"] = 2 if (n & 16 or n & 32) else 1
                    i += 1
                elif cmd == 0x61: # ESC a n
                    n = data[i+1]
                    align_map = {0: "left", 1: "center", 2: "right"}
                    current_line["align"] = align_map.get(n, "left")
                    i += 1
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
            raw_data = client.recv(1024 * 1024) 
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