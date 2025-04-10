import arxiv
import requests
import fitz  # PyMuPDF for PDF text extraction
import os

def fetch_paper(query="Artificial Intelligence", max_results=3):
    """Fetch research papers' titles, abstracts, and content from arXiv."""
    