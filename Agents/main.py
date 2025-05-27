
import asyncio
import os
from typing import List, Dict, Any
from datetime import datetime
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

# LangChain imports
from langchain.agents import create_react_agent, AgentExecutor
from langchain.tools import Tool
from langchain.prompts import PromptTemplate
from langchain_community.llms import Ollama
from langchain_community.utilities import ArxivAPIWrapper
from langchain.schema import Document

# PDF generation
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ResearchAgent:
    """Base class for research agents that search, summarize, and save research papers."""
    
    def __init__(self, model_name: str = "llama2", max_results: int = 5):
        self.model_name = model_name
        self.max_results = max_results
        self.llm = Ollama(model=model_name, temperature=0.1)
        self.arxiv = ArxivAPIWrapper(top_k_results=max_results)
        self.setup_tools()
        self.setup_agent()


    def setup_tools(self):
        """Setup the tools for the agent."""
        self.arxiv_tool = Tool(
            name="arxiv_search",
            description="Search for research papers on ArXiv. Input should be a search query.",
            func=self.arxiv.run
        )
        
        self.summarize_tool = Tool(
            name="summarize_paper",
            description="Summarize a research paper. Input should be the paper content.",
            func=self.summarize_paper
        )
        
        self.tools = [self.arxiv_tool, self.summarize_tool]