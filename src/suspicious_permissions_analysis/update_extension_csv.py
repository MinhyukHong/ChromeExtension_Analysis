import csv
import os
import re

import requests
from bs4 import BeautifulSoup

INPUT_CSV = "/home/minhyuk/Desktop/ChromeExtension_Analysis/src/suspicious_permissions_analysis/sampling_permissions.csv"
OUTPUT_CSV = "/home/minhyuk/Desktop/ChromeExtension_Analysis/src/suspicious_permissions_analysis/update_sampling_permissions.csv"

def extract_extension_id(path):
    """경로에서 확장 프로그램 ID를 추출"""
    match = re.search(r"/([^/]+)_\d+\.\d+\.zip$", path)
    return match.group(1) if match else None

def fetch_extension_name(extension_id):
    """Chrome Web Store에서 확장 프로그램 이름 가져오기"""
    url = f"https://chrome.google.com/webstore/detail/{extension_id}"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
    
    response = requests.get(url, headers=headers)
    
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")
            name_tag = soup.find("h1", class_="e-f-w")
            return name_tag.text.strip() if name_tag else "Unknown"
        else:
            return "Not Found"
    except Exception as e:
        print(f"Error fetching {extension_id}: {e}")
        return "Error"

def process_csv(input_csv, output_csv):
    """기존 CSV를 읽어 확장 프로그램 이름을 추가한 새 CSV 생성"""
    with open(input_csv, "r", encoding="utf-8") as infile, open(output_csv, "w", newline="", encoding="utf-8") as outfile:
        reader = csv.reader(infile)
        writer = csv.writer(outfile)
        
        # 헤더 수정
        header = next(reader)
        writer.writerow(["Extension Path", "Extension ID", "Extension Name", "Permissions"])
        
        for row in reader:
            extension_path = row[0]
            permissions = row[1] if len(row) > 1 else "None"
            
            extension_id = extract_extension_id(extension_path)
            if extension_id:
                extension_name = fetch_extension_name(extension_id)
                writer.writerow([extension_path, extension_id, extension_name, permissions])
            else:
                writer.writerow([extension_path, "Unknown", "Unknown", permissions])

process_csv(INPUT_CSV, OUTPUT_CSV)

print(f"Updated CSV saved to {OUTPUT_CSV}")