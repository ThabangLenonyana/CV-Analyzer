// CV Analyzer Single Page Application
function cvAnalyzerApp() {
    return {
        // View state
        currentView: 'upload',
        resultsTab: 'summary',
        
        // Upload state
        selectedFile: null,
        cvData: null,
        jobInputMode: 'sample',
        jobDescriptionJSON: '',
        selectedJob: null,
        sampleJobs: [],
        
        // Analysis state
        analysisResult: null,
        analysisStep: 0,
        
        // UI state
        uploading: false,
        analyzing: false,
        dragover: false,
        message: null,
        messageType: 'error',
        
        // Initialize the app
        init() {
            // Load sample jobs on init
            this.loadSampleJobs();
            
            // Set up auto-hide for messages
            this.$watch('message', (value) => {
                if (value) {
                    setTimeout(() => {
                        this.message = null;
                    }, 5000);
                }
            });
        },
        
        // File handling methods
        handleFileSelect(event) {
            const file = event.target.files[0];
            this.validateAndSetFile(file);
        },
        
        handleDrop(event) {
            this.dragover = false;
            const file = event.dataTransfer.files[0];
            this.validateAndSetFile(file);
        },
        
        validateAndSetFile(file) {
            if (!file) return;
            
            // Check file type
            const allowedTypes = window.appConfig?.allowedExtensions || ['pdf', 'docx'];
            const fileExt = file.name.split('.').pop().toLowerCase();
            
            if (!allowedTypes.includes(fileExt)) {
                this.showMessage(`Invalid file type. Allowed types: ${allowedTypes.join(', ')}`, 'error');
                return;
            }
            
            // Check file size
            const maxSize = (window.appConfig?.maxFileSizeMB || 10) * 1024 * 1024;
            if (file.size > maxSize) {
                this.showMessage(`File too large. Maximum size is ${window.appConfig?.maxFileSizeMB || 10}MB`, 'error');
                return;
            }
            
            this.selectedFile = file;
            this.showMessage('File selected successfully', 'success');
        },
        
        removeFile() {
            this.selectedFile = null;
            document.getElementById('cv-file').value = '';
        },
        
        // API methods
        async uploadCV() {
            if (!this.selectedFile) return;
            
            this.uploading = true;
            this.message = null;
            
            const formData = new FormData();
            formData.append('file', this.selectedFile);
            
            try {
                const response = await fetch('/api/cv/upload', {
                    method: 'POST',
                    body: formData
                });
                
                const result = await response.json();
                
                if (!response.ok) {
                    throw new Error(result.detail || 'Upload failed');
                }
                
                this.cvData = result.cv_data;
                this.showMessage('CV uploaded and parsed successfully!', 'success');
                
                // Clear file selection
                this.selectedFile = null;
                
            } catch (error) {
                this.showMessage(error.message, 'error');
            } finally {
                this.uploading = false;
            }
        },
        
        async loadSampleJobs() {
            try {
                const response = await fetch('/api/sample-job-descriptions');
                const result = await response.json();
                
                if (result.success) {
                    this.sampleJobs = result.samples;
                }
            } catch (error) {
                console.error('Failed to load sample jobs:', error);
            }
        },
        
        selectSampleJob(sample) {
            this.selectedJob = sample.data;
            this.jobDescriptionJSON = JSON.stringify(sample.data, null, 2);
            this.showMessage(`Selected: ${sample.data.job_title}`, 'success');
        },
        
        async validateJSON() {
            try {
                const jobData = JSON.parse(this.jobDescriptionJSON);
                
                const response = await fetch('/api/cv/validate-job-json', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(jobData)
                });
                
                const result = await response.json();
                
                if (result.valid) {
                    this.selectedJob = result.parsed_data;
                    this.showMessage('Valid job description format!', 'success');
                } else {
                    this.showMessage('Invalid format: ' + JSON.stringify(result.errors), 'error');
                }
                
            } catch (error) {
                this.showMessage('Invalid JSON: ' + error.message, 'error');
            }
        },
        
        async analyzeCV() {
            if (!this.cvData || !this.selectedJob) return;
            
            this.analyzing = true;
            this.analysisStep = 0;
            this.message = null;
            
            // Simulate progress steps
            const progressInterval = setInterval(() => {
                if (this.analysisStep < 4) {
                    this.analysisStep++;
                }
            }, 1500);
            
            try {
                const response = await fetch('/api/cv/analyze', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        cv_data: this.cvData,
                        job_description: this.selectedJob,
                        detailed: true
                    })
                });
                
                const result = await response.json();
                
                if (!response.ok) {
                    throw new Error(result.detail || 'Analysis failed');
                }
                
                this.analysisResult = result;
                this.showMessage('Analysis completed successfully!', 'success');
                
                // Complete progress
                this.analysisStep = 5;
                
                // Wait a moment then switch to results view
                setTimeout(() => {
                    this.currentView = 'results';
                }, 500);
                
            } catch (error) {
                this.showMessage(error.message, 'error');
            } finally {
                clearInterval(progressInterval);
                this.analyzing = false;
                this.analysisStep = 0;
            }
        },
        
        // Results methods
        exportResults() {
            if (!this.analysisResult) return;
            
            const dataStr = JSON.stringify(this.analysisResult, null, 2);
            const dataUri = 'data:application/json;charset=utf-8,'+ encodeURIComponent(dataStr);
            
            const exportFileDefaultName = `cv_analysis_${new Date().toISOString().slice(0,10)}.json`;
            
            const linkElement = document.createElement('a');
            linkElement.setAttribute('href', dataUri);
            linkElement.setAttribute('download', exportFileDefaultName);
            linkElement.click();
            
            this.showMessage('Results exported successfully!', 'success');
        },
        
        printResults() {
            window.print();
            this.showMessage('Print dialog opened', 'success');
        },
        
        shareResults() {
            // Placeholder for share functionality
            this.showMessage('Share feature coming soon!', 'info');
        },
        
        startNewAnalysis() {
            // Reset all state
            this.analysisResult = null;
            this.selectedJob = null;
            this.jobDescriptionJSON = '';
            this.cvData = null;
            this.selectedFile = null;
            this.jobInputMode = 'sample';
            this.currentView = 'upload';
            this.resultsTab = 'summary';
            
            // Clear file input
            const fileInput = document.getElementById('cv-file');
            if (fileInput) fileInput.value = '';
            
            this.showMessage('Ready for new analysis', 'success');
        },
        
        // Utility methods
        formatFileSize(bytes) {
            if (!bytes) return '';
            const sizes = ['Bytes', 'KB', 'MB', 'GB'];
            const i = Math.floor(Math.log(bytes) / Math.log(1024));
            return Math.round(bytes / Math.pow(1024, i) * 100) / 100 + ' ' + sizes[i];
        },
        
        showMessage(text, type = 'error') {
            this.message = text;
            this.messageType = type;
        },
        
        // Get score color class
        getScoreColor(score) {
            if (score >= 70) return 'text-green-600';
            if (score >= 50) return 'text-yellow-600';
            return 'text-red-600';
        },
        
        // Get match quality badge
        getMatchQualityBadge(quality) {
            const badges = {
                'full': 'bg-green-100 text-green-800',
                'partial': 'bg-yellow-100 text-yellow-800',
                'none': 'bg-red-100 text-red-800'
            };
            return badges[quality] || badges['none'];
        },
        
        // Navigation helpers
        canViewResults() {
            return this.analysisResult !== null;
        },
        
        // Format date for display
        formatDate(dateStr) {
            if (!dateStr) return 'Present';
            if (dateStr.toLowerCase() === 'present') return 'Present';
            
            try {
                const date = new Date(dateStr);
                return date.toLocaleDateString('en-US', { year: 'numeric', month: 'short' });
            } catch {
                return dateStr;
            }
        }
    }
}

// Initialize Alpine.js when DOM is ready
document.addEventListener('alpine:init', () => {
    Alpine.data('cvAnalyzerApp', cvAnalyzerApp);
});

// Add some global Alpine magic helpers
document.addEventListener('alpine:init', () => {
    // Magic helper for checking if a value exists in an array
    Alpine.magic('includes', () => {
        return (haystack, needle) => {
            if (!Array.isArray(haystack)) return false;
            return haystack.includes(needle);
        };
    });
    
    // Magic helper for truncating text
    Alpine.magic('truncate', () => {
        return (text, length = 100) => {
            if (!text || text.length <= length) return text;
            return text.substring(0, length) + '...';
        };
    });
});

// Handle browser back button
window.addEventListener('popstate', function(event) {
    // Handle navigation state if needed
});

// Service Worker registration for PWA capabilities (optional)
if ('serviceWorker' in navigator && window.location.protocol === 'https:') {
    navigator.serviceWorker.register('/static/sw.js').catch(err => {
        console.log('ServiceWorker registration failed: ', err);
    });
}