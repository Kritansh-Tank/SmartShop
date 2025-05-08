"""
Configuration file for Smart Shop - E-commerce Personalized Recommendation System
"""

import os
from pathlib import Path

# Project structure
BASE_DIR = Path(__file__).parent.resolve()
DATA_DIR = BASE_DIR / "data"
MODELS_DIR = BASE_DIR / "models"
AGENTS_DIR = BASE_DIR / "agents"
UTILS_DIR = BASE_DIR / "utils"

# Database settings
DB_PATH = BASE_DIR / "data" / "smartshop.db"

# LLM settings
OLLAMA_BASE_URL = "http://localhost:11434"  # Local Ollama endpoint
OLLAMA_LLM_MODEL = "qwen2.5:0.5b"

# Agent settings
AGENTS = {
    "customer_agent": {
        "name": "Customer Agent",
        "description": "Analyzes customer behavior and preferences"
    },
    "product_agent": {
        "name": "Product Agent",
        "description": "Manages product information and relationships"
    },
    "recommendation_agent": {
        "name": "Recommendation Agent",
        "description": "Generates personalized product recommendations"
    },
    "coordination_agent": {
        "name": "Coordination Agent",
        "description": "Orchestrates the interaction between other agents"
    }
}

# Dataset paths (relative to project root)
CUSTOMER_DATA_PATH = Path("./Dataset/[Usecase 2] Personalized Recommendations for E-Commerce/customer_data_collection.csv")
PRODUCT_DATA_PATH = Path("./Dataset/[Usecase 2] Personalized Recommendations for E-Commerce/product_recommendation_data.csv")

# System settings
EMBEDDING_MODEL = "qwen2.5:0.5b"  # Model to use for embeddings
EMBEDDING_DIMENSION = 384  # Dimension of embedding vectors
SIMILARITY_THRESHOLD = 0.75  # Threshold for similarity matching

# Recommendation settings
TOP_N_RECOMMENDATIONS = 5  # Number of top recommendations to provide
MIN_RECOMMENDATION_SCORE = 0.3  # Minimum score for recommendations

# Create necessary directories
def create_directories():
    """Create the necessary directories if they don't exist."""
    for directory in [DATA_DIR, MODELS_DIR, AGENTS_DIR, UTILS_DIR]:
        directory.mkdir(exist_ok=True)

# Initialize the project structure
create_directories() 