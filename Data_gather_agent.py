from langchain.agents import AgentExecutor, create_react_agent
from langchain_community.tools import ArxivQueryRun
from langchain_community.utilities import ArxivAPIWrapper
from langchain_ollama import OllamaLLM
from langchain.prompts import PromptTemplate

# Initialize the language model (Ollama with Llama3)
llm = OllamaLLM(model="llama3.1:latest")

# Create Arxiv tool
arxiv_tool = ArxivQueryRun()

# Define the tools list
tools = [arxiv_tool]

# Define a more explicit prompt template
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

# Create the agent with the corrected prompt
agent = create_react_agent(llm, tools, prompt)

# Create agent executor with a max iteration limit to prevent infinite loops
agent_executor = AgentExecutor(
    agent=agent,
    tools=tools,
    verbose=True,
    handle_parsing_errors=True,
    max_iterations=15,  # Limit the number of iteration
)

def search_blockchain_papers(query="blockchain", max_results=3):
    """
    Search for recent blockchain papers on Arxiv
    """
    input_query = f"Find the {max_results} most recent research papers about {query} on Arxiv and provide their titles, authors, and summaries."

    # Execute the agent
    results = agent_executor.invoke({
        "input": input_query,
        "tool_names": ", ".join([tool.name for tool in tools]),
        "tools": "\n".join([f"{tool.name}: {tool.description}" for tool in tools]),
        "agent_scratchpad": ""
    })

    return results


if __name__ == "__main__":
    try:
        result = search_blockchain_papers("blockchain", 3)
        print("\nFinal Result:")
        print(result["output"])
    except Exception as e:
        print(f"An error occurred: {str(e)}")