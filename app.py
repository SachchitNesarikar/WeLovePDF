from flask import Flask, render_template, request, send_file
from PyPDF2 import PdfReader, PdfWriter, PdfMerger
from PIL import Image
from io import BytesIO
from werkzeug.utils import secure_filename
import zipfile
import docx2pdf
import tempfile
import os
from dotenv import load_dotenv
import base64
import google.generativeai as genai
from pdfminer.high_level import extract_text
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from docx import Document

# Load environment variables
load_dotenv()

# Configure Gemini API
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-2.5-flash")

# Flask app
app = Flask(__name__)

# ---------- HELPERS ----------
def extract_text_with_pdfminer(pdf_bytes):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(pdf_bytes)
        tmp_path = tmp.name
    return extract_text(tmp_path)

# ---------- ROUTES ----------
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
    uploaded_files = request.files.getlist("pdf_files")
    if not uploaded_files or all(f.filename == "" for f in uploaded_files):
        return "No files uploaded", 400
    for file in uploaded_files:
        if file and file.filename:
            merger.append(file.stream)
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

# ---------- DELETE PAGES ----------
@app.route("/delete_pages", methods=["POST"])
def delete_pages():
    file = request.files["pdf_file"]
    cfpages_to_delete = request.form.get("pages_to_delete", "").strip()
    output_name = request.form.get("output_name", "DeletedPages")

    if not file or not file.filename.endswith(".pdf"):
        return "Please upload a valid PDF file", 400
    if not pages_to_delete:
        return "Please specify page numbers to delete", 400

    # Parse pages like "1,3,5-7"
    pages_to_delete_set = set()
    for part in pages_to_delete.split(","):
        part = part.strip()
        if "-" in part:
            start, end = map(int, part.split("-"))
            pages_to_delete_set.update(range(start - 1, end))
        else:
            pages_to_delete_set.add(int(part) - 1)

    reader = PdfReader(file.stream)
    writer = PdfWriter()

    for i, page in enumerate(reader.pages):
        if i not in pages_to_delete_set:
            writer.add_page(page)

    output_stream = BytesIO()
    writer.write(output_stream)
    output_stream.seek(0)

    return send_file(output_stream, as_attachment=True, download_name=f"{secure_filename(output_name)}.pdf")

# ---------- WORD TO PDF ----------
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

    reader = PdfReader(file.stream)
    text = "\n\n".join([page.extract_text() or "" for page in reader.pages])

    doc_stream = BytesIO()
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

# ---------- ANALYSE PDF ----------
@app.route("/analyse_pdf", methods=["POST"])
def analyse_pdf():
    file = request.files.get("pdf_file")
    if not file or not file.filename.endswith(".pdf"):
        return "Please upload a valid PDF file", 400

    try:
        pdf_bytes = file.read()
        output_name = secure_filename(file.filename)
        extracted_text = extract_text_with_pdfminer(pdf_bytes)

        prompt = f"Summarize the following PDF content:\n\n{extracted_text}"
        response = model.generate_content(prompt)
        summary = response.text

        return f"""
            <h2>Summary of {output_name}</h2>
            <div style="white-space: pre-wrap; font-family: sans-serif; line-height: 1.5;">
                {summary}
            </div>
        """
    except Exception as e:
        return f"Error analyzing PDF: {str(e)}", 500

# ---------- OCR (TEXT EXTRACTION) ----------
@app.route("/ocr_pdf", methods=["POST"])
def ocr_pdf():
    file = request.files.get("pdf_file")
    output_name = request.form.get("output_name", "OCRText")

    if not file or not file.filename.endswith(".pdf"):
        return "Please upload a valid PDF file", 400

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(file.read())
            tmp_path = tmp.name

        text = extract_text(tmp_path)
        output_stream = BytesIO()
        output_stream.write(text.encode("utf-8"))
        output_stream.seek(0)

        return send_file(output_stream, as_attachment=True, download_name=f"{secure_filename(output_name)}.txt")
    except Exception as e:
        return f"OCR failed: {str(e)}", 500

# ---------- EDIT PDF ----------
@app.route("/edit_pdf", methods=["POST"])
def edit_pdf():
    file = request.files.get("pdf_file")
    edit_text = request.form.get("edit_text", "").strip()
    page_number = int(request.form.get("page_number", 1)) - 1
    output_name = request.form.get("output_name", "EditedPDF")

    if not file or not file.filename.endswith(".pdf"):
        return "Please upload a valid PDF file", 400
    if not edit_text:
        return "Please enter text to add", 400

    try:
        overlay_stream = BytesIO()
        c = canvas.Canvas(overlay_stream, pagesize=letter)
        c.drawString(72, 720, edit_text)
        c.save()
        overlay_stream.seek(0)

        reader = PdfReader(file.stream)
        overlay_reader = PdfReader(overlay_stream)
        writer = PdfWriter()

        for i, page in enumerate(reader.pages):
            if i == page_number:
                page.merge_page(overlay_reader.pages[0])
            writer.add_page(page)

        output_stream = BytesIO()
        writer.write(output_stream)
        output_stream.seek(0)

        return send_file(output_stream, as_attachment=True, download_name=f"{secure_filename(output_name)}.pdf")
    except Exception as e:
        return f"PDF edit failed: {str(e)}", 500


# ---------- RUN ----------
if __name__ == "__main__":
    app.run(debug=True)
