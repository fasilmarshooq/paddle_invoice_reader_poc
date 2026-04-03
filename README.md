# Paddle.AI

An intelligent invoice processing application that automatically detects document types and extracts invoice numbers from PDFs and images using OCR technology.

## Features

- 📄 Upload PDF or Image files (JPEG, PNG)
- 🔍 OCR text extraction using PaddleOCR
- 🏷️ Automatic document type detection (Tax Invoice vs Tax Credit Note)
- 🔢 Smart invoice number extraction
- 💾 SQLite database for invoice history
- 🗑️ Delete invoices you no longer need
- 🎨 Modern React UI with drag-and-drop upload

## Tech Stack

**Frontend:**
- React 18
- Vite
- Tailwind CSS
- Axios

**Backend:**
- FastAPI (Python)
- PaddleOCR
- PyMuPDF (PDF processing)
- SQLite

**Infrastructure:**
- Docker with multi-stage build
- Single container deployment

## Quick Start

### Run the Application

```bash
./start.sh
```

This script will:
1. Check if Docker is installed
2. Build the Docker image
3. Create necessary directories
4. Start the container
5. Make the app available at http://localhost:8000

### Stop the Application

```bash
./stop.sh
```

## Usage

1. Open http://localhost:8000 in your browser
2. Drag and drop an invoice PDF or image file
3. Wait for processing (5-10 seconds)
4. View the extracted information in the history table
5. Click "View" to open the original file
6. Click "Delete" to remove an invoice

## API Endpoints

- `POST /api/upload` - Upload and process invoice
- `GET /api/history` - Retrieve all processed invoices
- `GET /api/pdf/{filename}` - View uploaded file
- `DELETE /api/invoice/{id}` - Delete invoice by ID
- `GET /health` - Health check

## Data Storage

All data is persisted in the `data/` directory:
- `data/uploads/` - Uploaded PDF and image files
- `data/db/` - SQLite database (invoices.db)

Data persists across container restarts.

## How It Works

1. **Upload**: User uploads a PDF or image file
2. **Text Extraction**:
   - PDFs: Try native text extraction first, fallback to OCR
   - Images: Direct OCR processing
3. **Document Detection**: Identify keywords for "Tax Invoice" or "Tax Credit Note"
4. **Number Extraction**: Use regex patterns to find 12-digit invoice numbers
5. **Storage**: Save metadata to SQLite and file to disk
6. **Display**: Show results in the web interface

## Development

### Backend (Local)
```bash
cd backend
pip install -r requirements.txt
pip install PyMuPDF
uvicorn main:app --reload --port 8000
```

### Frontend (Local)
```bash
cd frontend
npm install
npm run dev
```

Frontend dev server runs at http://localhost:5173 with API proxy to backend.

## Docker Commands

### View Logs
```bash
docker logs -f paddle-ai
```

### Access Container Shell
```bash
docker exec -it paddle-ai bash
```

### Rebuild
```bash
docker-compose up --build
```

### Build & Push
```bash
docker build -t ghcr.io/fasilmarshooq/invoicereaderpoc:latest .
docker push ghcr.io/fasilmarshooq/invoicereaderpoc:latest
```

### Multi-Platform Build & Push (requires buildx)
```bash
docker buildx build --builder multiplatform --platform linux/amd64,linux/arm64 -t ghcr.io/fasilmarshooq/invoicereaderpoc:latest --push .
```

## Requirements

- Docker (with docker-compose)
- 4GB+ RAM recommended for OCR processing

## License

MIT
