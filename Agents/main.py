
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
        
    def create_pdf(self, title: str, summary: str, filename: str):
        """Create a PDF with the research summary."""
        try:
            doc = SimpleDocTemplate(filename, pagesize=A4)
            styles = getSampleStyleSheet()
            
            # Custom styles
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=16,
                spaceAfter=30,
                alignment=1  # Center alignment
            )
            
            content = []
            
            # Add title
            content.append(Paragraph(title, title_style))
            content.append(Spacer(1, 12))
            
            # Add timestamp
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            content.append(Paragraph(f"Generated on: {timestamp}", styles['Normal']))
            content.append(Spacer(1, 12))
            
            # Add summary
            content.append(Paragraph("Research Summary", styles['Heading2']))
            content.append(Spacer(1, 12))
            
            # Split summary into paragraphs for better formatting
            summary_paragraphs = summary.split('\n\n')
            for para in summary_paragraphs:
                if para.strip():
                    content.append(Paragraph(para.strip(), styles['Normal']))
                    content.append(Spacer(1, 6))
            
            doc.build(content)
            logger.info(f"PDF saved as: {filename}")
            
        except Exception as e:
            logger.error(f"Error creating PDF: {e}")


class SequentialResearchAgent(ResearchAgent):
    """Sequential agent that processes papers one by one."""
    
    def search_and_summarize(self, query: str, output_dir: str = "summaries") -> List[str]:
        """Search for papers and summarize them sequentially."""
        os.makedirs(output_dir, exist_ok=True)
        
        logger.info(f"Starting sequential search for: {query}")
        
        # Search for papers
        search_result = self.agent_executor.invoke({
            "input": f"Search for recent research papers about: {query}"
        })
        
        # Parse the search results (this is simplified - you might need to adjust based on actual output)
        papers = self.parse_search_results(search_result['output'])
        
        summaries = []
        pdf_files = []
        
        for i, paper in enumerate(papers):
            logger.info(f"Processing paper {i+1}/{len(papers)}: {paper.get('title', 'Unknown')}")
            
            # Summarize the paper
            summary = self.summarize_paper(paper.get('summary', ''))
            summaries.append(summary)
            
            # Create PDF
            filename = f"{output_dir}/summary_{i+1}_{query.replace(' ', '_')}.pdf"
            self.create_pdf(
                title=paper.get('title', f'Research Paper {i+1}'),
                summary=summary,
                filename=filename
            )
            pdf_files.append(filename)
        
        logger.info(f"Sequential processing completed. Generated {len(pdf_files)} PDFs.")
        return pdf_files
    
    def parse_search_results(self, search_output: str) -> List[Dict[str, str]]:
        """Parse search results from arxiv tool output."""
        papers = []
        
        # Try to extract paper information from the search output
        lines = search_output.split('\n')
        current_paper = {}
        
        for line in lines:
            line = line.strip()
            if line.startswith('Title:'):
                if current_paper:
                    papers.append(current_paper)
                current_paper = {'title': line[6:].strip()}
            elif line.startswith('Summary:') or line.startswith('Abstract:'):
                current_paper['summary'] = line[8:].strip() if line.startswith('Summary:') else line[9:].strip()
        
        if current_paper:
            papers.append(current_paper)
        
        # If parsing fails, create dummy entries
        if not papers:
            papers = [{'title': f'Research Paper on {search_output[:100]}...', 'summary': search_output[:1000]}]
        
        return papers[:self.max_results]

class ParallelResearchAgent(ResearchAgent):
    """Parallel agent that processes papers concurrently."""
    
    def __init__(self, model_name: str = "llama2", max_results: int = 5, max_workers: int = 3):
        super().__init__(model_name, max_results)
        self.max_workers = max_workers
    
    def search_and_summarize(self, query: str, output_dir: str = "summaries") -> List[str]:
        """Search for papers and summarize them in parallel."""
        os.makedirs(output_dir, exist_ok=True)
        
        logger.info(f"Starting parallel search for: {query}")
        
        # Search for papers
        search_result = self.agent_executor.invoke({
            "input": f"Search for recent research papers about: {query}"
        })
        
        papers = self.parse_search_results(search_result['output'])
        
        pdf_files = []
        
        # Process papers in parallel
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all tasks
            future_to_paper = {
                executor.submit(self.process_single_paper, paper, i, query, output_dir): (paper, i)
                for i, paper in enumerate(papers)
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_paper):
                paper, index = future_to_paper[future]
                try:
                    pdf_file = future.result()
                    if pdf_file:
                        pdf_files.append(pdf_file)
                    logger.info(f"Completed processing paper {index + 1}")
                except Exception as e:
                    logger.error(f"Error processing paper {index + 1}: {e}")
        
        logger.info(f"Parallel processing completed. Generated {len(pdf_files)} PDFs.")
        return pdf_files
    
    def process_single_paper(self, paper: Dict[str, str], index: int, query: str, output_dir: str) -> str:
        """Process a single paper (summarize and create PDF)."""
        logger.info(f"Processing paper {index+1}: {paper.get('title', 'Unknown')}")
        
        # Summarize the paper
        summary = self.summarize_paper(paper.get('summary', ''))
        
        # Create PDF
        filename = f"{output_dir}/summary_{index+1}_{query.replace(' ', '_')}.pdf"
        self.create_pdf(
            title=paper.get('title', f'Research Paper {index+1}'),
            summary=summary,
            filename=filename
        )
        
        return filename
    
    def parse_search_results(self, search_output: str) -> List[Dict[str, str]]:
        """Parse search results from arxiv tool output."""
        # Same implementation as SequentialResearchAgent
        papers = []
        
        lines = search_output.split('\n')
        current_paper = {}
        
        for line in lines:
            line = line.strip()
            if line.startswith('Title:'):
                if current_paper:
                    papers.append(current_paper)
                current_paper = {'title': line[6:].strip()}
            elif line.startswith('Summary:') or line.startswith('Abstract:'):
                current_paper['summary'] = line[8:].strip() if line.startswith('Summary:') else line[9:].strip()
        
        if current_paper:
            papers.append(current_paper)
        
        if not papers:
            papers = [{'title': f'Research Paper on {search_output[:100]}...', 'summary': search_output[:1000]}]
        
        return papers[:self.max_results]

class AsyncResearchAgent(ResearchAgent):
    """Async agent for high-performance parallel processing."""
    
    def __init__(self, model_name: str = "llama2", max_results: int = 5, semaphore_limit: int = 3):
        super().__init__(model_name, max_results)
        self.semaphore = asyncio.Semaphore(semaphore_limit)
    
    async def search_and_summarize_async(self, query: str, output_dir: str = "summaries") -> List[str]:
        """Search for papers and summarize them asynchronously."""
        os.makedirs(output_dir, exist_ok=True)
        
        logger.info(f"Starting async search for: {query}")
        
        # Search for papers (this part is still synchronous as arxiv tool doesn't support async)
        search_result = self.agent_executor.invoke({
            "input": f"Search for recent research papers about: {query}"
        })
        
        papers = self.parse_search_results(search_result['output'])
        
        # Process papers asynchronously
        tasks = [
            self.process_single_paper_async(paper, i, query, output_dir)
            for i, paper in enumerate(papers)
        ]
        
        pdf_files = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out exceptions
        successful_files = [f for f in pdf_files if isinstance(f, str)]
        
        logger.info(f"Async processing completed. Generated {len(successful_files)} PDFs.")
        return successful_files
    
    async def process_single_paper_async(self, paper: Dict[str, str], index: int, query: str, output_dir: str) -> str:
        """Process a single paper asynchronously."""
        async with self.semaphore:
            logger.info(f"Processing paper {index+1}: {paper.get('title', 'Unknown')}")
            
            # Run CPU-bound tasks in thread pool
            loop = asyncio.get_event_loop()
            
            # Summarize the paper
            summary = await loop.run_in_executor(
                None, self.summarize_paper, paper.get('summary', '')
            )
            
            # Create PDF
            filename = f"{output_dir}/summary_{index+1}_{query.replace(' ', '_')}.pdf"
            await loop.run_in_executor(
                None, self.create_pdf, 
                paper.get('title', f'Research Paper {index+1}'), summary, filename
            )
            
            return filename
    
    def parse_search_results(self, search_output: str) -> List[Dict[str, str]]:
        """Parse search results from arxiv tool output."""
        # Same implementation as other agents
        papers = []
        
        lines = search_output.split('\n')
        current_paper = {}
        
        for line in lines:
            line = line.strip()
            if line.startswith('Title:'):
                if current_paper:
                    papers.append(current_paper)
                current_paper = {'title': line[6:].strip()}
            elif line.startswith('Summary:') or line.startswith('Abstract:'):
                current_paper['summary'] = line[8:].strip() if line.startswith('Summary:') else line[9:].strip()
        
        if current_paper:
            papers.append(current_paper)
        
        if not papers:
            papers = [{'title': f'Research Paper on {search_output[:100]}...', 'summary': search_output[:1000]}]
        
        return papers[:self.max_results]
    

def main():
    print("=== Sequential Research Agent ===")
    sequential_agent = SequentialResearchAgent(model_name="llama2", max_results=3)
    
    query = "machine learning transformers"
    pdf_files_seq = sequential_agent.search_and_summarize(query, output_dir="sequential_summaries")
    print(f"Sequential agent generated: {pdf_files_seq}")
    
    print("\n=== Parallel Research Agent ===")
    parallel_agent = ParallelResearchAgent(model_name="llama2", max_results=3, max_workers=2)
    
    query = "computer vision deep learning"
    pdf_files_par = parallel_agent.search_and_summarize(query, output_dir="parallel_summaries")
    print(f"Parallel agent generated: {pdf_files_par}")
    
    print("\n=== Async Research Agent ===")
    async def run_async_agent():
        async_agent = AsyncResearchAgent(model_name="llama2", max_results=3, semaphore_limit=2)
        query = "natural language processing"
        pdf_files_async = await async_agent.search_and_summarize_async(query, output_dir="async_summaries")
        print(f"Async agent generated: {pdf_files_async}")
    
    asyncio.run(run_async_agent())

if __name__ == "__main__":
    main()