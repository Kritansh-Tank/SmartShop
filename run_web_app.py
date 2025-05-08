"""
Run Script for SmartShop Web Application
"""

from smartshop.web_app import app

if __name__ == "__main__":
    # Run the application with debugging enabled
    app.run(host='0.0.0.0', port=5000, debug=True) 