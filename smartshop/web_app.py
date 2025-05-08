"""
Web UI for SmartShop E-commerce Personalized Recommendation System
"""

import os
import sys
import json
from pathlib import Path
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session, g
import pandas as pd
import re

# Add the parent directory to the system path
sys.path.append(str(Path(__file__).parent.parent))
from smartshop.agents.coordination_agent import CoordinationAgent
from smartshop.utils.database import Database, init_db
from smartshop.config import AGENTS, OLLAMA_BASE_URL, OLLAMA_LLM_MODEL
from smartshop.check_ollama import check_ollama_running, is_model_available

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'smartshop-secret-key-for-development')

# Add custom filters for templates
@app.template_filter('nl2br')
def nl2br(value):
    """Convert newlines to <br> tags for display in HTML."""
    if value:
        return value.replace('\n', '<br>')
    return value

# Check Ollama status at startup
OLLAMA_STATUS = {
    "running": check_ollama_running(),
    "model_available": False
}

if OLLAMA_STATUS["running"]:
    OLLAMA_STATUS["model_available"] = is_model_available(OLLAMA_LLM_MODEL)
    if not OLLAMA_STATUS["model_available"]:
        app.logger.warning(f"Ollama is running but model '{OLLAMA_LLM_MODEL}' is not available.")
        app.logger.warning(f"Please run: python -m smartshop.check_ollama")
else:
    app.logger.warning(f"Ollama is not running at {OLLAMA_BASE_URL}.")
    app.logger.warning("Please start Ollama with 'ollama serve' before using SmartShop.")
    app.logger.warning("Then run: python -m smartshop.check_ollama")

def get_db():
    """Get a database connection for the current request."""
    if 'db' not in g:
        g.db = Database()
    return g.db

def get_agent():
    """Get or initialize the coordination agent singleton."""
    if 'agent' not in g:
        g.agent = CoordinationAgent()
    return g.agent

def get_system_status():
    """Get the current system status."""
    db = get_db()
    database_exists = db.check_connection()
    
    # Check Ollama status again (in case it was started after app initialization)
    ollama_running = check_ollama_running()
    model_available = False
    if ollama_running:
        model_available = is_model_available(OLLAMA_LLM_MODEL)
    
    # Default values
    system_status = {
        "database_exists": database_exists,
        "config_loaded": True,  # Assume config is always loaded
        "agents_ready": ollama_running and model_available,  # Agents need Ollama with the correct model
        "has_data": False,
        "customer_count": 0,
        "product_count": 0,
        "is_ready": database_exists and ollama_running and model_available,
        "ollama_running": ollama_running,
        "model_available": model_available
    }
    
    # If database exists, try to get counts
    if database_exists:
        try:
            # First check if tables exist
            tables_exist = db.table_exists("customers") and db.table_exists("products")
            system_status["tables_exist"] = tables_exist
            
            if tables_exist:
                # Use direct database queries instead of pandas
                db.connect()
                
                customer_query = "SELECT COUNT(*) as count FROM customers"
                customer_result = db.fetch_one(customer_query)
                
                product_query = "SELECT COUNT(*) as count FROM products"
                product_result = db.fetch_one(product_query)
                
                if customer_result and product_result:
                    customer_count = customer_result[0]
                    product_count = product_result[0]
                    
                    system_status["customer_count"] = int(customer_count)
                    system_status["product_count"] = int(product_count)
                    system_status["has_data"] = (int(customer_count) > 0 or int(product_count) > 0)
                    
                    # Add debug info
                    app.logger.info(f"get_system_status: customer_count={customer_count}, product_count={product_count}, has_data={system_status['has_data']}")
        except Exception as e:
            # Tables might not exist yet
            app.logger.error(f"Error in get_system_status: {str(e)}")
            system_status["error"] = str(e)
    
    return system_status

@app.route('/')
def home():
    """Home page with system overview."""
    system_status = get_system_status()
    
    # Check if Ollama is not ready and show a warning
    if not system_status["ollama_running"]:
        flash("Ollama is not running. Please start it with 'ollama serve'", "warning")
    elif not system_status["model_available"]:
        flash(f"Model '{OLLAMA_LLM_MODEL}' is not available. Run 'python -m smartshop.check_ollama' to set it up.", "warning")
    
    return render_template('index.html', agents=AGENTS, system_status=system_status)

@app.route('/initialize', methods=['GET', 'POST'])
def initialize():
    """Initialize the system and database."""
    if request.method == 'POST':
        try:
            # Check Ollama status first
            system_status = get_system_status()
            if not system_status["ollama_running"]:
                flash("Ollama is not running. Please start it with 'ollama serve' before initializing.", "error")
                return redirect(url_for('initialize'))
            elif not system_status["model_available"]:
                flash(f"Model '{OLLAMA_LLM_MODEL}' is not available. Run 'python -m smartshop.check_ollama' to set it up.", "error")
                return redirect(url_for('initialize'))
            
            # Use a new database connection for initialization
            init_db()
            flash('System initialized successfully!', 'success')
        except Exception as e:
            flash(f'Error initializing system: {e}', 'error')
        return redirect(url_for('home'))
    
    system_status = get_system_status()
    return render_template('initialize.html', system_status=system_status)

@app.route('/check_ollama')
def check_ollama():
    """Page to check Ollama status and provide instructions."""
    system_status = get_system_status()
    return render_template('check_ollama.html', system_status=system_status, ollama_url=OLLAMA_BASE_URL, model=OLLAMA_LLM_MODEL)

@app.route('/load_data', methods=['GET', 'POST'])
def load_data():
    """Load data into the system."""
    if request.method == 'POST':
        try:
            # Check Ollama status first
            system_status = get_system_status()
            if not system_status["ollama_running"] or not system_status["model_available"]:
                flash("Ollama is not properly set up. Please check the Ollama status page.", "error")
                return redirect(url_for('check_ollama'))
            
            option = request.form.get('load_option', 'sample')
            
            if option == 'sample':
                # Import here to avoid circular imports
                from smartshop.data_loader import create_sample_data
                create_sample_data()
                flash('Sample data loaded successfully!', 'success')
            else:
                # Import here to avoid circular imports
                from smartshop.data_loader import load_all_data
                load_all_data()
                flash('Data loaded from CSV files successfully!', 'success')
        except Exception as e:
            flash(f'Error loading data: {e}', 'error')
        return redirect(url_for('home'))
    
    system_status = get_system_status()
    return render_template('load_data.html', system_status=system_status)

@app.route('/customers')
def list_customers():
    """List all customers in the database."""
    try:
        query = """
        SELECT customer_id, age, gender, location, customer_segment, avg_order_value
        FROM customers
        ORDER BY customer_id
        """
        # Connect directly to the database to avoid pandas encoding issues
        db = get_db()
        db.connect()
        customers = []
        
        result = db.fetch_all(query)
        if result:
            # Manually convert to dictionaries to avoid encoding issues
            columns = ["customer_id", "age", "gender", "location", "customer_segment", "avg_order_value"]
            for row in result:
                customer_dict = {}
                for i, col in enumerate(columns):
                    # Safely handle potentially binary data
                    if isinstance(row[i], bytes):
                        try:
                            # First try UTF-8
                            customer_dict[col] = row[i].decode('utf-8')
                        except UnicodeDecodeError:
                            try:
                                # Try with 'latin-1' which can decode any byte value
                                customer_dict[col] = row[i].decode('latin-1')
                            except Exception:
                                try:
                                    # Try with 'ascii' and ignore errors
                                    customer_dict[col] = row[i].decode('ascii', errors='ignore')
                                except Exception:
                                    # Last resort: represent as hex
                                    customer_dict[col] = f"[Binary: {row[i].hex()[:10]}...]"
                    else:
                        customer_dict[col] = row[i]
                customers.append(customer_dict)
        
        return render_template('customers.html', customers=customers)
    except Exception as e:
        flash(f'Error fetching customers: {e}', 'error')
        return redirect(url_for('home'))

@app.route('/products')
def list_products():
    """List all products in the database."""
    try:
        query = """
        SELECT product_id, category, subcategory, price, brand, product_rating
        FROM products
        ORDER BY category, subcategory
        """
        # Connect directly to the database to avoid pandas encoding issues
        db = get_db()
        db.connect()
        products = []
        
        result = db.fetch_all(query)
        if result:
            # Manually convert to dictionaries to avoid encoding issues
            columns = ["product_id", "category", "subcategory", "price", "brand", "product_rating"]
            for row in result:
                product_dict = {}
                for i, col in enumerate(columns):
                    # Safely handle potentially binary data
                    if isinstance(row[i], bytes):
                        try:
                            # First try UTF-8
                            product_dict[col] = row[i].decode('utf-8')
                        except UnicodeDecodeError:
                            try:
                                # Try with 'latin-1' which can decode any byte value
                                product_dict[col] = row[i].decode('latin-1')
                            except Exception:
                                try:
                                    # Try with 'ascii' and ignore errors
                                    product_dict[col] = row[i].decode('ascii', errors='ignore')
                                except Exception:
                                    # Last resort: represent as hex
                                    product_dict[col] = f"[Binary: {row[i].hex()[:10]}...]"
                    else:
                        product_dict[col] = row[i]
                products.append(product_dict)
        
        return render_template('products.html', products=products)
    except Exception as e:
        flash(f'Error fetching products: {e}', 'error')
        return redirect(url_for('home'))

@app.route('/recommendations', methods=['GET', 'POST'])
def recommendations():
    """Get personalized recommendations for a customer."""
    if request.method == 'POST':
        customer_id = request.form.get('customer_id')
        context_type = request.form.get('context_type', 'none')
        context_value = request.form.get('context_value', '')
        
        agent = get_agent()
        context = {}
        
        if context_type != 'none' and context_value:
            context[context_type] = context_value
        
        try:
            result = agent.get_personalized_recommendations(customer_id, context)
            return render_template('recommendation_results.html', results=result)
        except Exception as e:
            flash(f'Error generating recommendations: {e}', 'error')
            return redirect(url_for('recommendations'))
    
    # For GET request, show the form
    system_status = get_system_status()
    
    # Check if the system is ready to generate recommendations
    if not system_status['database_exists']:
        flash('Please initialize the system before using recommendations.', 'warning')
    elif not system_status['has_data']:
        flash('Please load data before using recommendations.', 'warning')
    
    return render_template('recommendations.html', system_status=system_status)

@app.route('/customer-analysis', methods=['GET', 'POST'])
def customer_analysis():
    """Analyze a customer's profile and behavior."""
    if request.method == 'POST':
        customer_id = request.form.get('customer_id')
        agent = get_agent()
        
        try:
            result = agent.get_customer_profile_analysis(customer_id)
            return render_template('customer_analysis_results.html', results=result)
        except Exception as e:
            flash(f'Error analyzing customer: {e}', 'error')
            return redirect(url_for('customer_analysis'))
    
    # For GET request, show the form
    system_status = get_system_status()
    
    # Check if the system is ready for analysis
    if not system_status['database_exists']:
        flash('Please initialize the system before using customer analysis.', 'warning')
    elif not system_status['has_data']:
        flash('Please load data before using customer analysis.', 'warning')
    
    return render_template('customer_analysis.html', system_status=system_status)

@app.route('/product-analysis', methods=['GET', 'POST'])
def product_analysis():
    """Analyze a product, its context, and potential customers."""
    if request.method == 'POST':
        product_id = request.form.get('product_id')
        agent = get_agent()
        
        try:
            result = agent.get_product_analysis(product_id)
            
            # Make sure all text fields use |safe and |nl2br instead of |linebreaksbr
            # No need to modify - templates already use |replace
            
            return render_template('product_analysis_results.html', results=result)
        except Exception as e:
            flash(f'Error analyzing product: {e}', 'error')
            return redirect(url_for('product_analysis'))
    
    # For GET request, show the form
    system_status = get_system_status()
    
    # Check if the system is ready for analysis
    if not system_status['database_exists']:
        flash('Please initialize the system before using product analysis.', 'warning')
    elif not system_status['has_data']:
        flash('Please load data before using product analysis.', 'warning')
    
    return render_template('product_analysis.html', system_status=system_status)

@app.route('/category-analysis', methods=['GET', 'POST'])
def category_analysis():
    """Analyze trends in a product category."""
    if request.method == 'POST':
        category = request.form.get('category')
        agent = get_agent()
        
        # Validate category input
        if not category:
            flash('Please select a valid category', 'error')
            return redirect(url_for('category_analysis'))
            
        app.logger.info(f"Processing category analysis for: {category}")
        
        try:
            # Get data from the agent
            result = agent.get_category_trend_analysis(category)
            
            # Debug information
            app.logger.info(f"Category analysis result keys: {result.keys()}")
            
            # Use chart data generated by the agent, or provide defaults if missing
            price_trend_data = result.get('price_trend_data', {
                'labels': [],
                'datasets': [{'label': 'Avg Price', 'data': []}]
            })
            
            popularity_data = result.get('popularity_data', {
                'labels': [],
                'datasets': [{'label': 'Popularity Score', 'data': []}]
            })
            
            # Check if we have actual data in the result
            if 'message' in result or (not result.get('trending_products') and not result.get('insights')):
                message = result.get('message', 'No data found for this category')
                flash(f'{message}. Please try another category.', 'warning')
                return redirect(url_for('category_analysis'))
            
            # Render the template with data
            return render_template(
                'category_analysis_results.html', 
                results=result,
                price_trend_data=price_trend_data,
                popularity_data=popularity_data
            )
        except Exception as e:
            app.logger.error(f"Error in category analysis: {str(e)}", exc_info=True)
            flash(f'Error analyzing category: {e}', 'error')
            return redirect(url_for('category_analysis'))
    
    # For GET request, show the form
    system_status = get_system_status()
    
    # Check if the system is ready for analysis
    if not system_status['database_exists']:
        flash('Please initialize the system before using category analysis.', 'warning')
    elif not system_status['has_data']:
        flash('Please load data before using category analysis.', 'warning')
    
    # Fetch categories directly to populate the dropdown
    categories = []
    try:
        db = get_db()
        db.connect()
        query = "SELECT DISTINCT category FROM products ORDER BY category"
        result = db.fetch_all(query)
        if result:
            for row in result:
                if isinstance(row[0], bytes):
                    try:
                        categories.append(row[0].decode('utf-8'))
                    except UnicodeDecodeError:
                        categories.append("[Binary data]")
                else:
                    categories.append(row[0])
    except Exception as e:
        app.logger.error(f"Error fetching categories: {str(e)}")
        flash('Error loading categories. Please check database connection.', 'error')
    
    return render_template('category_analysis.html', system_status=system_status, categories=categories)

@app.route('/seasonal-recommendations', methods=['GET', 'POST'])
def seasonal_recommendations():
    """Get seasonal product recommendations for a customer."""
    if request.method == 'POST':
        customer_id = request.form.get('customer_id')
        season = request.form.get('season')
        agent = get_agent()
        
        try:
            result = agent.get_seasonal_recommendations(customer_id, season)
            return render_template('seasonal_recommendations_results.html', results=result)
        except Exception as e:
            flash(f'Error generating seasonal recommendations: {e}', 'error')
            return redirect(url_for('seasonal_recommendations'))
    
    # For GET request, show the form
    system_status = get_system_status()
    
    # Check if the system is ready for recommendations
    if not system_status['database_exists']:
        flash('Please initialize the system before using seasonal recommendations.', 'warning')
    elif not system_status['has_data']:
        flash('Please load data before using seasonal recommendations.', 'warning')
    
    return render_template('seasonal_recommendations.html', system_status=system_status)

@app.route('/debug/system-status')
def debug_system_status():
    """Debug endpoint to display system status"""
    system_status = get_system_status()
    # Pretty format for display
    output = "<h1>System Status</h1>"
    output += "<pre>"
    for key, value in system_status.items():
        output += f"{key}: {value}\n"
    output += "</pre>"
    output += "<h2>Database Connection</h2>"
    output += f"<p>DB Path: {get_db().db_path}</p>"
    try:
        get_db().connect()
        output += "<p style='color:green'>Connection successful</p>"
        
        # Check tables
        query = "SELECT name FROM sqlite_master WHERE type='table'"
        tables = get_db().fetch_all(query)
        if not tables:
            output += "<p>No tables found</p>"
        else:
            output += "<h3>Tables:</h3><ul>"
            for table_row in tables:
                table = table_row[0]
                output += f"<li>{table}</li>"
                # Get count for each table
                try:
                    count_query = f"SELECT COUNT(*) as count FROM {table}"
                    count_result = get_db().fetch_one(count_query)
                    count = count_result[0] if count_result else 0
                    output += f" - {count} records"
                except:
                    output += " - Error getting count"
            output += "</ul>"
        
        get_db().close()
    except Exception as e:
        output += f"<p style='color:red'>Connection error: {str(e)}</p>"
    
    return output

@app.route('/api/system-status')
def api_system_status():
    """API endpoint to get system status."""
    try:
        system_status = get_system_status()
        return jsonify(system_status)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/customers')
def api_list_customers():
    """API endpoint to list all customers."""
    try:
        if not get_db().check_connection() or not get_db().table_exists("customers"):
            return jsonify([])
            
        query = "SELECT customer_id, age, gender, location FROM customers"
        # Use the same approach as in list_customers to avoid encoding issues
        db = get_db()
        db.connect()
        customers = []
        
        result = db.fetch_all(query)
        if result:
            columns = ["customer_id", "age", "gender", "location"]
            for row in result:
                customer_dict = {}
                for i, col in enumerate(columns):
                    # Safely handle potentially binary data
                    if isinstance(row[i], bytes):
                        try:
                            # First try UTF-8
                            customer_dict[col] = row[i].decode('utf-8')
                        except UnicodeDecodeError:
                            try:
                                # Try with 'latin-1' which can decode any byte value
                                customer_dict[col] = row[i].decode('latin-1')
                            except Exception:
                                try:
                                    # Try with 'ascii' and ignore errors
                                    customer_dict[col] = row[i].decode('ascii', errors='ignore')
                                except Exception:
                                    # Last resort: represent as hex
                                    customer_dict[col] = f"[Binary: {row[i].hex()[:10]}...]"
                    else:
                        customer_dict[col] = row[i]
                customers.append(customer_dict)
        
        return jsonify(customers)
    except Exception as e:
        # Return empty list instead of error
        return jsonify([])

@app.route('/api/products')
def api_list_products():
    """API endpoint to list all products."""
    try:
        if not get_db().check_connection() or not get_db().table_exists("products"):
            return jsonify([])
            
        query = "SELECT product_id, category, subcategory, price FROM products"
        # Use the same approach as in list_products to avoid encoding issues
        db = get_db()
        db.connect()
        products = []
        
        result = db.fetch_all(query)
        if result:
            columns = ["product_id", "category", "subcategory", "price"]
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
                products.append(product_dict)
        
        return jsonify(products)
    except Exception as e:
        # Return empty list instead of error
        return jsonify([])

@app.route('/api/categories')
def api_list_categories():
    """API endpoint to list all product categories."""
    try:
        if not get_db().check_connection() or not get_db().table_exists("products"):
            return jsonify([])
            
        query = "SELECT DISTINCT category FROM products ORDER BY category"
        # Use direct database access instead of pandas
        db = get_db()
        db.connect()
        categories = []
        
        result = db.fetch_all(query)
        if result:
            for row in result:
                # Each row should have only one element (the category)
                if isinstance(row[0], bytes):
                    try:
                        category = row[0].decode('utf-8')
                        categories.append(category)
                    except UnicodeDecodeError:
                        categories.append("[Binary data]")
                else:
                    categories.append(row[0])
        
        return jsonify(categories)
    except Exception as e:
        # Return empty list instead of error
        return jsonify([])

@app.route('/export_customers')
def export_customers():
    """Export customers data in the specified format."""
    format_type = request.args.get('format', 'csv')
    try:
        query = """
        SELECT customer_id, age, gender, location, customer_segment, avg_order_value
        FROM customers
        ORDER BY customer_id
        """
        # Use the same approach as in list_customers to avoid encoding issues
        db = get_db()
        db.connect()
        customers = []
        
        result = db.fetch_all(query)
        if result:
            columns = ["customer_id", "age", "gender", "location", "customer_segment", "avg_order_value"]
            for row in result:
                customer_dict = {}
                for i, col in enumerate(columns):
                    # Safely handle potentially binary data
                    if isinstance(row[i], bytes):
                        try:
                            # First try UTF-8
                            customer_dict[col] = row[i].decode('utf-8')
                        except UnicodeDecodeError:
                            try:
                                # Try with 'latin-1' which can decode any byte value
                                customer_dict[col] = row[i].decode('latin-1')
                            except Exception:
                                try:
                                    # Try with 'ascii' and ignore errors
                                    customer_dict[col] = row[i].decode('ascii', errors='ignore')
                                except Exception:
                                    # Last resort: represent as hex
                                    customer_dict[col] = f"[Binary: {row[i].hex()[:10]}...]"
                    else:
                        customer_dict[col] = row[i]
                customers.append(customer_dict)
        
        if format_type == 'json':
            response = jsonify(customers)
            response.headers["Content-Disposition"] = "attachment; filename=customers.json"
            return response
        else:  # default to CSV
            # Convert to DataFrame for CSV export
            customers_df = pd.DataFrame(customers)
            csv_data = customers_df.to_csv(index=False)
            response = app.response_class(
                csv_data,
                mimetype='text/csv',
                headers={"Content-Disposition": "attachment; filename=customers.csv"}
            )
            return response
    except Exception as e:
        flash(f'Error exporting customers: {e}', 'error')
        return redirect(url_for('list_customers'))

@app.route('/export_products')
def export_products():
    """Export products data in the specified format."""
    format_type = request.args.get('format', 'csv')
    try:
        query = """
        SELECT product_id, category, subcategory, price, brand, product_rating
        FROM products
        ORDER BY category, subcategory
        """
        # Use the same approach as in export_customers to avoid encoding issues
        db = get_db()
        db.connect()
        products = []
        
        result = db.fetch_all(query)
        if result:
            columns = ["product_id", "category", "subcategory", "price", "brand", "product_rating"]
            for row in result:
                product_dict = {}
                for i, col in enumerate(columns):
                    # Safely handle potentially binary data
                    if isinstance(row[i], bytes):
                        try:
                            # First try UTF-8
                            product_dict[col] = row[i].decode('utf-8')
                        except UnicodeDecodeError:
                            try:
                                # Try with 'latin-1' which can decode any byte value
                                product_dict[col] = row[i].decode('latin-1')
                            except Exception:
                                try:
                                    # Try with 'ascii' and ignore errors
                                    product_dict[col] = row[i].decode('ascii', errors='ignore')
                                except Exception:
                                    # Last resort: represent as hex
                                    product_dict[col] = f"[Binary: {row[i].hex()[:10]}...]"
                    else:
                        product_dict[col] = row[i]
                products.append(product_dict)
        
        if format_type == 'json':
            response = jsonify(products)
            response.headers["Content-Disposition"] = "attachment; filename=products.json"
            return response
        else:  # default to CSV
            # Convert to DataFrame for CSV export
            products_df = pd.DataFrame(products)
            csv_data = products_df.to_csv(index=False)
            response = app.response_class(
                csv_data,
                mimetype='text/csv',
                headers={"Content-Disposition": "attachment; filename=products.csv"}
            )
            return response
    except Exception as e:
        flash(f'Error exporting products: {e}', 'error')
        return redirect(url_for('list_products'))

@app.route('/debug/fix-encoding')
def debug_fix_encoding():
    """Debug endpoint to analyze and fix database encoding issues."""
    output = "<h1>Database Encoding Debug</h1>"
    
    try:
        # Connect to database
        db = get_db()
        db.connect()
        
        # Check if database exists
        if not os.path.exists(db.db_path):
            output += f"<p style='color:red'>Database file does not exist at {db.db_path}</p>"
            return output
        
        output += f"<p>Database file exists at {db.db_path}</p>"
        
        # Check encoding pragma
        encoding_result = db.fetch_one("PRAGMA encoding")
        output += f"<p>Database encoding: {encoding_result[0] if encoding_result else 'Unknown'}</p>"
        
        # Check for binary data in customers table
        try:
            query = "SELECT customer_id, age, gender, location FROM customers LIMIT 20"
            result = db.fetch_all(query)
            
            if not result:
                output += "<p>No customer records found.</p>"
            else:
                output += f"<p>Found {len(result)} customer records.</p>"
                output += "<h2>Sample Customer Data</h2>"
                output += "<table border='1'><tr><th>Column</th><th>Data Type</th><th>Value</th><th>Hex (if binary)</th></tr>"
                
                for row in result[:5]:  # Show first 5 rows
                    for i, col in enumerate(['customer_id', 'age', 'gender', 'location']):
                        value = row[i]
                        value_type = type(value).__name__
                        
                        if isinstance(value, bytes):
                            # Try to decode with different encodings
                            decoded = None
                            for encoding in ['utf-8', 'latin-1', 'ascii']:
                                try:
                                    decoded = value.decode(encoding)
                                    output += f"<tr><td>{col}</td><td>{value_type}</td><td>{decoded} (decoded with {encoding})</td><td>{value.hex()[:20]}</td></tr>"
                                    break
                                except UnicodeDecodeError:
                                    continue
                            
                            if decoded is None:
                                output += f"<tr><td>{col}</td><td>{value_type}</td><td>Cannot decode</td><td>{value.hex()[:20]}</td></tr>"
                        else:
                            output += f"<tr><td>{col}</td><td>{value_type}</td><td>{value}</td><td>N/A</td></tr>"
                
                output += "</table>"
                
                # Add option to fix the database
                output += "<h2>Fix Options</h2>"
                output += "<form method='post' action='/debug/run-fix-encoding'>"
                output += "<input type='submit' value='Run Database Fix'>"
                output += "</form>"
        except Exception as e:
            output += f"<p style='color:red'>Error accessing customers table: {str(e)}</p>"
        
        # Close connection
        db.close()
        
    except Exception as e:
        output += f"<p style='color:red'>Error: {str(e)}</p>"
    
    return output

@app.route('/debug/run-fix-encoding', methods=['POST'])
def debug_run_fix_encoding():
    """Run the database fix process."""
    try:
        # Import fix_database function from the script
        sys.path.append(str(Path(__file__).parent.parent))
        from fix_database import fix_database
        
        # Run the fix
        success = fix_database()
        
        if success:
            flash("Database encoding fix completed successfully. Please restart the application.", "success")
        else:
            flash("Database encoding fix failed. Check the server logs for details.", "error")
    except Exception as e:
        flash(f"Error running database fix: {str(e)}", "error")
    
    return redirect(url_for('debug_fix_encoding'))

@app.teardown_appcontext
def close_resources(e=None):
    """Close resources at the end of the request."""
    # Close database
    db = g.pop('db', None)
    if db is not None:
        db.close()
    
    # Close any agent resources if needed
    agent = g.pop('agent', None)
    # If the agent has a close method, you could call it here

if __name__ == '__main__':
    # Create template and static directories if they don't exist
    template_dir = Path(__file__).parent / 'templates'
    static_dir = Path(__file__).parent / 'static'
    template_dir.mkdir(exist_ok=True)
    static_dir.mkdir(exist_ok=True)
    
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True) 