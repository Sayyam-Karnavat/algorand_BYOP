import arxiv
import requests
import fitz  # PyMuPDF for PDF text extraction
import os

def fetch_paper(query="Artificial Intelligence", max_results=1):
    """Fetch a research paper's title, abstract, and content from arXiv."""
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
        results = client.results(search)
        paper = next(results, None)  # Get the first paper or None if no results
        
        if not paper:
            raise ValueError("No papers found for the given query.")

        # Extract metadata
        paper_title = paper.title
        paper_abstract = paper.summary
        pdf_url = paper.pdf_url
        
        # Download the PDF file
        response = requests.get(pdf_url, timeout=10)
        response.raise_for_status()  # Raise an error for bad HTTP responses
        pdf_file_path = "downloaded_paper.pdf"
        
        with open(pdf_file_path, "wb") as file:
            file.write(response.content)

        # Extract text from the downloaded PDF
        paper_text = extract_text_from_pdf(pdf_file_path)

        # Save the full text and metadata to a file
        with open("paper_content.txt", "w", encoding="utf-8") as file:
            file.write(f"Title: {paper_title}\n")
            file.write(f"Abstract: {paper_abstract}\n")
            file.write(f"PDF URL: {pdf_url}\n")
            file.write("\nFull Content:\n")
            file.write(paper_text)

        print(f"Paper '{paper_title}' processed successfully.")

    except requests.RequestException as e:
        print(f"Error downloading PDF: {e}")
    except ValueError as e:
        print(f"Error: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
    finally:
        # Clean up the downloaded PDF file
        if os.path.exists(pdf_file_path):
            os.remove(pdf_file_path)

def extract_text_from_pdf(pdf_file_path):
    """Extract text from the given PDF file using PyMuPDF (fitz)."""
    try:
        document = fitz.open(pdf_file_path)
        text = ""
        
        for page_num in range(document.page_count):
            page = document.load_page(page_num)
            text += page.get_text("text")
        
        document.close()
        return text
    except Exception as e:
        print(f"Error extracting text from PDF: {e}")
        return ""

if __name__ == "__main__":
    fetch_paper(query="Artificial Intelligence", max_results=1)