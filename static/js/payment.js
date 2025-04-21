// Stripe Payment Integration

document.addEventListener('DOMContentLoaded', function() {
    // Check if we're on the payment checkout page
    const paymentForm = document.getElementById('payment-form');
    if (!paymentForm) return;

    // Payment method selection
    const paymentMethods = document.querySelectorAll('input[name="payment_method"]');
    const paymentDetailsContainers = document.querySelectorAll('.payment-details');

    // Toggle payment details sections based on selection
    paymentMethods.forEach(method => {
        method.addEventListener('change', function() {
            const selectedMethod = this.value;
            
            // Hide all payment details sections
            paymentDetailsContainers.forEach(container => {
                container.classList.add('d-none');
            });
            
            // Show the selected payment method details
            const selectedContainer = document.getElementById(`${selectedMethod}-details`);
            if (selectedContainer) {
                selectedContainer.classList.remove('d-none');
            }
        });
    });

    // Address auto-fill toggle
    const useProfileAddress = document.getElementById('use-profile-address');
    const deliveryAddressField = document.getElementById('delivery-address');
    const profileAddress = deliveryAddressField.getAttribute('data-profile-address');
    
    if (useProfileAddress && deliveryAddressField && profileAddress) {
        useProfileAddress.addEventListener('change', function() {
            if (this.checked) {
                deliveryAddressField.value = profileAddress;
                deliveryAddressField.setAttribute('readonly', true);
            } else {
                deliveryAddressField.removeAttribute('readonly');
            }
        });
    }

    // Validate payment form before submission
    paymentForm.addEventListener('submit', function(event) {
        const selectedPaymentMethod = document.querySelector('input[name="payment_method"]:checked');
        
        if (!selectedPaymentMethod) {
            event.preventDefault();
            showAlert('Please select a payment method', 'danger');
            return;
        }

        const method = selectedPaymentMethod.value;
        
        // Validate card payment fields if selected
        if (method === 'card') {
            const cardNumber = document.getElementById('card-number');
            const cardExpiry = document.getElementById('card-expiry');
            const cardCvc = document.getElementById('card-cvc');
            
            if (cardNumber && cardExpiry && cardCvc) {
                if (!validateCardNumber(cardNumber.value)) {
                    event.preventDefault();
                    showAlert('Please enter a valid card number', 'danger');
                    return;
                }
                
                if (!validateCardExpiry(cardExpiry.value)) {
                    event.preventDefault();
                    showAlert('Please enter a valid expiry date (MM/YY)', 'danger');
                    return;
                }
                
                if (!validateCardCVC(cardCvc.value)) {
                    event.preventDefault();
                    showAlert('Please enter a valid CVC code', 'danger');
                    return;
                }
            }
        }
        
        // Validate UPI ID if UPI is selected
        if (method === 'upi') {
            const upiId = document.getElementById('upi-id');
            if (upiId && !validateUpiId(upiId.value)) {
                event.preventDefault();
                showAlert('Please enter a valid UPI ID', 'danger');
                return;
            }
        }
        
        // Add loading state to submit button
        const submitButton = this.querySelector('button[type="submit"]');
        if (submitButton) {
            submitButton.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Processing...';
            submitButton.disabled = true;
        }
    });

    // Helper functions for validation
    function validateCardNumber(cardNumber) {
        const regex = /^[0-9]{13,19}$/;
        return regex.test(cardNumber.replace(/\s/g, ''));
    }
    
    function validateCardExpiry(expiry) {
        const regex = /^(0[1-9]|1[0-2])\/([0-9]{2})$/;
        return regex.test(expiry);
    }
    
    function validateCardCVC(cvc) {
        const regex = /^[0-9]{3,4}$/;
        return regex.test(cvc);
    }
    
    function validateUpiId(upiId) {
        const regex = /^[a-zA-Z0-9._-]+@[a-zA-Z0-9.-]+$/;
        return regex.test(upiId);
    }
    
    function showAlert(message, type = 'info') {
        const alertContainer = document.getElementById('payment-alerts');
        if (!alertContainer) return;
        
        const alert = document.createElement('div');
        alert.className = `alert alert-${type} alert-dismissible fade show`;
        alert.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        alertContainer.appendChild(alert);
        
        // Auto-dismiss after 5 seconds
        setTimeout(() => {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }, 5000);
    }

    // Format card number with spaces
    const cardNumberInput = document.getElementById('card-number');
    if (cardNumberInput) {
        cardNumberInput.addEventListener('input', function() {
            let value = this.value.replace(/\D/g, '');
            if (value.length > 16) value = value.slice(0, 16);
            
            // Add spaces every 4 digits
            let formattedValue = '';
            for (let i = 0; i < value.length; i++) {
                if (i > 0 && i % 4 === 0) {
                    formattedValue += ' ';
                }
                formattedValue += value[i];
            }
            
            this.value = formattedValue;
        });
    }

    // Format card expiry with slash
    const cardExpiryInput = document.getElementById('card-expiry');
    if (cardExpiryInput) {
        cardExpiryInput.addEventListener('input', function() {
            let value = this.value.replace(/\D/g, '');
            if (value.length > 4) value = value.slice(0, 4);
            
            // Add slash after first 2 digits
            if (value.length > 2) {
                this.value = value.slice(0, 2) + '/' + value.slice(2);
            } else {
                this.value = value;
            }
        });
    }
});