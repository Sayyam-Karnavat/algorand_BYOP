import json
import requests
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
    


@tool
def extract_keywords(text: str, num_keywords: int = 10, method: str = "frequency") -> str:
    """
    Extract keywords from text using various methods.
    
    Args:
        text: Input text
        num_keywords: Number of keywords to extract
        method: Extraction method - 'frequency', 'tfidf', 'rake'
    
    Returns:
        JSON string with extracted keywords
    """
    try:
        # Preprocess text
        words = word_tokenize(text.lower())
        stop_words = set(stopwords.words('english'))
        lemmatizer = WordNetLemmatizer()
        
        # Remove stopwords and lemmatize
        filtered_words = [
            lemmatizer.lemmatize(word) 
            for word in words 
            if word.isalnum() and word not in stop_words and len(word) > 2
        ]
        
        if method == "frequency":
            # Simple frequency count
            word_freq = Counter(filtered_words)
            keywords = word_freq.most_common(num_keywords)
            
        elif method == "tfidf":
            # Simple TF-IDF implementation
            from sklearn.feature_extraction.text import TfidfVectorizer
            
            sentences = sent_tokenize(text)
            vectorizer = TfidfVectorizer(stop_words='english', max_features=num_keywords)
            tfidf_matrix = vectorizer.fit_transform(sentences)
            
            feature_names = vectorizer.get_feature_names_out()
            mean_scores = tfidf_matrix.mean(axis=0).A1
            keywords = [(feature_names[i], mean_scores[i]) for i in mean_scores.argsort()[::-1][:num_keywords]]
            
        else:  # Default to frequency
            word_freq = Counter(filtered_words)
            keywords = word_freq.most_common(num_keywords)
        
        result = {
            'method': method,
            'keywords': [{'word': word, 'score': float(score)} for word, score in keywords],
            'total_words': len(filtered_words),
            'unique_words': len(set(filtered_words))
        }
        
        return json.dumps(result, indent=2)
        
    except Exception as e:
        return f"Error in keyword extraction: {str(e)}"
    

@tool
def analyze_text_complexity(text: str) -> str:
    """
    Analyze text complexity and readability metrics.
    
    Args:
        text: Input text to analyze
    
    Returns:
        JSON string with complexity metrics
    """
    try:
        sentences = sent_tokenize(text)
        words = word_tokenize(text)
        
        # Basic metrics
        num_sentences = len(sentences)
        num_words = len(words)
        num_chars = len(text)
        
        # Average metrics
        avg_words_per_sentence = num_words / num_sentences if num_sentences > 0 else 0
        avg_chars_per_word = num_chars / num_words if num_words > 0 else 0
        
        # Vocabulary diversity (Type-Token Ratio)
        unique_words = len(set(word.lower() for word in words if word.isalnum()))
        ttr = unique_words / num_words if num_words > 0 else 0
        
        # Simple readability score (Flesch Reading Ease approximation)
        asl = avg_words_per_sentence  # Average sentence length
        asw = sum(len(word) for word in words if word.isalnum()) / len([w for w in words if w.isalnum()])  # Average syllables per word (approximated by character length)
        
        flesch_score = 206.835 - (1.015 * asl) - (84.6 * (asw / 3))  # Simplified calculation
        
        # Complexity classification
        if flesch_score >= 60:
            complexity = "Easy"
        elif flesch_score >= 30:
            complexity = "Moderate"
        else:
            complexity = "Difficult"
        
        result = {
            'basic_stats': {
                'sentences': num_sentences,
                'words': num_words,
                'characters': num_chars,
                'unique_words': unique_words
            },
            'averages': {
                'words_per_sentence': round(avg_words_per_sentence, 2),
                'chars_per_word': round(avg_chars_per_word, 2)
            },
            'complexity_metrics': {
                'type_token_ratio': round(ttr, 3),
                'flesch_score': round(flesch_score, 2),
                'complexity_level': complexity
            }
        }
        
        return json.dumps(result, indent=2)
        
    except Exception as e:
        return f"Error in text analysis: {str(e)}"
    
