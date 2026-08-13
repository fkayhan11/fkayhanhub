FROM python:3.10-slim

# Install system dependencies (Tesseract OCR, OpenCV dependencies)
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-tur \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all project files
COPY . .

# Expose port (Render sets PORT env variable)
EXPOSE 5005

# Run the server
CMD ["python", "excel_server.py"]
