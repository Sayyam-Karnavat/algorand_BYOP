from langchain.agents import AgentExecutor, create_react_agent
from langchain_community.tools import ArxivQueryRun
from langchain_community.utilities import ArxivAPIWrapper
from langchain_ollama import OllamaLLM
from langchain.prompts import PromptTemplate

# Initialize tools and their descriptions in a single function call
class DataGatherAgent:
    def __init__(self):
        self.llm = OllamaLLM(model="llama3.1:latest")
        arxiv_tool = ArxivQueryRun()
        self.arxiv_tool = arxiv_tool
        self.tool_descriptions = {"ArxivQueryRun": "A tool for querying papers on Arxiv."}

    def init_tools(self):
        """Initialize the tools."""
        return [self.arxiv_tool]

def create_agent(data_gather_agent, prompt):
    """Create the agent."""
    return create_react_agent(llm=data_gather_agent.llm, tools=data_gather_agent.init_tools(), prompt=prompt)

# Define the prompt template
prompt = PromptTemplate(
    input_variables=["input", "tool_names", "tools", "agent_scratchpad"],
    template="""You are a research assistant tasked with finding the latest papers on blockchain technology from Arxiv.

Available tools: {tool_names}
{tools}

Your task: {input}

To respond, you MUST follow this exact format:

THOUGHT: [Your step-by-step reasoning about how to solve the task]
ACTION: [tool name]
ACTION INPUT: [specific input to pass to the tool]

If you don't know how to proceed, still provide a THOUGHT section explaining your reasoning and then an ACTION to try something. Do not skip the ACTION section.

Current scratchpad (previous steps): {agent_scratchpad}
"""
)

def search_blockchain_papers(query="blockchain", max_results=3):
    """
    Search for recent blockchain papers on Arxiv
    """
    data_gather_agent = DataGatherAgent()
    
    input_query = f"Find the {max_results} most recent research papers about {query} on Arxiv and provide their titles, authors, and summaries."
    prompt_input = {
        "input": input_query,
        "tool_names": ", ".join([tool.name for tool in data_gather_agent.init_tools()]),
        "tools": "\n".join([f"{tool.name}: {data_gather_agent.tool_descriptions['tools'][tool.name]}" for tool in data_gather_agent.init_tools()]),
        "agent_scratchpad": ""
    }

    # Execute the agent
    try:
        agent = create_agent(data_gather_agent, prompt)
        results = agent.invoke(prompt_input)
        
        # Present search results in a structured format
        papers = []
        for result in results["output"]:
            title = result['title']
            authors = ', '.join(result['authors'])
            summary = result['summary']
            paper_info = f"Title: {title}\nAuthors: {authors}\nSummary: {summary}"
            papers.append(paper_info)
        
        return "\n".join(papers)

    except Exception as e:
        if isinstance(e, langchain.agents.exceptions.AgentExecutionException):
            print(f"Error executing agent: {str(e)}")
        else:
            print(f"An unexpected error occurred: {str(e)}")

if __name__ == "__main__":
    try:
        result = search_blockchain_papers("blockchain", 3)
        print("\nFinal Result:")
        print(result)
    except Exception as e:
        print(f"An error occurred: {str(e)}")
