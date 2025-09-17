import requests, json, time, os, signal
from datetime import datetime, timedelta

# 🔐 OAuth credentials
CLIENT_ID = "737936576743-5dq4nrm7gemrhcks9k4rj5jb0i1futqh.apps.googleusercontent.com"
CLIENT_SECRET = "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"
REFRESH_TOKEN = "1//04SZPj0Na1xgFCgYIARAAGAQSNwF-L9IrvlAvyrcEU5z2rVto6skNdq9MgFjQUAIPA7zfdJ6yhnT3zz77EpVEmXPCU7gWnSviCzo"
ACCESS_TOKEN = "ya29.a0AS3H6Nxk4L6qLjkxisU4QEfSvFFU3PyzNL5XFNRL1ZYhp1OLa4yVTavEeNTfjytwMJ4njQSVugnW-5sOV-araEOTpvUwxMDwXcuYc81YYoDVMXCchNMi2r98q-ztaCU4lnmvy4Ml1clfVqciuZY1KylSHTKkVlYEDVLrZXToexW4w4i97eElucopHsJ5GtdbVRtX34waCgYKAcUSARMSFQHGX2MimISWb5_lv3XIgKWZcpPozg0206"

# 📄 Sheet setup
SHEET_PREFIX = "UHBVN_hr0_"
STATE_FILE = "sheet_state.json"
INSTANCE_ID = f"Instance_{int(time.time())}"

# 🔄 Refresh access token
def refresh_access_token():
    global ACCESS_TOKEN
    token_url = "https://oauth2.googleapis.com/token"
    payload = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "refresh_token": REFRESH_TOKEN,
        "grant_type": "refresh_token"
    }
    res = requests.post(token_url, data=payload)
    if res.status_code == 200:
        ACCESS_TOKEN = res.json()["access_token"]
        print("🔄 Token refreshed.")
    else:
        print("❌ Token refresh failed:", res.text)

# 📦 Load sheet ID from Git file
def load_sheet_id():
    if not os.path.exists(STATE_FILE):
        return None
    try:
        with open(STATE_FILE, "r") as f:
            data = json.load(f)
            return data.get("sheet_id")
    except Exception as e:
        print("⚠️ Failed to read sheet_state.json:", e)
        return None

# 💾 Save sheet ID to Git file
def save_sheet_id(sheet_id):
    data = {
        "sheet_id": sheet_id,
        "created": datetime.utcnow().isoformat() + "Z"
    }
    with open(STATE_FILE, "w") as f:
        json.dump(data, f, indent=2)

# 🔍 Find sheet by name
def find_sheet_by_name(sheet_name):
    url = "https://www.googleapis.com/drive/v3/files"
    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}"}
    params = {
        "q": f"name='{sheet_name}' and mimeType='application/vnd.google-apps.spreadsheet'",
        "fields": "files(id, name)",
        "spaces": "drive",
        "corpora": "user"
    }
    res = requests.get(url, headers=headers, params=params)
    if res.status_code == 200:
        files = res.json().get("files", [])
        if files:
            return files[0]["id"]
    return None

# ✅ Create or get sheet
def create_or_get_sheet():
    refresh_access_token()

    sheet_id = load_sheet_id()
    if sheet_id:
        print(f"📄 Using existing sheet: {sheet_id}")
        return sheet_id

    sheet_name = f"{SHEET_PREFIX}{datetime.now().strftime('%Y%m%d_%H%M')}"
    sheet_id = find_sheet_by_name(sheet_name)
    if sheet_id:
        print(f"📄 Found existing sheet: {sheet_id}")
        save_sheet_id(sheet_id)
        return sheet_id

    url = "https://sheets.googleapis.com/v4/spreadsheets"
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    body = {"properties": {"title": sheet_name}}
    res = requests.post(url, headers=headers, data=json.dumps(body))
    if res.status_code == 200:
        sheet_id = res.json()["spreadsheetId"]
        print(f"📄 Sheet created: {sheet_id}")
        save_sheet_id(sheet_id)
        write_headers(sheet_id)
        return sheet_id
    else:
        print("❌ Sheet creation failed:", res.text)
        return None

# 📝 Write headers
def write_headers(sheet_id):
    url = f"https://sheets.googleapis.com/v4/spreadsheets/{sheet_id}/values/Sheet1!A1:append"
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    params = {"valueInputOption": "RAW"}
    data = {"values": [["timestamp (IST)", "instance_id", "utc_time"]]}
    requests.post(url, headers=headers, params=params, data=json.dumps(data))

# 🕒 Write timestamp + metadata
def write_log(sheet_id):
    ist_time = datetime.utcnow() + timedelta(hours=5, minutes=30)
    utc_time = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    ist_str = ist_time.strftime("%Y-%m-%d %H:%M:%S")

    url = f"https://sheets.googleapis.com/v4/spreadsheets/{sheet_id}/values/Sheet1!A2:append"
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    params = {"valueInputOption": "RAW"}
    data = {"values": [[ist_str, INSTANCE_ID, utc_time]]}
    res = requests.post(url, headers=headers, params=params, data=json.dumps(data))
    if res.status_code == 200:
        print(f"🕒 Logged: {ist_str}")
    else:
        print("❌ Log failed:", res.text)

# 🚀 Main loop
def main():
    sheet_id = create_or_get_sheet()
    if not sheet_id:
        print("❌ No sheet available. Exiting.")
        return

    while True:
        write_log(sheet_id)
        time.sleep(30)

main()
