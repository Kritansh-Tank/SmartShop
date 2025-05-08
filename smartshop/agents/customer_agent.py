"""
Customer Agent for analyzing customer behavior and preferences
"""

import sys
import json
from pathlib import Path
from typing import Dict, List, Any, Optional

# Add the parent directory to the system path
sys.path.append(str(Path(__file__).parent.parent.parent))
from smartshop.agents.base_agent import Agent
from smartshop.utils.database import Database
from smartshop.config import AGENTS

class CustomerAgent(Agent):
    """Agent specializing in customer behavior analysis and preference modeling."""
    
    def __init__(self):
        """Initialize the Customer Agent."""
        super().__init__(
            agent_id="customer_agent",
            name=AGENTS["customer_agent"]["name"],
            description=AGENTS["customer_agent"]["description"]
        )
        self.db = Database()
        
        # Register tools
        self.register_tool(
            "get_customer_profile",
            self.get_customer_profile,
            "Get detailed information about a customer by ID"
        )
        self.register_tool(
            "analyze_browsing_history",
            self.analyze_browsing_history,
            "Analyze a customer's browsing history to identify patterns and preferences"
        )
        self.register_tool(
            "analyze_purchase_history",
            self.analyze_purchase_history,
            "Analyze a customer's purchase history to identify patterns and preferences"
        )
        self.register_tool(
            "find_similar_customers",
            self.find_similar_customers,
            "Find customers with similar profiles and behaviors"
        )
        self.register_tool(
            "predict_customer_interests",
            self.predict_customer_interests,
            "Predict a customer's interests based on their profile and behavior"
        )
    
    def get_customer_profile(self, customer_id: str) -> Dict[str, Any]:
        """Get a customer's profile information.
        
        Args:
            customer_id: The customer's unique identifier
        
        Returns:
            Dict containing customer profile information
        """
        customer = self.db.get_customer(customer_id)
        
        if not customer:
            return {"error": f"Customer {customer_id} not found"}
        
        # Remove potentially sensitive or irrelevant information
        if 'created_at' in customer:
            del customer['created_at']
        if 'updated_at' in customer:
            del customer['updated_at']
        
        # Track this observation
        observation = f"Retrieved profile for customer {customer_id}: {json.dumps(customer)}"
        self.store_memory("observations", observation)
        
        return customer
    
    def analyze_browsing_history(self, customer_id: str) -> Dict[str, Any]:
        """Analyze a customer's browsing history.
        
        Args:
            customer_id: The customer's unique identifier
        
        Returns:
            Dict containing browsing patterns and categories of interest
        """
        customer = self.db.get_customer(customer_id)
        
        if not customer:
            return {"error": f"Customer {customer_id} not found"}
        
        browsing_history = customer.get('browsing_history', [])
        
        if not browsing_history:
            return {"message": "No browsing history available"}
        
        # Use LLM to analyze browsing patterns
        prompt = f"""
        Analyze the following browsing history for customer {customer_id} and identify patterns, 
        categories of interest, and potential preferences:
        
        Browsing History: {browsing_history}
        
        Please provide:
        1. Top categories of interest
        2. Browsing patterns (time patterns, frequency, etc. if available)
        3. Potential products they might be interested in
        """
        
        analysis = self.llm.generate(prompt, system_prompt=self.system_prompt)
        
        # Structure the response
        result = {
            "customer_id": customer_id,
            "browsing_history": browsing_history,
            "analysis": analysis
        }
        
        # Track this analysis as an observation
        observation = f"Analyzed browsing history for customer {customer_id}: {analysis}"
        self.store_memory("observations", observation)
        
        return result
    
    def analyze_purchase_history(self, customer_id: str) -> Dict[str, Any]:
        """Analyze a customer's purchase history.
        
        Args:
            customer_id: The customer's unique identifier
        
        Returns:
            Dict containing purchase patterns and product preferences
        """
        customer = self.db.get_customer(customer_id)
        
        if not customer:
            return {"error": f"Customer {customer_id} not found"}
        
        purchase_history = customer.get('purchase_history', [])
        
        if not purchase_history:
            return {"message": "No purchase history available"}
        
        # Use LLM to analyze purchase patterns
        prompt = f"""
        Analyze the following purchase history for customer {customer_id} and identify patterns, 
        product preferences, and potential future purchases:
        
        Purchase History: {purchase_history}
        
        Please provide:
        1. Top categories purchased
        2. Price range preferences
        3. Purchase frequency
        4. Potential products they might purchase next
        """
        
        analysis = self.llm.generate(prompt, system_prompt=self.system_prompt)
        
        # Structure the response
        result = {
            "customer_id": customer_id,
            "purchase_history": purchase_history,
            "analysis": analysis
        }
        
        # Track this analysis as an observation
        observation = f"Analyzed purchase history for customer {customer_id}: {analysis}"
        self.store_memory("observations", observation)
        
        return result
    
    def find_similar_customers(self, customer_id: str, limit: int = 5) -> Dict[str, Any]:
        """Find customers similar to the given customer.
        
        Args:
            customer_id: The customer's unique identifier
            limit: Maximum number of similar customers to return
        
        Returns:
            Dict containing similar customers and similarity metrics
        """
        # Get similar customers from the database
        similar_customers = self.db.get_similar_customers(customer_id, limit)
        
        if not similar_customers:
            return {"message": f"No similar customers found for {customer_id}"}
        
        # Track this as an observation
        observation = f"Found {len(similar_customers)} similar customers for {customer_id}"
        self.store_memory("observations", observation)
        
        return {
            "customer_id": customer_id,
            "similar_customers": similar_customers
        }
    
    def predict_customer_interests(self, customer_id: str) -> Dict[str, Any]:
        """Predict a customer's interests based on their profile and behavior.
        
        Args:
            customer_id: The customer's unique identifier
        
        Returns:
            Dict containing predicted interests and confidence scores
        """
        # Get customer data
        customer = self.db.get_customer(customer_id)
        
        if not customer:
            return {"error": f"Customer {customer_id} not found"}
        
        # Get browsing and purchase history
        browsing_history = customer.get('browsing_history', [])
        purchase_history = customer.get('purchase_history', [])
        
        # Combine customer data for analysis
        customer_info = {
            "customer_id": customer_id,
            "age": customer.get('age'),
            "gender": customer.get('gender'),
            "location": customer.get('location'),
            "customer_segment": customer.get('customer_segment'),
            "browsing_history": browsing_history,
            "purchase_history": purchase_history
        }
        
        # Use LLM to predict interests
        prompt = f"""
        Based on the following customer information, predict their interests and product preferences:
        
        Customer Info: {json.dumps(customer_info)}
        
        Please provide:
        1. Top 5 product categories they might be interested in, with confidence scores (0-1)
        2. Specific product types within those categories they might like
        3. Price sensitivity assessment (low, medium, high)
        4. Likelihood to respond to promotions or discounts (0-1)
        """
        
        analysis = self.llm.generate(prompt, system_prompt=self.system_prompt)
        
        # Track this analysis
        observation = f"Predicted interests for customer {customer_id}: {analysis}"
        self.store_memory("observations", observation)
        
        # Structure the response
        return {
            "customer_id": customer_id,
            "predictions": analysis
        }
    
    def generate_customer_profile_summary(self, customer_id: str) -> str:
        """Generate a comprehensive summary of a customer's profile and behavior.
        
        Args:
            customer_id: The customer's unique identifier
        
        Returns:
            String summary of the customer profile
        """
        # Get customer data
        customer = self.db.get_customer(customer_id)
        
        if not customer:
            return f"Customer {customer_id} not found"
        
        # Analyze browsing and purchase history
        browsing_analysis = self.analyze_browsing_history(customer_id)
        purchase_analysis = self.analyze_purchase_history(customer_id)
        
        # Generate the summary using LLM
        prompt = f"""
        Generate a comprehensive customer profile summary based on the following information:
        
        Basic Info:
        - Customer ID: {customer_id}
        - Age: {customer.get('age')}
        - Gender: {customer.get('gender')}
        - Location: {customer.get('location')}
        - Segment: {customer.get('customer_segment')}
        
        Browsing Analysis:
        {browsing_analysis.get('analysis', 'No browsing analysis available')}
        
        Purchase Analysis:
        {purchase_analysis.get('analysis', 'No purchase analysis available')}
        
        Please provide a comprehensive, well-structured summary that highlights key characteristics,
        preferences, and behavior patterns of this customer. The summary should be useful for 
        personalized marketing and product recommendations.
        """
        
        summary = self.llm.generate(prompt, system_prompt=self.system_prompt)
        
        # Store the summary in memory
        self.store_memory("reflections", summary, f"customer_summary_{customer_id}")
        
        return summary 