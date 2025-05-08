"""
Main module for the SmartShop E-commerce Personalized Recommendation System
"""

import sys
import json
import argparse
from pathlib import Path
from typing import Dict, List, Any, Optional

# Add the parent directory to the system path
sys.path.append(str(Path(__file__).parent.parent))
from smartshop.agents.coordination_agent import CoordinationAgent
from smartshop.utils.database import Database, init_db
from smartshop.config import AGENTS

def initialize_system():
    """Initialize the system by setting up the database and agents."""
    print("Initializing SmartShop E-commerce Personalized Recommendation System...")
    
    # Initialize the database
    init_db()
    
    # Initialize the coordination agent (which initializes all other agents)
    agent = CoordinationAgent()
    
    print("System initialization complete.")
    return agent

def get_recommendations(customer_id: str, context: Optional[Dict[str, Any]] = None):
    """Get personalized recommendations for a customer."""
    agent = CoordinationAgent()
    
    # Use the coordination agent to get personalized recommendations
    result = agent.get_personalized_recommendations(customer_id, context)
    
    return result

def get_customer_analysis(customer_id: str):
    """Get comprehensive analysis of a customer's profile and behavior."""
    agent = CoordinationAgent()
    
    # Use the coordination agent to get customer profile analysis
    result = agent.get_customer_profile_analysis(customer_id)
    
    return result

def get_product_analysis(product_id: str):
    """Get comprehensive analysis of a product."""
    agent = CoordinationAgent()
    
    # Use the coordination agent to get product analysis
    result = agent.get_product_analysis(product_id)
    
    return result

def get_category_analysis(category: str):
    """Get analysis of trends in a product category."""
    agent = CoordinationAgent()
    
    # Use the coordination agent to get category trend analysis
    result = agent.get_category_trend_analysis(category)
    
    return result

def get_seasonal_recommendations(customer_id: str, season: str):
    """Get seasonal product recommendations for a customer."""
    agent = CoordinationAgent()
    
    # Use the coordination agent to get seasonal recommendations
    result = agent.get_seasonal_recommendations(customer_id, season)
    
    return result

def main():
    """Main entry point for the command-line interface."""
    parser = argparse.ArgumentParser(description='SmartShop E-commerce Personalized Recommendation System')
    
    # Define subparsers for different commands
    subparsers = parser.add_subparsers(dest='command', help='Command to run')
    
    # Initialize command
    init_parser = subparsers.add_parser('init', help='Initialize the system')
    
    # Recommend command
    recommend_parser = subparsers.add_parser('recommend', help='Get personalized recommendations')
    recommend_parser.add_argument('customer_id', help='Customer ID')
    recommend_parser.add_argument('--context', type=json.loads, help='Context as JSON (e.g., {"occasion": "birthday"})')
    
    # Customer analysis command
    customer_parser = subparsers.add_parser('customer', help='Get customer analysis')
    customer_parser.add_argument('customer_id', help='Customer ID')
    
    # Product analysis command
    product_parser = subparsers.add_parser('product', help='Get product analysis')
    product_parser.add_argument('product_id', help='Product ID')
    
    # Category analysis command
    category_parser = subparsers.add_parser('category', help='Get category analysis')
    category_parser.add_argument('category', help='Product category')
    
    # Seasonal recommendations command
    seasonal_parser = subparsers.add_parser('seasonal', help='Get seasonal recommendations')
    seasonal_parser.add_argument('customer_id', help='Customer ID')
    seasonal_parser.add_argument('season', help='Season (e.g., Summer, Winter)')
    
    # Parse arguments
    args = parser.parse_args()
    
    # Execute the appropriate command
    if args.command == 'init':
        initialize_system()
        print("System initialized successfully.")
    
    elif args.command == 'recommend':
        result = get_recommendations(args.customer_id, args.context)
        print(json.dumps(result, indent=2))
    
    elif args.command == 'customer':
        result = get_customer_analysis(args.customer_id)
        print(json.dumps(result, indent=2))
    
    elif args.command == 'product':
        result = get_product_analysis(args.product_id)
        print(json.dumps(result, indent=2))
    
    elif args.command == 'category':
        result = get_category_analysis(args.category)
        print(json.dumps(result, indent=2))
    
    elif args.command == 'seasonal':
        result = get_seasonal_recommendations(args.customer_id, args.season)
        print(json.dumps(result, indent=2))
    
    else:
        parser.print_help()

if __name__ == "__main__":
    main() 