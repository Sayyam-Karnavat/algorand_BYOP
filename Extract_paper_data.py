import arxiv
import requests
import fitz  # PyMuPDF for PDF text extraction
import os

def fetch_paper(query, max_results=3 , save_file = "paper_content.txt"):
    """Fetch research papers' titles, abstracts, and content from arXiv."""
    try:
        print("Query :-" , query)
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
        with open(save_file, "w", encoding="utf-8") as output_file:
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
                
                with open(pdf_file_path, "wb") as file:
                    file.write(response.content)

                # Extract text from the downloaded PDF
                paper_text = extract_text_from_pdf(pdf_file_path)

                # Write the full text and metadata for this paper
                output_file.write(f"\n{'='*50}\n")
                output_file.write(f"Paper {index}\n")
                output_file.write(f"Title: {paper_title}\n")
                output_file.write(f"Abstract: {paper_abstract}\n")
                output_file.write(f"PDF URL: {pdf_url}\n")
                output_file.write("\nFull Content:\n")
                output_file.write(paper_text)
                output_file.write(f"\n{'='*50}\n")

                print(f"Paper {index}: '{paper_title}' processed successfully.")

                # Clean up the downloaded PDF file immediately after processing
                if os.path.exists(pdf_file_path):
                    os.remove(pdf_file_path)

    except requests.RequestException as e:
        print(f"Error downloading PDF: {e}")
    except ValueError as e:
        print(f"Error: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

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