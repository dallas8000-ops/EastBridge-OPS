"""PDF document fetcher for legal gazettes and court documents."""

import logging
import re
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup

from .base import FetchedItem

logger = logging.getLogger(__name__)

USER_AGENT = "EastBridge-Ops-Intelligence/1.0 (+https://github.com/eastbridge; compliance monitoring)"


def _http_get(url: str, timeout: float = 30.0) -> bytes:
    with httpx.Client(timeout=timeout, follow_redirects=True, headers={"User-Agent": USER_AGENT}) as client:
        response = client.get(url)
        response.raise_for_status()
        return response.content


def _extract_text_from_pdf_url(pdf_url: str) -> str:
    """Extract text from a PDF URL using available libraries."""
    try:
        pdf_content = _http_get(pdf_url)
        
        # Try PyPDF2 first
        try:
            import PyPDF2
            from io import BytesIO
            
            pdf_file = BytesIO(pdf_content)
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
            
            return text[:10000]  # Limit to prevent excessive processing
            
        except ImportError:
            logger.warning("PyPDF2 not available, falling back to basic text extraction")
            # Fallback: extract from URL and basic text processing
            return _basic_pdf_extraction(pdf_url, pdf_content)
            
    except Exception as exc:
        logger.warning("Failed to extract text from PDF %s: %s", pdf_url, exc)
        return ""


def _basic_pdf_extraction(pdf_url: str, content: bytes) -> str:
    """Basic text extraction when PDF libraries are unavailable."""
    # This is a fallback - extract what we can from the filename and URL
    filename = pdf_url.split("/")[-1]
    filename = re.sub(r"[._-]", " ", filename)
    filename = re.sub(r"\.pdf$", "", filename, flags=re.IGNORECASE)
    
    # Try to extract some readable text from the PDF content
    try:
        # Simple extraction of printable ASCII text
        text = content.decode('latin-1', errors='ignore')
        # Filter for likely text content
        readable = re.sub(r'[^\x20-\x7E\n\r\t]', ' ', text)
        readable = re.sub(r'\s+', ' ', readable)
        return readable[:5000] if len(readable) > 100 else filename
    except:
        return filename


def fetch_pdf_list(
    list_url: str,
    pdf_link_selector: str = "a[href$='.pdf']",
    max_items: int = 10,
    base_url: str | None = None,
) -> list[FetchedItem]:
    """Fetch PDF documents from a listing page."""
    try:
        html_content = _http_get(list_url).decode('utf-8', errors='ignore')
    except httpx.HTTPError as exc:
        logger.warning("Failed to fetch PDF list from %s: %s", list_url, exc)
        return []
    
    soup = BeautifulSoup(html_content, "lxml")
    base = base_url or list_url
    seen_urls: set[str] = set()
    items: list[FetchedItem] = []
    
    # Find all PDF links
    pdf_links = soup.select(pdf_link_selector)
    
    for link in pdf_links[:max_items]:
        href = link.get("href")
        if not href:
            continue
            
        url = urljoin(base, href)
        if url in seen_urls:
            continue
        seen_urls.add(url)
        
        # Get link text as title
        title = link.get_text(strip=True)
        if not title or len(title) < 5:
            # Try to get title from parent elements
            parent = link.parent
            if parent:
                title = parent.get_text(strip=True)
        
        if not title:
            title = url.split("/")[-1]
        
        # Extract text from PDF
        try:
            pdf_text = _extract_text_from_pdf_url(url)
            content = pdf_text if pdf_text else title
        except Exception as exc:
            logger.warning("Failed to process PDF %s: %s", url, exc)
            content = title
        
        items.append(
            FetchedItem(
                external_id=url[:512],
                title=title[:500],
                url=url,
                content=content[:8000],
                published_at=None,
            )
        )
    
    return items


def fetch_gazette_notices(
    gazette_url: str,
    max_items: int = 10,
) -> list[FetchedItem]:
    """Fetch Uganda Gazette notices specifically."""
    return fetch_pdf_list(
        list_url=gazette_url,
        pdf_link_selector="a[href*='gazette'], a[href*='Gazette'], a[href$='.pdf']",
        max_items=max_items,
    )