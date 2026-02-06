"""
PDF Handler Module for SnowScrape

Provides PDF parsing capabilities including:
- Text extraction (full document or by page)
- Table extraction (structured data from tables)
- Metadata extraction

Uses pdfplumber for reliable text and table extraction.
"""

import io
import re
from typing import Any, Dict, List, Optional, Union
from logger import get_logger

logger = get_logger(__name__)


def extract_pdf_text(
    pdf_bytes: bytes,
    page_range: Optional[List[int]] = None,
    join_pages: bool = True
) -> Union[str, List[str]]:
    """
    Extract text content from a PDF.

    Args:
        pdf_bytes: Raw PDF file content as bytes
        page_range: Optional [start, end] page indices (0-based). None = all pages.
        join_pages: If True, join all page text into single string. If False, return list.

    Returns:
        Extracted text as string (if join_pages=True) or list of page texts
    """
    import pdfplumber

    pages_text = []

    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        total_pages = len(pdf.pages)

        # Determine page range
        if page_range:
            start = max(0, page_range[0])
            end = min(total_pages, page_range[1] + 1) if len(page_range) > 1 else start + 1
        else:
            start, end = 0, total_pages

        for i in range(start, end):
            page = pdf.pages[i]
            text = page.extract_text() or ""
            pages_text.append(text)

    if join_pages:
        return "\n\n".join(pages_text)
    return pages_text


def extract_pdf_tables(
    pdf_bytes: bytes,
    page_range: Optional[List[int]] = None,
    table_settings: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """
    Extract tables from a PDF.

    Args:
        pdf_bytes: Raw PDF file content as bytes
        page_range: Optional [start, end] page indices (0-based). None = all pages.
        table_settings: Optional pdfplumber table extraction settings

    Returns:
        List of tables, each containing:
        - page: Page number (0-based)
        - headers: List of column headers (first row)
        - rows: List of data rows (dicts with header keys)
        - raw: Raw 2D array of all cells
    """
    import pdfplumber

    tables = []
    settings = table_settings or {}

    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        total_pages = len(pdf.pages)

        # Determine page range
        if page_range:
            start = max(0, page_range[0])
            end = min(total_pages, page_range[1] + 1) if len(page_range) > 1 else start + 1
        else:
            start, end = 0, total_pages

        for page_num in range(start, end):
            page = pdf.pages[page_num]
            page_tables = page.extract_tables(table_settings=settings) if settings else page.extract_tables()

            for table_idx, table in enumerate(page_tables):
                if not table or len(table) == 0:
                    continue

                # Clean up cells (remove None, strip whitespace)
                cleaned_table = []
                for row in table:
                    cleaned_row = [
                        (cell.strip() if isinstance(cell, str) else (str(cell) if cell is not None else ""))
                        for cell in row
                    ]
                    cleaned_table.append(cleaned_row)

                # First row as headers
                headers = cleaned_table[0] if cleaned_table else []

                # Convert remaining rows to dicts
                rows = []
                for row in cleaned_table[1:]:
                    row_dict = {}
                    for i, cell in enumerate(row):
                        header = headers[i] if i < len(headers) else f"column_{i}"
                        # Clean up header name for dict key
                        header_key = header.replace("\n", " ").strip() if header else f"column_{i}"
                        row_dict[header_key] = cell
                    rows.append(row_dict)

                tables.append({
                    "page": page_num,
                    "table_index": table_idx,
                    "headers": headers,
                    "rows": rows,
                    "raw": cleaned_table
                })

    return tables


def extract_pdf_metadata(pdf_bytes: bytes) -> Dict[str, Any]:
    """
    Extract metadata from a PDF.

    Args:
        pdf_bytes: Raw PDF file content as bytes

    Returns:
        Dict containing PDF metadata (title, author, creation date, etc.)
    """
    import pdfplumber

    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        metadata = pdf.metadata or {}
        return {
            "title": metadata.get("Title", ""),
            "author": metadata.get("Author", ""),
            "subject": metadata.get("Subject", ""),
            "creator": metadata.get("Creator", ""),
            "producer": metadata.get("Producer", ""),
            "creation_date": metadata.get("CreationDate", ""),
            "modification_date": metadata.get("ModDate", ""),
            "page_count": len(pdf.pages),
        }


def process_pdf_query(
    pdf_bytes: bytes,
    query: Dict[str, Any]
) -> Any:
    """
    Process a single PDF query.

    Query structure:
    {
        "name": "field_name",
        "type": "pdf_text" | "pdf_table" | "pdf_metadata",
        "query": "optional regex pattern for text extraction",
        "join": bool (for joining results),
        "pdf_config": {
            "page_range": [start, end],  # Optional page range
            "table_index": 0,            # Optional: specific table index
            "flatten": true              # Optional: flatten table rows to list
        }
    }

    Args:
        pdf_bytes: Raw PDF content
        query: Query configuration dict

    Returns:
        Extracted data based on query type
    """
    query_type = query.get("type", "pdf_text")
    query_expression = query.get("query", "")
    join_flag = query.get("join", False)
    pdf_config = query.get("pdf_config", {})
    page_range = pdf_config.get("page_range")

    try:
        if query_type == "pdf_text":
            # Extract text, optionally apply regex
            text = extract_pdf_text(pdf_bytes, page_range=page_range, join_pages=True)

            if query_expression:
                # Apply regex to extracted text
                results = re.findall(query_expression, text)
                if join_flag and results:
                    return "|".join(str(r) for r in results)
                return results

            return text

        elif query_type == "pdf_table":
            tables = extract_pdf_tables(pdf_bytes, page_range=page_range)

            if not tables:
                return []

            # If table_index specified, return that specific table
            table_index = pdf_config.get("table_index")
            if table_index is not None and 0 <= table_index < len(tables):
                table = tables[table_index]
            else:
                # Return first table by default, or all if multiple
                table = tables[0] if len(tables) == 1 else tables

            # Handle flatten option - return just the rows as a flat list
            flatten = pdf_config.get("flatten", False)
            if flatten:
                if isinstance(table, list):
                    # Multiple tables - flatten all rows
                    all_rows = []
                    for t in table:
                        all_rows.extend(t.get("rows", []))
                    return all_rows
                else:
                    return table.get("rows", [])

            # If query expression provided, use it to filter/extract specific column
            if query_expression and isinstance(table, dict):
                rows = table.get("rows", [])
                results = []
                for row in rows:
                    if query_expression in row:
                        results.append(row[query_expression])
                if join_flag and results:
                    return "|".join(str(r) for r in results)
                return results

            return table

        elif query_type == "pdf_metadata":
            return extract_pdf_metadata(pdf_bytes)

        else:
            logger.warning("Unknown PDF query type", query_type=query_type)
            return None

    except Exception as e:
        logger.error("Error processing PDF query", error=str(e))
        return None


def is_pdf_content(content: bytes, content_type: Optional[str] = None) -> bool:
    """
    Check if content is a PDF.

    Args:
        content: Raw content bytes
        content_type: Optional Content-Type header value

    Returns:
        True if content is a PDF
    """
    # Check Content-Type header
    if content_type:
        if "application/pdf" in content_type.lower():
            return True

    # Check PDF magic bytes
    if content and len(content) >= 5:
        # PDF files start with "%PDF-"
        if content[:5] == b"%PDF-":
            return True

    return False


def process_pdf_queries(
    pdf_bytes: bytes,
    queries: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Process multiple PDF queries on the same document.

    Args:
        pdf_bytes: Raw PDF content
        queries: List of query configurations

    Returns:
        Dict mapping query names to extracted data
    """
    extracted_data = {}

    for query in queries:
        query_name = query.get("name", "unnamed")

        # Only process PDF-type queries
        query_type = query.get("type", "")
        if not query_type.startswith("pdf_"):
            logger.debug("Skipping non-PDF query type", query_type=query_type)
            extracted_data[query_name] = None
            continue

        result = process_pdf_query(pdf_bytes, query)
        extracted_data[query_name] = result

    return extracted_data
