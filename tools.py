import os
import json
import re
import requests
import sqlite3
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Union
from urllib.parse import urlparse, quote
import xml.etree.ElementTree as ET
import logging

# LangChain tools
from langchain.tools import tool
from langchain_community.document_loaders import PyPDFLoader, WebBaseLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter

# Data analysis
import pandas as pd
import numpy as np
from collections import Counter
import matplotlib.pyplot as plt
import seaborn as sns
from wordcloud import WordCloud

# NLP
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize, sent_tokenize
from nltk.stem import WordNetLemmatizer

# Web scraping
from bs4 import BeautifulSoup



# Download required NLTK data
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')

try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('stopwords')

try:
    nltk.data.find('corpora/wordnet')
except LookupError:
    nltk.download('wordnet')


# ======================= ARXIV TOOLS =======================

@tool
def search_arxiv_advanced(query: str, max_results: int = 10, sort_by: str = "relevance", 
                         category: str = "", start_date: str = "", end_date: str = "") -> str:
    """
    Advanced ArXiv search with filtering options.
    
    Args:
        query: Search query string
        max_results: Maximum number of results to return (default: 10)
        sort_by: Sort order - 'relevance', 'lastUpdatedDate', 'submittedDate' (default: relevance)
        category: ArXiv category filter (e.g., 'cs.AI', 'stat.ML')
        start_date: Start date filter (YYYY-MM-DD format)
        end_date: End date filter (YYYY-MM-DD format)
    
    Returns:
        JSON string with paper details
    """
    try:
        # Build query
        search_query = query
        if category:
            search_query = f"cat:{category} AND ({query})"
        
        # Date filtering
        if start_date or end_date:
            date_filter = []
            if start_date:
                date_filter.append(f"submittedDate:[{start_date}*")
            if end_date:
                date_filter.append(f"TO {end_date}*]")
            if len(date_filter) == 2:
                search_query += f" AND submittedDate:[{start_date}* TO {end_date}*]"
            elif start_date:
                search_query += f" AND submittedDate:[{start_date}* TO *]"
            elif end_date:
                search_query += f" AND submittedDate:[* TO {end_date}*]"
        
        # ArXiv API call
        base_url = "http://export.arxiv.org/api/query"
        params = {
            'search_query': search_query,
            'start': 0,
            'max_results': max_results,
            'sortBy': sort_by,
            'sortOrder': 'descending'
        }
        
        response = requests.get(base_url, params=params)
        response.raise_for_status()
        
        # Parse XML response
        root = ET.fromstring(response.content)
        papers = []
        
        for entry in root.findall('{http://www.w3.org/2005/Atom}entry'):
            paper = {
                'id': entry.find('{http://www.w3.org/2005/Atom}id').text,
                'title': entry.find('{http://www.w3.org/2005/Atom}title').text.strip(),
                'summary': entry.find('{http://www.w3.org/2005/Atom}summary').text.strip(),
                'authors': [author.find('{http://www.w3.org/2005/Atom}name').text 
                           for author in entry.findall('{http://www.w3.org/2005/Atom}author')],
                'published': entry.find('{http://www.w3.org/2005/Atom}published').text,
                'updated': entry.find('{http://www.w3.org/2005/Atom}updated').text,
                'categories': [cat.get('term') for cat in entry.findall('{http://www.w3.org/2005/Atom}category')],
                'pdf_url': next((link.get('href') for link in entry.findall('{http://www.w3.org/2005/Atom}link') 
                               if link.get('title') == 'pdf'), None)
            }
            papers.append(paper)
        
        return json.dumps(papers, indent=2)
        
    except Exception as e:
        return f"Error searching ArXiv: {str(e)}"
    
@tool
def get_paper_citations(arxiv_id: str) -> str:
    """
    Get citation count and related papers for an ArXiv paper using Semantic Scholar API.
    
    Args:
        arxiv_id: ArXiv paper ID (e.g., '2012.12345')
    
    Returns:
        JSON string with citation information
    """
    try:
        # Clean ArXiv ID
        if arxiv_id.startswith('http'):
            arxiv_id = arxiv_id.split('/')[-1]
        if arxiv_id.startswith('arXiv:'):
            arxiv_id = arxiv_id[6:]
        
        # Semantic Scholar API
        url = f"https://api.semanticscholar.org/graph/v1/paper/ARXIV:{arxiv_id}"
        params = {
            'fields': 'title,authors,citationCount,citations.title,citations.authors,references.title,references.authors,year,venue'
        }
        
        response = requests.get(url, params=params)
        
        if response.status_code == 200:
            data = response.json()
            
            result = {
                'title': data.get('title', ''),
                'citation_count': data.get('citationCount', 0),
                'year': data.get('year', ''),
                'venue': data.get('venue', ''),
                'top_citations': [
                    {
                        'title': cite.get('title', ''),
                        'authors': [author.get('name', '') for author in cite.get('authors', [])]
                    }
                    for cite in data.get('citations', [])[:5]
                ],
                'top_references': [
                    {
                        'title': ref.get('title', ''),
                        'authors': [author.get('name', '') for author in ref.get('authors', [])]
                    }
                    for ref in data.get('references', [])[:5]
                ]
            }
            
            return json.dumps(result, indent=2)
        else:
            return f"Could not find citation data for ArXiv ID: {arxiv_id}"
            
    except Exception as e:
        return f"Error retrieving citation data: {str(e)}"
    
