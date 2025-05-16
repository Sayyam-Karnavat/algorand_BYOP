```python
from langchain_ollama import OllamaLLM
from langchain.prompts import PromptTemplate
import re
import os

def summarize_text(text):
    """Summarizes extracted text into bullet points."""
    
    # Define a more robust prompt template that doesn't require manual input for the summary length.
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
        
        # Post-processing to convert the summary into bullet points.
        if "bullet points" in str(summary).lower():
            summary = str(summary).split("bullet points:")[1]
            summary_lines = [s.strip() for s in summary.split("\n")]
            summary_bullet_points = "\n".join([f"* {point}" for point in summary_lines])
            
            return summary_bullet_points
        else:
            return summary
    except Exception as e:
        print(f"Error during summarization: {e}")
        return "Summarization failed."

def extract_text_from_file(file_path):
    """Extracts text from the saved paper content file and separates it by paper."""
    
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            content = file.read()
        
        # Split the content into sections based on a regular expression pattern that captures a specific separator.
        papers = re.split(r'\n\n\s*\n', content)[1:]  # Capture multiple blank lines followed by a newline
        
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
    
    match = re.search(r'^Title:\s*(.*)', paper_content, re.IGNORECASE | re.MULTILINE)
    
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
    from reportlab.platypus import SimpleDocTemplate, Paragraph, getSampleStyleSheet
    
    doc = SimpleDocTemplate(pdf_filename, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []
    
    # Add title to PDF
    story.append(Paragraph(f"Summary of: {paper_title}", styles['Title']))
    
    # Add the summary in bullet points if it was generated that way.
    if isinstance(summary, str) and "\n" in summary:
        for point in summary.split("\n"):
            story.append(Paragraph("* " + point, styles['BodyText']))
    else:
        story.append(Paragraph(summary, styles['BodyText']))
    
    doc.build(story)

# Example usage
file_path = 'path/to/your/file.txt'
summary_text = summarize_text(extract_text_from_file(file_path)[0])
save_to_pdf(summary_text, extract_paper_title(extract_text_from_file(file_path)[0]))
```
Note that the `reportlab` library is used for generating PDFs. Ensure it's installed (`pip install reportlab`) and importable in your environment before running this code.