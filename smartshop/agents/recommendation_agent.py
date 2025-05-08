"""
Recommendation Agent for generating personalized product recommendations
"""

import sys
import json
import random
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

# Add the parent directory to the system path
sys.path.append(str(Path(__file__).parent.parent.parent))
from smartshop.agents.base_agent import Agent
from smartshop.utils.database import Database
from smartshop.config import AGENTS, TOP_N_RECOMMENDATIONS, MIN_RECOMMENDATION_SCORE

class RecommendationAgent(Agent):
    """Agent specializing in generating personalized product recommendations."""
    
    def __init__(self):
        """Initialize the Recommendation Agent."""
        super().__init__(
            agent_id="recommendation_agent",
            name=AGENTS["recommendation_agent"]["name"],
            description=AGENTS["recommendation_agent"]["description"]
        )
        self.db = Database()
        
        # Register tools
        self.register_tool(
            "generate_recommendations",
            self.generate_recommendations,
            "Generate personalized recommendations for a customer"
        )
        self.register_tool(
            "get_recommendations_by_category",
            self.get_recommendations_by_category,
            "Generate recommendations in a specific category for a customer"
        )
        self.register_tool(
            "get_recommendations_by_occasion",
            self.get_recommendations_by_occasion,
            "Generate recommendations for a specific occasion or event"
        )
        self.register_tool(
            "get_recommendations_by_season",
            self.get_recommendations_by_season,
            "Generate recommendations based on the current season"
        )
        self.register_tool(
            "get_similar_customer_recommendations",
            self.get_similar_customer_recommendations,
            "Generate recommendations based on similar customers' preferences"
        )
    
    def _score_product_for_customer(self, customer_data: Dict[str, Any], product_data: Dict[str, Any]) -> float:
        """Calculate a recommendation score for a product and customer.
        
        Args:
            customer_data: Customer profile data
            product_data: Product data
            
        Returns:
            Recommendation score between 0 and 1
        """
        # Get browsing and purchase history
        browsing_history = customer_data.get('browsing_history', [])
        purchase_history = customer_data.get('purchase_history', [])
        
        # Calculate category match score
        category_match = 0.0
        if any(product_data['category'] in item for item in browsing_history):
            category_match += 0.3
        if any(product_data['category'] in item for item in purchase_history):
            category_match += 0.5
            
        # Calculate price match score based on average order value
        price_match = 0.0
        avg_order_value = customer_data.get('avg_order_value', 0)
        if avg_order_value > 0:
            # Customers tend to buy products with prices close to their average order value
            price_diff_ratio = abs(product_data['price'] - avg_order_value) / max(avg_order_value, 1000)
            price_match = max(0, 1 - min(price_diff_ratio, 1))
            
        # Use product rating as quality score
        quality_score = product_data.get('product_rating', 3.0) / 5.0
        
        # Calculate final score with weights
        score = (0.4 * category_match) + (0.3 * price_match) + (0.3 * quality_score)
        
        # Add a small random factor for diversity
        randomness = random.uniform(-0.05, 0.05)
        score = max(0, min(1, score + randomness))
        
        return score
    
    def generate_recommendations(self, customer_id: str, limit: int = TOP_N_RECOMMENDATIONS) -> Dict[str, Any]:
        """Generate personalized recommendations for a customer.
        
        Args:
            customer_id: The customer's unique identifier
            limit: Maximum number of recommendations to return
            
        Returns:
            Dict containing recommended products and explanations
        """
        # Get customer data
        customer = self.db.get_customer(customer_id)
        
        if not customer:
            return {"error": f"Customer {customer_id} not found"}
        
        # Query for potential products
        # In a real system, we would use a more sophisticated algorithm and pre-filter products
        query = """
        SELECT * FROM products
        ORDER BY product_rating DESC
        LIMIT 100
        """
        
        # Use direct database access instead of pandas
        self.db.connect()
        result = self.db.fetch_all(query)
        potential_products = []
        
        if result:
            # Get column names from cursor description
            columns = [desc[0] for desc in self.db.cursor.description]
            
            for row in result:
                product_dict = {}
                for i, col in enumerate(columns):
                    # Safely handle potentially binary data
                    if isinstance(row[i], bytes):
                        try:
                            product_dict[col] = row[i].decode('utf-8')
                        except UnicodeDecodeError:
                            product_dict[col] = "[Binary data]"
                    else:
                        product_dict[col] = row[i]
                potential_products.append(product_dict)
        
        if not potential_products:
            return {"message": "No products available for recommendations"}
        
        # Score each product for this customer
        scored_products = []
        for product in potential_products:
            score = self._score_product_for_customer(customer, product)
            if score >= MIN_RECOMMENDATION_SCORE:
                scored_products.append((product, score))
        
        # Sort by score (descending) and take top recommendations
        scored_products.sort(key=lambda x: x[1], reverse=True)
        top_recommendations = scored_products[:limit]
        
        # Format recommendations for storage and response
        recommendations_list = []
        for product, score in top_recommendations:
            # Store recommendation in database
            rec_data = {
                'customer_id': customer_id,
                'product_id': product['product_id'],
                'score': score
            }
            self.db.insert_recommendation(rec_data)
            
            # Add to response list
            recommendations_list.append({
                'product_id': product['product_id'],
                'category': product['category'],
                'subcategory': product['subcategory'],
                'price': product['price'],
                'brand': product['brand'],
                'score': score
            })
        
        # Use LLM to generate explanations for the recommendations
        prompt = f"""
        Generate personalized explanations for these product recommendations for customer {customer_id}:
        
        Customer Profile:
        {json.dumps({k: v for k, v in customer.items() if k not in ['created_at', 'updated_at']})}
        
        Recommended Products:
        {json.dumps(recommendations_list)}
        
        For each recommended product, provide:
        1. A personalized explanation of why this product would appeal to this customer
        2. How it relates to their browsing or purchase history
        3. Any special features of the product that align with the customer's preferences
        """
        
        explanations = self.llm.generate(prompt, system_prompt=self.system_prompt)
        
        # Track this as an observation
        observation = f"Generated {len(recommendations_list)} recommendations for customer {customer_id}"
        self.store_memory("observations", observation)
        
        return {
            "customer_id": customer_id,
            "recommendations": recommendations_list,
            "explanations": explanations
        }
    
    def get_recommendations_by_category(self, customer_id: str, category: str, limit: int = TOP_N_RECOMMENDATIONS) -> Dict[str, Any]:
        """Generate recommendations in a specific category for a customer.
        
        Args:
            customer_id: The customer's unique identifier
            category: Product category to recommend from
            limit: Maximum number of recommendations to return
            
        Returns:
            Dict containing recommended products and explanations
        """
        # Get customer data
        customer = self.db.get_customer(customer_id)
        
        if not customer:
            return {"error": f"Customer {customer_id} not found"}
        
        # Query for products in the specified category
        query = """
        SELECT * FROM products
        WHERE category = ?
        ORDER BY product_rating DESC
        LIMIT 50
        """
        
        # Use direct database access instead of pandas
        self.db.connect()
        result = self.db.fetch_all(query, (category,))
        potential_products = []
        
        if result:
            # Get column names from cursor description
            columns = [desc[0] for desc in self.db.cursor.description]
            
            for row in result:
                product_dict = {}
                for i, col in enumerate(columns):
                    # Safely handle potentially binary data
                    if isinstance(row[i], bytes):
                        try:
                            product_dict[col] = row[i].decode('utf-8')
                        except UnicodeDecodeError:
                            product_dict[col] = "[Binary data]"
                    else:
                        product_dict[col] = row[i]
                potential_products.append(product_dict)
        
        if not potential_products:
            return {"message": f"No products available in category {category}"}
        
        # Score each product for this customer
        scored_products = []
        for product in potential_products:
            score = self._score_product_for_customer(customer, product)
            if score >= MIN_RECOMMENDATION_SCORE:
                scored_products.append((product, score))
        
        # Sort by score (descending) and take top recommendations
        scored_products.sort(key=lambda x: x[1], reverse=True)
        top_recommendations = scored_products[:limit]
        
        # Format recommendations for storage and response
        recommendations_list = []
        for product, score in top_recommendations:
            # Store recommendation in database
            rec_data = {
                'customer_id': customer_id,
                'product_id': product['product_id'],
                'score': score
            }
            self.db.insert_recommendation(rec_data)
            
            # Add to response list
            recommendations_list.append({
                'product_id': product['product_id'],
                'category': product['category'],
                'subcategory': product['subcategory'],
                'price': product['price'],
                'brand': product['brand'],
                'score': score
            })
        
        # Use LLM to generate explanations for the recommendations
        prompt = f"""
        Generate personalized explanations for these {category} product recommendations for customer {customer_id}:
        
        Customer Profile:
        {json.dumps({k: v for k, v in customer.items() if k not in ['created_at', 'updated_at']})}
        
        Recommended Products in {category} category:
        {json.dumps(recommendations_list)}
        
        For each recommended product, provide:
        1. A personalized explanation of why this product would appeal to this customer
        2. How it relates to their browsing or purchase history
        3. Any special features of the product that align with the customer's preferences
        """
        
        explanations = self.llm.generate(prompt, system_prompt=self.system_prompt)
        
        # Track this as an observation
        observation = f"Generated {len(recommendations_list)} recommendations in {category} category for customer {customer_id}"
        self.store_memory("observations", observation)
        
        return {
            "customer_id": customer_id,
            "category": category,
            "recommendations": recommendations_list,
            "explanations": explanations
        }
    
    def get_recommendations_by_occasion(self, customer_id: str, occasion: str, limit: int = TOP_N_RECOMMENDATIONS) -> Dict[str, Any]:
        """Generate recommendations for a specific occasion or event.
        
        Args:
            customer_id: The customer's unique identifier
            occasion: The occasion or event (e.g., "birthday", "wedding")
            limit: Maximum number of recommendations to return
            
        Returns:
            Dict containing recommended products and explanations
        """
        # Get customer data
        customer = self.db.get_customer(customer_id)
        
        if not customer:
            return {"error": f"Customer {customer_id} not found"}
        
        # Query for well-rated products
        query = """
        SELECT * FROM products
        ORDER BY product_rating DESC
        LIMIT 50
        """
        
        # Use direct database access instead of pandas
        self.db.connect()
        result = self.db.fetch_all(query)
        potential_products = []
        
        if result:
            # Get column names from cursor description
            columns = [desc[0] for desc in self.db.cursor.description]
            
            for row in result:
                product_dict = {}
                for i, col in enumerate(columns):
                    # Safely handle potentially binary data
                    if isinstance(row[i], bytes):
                        try:
                            product_dict[col] = row[i].decode('utf-8')
                        except UnicodeDecodeError:
                            product_dict[col] = "[Binary data]"
                    else:
                        product_dict[col] = row[i]
                potential_products.append(product_dict)
        
        if not potential_products:
            return {"message": "No products available for recommendations"}
        
        # Use LLM to select and rank products for this occasion
        prompt = f"""
        For customer {customer_id} with the following profile:
        {json.dumps({k: v for k, v in customer.items() if k not in ['created_at', 'updated_at']})}
        
        And potential products:
        {json.dumps(potential_products[:20])}  # Limit to 20 for prompt size
        
        SELECT and RANK the top {limit} most suitable products for the occasion: {occasion}
        
        For each product, provide a suitability score (0-1) and a brief explanation of why it's
        appropriate for this occasion.
        
        ONLY include products that are truly relevant for a {occasion} occasion.
        The output should be in valid JSON format like:
        [
          {{
            "product_id": "...",
            "suitability_score": 0.95,
            "explanation": "This product is perfect for a {occasion} because..."
          }},
          ...
        ]
        """
        
        occasion_recommendations_json = self.llm.generate(prompt, system_prompt=self.system_prompt)
        
        # Parse the JSON response
        try:
            occasion_recommendations = json.loads(occasion_recommendations_json)
        except json.JSONDecodeError:
            # If parsing fails, try to extract JSON from the text
            try:
                json_start = occasion_recommendations_json.find('[')
                json_end = occasion_recommendations_json.rfind(']') + 1
                if json_start >= 0 and json_end > json_start:
                    occasion_recommendations = json.loads(occasion_recommendations_json[json_start:json_end])
                else:
                    # Fallback if we can't extract valid JSON
                    return {"message": f"Failed to generate recommendations for {occasion} occasion"}
            except:
                return {"message": f"Failed to generate recommendations for {occasion} occasion"}
        
        # Format the recommendations
        recommendations_list = []
        explanations_list = []
        
        # Get the full details for each recommended product
        for rec in occasion_recommendations[:limit]:
            product_id = rec.get('product_id')
            if not product_id:
                continue
            
            # Find the product details
            product_details = next((p for p in potential_products if p['product_id'] == product_id), None)
            if not product_details:
                continue
            
            # Create recommendation entry
            recommendations_list.append({
                'product_id': product_details['product_id'],
                'category': product_details['category'],
                'subcategory': product_details['subcategory'],
                'price': product_details['price'],
                'brand': product_details['brand'],
                'score': rec.get('suitability_score', 0.5)
            })
            
            # Store explanation
            explanations_list.append({
                'product_id': product_details['product_id'],
                'explanation': rec.get('explanation', '')
            })
            
            # Store recommendation in database
            rec_data = {
                'customer_id': customer_id,
                'product_id': product_details['product_id'],
                'score': rec.get('suitability_score', 0.5)
            }
            self.db.insert_recommendation(rec_data)
        
        # Use LLM to generate a cohesive explanation for all recommendations
        if recommendations_list:
            prompt = f"""
            Generate a cohesive explanation for why these products are recommended for customer {customer_id}'s {occasion} occasion:
            
            Customer Profile:
            {json.dumps({k: v for k, v in customer.items() if k not in ['created_at', 'updated_at']})}
            
            Recommended Products for {occasion.title()} Occasion:
            {json.dumps(recommendations_list)}
            
            Individual Product Explanations:
            {json.dumps(explanations_list)}
            
            Please craft a personalized, engaging message that weaves together the perfect {occasion} experience 
            with these products for this customer. Emphasize why they're ideal for this specific occasion and how 
            they match the customer's preferences.
            """
            
            cohesive_explanation = self.llm.generate(prompt, system_prompt=self.system_prompt)
        else:
            cohesive_explanation = f"We couldn't find suitable products for a {occasion} occasion based on your preferences."
        
        # Track this as an observation
        observation = f"Generated {len(recommendations_list)} recommendations for {occasion} occasion for customer {customer_id}"
        self.store_memory("observations", observation)
        
        return {
            "customer_id": customer_id,
            "occasion": occasion,
            "recommendations": recommendations_list,
            "explanations": cohesive_explanation
        }
    
    def get_recommendations_by_season(self, customer_id: str, season: str, limit: int = TOP_N_RECOMMENDATIONS) -> Dict[str, Any]:
        """Generate recommendations based on the current season.
        
        Args:
            customer_id: The customer's unique identifier
            season: The current season (e.g., "summer", "winter")
            limit: Maximum number of recommendations to return
            
        Returns:
            Dict containing recommended products and explanations
        """
        # Get customer data
        customer = self.db.get_customer(customer_id)
        
        if not customer:
            return {"error": f"Customer {customer_id} not found"}
        
        # Query for well-rated products
        query = """
        SELECT * FROM products
        ORDER BY product_rating DESC
        LIMIT 50
        """
        
        # Use direct database access instead of pandas
        self.db.connect()
        result = self.db.fetch_all(query)
        potential_products = []
        
        if result:
            # Get column names from cursor description
            columns = [desc[0] for desc in self.db.cursor.description]
            
            for row in result:
                product_dict = {}
                for i, col in enumerate(columns):
                    # Safely handle potentially binary data
                    if isinstance(row[i], bytes):
                        try:
                            product_dict[col] = row[i].decode('utf-8')
                        except UnicodeDecodeError:
                            product_dict[col] = "[Binary data]"
                    else:
                        product_dict[col] = row[i]
                potential_products.append(product_dict)
        
        if not potential_products:
            return {"message": "No products available for recommendations"}
        
        # Use LLM to identify and rank seasonal products
        prompt = f"""
        For customer {customer_id} with the following profile:
        {json.dumps({k: v for k, v in customer.items() if k not in ['created_at', 'updated_at']})}
        
        And potential products:
        {json.dumps(potential_products[:20])}  # Limit to 20 for prompt size
        
        SELECT and RANK the top {limit} most suitable products for the {season} season.
        
        For each product, provide a seasonal relevance score (0-1) and a brief explanation of why it's
        appropriate for the {season} season based on the customer's preferences.
        
        ONLY include products that are truly relevant for the {season} season.
        The output should be in valid JSON format like:
        [
          {{
            "product_id": "...",
            "seasonal_score": 0.95,
            "explanation": "This product is perfect for {season} because..."
          }},
          ...
        ]
        """
        
        seasonal_recommendations_json = self.llm.generate(prompt, system_prompt=self.system_prompt)
        
        # Parse the JSON response
        try:
            seasonal_recommendations = json.loads(seasonal_recommendations_json)
        except json.JSONDecodeError:
            # If parsing fails, try to extract JSON from the text
            try:
                json_start = seasonal_recommendations_json.find('[')
                json_end = seasonal_recommendations_json.rfind(']') + 1
                if json_start >= 0 and json_end > json_start:
                    seasonal_recommendations = json.loads(seasonal_recommendations_json[json_start:json_end])
                else:
                    # Fallback if we can't extract valid JSON
                    return {"message": f"Failed to generate recommendations for {season} season"}
            except:
                return {"message": f"Failed to generate recommendations for {season} season"}
        
        # Format the recommendations
        recommendations_list = []
        explanations_list = []
        
        # Get the full details for each recommended product
        for rec in seasonal_recommendations[:limit]:
            product_id = rec.get('product_id')
            if not product_id:
                continue
            
            # Find the product details
            product_details = next((p for p in potential_products if p['product_id'] == product_id), None)
            if not product_details:
                continue
            
            # Create recommendation entry
            recommendations_list.append({
                'product_id': product_details['product_id'],
                'category': product_details['category'],
                'subcategory': product_details['subcategory'],
                'price': product_details['price'],
                'brand': product_details['brand'],
                'score': rec.get('seasonal_score', 0.5)
            })
            
            # Store explanation
            explanations_list.append({
                'product_id': product_details['product_id'],
                'explanation': rec.get('explanation', '')
            })
            
            # Store recommendation in database
            rec_data = {
                'customer_id': customer_id,
                'product_id': product_details['product_id'],
                'score': rec.get('seasonal_score', 0.5)
            }
            self.db.insert_recommendation(rec_data)
        
        # Use LLM to generate a cohesive explanation for all recommendations
        if recommendations_list:
            prompt = f"""
            Generate a cohesive explanation for why these products are recommended for customer {customer_id} for the {season} season:
            
            Customer Profile:
            {json.dumps({k: v for k, v in customer.items() if k not in ['created_at', 'updated_at']})}
            
            Recommended Products for {season.title()} Season:
            {json.dumps(recommendations_list)}
            
            Individual Product Explanations:
            {json.dumps(explanations_list)}
            
            Please craft a personalized, engaging message that explains why these products are perfect for the {season} season,
            how they align with current seasonal trends, and how they match the customer's preferences.
            """
            
            cohesive_explanation = self.llm.generate(prompt, system_prompt=self.system_prompt)
        else:
            cohesive_explanation = f"We couldn't find suitable products for the {season} season based on your preferences."
        
        # Track this as an observation
        observation = f"Generated {len(recommendations_list)} recommendations for {season} season for customer {customer_id}"
        self.store_memory("observations", observation)
        
        return {
            "customer_id": customer_id,
            "season": season,
            "recommendations": recommendations_list,
            "explanations": cohesive_explanation
        }
    
    def get_similar_customer_recommendations(self, customer_id: str, limit: int = TOP_N_RECOMMENDATIONS) -> Dict[str, Any]:
        """Generate recommendations based on similar customers' preferences.
        
        Args:
            customer_id: The customer's unique identifier
            limit: Maximum number of recommendations to return
            
        Returns:
            Dict containing recommended products and explanations
        """
        # Get similar customers
        similar_customers = self.db.get_similar_customers(customer_id)
        
        if not similar_customers:
            # Fall back to regular recommendations if no similar customers
            return self.generate_recommendations(customer_id, limit)
        
        # Get recommendations for each similar customer
        similar_customer_ids = [sc['customer_id'] for sc in similar_customers]
        
        # Query for products that similar customers have interacted with
        placeholders = ','.join(['?' for _ in range(len(similar_customer_ids))])
        query = f"""
        SELECT DISTINCT p.product_id, p.category, p.subcategory, p.price, 
               p.brand, p.product_rating, COUNT(r.customer_id) as recommendation_count
        FROM products p
        JOIN recommendations r ON p.product_id = r.product_id
        WHERE r.customer_id IN ({placeholders})
        GROUP BY p.product_id
        ORDER BY recommendation_count DESC, p.product_rating DESC
        LIMIT 20
        """
        
        # Use direct database access instead of pandas
        self.db.connect()
        result = self.db.fetch_all(query, similar_customer_ids)
        candidate_products = []
        
        if result:
            columns = ["product_id", "category", "subcategory", "price", "brand", "product_rating", "recommendation_count"]
            for row in result:
                product_dict = {}
                for i, col in enumerate(columns):
                    # Safely handle potentially binary data
                    if isinstance(row[i], bytes):
                        try:
                            product_dict[col] = row[i].decode('utf-8')
                        except UnicodeDecodeError:
                            product_dict[col] = "[Binary data]"
                    else:
                        product_dict[col] = row[i]
                candidate_products.append(product_dict)
        
        # If not enough products, query for popular products
        if len(candidate_products) < limit:
            fallback_query = """
            SELECT product_id, category, subcategory, price, brand, product_rating
            FROM products
            ORDER BY product_rating DESC
            LIMIT ?
            """
            
            result = self.db.fetch_all(fallback_query, (20,))
            
            if result:
                columns = ["product_id", "category", "subcategory", "price", "brand", "product_rating"]
                for row in result:
                    # Skip products already in candidate_products
                    if any(p['product_id'] == row[0] for p in candidate_products):
                        continue
                        
                    product_dict = {}
                    for i, col in enumerate(columns):
                        # Safely handle potentially binary data
                        if isinstance(row[i], bytes):
                            try:
                                product_dict[col] = row[i].decode('utf-8')
                            except UnicodeDecodeError:
                                product_dict[col] = "[Binary data]"
                        else:
                            product_dict[col] = row[i]
                    product_dict["recommendation_count"] = 0  # Not recommended by similar customers
                    candidate_products.append(product_dict)
        
        if not candidate_products:
            # Fall back to regular recommendations if no candidate products
            return self.generate_recommendations(customer_id, limit)
        
        # Get customer data for personalization
        customer = self.db.get_customer(customer_id)
        
        # Score candidate products based on similar customer preferences and customer profile
        scored_products = []
        for product in candidate_products:
            # Base score from customer preferences
            base_score = self._score_product_for_customer(customer, product)
            
            # Boost score based on recommendation count from similar customers
            recommendation_boost = min(0.3, product.get("recommendation_count", 0) * 0.1)
            
            # Combined score
            combined_score = base_score + recommendation_boost
            
            if combined_score >= MIN_RECOMMENDATION_SCORE:
                scored_products.append((product, combined_score))
        
        # Sort by score (descending) and take top recommendations
        scored_products.sort(key=lambda x: x[1], reverse=True)
        top_recommendations = scored_products[:limit]
        
        # Format recommendations for storage and response
        recommendations_list = []
        for product, score in top_recommendations:
            # Store recommendation in database
            rec_data = {
                'customer_id': customer_id,
                'product_id': product['product_id'],
                'score': score
            }
            self.db.insert_recommendation(rec_data)
            
            # Add to response list
            recommendations_list.append({
                'product_id': product['product_id'],
                'category': product['category'],
                'subcategory': product['subcategory'],
                'price': product['price'],
                'brand': product['brand'],
                'score': score
            })
        
        # Use LLM to generate explanations for the recommendations
        prompt = f"""
        Generate personalized explanations for these product recommendations for customer {customer_id}, 
        based on similar customers' preferences:
        
        Customer Profile:
        {json.dumps({k: v for k, v in customer.items() if k not in ['created_at', 'updated_at']})}
        
        Similar Customers:
        {json.dumps(similar_customers)}
        
        Recommended Products:
        {json.dumps(recommendations_list)}
        
        For each recommended product, provide:
        1. A personalized explanation of why this product would appeal to this customer
        2. How it relates to what similar customers have enjoyed
        3. Any special features of the product that align with the customer's preferences
        """
        
        explanations = self.llm.generate(prompt, system_prompt=self.system_prompt)
        
        # Track this as an observation
        observation = f"Generated {len(recommendations_list)} recommendations for customer {customer_id} based on {len(similar_customers)} similar customers"
        self.store_memory("observations", observation)
        
        return {
            "customer_id": customer_id,
            "similar_customers": similar_customers,
            "recommendations": recommendations_list,
            "explanations": explanations
        } 