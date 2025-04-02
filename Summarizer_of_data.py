from langchain_ollama import OllamaLLM
from langchain.prompts import PromptTemplate

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
    llm = OllamaLLM(model="llama3.2:1b")
    chain = prompt_template | llm
    
    try:
        # Invoke the chain to get the summary
        summary = chain.invoke({"text": text})
        return summary
    except Exception as e:
        print(f"Error during summarization: {e}")
        return "Summarization failed."

def extract_text_from_file(file_path):
    """Extracts text from the saved paper content file."""
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            return file.read()
    except FileNotFoundError:
        print(f"Error: File '{file_path}' not found.")
        return ""
    except UnicodeDecodeError as e:
        print(f"Error decoding file: {e}")
        return ""
    except Exception as e:
        print(f"Unexpected error while reading file: {e}")
        return ""

if __name__ == "__main__":
    # Path to the paper content file
    file_path = "paper_content.txt"
    
    # Extract the full content from the file
    paper_content = extract_text_from_file(file_path)
    
    if paper_content:
        # Use the full content for summarization
        full_content = paper_content
        
        # Summarize the full content
        summary = summarize_text(full_content)
        print("\nSummary of Full Content in Bullet Points:")
        print(summary)
    else:
        print("No content to summarize.")