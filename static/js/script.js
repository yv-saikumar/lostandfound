document.addEventListener('DOMContentLoaded', function() {
    // Bootstrap tooltips initialization
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // Auto-hide flash messages after 5 seconds
    setTimeout(function() {
        var flashMessages = document.querySelectorAll('.alert:not(.no-auto-hide)');
        flashMessages.forEach(function(message) {
            var bsAlert = new bootstrap.Alert(message);
            bsAlert.close();
        });
    }, 5000);
    
    // Item image preview for upload forms
    var itemImageInput = document.getElementById('image');
    if (itemImageInput) {
        itemImageInput.addEventListener('change', function(e) {
            if (e.target.files.length > 0) {
                var reader = new FileReader();
                reader.onload = function(e) {
                    var previewContainer = document.createElement('div');
                    previewContainer.className = 'image-preview mt-2';
                    
                    var previewImage = document.createElement('img');
                    previewImage.className = 'img-thumbnail';
                    previewImage.style.maxHeight = '200px';
                    previewImage.src = e.target.result;
                    
                    // Remove any existing preview
                    var existingPreview = document.querySelector('.image-preview');
                    if (existingPreview) {
                        existingPreview.remove();
                    }
                    
                    // Add new preview
                    previewContainer.appendChild(previewImage);
                    itemImageInput.parentNode.appendChild(previewContainer);
                };
                reader.readAsDataURL(e.target.files[0]);
            }
        });
    }
    
    // Status update for claimed and verified items
    function updateItemStatuses() {
        var statusElements = document.querySelectorAll('.status-update');
        if (statusElements.length > 0) {
            statusElements.forEach(function(element) {
                var itemId = element.getAttribute('data-item-id');
                var statusUrl = `/api/item/${itemId}/status`;
                
                fetch(statusUrl)
                    .then(response => response.json())
                    .then(data => {
                        if (data.status !== element.getAttribute('data-status')) {
                            element.innerHTML = data.status_html;
                            element.setAttribute('data-status', data.status);
                            
                            // If status changed, we might want to refresh the page
                            if (data.status === 'claimed' && element.hasAttribute('data-refresh-on-claim')) {
                                window.location.reload();
                            }
                        }
                    })
                    .catch(error => console.error('Error fetching item status:', error));
            });
        }
    }
    
    // Update statuses every 60 seconds if needed
    if (document.querySelectorAll('.status-update').length > 0) {
        setInterval(updateItemStatuses, 60000);
    }
});
