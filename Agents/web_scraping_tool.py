
import requests
from langchain.tools import tool
from bs4 import BeautifulSoup
import re
import json


@tool
def scrape_paper_webpage(url: str) -> str:
    """
    Scrape additional information from a paper's webpage.
    
    Args:
        url: URL of the paper webpage
    
    Returns:
        JSON string with scraped information
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=10)        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Extract information
        result = {
            'url': url,
            'title': '',
            'abstract': '',
            'authors': [],
            'publication_info': '',
            'references_count': 0,
            'full_text_available': False
        }
        
        # Try to extract title
        title_selectors = ['h1', '.title', '#title', '[class*="title"]']
        for selector in title_selectors:
            title_elem = soup.select_one(selector)
            if title_elem:
                result['title'] = title_elem.get_text().strip()
                break
        
        # Try to extract abstract
        abstract_selectors = ['.abstract', '#abstract', '[class*="abstract"]']
        for selector in abstract_selectors:
            abstract_elem = soup.select_one(selector)
            if abstract_elem:
                result['abstract'] = abstract_elem.get_text().strip()
                break
        
        # Try to extract authors
        author_selectors = ['.authors', '.author', '[class*="author"]']
        for selector in author_selectors:
            author_elems = soup.select(selector)
            if author_elems:
                result['authors'] = [elem.get_text().strip() for elem in author_elems]
                break
        
        # Count references
        ref_selectors = ['[class*="reference"]', '[id*="reference"]', '.ref']
        for selector in ref_selectors:
            refs = soup.select(selector)
            if refs:
                result['references_count'] = len(refs)
                break
        
        # Check for full text
        if soup.find(text=re.compile(r'full.text|pdf|download', re.I)):
            result['full_text_available'] = True
        
        return json.dumps(result, indent=2)
        
    except Exception as e:
        return f"Error scraping webpage: {str(e)}"