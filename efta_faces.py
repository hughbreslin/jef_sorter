import os
import sqlite3
import json
import argparse
import hashlib
import cv2
import numpy as np
from pathlib import Path
from pdf2image import convert_from_path
from insightface.app import FaceAnalysis
from tqdm import tqdm

class FaceIntelligence:
    def __init__(self, db_path, output_dir):
        self.db_path = db_path
        self.output_dir = Path(output_dir)
        self.crops_dir = self.output_dir / "face_database"
        self.crops_dir.mkdir(parents=True, exist_ok=True)
        
        self._setup_db()
        # buffalo_l is the high-accuracy model
        self.app = FaceAnalysis(name='buffalo_l', providers=['CPUExecutionProvider'])
        self.app.prepare(ctx_id=0, det_size=(640, 640))

    def _setup_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''CREATE TABLE IF NOT EXISTS processed_files 
                            (file_hash TEXT PRIMARY KEY, file_path TEXT)''')
            conn.execute('''CREATE TABLE IF NOT EXISTS detections 
                            (id INTEGER PRIMARY KEY, file_path TEXT, page_num INTEGER, 
                             embedding BLOB, crop_path TEXT)''')

    def process_pdfs(self, input_dir):
        pdf_files = list(Path(input_dir).glob("*.pdf"))
        
        for pdf_path in tqdm(pdf_files, desc="Processing PDFs"):
            f_hash = hashlib.md5(open(pdf_path, 'rb').read()).hexdigest()
            
            # Check if already processed
            with sqlite3.connect(self.db_path) as conn:
                if conn.execute("SELECT 1 FROM processed_files WHERE file_hash=?", (f_hash,)).fetchone():
                    continue

            # Convert PDF pages to images
            images = convert_from_path(pdf_path)
            
            for page_idx, pil_img in enumerate(images):
                cv_img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
                faces = self.app.get(cv_img)
                
                with sqlite3.connect(self.db_path) as conn:
                    for i, face in enumerate(faces):
                        # 1. Crop the face
                        bbox = face.bbox.astype(int)
                        crop = cv_img[max(0, bbox[1]):bbox[3], max(0, bbox[0]):bbox[2]]
                        
                        if crop.size == 0: continue
                        
                        # Save temp crop to be sorted later
                        crop_name = f"{f_hash[:8]}_p{page_idx}_f{i}.jpg"
                        crop_path = self.crops_dir / "temp" / crop_name
                        crop_path.parent.mkdir(exist_ok=True)
                        cv2.imwrite(str(crop_path), crop)
                        
                        # 2. Store in DB
                        conn.execute("INSERT INTO detections (file_path, page_num, embedding, crop_path) VALUES (?, ?, ?, ?)",
                                     (str(pdf_path), page_idx, face.normed_embedding.tobytes(), str(crop_path)))
            
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("INSERT INTO processed_files (file_hash, file_path) VALUES (?, ?)", (f_hash, str(pdf_path)))

    def organize_and_summarize(self):
        """Clusters faces, moves crops to person-specific folders, and exports JSON."""
        with sqlite3.connect(self.db_path) as conn:
            data = conn.execute("SELECT id, file_path, embedding, crop_path FROM detections").fetchall()

        if not data: return
        
        embeddings = [np.frombuffer(d[2], dtype=np.float32) for d in data]
        clusters = [] # List of {'rep': embedding, 'members': [indices]}

        # Simple clustering (Threshold 0.6 is standard for Buffalo_L)
        for i, emb in enumerate(embeddings):
            match_found = False
            for idx, cluster in enumerate(clusters):
                if np.dot(emb, cluster['rep']) > 0.65:
                    cluster['members'].append(i)
                    match_found = True
                    break
            if not match_found:
                clusters.append({'rep': emb, 'members': [i]})

        summary_data = []
        for c_idx, cluster in enumerate(clusters):
            person_folder = self.crops_dir / f"Person_{c_idx + 1}"
            person_folder.mkdir(exist_ok=True)
            
            person_entry = {
                "person_id": c_idx + 1,
                "occurrence_count": len(cluster['members']),
                "files": []
            }

            for m_idx in cluster['members']:
                original_row = data[m_idx] # (id, file_path, embedding, crop_path)
                old_path = Path(original_row[3])
                new_path = person_folder / old_path.name
                
                if old_path.exists():
                    os.rename(old_path, new_path)
                
                person_entry["files"].append(original_row[1])
            
            summary_data.append(person_entry)

        # Save JSON Database
        with open(self.output_dir / "face_database.json", "w") as f:
            json.dump(summary_data, f, indent=4)
        
        print(f"Organized {len(clusters)} unique people into folders.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("input", help="Directory of PDFs")
    parser.add_argument("output", help="Output directory for DB and Crops")
    args = parser.parse_args()

    # DB is kept inside the output folder for portability
    db_file = Path(args.output) / "state_tracker.db"
    
    scanner = FaceIntelligence(str(db_file), args.output)
    scanner.process_pdfs(args.input)
    scanner.organize_and_summarize()