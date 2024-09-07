import os
from django.shortcuts import render
from django.conf import settings
from django.http import HttpResponse
from .forms import UploadFileForm
from PyPDF2 import PdfReader
from googletrans import Translator
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from io import BytesIO
import logging

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Updated map of supported languages to match form values
LANGUAGE_CODES = {
    "en": "en",
    "hi": "hi",
    "te": "te",
    "mr": "mr",
    "pa": "pa",
    "tulu": None,  # Google Translate doesn't support Tulu
}

# Font mapping for Indian languages with direct paths
LANGUAGE_FONTS = {
    "hi": ("C:\\Users\\shali\\Downloads\\gargi.ttf", "Gargi"),
    "te": ("C:\\Users\shali\\Downloads\\Lohit-Telugu.ttf", "Lohit-Telugu"),
    "mr": ("C:\\Users\\shali\Downloads\\YashomudraSemiBold_Italic.ttf", "Lohit-Marathi"),
    "pa": ("C:\\Users\\shali\Downloads\\Lohit-Gurmukhi.ttf", "Lohit-Punjabi"),
}

def handle_uploaded_file(f, filename):
    """Save the uploaded file to the media folder."""
    save_path = os.path.join(settings.MEDIA_ROOT, filename)
    with open(save_path, "wb+") as destination:
        for chunk in f.chunks():
            destination.write(chunk)
    return save_path

def read_file_content(file_path):
    """Read the content of the file based on its type."""
    file_extension = os.path.splitext(file_path)[1].lower()
    try:
        if file_extension in [".txt", ".md", ".csv"]:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()  # Read the entire file
        elif file_extension == ".pdf":
            reader = PdfReader(file_path)
            text = ""
            for page in reader.pages:
                text += page.extract_text()  # Extract text from all pages
            return text
        else:
            raise ValueError(f"Unsupported file format: {file_extension}")
    except Exception as e:
        raise ValueError(f"Error reading file: {str(e)}")

def create_pdf(content, filename, language):
    """Create a PDF file with the given content using appropriate font."""
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    y = height - 40

    # Use appropriate font for the language
    if language in LANGUAGE_FONTS:
        font_path, font_name = LANGUAGE_FONTS[language]
        try:
            logger.debug(f"Attempting to register font: {font_path}")
            pdfmetrics.registerFont(TTFont(font_name, font_path))
            p.setFont(font_name, 12)
            logger.debug(f"Successfully registered and set font: {font_name}")
        except Exception as e:
            logger.error(f"Error registering font {font_name}: {str(e)}")
            logger.warning(f"Falling back to default font for {language}")
            p.setFont("Helvetica", 12)
    else:
        logger.debug(f"No specific font defined for {language}. Using default font.")
        p.setFont("Helvetica", 12)

    try:
        for line in content.split("\n"):
            if y < 40:
                p.showPage()
                y = height - 40
            p.drawString(40, y, line)
            y -= 15
        p.showPage()
        p.save()
        buffer.seek(0)
        return buffer
    except Exception as e:
        logger.error(f"Error creating PDF: {str(e)}")
        raise

def translate_text(content, target_language):
    """Use googletrans to translate the content into the target language."""
    translator = Translator()

    # Check if the language is supported
    if target_language not in LANGUAGE_CODES or LANGUAGE_CODES[target_language] is None:
        raise ValueError(f"Translation for {target_language} is not supported.")

    try:
        translation = translator.translate(
            content, dest=LANGUAGE_CODES[target_language]
        )
        logger.debug(
            f"Translation result: {translation.text[:100]}..."
        )  # Log first 100 chars
        return translation.text
    except Exception as e:
        logger.error(f"Translation error: {str(e)}")
        raise ValueError(f"Translation error: {str(e)}")

def upload_and_translate(request):
    if request.method == "POST":
        form = UploadFileForm(request.POST, request.FILES)
        if form.is_valid():
            file = request.FILES["file"]
            target_language = form.cleaned_data["target_language"]

            if target_language not in LANGUAGE_CODES:
                return render(
                    request,
                    "upload.html",
                    {
                        "form": form,
                        "error_message": f"Unsupported language: {target_language}",
                    },
                )

            try:
                file_path = handle_uploaded_file(file, file.name)
                content = read_file_content(file_path)

                if not content:
                    return render(
                        request,
                        "upload.html",
                        {
                            "form": form,
                            "error_message": "The file is empty or contains no readable content.",
                        },
                    )

                # Check for Tulu or translate for other languages
                if LANGUAGE_CODES[target_language] is None:
                    translated_content = f"Translation for {target_language.capitalize()} is not supported yet."
                else:
                    translated_content = translate_text(content, target_language)

                # Create PDF
                pdf_buffer = create_pdf(translated_content, file.name, target_language)

                # Prepare response
                response = HttpResponse(
                    pdf_buffer.getvalue(), content_type="application/pdf"
                )
                response["Content-Disposition"] = (
                    f'attachment; filename="{file.name}_translated_{target_language}.pdf"'
                )
                return response
            except Exception as e:
                logger.error(f"Error in upload_and_translate: {str(e)}")
                return render(
                    request,
                    "upload.html",
                    {"form": form, "error_message": f"An error occurred: {str(e)}"},
                )
    else:
        form = UploadFileForm()
    return render(request, "upload.html", {"form": form})
