/**
 * Restaurant Dashboard JavaScript
 * Handles restaurant dashboard functionality
 */

document.addEventListener('DOMContentLoaded', function() {
    // Restaurant Details Update
    const saveRestaurantDetails = document.getElementById('saveRestaurantDetails');
    if (saveRestaurantDetails) {
        saveRestaurantDetails.addEventListener('click', async function() {
            const form = document.getElementById('editRestaurantForm');
            const formData = new FormData(form);
            
            // Validate rating
            const rating = parseFloat(formData.get('rating'));
            if (isNaN(rating) || rating < 0 || rating > 5) {
                alert('Rating must be between 0.0 and 5.0');
                return;
            }
            
            try {
                const response = await fetch('/api/restaurant/update_details', {
                    method: 'POST',
                    body: formData
                });
                
                const data = await response.json();
                
                if (data.success) {
                    // Show success message and reload page
                    alert('Restaurant details updated successfully!');
                    location.reload();
                } else {
                    alert(data.message || 'Error updating restaurant details');
                }
            } catch (error) {
                console.error('Error:', error);
                alert('An error occurred while updating restaurant details');
            }
        });
    }
    // Add Menu Item
    const saveMenuItem = document.getElementById('saveMenuItem');
    if (saveMenuItem) {
        saveMenuItem.addEventListener('click', function() {
            const form = document.getElementById('addMenuItemForm');
            const formData = new FormData(form);
            const data = {
                name: formData.get('name'),
                price: formData.get('price'),
                description: formData.get('description'),
                category: formData.get('category'),
                is_vegetarian: formData.get('is_vegetarian') === 'on'
            };

            fetch('/api/restaurant/add_menu_item', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(data)
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    location.reload();
                } else {
                    alert('Error adding menu item: ' + data.message);
                }
            });
        });
    }

    // Upload Restaurant Image
    const saveImage = document.getElementById('saveImage');
    const imageInput = document.getElementById('imageInput');

    if (saveImage && imageInput) {
        saveImage.addEventListener('click', async function() {
            const form = document.getElementById('uploadImageForm');
            const formData = new FormData(form);
            const buttonText = saveImage.querySelector('.button-text'); // Assumed structure
            const spinner = saveImage.querySelector('.spinner-border'); // Assumed structure

            // Validate file
            if (!imageInput.files || !imageInput.files[0]) {
                alert('Please select an image to upload');
                return;
            }

            // Show loading state
            saveImage.disabled = true;
            if(buttonText) buttonText.textContent = 'Uploading...'; //Handle potential null
            if(spinner) spinner.classList.remove('d-none'); //Handle potential null

            try {
                const response = await fetch('/api/restaurant/upload_image', {
                    method: 'POST',
                    body: formData
                });
                const data = await response.json();

                if (data.success) {
                    // Update image in UI
                    const restaurantImage = document.querySelector('.restaurant-image');
                    if (restaurantImage) {
                        restaurantImage.src = data.image_url;
                    }

                    // Show success message
                    alert('Image uploaded successfully!');

                    // Reset form
                    form.reset();
                } else {
                    throw new Error(data.message);
                }
            } catch (error) {
                console.error('Upload error:', error);
                alert(error.message || 'Error uploading image. Please try again.');
            } finally {
                // Reset button state
                saveImage.disabled = false;
                if(buttonText) buttonText.textContent = 'Upload'; //Handle potential null
                if(spinner) spinner.classList.add('d-none'); //Handle potential null
            }
        });
    }

    // Reset form when modal is closed
    const uploadImageModal = document.getElementById('uploadImageModal');
    if (uploadImageModal) {
        uploadImageModal.addEventListener('hidden.bs.modal', function () {
            const form = document.getElementById('uploadImageForm');
            form.reset();
        });
    }

    // Update Restaurant Location
    const saveLocation = document.getElementById('saveLocation');
    if (saveLocation) {
        saveLocation.addEventListener('click', function() {
            const form = document.getElementById('updateLocationForm');
            const formData = new FormData(form);
            const data = {
                location: formData.get('location')
            };

            fetch('/api/restaurant/update_location', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(data)
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    location.reload();
                } else {
                    alert('Error updating location: ' + data.message);
                }
            });
        });
    }

    // Restaurant status toggle
    const statusToggle = document.getElementById('restaurant-status-toggle');
    const statusBadge = document.getElementById('restaurant-status-badge');

    if (statusToggle) {
        statusToggle.addEventListener('change', function() {
            // Show loading state
            const originalText = statusBadge.textContent;
            statusBadge.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Updating...';

            fetch('/api/toggle_restaurant_status', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({}),
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // Update badge
                    statusBadge.textContent = data.is_open ? 'OPEN' : 'CLOSED';
                    statusBadge.className = `badge ${data.is_open ? 'bg-success' : 'bg-danger'}`;

                    // Show toast notification
                    if (window.showToast) {
                        window.showToast(data.message, data.is_open ? 'success' : 'warning');
                    } else {
                        alert(data.message);
                    }
                } else {
                    // Revert toggle if operation failed
                    statusToggle.checked = !statusToggle.checked;
                    statusBadge.textContent = originalText;

                    alert(data.message || 'Error updating restaurant status');
                }
            })
            .catch(error => {
                console.error('Error:', error);

                // Revert toggle if operation failed
                statusToggle.checked = !statusToggle.checked;
                statusBadge.textContent = originalText;

                alert('An error occurred. Please try again.');
            });
        });
    }

    // Menu item availability toggle
    const availabilityToggles = document.querySelectorAll('.toggle-availability');

    availabilityToggles.forEach(toggle => {
        toggle.addEventListener('change', function() {
            const menuItemId = this.getAttribute('data-menu-item-id');
            const menuItemCard = document.querySelector(`.menu-item-card[data-menu-item-id="${menuItemId}"]`);
            const availabilityBadge = menuItemCard.querySelector('.availability-badge');

            // Show loading state
            const originalText = availabilityBadge.textContent;
            availabilityBadge.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Updating...';

            fetch('/api/toggle_menu_item', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    item_id: menuItemId
                }),
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // Update menu item card
                    availabilityBadge.textContent = data.is_available ? 'In Stock' : 'Out of Stock';
                    availabilityBadge.className = `badge availability-badge ${data.is_available ? 'bg-success' : 'bg-danger'}`;

                    if (data.is_available) {
                        menuItemCard.classList.remove('out-of-stock');
                    } else {
                        menuItemCard.classList.add('out-of-stock');
                    }

                    // Show toast notification
                    if (window.showToast) {
                        window.showToast(data.message, data.is_available ? 'success' : 'warning');
                    }
                } else {
                    // Revert toggle if operation failed
                    this.checked = !this.checked;
                    availabilityBadge.textContent = originalText;

                    alert(data.message || 'Error updating menu item availability');
                }
            })
            .catch(error => {
                console.error('Error:', error);

                // Revert toggle if operation failed
                this.checked = !this.checked;
                availabilityBadge.textContent = originalText;

                alert('An error occurred. Please try again.');
            });
        });
    });

    // Order Status Updates
    const statusButtons = document.querySelectorAll('.update-order-status');
    statusButtons.forEach(button => {
        button.addEventListener('click', async function() {
            const orderId = this.dataset.orderId;
            const status = this.dataset.status;
            
            // Confirm cancellation
            if (status === 'cancelled') {
                if (!confirm('Are you sure you want to cancel this order?')) {
                    return;
                }
            }
            
            // Disable button and show loading state
            const originalText = this.innerHTML;
            this.disabled = true;
            this.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Processing...';
            
            try {
                const response = await fetch('/api/order/update_status', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        order_id: orderId,
                        status: status
                    })
                });
                
                const data = await response.json();
                
                if (data.success) {
                    if (window.showToast) {
                        window.showToast(data.message, 'success');
                    }
                    // Reload after a short delay to show the toast
                    setTimeout(() => location.reload(), 1000);
                } else {
                    this.disabled = false;
                    this.innerHTML = originalText;
                    alert(data.message || 'Error updating order status');
                }
            } catch (error) {
                console.error('Error:', error);
                this.disabled = false;
                this.innerHTML = originalText;
                alert('An error occurred. Please try again.');
            }
        });
    });

    // Menu item search functionality
    const menuSearch = document.getElementById('menu-search');
    const menuItems = document.querySelectorAll('.menu-item-card');
    const noResultsDiv = document.getElementById('no-menu-results');

    if (menuSearch) {
        menuSearch.addEventListener('input', function() {
            const searchQuery = this.value.toLowerCase();
            let visibleCount = 0;

            menuItems.forEach(item => {
                const name = item.querySelector('h6').textContent.toLowerCase();
                const description = item.querySelector('p.card-text') ?
                                   item.querySelector('p.card-text').textContent.toLowerCase() : '';
                const category = item.getAttribute('data-category') ?
                                item.getAttribute('data-category').toLowerCase() : '';

                if (name.includes(searchQuery) || description.includes(searchQuery) || category.includes(searchQuery)) {
                    item.style.display = '';
                    visibleCount++;
                } else {
                    item.style.display = 'none';
                }
            });

            // Show/hide no results message
            if (noResultsDiv) {
                noResultsDiv.style.display = visibleCount === 0 ? 'block' : 'none';
            }
        });
    }
});