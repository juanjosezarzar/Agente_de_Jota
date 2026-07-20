import os
import sys
import json
from instagrapi import Client

print("=== Instagram Session Helper ===")
sessionid = input("Paste your sessionid cookie here: ").strip()

if not sessionid:
    print("Error: sessionid cannot be empty.")
    sys.exit(1)

session_path = "session.json"

# Base template
data = {
    "uuids": {
        "phone_id": "e5afd6ff-47a5-4cc9-8b7c-c3db883a43f4",
        "uuid": "86e3d5fa-66a1-4683-9383-fd4290f4f854",
        "client_session_id": "2841c3be-5167-44ae-89e9-1ecdf16d2f21",
        "advertising_id": "cca00ab0-d316-45f2-95e7-03402a79e06d",
        "android_device_id": "android-662907740cc51722",
        "request_id": "8406298c-b89b-4e4d-b7f6-1e56bdc0d278",
        "tray_session_id": "0f413240-24eb-4bf3-9547-c2a32ccd03bc"
    },
    "mid": None,
    "ig_u_rur": None,
    "ig_www_claim": None,
    "authorization_data": {
        "ds_user_id": "64201218575",
        "sessionid": sessionid,
        "should_use_header_over_cookies": True
    },
    "cookies": {
        "ds_user_id": "64201218575",
        "sessionid": sessionid
    },
    "last_login": None,
    "device_settings": {
        "android_version": 26,
        "android_release": "8.0.0",
        "dpi": "480dpi",
        "resolution": "1080x1920",
        "manufacturer": "OnePlus",
        "device": "devitron",
        "model": "6T Dev",
        "cpu": "qcom",
        "app_version": "385.0.0.47.74",
        "version_code": "378906843",
        "bloks_versioning_id": "a8973d49a9cc6a6f65a4997c10216ce2a06f65a517010e64885e92029bb19221"
    },
    "user_agent": "Instagram 385.0.0.47.74 Android (26/8.0.0; 480dpi; 1080x1920; OnePlus; 6T Dev; devitron; qcom; en_US; 378906843)",
    "country": "US",
    "country_code": 1,
    "locale": "en_US",
    "timezone_offset": -14400,
    "request_timeout": 1,
    "public_request_retries_count": 3,
    "public_request_retries_timeout": 2,
    "session_retry_total": 3,
    "session_retry_backoff_factor": 2,
    "session_retry_statuses": [429, 500, 502, 503, 504]
}

with open(session_path, "w") as f:
    json.dump(data, f, indent=4)

print("\nSaved locally to session.json.")

# Test it
cl = Client()
try:
    cl.load_settings(session_path)
    print("Testing session validity...")
    info = cl.user_info_v1(cl.user_id)
    print(f"Success! Session is valid for @{info.username}")
    
    # Print instructions and the JSON
    print("\n" + "="*50)
    print("INSTRUCTIONS TO UPDATE GITHUB SECRETS:")
    print("1. Go to your GitHub repository.")
    print("2. Go to Settings -> Secrets and variables -> Actions.")
    print("3. Click Edit on 'INSTAGRAM_SESSION_SETTINGS'.")
    print("4. Replace the entire content with the JSON below:")
    print("="*50)
    print(json.dumps(data, indent=4))
    print("="*50)
except Exception as e:
    print(f"Error validating the new sessionid: {str(e)}")
    print("Please make sure you copied the correct sessionid and that you are logged in on your browser.")
