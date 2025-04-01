import csv
import json
import os
import random
import zipfile

# Over-Permissioned 권한 목록
OVER_PERMISSIONED = {
    "webRequest", "webRequestBlocking", "clipboardRead",
    "clipboardWrite", "nativeMessaging", "proxy", "debugger",
    "downloads", "management", "history", "cookies", "bookmarks"
}

SAMPLE_SIZE = 2000  # 랜덤 샘플링 개수

# ZIP 파일 리스트 가져오기 (하위 폴더 포함)
def get_zip_files(root_folder):
    zip_files = []
    for root, _, files in os.walk(root_folder):
        for file in files:
            if file.endswith(".zip"):
                zip_files.append(os.path.join(root, file))
    return zip_files

# ZIP 파일에서 manifest.json 추출
def extract_manifest_json(zip_path):
    try:
        with zipfile.ZipFile(zip_path, 'r') as z:
            for file in z.namelist():
                if file.endswith("manifest.json"):
                    with z.open(file) as f:
                        return json.load(f)  # JSON 파싱
    except (zipfile.BadZipFile, json.JSONDecodeError):
        return None
    return None

# Over-Permissioned 권한 검사
def check_permissions(manifest):
    if not manifest:
        return []
    
    permissions = manifest.get("permissions", [])
    
    if not isinstance(permissions, list):
        return []
    
    permissions = {p for p in permissions if isinstance(p, str)}
    
    over_permitted = permissions.intersection(OVER_PERMISSIONED)
    return list(over_permitted)

# 500개 랜덤 샘플링 후 분석
def analyze_sampled_extensions(input_folder, output_csv):
    zip_files = get_zip_files(input_folder)

    if len(zip_files) < SAMPLE_SIZE:
        print(f"ZIP 파일이 2000개 미만입니다. ({len(zip_files)}개 발견됨)")
        return

    # 랜덤 샘플링
    sampled_files = random.sample(zip_files, SAMPLE_SIZE)

    print("\n[샘플링된 2000개 익스텐션 분석 시작]\n")

    # CSV 파일 저장
    with open(output_csv, "w", newline="") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["Extension", "Permissions"])

        for zip_path in sampled_files:
            print(f"Analyzing: {zip_path}")
            manifest = extract_manifest_json(zip_path)
            over_permissions = check_permissions(manifest)
            writer.writerow([zip_path, ", ".join(over_permissions) if over_permissions else "None"])

    print(f"\n[분석 완료] 결과 저장: {output_csv}")

# 실행
if __name__ == "__main__":
    INPUT_FOLDER = "/home/minhyuk/Desktop/Download_extension/Extensions"  # ZIP 파일이 있는 폴더
    OUTPUT_CSV = "sampling_permissions.csv"

    analyze_sampled_extensions(INPUT_FOLDER, OUTPUT_CSV)