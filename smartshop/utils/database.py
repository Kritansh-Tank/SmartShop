"""
Database utility module for SQLite operations
"""

import sqlite3
import pandas as pd
import json
from pathlib import Path
import sys
import os

# Add the parent directory to the system path to import from config
sys.path.append(str(Path(__file__).parent.parent.parent))
from smartshop.config import DB_PATH, DATA_DIR

class Database:
    """Database manager for SmartShop application."""
    
    def __init__(self, db_path=DB_PATH):
        """Initialize the database connection."""
        self.db_path = db_path
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self.conn = None
        self.cursor = None
    
    def check_connection(self):
        """Check if the database exists and is accessible."""
        if os.path.exists(self.db_path):
            try:
                temp_conn = sqlite3.connect(self.db_path)
                temp_conn.close()
                return True
            except sqlite3.Error:
                return False
        return False
    
    def connect(self):
        """Connect to the SQLite database."""
        self.conn = sqlite3.connect(self.db_path)
        # Set text_factory to handle binary data correctly
        self.conn.text_factory = lambda b: b.decode('utf-8', errors='replace')
        self.cursor = self.conn.cursor()
        return self.conn
    
    def close(self):
        """Close the database connection."""
        if self.conn:
            self.conn.close()
            self.conn = None
            self.cursor = None
    
    def execute(self, query, params=None, commit=False):
        """Execute a SQL query."""
        if not self.conn:
            self.connect()
        
        if params:
            result = self.cursor.execute(query, params)
        else:
            result = self.cursor.execute(query)
        
        if commit:
            self.conn.commit()
        
        return result
    
    def executemany(self, query, params_list, commit=True):
        """Execute a SQL query with multiple parameter sets."""
        if not self.conn:
            self.connect()
        
        self.cursor.executemany(query, params_list)
        
        if commit:
            self.conn.commit()
    
    def fetch_all(self, query, params=None):
        """Execute a query and fetch all results."""
        self.execute(query, params)
        return self.cursor.fetchall()
    
    def fetch_one(self, query, params=None):
        """Execute a query and fetch one result."""
        self.execute(query, params)
        return self.cursor.fetchone()
    
    def fetch_df(self, query, params=None):
        """Execute a query and return results as a DataFrame."""
        if not self.conn:
            self.connect()
        
        if params:
            return pd.read_sql_query(query, self.conn, params=params)
        else:
            return pd.read_sql_query(query, self.conn)
    
    def table_exists(self, table_name):
        """Check if a table exists in the database."""
        query = "SELECT name FROM sqlite_master WHERE type='table' AND name=?"
        result = self.fetch_one(query, (table_name,))
        return result is not None
    
    def create_tables(self):
        """Create the necessary tables for the SmartShop application."""
        # Create customers table
        self.execute("""
        CREATE TABLE IF NOT EXISTS customers (
            customer_id TEXT PRIMARY KEY,
            age INTEGER,
            gender TEXT,
            location TEXT,
            browsing_history TEXT,
            purchase_history TEXT,
            customer_segment TEXT,
            avg_order_value REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """, commit=True)
        
        # Create products table
        self.execute("""
        CREATE TABLE IF NOT EXISTS products (
            product_id TEXT PRIMARY KEY,
            category TEXT,
            subcategory TEXT,
            price REAL,
            brand TEXT,
            avg_rating REAL,
            product_rating REAL,
            sentiment_score REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """, commit=True)
        
        # Create recommendations table
        self.execute("""
        CREATE TABLE IF NOT EXISTS recommendations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id TEXT,
            product_id TEXT,
            score REAL,
            recommended_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (customer_id) REFERENCES customers (customer_id),
            FOREIGN KEY (product_id) REFERENCES products (product_id)
        )
        """, commit=True)
        
        # Create interactions table (for tracking user-product interactions)
        self.execute("""
        CREATE TABLE IF NOT EXISTS interactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id TEXT,
            product_id TEXT,
            interaction_type TEXT,  -- browse, purchase, rate, etc.
            value REAL,  -- rating value, purchase amount, etc.
            interaction_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (customer_id) REFERENCES customers (customer_id),
            FOREIGN KEY (product_id) REFERENCES products (product_id)
        )
        """, commit=True)
        
        # Create agent_memory table (for storing agent memories)
        self.execute("""
        CREATE TABLE IF NOT EXISTS agent_memory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            agent_id TEXT,
            memory_type TEXT,
            memory_key TEXT,
            memory_value TEXT,
            embedding BLOB,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """, commit=True)
        
        # Create index for memory retrieval
        self.execute("""
        CREATE INDEX IF NOT EXISTS idx_agent_memory_agent_id_memory_type
        ON agent_memory (agent_id, memory_type)
        """, commit=True)
    
    def insert_customer(self, customer_data):
        """Insert or update a customer in the database."""
        # Convert list fields to JSON strings
        if isinstance(customer_data.get('browsing_history', []), list):
            customer_data['browsing_history'] = json.dumps(customer_data['browsing_history'])
        if isinstance(customer_data.get('purchase_history', []), list):
            customer_data['purchase_history'] = json.dumps(customer_data['purchase_history'])
        
        query = """
        INSERT OR REPLACE INTO customers 
        (customer_id, age, gender, location, browsing_history, purchase_history, 
         customer_segment, avg_order_value, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """
        params = (
            customer_data.get('customer_id'),
            customer_data.get('age'),
            customer_data.get('gender'),
            customer_data.get('location'),
            customer_data.get('browsing_history'),
            customer_data.get('purchase_history'),
            customer_data.get('customer_segment'),
            customer_data.get('avg_order_value')
        )
        self.execute(query, params, commit=True)
    
    def insert_product(self, product_data):
        """Insert or update a product in the database."""
        query = """
        INSERT OR REPLACE INTO products 
        (product_id, category, subcategory, price, brand,
         avg_rating, product_rating, sentiment_score, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """
        params = (
            product_data.get('product_id'),
            product_data.get('category'),
            product_data.get('subcategory'),
            product_data.get('price'),
            product_data.get('brand'),
            product_data.get('avg_rating'),
            product_data.get('product_rating'),
            product_data.get('sentiment_score')
        )
        self.execute(query, params, commit=True)
    
    def insert_recommendation(self, recommendation_data):
        """Insert a recommendation in the database."""
        query = """
        INSERT INTO recommendations 
        (customer_id, product_id, score, recommended_at)
        VALUES (?, ?, ?, CURRENT_TIMESTAMP)
        """
        params = (
            recommendation_data.get('customer_id'),
            recommendation_data.get('product_id'),
            recommendation_data.get('score')
        )
        self.execute(query, params, commit=True)
    
    def insert_interaction(self, interaction_data):
        """Insert an interaction in the database."""
        query = """
        INSERT INTO interactions 
        (customer_id, product_id, interaction_type, value, interaction_time)
        VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
        """
        params = (
            interaction_data.get('customer_id'),
            interaction_data.get('product_id'),
            interaction_data.get('interaction_type'),
            interaction_data.get('value')
        )
        self.execute(query, params, commit=True)
    
    def store_memory(self, agent_id, memory_type, memory_key, memory_value, embedding=None):
        """Store agent memory in the database."""
        query = """
        INSERT OR REPLACE INTO agent_memory 
        (agent_id, memory_type, memory_key, memory_value, embedding, updated_at)
        VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """
        params = (agent_id, memory_type, memory_key, memory_value, embedding)
        self.execute(query, params, commit=True)
    
    def retrieve_memory(self, agent_id, memory_type, memory_key=None):
        """Retrieve agent memory from the database."""
        if memory_key:
            query = """
            SELECT memory_value FROM agent_memory 
            WHERE agent_id = ? AND memory_type = ? AND memory_key = ?
            """
            result = self.fetch_one(query, (agent_id, memory_type, memory_key))
        else:
            query = """
            SELECT memory_key, memory_value FROM agent_memory 
            WHERE agent_id = ? AND memory_type = ?
            """
            result = self.fetch_all(query, (agent_id, memory_type))
        
        return result
    
    def get_customer(self, customer_id):
        """Get customer data by ID."""
        query = "SELECT * FROM customers WHERE customer_id = ?"
        result = self.fetch_one(query, (customer_id,))
        
        if result:
            # Convert column names and result to dict
            columns = [desc[0] for desc in self.cursor.description]
            customer_dict = {}
            
            # Safely handle potentially binary data when creating the dictionary
            for i, col in enumerate(columns):
                if isinstance(result[i], bytes):
                    try:
                        # First try UTF-8
                        customer_dict[col] = result[i].decode('utf-8')
                    except UnicodeDecodeError:
                        try:
                            # Try with 'latin-1' which can decode any byte value
                            customer_dict[col] = result[i].decode('latin-1')
                        except Exception:
                            try:
                                # Try with 'ascii' and ignore errors
                                customer_dict[col] = result[i].decode('ascii', errors='ignore')
                            except Exception:
                                # Last resort: represent as hex
                                customer_dict[col] = f"[Binary: {result[i].hex()[:10]}...]"
                else:
                    customer_dict[col] = result[i]
            
            # Parse JSON fields
            try:
                if customer_dict.get('browsing_history') and not isinstance(customer_dict['browsing_history'], list):
                    if not customer_dict['browsing_history'].startswith("[Binary:"):
                        customer_dict['browsing_history'] = json.loads(customer_dict['browsing_history'])
                if customer_dict.get('purchase_history') and not isinstance(customer_dict['purchase_history'], list):
                    if not customer_dict['purchase_history'].startswith("[Binary:"):
                        customer_dict['purchase_history'] = json.loads(customer_dict['purchase_history'])
            except json.JSONDecodeError:
                # Set to empty lists if JSON parsing fails
                if 'browsing_history' in customer_dict:
                    customer_dict['browsing_history'] = []
                if 'purchase_history' in customer_dict:
                    customer_dict['purchase_history'] = []
            
            return customer_dict
        
        return None
    
    def get_product(self, product_id):
        """Get product data by ID."""
        query = "SELECT * FROM products WHERE product_id = ?"
        result = self.fetch_one(query, (product_id,))
        
        if result:
            # Convert column names and result to dict
            columns = [desc[0] for desc in self.cursor.description]
            product_dict = {}
            
            # Safely handle potentially binary data when creating the dictionary
            for i, col in enumerate(columns):
                if isinstance(result[i], bytes):
                    try:
                        # First try UTF-8
                        product_dict[col] = result[i].decode('utf-8')
                    except UnicodeDecodeError:
                        try:
                            # Try with 'latin-1' which can decode any byte value
                            product_dict[col] = result[i].decode('latin-1')
                        except Exception:
                            try:
                                # Try with 'ascii' and ignore errors
                                product_dict[col] = result[i].decode('ascii', errors='ignore')
                            except Exception:
                                # Last resort: represent as hex
                                product_dict[col] = f"[Binary: {result[i].hex()[:10]}...]"
                else:
                    product_dict[col] = result[i]
            
            return product_dict
        
        return None
    
    def get_customer_recommendations(self, customer_id, limit=5):
        """Get recommendations for a specific customer."""
        query = """
        SELECT r.product_id, p.category, p.subcategory, p.price, p.brand, 
               p.product_rating, r.score
        FROM recommendations r
        JOIN products p ON r.product_id = p.product_id
        WHERE r.customer_id = ?
        ORDER BY r.score DESC, r.recommended_at DESC
        LIMIT ?
        """
        self.connect()
        result = self.fetch_all(query, (customer_id, limit))
        recommendations = []
        
        if result:
            columns = ["product_id", "category", "subcategory", "price", "brand", "product_rating", "score"]
            for row in result:
                rec_dict = {}
                for i, col in enumerate(columns):
                    # Safely handle potentially binary data
                    if isinstance(row[i], bytes):
                        try:
                            rec_dict[col] = row[i].decode('utf-8')
                        except UnicodeDecodeError:
                            rec_dict[col] = "[Binary data]"
                    else:
                        rec_dict[col] = row[i]
                recommendations.append(rec_dict)
        
        return recommendations
    
    def get_similar_customers(self, customer_id, limit=5):
        """Get similar customers based on demographics and behavior."""
        # First, get the target customer's data
        target = self.get_customer(customer_id)
        
        if not target:
            return []
        
        # Find similar customers based on segment, age range, and location
        query = """
        SELECT customer_id, age, gender, location, customer_segment, avg_order_value
        FROM customers
        WHERE customer_id != ? AND 
              customer_segment = ? AND 
              location = ? AND 
              ABS(age - ?) <= 5
        ORDER BY avg_order_value DESC
        LIMIT ?
        """
        
        params = (
            customer_id,
            target['customer_segment'],
            target['location'],
            target['age'],
            limit
        )
        
        self.connect()
        result = self.fetch_all(query, params)
        similar_customers = []
        
        if result:
            columns = ["customer_id", "age", "gender", "location", "customer_segment", "avg_order_value"]
            for row in result:
                customer_dict = {}
                for i, col in enumerate(columns):
                    # Safely handle potentially binary data
                    if isinstance(row[i], bytes):
                        try:
                            # First try UTF-8
                            customer_dict[col] = row[i].decode('utf-8')
                        except UnicodeDecodeError:
                            try:
                                # Try with 'latin-1' which can decode any byte value
                                customer_dict[col] = row[i].decode('latin-1')
                            except Exception:
                                try:
                                    # Try with 'ascii' and ignore errors
                                    customer_dict[col] = row[i].decode('ascii', errors='ignore')
                                except Exception:
                                    # Last resort: represent as hex
                                    customer_dict[col] = f"[Binary: {row[i].hex()[:10]}...]"
                    else:
                        customer_dict[col] = row[i]
                similar_customers.append(customer_dict)
        
        return similar_customers


# Initialize the database
def init_db():
    """Initialize the database and create tables."""
    print("Initializing database...")
    
    # First ensure the DB directory exists
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    
    # Check if the database already exists
    if os.path.exists(DB_PATH):
        print(f"Database already exists at {DB_PATH}")
        try:
            # Check if we can connect to it
            test_conn = sqlite3.connect(DB_PATH)
            test_conn.close()
            print("Successfully connected to existing database.")
        except sqlite3.Error as e:
            print(f"Error connecting to existing database: {e}")
            print("Will create a new database.")
            
            # Attempt to delete the existing database
            try:
                os.remove(DB_PATH)
                print(f"Removed existing database at {DB_PATH}")
            except OSError as e:
                print(f"Error removing existing database: {e}")
                print("Will try to continue anyway.")
    
    # Create a new database with explicit encoding settings
    db = Database()
    
    # Ensure SQLite encoding is configured correctly
    db.connect()
    
    # Set pragma for optimal performance and reliability
    db.execute("PRAGMA encoding = 'UTF-8'", commit=True)
    db.execute("PRAGMA foreign_keys = ON", commit=True)
    db.execute("PRAGMA journal_mode = WAL", commit=True)
    
    # Create all tables
    db.create_tables()
    
    # Check tables were created successfully
    tables = db.fetch_all("SELECT name FROM sqlite_master WHERE type='table'")
    if tables:
        print(f"Created tables: {', '.join(t[0] for t in tables)}")
    else:
        print("Warning: No tables were created.")
    
    db.close()
    return "Database initialized successfully."


if __name__ == "__main__":
    # Initialize the database when run directly
    print(init_db()) 