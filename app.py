from flask import Flask, render_template, request, send_file
from PyPDF2 import PdfReader, PdfWriter, PdfMerger
from PIL import Image
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
UPLOAD_FOLDER = "uploads"
OUTPUT_FOLDER = "outputs"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)


@app.route("/")
def index():
    return render_template("index.html")


# ---------- IMAGE TO PDF ----------
@app.route("/image_to_pdf", methods=["POST"])
def image_to_pdf():
    files = request.files.getlist("image_files")
    output_name = request.form.get("output_name", "image_to_pdf")

    image_list = []
    for file in files:
        if file and file.filename:
            filename = secure_filename(file.filename)
            filepath = os.path.join(UPLOAD_FOLDER, filename)
            file.save(filepath)
            image = Image.open(filepath).convert("RGB")
            image_list.append(image)

    if not image_list:
        return "No valid images uploaded", 400

    output_path = os.path.join(OUTPUT_FOLDER, f"{secure_filename(output_name)}.pdf")
    first_image = image_list[0]
    other_images = image_list[1:] if len(image_list) > 1 else []
    first_image.save(output_path, save_all=True, append_images=other_images)

    return send_file(output_path, as_attachment=True)


# ---------- SPLIT PDF ----------
@app.route("/split", methods=["POST"])
def split_pdf():
    file = request.files["pdf_file"]
    start_page = int(request.form.get("start_page")) - 1
    end_page = int(request.form.get("end_page"))
    custom_name = request.form.get("output_name", "split")

    filename = secure_filename(file.filename)
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    file.save(filepath)

    reader = PdfReader(filepath)
    writer = PdfWriter()

    for i in range(start_page, end_page):
        writer.add_page(reader.pages[i])

    output_filename = f"{secure_filename(custom_name)}.pdf"
    output_path = os.path.join(OUTPUT_FOLDER, output_filename)
    with open(output_path, "wb") as f:
        writer.write(f)

    return send_file(output_path, as_attachment=True)


# ---------- MERGE PDF (UP TO 3 FILES) ----------
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
            filename = secure_filename(file.filename)
            filepath = os.path.join(UPLOAD_FOLDER, filename)
            file.save(filepath)
            merger.append(filepath)
            any_uploaded = True

    if not any_uploaded:
        return "No files uploaded", 400

    output_filename = f"{secure_filename(custom_name)}.pdf"
    output_path = os.path.join(OUTPUT_FOLDER, output_filename)
    merger.write(output_path)
    merger.close()

    return send_file(output_path, as_attachment=True)


if __name__ == "__main__":
    app.run(debug=True)
