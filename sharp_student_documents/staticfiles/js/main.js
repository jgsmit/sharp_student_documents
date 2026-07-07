// Main JavaScript file for SharpDocs

// Wait for DOM to be loaded
document.addEventListener('DOMContentLoaded', function() {
    console.log('SharpDocs main.js loaded');
    
    // Initialize tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'))
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl)
    });
    
    // Initialize popovers
    var popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'))
    var popoverList = popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl)
    });
    
    // Auto-hide alerts after 5 seconds
    setTimeout(function() {
        var alerts = document.querySelectorAll('.alert');
        alerts.forEach(function(alert) {
            var bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        });
    }, 5000);
    
    // Smooth scroll for anchor links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            var target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth'
                });
            }
        });
    });
    
    // Form validation
    var forms = document.querySelectorAll('.needs-validation');
    Array.prototype.slice.call(forms).forEach(function (form) {
        form.addEventListener('submit', function (event) {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            form.classList.add('was-validated');
        }, false);
    });
    
    // Loading states for buttons
    document.querySelectorAll('.btn-loading').forEach(function(button) {
        button.addEventListener('click', function() {
            var originalText = this.innerHTML;
            this.innerHTML = '<span class="spinner-border spinner-border-sm me-2" role="status"></span> Loading...';
            this.disabled = true;
            
            // Reset after 3 seconds (for demo purposes)
            setTimeout(function() {
                button.innerHTML = originalText;
                button.disabled = false;
            }, 3000);
        });
    });
});

// Global functions for AJAX requests
window.SharpDocs = {
    // Helper function to get CSRF token
    getCookie: function(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    },
    
    // Helper function to show messages
    showMessage: function(message, type = 'info') {
        const alertDiv = document.createElement('div');
        alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
        alertDiv.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        const container = document.querySelector('.container');
        if (container) {
            container.insertBefore(alertDiv, container.firstChild);
            
            // Auto-hide after 5 seconds
            setTimeout(function() {
                const bsAlert = new bootstrap.Alert(alertDiv);
                bsAlert.close();
            }, 5000);
        }
    },
    
    // Helper function to format currency
    formatCurrency: function(amount) {
        return new Intl.NumberFormat('en-US', {
            style: 'currency',
            currency: 'USD'
        }).format(amount);
    },
    
    // Helper function to format date
    formatDate: function(date) {
        return new Date(date).toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    }
};

// Export for use in other scripts
if (typeof module !== 'undefined' && module.exports) {
    module.exports = SharpDocs;
}

// Withdrawal Management Functions
window.approveWithdrawal = function(withdrawalId) {
    if (confirm('Are you sure you want to approve this withdrawal request?')) {
        // Show processing message
        const row = document.querySelector(`[data-withdrawal-id="${withdrawalId}"]`);
        if (row) {
            const statusCell = row.querySelector('td:nth-child(6)');
            const actionsCell = row.querySelector('td:nth-child(7)');
            
            statusCell.innerHTML = '<span class="badge bg-info">Processing...</span>';
            actionsCell.innerHTML = '<div class="spinner-border spinner-border-sm" role="status"></div>';
            
            // Make actual API call
            fetch(`/withdrawals/admin/approve/${withdrawalId}/`, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': SharpDocs.getCookie('csrftoken'),
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({})
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // Update status based on response
                    const newStatus = data.new_status || 'processing';
                    const statusBadge = newStatus === 'completed' ? 'bg-success' : 'bg-info';
                    const statusText = newStatus === 'completed' ? 'Completed' : 'Processing';
                    
                    statusCell.innerHTML = `<span class="badge ${statusBadge}">${statusText}</span>`;
                    actionsCell.innerHTML = `
                        <div class="btn-group btn-group-sm">
                            <a href="#" class="btn btn-primary" title="View Details" onclick="viewWithdrawalDetails('${withdrawalId}')">
                                <i class="bi bi-eye"></i>
                            </a>
                            <a href="#" class="btn btn-info" title="View Progress">
                                <i class="bi bi-clock"></i>
                            </a>
                        </div>
                    `;
                    
                    // Show success message
                    SharpDocs.showMessage(data.message || 'Withdrawal request approved successfully!', 'success');
                } else {
                    // Show error message
                    SharpDocs.showMessage(data.error || 'Failed to approve withdrawal', 'danger');
                    // Reset UI
                    location.reload();
                }
            })
            .catch(error => {
                console.error('Error:', error);
                SharpDocs.showMessage('Failed to approve withdrawal. Please try again.', 'danger');
                location.reload();
            });
        }
    }
};

window.rejectWithdrawal = function(withdrawalId) {
    if (confirm('Are you sure you want to reject this withdrawal request? This action cannot be undone!')) {
        // Show processing message
        const row = document.querySelector(`[data-withdrawal-id="${withdrawalId}"]`);
        if (row) {
            const statusCell = row.querySelector('td:nth-child(6)');
            const actionsCell = row.querySelector('td:nth-child(7)');
            
            statusCell.innerHTML = '<span class="badge bg-info">Processing...</span>';
            actionsCell.innerHTML = '<div class="spinner-border spinner-border-sm" role="status"></div>';
            
            // Make actual API call
            fetch(`/withdrawals/admin/reject/${withdrawalId}/`, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': SharpDocs.getCookie('csrftoken'),
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({})
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    statusCell.innerHTML = '<span class="badge bg-danger">Failed</span>';
                    actionsCell.innerHTML = `
                        <div class="btn-group btn-group-sm">
                            <a href="#" class="btn btn-primary" title="View Details" onclick="viewWithdrawalDetails('${withdrawalId}')">
                                <i class="bi bi-eye"></i>
                            </a>
                            <a href="#" class="btn btn-warning" title="Retry">
                                <i class="bi bi-arrow-clockwise"></i>
                            </a>
                        </div>
                    `;
                    
                    // Show success message
                    SharpDocs.showMessage(data.message || 'Withdrawal request rejected successfully!', 'warning');
                } else {
                    // Show error message
                    SharpDocs.showMessage(data.error || 'Failed to reject withdrawal', 'danger');
                    // Reset UI
                    location.reload();
                }
            })
            .catch(error => {
                console.error('Error:', error);
                SharpDocs.showMessage('Failed to reject withdrawal. Please try again.', 'danger');
                location.reload();
            });
        }
    }
};

window.viewWithdrawalDetails = function(withdrawalId) {
    // Show loading message
    const modal = document.createElement('div');
    modal.className = 'modal fade';
    modal.innerHTML = `
        <div class="modal-dialog">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title">Withdrawal Details</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                </div>
                <div class="modal-body text-center">
                    <div class="spinner-border text-primary" role="status">
                        <span class="visually-hidden">Loading...</span>
                    </div>
                    <p class="mt-3">Loading withdrawal details...</p>
                </div>
            </div>
        </div>
    `;
    
    document.body.appendChild(modal);
    const bsModal = new bootstrap.Modal(modal);
    bsModal.show();
    
    // Fetch withdrawal details
    fetch(`/withdrawals/admin/details/${withdrawalId}/`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                const modalBody = modal.querySelector('.modal-body');
                modalBody.innerHTML = `
                    <div class="row">
                        <div class="col-md-6">
                            <h6>User Information</h6>
                            <p><strong>Username:</strong> ${data.user.username}</p>
                            <p><strong>Email:</strong> ${data.user.email}</p>
                            <p><strong>Full Name:</strong> ${data.user.get_full_name || 'N/A'}</p>
                        </div>
                        <div class="col-md-6">
                            <h6>Withdrawal Details</h6>
                            <p><strong>Amount:</strong> $${data.amount}</p>
                            <p><strong>Type:</strong> ${data.get_payout_type_display}</p>
                            <p><strong>Method:</strong> ${data.withdrawal_method.get_method_type_display}</p>
                            <p><strong>Status:</strong> ${data.status}</p>
                            <p><strong>Requested:</strong> ${SharpDocs.formatDate(data.requested_at)}</p>
                        </div>
                    </div>
                    ${data.failure_reason ? `<div class="alert alert-danger"><strong>Failure Reason:</strong> ${data.failure_reason}</div>` : ''}
                `;
            } else {
                const modalBody = modal.querySelector('.modal-body');
                modalBody.innerHTML = `
                    <div class="alert alert-danger">
                        <strong>Error:</strong> ${data.error || 'Failed to load withdrawal details'}
                    </div>
                `;
            }
        })
        .catch(error => {
            console.error('Error:', error);
            const modalBody = modal.querySelector('.modal-body');
            modalBody.innerHTML = `
                <div class="alert alert-danger">
                    <strong>Error:</strong> Failed to load withdrawal details
                </div>
            `;
        });
    
    // Clean up modal when hidden
    modal.addEventListener('hidden.bs.modal', function () {
        document.body.removeChild(modal);
    });
};
