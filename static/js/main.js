/**
 * EZFOODZ - Main JavaScript
 * Global functions and utilities for the application
 */

document.addEventListener('DOMContentLoaded', function() {
    // Initialize Bootstrap tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Initialize Bootstrap popovers
    var popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    var popoverList = popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });
    
    // Auto-close flash messages after 5 seconds
    setTimeout(function() {
        const flashMessages = document.querySelectorAll('.alert:not(.alert-warning, .alert-danger)');
        flashMessages.forEach(function(message) {
            const closeButton = message.querySelector('.btn-close');
            if (closeButton) {
                closeButton.click();
            } else {
                message.classList.remove('show');
                message.style.display = 'none';
            }
        });
    }, 5000);
    
    // Show toast notifications
    window.showToast = function(message, type = 'info') {
        // Create toast container if it doesn't exist
        let toastContainer = document.getElementById('toast-container');
        
        if (!toastContainer) {
            toastContainer = document.createElement('div');
            toastContainer.id = 'toast-container';
            toastContainer.className = 'toast-container position-fixed bottom-0 end-0 p-3';
            toastContainer.style.zIndex = '1070';
            document.body.appendChild(toastContainer);
        }
        
        // Create toast element
        const toastId = 'toast-' + Date.now();
        const toast = document.createElement('div');
        toast.id = toastId;
        toast.className = `toast align-items-center text-white bg-${type} border-0`;
        toast.setAttribute('role', 'alert');
        toast.setAttribute('aria-live', 'assertive');
        toast.setAttribute('aria-atomic', 'true');
        
        // Toast content
        toast.innerHTML = `
            <div class="d-flex">
                <div class="toast-body">
                    ${message}
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
            </div>
        `;
        
        // Add toast to container
        toastContainer.appendChild(toast);
        
        // Initialize and show the toast
        const toastInstance = new bootstrap.Toast(toast, {
            autohide: true,
            delay: 5000
        });
        
        toastInstance.show();
        
        // Remove toast from DOM after it's hidden
        toast.addEventListener('hidden.bs.toast', function () {
            toast.remove();
        });
    };
    
    // Handle any forms with class 'needs-validation'
    const forms = document.querySelectorAll('.needs-validation');
    
    forms.forEach(form => {
        form.addEventListener('submit', function(event) {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            
            form.classList.add('was-validated');
        }, false);
    });
    
    // Quantity controls for menu items
    const decreaseButtons = document.querySelectorAll('.quantity-decrease');
    const increaseButtons = document.querySelectorAll('.quantity-increase');
    
    decreaseButtons.forEach(button => {
        button.addEventListener('click', function() {
            const input = this.parentElement.querySelector('input[type="number"]') || 
                          this.nextElementSibling;
            const currentValue = parseInt(input.value || input.textContent);
            
            if (currentValue > 1) {
                if (input.tagName === 'INPUT') {
                    input.value = currentValue - 1;
                } else {
                    input.textContent = currentValue - 1;
                }
            }
        });
    });
    
    increaseButtons.forEach(button => {
        button.addEventListener('click', function() {
            const input = this.parentElement.querySelector('input[type="number"]');
            if (!input) return;
            
            const currentValue = parseInt(input.value);
            const max = parseInt(input.getAttribute('max') || 10);
            
            if (currentValue < max) {
                input.value = currentValue + 1;
                // Trigger change event to update cart
                input.dispatchEvent(new Event('change'));
            }
        });
    });
});

/**
 * Format a number as Indian Rupees
 * @param {number} amount - The amount to format
 * @returns {string} - Formatted amount
 */
function formatCurrency(amount) {
    return '₹' + amount.toFixed(2);
}

/**
 * Format a date string
 * @param {string} dateString - ISO date string
 * @param {string} format - Format option: 'short', 'long', 'time'
 * @returns {string} - Formatted date
 */
function formatDate(dateString, format = 'short') {
    const date = new Date(dateString);
    
    if (isNaN(date)) {
        return 'Invalid date';
    }
    
    switch (format) {
        case 'short':
            return date.toLocaleDateString('en-IN');
        case 'long':
            return date.toLocaleDateString('en-IN', {
                weekday: 'long',
                year: 'numeric',
                month: 'long',
                day: 'numeric'
            });
        case 'time':
            return date.toLocaleTimeString('en-IN', {
                hour: '2-digit',
                minute: '2-digit'
            });
        default:
            return date.toLocaleString('en-IN');
    }
}

/**
 * Debounce function to limit the rate at which a function can fire
 * @param {function} func - The function to debounce
 * @param {number} wait - The delay in milliseconds
 * @returns {function} - Debounced function
 */
function debounce(func, wait) {
    let timeout;
    
    return function(...args) {
        const context = this;
        clearTimeout(timeout);
        
        timeout = setTimeout(() => {
            func.apply(context, args);
        }, wait);
    };
}
