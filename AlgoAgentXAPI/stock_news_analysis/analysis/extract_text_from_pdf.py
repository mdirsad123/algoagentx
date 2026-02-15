"""
python -m stock_news_analysis.analysis.extract_text_from_pdf
"""

import re
import requests
import fitz  # PyMuPDF
import io
import xml.etree.ElementTree as ET
import requests
from transformers import pipeline

summarizer = pipeline("summarization", model="facebook/bart-large-cnn")

def extract_text_from_bse_pdf(url: str) -> str:
    """
    Extracts text from a BSE announcement PDF URL.

    Parameters:
        url (str): The full BSE announcement PDF URL.

    Returns:
        str: Extracted text content from the PDF.

    Raises:
        ValueError: If the response is not a PDF.
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Referer": "https://www.nseindia.com/"
    }

    response = requests.get(url, headers=headers)

    if response.headers.get("Content-Type") != "application/pdf":
        raise ValueError(f"Expected a PDF, but got: {response.headers.get('Content-Type')}")

    pdf_file = fitz.open(stream=io.BytesIO(response.content), filetype="pdf")

    full_text = ""
    for page in pdf_file:
        full_text += page.get_text()

    return full_text

def extract_text_from_nse_xml(url: str) -> str:
    # ✅ Auto-correct common domain typos using regex
    url = re.sub(r"nsearchives\.nse.*?dia\.co+m", "nsearchives.nseindia.com", url)

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Referer": "https://www.nseindia.com/"
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        raise ValueError(f"❌ Failed to fetch the file: {e}")

    content_type = response.headers.get("Content-Type", "").lower()

    if "pdf" in content_type:
        pdf_file = fitz.open(stream=io.BytesIO(response.content), filetype="pdf")
        return "\n".join([page.get_text() for page in pdf_file])

    elif "xml" in content_type:
        try:
            tree = ET.ElementTree(ET.fromstring(response.content))
            root = tree.getroot()
            return "\n".join([
                elem.text.strip()
                for elem in root.iter()
                if elem.text and elem.text.strip()
            ])
        except ET.ParseError as e:
            raise ValueError(f"❌ Failed to parse XML content: {e}")

    else:
        raise ValueError(f"❌ Unsupported content type: {content_type}")
if __name__ == "__main__":
    url = "https://nsearchives.nseinndia.com/corporate/xbrl/PRIOR_INTIMATION_57604_1463186_05062025115804_WEB.xml"
    try:
        # text = extract_text_from_bse_pdf(url)
        text = extract_text_from_nse_xml(url)
        print("📝befor Summary:")
        print(text[300:5000])
        
    except ValueError as e:
        print("Failed to extract PDF:", e)

