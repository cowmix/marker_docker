import traceback
import click
import os
import img2pdf
from PIL import Image
import uvicorn
from pydantic import BaseModel, Field
from starlette.responses import HTMLResponse
import mimetypes
from marker.config.parser import ConfigParser
from marker.output import text_from_rendered
import base64
from contextlib import asynccontextmanager
from typing import Optional, Annotated
import io
from fastapi import FastAPI, Form, File, UploadFile
from marker.converters.pdf import PdfConverter
from marker.models import create_model_dict
from marker.settings import settings

app_data = {}

UPLOAD_DIRECTORY = "./uploads"
os.makedirs(UPLOAD_DIRECTORY, exist_ok=True)

SUPPORTED_IMAGE_TYPES = {
    'image/jpeg', 'image/png', 'image/tiff', 'image/bmp', 'image/webp'
}

def convert_image_to_pdf(image_path: str) -> str:
    """Convert an image file to PDF format.
    
    Args:
        image_path: Path to the input image file
        
    Returns:
        Path to the generated PDF file
    """
    pdf_path = os.path.splitext(image_path)[0] + '.pdf'
    
    # Open and convert image if needed
    with Image.open(image_path) as img:
        # Convert to RGB if image is in RGBA mode
        if img.mode in ('RGBA', 'LA'):
            background = Image.new('RGB', img.size, 'white')
            background.paste(img, mask=img.split()[-1])
            img = background
        
        # Save as PDF
        if img.mode not in ('RGB', 'L'):
            img = img.convert('RGB')
            
        with open(pdf_path, 'wb') as f:
            f.write(img2pdf.convert(image_path))
    
    return pdf_path

@asynccontextmanager
async def lifespan(app: FastAPI):
    app_data["models"] = create_model_dict()
    yield
    if "models" in app_data:
        del app_data["models"]

def create_app(root_path: str = "") -> FastAPI:
    app = FastAPI(
        lifespan=lifespan,
        root_path=root_path,
    )

    @app.get("/")
    async def root():
        return HTMLResponse(
            f"""
    <h1>Marker API</h1>
    <ul>
        <li><a href="{root_path}/docs">API Documentation</a></li>
        <li><a href="{root_path}/marker">Run marker (post request only)</a></li>
    </ul>
    """
        )

    class CommonParams(BaseModel):
        filepath: Annotated[
            Optional[str], Field(description="The path to the PDF/image file to convert.")
        ]
        page_range: Annotated[
            Optional[str],
            Field(description="Page range to convert, specify comma separated page numbers or ranges. Example: 0,5-10,20", example=None)
        ] = None
        languages: Annotated[
            Optional[str],
            Field(description="Comma separated list of languages to use for OCR. Must be either the names or codes from from https://github.com/VikParuchuri/surya/blob/master/surya/languages.py.", example=None)
        ] = None
        force_ocr: Annotated[
            bool,
            Field(
                description="Force OCR on all pages of the PDF. Defaults to False. This can lead to worse results if you have good text in your PDFs (which is true in most cases)."
            ),
        ] = False
        paginate_output: Annotated[
            bool,
            Field(
                description="Whether to paginate the output. Defaults to False. If set to True, each page of the output will be separated by a horizontal rule that contains the page number."
            ),
        ] = False
        output_format: Annotated[
            str,
            Field(description="The format to output the text in. Can be 'markdown', 'json', or 'html'. Defaults to 'markdown'.")
        ] = "markdown"

    async def _convert_pdf(params: CommonParams):
        assert params.output_format in ["markdown", "json", "html"], "Invalid output format"
        try:
            options = params.model_dump()
            print(options)
            config_parser = ConfigParser(options)
            config_dict = config_parser.generate_config_dict()
            config_dict["pdftext_workers"] = 1
            converter = PdfConverter(
                config=config_dict,
                artifact_dict=app_data["models"],
                processor_list=config_parser.get_processors(),
                renderer=config_parser.get_renderer()
            )
            rendered = converter(params.filepath)
            text, _, images = text_from_rendered(rendered)
            metadata = rendered.metadata
        except Exception as e:
            traceback.print_exc()
            return {
                "success": False,
                "error": str(e),
            }

        encoded = {}
        for k, v in images.items():
            byte_stream = io.BytesIO()
            v.save(byte_stream, format=settings.OUTPUT_IMAGE_FORMAT)
            encoded[k] = base64.b64encode(byte_stream.getvalue()).decode(settings.OUTPUT_ENCODING)

        return {
            "format": params.output_format,
            "output": text,
            "images": encoded,
            "metadata": metadata,
            "success": True,
        }

    @app.post("/marker")
    async def convert_pdf(params: CommonParams):
        return await _convert_pdf(params)

    @app.post("/marker/upload")
    async def convert_pdf_upload(
        page_range: Optional[str] = Form(default=None),
        languages: Optional[str] = Form(default=None),
        force_ocr: Optional[bool] = Form(default=False),
        paginate_output: Optional[bool] = Form(default=False),
        output_format: Optional[str] = Form(default="markdown"),
        file: UploadFile = File(
            ..., description="The PDF or image file to convert.",
            media_type="application/pdf,image/jpeg,image/png,image/tiff,image/bmp,image/webp"
        ),
    ):
        upload_path = os.path.join(UPLOAD_DIRECTORY, file.filename)
        with open(upload_path, "wb+") as upload_file:
            file_contents = await file.read()
            upload_file.write(file_contents)

        # Check if the uploaded file is an image
        mime_type, _ = mimetypes.guess_type(upload_path)
        if mime_type in SUPPORTED_IMAGE_TYPES:
            # Convert image to PDF
            pdf_path = convert_image_to_pdf(upload_path)
            # Clean up original image
            os.remove(upload_path)
            upload_path = pdf_path

        params = CommonParams(
            filepath=upload_path,
            page_range=page_range,
            languages=languages,
            force_ocr=force_ocr,
            paginate_output=paginate_output,
            output_format=output_format,
        )
        
        results = await _convert_pdf(params)
        os.remove(upload_path)
        return results

    return app

@click.command()
@click.option("--port", type=int, default=8000, help="Port to run the server on")
@click.option("--host", type=str, default="127.0.0.1", help="Host to run the server on")
@click.option("--root-path", type=str, default="", help="Root path for the application (e.g., /api/marker)")
def main(port: int, host: str, root_path: str):
    app = create_app(root_path)
    uvicorn.run(
        app,
        host=host,
        port=port,
    )

if __name__ == "__main__":
    main()