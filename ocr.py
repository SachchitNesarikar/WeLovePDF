import pytesseract
from pdf2image import convert_from_bytes
from PIL import Image
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

pytesseract.pytesseract.tesseract_cmd = r"/usr/bin/tesseract"

def ocr_image_to_text(image_bytes):
    try:
        image = Image.open(BytesIO(image_bytes))
        text = pytesseract.image_to_string(image)
        return text
    except Exception as e:
        return f"Error during OCR: {str(e)}"

def ocr_pdf_to_text(pdf_bytes):
    try:
        images = convert_from_bytes(pdf_bytes, dpi=300)
        text = ""
        for img in images:
            text += pytesseract.image_to_string(img) + "\n\n"
        return text
    except Exception as e:
        return f"Error during PDF OCR: {str(e)}"

def text_to_pdf(text, output_pdf_path):
    try:
        c = canvas.Canvas(output_pdf_path, pagesize=letter)
        width, height = letter
        
        c.setFont("Helvetica", 10)
        line_height = 12
        margin = 40
        y_position = height - margin

        lines = text.split("\n")
        
        for line in lines:
            if y_position < margin:
                c.showPage()
                c.setFont("Helvetica", 10)
                y_position = height - margin

            c.drawString(margin, y_position, line)
            y_position -= line_height
        
        c.save()
        return f"PDF saved to {output_pdf_path}"
    except Exception as e:
        return f"Error generating PDF: {str(e)}"