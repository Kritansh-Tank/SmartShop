#!/usr/bin/env python
from smartshop.utils.database import Database

def list_customers():
    db = Database()
    db.connect()
    
    query = "SELECT customer_id FROM customers LIMIT 10"
    results = db.fetch_all(query)
    
    if not results:
        print("No customers found in the database.")
        return []
    
    customers = []
    print("Available customers:")
    for row in results:
        customer_id = row[0]
        if isinstance(customer_id, bytes):
            try:
                # First try UTF-8
                customer_id = customer_id.decode('utf-8')
            except UnicodeDecodeError:
                try:
                    # Try with 'latin-1' which can decode any byte value
                    customer_id = customer_id.decode('latin-1')
                except Exception:
                    try:
                        # Try with 'ascii' and ignore errors
                        customer_id = customer_id.decode('ascii', errors='ignore')
                    except Exception:
                        # Last resort: represent as hex
                        customer_id = f"[Binary: {customer_id.hex()[:10]}...]"
        print(f"- {customer_id}")
        customers.append(customer_id)
    
    return customers

if __name__ == "__main__":
    list_customers() 