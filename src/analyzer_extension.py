import os
import zipfile
import json
import re # 단순 검색에는 필요 없지만, 나중을 위해 남겨둘 수 있음
import random
import csv
from collections import defaultdict
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# 📌 API 카테고리별 목록 정의 (summary.csv 용도 - 실제 코드 검색 패턴 포함)
# 이 목록은 extract_api_counts 함수에서 사용됨
API_CATEGORIES = {
    "Clipboard": [
        "navigator.clipboard.readText",
        "navigator.clipboard.writeText",
        "document.execCommand('paste')",
        "document.execCommand('copy')"
    ],
    "Downloads": [
        "chrome.downloads.download",
        "chrome.downloads.search",
        "chrome.downloads.open",
        "chrome.downloads.erase",
        "chrome.downloads.removeFile"
    ],
    "Storage": [
        "chrome.storage.local.get",
        "chrome.storage.local.set",
        "chrome.storage.sync.get",
        "chrome.storage.sync.set",
        "indexedDB.open",
        "localStorage.setItem",
        "sessionStorage.getItem",
        "navigator.storage.persist"
    ],
    "Tabs": [
        "chrome.tabs.create",
        "chrome.tabs.query",
        "chrome.tabs.update",
        "chrome.tabs.get",
        "chrome.tabs.remove",
        "chrome.tabs.executeScript",
        "chrome.tabs.onUpdated.addListener",
        "chrome.tabs.onActivated.addListener",
        "chrome.tabs.captureVisibleTab"
    ],
    "Scripting": [
        "chrome.scripting.executeScript",
        "chrome.scripting.insertCSS",
        "chrome.scripting.removeCSS",
        "chrome.scripting.registerContentScripts"
    ],
    "Identity": [
        "chrome.identity.getAuthToken",
        "chrome.identity.getProfileUserInfo",
        "chrome.identity.launchWebAuthFlow"
    ],
    "WebRequest": [
        "chrome.webRequest.onBeforeRequest",
        "chrome.webRequest.onHeadersReceived",
        "chrome.webRequest.onCompleted"
    ],
    "Bookmarks": [
        "chrome.bookmarks.create",
        "chrome.bookmarks.get",
        "chrome.bookmarks.search",
        "chrome.bookmarks.update",
        "chrome.bookmarks.remove"
    ],
    "History": [
        "chrome.history.search",
        "chrome.history.addUrl",
        "chrome.history.deleteUrl",
        "chrome.history.deleteAll"
    ],
    "Alarms": [
        "chrome.alarms.create",
        "chrome.alarms.get",
        "chrome.alarms.clear",
        "chrome.alarms.onAlarm.addListener"
    ],
    "Notifications": [
        "chrome.notifications.create",
        "chrome.notifications.update",
        "chrome.notifications.clear",
        "chrome.notifications.onClicked.addListener"
    ],
    "Context Menus": [
        "chrome.contextMenus.create",
        "chrome.contextMenus.update",
        "chrome.contextMenus.remove",
        "chrome.contextMenus.onClicked.addListener"
    ],
    "File System": [
        "document.querySelector",
        "file.name",
        "file.type",
        "file.size",
        "file.lastModified",
        "new Blob",
        "FileReader.readAsText",
        "FileReader.readAsDataURL",
        "FileReader.readAsArrayBuffer",
        "window.requestFileSystem",
        "fileEntry.createWriter",
        "indexedDB.transaction",
        "store.put",
        "localStorage.getItem",
        "sessionStorage.setItem",
        "document.cookie",
        "Element.requestPointerLock"
    ],
    "Network": [
        "fetch",
        "new XMLHttpRequest",
        "new WebSocket",
        "navigator.sendBeacon",
        "new RTCPeerConnection",
        "chrome.proxy.settings.set",
        "chrome.dns.resolve",
        "chrome.mdns.onServiceList",
        "chrome.signedInDevices.get"
    ],
    "Rendering": [
        "document.createElement",
        "document.appendChild",
        "element.innerHTML",
        "document.getElementById",
        "element.style",
        "new MutationObserver",
        "setTimeout",
        "setInterval",
        "canvas.getContext",
        "CanvasRenderingContext2D.drawImage",
        "document.designMode",
        "shadowRoot.attachShadow",
        "window.open",
        "chrome.windows.create",
        "chrome.declarativeContent.onPageChanged"
    ],
    "User Interaction": [
        "addEventListener",
        "document.onmousemove",
        "document.onkeypress",
        "document.onkeydown",
        "window.onbeforeunload",
        "chrome.permissions.request",
        "window.alert",
        "window.confirm",
        "window.prompt",
        "chrome.input.ime.onFocus",
        "chrome.fileBrowserHandler.onExecute"
    ]
}
# API 키워드 -> Category 매핑 (summary.csv 용도)
API_TO_CATEGORY = {api: category for category, apis in API_CATEGORIES.items() for api in apis}


# 📌 권한별 필요한 API 매핑 (검색 가능한 실제 API 패턴 위주로 정제)
# 키: Manifest에 선언되는 실제 권한 이름
# 값: 해당 권한 사용 시 코드에서 발견될 가능성이 높은 API 호출 패턴 (문자열) 리스트
PERMISSION_TO_APIS = {
    "activeTab": ["chrome.scripting.executeScript", "chrome.scripting.insertCSS", "chrome.tabs.captureVisibleTab"], # get/update는 tabs 권한과 겹침
    "alarms": ["chrome.alarms."], # Prefix 사용
    "bookmarks": ["chrome.bookmarks."],
    "browsingData": ["chrome.browsingData."],
    "clipboardRead": ["navigator.clipboard.readText", "document.execCommand('paste')"],
    "clipboardWrite": ["navigator.clipboard.writeText", "document.execCommand('copy')"],
    "commands": ["chrome.commands."],
    "contentSettings": ["chrome.contentSettings."],
    "contextMenus": ["chrome.contextMenus."],
    "cookies": ["chrome.cookies."], # Host Permissions 필요
    "debugger": ["chrome.debugger."],
    "declarativeContent": ["chrome.declarativeContent."],
    "declarativeNetRequest": ["chrome.declarativeNetRequest."],
    "declarativeNetRequestWithHostAccess": ["chrome.declarativeNetRequest."],
    "declarativeNetRequestFeedback": ["chrome.declarativeNetRequest."],
    "desktopCapture": ["chrome.desktopCapture."],
    "downloads": ["chrome.downloads."],
    "history": ["chrome.history."],
    "identity": ["chrome.identity."],
    "idle": ["chrome.idle."],
    "management": ["chrome.management."],
    "nativeMessaging": ["chrome.runtime.connectNative", "chrome.runtime.sendNativeMessage"],
    "notifications": ["chrome.notifications."],
    "offscreen": ["chrome.offscreen."],
    "pageCapture": ["chrome.pageCapture."],
    "permissions": ["chrome.permissions."],
    "power": ["chrome.power."],
    "privacy": ["chrome.privacy."],
    "processes": ["chrome.processes."],
    "proxy": ["chrome.proxy."],
    "pushMessaging": ["chrome.pushMessaging.", "PushManager."],
    "scripting": ["chrome.scripting."], # Host Permissions 또는 activeTab 필요
    "search": ["chrome.search."],
    "sessions": ["chrome.sessions."],
    "sidePanel": ["chrome.sidePanel."],
    "storage": ["chrome.storage."], # 기본적인 storage API
    "system.cpu": ["chrome.system.cpu."],
    "system.display": ["chrome.system.display."],
    "system.memory": ["chrome.system.memory."],
    "system.storage": ["chrome.system.storage."],
    "tabCapture": ["chrome.tabCapture."],
    "tabGroups": ["chrome.tabGroups."],
    "tabs": ["chrome.tabs."],
    "topSites": ["chrome.topSites."],
    "tts": ["chrome.tts."],
    "ttsEngine": ["chrome.ttsEngine."],
    # unlimitedStorage: 관련 스토리지 API 사용 시 제거 (아래 API들)
    "unlimitedStorage": ["chrome.storage.local.", "indexedDB.", "navigator.storage.persist", "CacheStorage.", "caches."],#기존 storage 10MB 이상
    "webNavigation": ["chrome.webNavigation."],
    "webRequest": ["chrome.webRequest."], # Listener 추가/제거가 주 사용 형태
    # Additional Permissions
    "userScripts": ["chrome.userScripts."],
    "mdns": ["chrome.mdns."],
    "system.network": ["chrome.system.network."],
    "certificateProvider": ["chrome.certificateProvider."],
    "documentScan": ["chrome.documentScan."],
    "pointerLock": ["requestPointerLock", "exitPointerLock"], # Element/document 메소드
    "signedInDevices": ["chrome.signedInDevices."],
    "usb": ["chrome.usb."],
    "hid": ["chrome.hid."],
    "serial": ["chrome.serial."],
    "input": ["chrome.input.ime."],
    "favicon": [], # 분석 대상 아님 (Known 처리용)
    # Enterprise Specific
    "enterprise.deviceAttributes": ["chrome.enterprise.deviceAttributes."],
    "enterprise.hardwarePlatform": ["chrome.enterprise.hardwarePlatform."],
    "enterprise.networkingAttributes": ["chrome.enterprise.networkingAttributes."],
    "enterprise.platformKeys": ["chrome.enterprise.platformKeys."],
    "platformKeys": ["chrome.platformKeys."],
    # ChromeOS Specific
    "fileBrowserHandler": ["chrome.fileBrowserHandler."],
    "fileSystemProvider": ["chrome.fileSystemProvider."],
    "loginState": ["chrome.loginState."],
    "printerProvider": ["chrome.printerProvider."],
    "vpnProvider": ["chrome.vpnProvider."],
    "webAuthenticationProxy": ["chrome.webAuthenticationProxy."],
    # Device Access
    "geolocation": ["navigator.geolocation."], # Prefix 사용
    # Deprecated
    "gcm": ["chrome.gcm."],
    "webRequestBlocking": ["chrome.webRequest."],

    "background": [],
}
# 모든 검색 대상 API 패턴 생성 (중복 제거)
ALL_SEARCH_PATTERNS = set()
for patterns in PERMISSION_TO_APIS.values():
    ALL_SEARCH_PATTERNS.update(p for p in patterns if p) # 빈 문자열 제외


SAMPLE_RESULTS = []

# 📌 API 사용 횟수 계산 함수 (summary.csv용)
def extract_api_counts(content):
    """주어진 content에서 API_CATEGORIES 키워드의 사용 횟수를 계산합니다."""
    counts = defaultdict(int)
    for api_keyword in API_TO_CATEGORY.keys(): # API_CATEGORIES의 키워드 사용
        try:
            count = content.count(api_keyword)
            if count > 0: counts[api_keyword] += count
        except Exception as e: logging.error(f"Error counting API '{api_keyword}': {e}"); continue
    return counts

# 📌 코드 내용에서 API 패턴 존재 여부 확인 함수 (Over-permission 분석용)
def extract_apis_from_content(content, search_patterns):
    """주어진 content에서 search_patterns 목록의 문자열이 하나라도 존재하는지 확인하고,
       존재하는 패턴들을 set으로 반환합니다."""
    found_patterns = set()
    # 모든 정의된 검색 패턴에 대해 반복
    for pattern in search_patterns:
        try:
            # 단순 문자열 포함 여부 확인 (find()와 유사)
            if pattern in content:
                found_patterns.add(pattern)
                logging.debug(f"Found pattern: {pattern}") # 디버깅 시 주석 해제
        except Exception as e:
            # 매우 긴 패턴이나 특수 문자가 많은 경우 오류 발생 가능성 있음
            logging.warning(f"Error searching for pattern '{pattern}': {e}")
            continue
    return found_patterns

# 📌 manifest.json에서 permissions 추출 함수 (Known API 권한만 필터링)
def extract_permissions_from_manifest(content):
    """Manifest에서 모든 권한 목록과, PERMISSION_TO_APIS에 정의된 알려진 API 권한 목록을 추출합니다."""
    all_declared_permissions = []
    declared_known_api_permissions = set()
    try:
        manifest = json.loads(content)
        permissions_in_manifest = set(manifest.get("permissions", []))
        host_permissions_in_manifest = set(manifest.get("host_permissions", []))
        all_declared_permissions = list(permissions_in_manifest.union(host_permissions_in_manifest))

        # 알려진 최상위 API 권한만 필터링 (PERMISSION_TO_APIS의 키와 비교)
        for perm in permissions_in_manifest:
            # 호스트 권한 아니고, PERMISSION_TO_APIS의 키에 존재하면 추가
            if not perm.startswith(('<', 'http:', 'https:', '*:', 'file:')) and perm in PERMISSION_TO_APIS:
                 # 'favicon' 같이 분석 안 할 권한은 제외할 수도 있음 (여기서는 일단 포함시키되, PERMISSION_TO_APIS 값이 비어있음)
                 declared_known_api_permissions.add(perm)

        return all_declared_permissions, declared_known_api_permissions
    except json.JSONDecodeError:
        logging.error("Failed to decode manifest.json")
        return [], set()
    except Exception as e:
        logging.error(f"Error processing manifest: {e}")
        return [], set()

# 📌 "API 패턴 -> 필요 권한" 매핑 생성 함수
def create_api_pattern_to_permission_map(permission_map):
    """PERMISSION_TO_APIS를 기반으로 역방향 매핑 생성"""
    api_to_perms = defaultdict(set)
    for permission, api_patterns in permission_map.items():
        # 빈 패턴 리스트(e.g., favicon)는 건너뛰기
        if not api_patterns:
            continue
        for pattern in api_patterns:
            if pattern: # 유효한 패턴만 추가
                api_to_perms[pattern].add(permission)
    logging.debug(f"API Pattern -> Permissions map created with {len(api_to_perms)} entries.")
    return api_to_perms

# 📌 ZIP 파일 내 파일 검사 (Over-permission 분석 로직)
def analyze_zip(zip_path, api_pattern_to_permission_map, all_search_patterns):
    """개별 ZIP 파일을 분석하여 Over-permission을 찾습니다."""
    declared_permissions_all = []
    declared_known_api_permissions = set()
    potential_over_permissions = set()
    found_api_patterns_in_code = set() # 전체 JS 파일에서 발견된 모든 API 패턴
    api_counts = defaultdict(lambda: defaultdict(int))
    wasm_exist = "X"
    manifest_found = False

    try:
        with zipfile.ZipFile(zip_path, 'r') as z:
            # 1단계: Manifest 읽기
            for name in z.namelist():
                if name.startswith("__MACOSX/") or name.startswith("._") or name == ".DS_Store": continue
                if name.lower().endswith("manifest.json"):
                    manifest_found = True
                    try:
                        with z.open(name) as f:
                            manifest_content = f.read().decode("utf-8", errors='replace')
                            declared_permissions_all, declared_known_api_permissions = extract_permissions_from_manifest(manifest_content)
                            potential_over_permissions = declared_known_api_permissions.copy() # 분석 시작점
                            logging.info(f"Manifest read for {os.path.basename(zip_path)}. Known API permissions to check: {declared_known_api_permissions}")
                            break
                    except Exception as e: logging.error(f"Error reading manifest {name} in {zip_path}: {e}")

            if not manifest_found:
                 logging.warning(f"manifest.json not found in {zip_path}. Cannot perform over-permission analysis.")
                 # Manifest 없으면 결과에 에러 표시하고 반환
                 SAMPLE_RESULTS.append({"zip": os.path.basename(zip_path), "permissions": ["Error: manifest.json not found"], "over_permissions": [], "wasm_exist": "X", "api_counts": {}})
                 return

            # 2단계: JS 코드 분석 및 API 패턴 추출
            logging.info(f"Scanning JS files in {os.path.basename(zip_path)}...")
            js_files_count = 0
            for name in z.namelist():
                if name.startswith("__MACOSX/") or name.startswith("._") or name == ".DS_Store" or name.lower().endswith("manifest.json"): continue
                if name.endswith(".wasm"): wasm_exist = "O"

                if name.endswith(".js"):
                    js_files_count += 1
                    logging.debug(f"Reading JS file: {name}")
                    try:
                        with z.open(name) as f:
                            # 파일을 한번에 읽음 (메모리 사용량 주의)
                            content = f.read().decode("utf-8", errors='replace')
                            if not content: # 빈 파일 스킵
                                logging.debug(f"Skipping empty JS file: {name}")
                                continue

                            # Over-permission 분석용 API 패턴 추출 (단순 포함 검색)
                            patterns_in_file = extract_apis_from_content(content, all_search_patterns)
                            if patterns_in_file:
                                logging.debug(f"API patterns found in {name}: {patterns_in_file}")
                                found_api_patterns_in_code.update(patterns_in_file) # 세트에 누적

                            # API 카운트 (부가 정보)
                            temp_api_counts = extract_api_counts(content)
                            for api, count in temp_api_counts.items():
                                category = API_TO_CATEGORY.get(api, "Unknown")
                                api_counts[category][api] += count
                    # 파일 읽기/디코딩 오류는 개별 파일에 대해 로깅하고 계속 진행
                    except UnicodeDecodeError as ude:
                        logging.warning(f"Unicode decode error in JS file {name}: {ude}. Skipping file content analysis.")
                    except Exception as e:
                        logging.error(f"Error reading or processing JS file {name} in {zip_path}: {e}")
            logging.info(f"Finished scanning {js_files_count} JS files. Total unique API patterns found: {len(found_api_patterns_in_code)}")
            logging.debug(f"All found API patterns: {found_api_patterns_in_code}")

            # 3단계: Over-permission 분석
            logging.info("Analyzing for over-permissions...")
            permissions_confirmed_used = set() # 이번 분석에서 사용된 것으로 확인된 권한

            # 발견된 모든 API 패턴에 대해 반복
            for found_pattern in found_api_patterns_in_code:
                # 이 패턴이 필요로 하는 권한들을 찾음
                required_permissions = api_pattern_to_permission_map.get(found_pattern, set())
                if required_permissions:
                    logging.debug(f"Pattern '{found_pattern}' requires permissions: {required_permissions}")
                    # 이 권한들이 원래 선언된 권한 목록에 있는지 확인
                    for req_perm in required_permissions:
                        if req_perm in declared_known_api_permissions: # potential_over_permissions 대신 원래 선언된 목록과 비교
                            permissions_confirmed_used.add(req_perm)
                            logging.debug(f"Confirmed usage for permission: {req_perm}")

            # 최종 Over-permission = (선언된 알려진 API 권한) - (사용된 것으로 확인된 권한)
            final_over_permissions = declared_known_api_permissions - permissions_confirmed_used
            logging.info(f"Over-permission analysis complete. Identified as potentially unused: {final_over_permissions}")


    except zipfile.BadZipFile:
        logging.error(f"Failed to open zip file (BadZipFile): {zip_path}")
        SAMPLE_RESULTS.append({"zip": os.path.basename(zip_path), "permissions": ["Error: BadZipFile"], "over_permissions": [], "wasm_exist": "X", "api_counts": {}})
        return
    except Exception as e:
        logging.error(f"An unexpected error occurred analyzing {zip_path}: {e}", exc_info=True)
        SAMPLE_RESULTS.append({"zip": os.path.basename(zip_path), "permissions": [f"Error: {type(e).__name__}"], "over_permissions": [], "wasm_exist": "X", "api_counts": {}})
        return

    # 최종 결과 저장
    SAMPLE_RESULTS.append({
        "zip": os.path.basename(zip_path),
        "permissions": declared_permissions_all, # Manifest의 모든 권한
        "over_permissions": sorted(list(final_over_permissions)), # 최종 Over-permission 목록
        "wasm_exist": wasm_exist,
        "api_counts": dict(api_counts)
    })


# 📌 CSV 저장 함수 (기존 유지)
def save_to_csv():
    # ...(이전과 동일)...
    categories = list(API_CATEGORIES.keys()) + ["Unknown"]
    with open("summary.csv", "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["Category", "API", "Total Count"])
        total_counts = defaultdict(lambda: defaultdict(int))
        for result in SAMPLE_RESULTS:
            if isinstance(result.get("api_counts"), dict):
                for category, apis in result["api_counts"].items():
                    for api, count in apis.items(): total_counts[category][api] += count
        all_apis_sorted = []
        for category, apis in total_counts.items():
            for api, count in apis.items(): all_apis_sorted.append((category, api, count))
        all_apis_sorted.sort(key=lambda x: x[2], reverse=True)
        for category, api, count in all_apis_sorted: writer.writerow([category, api, count])

    with open("detailed_analysis.csv", "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow([
            "ZIP File", "Permissions (manifest)", "Over Permissions", "WASM Exist"
        ] + categories)
        for result in SAMPLE_RESULTS:
            permissions_list = result.get("permissions", [])
            over_permissions_list = result.get("over_permissions", [])
            wasm_val = result.get("wasm_exist", "X")
            api_counts_dict = result.get("api_counts", {})
            row = [
                result.get("zip", "Unknown ZIP"),
                json.dumps(permissions_list, ensure_ascii=False, sort_keys=True),
                json.dumps(over_permissions_list, ensure_ascii=False, sort_keys=True),
                wasm_val
            ]
            if not isinstance(api_counts_dict, dict): api_counts_dict = {}
            for category in categories:
                category_apis = api_counts_dict.get(category, {})
                sorted_counts = sorted(category_apis.items(), key=lambda x: x[1], reverse=True)
                row.append(json.dumps({api: count for api, count in sorted_counts}, ensure_ascii=False))
            writer.writerow(row)


# 📌 실행 부분
def sampling_analyze(folder_path, sample_size=None):
    # 분석 시작 전, 필요한 매핑 생성
    api_pattern_to_permission_map = create_api_pattern_to_permission_map(PERMISSION_TO_APIS)
    # 모든 검색 대상 패턴 미리 준비
    all_search_patterns = set(p for patterns in PERMISSION_TO_APIS.values() for p in patterns if p)

    extensions = []
    for f in os.listdir(folder_path):
        if f.endswith(".zip") or f.endswith(".crx"):
            extensions.append(os.path.join(folder_path, f))

    if not extensions: logging.warning(f"No .zip or .crx files found in {folder_path}"); return

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
        logging.info(f"Starting analysis for: {os.path.basename(ext_path)}")
        # analyze_zip 호출 시 필요한 매핑 전달
        analyze_zip(ext_path, api_pattern_to_permission_map, all_search_patterns)
        logging.info(f"Finished analysis for: {os.path.basename(ext_path)}")

    if SAMPLE_RESULTS:
        print("Analysis complete. Saving results to CSV...")
        save_to_csv()
        print("CSV files saved: summary.csv, detailed_analysis.csv")
    else:
        print("Analysis completed, but no results were generated.")

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2: print("Usage: python ... <folder> [sample_size]"); sys.exit(1)
    folder = sys.argv[1]; size = None
    if len(sys.argv) > 2:
        try: size = int(sys.argv[2]);
        except ValueError: size = None
        if size is not None and size <= 0: size = None
    if not os.path.isdir(folder): print(f"Error: Folder not found - {folder}"); sys.exit(1)
    sampling_analyze(folder, size)
