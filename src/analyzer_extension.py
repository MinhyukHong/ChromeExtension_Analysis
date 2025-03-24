import os
import zipfile
import json
import re
import random
import csv
from collections import defaultdict

# 📌 API 카테고리별 목록 정의
API_CATEGORIES = {
    "File System": [
        "document.querySelector('input[type=\"file\"]')", "file.name", "file.type", "file.size",
        "file.lastModified", "new Blob", "FileReader.readAsText", "FileReader.readAsDataURL",
        "FileReader.readAsArrayBuffer", "window.requestFileSystem", "fileEntry.createWriter",
        "indexedDB.open", "indexedDB.transaction", "store.put", "localStorage.setItem",
        "localStorage.getItem", "sessionStorage.setItem", "sessionStorage.getItem", "document.cookie",
        "navigator.clipboard.readText", "navigator.clipboard.writeText"
    ],
    "Network": [
        "fetch", "new XMLHttpRequest", "new WebSocket", "navigator.sendBeacon",
        "new RTCPeerConnection", "chrome.webRequest.onBeforeRequest.addListener",
        "chrome.webRequest.onHeadersReceived.addListener", "chrome.identity.getAuthToken",
        "chrome.proxy.settings.set", "chrome.dns.resolve"
    ],
    "Rendering": [
        "document.createElement", "document.appendChild", "element.innerHTML",
        "document.querySelector", "document.getElementById", "element.style",
        "new MutationObserver", "chrome.tabs.executeScript", "setTimeout",
        "setInterval", "canvas.getContext", "CanvasRenderingContext2D.drawImage",
        "document.designMode", "shadowRoot.attachShadow", "window.open",
        "chrome.windows.create", "chrome.tabs.create", "chrome.notifications.create"
    ],
    "User Interaction": [
        "addEventListener", "document.onmousemove", "document.onkeypress",
        "document.onkeydown", "window.onbeforeunload", "chrome.contextMenus.create",
        "chrome.alarms.create", "chrome.notifications.onClicked.addListener",
        "chrome.permissions.request", "chrome.tabs.onActivated.addListener",
        "window.alert", "window.confirm", "window.prompt"
    ],
    "Storage": [
        "chrome.storage.local.get", "chrome.storage.local.set",
        "chrome.storage.sync.get", "chrome.storage.sync.set"
    ],
    "Device": [
        "navigator.geolocation.getCurrentPosition", "navigator.geolocation.watchPosition",
        "navigator.mediaDevices.getUserMedia", "navigator.mediaDevices.enumerateDevices"
    ],
    "Security": [
        "chrome.permissions.request", "chrome.identity.getAuthToken",
        "chrome.privacy.network.webRTCIPHandlingPolicy"
    ]
}

# API -> Category 매핑
API_TO_CATEGORY = {api: category for category, apis in API_CATEGORIES.items() for api in apis}

# 권한별 필요한 API 매핑
PERMISSION_TO_APIS = {
    "bookmarks": ["chrome.bookmarks.*"],
    "clipboardRead": ["navigator.clipboard.readText", "document.execCommand('paste')"],
    "clipboardWrite": ["navigator.clipboard.writeText", "document.execCommand('copy')"],
    "tabs": ["chrome.tabs.*"],
    "cookies": ["chrome.cookies.*"],
    "downloads": ["chrome.downloads.*"],
    "history": ["chrome.history.*"],
    "management": ["chrome.management.*"],
    "webRequest": ["chrome.webRequest.*"],
    "webRequestBlocking": ["chrome.webRequest.onBeforeRequest.addListener"],
    "nativeMessaging": ["chrome.runtime.connectNative", "chrome.runtime.sendNativeMessage"],
    "proxy": ["chrome.proxy.settings.*"],
    "geolocation": ["navigator.geolocation.getCurrentPosition"],
    "storage": ["chrome.storage.*"]
}

SAMPLE_RESULTS = []

# 📌 API 검출
def extract_apis(content):
    found_apis = defaultdict(int)
    for api in API_TO_CATEGORY.keys():
        matches = re.findall(re.escape(api), content)
        if matches:
            found_apis[api] += len(matches)
    return found_apis

# 📌 manifest.json에서 permissions 추출 및 API 매칭
def extract_permissions(content):
    try:
        manifest = json.loads(content)
        permissions = set(manifest.get("permissions", []))
        matched_apis = set()

        for perm, apis in PERMISSION_TO_APIS.items():
            if perm in permissions:
                matched_apis.update(apis)

        return list(permissions), list(matched_apis)
    except json.JSONDecodeError:
        return [], []

# 📌 ZIP 파일 내 파일 검사
def analyze_zip(zip_path):
    api_counts = defaultdict(lambda: defaultdict(int))
    permissions, matched_apis = [], []
    wasm_exist = "X"

    try:
        with zipfile.ZipFile(zip_path, 'r') as z:
            for name in z.namelist():
                if name.startswith("__MACOSX/") or name.startswith("._"):
                    continue
                if name.endswith(".wasm"):
                    wasm_exist = "O"

                if not (name.endswith(".js") or name.endswith(".json")):
                    continue

                with z.open(name) as f:
                    content = f.read().decode("utf-8", errors="ignore")
                    if "manifest.json" in name:
                        permissions, matched_apis = extract_permissions(content)
                    else:
                        found_apis = extract_apis(content)
                        for api, count in found_apis.items():
                            category = API_TO_CATEGORY[api]
                            api_counts[category][api] += count

    except zipfile.BadZipFile:
        print(f"Failed to open zip file: {zip_path}")

    # ✅ `unmatched_permissions` 수정
    matched_permissions = {perm for perm, apis in PERMISSION_TO_APIS.items() if any(api in matched_apis for api in apis)}
    unmatched_permissions = list(set(permissions) - matched_permissions)

    SAMPLE_RESULTS.append({
        "zip": os.path.basename(zip_path),
        "permissions": permissions,
        "matched_apis": matched_apis,
        "unmatched_permissions": unmatched_permissions,
        "wasm_exist": wasm_exist,
        "api_counts": api_counts
    })

# 📌 CSV 저장
def save_to_csv():
    categories = list(API_CATEGORIES.keys())

    with open("summary.csv", "w", newline="") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["Category", "API", "Count"])

        total_counts = defaultdict(lambda: defaultdict(int))
        for result in SAMPLE_RESULTS:
            for category, apis in result["api_counts"].items():
                for api, count in apis.items():
                    total_counts[category][api] += count

        for category, apis in total_counts.items():
            for api, count in sorted(apis.items(), key=lambda x: x[1], reverse=True):
                writer.writerow([category, api, count])

    with open("detailed_analysis.csv", "w", newline="") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["ZIP File", "Permissions", "Matched APIs", "Unmatched Permissions", "WASM Exist"] + categories)

        for result in SAMPLE_RESULTS:
            row = [
                result["zip"],
                json.dumps(result["permissions"]),
                json.dumps(result["matched_apis"]),
                json.dumps(result["unmatched_permissions"]),
                result["wasm_exist"]
            ]
            for category in categories:
                sorted_counts = sorted(result["api_counts"][category].items(), key=lambda x: x[1], reverse=True)
                row.append(json.dumps({api: count for api, count in sorted_counts}))
            writer.writerow(row)

# 📌 실행
def sampling_analyze(folder_path):
    extensions = [os.path.join(folder_path, f) for f in os.listdir(folder_path) if f.endswith(".zip")]
    sampled_extensions = random.sample(extensions, min(500, len(extensions)))
    
    for ext in sampled_extensions:
        analyze_zip(ext)

    save_to_csv()

if __name__ == "__main__":
    import sys
    sampling_analyze(sys.argv[1])

