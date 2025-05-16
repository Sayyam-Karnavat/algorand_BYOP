```python
from langchain.agents import AgentExecutor, create_react_agent
from langchain_community.tools import ArxivQueryRun
from langchain_community.utilities import ArxivAPIWrapper
from langchain_ollama import OllamaLLM
from langchain.prompts import PromptTemplate

class DataGatherAgent:
    def __init__(self):
        self.llm = OllamaLLM(model="llama3.1:latest")
        arxiv_tool = ArxivQueryRun()
        self.arxiv_tool = arxiv_tool
        self.tool_descriptions = {"ArxivQueryRun": "A tool for querying papers on Arxiv."}

    def init_tools(self):
        """ Initialize the tools. """
        return [self.arxiv_tool]

class PromptTemplate(metaclass=ABCMeta):
    @abc.abstractproperty
    def max_length(self): ...

    def generate(self, input_query):
        if input_query:
            # Limit input length to prevent infinite loop
            max_length = self.max_length
            input_text = input_query[:max_length]
            return input_text
        else:
            return ""

def search_blockchain_papers(query, max_results=3):
    # Add check to ensure query is not empty
    if query:
        # Limit input length to prevent infinite loop
        max_length = 50
        input_text = query[:max_length]
        results = AgentExecutor.invoke(create_react_agent([self.arxiv_tool]), input_text)
        papers = []
        for result in results:
            paper = result.get("paper")
            if paper:
                papers.append(paper)
        return papers[:max_results]
    else:
        return []

if __name__ == "__main__":
    try:
        result = search_blockchain_papers("blockchain")
        print("\nFinal Result:")
        print(result)
    except Exception as e:
        print(f"An error occurred: {str(e)}")
```