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

        # Fetch results
        results = list(client.results(search))  # Convert to list to process all results

        if not results:
            raise ValueError("No papers found for the given query.")
        
        # Open the output file once in write mode to overwrite any existing content
        with open("paper_content.txt", "w", encoding="utf-8") as output_file:
            # Process each paper one by one
            for index, paper in enumerate(results, 1):
                # Extract metadata
                paper_title = paper.title
                paper_abstract = paper.summary
                pdf_url = paper.pdf_url

                # Download the PDF file
                response = requests.get(pdf_url, timeout=10)
                response.raise_for_status()  # Raise an error for bad HTTP responses
                pdf_file_path = f"downloaded_paper_{index}.pdf"