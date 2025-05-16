import arxiv
import requests
import fitz  # PyMuPDF for PDF text extraction
import os
import random
import time

def load_fetched_papers(history_file="fetched_papers.txt"):
    """Load previously fetched paper URLs from a file."""
    if os.path.exists(history_file):
        with open(history_file, "r", encoding="utf-8") as file:
            return set(line.strip() for line in file if line.strip())
    return set()

def save_fetched_paper(pdf_url, history_file="fetched_papers.txt"):
    """Save a paper's URL to the history file."""
    with open(history_file, "a", encoding="utf-8") as file:
        file.write(f"{pdf_url}\n")

def fetch_paper(save_file, query="Artificial Intelligence", max_results=3, start_index=0):
    """Fetch unique research papers' titles, abstracts, and content from arXiv."""
    try:
        # Load previously fetched papers
        fetched_papers = load_fetched_papers()

        # Initialize the arXiv client
        client = arxiv.Client()

        # Create a search object with pagination
        query_params = {
            "query": query,
            "max_results": max_results + 10,  
            "sort_by": arxiv.SortCriterion.SubmittedDate
        }

        results = []
        while True:
            search = arxiv.Search(**query_params)
            new_results = list(client.results(search))
            if not new_results:
                break
            results.extend(new_results)

        # Filter out previously fetched papers
        unique_results = [paper for paper in results[start_index:] if paper.pdf_url not in fetched_papers]

        if not unique_results:
            raise ValueError(f"No new papers found after skipping {start_index} results and excluding duplicates.")

        # Randomize and select up to max_results
        random.shuffle(unique_results)
        selected_results = unique_results[:max_results]

        with open(save_file, "w", encoding="utf-8") as output_file:
            for index, paper in enumerate(selected_results, 1):
                try:
                    pdf_url = paper.pdf_url
                    response = requests.get(pdf_url, timeout=10)
                    response.raise_for_status()  
                    pdf_file_path = f"downloaded_paper_{index}.pdf"
                    
                    with open(pdf_file_path, "wb") as file:
                        file.write(response.content)

                    # Extract text from the downloaded PDF
                    paper_text = extract_text_from_pdf(pdf_file_path)
                    
                    # Write the full text and metadata for this paper
                    output_file.write(f"\n{'='*50}\n")
                    output_file.write(f"Paper {index}\n")
                    output_file.write(f"Title: {paper.title or ''}\n")  # Add check for empty title
                    output_file.write(f"Abstract: {paper.summary or ''}\n")  # Add check for empty abstract
                    output_file.write(f"PDF URL: {pdf_url}\n")
                    submission_date = paper.published
                    if submission_date:
                        output_file.write(f"Submission Date: {submission_date}\n")
                    else:
                        output_file.write("Submission Date: Not Available\n")  # Add default message

                    with open(pdf_file_path, 'r') as f:
                        paper_text = f.read()
                    
                    output_file.write(f"Text: {paper_text or ''}\n")  # Write text if available
                    
                except Exception as e:
                    print(f"Error processing paper {index}: {str(e)}")
                    
    except Exception as e:
        print(f"Error fetching papers: {str(e)}")

def extract_text_from_pdf(file_path):
    try:
        with fitz.open(file_path) as doc:
            text = ''
            for page in doc:
                text += page.get_text()
            return text
    except Exception as e:
        print(f"Error extracting text from PDF: {str(e)}")
        
def main():
    save_file = 'output.txt'
    query = "research papers"
    max_results = 10
    start_index = 0
    
    fetch_paper(save_file, query, max_results, start_index)

if __name__ == "__main__":
    main()