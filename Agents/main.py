
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


    def setup_agent(self):
        """Setup the ReAct agent."""
        template = """
        You are a research assistant that helps find and summarize academic papers.
        
        You have access to the following tools:
        {tools}
        
        Use the following format:
        Question: the input question you must answer
        Thought: you should always think about what to do
        Action: the action to take, should be one of [{tool_names}]
        Action Input: the input to the action
        Observation: the result of the action
        ... (this Thought/Action/Action Input/Observation can repeat N times)
        Thought: I now know the final answer
        Final Answer: the final answer to the original input question
        
        Question: {input}
        Thought: {agent_scratchpad}
        """
        
        prompt = PromptTemplate.from_template(template)
        
        self.agent = create_react_agent(
            llm=self.llm,
            tools=self.tools,
            prompt=prompt
        )
        
        self.agent_executor = AgentExecutor(
            agent=self.agent,
            tools=self.tools,
            verbose=True,
            handle_parsing_errors=True,
            max_iterations=10
        )
    
    def summarize_paper(self, paper_content: str) -> str:
        """Summarize a research paper using the LLM."""
        summarize_prompt = f"""
        Please provide a comprehensive summary of this research paper. Include:
        1. Main research question/objective
        2. Key methodology used
        3. Major findings/results
        4. Conclusions and implications
        5. Limitations mentioned by authors
        
        Paper content:
        {paper_content[:4000]}  # Limit content to avoid token limits
        
        Summary:
        """
        
        try:
            summary = self.llm.invoke(summarize_prompt)
            return summary
        except Exception as e:
            logger.error(f"Error summarizing paper: {e}")
            return f"Error generating summary: {str(e)}"
        
    