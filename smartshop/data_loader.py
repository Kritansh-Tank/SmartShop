"""
Data loader script to import CSV data into the SQLite database
"""

import sys
import os
import pandas as pd
import json
import ast
from pathlib import Path
from tqdm import tqdm

# Add the parent directory to the system path
sys.path.append(str(Path(__file__).parent.parent))
from smartshop.utils.database import Database, init_db
from smartshop.config import CUSTOMER_DATA_PATH, PRODUCT_DATA_PATH

def load_customer_data(db: Database, file_path: Path):
    """Load customer data from CSV file into the database.
    
    Args:
        db: Database instance
        file_path: Path to the customer data CSV file
    """
    print(f"Loading customer data from {file_path}...")
    
    # Read the CSV file with explicit encoding options
    try:
        # Try multiple encodings in order
        encodings = ['ascii', 'utf-8', 'latin-1']
        df = None
        
        for encoding in encodings:
            try:
                print(f"Attempting to read with {encoding} encoding...")
                df = pd.read_csv(file_path, encoding=encoding)
                print(f"Successfully loaded with {encoding} encoding.")
                break
            except UnicodeDecodeError:
                print(f"Failed to read with {encoding} encoding.")
                continue
        
        if df is None:
            # Last resort: read with latin-1 which should handle any byte values
            print(f"Using latin-1 encoding as fallback...")
            df = pd.read_csv(file_path, encoding='latin-1')
        
        print(f"Loaded {len(df)} customer records.")
    except Exception as e:
        print(f"Error loading customer data: {e}")
        return
    
    # Process and insert each customer record
    for _, row in tqdm(df.iterrows(), total=len(df)):
        try:
            # Convert string representations of lists to actual lists
            browsing_history = []
            purchase_history = []
            
            if 'Browsing_History' in row and row['Browsing_History']:
                try:
                    browsing_history = ast.literal_eval(row['Browsing_History'])
                except (ValueError, SyntaxError):
                    # Handle non-standard list formats or strings
                    browsing_history = row['Browsing_History'].replace('[', '').replace(']', '').split(',')
                    browsing_history = [item.strip() for item in browsing_history if item.strip()]
            
            if 'Purchase_History' in row and row['Purchase_History']:
                try:
                    purchase_history = ast.literal_eval(row['Purchase_History'])
                except (ValueError, SyntaxError):
                    # Handle non-standard list formats or strings
                    purchase_history = row['Purchase_History'].replace('[', '').replace(']', '').split(',')
                    purchase_history = [item.strip() for item in purchase_history if item.strip()]
            
            # Create customer record
            customer_data = {
                'customer_id': str(row['Customer_ID']),  # Convert to string to ensure consistency
                'age': row['Age'],
                'gender': str(row['Gender']),
                'location': str(row['Location']),
                'browsing_history': browsing_history,
                'purchase_history': purchase_history,
                'customer_segment': str(row['Customer_Segment']),
                'avg_order_value': row['Avg_Order_Value']
            }
            
            # Insert into database
            db.insert_customer(customer_data)
            
        except Exception as e:
            print(f"Error processing customer {row.get('Customer_ID', 'unknown')}: {e}")
    
    print("Customer data loaded successfully.")

def load_product_data(db: Database, file_path: Path):
    """Load product data from CSV file into the database.
    
    Args:
        db: Database instance
        file_path: Path to the product data CSV file
    """
    print(f"Loading product data from {file_path}...")
    
    # Read the CSV file with explicit encoding options
    try:
        # Try multiple encodings in order
        encodings = ['ascii', 'utf-8', 'latin-1']
        df = None
        
        for encoding in encodings:
            try:
                print(f"Attempting to read with {encoding} encoding...")
                df = pd.read_csv(file_path, encoding=encoding)
                print(f"Successfully loaded with {encoding} encoding.")
                break
            except UnicodeDecodeError:
                print(f"Failed to read with {encoding} encoding.")
                continue
        
        if df is None:
            # Last resort: read with latin-1 which should handle any byte values
            print(f"Using latin-1 encoding as fallback...")
            df = pd.read_csv(file_path, encoding='latin-1')
        
        print(f"Loaded {len(df)} product records.")
    except Exception as e:
        print(f"Error loading product data: {e}")
        return
    
    # Process and insert each product record
    for _, row in tqdm(df.iterrows(), total=len(df)):
        try:
            # Create product record
            product_data = {
                'product_id': str(row['Product_ID']),  # Convert to string to ensure consistency
                'category': str(row['Category']),
                'subcategory': str(row['Subcategory']),
                'price': row['Price'],
                'brand': str(row['Brand']),
                'avg_rating': row['Average_Rating_of_Similar_Products'],
                'product_rating': row['Product_Rating'],
                'sentiment_score': row['Customer_Review_Sentiment_Score']
            }
            
            # Insert into database
            db.insert_product(product_data)
            
        except Exception as e:
            print(f"Error processing product {row.get('Product_ID', 'unknown')}: {e}")
    
    print("Product data loaded successfully.")

def load_all_data():
    """Load all data from CSV files into the database."""
    print("Initializing database...")
    init_db()
    
    db = Database()
    
    # Load customer data
    if CUSTOMER_DATA_PATH.exists():
        load_customer_data(db, CUSTOMER_DATA_PATH)
    else:
        print(f"Customer data file not found: {CUSTOMER_DATA_PATH}")
    
    # Load product data
    if PRODUCT_DATA_PATH.exists():
        load_product_data(db, PRODUCT_DATA_PATH)
    else:
        print(f"Product data file not found: {PRODUCT_DATA_PATH}")
    
    # Close the database connection
    db.close()
    
    print("Data loading complete.")

def create_sample_data():
    """Create sample data for testing when real data is not available."""
    print("Creating sample data for testing...")
    
    db = Database()
    
    # Create sample customers
    sample_customers = [
        {
            'customer_id': 'C1000',
            'age': 28,
            'gender': 'Female',
            'location': 'New York',
            'browsing_history': ['Books', 'Fashion', 'Electronics'],
            'purchase_history': ['Biography', 'Jeans'],
            'customer_segment': 'New Visitor',
            'avg_order_value': 1500.0
        },
        {
            'customer_id': 'C1001',
            'age': 35,
            'gender': 'Male',
            'location': 'San Francisco',
            'browsing_history': ['Electronics', 'Fitness'],
            'purchase_history': ['Smartphone', 'Resistance Bands'],
            'customer_segment': 'Frequent Buyer',
            'avg_order_value': 2500.0
        },
        {
            'customer_id': 'C1002',
            'age': 42,
            'gender': 'Female',
            'location': 'Chicago',
            'browsing_history': ['Home Decor', 'Beauty'],
            'purchase_history': ['Wall Art', 'Lipstick'],
            'customer_segment': 'Occasional Shopper',
            'avg_order_value': 1200.0
        }
    ]
    
    # Create sample products
    sample_products = [
        {
            'product_id': 'P2000',
            'category': 'Electronics',
            'subcategory': 'Smartphone',
            'price': 999.99,
            'brand': 'TechBrand',
            'avg_rating': 4.5,
            'product_rating': 4.7,
            'sentiment_score': 0.85
        },
        {
            'product_id': 'P2001',
            'category': 'Fashion',
            'subcategory': 'Jeans',
            'price': 89.99,
            'brand': 'FashionCo',
            'avg_rating': 4.2,
            'product_rating': 4.1,
            'sentiment_score': 0.75
        },
        {
            'product_id': 'P2002',
            'category': 'Books',
            'subcategory': 'Biography',
            'price': 24.99,
            'brand': 'Publishers Inc',
            'avg_rating': 4.3,
            'product_rating': 4.4,
            'sentiment_score': 0.82
        },
        {
            'product_id': 'P2003',
            'category': 'Home Decor',
            'subcategory': 'Wall Art',
            'price': 149.99,
            'brand': 'HomeStyle',
            'avg_rating': 4.0,
            'product_rating': 4.2,
            'sentiment_score': 0.78
        },
        {
            'product_id': 'P2004',
            'category': 'Beauty',
            'subcategory': 'Lipstick',
            'price': 19.99,
            'brand': 'BeautyGlow',
            'avg_rating': 4.1,
            'product_rating': 4.0,
            'sentiment_score': 0.72
        },
        {
            'product_id': 'P2005',
            'category': 'Fitness',
            'subcategory': 'Resistance Bands',
            'price': 29.99,
            'brand': 'FitLife',
            'avg_rating': 4.4,
            'product_rating': 4.3,
            'sentiment_score': 0.80
        }
    ]
    
    # Insert sample customers
    for customer in sample_customers:
        db.insert_customer(customer)
    
    # Insert sample products
    for product in sample_products:
        db.insert_product(product)
    
    # Create some sample recommendations
    sample_recommendations = [
        {
            'customer_id': 'C1000',
            'product_id': 'P2002',
            'score': 0.92
        },
        {
            'customer_id': 'C1000',
            'product_id': 'P2001',
            'score': 0.85
        },
        {
            'customer_id': 'C1001',
            'product_id': 'P2000',
            'score': 0.95
        },
        {
            'customer_id': 'C1001',
            'product_id': 'P2005',
            'score': 0.88
        },
        {
            'customer_id': 'C1002',
            'product_id': 'P2003',
            'score': 0.90
        },
        {
            'customer_id': 'C1002',
            'product_id': 'P2004',
            'score': 0.87
        }
    ]
    
    # Insert sample recommendations
    for recommendation in sample_recommendations:
        db.insert_recommendation(recommendation)
    
    # Close the database connection
    db.close()
    
    print("Sample data created successfully.")

def main():
    """Main entry point for the data loader script."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Data loader for SmartShop E-commerce Recommendation System')
    parser.add_argument('--sample', action='store_true', help='Create sample data instead of loading from CSV')
    
    args = parser.parse_args()
    
    if args.sample:
        # Initialize the database first
        init_db()
        # Create sample data
        create_sample_data()
    else:
        # Load data from CSV files
        load_all_data()

if __name__ == "__main__":
    main() 