import os
import zipfile
import json
import re
import random
import csv
from collections import defaultdict

# **📌 API 카테고리별 목록 정의**
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
    ]
}

API_TO_CATEGORY = {api: category for category, apis in API_CATEGORIES.items() for api in apis}
API_COUNTS = defaultdict(lambda: defaultdict(int))
SAMPLE_RESULTS = []  # 샘플별 결과 저장

# **📌 API 카운트 증가 (전역 API_COUNTS 업데이트)**
def add_api_count(api_name):
    category = API_TO_CATEGORY.get(api_name)
    if category:
        API_COUNTS[category][api_name] += 1

# **📌 API 검출 (전역 API_COUNTS 업데이트)**
def extract_apis(content):
    for api in API_TO_CATEGORY.keys():
        matches = re.findall(re.escape(api), content)
        for _ in matches:
            add_api_count(api)

# **📌 manifest.json에서 permissions 추출**
def extract_permissions(content):
    try:
        manifest = json.loads(content)
        return manifest.get("permissions", [])
    except json.JSONDecodeError:
        return []

# **📌 ZIP 파일 내 파일 검사**
def analyze_zip(zip_path):
    api_counts = defaultdict(lambda: defaultdict(int))
    permissions = []
    try:
        with zipfile.ZipFile(zip_path, 'r') as z:
            for name in z.namelist():
                if name.startswith("__MACOSX/") or name.startswith("._"):
                    continue
                if not (name.endswith(".js") or name.endswith(".json") or "manifest.json" in name):
                    continue

                with z.open(name) as f:
                    content = f.read().decode("utf-8", errors="ignore")
                    if "manifest.json" in name:
                        permissions = extract_permissions(content)
                    else:
                        for api in API_TO_CATEGORY:
                            matches = re.findall(re.escape(api), content)
                            for _ in matches:
                                category = API_TO_CATEGORY[api]
                                api_counts[category][api] += 1
                                add_api_count(api)  # ✅ 전역 API_COUNTS 업데이트
                print(f"Analyzing file: {name}")
    except zipfile.BadZipFile:
        print(f"Failed to open zip file: {zip_path}")
    
    SAMPLE_RESULTS.append({
        "zip": os.path.basename(zip_path),
        "permissions": permissions,
        "api_counts": api_counts
    })

# **📌 CSV 저장 (통합 통계 + 상세 분석)**
def save_to_csv():
    # 통합 통계 저장
    if API_COUNTS:  # ✅ 비어있지 않은 경우만 저장
        with open("summary.csv", "w", newline="") as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(["Category", "API", "Count"])
            for category, apis in API_COUNTS.items():
                for api, count in sorted(apis.items(), key=lambda x: x[1], reverse=True):
                    writer.writerow([category, api, count])
        print("Saved summary to summary.csv")
    else:
        print("No API usage found, summary.csv not created.")

    # 샘플별 상세 분석 저장
    with open("detailed_analysis.csv", "w", newline="") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["ZIP File", "Permissions", "File System", "Network", "Rendering", "User Interaction"])
        for result in SAMPLE_RESULTS:
            row = [
                result["zip"],
                json.dumps(result["permissions"])
            ]
            for category in ["File System", "Network", "Rendering", "User Interaction"]:
                sorted_counts = sorted(result["api_counts"][category].items(), key=lambda x: x[1], reverse=True)
                row.append(json.dumps({api: count for api, count in sorted_counts}))
            writer.writerow(row)
    print("Saved detailed analysis to detailed_analysis.csv")

# **📌 API 분석 결과 출력 (카테고리별)**
def print_api_results():
    print("\n=== API Usage Summary ===")
    for category, apis in API_COUNTS.items():
        print(f"\n[{category}]")
        for api, count in sorted(apis.items(), key=lambda x: x[1], reverse=True):
            print(f"{api}: {count}")

# **📌 실행 진입점**
def sampling_analyze(folder_path):
    extensions = get_extension_list(folder_path)
    if len(extensions) < 500:
        print(f"ZIP files are under 500 ({len(extensions)} found)")
        return

    random.seed()
    sampled_extensions = random.sample(extensions, 500)

    print("\n[List of Extensions after sampling]\n")
    for idx, ext in enumerate(sampled_extensions, start=1):
        print(f"{idx}. {ext}")
        analyze_zip(ext)

    print_api_results()
    save_to_csv()

# **📌 Extension ZIP 파일 리스트를 가져옴**
def get_extension_list(folder_path):
    return [os.path.join(folder_path, f) for f in os.listdir(folder_path) if f.endswith(".zip")]

# **📌 실행 진입점**
if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <Folder that includes ZIP files>")
        sys.exit(1)

    sampling_analyze(sys.argv[1])

