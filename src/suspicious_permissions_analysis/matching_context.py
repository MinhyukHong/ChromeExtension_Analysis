import pandas as pd
import requests

CHROME_STATS_API = "https://chrome-stats.com/api/detail?id={extension_id}"
API_KEY = ""  # ChromeStats API Key

# 분석할 고위험 권한 목록
suspicious_permissions = [
    "webRequest", "webRequestBlocking", "clipboardRead", "clipboardWrite",
    "nativeMessaging", "proxy", "debugger", "downloads", "management", 
    "history", "cookies", "bookmarks"
]

# 권한 관련 키워드
context_keywords = {
    "webRequest": ["network", "traffic", "request"],
    "clipboardRead": ["clipboard", "copy", "paste"],
    "clipboardWrite": ["clipboard", "copy", "paste"],
    "nativeMessaging": ["native", "host", "external", "desktop"],
    "proxy": ["vpn", "proxy", "ip"],
    "debugger": ["debug", "devtool"],
    "downloads": ["download", "file", "pdf"],
    "management": ["extension management", "enable", "disable"],
    "history": ["history", "visit log"],
    "cookies": ["cookie", "session", "login"],
    "bookmarks": ["bookmark", "save page"]
}

def fetch_extension_info(extension_id):
    try:
        headers = {"x-api-key": API_KEY}
        url = CHROME_STATS_API.format(extension_id=extension_id)
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        print(f"[!] Error fetching info for {extension_id}: {e}")
    return None

def is_permission_contextual(text, permission):
    keywords = context_keywords.get(permission, [])
    return any(kw in text.lower() for kw in keywords)

def analyze_permissions(extension_id, permissions):
    info = fetch_extension_info(extension_id)
    if not info:
        return "Unknown", ""

    context = f"{info.get('name', '')} {info.get('summary', '')} {info.get('description', '')} {info.get('category', '')}"
    
    flagged = []
    for p in permissions.split(","):
        p = p.strip()
        if p in suspicious_permissions and not is_permission_contextual(context, p):
            flagged.append(p)

    if flagged:
        return ", ".join(flagged), "Flagged"  # suspicious → 'Flagged' 표시
    else:
        return "Valid", ""

# CSV 로드
df = pd.read_csv("/Users/minhyuk/Desktop/csf/ChromeExtension_Analysis/src/suspicious_permissions_analysis/update_sampling_permissions.csv", encoding="utf-8-sig")

# 분석 실행
df[["Suspicious Permissions", "Suspicious Check"]] = df.apply(
    lambda row: analyze_permissions(row["Extension ID"], row["Permissions"]) if pd.notna(row["Permissions"]) else ("None", ""),
    axis=1, result_type="expand"
)

# 저장
df.to_csv("/Users/minhyuk/Desktop/csf/ChromeExtension_Analysis/src/suspicious_permissions_analysis/flagged_suspicious_permissions.csv", index=False, encoding="utf-8-sig")

print("✅ 'Suspicious Permissions'와 'Suspicious Check' 컬럼 추가 완료.")