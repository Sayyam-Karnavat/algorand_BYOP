import langchain
from langchain_ollama import ChatOllama
from langchain.tools import ArxivQueryRun
from langchain.agents import AgentExecutor, create_react_agent
from langchain.prompts import PromptTemplate
import re
import uuid
from datetime import datetime

# Initialize the LLM with Ollama (using a suitable model, e.g., llama3)
llm = ChatOllama(model="llama3", temperature=0.7)

# Initialize the arXiv tool
arxiv_tool = ArxivQueryRun()

# Define the tools available to the agent
tools = [arxiv_tool]

# Define a prompt template for the agent
agent_prompt = PromptTemplate(
    input_variables=["input", "agent_scratchpad"],
    template="""You are an AI research assistant. Your task is to search for the latest research papers on a given topic using the arXiv tool, summarize the most important parts of each paper, and prepare the content for PDF generation. For each paper, provide a concise summary (100-150 words) focusing on the main findings, methodology, and contributions. Ensure the summaries are clear and professional.

Tools available: {tools}

Query: {input}

{agent_scratchpad}
"""
)

# Create the ReAct agent
agent = create_react_agent(llm=llm, tools=tools, prompt=agent_prompt)
agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

# Summarization prompt template
summary_prompt = PromptTemplate(
    input_variables=["paper_content"],
    template="""Summarize the following research paper content in 100-150 words, focusing on the main findings, methodology, and contributions. Ensure the summary is concise, clear, and professional:

{paper_content}
"""
)


# LaTeX template for PDF generation
latex_template = """\\documentclass[a4paper,12pt]{article}
\\usepackage[utf8]{inputenc}
\\usepackage[T1]{fontenc}
\\usepackage{geometry}
\\usepackage{parskip}
\\usepackage{sectsty}
\\usepackage{amsmath}
\\usepackage{amsfonts}
\\usepackage{amssymb}
\\usepackage{tocloft}
\\usepackage{xcolor}
\\usepackage{hyperref}
\\geometry{margin=1in}
\\allsectionsfont{\\sffamily}
\\title{{Research Paper Summaries}}
\\author{{AI Research Assistant}}
\\date{{{current_date}}}

\\begin{document}
\\maketitle
\\tableofcontents
\\newpage

{sections}

\\end{document}
"""

section_template = """\\section*{{Paper: {title}}}
\\textbf{{Authors:}} {authors}\\\\
\\textbf{{arXiv ID:}} {arxiv_id}\\\\
\\textbf{{Published:}} {published}\\\\
\\textbf{{Summary:}} {summary}
"""


def clean_text(text):
    """Clean text for LaTeX by escaping special characters."""
    text = re.sub(r'[\\{}#%&]', lambda m: '\\' + m.group(0), text)
    text = re.sub(r'\n+', ' ', text)
    return text.strip()

def sequential_arxiv_search(topic, max_results=3):
    """Perform a sequential search and summarization of arXiv papers."""
    # Run the agent to search for papers
    query = f"Search for the latest research papers on {topic} published in the last 6 months."
    result = agent_executor.invoke({"input": query})
    
    # Extract paper details from the result (assuming arXiv tool returns a formatted string)
    papers = result.get('output', '')
    if not papers:
        return "No papers found."

    # Split the output into individual papers (assuming arXiv tool returns a list-like string)
    paper_list = papers.split('\n\n')[:max_results]
    sections = []
    
    for paper in paper_list:
        # Parse paper details (simplified parsing, adjust based on actual arXiv tool output)
        title = re.search(r'Title:\s*(.*?)(?:\n|$)', paper)
        authors = re.search(r'Authors:\s*(.*?)(?:\n|$)', paper)
        arxiv_id = re.search(r'arXiv ID:\s*(.*?)(?:\n|$)', paper)
        published = re.search(r'Published:\s*(.*?)(?:\n|$)', paper)
        abstract = re.search(r'Summary:\s*(.*?)(?:\n|$)', paper)
        
        title = title.group(1) if title else "Unknown Title"
        authors = authors.group(1) if authors else "Unknown Authors"
        arxiv_id = arxiv_id.group(1) if arxiv_id else "Unknown ID"
        published = published.group(1) if published else "Unknown Date"
        abstract = abstract.group(1) if abstract else "No abstract available."
        
        # Summarize the paper content
        summary_input = f"Title: {title}\nAbstract: {abstract}"
        summary_result = llm.invoke(summary_prompt.format(paper_content=summary_input))
        summary = summary_result.content if hasattr(summary_result, 'content') else str(summary_result)
        
        # Clean text for LaTeX
        title = clean_text(title)
        authors = clean_text(authors)
        summary = clean_text(summary)
        
        # Create section for this paper
        sections.append(section_template.format(
            title=title,
            authors=authors,
            arxiv_id=arxiv_id,
            published=published,
            summary=summary
        ))
    
    # Generate LaTeX content
    current_date = datetime.now().strftime("%B %d, %Y")
    latex_content = latex_template.format(
        current_date=current_date,
        sections="\n\n".join(sections)
    )
    
    return latex_content