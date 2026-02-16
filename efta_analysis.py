import os
import sys
import base64
import requests
import argparse
from io import BytesIO
from pdf2image import convert_from_path

# --- CONFIGURATION ---
LM_STUDIO_URL = "http://localhost:1234/v1/chat/completions"
DPI = 150  # Lower DPI = faster processing on M4

def analyze_page(base64_image, template):
    payload = {
        "model": "loaded-model",
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": template},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}
                    }
                ]
            }
        ],
        "temperature": 0.0
    }
    
    try:
        response = requests.post(LM_STUDIO_URL, json=payload, timeout=300)
        response.raise_for_status()
        return response.json()['choices'][0]['message']['content']
    except Exception as e:
        return f"API ERROR: {str(e)}"

def process_pdfs(input_folder, template_path, output_folder):
    # Ensure template exists
    if not os.path.exists(template_path):
        print(f"❌ Error: Template file not found at {template_path}")
        return

    # Ensure output directory exists
    if not os.path.exists(output_folder):
        print(f"📁 Creating output directory: {output_folder}")
        os.makedirs(output_folder)

    with open(template_path, 'r') as f:
        template = f.read()

    files = [f for f in os.listdir(input_folder) if f.lower().endswith('.pdf')]
    if not files:
        print(f"❓ No PDFs found in {input_folder}")
        return

    print(f"🚀 Found {len(files)} PDFs. Saving results to: {output_folder}")

    for filename in files:
        pdf_path = os.path.join(input_folder, filename)
        print(f"\n📄 Processing: {filename}")
        
        try:
            # Convert PDF to images
            print(f"  -> Converting PDF to images (DPI={DPI})...")
            images = convert_from_path(pdf_path, dpi=DPI)
            
            for i, img in enumerate(images):
                print(f"  -> Analyzing Page {i+1}/{len(images)}...")
                
                # Encode image
                buffered = BytesIO()
                img.save(buffered, format="JPEG")
                img_str = base64.b64encode(buffered.getvalue()).decode('utf-8')
                
                # Get Analysis
                analysis = analyze_page(img_str, template)
                
                # Print output to terminal immediately
                print("-" * 30)
                print(f"OUTPUT PAGE {i+1}:\n{analysis}")
                print("-" * 30)
                
                # Save to specific output folder
                output_fn = f"{filename}_page_{i+1}.md"
                output_path = os.path.join(output_folder, output_fn)
                with open(output_path, "w") as f:
                    f.write(analysis)

        except Exception as e:
            print(f"❌ Critical Error on {filename}: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Vision-based PDF Parser using LM Studio")
    parser.add_argument("input", default="./docs", help="Folder containing PDF files")
    parser.add_argument("template", default="./prompt.md", help="Path to the markdown template file")
    parser.add_argument("output", default="./analysis" help="Folder where analysis files will be saved")
    
    args = parser.parse_args()
    
    process_pdfs(args.input, args.template, args.output)