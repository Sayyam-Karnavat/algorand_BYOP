import arxiv
import requests
import fitz  # PyMuPDF for PDF text extraction
import os

def fetch_paper(query="Artificial Intelligence", max_results=3):
    """Fetch research papers' titles, abstracts, and content from arXiv."""
    try:
        # Initialize the arXiv client
        client = arxiv.Client()

        # Create a search object
        search = arxiv.Search(
            query=query,
            max_results=max_results,
            sort_by=arxiv.SortCriterion.SubmittedDate
        )