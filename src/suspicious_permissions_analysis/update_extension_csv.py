import csv
import re

import requests

INPUT_CSV = "/Users/minhyuk/Desktop/csf/ChromeExtension_Analysis/src/suspicious_permissions_analysis/sampling_permissions.csv"
OUTPUT_CSV = "/Users/minhyuk/Desktop/csf/ChromeExtension_Analysis/src/suspicious_permissions_analysis/update_sampling_permissions.csv"
API_KEY = ''  # ChromeStats API Key
API_URL = 'https://chrome-stats.com/api/detail'

def extract_extension_id(path):
    """경로에서 확장 프로그램 ID를 추출 (복잡한 버전명 처리 포함)"""
    match = re.search(r"/([a-p]{32})_[^/]+\.zip$", path)
    return match.group(1) if match else None

def fetch_extension_info(extension_id):
    """ChromeStats API로 확장 프로그램 정보 가져오기"""
    headers = {'x-api-key': API_KEY}
    params = {'id': extension_id}
    try:
        response = requests.get(API_URL, headers=headers, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        name = data.get('name', 'Unknown')
        description = data.get('description', 'Unknown')
        return name.strip(), description.strip()
    except Exception as e:
        print(f"[!] Error fetching {extension_id}: {e}")
        return "Unknown", "Unknown"

def process_csv(input_csv, output_csv):
    """CSV를 처리하고 확장 프로그램 이름과 설명 추가"""
    with open(input_csv, "r", encoding="utf-8") as infile, open(output_csv, "w", newline="", encoding="utf-8-sig") as outfile:
        reader = csv.reader(infile)
        writer = csv.writer(outfile)

        header = next(reader)
        new_header = ["Extension Path", "Extension ID", "Extension Name", "Extension Description", "Permissions"]
        writer.writerow(new_header)

        for row in reader:
            extension_path = row[0]
            permissions = row[1] if len(row) > 1 else "None"
            extension_id = extract_extension_id(extension_path)

            if extension_id:
                name, desc = fetch_extension_info(extension_id)
                print(f"[+] {extension_id} → {name}")
                writer.writerow([extension_path, extension_id, name, desc, permissions])
            else:
                print(f"[!] Failed to parse ID from: {extension_path}")
                writer.writerow([extension_path, "Unknown", "Unknown", "Unknown", permissions])

process_csv(INPUT_CSV, OUTPUT_CSV)