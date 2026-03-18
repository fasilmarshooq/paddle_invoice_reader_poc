import os
import re
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List, Dict
import io

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from paddleocr import PaddleOCR
from PIL import Image
import fitz  # PyMuPDF

# Initialize FastAPI app
app = FastAPI(title="InvoiceAI")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Directories
UPLOAD_DIR = Path("/app/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
DB_DIR = Path("/app/db")
DB_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DB_DIR / "invoices.db"

# Initialize PaddleOCR with Arabic and English support
ocr = PaddleOCR(
    use_angle_cls=True,
    lang='en',  # Can add 'arabic_ocr' if needed
    use_gpu=False,
    show_log=False
)

# Initialize SQLite database
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS invoices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_number TEXT NOT NULL,
            document_type TEXT NOT NULL,
            filename TEXT NOT NULL,
            filepath TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

init_db()


def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """Extract text from PDF using PyMuPDF first, fallback to OCR"""
    try:
        # Try text extraction first (faster)
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        text = ""
        for page in doc:
            text += page.get_text()
        doc.close()

        if text.strip():
            return text
    except Exception as e:
        print(f"PDF text extraction failed: {e}")

    # Fallback to OCR
    return extract_text_with_ocr(pdf_bytes, is_pdf=True)


def extract_text_with_ocr(file_bytes: bytes, is_pdf: bool = False) -> str:
    """Extract text using PaddleOCR"""
    try:
        if is_pdf:
            # Convert PDF to images
            doc = fitz.open(stream=file_bytes, filetype="pdf")
            text = ""
            for page_num in range(len(doc)):
                page = doc[page_num]
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # 2x zoom for better OCR
                img_bytes = pix.tobytes("png")
                img = Image.open(io.BytesIO(img_bytes))

                # Run OCR
                result = ocr.ocr(img_bytes, cls=True)
                if result and result[0]:
                    text += "\n".join([line[1][0] for line in result[0]])
            doc.close()
            return text
        else:
            # Direct image OCR
            img = Image.open(io.BytesIO(file_bytes))
            result = ocr.ocr(file_bytes, cls=True)
            if result and result[0]:
                return "\n".join([line[1][0] for line in result[0]])
            return ""
    except Exception as e:
        print(f"OCR extraction failed: {e}")
        return ""


def detect_document_type(text: str) -> str:
    """Detect if document is Tax Invoice or Tax Credit Note"""
    text_upper = text.upper()

    # Check for credit note keywords
    credit_keywords = [
        "TAX CREDIT NOTE",
        "CREDIT NOTE",
        "إشعار دائن",
        "إشعار ائتمان"
    ]

    # Check for invoice keywords
    invoice_keywords = [
        "TAX INVOICE",
        "INVOICE",
        "فاتورة الضريبة",
        "فاتورة"
    ]

    # Priority: Credit Note detection
    for keyword in credit_keywords:
        if keyword in text_upper or keyword in text:
            return "Tax Credit Note"

    # Check for invoice
    for keyword in invoice_keywords:
        if keyword in text_upper or keyword in text:
            return "Tax Invoice"

    return "Unknown"


def extract_invoice_number(text: str) -> str:
    """Extract 12-digit invoice number using regex"""
    # Pattern 1: TAX INVOICE# or TAX CREDIT NOTE followed by 12 digits
    patterns = [
        r'TAX\s+(?:CREDIT\s+NOTE|INVOICE)\s*[#:]?\s*(\d{12})',
        r'(?:INVOICE|CREDIT\s+NOTE)\s*(?:NUMBER|NO\.?|#)?\s*[:]?\s*(\d{12})',
        r'(?:رقم|الرقم)\s*(?:الفاتورة|الإشعار)?\s*[:]?\s*(\d{12})',
        r'\b(\d{12})\b'  # Fallback: any 12-digit number
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1)

    return "Not Found"


@app.post("/api/upload")
async def upload_invoice(file: UploadFile = File(...)):
    """Upload and process invoice"""
    try:
        # Validate file type
        if not file.content_type in ["application/pdf", "image/jpeg", "image/png", "image/jpg"]:
            raise HTTPException(status_code=400, detail="Only PDF and image files are supported")

        # Read file
        file_bytes = await file.read()

        # Generate unique filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_{file.filename}"
        filepath = UPLOAD_DIR / filename

        # Save file
        with open(filepath, "wb") as f:
            f.write(file_bytes)

        # Extract text
        if file.content_type == "application/pdf":
            text = extract_text_from_pdf(file_bytes)
        else:
            text = extract_text_with_ocr(file_bytes, is_pdf=False)

        # Detect document type
        doc_type = detect_document_type(text)

        # Extract invoice number
        invoice_number = extract_invoice_number(text)

        # Save to database
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO invoices (invoice_number, document_type, filename, filepath) VALUES (?, ?, ?, ?)",
            (invoice_number, doc_type, filename, str(filepath))
        )
        conn.commit()
        invoice_id = cursor.lastrowid
        conn.close()

        return JSONResponse({
            "success": True,
            "id": invoice_id,
            "invoice_number": invoice_number,
            "document_type": doc_type,
            "filename": filename
        })

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/history")
async def get_history():
    """Get all processed invoices"""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM invoices ORDER BY created_at DESC")
        rows = cursor.fetchall()
        conn.close()

        invoices = []
        for row in rows:
            invoices.append({
                "id": row["id"],
                "invoice_number": row["invoice_number"],
                "document_type": row["document_type"],
                "filename": row["filename"],
                "created_at": row["created_at"]
            })

        return JSONResponse({"invoices": invoices})

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/pdf/{filename}")
async def get_pdf(filename: str):
    """Serve PDF file"""
    filepath = UPLOAD_DIR / filename
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(filepath)


@app.delete("/api/invoice/{invoice_id}")
async def delete_invoice(invoice_id: int):
    """Delete invoice by ID"""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Get invoice info
        cursor.execute("SELECT * FROM invoices WHERE id = ?", (invoice_id,))
        invoice = cursor.fetchone()

        if not invoice:
            conn.close()
            raise HTTPException(status_code=404, detail="Invoice not found")

        # Delete file from disk
        filepath = Path(invoice["filepath"])
        if filepath.exists():
            filepath.unlink()

        # Delete from database
        cursor.execute("DELETE FROM invoices WHERE id = ?", (invoice_id,))
        conn.commit()
        conn.close()

        return JSONResponse({"success": True, "message": "Invoice deleted successfully"})

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Serve React frontend (mount this last)
@app.get("/")
async def root():
    """Serve index.html"""
    return FileResponse("/app/frontend/dist/index.html")

# Mount static files
app.mount("/assets", StaticFiles(directory="/app/frontend/dist/assets"), name="assets")

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy"}
