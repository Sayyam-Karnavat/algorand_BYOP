import langchain
from langchain_ollama import ChatOllama
from langchain.tools import ArxivQueryRun
from langchain.agents import AgentExecutor, create_react_agent
from langchain.prompts import PromptTemplate
import re
import uuid
import asyncio
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

# Initialize the LLM with Ollama
llm = ChatOllama(model="llama3", temperature=0.7)

# Initialize the arXiv tool
arxiv_tool = ArxivQueryRun()

# Define the tools available to the agent
tools = [arxiv_tool]

# Define a prompt template for the agent
agent_prompt = PromptTemplate(
    input_variables=["input", "agent_scratchpad"],
    template="""You are an AI research assistant. Your task is to search for the latest research papers on a given topic using the arXiv tool. Return the raw results for further processing.

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

async def summarize_paper(paper, executor):
    """Summarize a single paper using the LLM in a thread pool."""
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
    loop = asyncio.get_event_loop()
    summary_result = await loop.run_in_executor(executor, lambda: llm.invoke(summary_prompt.format(paper_content=summary_input)))
    summary = summary_result.content if hasattr(summary_result, 'content') else str(summary_result)
    
    # Clean text for LaTeX
    title = clean_text(title)
    authors = clean_text(authors)
    summary = clean_text(summary)
    
    return section_template.format(
        title=title,
        authors=authors,
        arxiv_id=arxiv_id,
        published=published,
        summary=summary
    )

async def parallel_arxiv_search(topic, max_results=3):
    """Perform a parallel search and summarization of arXiv papers."""
    # Run the agent to search for papers
    query = f"Search for the latest research papers on {topic} published in the last 6 months."
    result = await asyncio.to_thread(agent_executor.invoke, {"input": query})
    
    # Extract paper details
    papers = result.get('output', '')
    if not papers:
        return "No papers found."
    
    paper_list = papers.split('\n\n')[:max_results]
    
    # Process papers in parallel using a thread pool
    with ThreadPoolExecutor() as executor:
        tasks = [summarize_paper(paper, executor) for paper in paper_list]
        sections = await asyncio.gather(*tasks)
    
    # Generate LaTeX content
    current_date = datetime.now().strftime("%B %d, %Y")
    latex_content = latex_template.format(
        current_date=current_date,
        sections="\n\n".join(sections)
    )
    
    return latex_content

# Example usage
async def main():
    topic = "machine learning"
    latex_content = await parallel_arxiv_search(topic)
    print("Generated LaTeX content for PDF:")
    print(latex_content)
    
    # Save LaTeX content as a file for PDF compilation
    latex_output = f"""<xaiArtifact artifact_id="4936decf-4b35-4e48-8e50-4bdd5519d5a1" artifact_version_id="858d2130-a0d5-4659-bd4d-0e149a4925cd" title="research_summaries.tex" contentType="text/latex">"""