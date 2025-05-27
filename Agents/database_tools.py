
import sqlite3

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