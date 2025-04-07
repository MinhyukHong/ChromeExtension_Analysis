import os
import zipfile
import shutil
import argparse
import logging
from pathlib import Path

# --- 로깅 설정 ---
# INFO 레벨 이상의 메시지를 콘솔에 출력하고, 파일에도 저장합니다.
log_file = 'wasm_zip_finder.log'
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file, mode='w', encoding='utf-8'), # 파일 핸들러
        logging.StreamHandler() # 콘솔 핸들러
    ]
)

def find_and_copy_wasm_zips(source_dir, dest_dir):
    """
    source_dir 및 하위 디렉토리에서 .zip 파일을 찾아 .wasm 파일 포함 여부를 확인하고,
    포함된 경우 dest_dir로 복사합니다.

    Args:
        source_dir (str): 검색을 시작할 상위 디렉토리 경로.
        dest_dir (str): .wasm을 포함하는 .zip 파일을 복사할 목적지 디렉토리 경로.
    """
    source_path = Path(source_dir).resolve() # 절대 경로로 변환
    dest_path = Path(dest_dir).resolve()

    # 목적지 디렉토리 확인 및 생성
    try:
        dest_path.mkdir(parents=True, exist_ok=True)
        logging.info(f"Destination directory ensured: {dest_path}")
    except OSError as e:
        logging.error(f"Failed to create destination directory '{dest_path}': {e}")
        return

    if not source_path.is_dir():
        logging.error(f"Source directory not found or is not a directory: {source_path}")
        return

    logging.info(f"Starting scan in: {source_path}")
    wasm_zip_count = 0
    processed_zip_count = 0

    # os.walk를 사용하여 하위 디렉토리 포함 모든 파일 검색
    for root, _, files in os.walk(source_path):
        logging.debug(f"Scanning directory: {root}")
        for filename in files:
            # 파일 확장자가 .zip인지 확인 (대소문자 구분 없이)
            if filename.lower().endswith('.zip'):
                processed_zip_count += 1
                zip_file_path = Path(root) / filename
                logging.debug(f"Found ZIP file: {zip_file_path}")
                wasm_found_in_zip = False

                try:
                    # ZIP 파일 열기 (읽기 모드)
                    with zipfile.ZipFile(zip_file_path, 'r') as zf:
                        # ZIP 파일 내의 모든 멤버(파일/디렉토리) 이름 목록 가져오기
                        member_list = zf.namelist()
                        # 각 멤버 이름 확인
                        for member_name in member_list:
                            # .wasm 확장자를 가진 파일이 있는지 확인 (대소문자 구분 없이)
                            if member_name.lower().endswith('.wasm'):
                                wasm_found_in_zip = True
                                logging.info(f"Found .wasm file ('{member_name}') inside: {zip_file_path}")
                                break # .wasm 파일 하나라도 찾으면 내부 루프 중단

                except zipfile.BadZipFile:
                    logging.warning(f"Skipping corrupted or invalid ZIP file: {zip_file_path}")
                    continue # 다음 파일로 넘어감
                except FileNotFoundError:
                    logging.warning(f"ZIP file vanished during processing (should not happen often): {zip_file_path}")
                    continue
                except Exception as e:
                    logging.error(f"Error reading ZIP file {zip_file_path}: {e}")
                    continue # 다음 파일로 넘어감

                # .wasm 파일이 발견된 경우, 목적지 디렉토리로 복사
                if wasm_found_in_zip:
                    destination_file_path = dest_path / filename
                    try:
                        # shutil.copy2를 사용하여 메타데이터(수정 시간 등)도 함께 복사
                        shutil.copy2(zip_file_path, destination_file_path)
                        logging.info(f"Copied '{filename}' to {dest_path}")
                        wasm_zip_count += 1
                    except shutil.SameFileError:
                         logging.warning(f"Source and destination are the same file: {zip_file_path}")
                    except PermissionError:
                        logging.error(f"Permission denied to copy file to: {destination_file_path}")
                    except Exception as e:
                        logging.error(f"Failed to copy {zip_file_path} to {destination_file_path}: {e}")

    logging.info(f"Scan finished. Processed {processed_zip_count} ZIP files.")
    logging.info(f"Found and copied {wasm_zip_count} ZIP files containing .wasm files to: {dest_path}")

def main():
    # 명령줄 인자 파서 설정
    parser = argparse.ArgumentParser(
        description="Scan a directory recursively for ZIP files containing .wasm files and copy them to a destination directory."
    )
    parser.add_argument(
        "source_directory",
        help="The source directory path to start scanning."
    )
    parser.add_argument(
        "destination_directory",
        help="The destination directory path where ZIP files containing .wasm will be copied."
    )
    args = parser.parse_args()

    # 함수 호출
    find_and_copy_wasm_zips(args.source_directory, args.destination_directory)

if __name__ == "__main__":
    main()
