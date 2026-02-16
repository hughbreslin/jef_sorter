# jef_sorter
A sorting utility for the Jeffrey Epstein Files

This is meant as a starting point / example :) All scripts vibe coded with Gemini Fast.

Use the 'efta_download.py' script to download the files - you must figure out the cookie yourself. Downloads are indexed using the .json file and it is advisable to skip large missing file sections to reduce requests.

```python
python efta_download.py -c "" -o "./docs"
```

Use the 'efta_analysis.py" script and the associated prompt file to classify documents. I used LLM Studio on my M4 Mac mini with 32GB of RAM running qwen2.5-vl-7b-instruct with a 32768 token context window.

```python
python efta_analysis.py ./docs ./prompt.md ./analysis
```

As a progression a more layered classification system could be used with different models. One to do an initial sort based on the first page of a doc to decide pictures or text or mix maybe and then subsequently the doc can be summarized by a more specialized prompt. I also need to check the image scaling to ensure this is good and maybe see if images could be passed together instead of separately in prompts as a single document - a classifier would help!

This comes with no warranty and do not abuse the file download facility.
