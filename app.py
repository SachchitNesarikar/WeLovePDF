from flask import Flask, render_template, request, send_file
from PyPDF2 import PdfReader, PdfWriter, PdfMerger
from PIL import Image
from io import BytesIO
from werkzeug.utils import secure_filename

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

<<<<<<< HEAD
    return send_file(output_path, as_attachment=True)

# ---------- COMPRESS PDF ----------
@app.route("/compress", methods=["POST"])
def compress_pdf():
    file = request.files["pdf_file"]
    quality = request.form.get("quality", "medium")  # user can choose compression level
    output_name = request.form.get("output_name", "compressed")

    if not file or not file.filename.endswith(".pdf"):
        return "Please upload a valid PDF file", 400

    filename = secure_filename(file.filename)
    input_path = os.path.join(UPLOAD_FOLDER, filename)
    output_path = os.path.join(OUTPUT_FOLDER, f"{secure_filename(output_name)}.pdf")

    file.save(input_path)

    try:
        from PyPDF2 import PdfReader, PdfWriter
        reader = PdfReader(input_path)
        writer = PdfWriter()

        
        for page in reader.pages:
            page.compress_content_streams()  
            writer.add_page(page)

        with open(output_path, "wb") as f:
            writer.write(f)

    except Exception as e:
        return f"Error compressing PDF: {e}", 500

    return send_file(output_path, as_attachment=True)

=======
    output_filename = f"{secure_filename(custom_name)}.pdf"
    return send_file(output_stream, as_attachment=True, download_name=output_filename)
>>>>>>> fa5cdd5ecdc9ea2f74f24f9e7a8e4d64fdcdd47a

if __name__ == "__main__":
    app.run(debug=True)


