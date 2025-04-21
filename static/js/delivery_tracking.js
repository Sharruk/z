// Delivery Tracking System

// Global variables
let map;
let directionsService;
let directionsRenderer;
let customerMarker;
let deliveryMarker;
let restaurantMarker;
let watchId;
let trackingInterval;
let currentPosition;
let lastDeliveryPosition;
let customerPosition;
let restaurantPosition;
let etaUpdateInterval;

// Styling for the dark theme map
const darkMapStyle = [
    { elementType: "geometry", stylers: [{ color: "#242f3e" }] },
    { elementType: "labels.text.stroke", stylers: [{ color: "#242f3e" }] },
    { elementType: "labels.text.fill", stylers: [{ color: "#746855" }] },
    {
        featureType: "administrative.locality",
        elementType: "labels.text.fill",
        stylers: [{ color: "#d59563" }],
    },
    {
        featureType: "poi",
        elementType: "labels.text.fill",
        stylers: [{ color: "#d59563" }],
    },
    {
        featureType: "poi.park",
        elementType: "geometry",
        stylers: [{ color: "#263c3f" }],
    },
    {
        featureType: "poi.park",
        elementType: "labels.text.fill",
        stylers: [{ color: "#6b9a76" }],
    },
    {
        featureType: "road",
        elementType: "geometry",
        stylers: [{ color: "#38414e" }],
    },
    {
        featureType: "road",
        elementType: "geometry.stroke",
        stylers: [{ color: "#212a37" }],
    },
    {
        featureType: "road",
        elementType: "labels.text.fill",
        stylers: [{ color: "#9ca5b3" }],
    },
    {
        featureType: "road.highway",
        elementType: "geometry",
        stylers: [{ color: "#746855" }],
    },
    {
        featureType: "road.highway",
        elementType: "geometry.stroke",
        stylers: [{ color: "#1f2835" }],
    },
    {
        featureType: "road.highway",
        elementType: "labels.text.fill",
        stylers: [{ color: "#f3d19c" }],
    },
    {
        featureType: "transit",
        elementType: "geometry",
        stylers: [{ color: "#2f3948" }],
    },
    {
        featureType: "transit.station",
        elementType: "labels.text.fill",
        stylers: [{ color: "#d59563" }],
    },
    {
        featureType: "water",
        elementType: "geometry",
        stylers: [{ color: "#17263c" }],
    },
    {
        featureType: "water",
        elementType: "labels.text.fill",
        stylers: [{ color: "#515c6d" }],
    },
    {
        featureType: "water",
        elementType: "labels.text.stroke",
        stylers: [{ color: "#17263c" }],
    },
];

// Main function to initialize delivery tracking
function initDeliveryTracking(orderId, isDeliveryPartner = false) {
    // Don't initialize if Google Maps is not loaded
    if (!window.google || !window.google.maps) {
        console.error('Google Maps API not loaded');
        return;
    }

    // Initialize map and services
    function initMap() {
        const mapElement = document.getElementById('map');
        if (!mapElement) return;
        
        // Default to Chennai coordinates if no specific location
        const defaultLat = 13.0827;
        const defaultLng = 80.2707;
        
        map = new google.maps.Map(mapElement, {
            center: { lat: defaultLat, lng: defaultLng },
            zoom: 13,
            styles: darkMapStyle
        });
        
        // Initialize directions service and renderer
        directionsService = new google.maps.DirectionsService();
        directionsRenderer = new google.maps.DirectionsRenderer({
            map: map,
            suppressMarkers: true, // We'll create custom markers
            polylineOptions: {
                strokeColor: '#00BFA6',
                strokeWeight: 5,
                strokeOpacity: 0.7
            }
        });
        
        // If delivery partner, start tracking and sending updates
        if (isDeliveryPartner) {
            startTracking();
        } else {
            // For customers, just receive updates
            startReceivingUpdates();
        }
    }
    
    // Start tracking (for delivery partners)
    function startTracking() {
        // Show location permission warning if needed
        const permissionWarning = document.getElementById('location-permission-warning');
        
        // Check if geolocation is available
        if (!navigator.geolocation) {
            if (permissionWarning) {
                permissionWarning.textContent = 'Geolocation is not supported by your browser.';
                permissionWarning.classList.remove('d-none');
            }
            return;
        }
        
        // Start watching position
        watchId = navigator.geolocation.watchPosition(
            onPositionUpdate,
            onPositionError,
            {
                enableHighAccuracy: true,
                timeout: 10000,
                maximumAge: 0
            }
        );
        
        // Fetch initial customer and restaurant locations
        Promise.all([
            fetchCustomerLocation(orderId),
            fetchRestaurantLocation(orderId)
        ]).then(([customerLoc, restaurantLoc]) => {
            customerPosition = customerLoc;
            restaurantPosition = restaurantLoc;
            
            // Add markers for customer and restaurant
            addCustomerMarker(customerPosition);
            addRestaurantMarker(restaurantPosition);
            
            // Fit bounds to include all markers
            if (currentPosition) {
                const bounds = new google.maps.LatLngBounds();
                bounds.extend(new google.maps.LatLng(currentPosition.lat, currentPosition.lng));
                bounds.extend(new google.maps.LatLng(customerPosition.lat, customerPosition.lng));
                if (restaurantPosition) {
                    bounds.extend(new google.maps.LatLng(restaurantPosition.lat, restaurantPosition.lng));
                }
                map.fitBounds(bounds);
            }
        }).catch(error => {
            console.error('Error fetching locations:', error);
        });
    }
    
    // Handle position updates
    function onPositionUpdate(position) {
        const { latitude, longitude } = position.coords;
        currentPosition = { lat: latitude, lng: longitude };
        
        // Update delivery marker on map
        if (!deliveryMarker) {
            // Create marker if it doesn't exist
            deliveryMarker = new google.maps.Marker({
                position: currentPosition,
                map: map,
                icon: {
                    url: 'https://maps.google.com/mapfiles/ms/icons/motorcycling.png',
                    scaledSize: new google.maps.Size(40, 40)
                },
                title: 'Delivery Partner'
            });
        } else {
            // Update marker position
            deliveryMarker.setPosition(new google.maps.LatLng(latitude, longitude));
        }
        
        // Send position update to server
        sendPositionUpdate(orderId, currentPosition);
        
        // Update route if we have customer position
        if (customerPosition) {
            if (!lastDeliveryPosition || 
                google.maps.geometry.spherical.computeDistanceBetween(
                    new google.maps.LatLng(lastDeliveryPosition.lat, lastDeliveryPosition.lng),
                    new google.maps.LatLng(latitude, longitude)
                ) > 50) { // Only update if moved more than 50 meters
                
                updateRoute();
                lastDeliveryPosition = { ...currentPosition };
            }
        }
    }
    
    // Handle position errors
    function onPositionError(error) {
        console.error('Geolocation error:', error);
        const permissionWarning = document.getElementById('location-permission-warning');
        
        if (permissionWarning) {
            switch (error.code) {
                case error.PERMISSION_DENIED:
                    permissionWarning.textContent = 'Location permission denied. Please enable location access.';
                    break;
                case error.POSITION_UNAVAILABLE:
                    permissionWarning.textContent = 'Location information is unavailable.';
                    break;
                case error.TIMEOUT:
                    permissionWarning.textContent = 'Location request timed out.';
                    break;
                case error.UNKNOWN_ERROR:
                    permissionWarning.textContent = 'An unknown error occurred while retrieving location.';
                    break;
            }
            
            permissionWarning.classList.remove('d-none');
        }
    }
    
    // Update route between delivery and customer
    function updateRoute() {
        if (!directionsService || !customerPosition || !currentPosition) return;
        
        const origin = new google.maps.LatLng(currentPosition.lat, currentPosition.lng);
        const destination = new google.maps.LatLng(customerPosition.lat, customerPosition.lng);
        
        directionsService.route({
            origin: origin,
            destination: destination,
            travelMode: google.maps.TravelMode.DRIVING
        }, (result, status) => {
            if (status === google.maps.DirectionsStatus.OK) {
                directionsRenderer.setDirections(result);
                
                // Calculate and update ETA
                calculateETA(origin, destination);
            } else {
                console.error('Directions request failed:', status);
            }
        });
    }
    
    // Calculate ETA between two points
    function calculateETA(origin, destination) {
        if (!directionsService) return;
        
        directionsService.route({
            origin: origin,
            destination: destination,
            travelMode: google.maps.TravelMode.DRIVING
        }, (result, status) => {
            if (status === google.maps.DirectionsStatus.OK && result.routes.length > 0) {
                const route = result.routes[0];
                if (route.legs.length > 0) {
                    const leg = route.legs[0];
                    updateETADisplay(leg.duration.text);
                }
            }
        });
    }
    
    // Update ETA on display
    function updateETADisplay(etaText) {
        const etaElement = document.getElementById('delivery-eta');
        if (etaElement) {
            etaElement.textContent = `Estimated arrival: ${etaText}`;
        }
    }
    
    // Fetch customer location from server
    async function fetchCustomerLocation(orderId) {
        try {
            const response = await fetch(`/api/order/${orderId}/location`);
            const data = await response.json();
            
            if (data.success) {
                return {
                    lat: data.latitude,
                    lng: data.longitude,
                    address: data.address
                };
            } else {
                throw new Error(data.message || 'Failed to fetch customer location');
            }
        } catch (error) {
            console.error('Error fetching customer location:', error);
            throw error;
        }
    }
    
    // Fetch restaurant location from server (would need to be implemented on server)
    async function fetchRestaurantLocation(orderId) {
        // In real application, this would be an API endpoint
        // For demo purposes, we'll use a hardcoded location (Chennai area)
        return {
            lat: 13.0827 + (Math.random() * 0.02 - 0.01),
            lng: 80.2707 + (Math.random() * 0.02 - 0.01),
            name: 'Restaurant'
        };
    }
    
    // Send delivery position updates to server
    function sendPositionUpdate(orderId, position) {
        if (!isDeliveryPartner || !position) return;
        
        fetch('/api/delivery/update_location', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                order_id: orderId,
                latitude: position.lat,
                longitude: position.lng
            })
        }).catch(error => {
            console.error('Error sending position update:', error);
        });
    }
    
    // For customers: receive delivery partner location updates
    function startReceivingUpdates() {
        // Fetch customer location
        fetchCustomerLocation(orderId).then(location => {
            customerPosition = location;
            addCustomerMarker(customerPosition);
            
            // Center map on customer position initially
            map.setCenter(new google.maps.LatLng(customerPosition.lat, customerPosition.lng));
            map.setZoom(15);
            
            // Start polling for delivery partner location
            trackingInterval = setInterval(() => {
                fetch(`/api/order/${orderId}/delivery_location`)
                    .then(response => response.json())
                    .then(data => {
                        if (data.success) {
                            const deliveryPosition = {
                                lat: data.latitude,
                                lng: data.longitude
                            };
                            
                            // Update delivery marker
                            if (!deliveryMarker) {
                                deliveryMarker = new google.maps.Marker({
                                    position: deliveryPosition,
                                    map: map,
                                    icon: {
                                        url: 'https://maps.google.com/mapfiles/ms/icons/motorcycling.png',
                                        scaledSize: new google.maps.Size(40, 40)
                                    },
                                    title: 'Delivery Partner'
                                });
                            } else {
                                deliveryMarker.setPosition(new google.maps.LatLng(deliveryPosition.lat, deliveryPosition.lng));
                            }
                            
                            // Update route
                            if (customerPosition) {
                                const origin = new google.maps.LatLng(deliveryPosition.lat, deliveryPosition.lng);
                                const destination = new google.maps.LatLng(customerPosition.lat, customerPosition.lng);
                                
                                directionsService.route({
                                    origin: origin,
                                    destination: destination,
                                    travelMode: google.maps.TravelMode.DRIVING
                                }, (result, status) => {
                                    if (status === google.maps.DirectionsStatus.OK) {
                                        directionsRenderer.setDirections(result);
                                        
                                        // Calculate and update ETA
                                        if (result.routes.length > 0 && result.routes[0].legs.length > 0) {
                                            const leg = result.routes[0].legs[0];
                                            updateETADisplay(leg.duration.text);
                                        }
                                    }
                                });
                                
                                // Fit bounds to include both markers
                                const bounds = new google.maps.LatLngBounds();
                                bounds.extend(origin);
                                bounds.extend(destination);
                                map.fitBounds(bounds);
                            }
                        }
                    })
                    .catch(error => {
                        console.error('Error fetching delivery location:', error);
                    });
            }, 10000); // Update every 10 seconds
        }).catch(error => {
            console.error('Error starting location updates:', error);
        });
    }
    
    // Add customer marker to map
    function addCustomerMarker(position) {
        if (!map) return;
        
        customerMarker = new google.maps.Marker({
            position: new google.maps.LatLng(position.lat, position.lng),
            map: map,
            icon: {
                url: 'https://maps.google.com/mapfiles/ms/icons/red-dot.png',
                scaledSize: new google.maps.Size(40, 40)
            },
            title: 'Delivery Location'
        });
        
        // Add info window with address
        if (position.address) {
            const infoWindow = new google.maps.InfoWindow({
                content: `<div><strong>Delivery Address:</strong><br>${position.address}</div>`
            });
            
            customerMarker.addListener('click', function() {
                infoWindow.open(map, customerMarker);
            });
        }
    }
    
    // Add restaurant marker to map
    function addRestaurantMarker(position) {
        if (!map || !position) return;
        
        restaurantMarker = new google.maps.Marker({
            position: new google.maps.LatLng(position.lat, position.lng),
            map: map,
            icon: {
                url: 'https://maps.google.com/mapfiles/ms/icons/yellow-dot.png',
                scaledSize: new google.maps.Size(40, 40)
            },
            title: 'Restaurant'
        });
        
        // Add info window with name
        if (position.name) {
            const infoWindow = new google.maps.InfoWindow({
                content: `<div><strong>${position.name}</strong></div>`
            });
            
            restaurantMarker.addListener('click', function() {
                infoWindow.open(map, restaurantMarker);
            });
        }
    }
    
    // Stop tracking when leaving the page
    function stopTracking() {
        if (watchId) {
            navigator.geolocation.clearWatch(watchId);
            watchId = null;
        }
        
        if (trackingInterval) {
            clearInterval(trackingInterval);
            trackingInterval = null;
        }
        
        if (etaUpdateInterval) {
            clearInterval(etaUpdateInterval);
            etaUpdateInterval = null;
        }
    }
    
    // Initialize the map
    initMap();
    
    // Add event listener to stop tracking when leaving the page
    window.addEventListener('beforeunload', stopTracking);
}

// This function will be called by the Google Maps API callback
function initTrackingMap() {
    // The tracking initialization is called from the HTML template
    // This function is just a placeholder for the Maps API callback
}