import os
import sqlite3
import json
import argparse
import hashlib
import cv2
import gc
import numpy as np
from pathlib import Path
from multiprocessing import Process, set_start_method
from pdf2image import convert_from_path
from insightface.app import FaceAnalysis
from tqdm import tqdm
import tempfile

def process_worker(pdf_batch, db_path, faces_dir):
    """Worker process that handles a chunk of PDFs and then exits to clear RAM."""
    # Ensure local face crop directory exists
    temp_unsorted = faces_dir / "temp_unsorted"
    temp_unsorted.mkdir(parents=True, exist_ok=True)
    
    app = FaceAnalysis(name='buffalo_l', providers=['CPUExecutionProvider'])
    app.prepare(ctx_id=0, det_size=(640, 640))
    
    for pdf_path in pdf_batch:
        f_hash = hashlib.md5(open(pdf_path, 'rb').read()).hexdigest()
        
        with tempfile.TemporaryDirectory() as temp_path:
            try:
                # dpi=120 balances RAM usage and accuracy
                images = convert_from_path(pdf_path, dpi=120, output_folder=temp_path, fmt="jpeg", paths_only=True)
                
                for page_idx, img_path in enumerate(images):
                    cv_img = cv2.imread(img_path)
                    if cv_img is None: continue
                    
                    faces = app.get(cv_img)
                    
                    with sqlite3.connect(db_path) as conn:
                        for i, face in enumerate(faces):
                            bbox = face.bbox.astype(int)
                            y1, y2, x1, x2 = max(0, bbox[1]), bbox[3], max(0, bbox[0]), bbox[2]
                            crop = cv_img[y1:y2, x1:x2]
                            if crop.size == 0: continue
                            
                            crop_name = f"{f_hash[:8]}_p{page_idx}_f{i}.jpg"
                            save_path = temp_unsorted / crop_name
                            cv2.imwrite(str(save_path), crop)
                            
                            conn.execute("INSERT INTO detections (file_path, embedding, crop_path) VALUES (?, ?, ?)",
                                         (str(pdf_path), face.normed_embedding.tobytes(), str(save_path)))
                    del cv_img
                
                with sqlite3.connect(db_path) as conn:
                    conn.execute("INSERT INTO processed_files (file_hash, file_path) VALUES (?, ?)", (f_hash, str(pdf_path)))
                
            except Exception as e:
                print(f"\n[Error] {pdf_path.name}: {e}")
    
    del app
    gc.collect()

def organize_and_summarize(db_path, output_dir, faces_dir):
    print("\nClustering faces and generating final database...")
    with sqlite3.connect(db_path) as conn:
        data = conn.execute("SELECT id, file_path, embedding, crop_path FROM detections").fetchall()

    if not data:
        print("No faces found to organize.")
        return
    
    embeddings = [np.frombuffer(d[2], dtype=np.float32) for d in data]
    clusters = [] 

    for i, emb in enumerate(embeddings):
        match_found = False
        for cluster in clusters:
            if np.dot(emb, cluster['rep']) > 0.65:
                cluster['members'].append(i)
                match_found = True
                break
        if not match_found:
            clusters.append({'rep': emb, 'members': [i]})

    summary_data = []
    # Progress bar for the final organization step
    for c_idx, cluster in enumerate(tqdm(clusters, desc="Sorting into folders")):
        person_folder = faces_dir / f"Person_{c_idx + 1}"
        person_folder.mkdir(parents=True, exist_ok=True)
        
        person_entry = {"person_id": c_idx + 1, "count": len(cluster['members']), "found_in": []}

        for m_idx in cluster['members']:
            row = data[m_idx]
            old_path = Path(row[3])
            new_path = person_folder / old_path.name
            if old_path.exists():
                os.rename(old_path, new_path)
            person_entry["found_in"].append(row[1])
        
        person_entry["found_in"] = list(set(person_entry["found_in"]))
        summary_data.append(person_entry)

    with open(output_dir / "face_db.json", "w") as f:
        json.dump(summary_data, f, indent=4)
    
    print(f"\nDone! Database created with {len(clusters)} unique individuals.")

if __name__ == "__main__":
    try:
        set_start_method('spawn', force=True)
    except RuntimeError: pass

    parser = argparse.ArgumentParser()
    parser.add_argument("input", help="Source folder of PDFs")
    parser.add_argument("output", help="Output directory for all results")
    args = parser.parse_args()

    # Automatic Directory Setup
    out_path = Path(args.output)
    out_path.mkdir(parents=True, exist_ok=True)
    db_file = out_path / "scan_state.db"
    faces_dir = out_path / "identified_faces"
    faces_dir.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(db_file) as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS processed_files (file_hash TEXT PRIMARY KEY, file_path TEXT)")
        conn.execute("CREATE TABLE IF NOT EXISTS detections (id INTEGER PRIMARY KEY, file_path TEXT, embedding BLOB, crop_path TEXT)")

    # Resume Logic
    all_pdfs = list(Path(args.input).glob("*.pdf"))
    with sqlite3.connect(db_file) as conn:
        processed = {row[0] for row in conn.execute("SELECT file_path FROM processed_files").fetchall()}
    pending = [p for p in all_pdfs if str(p) not in processed]

    # Processing with Progress Bar
    batch_size = 10
    with tqdm(total=len(pending), desc="Total PDF Progress", unit="pdf") as pbar:
        for i in range(0, len(pending), batch_size):
            batch = pending[i : i + batch_size]
            p = Process(target=process_worker, args=(batch, db_file, faces_dir))
            p.start()
            p.join()
            pbar.update(len(batch))

    organize_and_summarize(db_file, out_path, faces_dir)