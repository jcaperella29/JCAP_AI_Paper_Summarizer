import os
import fitz  # PyMuPDF
import requests
import threading
import concurrent.futures
from flask import Flask, render_template, request, redirect, send_file, url_for, flash

app = Flask(__name__)
app.secret_key = 'your-secret-key'
UPLOAD_FOLDER = 'uploads'
SUMMARY_FOLDER = 'summaries'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(SUMMARY_FOLDER, exist_ok=True)

summary_cache = {}

def extract_text_chunks(pdf_path, chunk_size=3000):
    doc = fitz.open(pdf_path)
    text_chunks = []
    current_text = ""
    for page in doc:
        current_text += page.get_text() + "\n"
        if len(current_text) >= chunk_size:
            text_chunks.append(current_text)
            current_text = ""
    if current_text:
        text_chunks.append(current_text)
    return text_chunks

def summarize_chunks(chunks):
    summary_sections = [""] * len(chunks)

    def summarize_single(i, chunk):
        prompt = f"Summarize this section of a research paper:\n\n{chunk}"
        try:
            response = requests.post(
                "http://localhost:11434/api/generate",
                json={"model": "mistral", "prompt": prompt, "stream": False}
            )
            if response.status_code != 200:
                raise Exception(f"HTTP {response.status_code}: {response.text}")
            result = response.json().get("response", "").strip()
            if not result:
                result = "⚠️ No summary returned by model."
        except Exception as e:
            result = f"❌ Error: {e}"

        section = f"\n🧠 === Summary of Section {i+1} ===\n{result}\n"
        summary_sections[i] = section

    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = [executor.submit(summarize_single, i, chunk) for i, chunk in enumerate(chunks)]
        for f in concurrent.futures.as_completed(futures):
            pass

    return "".join(summary_sections)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/summarize', methods=['POST'])
def summarize():
    if 'pdf' not in request.files:
        flash("No file uploaded.")
        return redirect(url_for('index'))

    file = request.files['pdf']
    if file.filename == '':
        flash("No selected file.")
        return redirect(url_for('index'))

    pdf_path = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(pdf_path)

    chunks = extract_text_chunks(pdf_path)
    summary = summarize_chunks(chunks)

    summary_file = os.path.join(SUMMARY_FOLDER, f"{os.path.splitext(file.filename)[0]}_summary.txt")
    with open(summary_file, 'w', encoding='utf-8') as f:
        f.write(summary)

    summary_cache['last_summary_file'] = summary_file
    summary_cache['text'] = summary

    return render_template('summary.html', summary=summary)

@app.route('/download')
def download_summary():
    summary_file = summary_cache.get('last_summary_file')
    if summary_file and os.path.exists(summary_file):
        return send_file(summary_file, as_attachment=True)
    else:
        flash("No summary available to download.")
        return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)

