import os
import zipfile
import json
import esprima
import csv
from collections import defaultdict

# 분석할 JavaScript API 리스트
API_LIST = [
    "fetch", "XMLHttpRequest", "navigator.sendBeacon", "new WebSocket",
    "FileReader.readAsText", "FileReader.readAsDataURL", "FileReader.readAsArrayBuffer",
    "document.createElement", "document.appendChild", "document.cookie",
    "navigator.clipboard.readText", "navigator.clipboard.writeText",
    "chrome.webRequest.onBeforeRequest.addListener", "chrome.identity.getAuthToken"
]

# 변수 추적을 위한 딕셔너리
variable_map = {}

# ZIP 압축 해제
def extract_zip(zip_path, extract_to):
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(extract_to)

# JavaScript 파일 AST 분석
def analyze_js_file(file_path):
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()
    
    try:
        tree = esprima.parseScript(content, tolerant=True)
    except Exception:
        return {}

    api_counts = defaultdict(int)

    # AST 노드 순회하며 API 호출 탐지
    for node in tree.body:
        if isinstance(node, esprima.nodes.ExpressionStatement):
            expr = node.expression
            if isinstance(expr, esprima.nodes.CallExpression):
                func_name = extract_function_name(expr)
                if func_name in API_LIST:
                    api_counts[func_name] += 1
    
    return api_counts

# AST에서 함수명 추출
def extract_function_name(expr):
    if isinstance(expr.callee, esprima.nodes.Identifier):
        return expr.callee.name
    elif isinstance(expr.callee, esprima.nodes.MemberExpression):
        return extract_member_expression(expr.callee)
    return None

# Member Expression 추출 (예: document.createElement)
def extract_member_expression(expr):
    if isinstance(expr.object, esprima.nodes.Identifier) and isinstance(expr.property, esprima.nodes.Identifier):
        return f"{expr.object.name}.{expr.property.name}"
    return None

# manifest.json 분석 (permissions 추출)
def analyze_manifest(manifest_path):
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)
    return manifest.get("permissions", [])

# ZIP 파일 분석
def analyze_extension(zip_path, output_csv):
    extract_dir = zip_path.replace(".zip", "")
    extract_zip(zip_path, extract_dir)

    api_counts = defaultdict(int)
    permissions = []

    # 폴더 내 파일 탐색
    for root, _, files in os.walk(extract_dir):
        for file in files:
            file_path = os.path.join(root, file)
            if file.endswith(".js"):
                file_api_counts = analyze_js_file(file_path)
                for api, count in file_api_counts.items():
                    api_counts[api] += count
            elif file == "manifest.json":
                permissions = analyze_manifest(file_path)

    # CSV 파일 저장
    with open(output_csv, "a", newline="") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow([zip_path, api_counts, permissions])

    # 결과 출력
    print(f"\n[Analysis Completed] {zip_path}")
    print(f"API Counts: {dict(api_counts)}")
    print(f"Permissions: {permissions}")


#batch_analyzer.py
#import os
#from analyzer_extension import analyzer_extension

INPUT_FOLDER = "/home/minhyuk/Desktop/Download_extension/other"  # ZIP 파일이 있는 폴더
OUTPUT_CSV = "extension_analysis.csv"

# 모든 ZIP 파일 분석 실행
def batch_analyze():
    with open(OUTPUT_CSV, "w", newline="") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["File", "API Counts", "Permissions"])

    for file in os.listdir(INPUT_FOLDER):
        if file.endswith(".zip"):
            zip_path = os.path.join(INPUT_FOLDER, file)
            analyze_extension(zip_path, OUTPUT_CSV)

batch_analyze()


