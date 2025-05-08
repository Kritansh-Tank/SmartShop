"""
Script to check if the required Ollama model is available and pull it if needed
"""

import os
import sys
import requests
import time
import subprocess
from pathlib import Path

# Add the parent directory to the system path
sys.path.append(str(Path(__file__).parent.parent))
from smartshop.config import OLLAMA_BASE_URL, OLLAMA_LLM_MODEL

def check_ollama_running():
    """Check if Ollama is running locally."""
    try:
        response = requests.get(OLLAMA_BASE_URL)
        return response.status_code == 200
    except requests.exceptions.RequestException:
        return False

def get_available_models():
    """Get list of available models in Ollama."""
    try:
        response = requests.get(f"{OLLAMA_BASE_URL}/api/tags")
        if response.status_code == 200:
            return response.json().get("models", [])
        return []
    except requests.exceptions.RequestException:
        return []

def is_model_available(model_name):
    """Check if specified model is available."""
    models = get_available_models()
    available_models = [model.get("name") for model in models]
    return model_name in available_models

def pull_model(model_name):
    """Pull the specified model using Ollama."""
    print(f"Pulling model '{model_name}'... This may take some time.")
    try:
        if os.name == 'nt':  # Windows
            # For Windows, we use subprocess to run the command
            result = subprocess.run(["ollama", "pull", model_name], capture_output=True, text=True)
            if result.returncode == 0:
                print(f"Successfully pulled model '{model_name}'.")
                return True
            else:
                print(f"Failed to pull model: {result.stderr}")
                return False
        else:  # Linux/Mac
            # For Unix systems, we can use os.system
            result = os.system(f"ollama pull {model_name}")
            if result == 0:
                print(f"Successfully pulled model '{model_name}'.")
                return True
            else:
                print(f"Failed to pull model. Exit code: {result}")
                return False
    except Exception as e:
        print(f"Error pulling model: {e}")
        return False

def start_ollama():
    """Attempt to start Ollama if it's not running."""
    try:
        if os.name == 'nt':  # Windows
            print("Attempting to start Ollama...")
            subprocess.Popen(["ollama", "serve"], 
                             creationflags=subprocess.CREATE_NEW_CONSOLE,
                             shell=True)
        else:  # Linux/Mac
            print("Attempting to start Ollama...")
            os.system("ollama serve &")
            
        # Wait a bit for Ollama to start
        print("Waiting for Ollama to start...")
        for _ in range(5):  # Try for 5 seconds
            time.sleep(1)
            if check_ollama_running():
                print("Ollama started successfully.")
                return True
                
        print("Could not verify that Ollama started.")
        return False
    except Exception as e:
        print(f"Error starting Ollama: {e}")
        return False

def main():
    """Main function to check and setup Ollama with the required model."""
    print(f"Checking Ollama setup for model: {OLLAMA_LLM_MODEL}")
    
    # First, check if Ollama is running
    if not check_ollama_running():
        print("Ollama is not running.")
        if not start_ollama():
            print("Could not start Ollama. Please start it manually with 'ollama serve'")
            print("Then run this script again.")
            return False
    
    # Now check if the model is available
    if not is_model_available(OLLAMA_LLM_MODEL):
        print(f"Model '{OLLAMA_LLM_MODEL}' is not available locally.")
        if not pull_model(OLLAMA_LLM_MODEL):
            print(f"Failed to pull model '{OLLAMA_LLM_MODEL}'.")
            print(f"Please manually run: ollama pull {OLLAMA_LLM_MODEL}")
            return False
    else:
        print(f"Model '{OLLAMA_LLM_MODEL}' is already available locally.")
    
    print("Ollama setup is complete and ready to use with SmartShop!")
    return True

if __name__ == "__main__":
    success = main()
    if success:
        # Test the model
        print("\nTesting model with a simple prompt...")
        try:
            response = requests.post(
                f"{OLLAMA_BASE_URL}/api/generate",
                json={"model": OLLAMA_LLM_MODEL, "prompt": "Hello, how are you?", "stream": False}
            )
            if response.status_code == 200:
                result = response.json()
                print(f"Response: {result.get('response', 'No response')[:100]}...")
                print("\nModel test successful! The system is ready to use.")
            else:
                print(f"Error testing model: Status code {response.status_code}")
        except Exception as e:
            print(f"Error testing model: {e}")
    
    sys.exit(0 if success else 1) 
