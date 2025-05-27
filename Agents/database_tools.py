
import sqlite3
import json
from langchain.tools import tool

# ======================= DATABASE TOOLS =======================

@tool
def create_research_database(db_path: str = "research_papers.db") -> str:
    """
    Create a SQLite database for storing research papers and their metadata.
    
    Args:
        db_path: Path to the database file
    
    Returns:
        Status message
    """
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Create papers table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS papers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                arxiv_id TEXT UNIQUE,
                title TEXT NOT NULL,
                abstract TEXT,
                authors TEXT,
                published_date TEXT,
                categories TEXT,
                pdf_url TEXT,
                citation_count INTEGER DEFAULT 0,
                keywords TEXT,
                summary TEXT,
                complexity_score REAL,
                added_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create citations table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS citations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                paper_id INTEGER,
                cited_paper_id INTEGER,
                citation_context TEXT,
                FOREIGN KEY (paper_id) REFERENCES papers (id),
                FOREIGN KEY (cited_paper_id) REFERENCES papers (id)
            )
        ''')
        
        # Create research_sessions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS research_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_name TEXT NOT NULL,
                query TEXT,
                papers_found INTEGER,
                created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
        
        return f"Research database created successfully at: {db_path}"
        
    except Exception as e:
        return f"Error creating database: {str(e)}"
    

@tool
def save_paper_to_database(paper_data: str, db_path: str = "research_papers.db") -> str:
    """
    Save paper information to the research database.
    
    Args:
        paper_data: JSON string containing paper information
        db_path: Path to the database file
    
    Returns:
        Status message
    """
    try:
        paper = json.loads(paper_data)
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Insert paper data
        cursor.execute('''
            INSERT OR REPLACE INTO papers 
            (arxiv_id, title, abstract, authors, published_date, categories, 
             pdf_url, citation_count, keywords, summary, complexity_score)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            paper.get('id', '').split('/')[-1] if paper.get('id') else None,
            paper.get('title', ''),
            paper.get('summary', ''),
            json.dumps(paper.get('authors', [])),
            paper.get('published', ''),
            json.dumps(paper.get('categories', [])),
            paper.get('pdf_url', ''),
            paper.get('citation_count', 0),
            json.dumps(paper.get('keywords', [])),
            paper.get('ai_summary', ''),
            paper.get('complexity_score', 0.0)
        ))
        
        conn.commit()
        paper_id = cursor.lastrowid
        conn.close()
        
        return f"Paper saved to database with ID: {paper_id}"
        
    except Exception as e:
        return f"Error saving paper: {str(e)}"
    

def query_research_database(query: str, db_path: str = "research_papers.db") -> str:
    """
    Query the research database for papers matching criteria.
    
    Args:
        query: Search query (searches title, abstract, and keywords)
        db_path: Path to the database file
    
    Returns:
        JSON string with matching papers
    """
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Search query
        search_query = f"%{query}%"
        cursor.execute('''
            SELECT arxiv_id, title, abstract, authors, published_date, 
                   citation_count, keywords, complexity_score
            FROM papers 
            WHERE title LIKE ? OR abstract LIKE ? OR keywords LIKE ?
            ORDER BY citation_count DESC, published_date DESC
            LIMIT 20
        ''', (search_query, search_query, search_query))
        
        papers = []
        for row in cursor.fetchall():
            paper = {
                'arxiv_id': row[0],
                'title': row[1],
                'abstract': row[2][:300] + '...' if len(row[2]) > 300 else row[2],
                'authors': json.loads(row[3]) if row[3] else [],
                'published_date': row[4],
                'citation_count': row[5],
                'keywords': json.loads(row[6]) if row[6] else [],
                'complexity_score': row[7]
            }
            papers.append(paper)
        
        conn.close()
        
        result = {
            'query': query,
            'results_count': len(papers),
            'papers': papers
        }
        
        return json.dumps(result, indent=2)
        
    except Exception as e:
        logger.error(f"Error querying database: {e}")
        return f"Error querying database: {str(e)}"