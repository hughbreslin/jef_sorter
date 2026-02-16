import os
import subprocess
import time
import json
import sys
import argparse
import logging

# Logging configuration
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s | %(message)s',
    datefmt='%H:%M:%S'
)

BASE_URL_TEMPLATE = "https://www.justice.gov/epstein/files/DataSet%20{ds_num}/EFTA{file_num:08d}.pdf"
INDEX_FILE = "efta_index.json"
DATASET_IDS = [1,2,3,4,5,6,7,8,9, 10, 11, 12]

def load_index():
    if os.path.exists(INDEX_FILE):
        try:
            with open(INDEX_FILE, 'r') as f:
                return json.load(f)
        except:
            pass
    return {"datasets": {}, "last_efta": 3858}

def save_index(index_data):
    with open(INDEX_FILE, 'w') as f:
        json.dump(index_data, f, indent=4)

def check_file_exists(ds_num, file_num, cookie):
    """Lightweight HEAD request to check for file in next dataset."""
    url = BASE_URL_TEMPLATE.format(ds_num=ds_num, file_num=file_num)
    cmd = ['curl', '-I', '-L', '-s', '-b', cookie, '-A', 'Safari/605.1.15', url]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return any(status in result.stdout for status in ["HTTP/1.1 200", "HTTP/2 200"])

def download_file(ds_num, file_num, output_dir, cookie):
    filename = f"EFTA{file_num:08d}.pdf"
    filepath = os.path.join(output_dir, filename)

    if os.path.exists(filepath) and os.path.getsize(filepath) > 60000:
        return "ALREADY_EXISTS" 

    url = BASE_URL_TEMPLATE.format(ds_num=ds_num, file_num=file_num)
    cmd = ['curl', '-L', '-f', '-sS', '-b', cookie, '-o', filepath, url]
    
    result = subprocess.run(cmd, capture_output=True)
    if result.returncode == 0 and os.path.exists(filepath) and os.path.getsize(filepath) > 60000:
        return "SUCCESS"
    
    if os.path.exists(filepath): os.remove(filepath)
    return "MISS"

def main():
    parser = argparse.ArgumentParser(description="Perpetual DOJ PDF Downloader")
    parser.add_argument("-c", "--cookie", required=True, help="The justice.gov session cookie - you must be over 18 to enter this.")
    parser.add_argument("-o", "--output", default="./docs", help="Directory to save files (default: ./docs)")
    args = parser.parse_args()

    if not os.path.exists(args.output): 
        os.makedirs(args.output)

    index_data = load_index()
    curr_efta = index_data.get("last_efta", 3858)
    ds_index = 0

    print("\n" + "="*60)
    print(f"♾️  PERPETUAL DOJ TICK-TOCK MODE")
    print(f"📂 Output Dir: {args.output}")
    print(f"📄 Resume Point: EFTA{curr_efta:08d}")
    print("="*60 + "\n")

    try:
        while ds_index < len(DATASET_IDS):
            current_ds = str(DATASET_IDS[ds_index])
            
            if current_ds not in index_data["datasets"]:
                index_data["datasets"][current_ds] = {"start": curr_efta, "end": None}

            index_data["last_efta"] = curr_efta
            save_index(index_data)

            # TICK: Attempt current folder
            status = download_file(int(current_ds), curr_efta, args.output, args.cookie)
            
            if status == "SUCCESS":
                print(f"\n✅ [SAVED] DS{current_ds} | EFTA{curr_efta:08d}")
                index_data["datasets"][current_ds]["end"] = curr_efta
                curr_efta += 1
                continue

            elif status == "ALREADY_EXISTS":
                sys.stdout.write(f"\r⏭️  [SKIP] EFTA{curr_efta:08d}...")
                sys.stdout.flush()
                curr_efta += 1
                continue
            
            # TOCK: Current failed. Check NEXT dataset folder immediately.
            if ds_index + 1 < len(DATASET_IDS):
                next_ds = DATASET_IDS[ds_index + 1]
                if check_file_exists(next_ds, curr_efta, args.cookie):
                    print(f"\n✨ [PIVOT] Found EFTA{curr_efta:08d} in DS{next_ds}! Shifting dataset...")
                    ds_index += 1
                    continue

            sys.stdout.write(f"\r🏜️  [GAP] Searching EFTA{curr_efta:08d} in DS{current_ds}...")
            sys.stdout.flush()
            curr_efta += 1
            time.sleep(0.05)

    except KeyboardInterrupt:
        print(f"\n\n🛑 User stopped. Resume point saved at EFTA{curr_efta:08d}")
        save_index(index_data)
        sys.exit(0)

if __name__ == "__main__":
    main()