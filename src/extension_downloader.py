import csv
import os
import re

import requests

# API 기본 URL 설정
BASE_URL = "https://chrome-stats.com/api"

# API 키 설정
API_KEYS = "your keys"
api_key_index = 0

HEADERS = {
    "x-api-key": API_KEYS[0]
}

# 기본 다운로드 폴더 설정
BASE_DOWNLOAD_FOLDER = "your_download_path"
os.makedirs(BASE_DOWNLOAD_FOLDER, exist_ok=True)

# CSV 파일 경로 설정
CSV_FILE_PATH = "your_file_path"

def sanitize_filename(filename):
    return re.sub(r'[<>:"/\\|?*()]', '', filename)

def get_next_api_key():
    """
    Obtain the following API keys cyclically
    """
    global api_key_index
    api_key = API_KEYS[api_key_index]
    api_key_index = (api_key_index + 1) % len(API_KEYS)
    return api_key

def get_available_versions(extension_id, retries=5):
    """
    /api/list-versions 엔드포인트를 호출해 확장 프로그램의 사용 가능한 버전 목록을 가져옴.
    """
    global HEADERS
    HEADERS["x-api-key"] = get_next_api_key()
    url = f"{BASE_URL}/list-versions"
    params = {"id": extension_id}
    
    response = requests.get(url, headers=HEADERS, params=params)
    if response.status_code == 200:
        data = response.json()
        return data.get("downloads", {}).get("allVersions", [])  # allVersions 리스트 추출
    elif response.status_code == 429:
        if retries > 0:
            print(f"Rate limit exceeded. Retrying with next key... (Attempts left: {retries})")
            return get_available_versions(extension_id, retries=retries - 1)
        else:
            print("All retries exhausted. Skipping this request.")
            return None
    else:
        print(f"Failed to get versions for {extension_id}: {response.status_code}, Response: {response.text}")
        return None


def download_extension(extension_id, version, file_type, category):
    """
    /api/download 엔드포인트를 호출해 확장 프로그램을 다운로드.
    """
    # 카테고리에 맞는 폴더 생성
    category_folder = os.path.join(BASE_DOWNLOAD_FOLDER, category)
    os.makedirs(category_folder, exist_ok=True)
    
    # safe file name
    safe_version = sanitize_filename(version)
    file_path = os.path.join(category_folder, f"{extension_id}_{safe_version}.{file_type.lower()}")

    # Skip if file already exists
    if os.path.exists(file_path):
        print(f"File already exists: {file_path}, skipping download.")
        return
    
    # 다운로드 URL 생성
    url = f"{BASE_URL}/download"
    params = {"id": extension_id, "version": version, "type": file_type}
    response = requests.get(url, headers=HEADERS, params=params, stream=True)
    
    if response.status_code == 200:
        with open(file_path, "wb") as file:
            for chunk in response.iter_content(chunk_size=1024):
                file.write(chunk)
        print(f"Downloaded: {file_path}")
    else:
        print(f"Failed to download {extension_id} version {version}: {response.status_code}, Response: {response.text}")

def main():
    start_row = 0
    # CSV 파일 읽기
    with open(CSV_FILE_PATH, "r") as file:
        reader = list(csv.DictReader(file))  # CSV -> list
        total_rows = len(reader)
        print(f"Total rows in file: {total_rows}")
        
        
        for row_index, row in enumerate(reader, start=1):
            if row_index < start_row:
                continue
            
            extension_id = row.get("id", "").strip()  # ID에서 공백 제거
            category = row.get("category", "").strip()  # 카테고리 가져오기
            
            
            if not category:
                category = "uncategorized"
            
            if not extension_id:  # ID가 없으면 건너뜀
                print(f"Skipping row {row_index} due to missing extension ID: {row}")
                continue
            
            print(f"Processing row {row_index}/{total_rows}, extension ID: {extension_id} in category: {category}")
            
            
            if row_index >= total_rows:
                print("Processing last row:", row)
            
            
            # 사용 가능한 버전 가져오기
            versions = get_available_versions(extension_id)
            if versions:
                # 가장 최신 버전 선택
                latest_version_info = versions[0]
                latest_version = latest_version_info["version"]
                print(f"Latest version for {extension_id}: {latest_version}")
                
                # 확장 프로그램 다운로드
                download_extension(extension_id, latest_version, file_type="ZIP", category=category)

if __name__ == "__main__":
    main()