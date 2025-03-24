import os
import shutil
import pandas as pd

def copy_files_from_csv(csv_file, destination_folder):
    # CSV 파일 읽기
    df = pd.read_csv(csv_file)

    # path 열 확인
    if 'Extension Path' not in df.columns:
        raise ValueError("CSV 파일에 'path' 열이 존재하지 않습니다.")

    # 대상 폴더가 없으면 생성
    os.makedirs(destination_folder, exist_ok=True)

    for file_path in df['Extension Path']:
        file_path = str(file_path).strip()  # 경로 공백 제거

        if os.path.isfile(file_path):  # 파일이 존재하는지 확인
            file_name = os.path.basename(file_path)  # 파일 이름 추출
            destination_path = os.path.join(destination_folder, file_name)
            
            # 파일이 중복될 경우 새로운 이름 부여
            counter = 1
            while os.path.exists(destination_path):
                name, ext = os.path.splitext(file_name)
                destination_path = os.path.join(destination_folder, f"{name}_{counter}{ext}")
                counter += 1

            shutil.copy2(file_path, destination_path)  # 파일 복사
            print(f"Copied: {file_path} -> {destination_path}")
        else:
            print(f"File not found: {file_path}")

# 사용 예시
csv_file_path = "filtered_permission_info.csv"  # CSV 파일 경로
destination_dir = "collected_files"  # 모을 폴더

copy_files_from_csv(csv_file_path, destination_dir)

