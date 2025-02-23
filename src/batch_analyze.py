import os
from analyze_extension import analyze_extension

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

