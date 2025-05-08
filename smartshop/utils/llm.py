"""
LLM utility module for interacting with Ollama
"""

import requests
import json
import numpy as np
import sys
import time
from pathlib import Path

# Add the parent directory to the system path to import from config
sys.path.append(str(Path(__file__).parent.parent.parent))
from smartshop.config import OLLAMA_BASE_URL, OLLAMA_LLM_MODEL, EMBEDDING_DIMENSION

class OllamaClient:
    """Client for interacting with Ollama LLM API."""
    
    def __init__(self, base_url=OLLAMA_BASE_URL, model=OLLAMA_LLM_MODEL, max_retries=3, retry_delay=2):
        """Initialize the Ollama client.
        
        Args:
            base_url: Ollama API base URL
            model: Model name to use
            max_retries: Maximum number of retry attempts
            retry_delay: Delay in seconds between retries
        """
        self.base_url = base_url
        self.model = model
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.generate_endpoint = f"{base_url}/api/generate"
        self.embeddings_endpoint = f"{base_url}/api/embeddings"
        self.chat_endpoint = f"{base_url}/api/chat"
        self.list_endpoint = f"{base_url}/api/tags"
        
        # Validate connection and model availability
        self._validate_connection()
    
    def _validate_connection(self):
        """Validate connection to Ollama and verify model availability."""
        try:
            # Check connection to Ollama server
            response = requests.get(self.base_url)
            response.raise_for_status()
            
            # Check if the model is available
            list_response = requests.get(self.list_endpoint)
            list_response.raise_for_status()
            models = list_response.json().get("models", [])
            available_models = [model.get("name") for model in models]
            
            if not models:
                print(f"Warning: No models found in Ollama instance at {self.base_url}")
            elif self.model not in available_models:
                base_model_name = self.model.split(':')[0] if ':' in self.model else self.model
                if any(base_model_name in model for model in available_models):
                    closest_model = next((model for model in available_models if base_model_name in model), None)
                    print(f"Warning: Model '{self.model}' not found, but similar model '{closest_model}' is available.")
                    print(f"You may need to run: 'ollama pull {self.model}'")
                else:
                    print(f"Warning: Model '{self.model}' not found in Ollama. Available models: {available_models}")
                    print(f"You may need to run: 'ollama pull {self.model}'")
        except requests.exceptions.RequestException as e:
            print(f"Warning: Could not connect to Ollama at {self.base_url}: {e}")
            print("Make sure Ollama is running locally with: 'ollama serve'")
            print(f"The model '{self.model}' should be available. To pull it: 'ollama pull {self.model}'")
    
    def _execute_with_retry(self, request_func):
        """Execute a request with retry logic.
        
        Args:
            request_func: Function to execute that makes the request
            
        Returns:
            Result of the request or empty result on failure
        """
        retries = 0
        while retries < self.max_retries:
            try:
                return request_func()
            except requests.exceptions.RequestException as e:
                retries += 1
                if retries < self.max_retries:
                    print(f"Request failed: {e}. Retrying in {self.retry_delay} seconds... (Attempt {retries}/{self.max_retries})")
                    time.sleep(self.retry_delay)
                else:
                    print(f"Request failed after {self.max_retries} attempts: {e}")
                    return None
    
    def generate(self, prompt, system_prompt=None, max_tokens=1024, temperature=0.7):
        """Generate text from a prompt."""
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "max_tokens": max_tokens,
            "temperature": temperature
        }
        
        if system_prompt:
            payload["system"] = system_prompt
        
        def request_func():
            response = requests.post(self.generate_endpoint, json=payload)
            response.raise_for_status()
            result = response.json()
            return result.get("response", "")
        
        result = self._execute_with_retry(request_func)
        return result if result is not None else "[Error: Could not generate response. Make sure Ollama is running with the correct model.]"
    
    def get_embedding(self, text):
        """Get embedding vector for a text."""
        payload = {
            "model": self.model,
            "prompt": text
        }
        
        def request_func():
            response = requests.post(self.embeddings_endpoint, json=payload)
            response.raise_for_status()
            result = response.json()
            return result.get("embedding", [0] * EMBEDDING_DIMENSION)
        
        result = self._execute_with_retry(request_func)
        return result if result is not None else [0] * EMBEDDING_DIMENSION
    
    def chat(self, messages, system_prompt=None, temperature=0.7):
        """Chat with the LLM using a message format."""
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "temperature": temperature
        }
        
        if system_prompt:
            payload["system"] = system_prompt
        
        def request_func():
            response = requests.post(self.chat_endpoint, json=payload)
            response.raise_for_status()
            result = response.json()
            return result.get("message", {}).get("content", "")
        
        result = self._execute_with_retry(request_func)
        return result if result is not None else "[Error: Could not generate chat response. Make sure Ollama is running with the correct model.]"
    
    def similarity(self, embedding1, embedding2):
        """Calculate cosine similarity between two embeddings."""
        if not embedding1 or not embedding2:
            return 0.0
        
        # Convert to numpy arrays
        vec1 = np.array(embedding1)
        vec2 = np.array(embedding2)
        
        # Compute cosine similarity
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot_product / (norm1 * norm2)


# Test the Ollama client when run directly
if __name__ == "__main__":
    client = OllamaClient()
    print("Testing connection to local Ollama instance...")
    
    # Test text generation
    print("Testing text generation...")
    response = client.generate("What is the best way to recommend products to e-commerce customers?")
    print(f"LLM Response: {response}\n")
    
    # Test embeddings
    print("Testing embeddings...")
    text = "Personalized product recommendations for e-commerce"
    embedding = client.get_embedding(text)
    print(f"Embedding shape: {len(embedding)}")
    print(f"First 5 dimensions: {embedding[:5]}\n")
    
    # Test chat
    print("Testing chat...")
    messages = [
        {"role": "user", "content": "How can AI improve e-commerce recommendations?"}
    ]
    chat_response = client.chat(messages)
    print(f"Chat Response: {chat_response}")
    
    print("\nAll tests completed. If you see any error messages above, please check your Ollama setup.") 