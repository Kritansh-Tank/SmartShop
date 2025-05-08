"""
Coordination Agent for orchestrating the interaction between other agents
"""

import sys
import json
from pathlib import Path
from typing import Dict, List, Any, Optional

# Add the parent directory to the system path
sys.path.append(str(Path(__file__).parent.parent.parent))
from smartshop.agents.base_agent import Agent
from smartshop.agents.customer_agent import CustomerAgent
from smartshop.agents.product_agent import ProductAgent
from smartshop.agents.recommendation_agent import RecommendationAgent
from smartshop.utils.database import Database
from smartshop.config import AGENTS

class CoordinationAgent(Agent):
    """Agent responsible for coordinating the interactions between other agents in the system."""
    
    def __init__(self):
        """Initialize the Coordination Agent."""
        super().__init__(
            agent_id="coordination_agent",
            name=AGENTS["coordination_agent"]["name"],
            description=AGENTS["coordination_agent"]["description"]
        )
        self.db = Database()
        
        # Initialize other agents
        self.customer_agent = CustomerAgent()
        self.product_agent = ProductAgent()
        self.recommendation_agent = RecommendationAgent()
        
        # Register tools
        self.register_tool(
            "get_personalized_recommendations",
            self.get_personalized_recommendations,
            "Get personalized product recommendations for a customer"
        )
        self.register_tool(
            "get_customer_profile_analysis",
            self.get_customer_profile_analysis,
            "Get comprehensive analysis of a customer's profile and behavior"
        )
        self.register_tool(
            "get_product_analysis",
            self.get_product_analysis,
            "Get comprehensive analysis of a product, its context, and potential customers"
        )
        self.register_tool(
            "get_category_trend_analysis",
            self.get_category_trend_analysis,
            "Get analysis of trends in a product category"
        )
        self.register_tool(
            "get_seasonal_recommendations",
            self.get_seasonal_recommendations,
            "Get seasonal product recommendations for a customer"
        )
    
    def get_personalized_recommendations(self, customer_id: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Get personalized product recommendations for a customer.
        
        Args:
            customer_id: The customer's unique identifier
            context: Optional context for the recommendation (e.g., occasion, season)
            
        Returns:
            Dict containing personalized recommendations with explanations
        """
        # Get the customer profile from the customer agent
        customer_profile = self.customer_agent.get_customer_profile(customer_id)
        
        if 'error' in customer_profile:
            return customer_profile
        
        # Predict customer interests based on their profile
        customer_interests = self.customer_agent.predict_customer_interests(customer_id)
        
        # Determine what type of recommendations to get based on context
        if context and 'occasion' in context:
            # Get occasion-specific recommendations
            recommendation_result = self.recommendation_agent.get_recommendations_by_occasion(
                customer_id, context['occasion']
            )
        elif context and 'season' in context:
            # Get season-specific recommendations
            recommendation_result = self.recommendation_agent.get_recommendations_by_season(
                customer_id, context['season']
            )
        elif context and 'category' in context:
            # Get category-specific recommendations
            recommendation_result = self.recommendation_agent.get_recommendations_by_category(
                customer_id, context['category']
            )
        else:
            # Get general personalized recommendations
            recommendation_result = self.recommendation_agent.generate_recommendations(customer_id)
        
        # Get product insights for the top recommended product (if any)
        product_insights = None
        if recommendation_result.get('recommendations', []):
            top_product_id = recommendation_result['recommendations'][0]['product_id']
            product_insights = self.product_agent.get_product_details(top_product_id)
        
        # Combine all insights using LLM
        prompt = f"""
        Create a comprehensive personalized shopping experience for customer {customer_id} based on:
        
        1. Customer Profile: 
        {json.dumps(customer_profile)}
        
        2. Customer Interests: 
        {json.dumps(customer_interests.get('predictions', ''))}
        
        3. Product Recommendations: 
        {json.dumps(recommendation_result.get('recommendations', []))}
        
        4. Recommendation Explanations: 
        {recommendation_result.get('explanations', '')}
        
        {f"5. Top Product Insights: {json.dumps(product_insights)}" if product_insights else ""}
        
        Please provide:
        1. A personalized shopping guide that introduces the recommendations
        2. Why these products are perfect for this customer
        3. How these recommendations align with their interests and preferences
        4. Any cross-selling or complementary product opportunities
        """
        
        personalized_shopping_guide = self.llm.generate(prompt, system_prompt=self.system_prompt)
        
        # Track this as an observation
        observation = f"Created personalized shopping guide for customer {customer_id} with {len(recommendation_result.get('recommendations', []))} recommendations"
        self.store_memory("observations", observation)
        
        # Combine all results into a unified response
        return {
            "customer_id": customer_id,
            "context": context,
            "recommendations": recommendation_result.get('recommendations', []),
            "customer_interests": customer_interests.get('predictions', ''),
            "personalized_shopping_guide": personalized_shopping_guide
        }
    
    def get_customer_profile_analysis(self, customer_id: str) -> Dict[str, Any]:
        """Get comprehensive analysis of a customer's profile and behavior.
        
        Args:
            customer_id: The customer's unique identifier
            
        Returns:
            Dict containing customer profile analysis
        """
        # Get customer profile data
        customer_profile = self.customer_agent.get_customer_profile(customer_id)
        
        if 'error' in customer_profile:
            return customer_profile
        
        # Get browsing history analysis
        browsing_analysis = self.customer_agent.analyze_browsing_history(customer_id)
        
        # Get purchase history analysis
        purchase_analysis = self.customer_agent.analyze_purchase_history(customer_id)
        
        # Get similar customers
        similar_customers = self.customer_agent.find_similar_customers(customer_id)
        
        # Get recommendations for this customer
        recommendations = self.recommendation_agent.generate_recommendations(customer_id)
        
        # Generate a comprehensive customer profile summary
        customer_summary = self.customer_agent.generate_customer_profile_summary(customer_id)
        
        # Track this as an observation
        observation = f"Generated comprehensive profile analysis for customer {customer_id}"
        self.store_memory("observations", observation)
        
        # Combine all results into a unified response
        return {
            "customer_id": customer_id,
            "profile": customer_profile,
            "browsing_analysis": browsing_analysis.get('analysis', ''),
            "purchase_analysis": purchase_analysis.get('analysis', ''),
            "similar_customers": similar_customers.get('similar_customers', []),
            "recommendations": recommendations.get('recommendations', []),
            "summary": customer_summary
        }
    
    def get_product_analysis(self, product_id: str) -> Dict[str, Any]:
        """Get comprehensive analysis of a product, its context, and potential customers.
        
        Args:
            product_id: The product's unique identifier
            
        Returns:
            Dict containing product analysis
        """
        # Get product details
        product_details = self.product_agent.get_product_details(product_id)
        
        if 'error' in product_details:
            return product_details
        
        # Get similar products
        similar_products = self.product_agent.find_similar_products(product_id)
        
        # Get complementary products
        complementary_products = self.product_agent.find_complementary_products(product_id)
        
        # Get category insights
        category_insights = self.product_agent.get_category_insights(product_details['category'])
        
        # Generate comprehensive product insight report
        product_report = self.product_agent.generate_product_insight_report(product_id)
        
        # Track this as an observation
        observation = f"Generated comprehensive analysis for product {product_id}"
        self.store_memory("observations", observation)
        
        # Combine all results into a unified response
        return {
            "product_id": product_id,
            "details": product_details,
            "similar_products": similar_products.get('similar_products', []),
            "complementary_products": complementary_products.get('complementary_products', []),
            "category_insights": category_insights.get('analysis', ''),
            "report": product_report
        }
    
    def get_category_trend_analysis(self, category: str) -> Dict[str, Any]:
        """Get analysis of trends in a product category.
        
        Args:
            category: Product category to analyze
            
        Returns:
            Dict containing category trend analysis and chart data
        """
        # Get category insights
        category_insights = self.product_agent.get_category_insights(category)
        
        if 'message' in category_insights:
            return category_insights
        
        # Get trending products in this category
        trending_products = self.product_agent.find_trending_products(category)
        
        # Generate trend analysis using LLM
        prompt = f"""
        Analyze trends in the {category} product category based on:
        
        Category Insights:
        {category_insights.get('analysis', '')}
        
        Trending Products:
        {json.dumps(trending_products.get('trending_products', []))}
        
        Trending Analysis:
        {trending_products.get('analysis', '')}
        
        Please provide:
        1. Overall category trends and market dynamics
        2. Customer preferences and behavior trends in this category
        3. Emerging product features or innovations in this category
        4. Recommendations for marketing and merchandising products in this category
        5. Predictions for future trends in this category
        """
        
        trend_analysis = self.llm.generate(prompt, system_prompt=self.system_prompt)
        
        # Generate chart data based on actual insights
        price_trend_data = self._generate_price_trend_data(category_insights)
        popularity_data = self._generate_popularity_data(trending_products)
        
        # Track this as an observation
        observation = f"Generated trend analysis for {category} category"
        self.store_memory("observations", observation)
        
        # Combine all results into a unified response
        return {
            "category": category,
            "insights": category_insights.get('analysis', ''),
            "trending_products": trending_products.get('trending_products', []),
            "trend_analysis": trend_analysis,
            "price_trend_data": price_trend_data,
            "popularity_data": popularity_data
        }
    
    def _generate_price_trend_data(self, category_insights: Dict[str, Any]) -> Dict[str, Any]:
        """Generate price trend chart data based on category insights.
        
        Args:
            category_insights: Category insights from product agent
            
        Returns:
            Dict containing chart data for price trends
        """
        # Use actual stats from category insights to create a realistic trend
        avg_price = category_insights.get('stats', {}).get('avg_price', 100)
        min_price = category_insights.get('stats', {}).get('min_price', 50)
        max_price = category_insights.get('stats', {}).get('max_price', 150)
        
        # Create simulated monthly price trends based on the actual price range
        months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun']
        
        # Start with avg price and vary within bounds of min/max
        import random
        random.seed(avg_price)  # Use avg_price as seed for deterministic results
        
        # Calculate a realistic range for variations (20% of the price range)
        variation_range = (max_price - min_price) * 0.2
        
        # Generate realistic price trend data
        prices = []
        current_price = avg_price
        
        for _ in months:
            # Add a small random variation, keeping within the min/max bounds
            variation = random.uniform(-variation_range, variation_range)
            current_price = max(min_price, min(max_price, current_price + variation))
            prices.append(round(current_price, 2))
        
        return {
            'labels': months,
            'datasets': [{
                'label': 'Avg Price',
                'data': prices,
                'borderColor': 'rgba(75, 192, 192, 1)',
                'backgroundColor': 'rgba(75, 192, 192, 0.2)',
            }]
        }
    
    def _generate_popularity_data(self, trending_products: Dict[str, Any]) -> Dict[str, Any]:
        """Generate popularity chart data based on trending products.
        
        Args:
            trending_products: Trending products data from product agent
            
        Returns:
            Dict containing chart data for product popularity
        """
        # Extract product IDs and ratings from trending products
        products = trending_products.get('trending_products', [])
        
        # If no products, return empty data
        if not products:
            return {'labels': [], 'datasets': [{'label': 'Popularity Score', 'data': []}]}
        
        # Use actual product data to create the chart
        product_ids = []
        popularity_scores = []
        
        for product in products[:5]:  # Limit to 5 products for readability
            product_ids.append(product.get('product_id', ''))
            # Scale product_rating to a 0-100 popularity score
            rating = product.get('product_rating', 0)
            if isinstance(rating, str):
                try:
                    rating = float(rating)
                except ValueError:
                    rating = 0
            
            # Convert rating to a 0-100 popularity score
            popularity_score = round(rating * 20, 1) if rating else 0
            popularity_scores.append(popularity_score)
        
        return {
            'labels': product_ids,
            'datasets': [{
                'label': 'Popularity Score',
                'data': popularity_scores,
                'backgroundColor': 'rgba(54, 162, 235, 0.5)',
                'borderColor': 'rgba(54, 162, 235, 1)',
                'borderWidth': 1
            }]
        }
    
    def get_seasonal_recommendations(self, customer_id: str, season: str) -> Dict[str, Any]:
        """Get seasonal product recommendations for a customer.
        
        Args:
            customer_id: The customer's unique identifier
            season: Current season (e.g., "Summer", "Winter")
            
        Returns:
            Dict containing seasonal recommendations with explanations
        """
        # Get customer profile
        customer_profile = self.customer_agent.get_customer_profile(customer_id)
        
        if 'error' in customer_profile:
            return customer_profile
        
        # Get season-specific recommendations
        seasonal_recommendations = self.recommendation_agent.get_recommendations_by_season(customer_id, season)
        
        # Get category insights for the top recommended product's category
        category_insights = None
        if seasonal_recommendations.get('recommendations', []):
            top_category = seasonal_recommendations['recommendations'][0]['category']
            category_insights = self.product_agent.get_category_insights(top_category)
        
        # Generate seasonal shopping guide using LLM
        prompt = f"""
        Create a {season} season shopping guide for customer {customer_id} based on:
        
        Customer Profile:
        {json.dumps(customer_profile)}
        
        Seasonal Recommendations:
        {json.dumps(seasonal_recommendations.get('recommendations', []))}
        
        Recommendation Explanations:
        {seasonal_recommendations.get('explanations', '')}
        
        {f"Category Insights: {category_insights.get('analysis', '')}" if category_insights else ""}
        
        Please provide:
        1. A personalized {season} shopping guide for this customer
        2. How these products fit into {season} activities and needs
        3. Why these specific products are perfect for this customer in {season}
        4. Any special {season} tips or advice related to these products
        """
        
        seasonal_shopping_guide = self.llm.generate(prompt, system_prompt=self.system_prompt)
        
        # Track this as an observation
        observation = f"Created {season} shopping guide for customer {customer_id}"
        self.store_memory("observations", observation)
        
        # Combine all results into a unified response
        return {
            "customer_id": customer_id,
            "season": season,
            "recommendations": seasonal_recommendations.get('recommendations', []),
            "seasonal_shopping_guide": seasonal_shopping_guide
        } 