// SmartShop Web UI JavaScript

document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Initialize popovers
    var popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });

    // Auto-close alerts after 5 seconds
    setTimeout(function() {
        var alerts = document.querySelectorAll('.alert');
        alerts.forEach(function(alert) {
            var bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        });
    }, 5000);

    // Customer ID selector with AJAX loading
    const customerSelector = document.getElementById('customer_id');
    if (customerSelector) {
        fetch('/api/customers')
            .then(response => response.json())
            .then(data => {
                if (Array.isArray(data)) {
                    data.forEach(customer => {
                        const option = document.createElement('option');
                        option.value = customer.customer_id;
                        option.textContent = `${customer.customer_id} - ${customer.gender}, ${customer.age}, ${customer.location}`;
                        customerSelector.appendChild(option);
                    });
                }
            })
            .catch(error => console.error('Error loading customers:', error));
    }

    // Product ID selector with AJAX loading
    const productSelector = document.getElementById('product_id');
    if (productSelector) {
        fetch('/api/products')
            .then(response => response.json())
            .then(data => {
                if (Array.isArray(data)) {
                    data.forEach(product => {
                        const option = document.createElement('option');
                        option.value = product.product_id;
                        option.textContent = `${product.product_id} - ${product.category}: ${product.subcategory} ($${product.price})`;
                        productSelector.appendChild(option);
                    });
                }
            })
            .catch(error => console.error('Error loading products:', error));
    }

    // Category selector with AJAX loading
    const categorySelector = document.getElementById('category');
    if (categorySelector) {
        // Only load categories via AJAX if there are no options (other than the default) already
        const existingOptions = categorySelector.querySelectorAll('option:not([value=""])').length;
        
        if (existingOptions === 0) {
            fetch('/api/categories')
                .then(response => response.json())
                .then(data => {
                    if (Array.isArray(data)) {
                        data.forEach(category => {
                            const option = document.createElement('option');
                            option.value = category;
                            option.textContent = category;
                            categorySelector.appendChild(option);
                        });
                    }
                })
                .catch(error => console.error('Error loading categories:', error));
        }
    }

    // Context type change handler
    const contextType = document.getElementById('context_type');
    const contextValueContainer = document.getElementById('context_value_container');
    const contextValueInput = document.getElementById('context_value');
    const contextValueLabel = document.getElementById('context_value_label');
    
    if (contextType && contextValueContainer && contextValueLabel) {
        contextType.addEventListener('change', function() {
            const selectedValue = this.value;
            
            if (selectedValue === 'none') {
                contextValueContainer.style.display = 'none';
                contextValueInput.removeAttribute('required');
            } else {
                contextValueContainer.style.display = 'block';
                contextValueInput.setAttribute('required', 'required');
                
                if (selectedValue === 'occasion') {
                    contextValueLabel.textContent = 'Occasion (e.g., birthday, anniversary)';
                    contextValueInput.placeholder = 'Enter occasion';
                } else if (selectedValue === 'season') {
                    contextValueLabel.textContent = 'Season (e.g., Summer, Winter)';
                    contextValueInput.placeholder = 'Enter season';
                } else if (selectedValue === 'category') {
                    contextValueLabel.textContent = 'Product Category';
                    contextValueInput.placeholder = 'Enter product category';
                }
            }
        });
        
        // Trigger change event on page load
        const event = new Event('change');
        contextType.dispatchEvent(event);
    }
}); 