import os
from dotenv import load_dotenv
load_dotenv()
import shutil
import tempfile
from fastapi import FastAPI, UploadFile, File, HTTPException, Form, Security, Depends, Request
from fastapi.security.api_key import APIKeyHeader
from app.services.score import evaluate_pdf
from fastapi.responses import RedirectResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import uvicorn
import sys
from contextlib import asynccontextmanager

# Ensure stdout uses utf-8 to prevent crashes when printing emojis on Windows
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Setup Rate Limiting
limiter = Limiter(key_func=get_remote_address)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Validate LLM provider configuration
    from app.core.prompt import DEFAULT_MODEL
    from app.utils.llm_utils import initialize_llm_provider
    import logging
    try:
        if not os.getenv("API_KEY"):
            raise RuntimeError("API_KEY environment variable is not set. Refusing to start with insecure default.")
            
        # This will raise a RuntimeError if the required API key is missing
        initialize_llm_provider(DEFAULT_MODEL)
        logging.info(f"Successfully validated LLM provider for model: {DEFAULT_MODEL}")
    except RuntimeError as e:
        logging.critical(f"Startup failed: {str(e)}")
        sys.exit(1)
    yield

app = FastAPI(
    title="CV ATS API",
    description="Evaluate resume ATS compatibility, formatting, and structure.",
    version="1.0.0",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# API Key Security
API_KEY = os.getenv("API_KEY")
API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

async def get_api_key(api_key_header: str = Security(api_key_header)):
    if api_key_header == API_KEY:
        return api_key_header
    raise HTTPException(
        status_code=403, detail="Could not validate credentials"
    )

@app.get("/")
async def root():
    """Redirect to the API documentation."""
    return RedirectResponse(url="/docs")

@app.post("/evaluate")
@limiter.limit("5/minute")
def evaluate(
    request: Request,
    file: UploadFile = File(...),
    api_key: str = Depends(get_api_key)
):
    """
    Evaluate a resume PDF file for ATS compatibility, formatting issues, and structure.
    """
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    # Note: We rely on the PyMuPDF parser in evaluate_pdf to reject corrupt or 
    # non-PDF files that bypassed the extension check, which will be caught by the generic exception handler.

    # Save uploaded file to a temporary directory
    temp_dir = tempfile.mkdtemp()
    temp_pdf_path = os.path.join(temp_dir, "upload.pdf")

    try:
        # Check file size before saving (limit to 10MB)
        file.file.seek(0, 2)
        file_size = file.file.tell()
        file.file.seek(0)
        
        if file_size > 10 * 1024 * 1024:
            raise HTTPException(status_code=413, detail="File too large. Maximum size is 10MB.")

        with open(temp_pdf_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Process the PDF using the existing ATS logic, bypassing cache for the API route
        result = evaluate_pdf(temp_pdf_path, use_cache=False)

        if result is None:
            raise HTTPException(
                status_code=500, detail="Failed to evaluate the resume. Result was None."
            )

        return result.model_dump()

    except HTTPException:
        raise
    except Exception as e:
        import logging
        logging.error(f"Internal server error during evaluation: {str(e)}")
        raise HTTPException(status_code=500, detail="An internal server error occurred while processing the resume.")
    finally:
        # Clean up the temporary directory
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000)
