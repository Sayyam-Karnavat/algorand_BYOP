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