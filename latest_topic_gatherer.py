from langchain_ollama import ChatOllama
from langchain_community.tools import DuckDuckGoSearchResults
from langchain.agents import initialize_agent, AgentType
from langchain.prompts import PromptTemplate

def get_blockchain_research_topics(max_results: int) -> list:
    """
    Search the web for the latest blockchain research paper topics using DuckDuckGo and return a list of topics.
    
    Args:
        max_results (int): Maximum number of topic names to return.
    
    Returns:
        list: List of blockchain research topic names.
    """
    # Initialize the Ollama model
    llm = ChatOllama(model="llama3", temperature=0.3)

    # Initialize DuckDuckGo search tool with a reasonable max_results for web search
    search_tool = DuckDuckGoSearchResults(max_results=5)  # Limiting to 5 web results for efficiency

    # Define a prompt template for extracting topics
    prompt_template = PromptTemplate(
        input_variables=["web_content", "max_results"],
        template="""
        You are a research assistant tasked with identifying the latest blockchain research paper topics.
        Based on the following web content from a DuckDuckGo search, extract a list of concise blockchain research topic names.
        Return exactly {max_results} unique topics, prioritizing the most recent and relevant ones from 2025 or late 2024.
        If fewer than {max_results} topics are found, return all available topics.
        Format the output as a numbered list, with each topic on a new line.
        Do not include explanations or additional text beyond the list.

        Web content:
        {web_content}
        """
    )

    # Create a chain to process the web content and extract topics
    topic_chain = prompt_template | llm

    # Initialize the agent with the search tool
    agent = initialize_agent(
        tools=[search_tool],
        llm=llm,
        agent_type=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
        verbose=False
    )

    # Perform the web search using the agent
    query = "latest blockchain research paper topics 2025"
    try:
        search_result = agent.invoke(f"Search for: {query}")
        # Extract the output from the agent's result (dictionary)
        web_content = search_result.get("output", str(search_result))
    except Exception as e:
        return [f"Error during search: {str(e)}"]

    # Extract topics using the topic chain
    try:
        # Use invoke instead of run for RunnableSequence
        topics_response = topic_chain.invoke(
            {"web_content": web_content, "max_results": max_results}
        )
        # Extract content from the response (ChatOllama returns a message object)
        topics_text = topics_response.content
        # Parse the response into a list
        topics = [topic.strip() for topic in topics_text.strip().split("\n") if topic.strip()]
        return topics[:max_results]
    except Exception as e:
        return [f"Error processing topics: {str(e)}"]

if __name__ == "__main__":
    # Example usage
    max_results = 5
    topics = get_blockchain_research_topics(max_results)
    print(f"Latest Blockchain Research Topics (Max {max_results}):")
    for i, topic in enumerate(topics, 1):
        print(f"{i}. {topic}")