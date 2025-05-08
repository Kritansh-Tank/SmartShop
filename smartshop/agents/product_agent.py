"""
Product Agent for managing product information and relationships
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

class ProductAgent(Agent):
    """Agent specializing in product information and relationships between products."""
    
    def __init__(self):
        """Initialize the Product Agent."""
        super().__init__(
            agent_id="product_agent",
            name=AGENTS["product_agent"]["name"],
            description=AGENTS["product_agent"]["description"]
        )
        self.db = Database()
        
        # Register tools
        self.register_tool(
            "get_product_details",
            self.get_product_details,
            "Get detailed information about a product by ID"
        )
        self.register_tool(
            "find_similar_products",
            self.find_similar_products,
            "Find products similar to a given product"
        )
        self.register_tool(
            "find_complementary_products",
            self.find_complementary_products,
            "Find products that complement a given product"
        )
        self.register_tool(
            "get_category_insights",
            self.get_category_insights,
            "Get insights about a product category"
        )
        self.register_tool(
            "find_trending_products",
            self.find_trending_products,
            "Find trending products in a category or overall"
        )
    
    def get_product_details(self, product_id: str) -> Dict[str, Any]:
        """Get detailed information about a product.
        
        Args:
            product_id: The product's unique identifier
        
        Returns:
            Dict containing product details
        """
        product = self.db.get_product(product_id)
        
        if not product:
            return {"error": f"Product {product_id} not found"}
        
        # Remove potentially unnecessary information
        if 'created_at' in product:
            del product['created_at']
        if 'updated_at' in product:
            del product['updated_at']
        
        # Track this observation
        observation = f"Retrieved details for product {product_id}: {json.dumps(product)}"
        self.store_memory("observations", observation)
        
        return product
    
    def find_similar_products(self, product_id: str, limit: int = 5) -> Dict[str, Any]:
        """Find products similar to the given product.
        
        Args:
            product_id: The product's unique identifier
            limit: Maximum number of similar products to return
        
        Returns:
            Dict containing similar products with similarity scores
        """
        # Get the target product
        product = self.db.get_product(product_id)
        
        if not product:
            return {"error": f"Product {product_id} not found"}
        
        # Query for similar products
        query = """
        SELECT p.product_id, p.category, p.subcategory, p.price, p.brand, 
               p.product_rating, 
               ABS(p.price - ?) / 5000.0 + 
               ABS(p.product_rating - ?) / 5.0 AS similarity_score
        FROM products p
        WHERE p.product_id != ? 
          AND p.category = ?
        ORDER BY similarity_score ASC
        LIMIT ?
        """
        
        params = (
            product['price'],
            product['product_rating'],
            product_id,
            product['category'],
            limit
        )
        
        # Use direct database access instead of pandas
        self.db.connect()
        result = self.db.fetch_all(query, params)
        similar_products = []
        
        if result:
            columns = ["product_id", "category", "subcategory", "price", "brand", "product_rating", "similarity_score"]
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
                similar_products.append(product_dict)
        
        if not similar_products:
            return {"message": f"No similar products found for {product_id}"}
        
        # Use LLM to analyze similarity
        prompt = f"""
        Analyze the similarity between product {product_id} with the following details:
        {json.dumps(product)}
        
        And these similar products:
        {json.dumps(similar_products)}
        
        For each similar product, provide a brief explanation of why it's similar and 
        what features or attributes are shared between them.
        """
        
        analysis = self.llm.generate(prompt, system_prompt=self.system_prompt)
        
        # Track this as an observation
        observation = f"Found {len(similar_products)} similar products for {product_id}"
        self.store_memory("observations", observation)
        
        return {
            "product_id": product_id,
            "similar_products": similar_products,
            "analysis": analysis
        }
    
    def find_complementary_products(self, product_id: str, limit: int = 5) -> Dict[str, Any]:
        """Find products that complement the given product.
        
        Args:
            product_id: The product's unique identifier
            limit: Maximum number of complementary products to return
        
        Returns:
            Dict containing complementary products with explanations
        """
        # Get the target product
        product = self.db.get_product(product_id)
        
        if not product:
            return {"error": f"Product {product_id} not found"}
        
        # Query for complementary products (products in different categories)
        query = """
        SELECT p.product_id, p.category, p.subcategory, p.price, p.brand, p.product_rating
        FROM products p
        WHERE p.product_id != ? 
          AND p.category != ?
        ORDER BY p.product_rating DESC
        LIMIT ?
        """
        
        params = (product_id, product['category'], limit)
        
        # Use direct database access instead of pandas
        self.db.connect()
        result = self.db.fetch_all(query, params)
        complementary_products = []
        
        if result:
            columns = ["product_id", "category", "subcategory", "price", "brand", "product_rating"]
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
                complementary_products.append(product_dict)
        
        if not complementary_products:
            return {"message": f"No complementary products found for {product_id}"}
        
        # Use LLM to analyze complementary relationships
        prompt = f"""
        Analyze how the following products might complement product {product_id} with these details:
        {json.dumps(product)}
        
        Potential complementary products:
        {json.dumps(complementary_products)}
        
        For each product, provide a brief explanation of why it complements the original product,
        how they might be used together, and what type of customer might be interested in both.
        """
        
        analysis = self.llm.generate(prompt, system_prompt=self.system_prompt)
        
        # Track this as an observation
        observation = f"Found {len(complementary_products)} complementary products for {product_id}"
        self.store_memory("observations", observation)
        
        return {
            "product_id": product_id,
            "complementary_products": complementary_products,
            "analysis": analysis
        }
    
    def get_category_insights(self, category: str) -> Dict[str, Any]:
        """Get insights about a product category.
        
        Args:
            category: Product category to analyze
        
        Returns:
            Dict containing category insights and analysis
        """
        # Query for products in this category
        count_query = """
        SELECT COUNT(*) as product_count,
               AVG(price) as avg_price,
               MIN(price) as min_price,
               MAX(price) as max_price,
               AVG(product_rating) as avg_rating
        FROM products
        WHERE category = ?
        """
        
        self.db.connect()
        stats_result = self.db.fetch_one(count_query, (category,))
        
        if not stats_result or stats_result[0] == 0:
            return {"message": f"No products found in category {category}"}
        
        # Create stats dictionary
        stats = {
            "product_count": stats_result[0],
            "avg_price": stats_result[1],
            "min_price": stats_result[2],
            "max_price": stats_result[3],
            "avg_rating": stats_result[4]
        }
        
        # Get unique subcategories
        subcat_query = """
        SELECT DISTINCT subcategory
        FROM products
        WHERE category = ?
        """
        
        subcat_results = self.db.fetch_all(subcat_query, (category,))
        subcategories = [row[0] for row in subcat_results] if subcat_results else []
        
        # Get top rated products
        top_products_query = """
        SELECT product_id, subcategory, price, brand, product_rating
        FROM products
        WHERE category = ?
        ORDER BY product_rating DESC
        LIMIT 5
        """
        
        top_result = self.db.fetch_all(top_products_query, (category,))
        top_products = []
        
        if top_result:
            columns = ["product_id", "subcategory", "price", "brand", "product_rating"]
            for row in top_result:
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
                top_products.append(product_dict)
        
        # Use LLM to generate insights
        prompt = f"""
        Generate insights and analysis for the product category: {category}
        
        Category Statistics:
        - Number of Products: {stats['product_count']}
        - Average Price: ${stats['avg_price']:.2f}
        - Price Range: ${stats['min_price']:.2f} - ${stats['max_price']:.2f}
        - Average Rating: {stats['avg_rating']:.1f}/5.0
        
        Subcategories: {subcategories}
        
        Top Rated Products:
        {json.dumps(top_products)}
        
        Please provide:
        1. Overall analysis of this product category
        2. Price point analysis and what it indicates about the market
        3. Insights about the subcategories and their significance
        4. Customer preferences based on top-rated products
        5. Recommendations for shoppers interested in this category
        """
        
        analysis = self.llm.generate(prompt, system_prompt=self.system_prompt)
        
        # Track this as an observation
        observation = f"Generated insights for category {category} with {stats['product_count']} products"
        self.store_memory("observations", observation)
        
        return {
            "category": category,
            "stats": stats,
            "subcategories": subcategories,
            "top_products": top_products,
            "analysis": analysis
        }
    
    def find_trending_products(self, category: Optional[str] = None, limit: int = 5) -> Dict[str, Any]:
        """Find trending products in a category or overall.
        
        Args:
            category: Optional product category to filter by
            limit: Maximum number of trending products to return
        
        Returns:
            Dict containing trending products with analysis
        """
        # Construct query based on category filter
        if category:
            query = """
            SELECT product_id, category, subcategory, price, brand, product_rating
            FROM products
            WHERE category = ?
            ORDER BY product_rating DESC, created_at DESC
            LIMIT ?
            """
            params = (category, limit)
        else:
            query = """
            SELECT product_id, category, subcategory, price, brand, product_rating
            FROM products
            ORDER BY product_rating DESC, created_at DESC
            LIMIT ?
            """
            params = (limit,)
        
        # Use direct database access instead of pandas
        self.db.connect()
        result = self.db.fetch_all(query, params)
        trending_products = []
        
        if result:
            columns = ["product_id", "category", "subcategory", "price", "brand", "product_rating"]
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
                trending_products.append(product_dict)
        
        if not trending_products:
            if category:
                return {"message": f"No trending products found in category {category}"}
            else:
                return {"message": "No trending products found"}
        
        # Use LLM to analyze trends
        prompt = f"""
        Analyze the following trending products {f"in the {category} category" if category else "across all categories"}:
        
        {json.dumps(trending_products)}
        
        Please provide:
        1. A summary of the trending products and what they indicate about current consumer preferences
        2. Common characteristics among these trending products
        3. Why these products might be popular (features, price points, etc.)
        4. Insights for merchants or shoppers based on these trends
        """
        
        analysis = self.llm.generate(prompt, system_prompt=self.system_prompt)
        
        # Track this as an observation
        observation = f"Found {len(trending_products)} trending products {f'in category {category}' if category else 'overall'}"
        self.store_memory("observations", observation)
        
        return {
            "category": category,
            "trending_products": trending_products,
            "analysis": analysis
        }
    
    def generate_product_insight_report(self, product_id: str) -> str:
        """Generate a comprehensive insight report for a product.
        
        Args:
            product_id: The product's unique identifier
        
        Returns:
            String containing a comprehensive report about the product
        """
        # Get product details
        product = self.db.get_product(product_id)
        
        if not product:
            return f"Product {product_id} not found"
        
        # Get similar and complementary products
        similar_products = self.find_similar_products(product_id)
        complementary_products = self.find_complementary_products(product_id)
        
        # Get category insights
        category_insights = self.get_category_insights(product['category'])
        
        # Generate the report using LLM
        prompt = f"""
        Generate a comprehensive product insight report based on the following information:
        
        Product Details:
        {json.dumps(product)}
        
        Similar Products Analysis:
        {similar_products.get('analysis', 'No similar products analysis available')}
        
        Complementary Products Analysis:
        {complementary_products.get('analysis', 'No complementary products analysis available')}
        
        Category Insights:
        {category_insights.get('analysis', 'No category insights available')}
        
        Please provide a well-structured report that includes:
        1. Product overview and positioning
        2. Competitive landscape and similar products
        3. Cross-selling opportunities with complementary products
        4. Category context and where this product fits in
        5. Strategic recommendations for marketing and promoting this product
        """
        
        report = self.llm.generate(prompt, system_prompt=self.system_prompt)
        
        # Store the report in memory
        self.store_memory("reflections", report, f"product_report_{product_id}")
        
        return report 