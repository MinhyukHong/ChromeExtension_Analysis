import os
import zipfile
import json
import csv
import esprima
from collections import defaultdict

# **📌 API 카테고리별 목록**
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

# **📌 API 이름 → 카테고리 매핑**
API_TO_CATEGORY = {api: category for category, apis in API_CATEGORIES.items() for api in apis}

# **📌 변수 추적을 위한 딕셔너리**
variable_map = {}

# **📌 ZIP 압축 해제**
def extract_zip(zip_path, extract_to):
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(extract_to)

# **📌 AST에서 변수 추적**
def track_variables(node):
    """ 변수 선언 및 할당 추적 (API가 변수에 저장되는 경우) """
    if node.type == "VariableDeclaration":
        for decl in node.declarations:
            if decl.id.type == "Identifier" and decl.init is not None:
                var_name = decl.id.name
                assigned_func = extract_function_name(decl.init)
                if assigned_func and assigned_func in API_TO_CATEGORY:
                    variable_map[var_name] = assigned_func  # 변수 → API 매핑

# **📌 AST에서 함수명 추출**
def extract_function_name(expr):
    """ 함수명 추출 (document.createElement 등 감지) """
    if expr.type == "Identifier":  # fetch(), setTimeout() 같은 단일 함수
        return variable_map.get(expr.name, expr.name)  # 변수 치환 추적
    elif expr.type == "MemberExpression":  # document.createElement, navigator.clipboard.readText
        obj = extract_function_name(expr.object)
        prop = extract_function_name(expr.property)
        if obj and prop:
            return f"{obj}.{prop}"
    return None

# **📌 AST 트리 전체 탐색하여 API 호출 감지**
def analyze_ast_recursively(node, api_counts):
    """ 재귀적으로 AST를 탐색하여 API 호출 감지 """
    if isinstance(node, list):
        for child in node:
            analyze_ast_recursively(child, api_counts)
    elif isinstance(node, dict):
        for key, value in node.items():
            analyze_ast_recursively(value, api_counts)
    elif hasattr(node, "type"):  # AST 노드인 경우
        if node.type == "CallExpression":  # 함수 호출 감지
            func_name = extract_function_name(node.callee)
            if func_name in API_TO_CATEGORY:
                category = API_TO_CATEGORY[func_name]
                api_counts[category][func_name] += 1
        elif node.type == "VariableDeclaration":  # 변수 추적
            track_variables(node)

        # 노드 내부 탐색 (재귀)
        for attr in dir(node):
            if not attr.startswith("_"):  # 내부 속성 제외
                analyze_ast_recursively(getattr(node, attr), api_counts)

# **📌 JavaScript 파일 AST 분석**
def analyze_js_file(file_path):
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()

    try:
        tree = esprima.parseScript(content, tolerant=True)
    except Exception:
        return defaultdict(lambda: defaultdict(int))

    api_counts = defaultdict(lambda: defaultdict(int))

    # **AST 트리 전체 탐색**
    analyze_ast_recursively(tree, api_counts)

    return api_counts

# **📌 manifest.json 분석 (permissions 추출)**
def analyze_manifest(manifest_path):
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)
    return manifest.get("permissions", [])

# **📌 ZIP 파일 분석**
def analyze_extension(zip_path, output_csv):
    extract_dir = zip_path.replace(".zip", "")
    extract_zip(zip_path, extract_dir)

    global variable_map
    variable_map = {}  # 변수 맵 초기화
    api_counts = defaultdict(lambda: defaultdict(int))
    permissions = []

    # 폴더 내 파일 탐색
    for root, _, files in os.walk(extract_dir):
        for file in files:
            file_path = os.path.join(root, file)
            if file.endswith(".js"):
                file_api_counts = analyze_js_file(file_path)
                for category, apis in file_api_counts.items():
                    for api, count in apis.items():
                        api_counts[category][api] += count
            elif file == "manifest.json":
                permissions = analyze_manifest(file_path)

    # CSV 파일 저장
    with open(output_csv, "a", newline="") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow([zip_path, json.dumps(api_counts), permissions])

    # 결과 출력
    print(f"\n[Analysis Completed] {zip_path}")
    print(f"API Counts: {json.dumps(api_counts, indent=2)}")
    print(f"Permissions: {permissions}")

# **📌 여러 개의 ZIP 파일을 자동으로 분석**
def batch_analyze(input_folder, output_csv):
    with open(output_csv, "w", newline="") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["File", "API Counts", "Permissions"])

    for file in os.listdir(input_folder):
        if file.endswith(".zip"):
            zip_path = os.path.join(input_folder, file)
            analyze_extension(zip_path, output_csv)

# **실행 예시**
if __name__ == "__main__":
    INPUT_FOLDER = "/Users/choohimchan/Downloads/Lab"  # ZIP 파일이 있는 폴더
    OUTPUT_CSV = "extension_analysis.csv"
    
    batch_analyze(INPUT_FOLDER, OUTPUT_CSV)

