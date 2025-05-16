from langchain_ollama import OllamaLLM
from langchain.prompts import PromptTemplate
import re
import os

def summarize_text(text):
    """Summarizes extracted text into bullet points."""
    prompt_template = PromptTemplate(
        input_variables=["text"],
        template="""
        Summarize the following research paper content into concise bullet points:
        {text}
        Provide clear, concise, and comprehensive bullet points covering the main ideas, methods, results, and conclusions.
        """
    )
    
    # Initialize the LLaMA model
    llm = OllamaLLM(model="llama2:latest")
    chain = prompt_template | llm
    
    try:
        # Invoke the chain to get the summary
        summary = chain.invoke({"text": text})
        return summary
    except Exception as e:
        print(f"Error during summarization: {e}")
        return "Summarization failed."

def extract_text_from_file(file_path):
    """Extracts text from the saved paper content file and separates it by paper."""
    
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            content = file.read()
        
        # Split the content by the separator used in the previous script
        papers = content.split("="*50)[1:]  # Skip the first empty split if any
        
        paper_contents = []
        
        for paper in papers:
            paper = paper.strip()
            if paper:  # Only process non-empty sections
                paper_contents.append(paper)
                
        return paper_contents  # List of individual paper contents
    except FileNotFoundError as e:
        print(f"Error: File '{file_path}' not found.")
        return []
    except UnicodeDecodeError as e:
        print(f"Error decoding file: {e}")
        return []
    except Exception as e:
        print(f"Unexpected error while reading file: {e}")
        return []

def extract_paper_title(paper_content):
    """Extracts the paper title from the content using regular expressions."""
    
    import re
    match = re.search(r'Title:\s*(.*)', paper_content, re.IGNORECASE)
    
    if match:
        # Extract everything after "Title:" and strip whitespace
        return match.group(1).strip()
    else:
        return "Untitled_Paper"  # Default if no title found

def save_to_pdf(summary, paper_title, output_dir="summaries"):
    """Saves the summary to a PDF file with the paper title as the filename."""
    
    import os
    
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    # Sanitize the paper title to make it a valid filename
    sanitized_title = re.sub(r'[<>:"/\\|?*]', '', paper_title)
    pdf_filename = f"{output_dir}/{sanitized_title}.pdf"
    
    # Create PDF
    doc = SimpleDocTemplate(pdf_filename, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []
    
    # Add title to PDF
    story.append(Paragraph(f"Summary of: {paper_title}", styles['Title']))
    story.append(Paragraph("<br/>", styles['Normal']))  # Spacer
    
    # Split summary into lines and add as paragraphs
    for line in summary.splitlines():
        if line.strip():
            story.append(Paragraph(line, styles['BodyText']))
            
    # Build the PDF
    try:
        doc.build(story)
        print(f"Saved summary to {pdf_filename}")
    except Exception as e:
        print(f"Error saving PDF {pdf_filename}: {e}")

# Example usage
if __name__ == "__main__":
    paper_path = "C:\\path\\to\\paper.txt"
    papers_contents = extract_text_from_file(paper_path)
    
    for i, content in enumerate(papers_contents):
        summary = summarize_text(content)
        title = extract_paper_title(content)
        
        save_to_pdf(summary, title, output_dir="summaries")
