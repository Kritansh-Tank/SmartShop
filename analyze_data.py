import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

# Paths to dataset files
CUSTOMER_DATA = Path("Dataset/[Usecase 2] Personalized Recommendations for E-Commerce/customer_data_collection.csv")
PRODUCT_DATA = Path("Dataset/[Usecase 2] Personalized Recommendations for E-Commerce/product_recommendation_data.csv")

def load_and_clean_customer_data():
    """Load and clean customer data"""
    try:
        # Try different encodings
        for encoding in ['utf-8', 'latin1', 'cp1252']:
            try:
                df = pd.read_csv(CUSTOMER_DATA, encoding=encoding)
                break
            except UnicodeDecodeError:
                continue
            except Exception as e:
                print(f"Error reading customer data with encoding {encoding}: {e}")
                return None
        
        print(f"\n{'='*80}")
        print(f"CUSTOMER DATA ANALYSIS")
        print(f"{'='*80}")
        print(f"File: {CUSTOMER_DATA}")
        print(f"Shape: {df.shape} (rows, columns)")
        print(f"Columns: {df.columns.tolist()}")
        
        # Handle missing values
        print(f"\nMissing values before cleaning:")
        print(df.isnull().sum())
        
        # Basic data cleaning and type conversion
        # (Add specific cleaning steps as needed based on the data)
        
        print("\nSample data:")
        pd.set_option('display.max_columns', None)
        pd.set_option('display.width', 1000)
        print(df.head())
        
        # Customer data insights
        print("\nCustomer insights:")
        if 'Age' in df.columns:
            print(f"Age statistics: \n{df['Age'].describe()}")
        
        if 'Gender' in df.columns:
            print(f"\nGender distribution: \n{df['Gender'].value_counts()}")
        
        if 'Location' in df.columns:
            print(f"\nTop locations: \n{df['Location'].value_counts().head(5)}")
        
        if 'Customer_Segment' in df.columns:
            print(f"\nCustomer segments: \n{df['Customer_Segment'].value_counts()}")
        
        return df
    
    except Exception as e:
        print(f"Error processing customer data: {e}")
        return None

def load_and_clean_product_data():
    """Load and clean product data"""
    try:
        # Try different encodings
        for encoding in ['utf-8', 'latin1', 'cp1252']:
            try:
                df = pd.read_csv(PRODUCT_DATA, encoding=encoding)
                break
            except UnicodeDecodeError:
                continue
            except Exception as e:
                print(f"Error reading product data with encoding {encoding}: {e}")
                return None
        
        print(f"\n{'='*80}")
        print(f"PRODUCT DATA ANALYSIS")
        print(f"{'='*80}")
        print(f"File: {PRODUCT_DATA}")
        print(f"Shape: {df.shape} (rows, columns)")
        print(f"Columns: {df.columns.tolist()}")
        
        # Handle missing values
        print(f"\nMissing values before cleaning:")
        print(df.isnull().sum())
        
        # Basic data cleaning and type conversion
        # (Add specific cleaning steps as needed based on the data)
        
        print("\nSample data:")
        pd.set_option('display.max_columns', None)
        pd.set_option('display.width', 1000)
        print(df.head())
        
        # Product data insights
        print("\nProduct insights:")
        if 'Category' in df.columns:
            print(f"Categories: \n{df['Category'].value_counts()}")
        
        if 'Price' in df.columns:
            print(f"\nPrice statistics: \n{df['Price'].describe()}")
        
        if 'Product_Rating' in df.columns:
            print(f"\nRating statistics: \n{df['Product_Rating'].describe()}")
        
        if 'Probability_of_Recommendation' in df.columns:
            print(f"\nRecommendation probability statistics: \n{df['Probability_of_Recommendation'].describe()}")
        
        return df
    
    except Exception as e:
        print(f"Error processing product data: {e}")
        return None

if __name__ == "__main__":
    print("Analyzing e-commerce dataset for personalized recommendations")
    
    customer_df = load_and_clean_customer_data()
    product_df = load_and_clean_product_data()
    
    print("\nDataset analysis complete.") 