"""PDF text extraction service.

Extracts readable text from PDF files for knowledge base ingestion.
"""

import logging
import io
from typing import BinaryIO

try:
    import pdfplumber
except ImportError:
    pdfplumber = None

logger = logging.getLogger(__name__)


async def extract_pdf_text(file_content: bytes, filename: str) -> dict:
    """Extract text content from a PDF file.

    Args:
        file_content: Raw bytes of the PDF file
        filename: Original filename (for logging/error messages)

    Returns:
        {"title": str, "content": str, "filename": str}

    Raises:
        ValueError: if PDF is unreadable or content is empty
        ImportError: if pdfplumber is not installed
    """
    if pdfplumber is None:
        raise ImportError(
            "pdfplumber is required for PDF extraction. "
            "Install with: pip install pdfplumber"
        )

    if len(file_content) == 0:
        raise ValueError(f"PDF file {filename} is empty")

    if len(file_content) > 50 * 1024 * 1024:  # 50MB limit
        raise ValueError(
            f"PDF file {filename} is too large ({len(file_content) / 1024 / 1024:.1f}MB). "
            "Maximum size: 50MB"
        )

    try:
        # pdfplumber works with file-like objects
        pdf_file = io.BytesIO(file_content)
        
        with pdfplumber.open(pdf_file) as pdf:
            if len(pdf.pages) == 0:
                raise ValueError(f"PDF {filename} has no pages")

            # Extract text from all pages
            text_parts = []
            for page_num, page in enumerate(pdf.pages, 1):
                page_text = page.extract_text()
                if page_text:
                    # Clean up excessive whitespace
                    page_text = page_text.strip()
                    if page_text:
                        text_parts.append(page_text)
                        logger.debug(
                            "Extracted %d chars from page %d of %s",
                            len(page_text), page_num, filename
                        )

            if not text_parts:
                raise ValueError(
                    f"PDF {filename} contains no extractable text. "
                    "The PDF may be image-based or encrypted."
                )

            # Combine all pages with page breaks
            full_text = "\n\n".join(text_parts)

            # Basic cleanup
            full_text = _clean_pdf_text(full_text)

            if len(full_text) < 50:
                raise ValueError(
                    f"Extracted text from {filename} is too short ({len(full_text)} chars). "
                    "The PDF may not contain meaningful content."
                )

            # Try to extract title from metadata or first line
            title = None
            try:
                if pdf.metadata and pdf.metadata.get("Title"):
                    title = pdf.metadata["Title"]
            except Exception:
                pass
            
            if not title:
                # Use first non-empty line as title
                first_line = full_text.split("\n")[0].strip()
                if first_line and len(first_line) < 200:
                    title = first_line
                else:
                    title = filename

            return {
                "title": title,
                "content": full_text,
                "filename": filename,
                "page_count": len(pdf.pages),
            }

    except pdfplumber.pdfminer.pdfdocument.PDFPasswordIncorrect:
        raise ValueError(f"PDF {filename} is password-protected and cannot be extracted")
    except Exception as e:
        logger.error("Failed to extract text from %s: %s", filename, e)
        raise ValueError(f"Failed to extract text from {filename}: {str(e)}")


def _clean_pdf_text(text: str) -> str:
    """Clean up extracted PDF text.
    
    - Normalize whitespace
    - Remove excessive line breaks
    - Fix common OCR issues
    """
    import re
    
    # Normalize line breaks (some PDFs have weird spacing)
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    # Remove lines that are just page numbers or headers/footers
    lines = text.split('\n')
    cleaned_lines = []
    for line in lines:
        line = line.strip()
        # Skip lines that are just page numbers (e.g. "Page 5" or "5")
        if re.match(r'^(page\s*)?\d+$', line, re.IGNORECASE):
            continue
        # Skip very short lines that look like artifacts
        if len(line) < 3 and not re.match(r'^[A-Z]\.?$', line):
            continue
        cleaned_lines.append(line)
    
    text = '\n'.join(cleaned_lines)
    
    # Normalize whitespace within lines
    text = re.sub(r'[ \t]+', ' ', text)
    
    # Final cleanup
    text = text.strip()
    
    return text
