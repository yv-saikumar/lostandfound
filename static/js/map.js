// This is a utility file for map-related functionality
// Used in report_item.html and item_details.html

function initializeMap(containerId, lat, lng, editable = false) {
    // Initialize the map
    const map = L.map(containerId).setView([lat, lng], 13);
    
    // Add the OpenStreetMap tile layer
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
    }).addTo(map);
    
    // Add a marker at the specified location
    const marker = L.marker([lat, lng], {
        draggable: editable
    }).addTo(map);
    
    // If editable, allow the marker to be dragged
    if (editable) {
        marker.on('dragend', function(e) {
            const position = marker.getLatLng();
            document.getElementById('latitude').value = position.lat;
            document.getElementById('longitude').value = position.lng;
        });
        
        // Also allow clicking on the map to move the marker
        map.on('click', function(e) {
            marker.setLatLng(e.latlng);
            document.getElementById('latitude').value = e.latlng.lat;
            document.getElementById('longitude').value = e.latlng.lng;
        });
    }
    
    return { map, marker };
}

function getUserLocation() {
    return new Promise((resolve, reject) => {
        if (navigator.geolocation) {
            navigator.geolocation.getCurrentPosition(
                position => {
                    resolve({
                        lat: position.coords.latitude,
                        lng: position.coords.longitude
                    });
                },
                error => {
                    console.error("Error getting user location:", error);
                    reject(error);
                }
            );
        } else {
            const error = new Error("Geolocation is not supported by this browser.");
            console.error(error);
            reject(error);
        }
    });
}

function geocodeAddress(address) {
    return new Promise((resolve, reject) => {
        // Using Nominatim OpenStreetMap service for geocoding
        const url = `https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(address)}`;
        
        fetch(url)
            .then(response => response.json())
            .then(data => {
                if (data && data.length > 0) {
                    resolve({
                        lat: parseFloat(data[0].lat),
                        lng: parseFloat(data[0].lon)
                    });
                } else {
                    reject(new Error("Location not found"));
                }
            })
            .catch(error => {
                console.error("Geocoding error:", error);
                reject(error);
            });
    });
}
