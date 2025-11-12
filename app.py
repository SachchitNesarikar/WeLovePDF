from flask import Flask, render_template, request, send_file
from PyPDF2 import PdfReader, PdfWriter, PdfMerger
from PIL import Image
from io import BytesIO
from werkzeug.utils import secure_filename
import zipfile
import fitz  # PyMuPDF
import docx2pdf
import tempfile
import os
from dotenv import load_dotenv
load_dotenv()
import base64
import requests
from flask import jsonify
from gemini_notes import get_subtopics, get_notes  # if in separate file
import google.generativeai as genai
import base64

# Configure Gemini with your API key

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_API_ENDPOINT = os.getenv("GEMINI_API_ENDPOINT")

app = Flask(__name__)  

@app.route("/")
def index():
    return render_template("index.html")

# ---------- IMAGE TO PDF ----------
@app.route("/image_to_pdf", methods=["POST"])
def image_to_pdf():
    files = request.files.getlist("image_files")
    output_name = request.form.get("output_name", "image_to_pdf").strip()

    image_list = []
    for file in files:
        if file and file.filename:
            try:
                image = Image.open(file.stream).convert("RGB")
                image_list.append(image)
            except Exception as e:
                print(f"Skipping {file.filename}: {e}")

    if not image_list:
        return "No valid images uploaded", 400

    if not output_name.lower().endswith(".pdf"):
        output_name += ".pdf"

    output_stream = BytesIO()
    image_list[0].save(output_stream, save_all=True, append_images=image_list[1:], format="PDF")
    output_stream.seek(0)

    return send_file(output_stream, as_attachment=True, download_name=output_name)

# ---------- SPLIT PDF ----------
@app.route("/split", methods=["POST"])
def split_pdf():
    file = request.files["pdf_file"]
    start_page = int(request.form.get("start_page")) - 1
    end_page = int(request.form.get("end_page"))
    custom_name = request.form.get("output_name", "split")

    reader = PdfReader(file.stream)
    writer = PdfWriter()

    for i in range(start_page, end_page):
        writer.add_page(reader.pages[i])

    output_stream = BytesIO()
    writer.write(output_stream)
    output_stream.seek(0)

    output_filename = f"{secure_filename(custom_name)}.pdf"
    return send_file(output_stream, as_attachment=True, download_name=output_filename)

# ---------- MERGE PDF ----------
@app.route("/merge", methods=["POST"])
def merge_pdfs():
    custom_name = request.form.get("output_name", "merged")
    merger = PdfMerger()

    uploaded_files = [
        request.files.get("pdf_file1"),
        request.files.get("pdf_file2"),
        request.files.get("pdf_file3")
    ]

    any_uploaded = False
    for file in uploaded_files:
        if file and file.filename:
            merger.append(file.stream)
            any_uploaded = True

    if not any_uploaded:
        return "No files uploaded", 400

    output_stream = BytesIO()
    merger.write(output_stream)
    merger.close()
    output_stream.seek(0)

    output_filename = f"{secure_filename(custom_name)}.pdf"
    return send_file(output_stream, as_attachment=True, download_name=output_filename)

# ---------- COMPRESS PDF ----------
@app.route("/compress", methods=["POST"])
def compress_pdf():
    file = request.files["pdf_file"]
    quality = request.form.get("quality", "medium")
    output_name = request.form.get("output_name", "compressed")

    if not file or not file.filename.endswith(".pdf"):
        return "Please upload a valid PDF file", 400

    reader = PdfReader(file.stream)
    writer = PdfWriter()

    for page in reader.pages:
        page.compress_content_streams()
        writer.add_page(page)

    output_stream = BytesIO()
    writer.write(output_stream)
    output_stream.seek(0)

    output_filename = f"{secure_filename(output_name)}.pdf"
    return send_file(output_stream, as_attachment=True, download_name=output_filename)

# ---------- IMAGE EXTRACTION FROM PDF ----------
@app.route("/extract_images", methods=["POST"])
def extract_images():
    file = request.files["pdf_file"]
    output_name = request.form.get("output_name", "ExtractedImages")

    pdf = fitz.open(stream=file.read(), filetype="pdf")
    zip_stream = BytesIO()
    with zipfile.ZipFile(zip_stream, "w") as zipf:
        for page_index in range(len(pdf)):
            images = pdf[page_index].get_images(full=True)
            for img_index, img in enumerate(images):
                xref = img[0]
                base_image = pdf.extract_image(xref)
                image_bytes = base_image["image"]
                ext = base_image["ext"]
                zipf.writestr(f"page{page_index+1}_img{img_index+1}.{ext}", image_bytes)
    zip_stream.seek(0)
    return send_file(zip_stream, as_attachment=True, download_name=f"{secure_filename(output_name)}.zip")

# ---------- WORD TO PDF ----------x
@app.route("/word_to_pdf", methods=["POST"])
def word_to_pdf():
    word_file = request.files["word_file"]
    output_name = request.form.get("output_name", "ConvertedPDF")

    with tempfile.TemporaryDirectory() as tmpdir:
        input_path = os.path.join(tmpdir, secure_filename(word_file.filename))
        output_path = os.path.join(tmpdir, f"{secure_filename(output_name)}.pdf")
        word_file.save(input_path)
        docx2pdf.convert(input_path, output_path)
        with open(output_path, "rb") as f:
            pdf_bytes = f.read()
    return send_file(BytesIO(pdf_bytes), as_attachment=True, download_name=f"{secure_filename(output_name)}.pdf")

# ---------- PDF TO WORD ----------
@app.route("/pdf_to_word", methods=["POST"])
def pdf_to_word():
    file = request.files["pdf_file"]
    output_name = request.form.get("output_name", "ConvertedWord")

    pdf = fitz.open(stream=file.read(), filetype="pdf")
    text = "\n\n".join([page.get_text() for page in pdf])
    doc_stream = BytesIO()
    from docx import Document
    doc = Document()
    doc.add_paragraph(text)
    doc.save(doc_stream)
    doc_stream.seek(0)
    return send_file(doc_stream, as_attachment=True, download_name=f"{secure_filename(output_name)}.docx")

# ---------- IMAGE COMPRESSOR ----------
@app.route("/compress_image", methods=["POST"])
def compress_image():
    file = request.files["image_file"]
    quality = int(request.form.get("quality", 70))
    output_name = request.form.get("output_name", "CompressedImage")

    image = Image.open(file.stream)
    output_stream = BytesIO()
    image.save(output_stream, format="JPEG", quality=quality)
    output_stream.seek(0)

    return send_file(output_stream, as_attachment=True, download_name=f"{secure_filename(output_name)}.jpg")


genai.configure(api_key=GEMINI_API_KEY)

# Use the Gemini model
model = genai.GenerativeModel("gemini-pro")

def summarize_pdf(pdf_bytes):
    # Encode PDF to base64
    encoded_pdf = base64.b64encode(pdf_bytes).decode("utf-8")

    # Prepare content parts
    contents = [
        {
            "inline_data": {
                "mime_type": "application/pdf",
                "data": encoded_pdf
            }
        },
        {
            "text": "Summarize this PDF document."
        }
    ]

    # Generate summary
    response = model.generate_content(contents)
    return response.text

    
# @app.route("/generate_subtopics", methods=["POST"])
# def generate_subtopics():
#     topic = request.form.get("topic", "").strip()
#     if not topic:
#         return "Topic is required", 400
#     subtopics = get_subtopics(topic)
#     return jsonify(subtopics=subtopics)

# @app.route("/generate_notes", methods=["POST"])
# def generate_notes():
#     selected = request.form.getlist("subtopics")
#     if not selected:
#         return "No subtopics selected", 400
#     notes = get_notes(selected)
#     return jsonify(notes=notes)


if __name__ == "__main__":
    app.run(debug=True)