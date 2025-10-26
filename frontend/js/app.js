/**
 * Stock Trading Quant Engine - Frontend Application
 * Built with Alpine.js, Bootstrap 5.3, and HTMX
 */

function app() {
    return {
        // ============================================
        // Application State
        // ============================================
        currentStep: 0,
        isRunning: false,
        statusMessage: 'Ready to start. Click any step to begin.',
        statusType: 'info',
        apiStatus: 'Checking...',
        apiStatusClass: 'badge bg-secondary',

        // Step information
        steps: {
            0: { name: 'Idle', icon: '⏸️', color: 'secondary' },
            1: { name: 'Generate Features', icon: '⚡', color: 'info' },
            2: { name: 'Generate Labels', icon: '🏷️', color: 'info' },
            3: { name: 'Train Models', icon: '🤖', color: 'info' },
            4: { name: 'Generate Predictions', icon: '🎯', color: 'info' },
            5: { name: 'Start API', icon: '🚀', color: 'success' }
        },

        // ============================================
        // Computed Properties
        // ============================================
        get currentStepLabel() {
            const step = this.steps[this.currentStep] || this.steps[0];
            return `${step.icon} ${step.name}`;
        },

        get statusAlertClass() {
            const classes = ['alert', 'mb-0', 'fade', 'show'];
            classes.push(`alert-${this.statusType}`);
            return classes.join(' ');
        },

        // ============================================
        // Lifecycle Methods
        // ============================================
        async initApp() {
            console.log('🚀 Quant Trading Engine - Initializing...');

            // Check API status on load
            await this.checkApiStatus();

            // Set up HTMX event listeners
            this.setupHTMXListeners();

            // Setup periodic API status check
            setInterval(() => {
                if (!this.isRunning) {
                    this.checkApiStatus();
                }
            }, 5000); // Check every 5 seconds

            console.log('✅ Application initialized');
        },

        // ============================================
        // API Status Methods
        // ============================================
        async checkApiStatus() {
            try {
                const response = await fetch('http://localhost:8000/v1/health', {
                    method: 'GET',
                    headers: {
                        'Accept': 'application/json'
                    }
                });

                if (response.ok) {
                    this.apiStatus = '✅ API Running (port 8000)';
                    this.apiStatusClass = 'badge bg-success';
                    console.log('✅ API is running');
                } else {
                    this.setApiOffline();
                }
            } catch (error) {
                this.setApiOffline();
            }
        },

        setApiOffline() {
            this.apiStatus = '⚠️ API Offline';
            this.apiStatusClass = 'badge bg-warning';
            console.warn('⚠️ API is not running');
        },

        // ============================================
        // Status Update Methods
        // ============================================
        updateStatus(step, message, type = 'info') {
            this.statusMessage = message;
            this.statusType = type;
            this.isRunning = type === 'info';

            // Add timestamp
            const timestamp = new Date().toLocaleTimeString();
            console.log(`[${timestamp}] ${step}: ${message}`);
        },

        // ============================================
        // HTMX Integration
        // ============================================
        setupHTMXListeners() {
            // Before request
            document.addEventListener('htmx:beforeRequest', (event) => {
                this.isRunning = true;
                document.body.classList.add('cursor-wait');
            });

            // After request
            document.addEventListener('htmx:afterRequest', (event) => {
                this.isRunning = false;
                document.body.classList.remove('cursor-wait');

                // Check if request was successful
                if (event.detail.xhr.status === 200) {
                    this.statusType = 'success';
                    this.statusMessage = `✅ ${this.steps[this.currentStep]?.name || 'Step'} completed successfully!`;
                    console.log('✅ Request completed');
                } else {
                    this.statusType = 'danger';
                    this.statusMessage = `❌ Error: ${event.detail.xhr.statusText}`;
                    console.error('❌ Request failed', event.detail.xhr);
                }
            });

            // On error
            document.addEventListener('htmx:responseError', (event) => {
                this.isRunning = false;
                this.statusType = 'danger';
                this.statusMessage = `❌ Error occurred. Please check the console.`;
                console.error('❌ Response error', event);
            });

            // On network error
            document.addEventListener('htmx:sendError', (event) => {
                this.isRunning = false;
                this.statusType = 'danger';
                this.statusMessage = `❌ Network error. Is the server running?`;
                console.error('❌ Network error', event);
            });
        },

        // ============================================
        // Pipeline Step Methods
        // ============================================
        async executeStep(stepNumber, description) {
            this.currentStep = stepNumber;
            this.updateStatus(
                `Step ${stepNumber}`,
                description,
                'info'
            );
        },

        // ============================================
        // Helper Methods
        // ============================================
        async sleep(ms) {
            return new Promise(resolve => setTimeout(resolve, ms));
        },

        getTimeFormatted() {
            const now = new Date();
            return now.toLocaleTimeString('en-US', {
                hour12: false,
                hour: '2-digit',
                minute: '2-digit',
                second: '2-digit'
            });
        },

        clearStatus() {
            this.statusMessage = 'Ready to start. Click any step to begin.';
            this.statusType = 'info';
            this.currentStep = 0;
        },

        // ============================================
        // Logging Methods
        // ============================================
        logSuccess(message) {
            console.log(`✅ ${message}`);
            this.statusMessage = message;
            this.statusType = 'success';
        },

        logError(message) {
            console.error(`❌ ${message}`);
            this.statusMessage = message;
            this.statusType = 'danger';
        },

        logInfo(message) {
            console.info(`ℹ️ ${message}`);
            this.statusMessage = message;
            this.statusType = 'info';
        },

        logWarning(message) {
            console.warn(`⚠️ ${message}`);
            this.statusMessage = message;
            this.statusType = 'warning';
        }
    }
}

// ============================================
// Global HTMX Configuration
// ============================================

// Configure HTMX defaults
if (window.htmx) {
    htmx.config.timeout = 300000; // 5 minutes
    htmx.config.indicatorStyle = 'spinner';
    htmx.config.defaultIndicatorStyle = 'spinner';

    // Add CORS headers if needed
    htmx.config.refreshOnHistoryMiss = true;
}

// ============================================
// Global Event Listeners
// ============================================

// Log when page loads
window.addEventListener('load', () => {
    console.log('📊 Stock Trading Quant Engine Ready');
    console.log('🌐 Control Server: http://localhost:3000');
    console.log('🔌 API Server: http://localhost:8000');
});

// Handle page visibility change
document.addEventListener('visibilitychange', () => {
    if (document.hidden) {
        console.log('👋 Application minimized');
    } else {
        console.log('👀 Application resumed');
    }
});

// Handle before unload
window.addEventListener('beforeunload', (event) => {
    if (document.body.classList.contains('cursor-wait')) {
        event.preventDefault();
        event.returnValue = 'A pipeline step is still running. Are you sure you want to leave?';
    }
});

// ============================================
// Console Branding
// ============================================

console.log('%c📈 Stock Trading Quant Engine', 'font-size: 24px; color: #0d6efd; font-weight: bold;');
console.log('%cBootstrap 5.3 + HTMX + Alpine.js', 'font-size: 14px; color: #666;');
console.log('%c', 'background: linear-gradient(135deg, #0d6efd 0%, #0a58ca 100%); padding: 20px;');

// ============================================
// End of Application Script
// ============================================
