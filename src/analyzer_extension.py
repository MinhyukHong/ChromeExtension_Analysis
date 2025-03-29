import os
import zipfile
import json
import re
import random
import csv
from collections import defaultdict

# 📌 API 카테고리별 목록 정의 (기존 유지)
API_CATEGORIES = {
    "File System": [
        "document.querySelector", "file.name", "file.type", "file.size",
        "file.lastModified", "new Blob", "FileReader.readAsText", "FileReader.readAsDataURL",
        "FileReader.readAsArrayBuffer", "window.requestFileSystem", "fileEntry.createWriter",
        "indexedDB.open", "indexedDB.transaction", "store.put", "localStorage.setItem",
        "localStorage.getItem", "sessionStorage.setItem", "sessionStorage.getItem", "document.cookie",
        "navigator.clipboard.readText", "navigator.clipboard.writeText",
        "Element.requestPointerLock", # pointerLock 관련
    ],
    "Network": [
        "fetch", "new XMLHttpRequest", "new WebSocket", "navigator.sendBeacon",
        "new RTCPeerConnection", "chrome.webRequest.onBeforeRequest.addListener",
        "chrome.webRequest.onHeadersReceived.addListener", "chrome.identity.getAuthToken",
        "chrome.proxy.settings.set", "chrome.dns.resolve",
        "chrome.mdns.onServiceList", # mdns 관련
        "chrome.signedInDevices.get", # signedInDevices 관련
    ],
    "Rendering": [
        "document.createElement", "document.appendChild", "element.innerHTML",
        "document.getElementById", "element.style",
        "new MutationObserver", "chrome.tabs.executeScript", "setTimeout",
        "setInterval", "canvas.getContext", "CanvasRenderingContext2D.drawImage",
        "document.designMode", "shadowRoot.attachShadow", "window.open",
        "chrome.windows.create", "chrome.tabs.create", "chrome.notifications.create",
        "chrome.declarativeContent.onPageChanged", # declarativeContent 관련
    ],
    "User Interaction": [
        "addEventListener", "document.onmousemove", "document.onkeypress",
        "document.onkeydown", "window.onbeforeunload", "chrome.contextMenus.create",
        "chrome.alarms.create", "chrome.notifications.onClicked.addListener",
        "chrome.permissions.request", "chrome.tabs.onActivated.addListener",
        "window.alert", "window.confirm", "window.prompt",
        "chrome.input.ime.onFocus", # input (IME) 관련
        "chrome.fileBrowserHandler.onExecute", # fileBrowserHandler 관련
    ],
    "Storage": [
        "chrome.storage.local.get", "chrome.storage.local.set",
        "chrome.storage.sync.get", "chrome.storage.sync.set",
    ],
    "Device": [
        "navigator.geolocation.getCurrentPosition", "navigator.geolocation.watchPosition",
        "navigator.mediaDevices.getUserMedia", "navigator.mediaDevices.enumerateDevices",
        "chrome.usb.findDevices", # usb 관련
        "chrome.hid.getDevices", # hid 관련
        "chrome.serial.getDevices", # serial 관련
        "chrome.documentScan.scan", # documentScan 관련
    ],
    "Security": [
        "chrome.permissions.request", "chrome.identity.getAuthToken",
        "chrome.privacy.network.webRTCIPHandlingPolicy",
        "chrome.enterprise.deviceAttributes.getDirectoryDeviceId", # enterprise 관련
        "chrome.enterprise.platformKeys.getToken", # enterprise 관련
        "chrome.platformKeys.selectClientCertificates", # platformKeys 관련
        "chrome.certificateProvider.requestPin", # certificateProvider 관련
    ],
    "System": [
         "chrome.system.cpu.getInfo",
         "chrome.system.display.getInfo",
         "chrome.system.memory.getInfo",
         "chrome.system.storage.getInfo",
         "chrome.system.network.getNetworkInterfaces", # system.network 관련
    ],
    # 추가된 API 카테고리 또는 기존 카테고리에 분배
    "File System Provider": [ # ChromeOS
        "chrome.fileSystemProvider.mount",
        "chrome.fileSystemProvider.onOpenFileRequested",
    ],
    "User Scripts": [
        "chrome.userScripts.register",
    ]
}

# API -> Category 매핑 (기존 유지)
API_TO_CATEGORY = {api: category for category, apis in API_CATEGORIES.items() for api in apis}

# 📌 권한별 필요한 API 매핑 (기존 유지)
PERMISSION_TO_APIS = {
    # User Choice / Activation
    "activeTab": ["chrome.scripting.*", "chrome.tabs.captureVisibleTab", "chrome.tabs.get", "chrome.tabs.update"],

    # Core Extension APIs
    "alarms": ["chrome.alarms.*"],
    "bookmarks": ["chrome.bookmarks.*"],
    "browsingData": ["chrome.browsingData.*"],
    "clipboardRead": ["navigator.clipboard.readText", "document.execCommand('paste')"],
    "clipboardWrite": ["navigator.clipboard.writeText", "document.execCommand('copy')", "document.execCommand('cut')", "navigator.clipboard.write"],
    "commands": ["chrome.commands.*"],
    "contentSettings": ["chrome.contentSettings.*"],
    "contextMenus": ["chrome.contextMenus.*"],
    "cookies": ["chrome.cookies.*"], # Host Permissions 필요
    "debugger": ["chrome.debugger.*"],
    "declarativeContent": ["chrome.declarativeContent.*"],
    "declarativeNetRequest": ["chrome.declarativeNetRequest.*"],
    "declarativeNetRequestWithHostAccess": ["chrome.declarativeNetRequest.*"], # Host Permissions 필요
    "declarativeNetRequestFeedback": ["chrome.declarativeNetRequest.*"],
    "desktopCapture": ["chrome.desktopCapture.*"],
    "downloads": ["chrome.downloads.*"], # downloads.open, downloads.ui는 이 권한 하위 API임
    "history": ["chrome.history.*"],
    "identity": ["chrome.identity.*"], # identity.email은 이 권한 하위 API 기능임
    "idle": ["chrome.idle.*"],
    "management": ["chrome.management.*"],
    "nativeMessaging": ["chrome.runtime.connectNative", "chrome.runtime.sendNativeMessage"],
    "notifications": ["chrome.notifications.*"],
    "offscreen": ["chrome.offscreen.*"],
    "pageCapture": ["chrome.pageCapture.*"],
    "permissions": ["chrome.permissions.*"], # 선택적 권한 관리
    "power": ["chrome.power.*"],
    "privacy": ["chrome.privacy.*"],
    "proxy": ["chrome.proxy.*"],
    "pushMessaging": ["chrome.pushMessaging.*", "PushManager.*"],
    "scripting": ["chrome.scripting.*"], # Host Permissions 또는 activeTab 필요
    "search": ["chrome.search.*"],
    "sessions": ["chrome.sessions.*"],
    "sidePanel": ["chrome.sidePanel.*"],
    "storage": ["chrome.storage.*"],
    "system.cpu": ["chrome.system.cpu.*"],
    "system.display": ["chrome.system.display.*"],
    "system.memory": ["chrome.system.memory.*"],
    "system.storage": ["chrome.system.storage.*"],
    "tabCapture": ["chrome.tabCapture.*"],
    "tabGroups": ["chrome.tabGroups.*"],
    "tabs": ["chrome.tabs.*"], # 민감 정보 접근 시 Host Permissions 또는 activeTab 필요
    "topSites": ["chrome.topSites.*"],
    "tts": ["chrome.tts.*"],
    "ttsEngine": ["chrome.ttsEngine.*"],
    "unlimitedStorage": ["chrome.storage.local", "indexedDB", "Cache API"],
    "webNavigation": ["chrome.webNavigation.*"], # Host Permissions 필요할 수 있음
    "webRequest": ["chrome.webRequest.*"], # MV3에서는 관찰만 가능, Host Permissions 필요

    # Newly Added / Reviewed Permissions
    "userScripts": ["chrome.userScripts.*"], # Host Permissions 필요
    "mdns": ["chrome.mdns.*"],
    "system.network": ["chrome.system.network.*"],
    "certificateProvider": ["chrome.certificateProvider.*"], # (ChromeOS)
    "documentScan": ["chrome.documentScan.*"], # (ChromeOS)
    "pointerLock": ["Element.requestPointerLock"], # (Web API)
    "signedInDevices": ["chrome.signedInDevices.*"],
    "usb": ["chrome.usb.*"], # (User Consent 필요)
    "hid": ["chrome.hid.*"], # (User Consent 필요)
    "serial": ["chrome.serial.*"], # (User Consent 필요)
    "input": ["chrome.input.ime.*"], # (IME)

    # Enterprise Specific (ChromeOS / Managed Env)
    "enterprise.deviceAttributes": ["chrome.enterprise.deviceAttributes.*"],
    "enterprise.hardwarePlatform": ["chrome.enterprise.hardwarePlatform.*"],
    "enterprise.networkingAttributes": ["chrome.enterprise.networkingAttributes.*"],
    "enterprise.platformKeys": ["chrome.enterprise.platformKeys.*"],
    "platformKeys": ["chrome.platformKeys.*"], # (ChromeOS, Non-Enterprise version)

    # ChromeOS Specific
    "fileBrowserHandler": ["chrome.fileBrowserHandler.*"],
    "fileSystemProvider": ["chrome.fileSystemProvider.*"],

    # Device Access
    "geolocation": ["navigator.geolocation.*"],

    # Deprecated
    "gcm": ["chrome.gcm.*"], # Deprecated, use pushMessaging
    "webRequestBlocking": ["chrome.webRequest.*"], # MV3에서는 declarativeNetRequest 사용
}


SAMPLE_RESULTS = []

# 📌 API 검출 (기존 유지)
def extract_apis(content):
    found_apis = defaultdict(int)
    for api in API_TO_CATEGORY.keys():
        try:
            count = content.count(api)
            if count > 0:
                found_apis[api] += count
        except Exception as e:
            print(f"Error counting API '{api}': {e}")
            continue
    return found_apis

# 📌 manifest.json에서 permissions 추출 및 API 매칭 (수정됨 - 하위 권한 처리 로직 추가)
def extract_permissions_and_apis(content):
    try:
        manifest = json.loads(content)
        permissions_in_manifest = set(manifest.get("permissions", []))
        host_permissions_in_manifest = set(manifest.get("host_permissions", []))

        all_permissions = list(permissions_in_manifest.union(host_permissions_in_manifest))

        # manifest에 선언된 permission 중 PERMISSION_TO_APIS 딕셔너리에 정의되지 않은 것들 찾기 (하위 권한 제외 로직 추가)
        known_defined_permissions = set(PERMISSION_TO_APIS.keys())
        unmatched_permissions = []

        # API 관련 권한만 필터링 (호스트 권한 패턴 제외)
        api_permissions_from_manifest = {p for p in permissions_in_manifest if not p.startswith(('<', 'http:', 'https:', '*:', 'file:'))}

        for p in api_permissions_from_manifest:
            is_known = False
            # 1. 정확히 일치하는지 확인
            if p in known_defined_permissions:
                is_known = True
            # 2. 정확히 일치하지 않고 '.'을 포함하는 경우, 상위 권한이 알려진 것인지 확인
            elif '.' in p:
                parent_p = p.split('.')[0]
                if parent_p in known_defined_permissions:
                    # 상위 권한이 정의되어 있으면 하위 항목도 알려진 것으로 간주
                    is_known = True
                    # print(f"Info: Permission '{p}' considered known because parent '{parent_p}' is defined.") # 디버깅용 로그

            # 알려지지 않은 경우에만 unmatched 리스트에 추가
            if not is_known:
                unmatched_permissions.append(p)

        return all_permissions, unmatched_permissions
    except json.JSONDecodeError:
        print("Warning: Failed to decode manifest.json")
        return [], []
    except Exception as e:
        print(f"Error processing manifest: {e}")
        return [], []


# 📌 ZIP 파일 내 파일 검사 (기존 유지)
def analyze_zip(zip_path):
    api_counts = defaultdict(lambda: defaultdict(int))
    permissions_from_manifest = []
    unmatched_permissions_from_manifest = []
    wasm_exist = "X"

    try:
        with zipfile.ZipFile(zip_path, 'r') as z:
            manifest_content = None
            for name in z.namelist():
                if name.startswith("__MACOSX/") or name.startswith("._") or name == ".DS_Store":
                    continue
                if name.lower().endswith("manifest.json"):
                    try:
                        with z.open(name) as f:
                            manifest_content = f.read().decode("utf-8", errors="ignore")
                            permissions_from_manifest, unmatched_permissions_from_manifest = extract_permissions_and_apis(manifest_content)
                            break
                    except Exception as e:
                         print(f"Error reading manifest {name} in {zip_path}: {e}")

            if manifest_content is None:
                 print(f"Warning: manifest.json not found in {zip_path}. Skipping analysis.")
                 return

            for name in z.namelist():
                if name.startswith("__MACOSX/") or name.startswith("._") or name == ".DS_Store" or name.lower().endswith("manifest.json"):
                    continue

                if name.endswith(".wasm"):
                    wasm_exist = "O"

                if name.endswith(".js"):
                    try:
                        with z.open(name) as f:
                            content = f.read().decode("utf-8", errors="ignore")
                            found_apis_in_file = extract_apis(content)
                            for api, count in found_apis_in_file.items():
                                category = API_TO_CATEGORY.get(api, "Unknown")
                                api_counts[category][api] += count
                    except Exception as e:
                        print(f"Error reading JS file {name} in {zip_path}: {e}")

    except zipfile.BadZipFile:
        print(f"Failed to open zip file (BadZipFile): {zip_path}")
        SAMPLE_RESULTS.append({
            "zip": os.path.basename(zip_path),
            "permissions": ["Error: BadZipFile"],
            "unmatched_permissions": [],
            "wasm_exist": "X",
            "api_counts": {}
        })
        return
    except Exception as e:
        print(f"An unexpected error occurred analyzing {zip_path}: {e}")
        SAMPLE_RESULTS.append({
            "zip": os.path.basename(zip_path),
            "permissions": [f"Error: {type(e).__name__}"],
            "unmatched_permissions": [],
            "wasm_exist": "X",
            "api_counts": {}
        })
        return

    SAMPLE_RESULTS.append({
        "zip": os.path.basename(zip_path),
        "permissions": permissions_from_manifest,
        "unmatched_permissions": unmatched_permissions_from_manifest,
        "wasm_exist": wasm_exist,
        "api_counts": dict(api_counts)
    })

# 📌 CSV 저장 (기존 유지)
def save_to_csv():
    categories = list(API_CATEGORIES.keys()) + ["Unknown"]

    with open("summary.csv", "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["Category", "API", "Total Count"])

        total_counts = defaultdict(lambda: defaultdict(int))
        for result in SAMPLE_RESULTS:
            if isinstance(result.get("api_counts"), dict):
                for category, apis in result["api_counts"].items():
                    for api, count in apis.items():
                        total_counts[category][api] += count

        all_apis_sorted = []
        for category, apis in total_counts.items():
            for api, count in apis.items():
                all_apis_sorted.append((category, api, count))

        all_apis_sorted.sort(key=lambda x: x[2], reverse=True)
        for category, api, count in all_apis_sorted:
             writer.writerow([category, api, count])

    with open("detailed_analysis.csv", "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow([
            "ZIP File", "Permissions (manifest)",
            "Unmatched Permissions (Unknown to script)",
            "WASM Exist"
        ] + categories)

        for result in SAMPLE_RESULTS:
            permissions_list = result.get("permissions", [])
            unmatched_list = result.get("unmatched_permissions", [])
            wasm_val = result.get("wasm_exist", "X")
            api_counts_dict = result.get("api_counts", {})

            row = [
                result.get("zip", "Unknown ZIP"),
                json.dumps(permissions_list, ensure_ascii=False),
                json.dumps(unmatched_list, ensure_ascii=False),
                wasm_val
            ]

            if not isinstance(api_counts_dict, dict):
                api_counts_dict = {}

            for category in categories:
                category_apis = api_counts_dict.get(category, {})
                sorted_counts = sorted(category_apis.items(), key=lambda x: x[1], reverse=True)
                row.append(json.dumps({api: count for api, count in sorted_counts}, ensure_ascii=False))
            writer.writerow(row)

# 📌 실행 (기존 유지)
def sampling_analyze(folder_path, sample_size=None):
    extensions = []
    for f in os.listdir(folder_path):
        if f.endswith(".zip") or f.endswith(".crx"):
            extensions.append(os.path.join(folder_path, f))

    if not extensions:
        print(f"No .zip or .crx files found in {folder_path}")
        return

    if sample_size is not None and sample_size > 0 and sample_size < len(extensions):
        sampled_extensions = random.sample(extensions, sample_size)
        print(f"Analyzing {len(sampled_extensions)} sampled extensions...")
    else:
        sampled_extensions = extensions
        print(f"Analyzing all {len(sampled_extensions)} extensions...")

    count = 0
    for ext_path in sampled_extensions:
        count += 1
        print(f"[{count}/{len(sampled_extensions)}] Analyzing: {os.path.basename(ext_path)}")
        analyze_zip(ext_path)

    if SAMPLE_RESULTS:
        print("Analysis complete. Saving results to CSV...")
        save_to_csv()
        print("CSV files saved: summary.csv, detailed_analysis.csv")
    else:
        print("Analysis completed, but no results were generated.")


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python your_script_name.py <path_to_extensions_folder> [sample_size]")
        print("       [sample_size] is optional. If omitted, all extensions are analyzed.")
        sys.exit(1)

    folder = sys.argv[1]
    size = None
    if len(sys.argv) > 2:
        try:
            size = int(sys.argv[2])
            if size <= 0:
                 print("Warning: Sample size must be positive. Analyzing all extensions.")
                 size = None
        except ValueError:
            print("Warning: Invalid sample size provided. Analyzing all extensions.")
            size = None

    if not os.path.isdir(folder):
        print(f"Error: Folder not found - {folder}")
        sys.exit(1)

    sampling_analyze(folder, size)
