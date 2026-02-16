# jef_sorter
A sorting utility for the Jeffrey Epstein Files

This is meant as a starting point / example :) All scripts vibe coded with Gemini Fast. It can be used to download and classify the documents.

Use the 'efta_download.py' script to download the files - you must figure out the cookie yourself. Downloads are indexed using the .json file and it is advisable to skip large missing file sections to reduce requests.

```python
python efta_download.py -c "" -o "./docs"
```

Use the 'efta_analysis.py" script and the associated prompt file to classify documents. I used LLM Studio on my M4 Mac mini with 32GB of RAM running qwen2.5-vl-7b-instruct with a 32768 token context window.

```python
python efta_analysis.py ./docs ./prompt.md ./analysis
```

Use the 'efta_faces.py" script to find all faces in the PDFs. This script will crop and associate all of the faces from the PDF files and create a report of what documents contain what face. This can be used to locate individuals within the documents, It will also crop all images into subfolders to be checked easily.

```python
python efta_faces.py ./docs ./faces
```

A sample output example running the analysis script for EFTA00000002.pdf

```json
{
  "ownership": "Personal (Epstein)",
  "date": "",
  "source_evidence": "",
  "doc_type": "Images",
  "short_summary": "A photograph of a building entrance with ornate architectural details.",
  "entities_identified": [],
  "full_doc_summary": ""
}
```

A sample output example running the analysis script for EFTA00030420.pdf_page_3

```json
{
  "ownership": "State/Official",
  "date": "04-12-2020",
  "source_evidence": "Today our office is sending via FedEx a replacement drive for Ghislaine Maxwell, which should arrive at the MDC tomorrow. This drive will replace the drive that Maxwell recently dropped and broke, and the accompanying cover letters are attached.",
  "doc_type": "Correspondence",
  "short_summary": "A U.S. Attorney's Office email confirms sending a replacement drive for Ghislaine Maxwell via FedEx to the MDC.",
  "entities_identified": ["Ghislaine Maxwell", "U.S. Attorney's Office, SDNY"],
  "full_doc_summary": "The document is an email from the U.S. Attorney's Office in New York regarding the sending of a replacement drive for Ghislaine Maxwell via FedEx to the MDC (Manhattan District Court). The email mentions that this replaces a broken drive recently dropped by Maxwell and includes attached cover letters."
}
```

As a progression a more layered classification system could be used with different models. One to do an initial sort based on the first page of a doc to decide pictures or text or mix maybe and then subsequently the doc can be summarized by a more specialized prompt. I also need to check the image scaling to ensure this is good and maybe see if images could be passed together instead of separately in prompts as a single document - a classifier would help!

This comes with no warranty and do not abuse the file download facility.
