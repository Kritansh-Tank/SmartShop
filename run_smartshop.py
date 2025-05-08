#!/usr/bin/env python3
"""
Run script for SmartShop E-commerce Personalized Recommendation System
"""

import os
import sys
import time
import argparse
import subprocess
from pathlib import Path

# Add the smartshop package to the path
current_dir = Path(__file__).resolve().parent
sys.path.append(str(current_dir))

from smartshop.check_ollama import check_ollama_running, is_model_available
from smartshop.config import OLLAMA_BASE_URL, OLLAMA_LLM_MODEL

def check_requirements():
    """Check if all requirements are met to run SmartShop."""
    print("Checking requirements...")
    
    # Check if Ollama is running
    if not check_ollama_running():
        print("\n❌ Ollama is not running!")
        choice = input("Would you like to start Ollama now? (y/n): ")
        if choice.lower() == 'y':
            try:
                if os.name == 'nt':  # Windows
                    subprocess.Popen(["ollama", "serve"], 
                                    creationflags=subprocess.CREATE_NEW_CONSOLE,
                                    shell=True)
                else:  # Linux/Mac
                    subprocess.Popen(["ollama", "serve"], 
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE,
                                    start_new_session=True)
                
                print("Starting Ollama... please wait...")
                # Wait for Ollama to start
                for _ in range(5):
                    time.sleep(1)
                    if check_ollama_running():
                        print("✅ Ollama started successfully!")
                        break
                else:
                    print("⚠️ Could not verify that Ollama started. Continuing anyway...")
            except Exception as e:
                print(f"Error starting Ollama: {e}")
                print("Please start Ollama manually with 'ollama serve' in a separate terminal.")
                return False
        else:
            print("Please start Ollama with 'ollama serve' in a separate terminal.")
            return False
    else:
        print("✅ Ollama is running")
    
    # Check if the model is available
    if not is_model_available(OLLAMA_LLM_MODEL):
        print(f"\n❌ Required model '{OLLAMA_LLM_MODEL}' is not available!")
        choice = input(f"Would you like to pull the '{OLLAMA_LLM_MODEL}' model now? (y/n): ")
        if choice.lower() == 'y':
            print(f"Pulling model '{OLLAMA_LLM_MODEL}'... This may take some time.")
            try:
                if os.name == 'nt':  # Windows
                    result = subprocess.run(["ollama", "pull", OLLAMA_LLM_MODEL], 
                                           capture_output=True, text=True)
                    if result.returncode == 0:
                        print(f"✅ Successfully pulled model '{OLLAMA_LLM_MODEL}'.")
                    else:
                        print(f"❌ Failed to pull model: {result.stderr}")
                        return False
                else:  # Linux/Mac
                    result = os.system(f"ollama pull {OLLAMA_LLM_MODEL}")
                    if result == 0:
                        print(f"✅ Successfully pulled model '{OLLAMA_LLM_MODEL}'.")
                    else:
                        print(f"❌ Failed to pull model. Exit code: {result}")
                        return False
            except Exception as e:
                print(f"Error pulling model: {e}")
                return False
        else:
            print(f"Please pull the model manually with 'ollama pull {OLLAMA_LLM_MODEL}'.")
            return False
    else:
        print(f"✅ Model '{OLLAMA_LLM_MODEL}' is available")
    
    return True

def run_webapp():
    """Run the SmartShop web application."""
    try:
        # Import here to avoid importing before checks
        from smartshop.web_app import app
        
        print("\nStarting SmartShop web application...")
        port = int(os.environ.get('PORT', 5000))
        app.run(host='0.0.0.0', port=port, debug=True)
    except Exception as e:
        print(f"Error starting web application: {e}")
        return False
    
    return True

def run_test():
    """Run the Ollama connection test."""
    try:
        # Import and run the test script
        from test_ollama_connection import test_ollama_connection
        test_ollama_connection()
    except Exception as e:
        print(f"Error running test: {e}")
        return False
    
    return True

def main():
    """Main entry point for the run script."""
    parser = argparse.ArgumentParser(description='Run SmartShop E-commerce Recommendation System')
    parser.add_argument('--skip-checks', action='store_true', help='Skip requirement checks')
    parser.add_argument('--test', action='store_true', help='Run Ollama connection test only')
    
    args = parser.parse_args()
    
    print("=" * 80)
    print(" SmartShop E-commerce Personalized Recommendation System")
    print("=" * 80)
    
    if args.test:
        print("\nRunning Ollama connection test...")
        run_test()
        return
    
    if not args.skip_checks:
        if not check_requirements():
            print("\n❌ Requirements check failed. Please fix the issues and try again.")
            return
    
    # If we get here, all requirements are met (or checks were skipped)
    success = run_webapp()
    
    if not success:
        print("\n❌ Failed to run SmartShop. Please check the error messages above.")

if __name__ == "__main__":
    main()