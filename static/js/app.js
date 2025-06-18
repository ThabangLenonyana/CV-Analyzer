function app() {
    return {
        // App state
        loading: false,
        currentRoute: 'upload',
        
        // Data
        cvData: null,
        jobs: [],
        filteredJobs: [],
        selectedJob: null,
        analysisResult: null,
        recentUploads: [],
        analysisHistory: [],
        recentAnalyses: [],  // Add this
        topJobs: [],  // Add this
        
        // UI state
        analyzing: false,
        analysisStep: 0,
        uploadingCV: false,  // Add this
        uploadStep: 0,  // Add this
        uploadProgress: 0,  // Add this
        loadingJobs: false,
        showRecentUploads: false,
        showDetailedResults: false,
        jobSearchQuery: '',
        dragover: false,
        
        // Modal states
        showRecentCVsModal: false,
        showRecentAnalysesModal: false,
        
        // Modal data
        allRecentCVs: [],
        filteredRecentCVs: [],
        recentCVsSearch: '',
        loadingAllCVs: false,
        
        allAnalyses: [],
        filteredAnalyses: [],
        analysesSearch: '',
        analysesScoreFilter: '',
        analysesSortBy: 'date',
        loadingAllAnalyses: false,
        
        // Pages content
        pages: {
            upload: '',
            history: '',
            jobs: ''
        },
        
        // Component content
        analysisResultsModal: '',
        notificationsComponent: '',
        recentCVsModal: '',  // Add this
        recentAnalysesModal: '',  // Add this
        
        async init() {
            // Initialize the notification system first
            this.initializeNotificationSystem();
            
            await this.loadComponents();
            await this.loadPageTemplates();
            await Promise.all([
                this.loadJobs(),
                this.loadRecentUploads(),
                this.loadRecentAnalyses()  // Add this
            ]);
            this.navigateTo('upload');
        },
        
        initializeNotificationSystem() {
            // Define the notification system function in the global scope
            window.notificationSystem = function() {
                return {
                    notifications: [],
                    showPanel: false,
                    activeToast: null,
                    toastTimeout: null,
                    maxNotifications: 50,

                    init() {
                        // Load notifications from localStorage
                        const saved = localStorage.getItem('notificationHistory');
                        if (saved) {
                            this.notifications = JSON.parse(saved);
                        }

                        // Listen for global notification events
                        window.addEventListener('show-notification', (event) => {
                            this.addNotification(event.detail);
                        });
                    },

                    get unreadCount() {
                        return this.notifications.filter(n => !n.read).length;
                    },

                    toggleNotificationPanel() {
                        this.showPanel = !this.showPanel;
                        if (this.showPanel && this.unreadCount > 0) {
                            // Auto mark as read after 2 seconds
                            setTimeout(() => {
                                this.markAllAsRead();
                            }, 2000);
                        }
                    },

                    addNotification(data) {
                        const notification = {
                            id: Date.now() + Math.random(),
                            title: data.title || this.getDefaultTitle(data.type),
                            message: data.message,
                            type: data.type || 'info',
                            timestamp: new Date().toISOString(),
                            read: false
                        };

                        // Add to beginning of array
                        this.notifications.unshift(notification);

                        // Limit the number of notifications
                        if (this.notifications.length > this.maxNotifications) {
                            this.notifications = this.notifications.slice(0, this.maxNotifications);
                        }

                        // Save to localStorage
                        this.saveNotifications();

                        // Show toast
                        this.showToast(notification);
                    },

                    getDefaultTitle(type) {
                        const titles = {
                            success: 'Success',
                            error: 'Error',
                            warning: 'Warning',
                            info: 'Information'
                        };
                        return titles[type] || 'Notification';
                    },

                    showToast(notification) {
                        this.activeToast = notification;

                        // Clear existing timeout
                        if (this.toastTimeout) {
                            clearTimeout(this.toastTimeout);
                        }

                        // Auto dismiss after 5 seconds
                        this.toastTimeout = setTimeout(() => {
                            this.dismissToast();
                        }, 5000);
                    },

                    dismissToast() {
                        this.activeToast = null;
                        if (this.toastTimeout) {
                            clearTimeout(this.toastTimeout);
                        }
                    },

                    markAsRead(id) {
                        const notification = this.notifications.find(n => n.id === id);
                        if (notification) {
                            notification.read = true;
                            this.saveNotifications();
                        }
                    },

                    markAllAsRead() {
                        this.notifications.forEach(n => n.read = true);
                        this.saveNotifications();
                    },

                    removeNotification(id) {
                        this.notifications = this.notifications.filter(n => n.id !== id);
                        this.saveNotifications();
                    },

                    clearAll() {
                        if (confirm('Are you sure you want to clear all notifications?')) {
                            this.notifications = [];
                            this.saveNotifications();
                        }
                    },

                    saveNotifications() {
                        localStorage.setItem('notificationHistory', JSON.stringify(this.notifications));
                    },

                    formatTime(timestamp) {
                        const date = new Date(timestamp);
                        const now = new Date();
                        const diff = now - date;

                        // Less than a minute
                        if (diff < 60000) {
                            return 'Just now';
                        }

                        // Less than an hour
                        if (diff < 3600000) {
                            const minutes = Math.floor(diff / 60000);
                            return `${minutes} minute${minutes > 1 ? 's' : ''} ago`;
                        }

                        // Less than a day
                        if (diff < 86400000) {
                            const hours = Math.floor(diff / 3600000);
                            return `${hours} hour${hours > 1 ? 's' : ''} ago`;
                        }

                        // Less than a week
                        if (diff < 604800000) {
                            const days = Math.floor(diff / 86400000);
                            return `${days} day${days > 1 ? 's' : ''} ago`;
                        }

                        // Default to date
                        return date.toLocaleDateString();
                    },

                    showAll() {
                        // This could navigate to a dedicated notifications page
                        this.showPanel = false;
                        // Implement navigation to full notifications view if needed
                    }
                };
            };

            // Global function to trigger notifications
            window.showNotification = function(message, type = 'info', title = null) {
                window.dispatchEvent(new CustomEvent('show-notification', {
                    detail: { message, type, title }
                }));
            };
        },
        
        async loadComponents() {
            // Load notifications component HTML (without script tags)
            try {
                const notifResponse = await fetch('/api/components/notifications');
                if (!notifResponse.ok) throw new Error('Failed to load notifications component');
                let notifHTML = await notifResponse.text();
                
                // Remove script tags as we're handling the JS separately
                notifHTML = notifHTML.replace(/<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>/gi, '');
                
                this.notificationsComponent = notifHTML;
            } catch (error) {
                console.error('Error loading notifications component:', error);
                // Fallback to a simple notification bell if component fails to load
                this.notificationsComponent = '<button class="p-2 text-gray-400 hover:text-gray-600"><svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" /></svg></button>';
            }
            
            // Load modal components
            try {
                const cvsModalResponse = await fetch('/api/components/recent-cvs-modal');
                if (cvsModalResponse.ok) {
                    this.recentCVsModal = await cvsModalResponse.text();
                }
                
                const analysesModalResponse = await fetch('/api/components/recent-analyses-modal');
                if (analysesModalResponse.ok) {
                    this.recentAnalysesModal = await analysesModalResponse.text();
                }
            } catch (error) {
                console.error('Error loading modal components:', error);
            }
        },
        
        async loadPageTemplates() {
            // Load the upload page template
            try {
                const uploadResponse = await fetch('/api/components/upload-page');
                if (!uploadResponse.ok) throw new Error('Failed to load upload page');
                this.pages.upload = await uploadResponse.text();
            } catch (error) {
                console.error('Error loading upload page:', error);
                this.pages.upload = '<div class="text-center py-12"><h2 class="text-xl font-semibold text-gray-900">Error Loading Page</h2><p class="text-gray-600 mt-2">Please refresh the page</p></div>';
            }

            // Load the analysis results modal template
            try {
                const modalResponse = await fetch('/api/components/analysis-results-modal');
                if (!modalResponse.ok) throw new Error('Failed to load analysis modal');
                this.analysisResultsModal = await modalResponse.text();
            } catch (error) {
                console.error('Error loading analysis modal:', error);
                // Set default modal content
                this.analysisResultsModal = '<div class="fixed inset-0 z-50 flex items-center justify-center bg-gray-500 bg-opacity-75"><div class="bg-white p-6 rounded-lg">Error loading modal</div></div>';
            }

            // Set placeholder content for other pages
            this.pages.history = '<div class="text-center py-12"><h2 class="text-xl font-semibold text-gray-900">Analysis History</h2><p class="text-gray-600 mt-2">Coming soon...</p></div>';
            this.pages.jobs = '<div class="text-center py-12"><h2 class="text-xl font-semibold text-gray-900">Job Management</h2><p class="text-gray-600 mt-2">Coming soon...</p></div>';
        },
        
        navigateTo(route) {
            this.currentRoute = route;
            // Reset some states when navigating
            if (route !== 'upload') {
                this.showDetailedResults = false;
            }
        },
        
        async loadJobs() {
            this.loadingJobs = true;
            try {
                const response = await fetch('/api/jobs');
                if (!response.ok) throw new Error('Failed to load jobs');
                
                const result = await response.json();
                this.jobs = (result.data || []).map(job => {
                    // If job_data field exists, use it (contains StructuredJobDescription)
                    if (job.job_data) {
                        return {
                            id: job.id,
                            title: job.job_data.job_title,
                            company: job.job_data.company,
                            location: job.job_data.location,
                            experience_level: job.job_data.experience_level,
                            required_skills: job.job_data.required_skills || [],
                            ...job.job_data  // Include all other fields
                        };
                    }
                    // Fallback for different structure
                    return {
                        id: job.id,
                        title: job.job_title || job.title,
                        company: job.company,
                        location: job.location,
                        experience_level: job.experience_level,
                        required_skills: job.required_skills || [],
                        ...job
                    };
                });
                
                this.filteredJobs = this.jobs;
                this.topJobs = this.jobs.slice(0, 5);
            } catch (error) {
                console.error('Error loading jobs:', error);
                this.showNotification('Error loading job descriptions', 'error', 'Failed to Load Jobs');
                this.jobs = [];
                this.filteredJobs = [];
                this.topJobs = [];
            } finally {
                this.loadingJobs = false;
            }
        },
        
        async loadRecentUploads() {
            try {
                const response = await fetch('/api/cv/recent?limit=5');
                if (!response.ok) throw new Error('Failed to load recent uploads');
                
                const result = await response.json();
                this.recentUploads = (result.data || []).map(cv => {
                    // Map based on the actual database structure
                    if (cv.file_upload) {
                        return {
                            id: cv.id,
                            filename: cv.file_upload.original_filename || cv.file_upload.filename,
                            upload_date: cv.parsed_date || cv.file_upload.upload_date,
                            contact_name: cv.contact_name,
                            contact_email: cv.contact_email
                        };
                    }
                    // Fallback for different API response structure
                    return {
                        id: cv.id,
                        filename: cv.filename || cv.original_filename || 'Unknown',
                        upload_date: cv.upload_date || cv.parsed_date || cv.created_at,
                        contact_name: cv.contact_name,
                        contact_email: cv.contact_email
                    };
                });
            } catch (error) {
                console.error('Error loading recent uploads:', error);
                this.recentUploads = [];
            }
        },
        
        async loadRecentAnalyses() {
            try {
                const response = await fetch('/api/analyses/recent?limit=3');
                if (!response.ok) {
                    const errorData = await response.json();
                    console.error('API Error:', errorData);
                    throw new Error(errorData.detail || 'Failed to load recent analyses');
                }
                
                const result = await response.json();
                this.recentAnalyses = (result.data || []).map(analysis => {
                    // Extract key information from the analysis record
                    const analysisData = analysis.analysis_data || {};
                    const cvRecord = analysis.cv_record || {};
                    const jobRecord = analysis.job_description || {};
                    
                    // Extract job title from the job_data JSON field
                    let jobTitle = 'Unknown Job';
                    if (jobRecord.job_data && jobRecord.job_data.job_title) {
                        jobTitle = jobRecord.job_data.job_title;
                    } else if (jobRecord.job_title) {
                        jobTitle = jobRecord.job_title;
                    }
                    
                    // Extract CV name from various possible sources
                    let cvName = 'Unknown CV';
                    if (cvRecord.file_upload && cvRecord.file_upload.original_filename) {
                        cvName = cvRecord.file_upload.original_filename;
                    } else if (cvRecord.contact_name) {
                        cvName = cvRecord.contact_name;
                    } else if (cvRecord.parsed_data && cvRecord.parsed_data.contact_info && cvRecord.parsed_data.contact_info.name) {
                        cvName = cvRecord.parsed_data.contact_info.name;
                    }
                    
                    return {
                        id: analysis.id,
                        job_title: jobTitle,
                        cv_name: cvName,
                        score: analysisData.suitability_score || analysis.suitability_score || 0,
                        analysis_date: analysis.analysis_date || analysis.created_at || new Date().toISOString(),
                        // Store the full analysis record for later use
                        _fullRecord: analysis
                    };
                });
            } catch (error) {
                console.error('Error loading recent analyses:', error);
                this.recentAnalyses = [];
                // Don't show notification during initial load to avoid spam
                if (this.currentRoute === 'upload') {
                    // Silently fail on initial load
                }
            }
        },
        
        filterJobs() {
            if (!this.jobSearchQuery.trim()) {
                this.filteredJobs = this.jobs;
                return;
            }
            
            const query = this.jobSearchQuery.toLowerCase();
            this.filteredJobs = this.jobs.filter(job => 
                (job.title || job.job_title || '').toLowerCase().includes(query) ||
                (job.company || '').toLowerCase().includes(query) ||
                (job.required_skills || []).some(skill => 
                    skill.toLowerCase().includes(query)
                )
            );
        },
        
        async handleFileUpload(event) {
            const file = event.target.files[0];
            if (!file) return;
            
            // Validate file type - hard coded allowed types
            const allowedTypes = ['.pdf', '.docx'];
            const fileExtension = '.' + file.name.split('.').pop().toLowerCase();
            
            if (!allowedTypes.includes(fileExtension)) {
                this.showNotification(
                    `Please upload ${allowedTypes.join(' or ')} files only`,
                    'error',
                    'Invalid File Type'
                );
                event.target.value = '';
                return;
            }
            
            const formData = new FormData();
            formData.append('file', file);
            
            // Initialize upload progress
            this.uploadingCV = true;
            this.uploadStep = 0;
            this.uploadProgress = 0;
            this.showNotification('Uploading CV...', 'info');
            
            // Simulate upload progress
            const progressInterval = setInterval(() => {
                if (this.uploadProgress < 90) {
                    this.uploadProgress += 10;
                    if (this.uploadProgress >= 30 && this.uploadStep < 1) this.uploadStep = 1;
                    if (this.uploadProgress >= 60 && this.uploadStep < 2) this.uploadStep = 2;
                    if (this.uploadProgress >= 80 && this.uploadStep < 3) this.uploadStep = 3;
                }
            }, 200);
            
            try {
                const response = await fetch('/api/cv/upload', {
                    method: 'POST',
                    body: formData
                });
                
                if (!response.ok) {
                    const error = await response.json();
                    throw new Error(error.detail || 'Upload failed');
                }
                
                const result = await response.json();
                // Ensure cvData has all necessary properties including id
                this.cvData = {
                    ...result.data,
                    id: result.data.id || result.id || null  // Ensure id is always present
                };
                
                // Complete progress
                clearInterval(progressInterval);
                this.uploadProgress = 100;
                this.uploadStep = 3;
                
                setTimeout(() => {
                    this.uploadingCV = false;
                    this.uploadStep = 0;
                    this.uploadProgress = 0;
                    this.showNotification('CV uploaded and parsed successfully', 'success', 'Upload Successful');
                }, 500);
                
                // Load recent uploads after successful upload
                await this.loadRecentUploads();
            } catch (error) {
                console.error('Upload error:', error);
                clearInterval(progressInterval);
                this.uploadingCV = false;
                this.uploadStep = 0;
                this.uploadProgress = 0;
                this.showNotification(
                    error.message || 'Error uploading CV',
                    'error',
                    'Upload Failed'
                );
            } finally {
                event.target.value = '';
            }
        },
        
        async handleDrop(event) {
            this.dragover = false;
            const file = event.dataTransfer.files[0];
            if (file) {
                const fakeEvent = { target: { files: [file] } };
                await this.handleFileUpload(fakeEvent);
            }
        },
        
        selectJob(job) {
            this.selectedJob = job;
            this.showNotification(
                `Selected job: ${job.title || job.job_title}`,
                'info'
            );
        },
        
        clearJobSelection() {
            this.selectedJob = null;
            this.jobSearchQuery = '';
            this.filterJobs();
        },
        
        clearCV() {
            this.cvData = null;
            this.selectedJob = null;
            this.analysisResult = null;
            this.showDetailedResults = false;
            const uploadInput = document.getElementById('cv-upload');
            if (uploadInput) uploadInput.value = '';
        },
        
        async selectRecentUpload(upload) {
            this.loading = true;
            try {
                const response = await fetch(`/api/cv/${upload.id}`);
                if (!response.ok) throw new Error('Failed to load CV');
                
                const result = await response.json();
                
                // Based on CVRecord model, the parsed_data field contains the StructuredCV
                if (result.data && result.data.parsed_data) {
                    this.cvData = result.data.parsed_data;
                    // Ensure we keep the CV record ID for analysis
                    this.cvData.id = result.data.id || upload.id;
                } else if (result.parsed_data) {
                    this.cvData = result.parsed_data;
                    this.cvData.id = result.id || upload.id;
                } else {
                    // Fallback if API returns differently
                    this.cvData = result;
                    if (!this.cvData.id) {
                        this.cvData.id = upload.id;
                    }
                }
                
                this.showNotification('Previous CV loaded successfully', 'success');
                
                // Clear any existing job selection and analysis
                this.selectedJob = null;
                this.analysisResult = null;
                this.showDetailedResults = false;
                
            } catch (error) {
                console.error('Error loading CV:', error);
                this.showNotification('Failed to load previous CV', 'error');
            } finally {
                this.loading = false;
            }
        },
        
        toggleRecentUploads() {
            this.showRecentUploads = !this.showRecentUploads;
        },
        
        async startAnalysis() {
            if (!this.cvData || !this.selectedJob) {
                this.showNotification(
                    'Please upload a CV and select a job description',
                    'warning',
                    'Missing Information'
                );
                return;
            }
            
            // Additional check for CV ID
            if (!this.cvData.id) {
                this.showNotification(
                    'CV data is incomplete. Please re-upload your CV.',
                    'error',
                    'Invalid CV Data'
                );
                return;
            }
            
            this.analyzing = true;
            this.analysisStep = 0;
            this.analysisResult = null;
            this.showDetailedResults = false;
            
            this.showNotification('Starting CV analysis...', 'info');
            
            // Simulate progress steps
            const progressInterval = setInterval(() => {
                if (this.analysisStep < 4) {
                    this.analysisStep++;
                } else {
                    clearInterval(progressInterval);
                }
            }, 800);
            
            try {
                const response = await fetch('/api/analyze', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        cv_id: this.cvData.id,
                        job_id: this.selectedJob.id
                    })
                });
                
                if (!response.ok) {
                    const error = await response.json();
                    throw new Error(error.error || error.detail || 'Analysis failed');
                }
                
                const result = await response.json();
                this.analysisResult = result.data;
                this.showNotification(
                    'CV analysis completed successfully',
                    'success',
                    'Analysis Complete'
                );
                
                // Refresh recent analyses after successful analysis
                await this.loadRecentAnalyses();
            } catch (error) {
                console.error('Analysis error:', error);
                this.showNotification(
                    error.message || 'Error during analysis',
                    'error',
                    'Analysis Failed'
                );
            } finally {
                clearInterval(progressInterval);
                this.analyzing = false;
                this.analysisStep = 0;
            }
        },
        
        startNewAnalysis() {
            this.analysisResult = null;
            this.selectedJob = null;
            this.cvData = null;
            this.showDetailedResults = false;
            this.jobSearchQuery = '';
            this.filterJobs();
            const uploadInput = document.getElementById('cv-upload');
            if (uploadInput) uploadInput.value = '';
        },
        
        exportResults() {
            // TODO: Implement PDF export
            this.showNotification('Export feature coming soon', 'info', 'Feature Not Available');
        },
        
        formatDate(dateString) {
            if (!dateString) return 'Unknown date';
            try {
                return new Date(dateString).toLocaleDateString('en-US', {
                    year: 'numeric',
                    month: 'short',
                    day: 'numeric',
                    hour: '2-digit',
                    minute: '2-digit'
                });
            } catch (error) {
                return dateString;
            }
        },
        
        formatAdditionalDetails(details) {
            if (!details) return '';
            if (typeof details === 'string') {
                return details.replace(/\n/g, '<br>');
            }
            if (typeof details === 'object') {
                // Handle structured recommendations
                let html = '';
                if (details.strengths) {
                    html += '<h5 class="font-semibold mb-2">Strengths:</h5><ul class="list-disc pl-5 mb-4">';
                    details.strengths.forEach(item => {
                        html += `<li>${item}</li>`;
                    });
                    html += '</ul>';
                }
                if (details.areas_for_improvement) {
                    html += '<h5 class="font-semibold mb-2">Areas for Improvement:</h5><ul class="list-disc pl-5 mb-4">';
                    details.areas_for_improvement.forEach(item => {
                        html += `<li>${item}</li>`;
                    });
                    html += '</ul>';
                }
                if (details.recommendations) {
                    html += '<h5 class="font-semibold mb-2">Recommendations:</h5><ul class="list-disc pl-5">';
                    details.recommendations.forEach(item => {
                        html += `<li>${item}</li>`;
                    });
                    html += '</ul>';
                }
                return html || JSON.stringify(details, null, 2);
            }
            return JSON.stringify(details, null, 2);
        },
        
        // Helper method to show notifications safely
        showNotification(message, type = 'info', title = null) {
            // Check if window.showNotification is available
            if (typeof window.showNotification === 'function') {
                window.showNotification(message, type, title);
            } else {
                // Fallback to console logging if notification system isn't ready
                console.log(`[${type.toUpperCase()}] ${title || ''}: ${message}`);
                
                // Try again after a short delay
                setTimeout(() => {
                    if (typeof window.showNotification === 'function') {
                        window.showNotification(message, type, title);
                    }
                }, 100);
            }
        },
        
        async viewPreviousAnalysis(analysisId) {
            this.loading = true;
            this.showNotification('Loading previous analysis...', 'info');
            
            try {
                // First check if we have the analysis in our recent analyses cache
                const cachedAnalysis = this.recentAnalyses.find(a => a.id === analysisId);
                let analysisRecord;
                
                if (cachedAnalysis && cachedAnalysis._fullRecord) {
                    // Use cached data if available
                    analysisRecord = cachedAnalysis._fullRecord;
                } else {
                    // Otherwise fetch from API
                    const response = await fetch(`/api/analyses/${analysisId}`);
                    if (!response.ok) throw new Error('Failed to load analysis');
                    
                    const result = await response.json();
                    analysisRecord = result.data || result;
                }
                
                // Extract and set the analysis result from analysis_data field
                if (analysisRecord.analysis_data) {
                    this.analysisResult = analysisRecord.analysis_data;
                    
                    // Ensure the analysis result has all expected fields
                    this.analysisResult = {
                        suitability_score: this.analysisResult.suitability_score || 0,
                        technical_score: this.analysisResult.technical_score || 0,
                        experience_score: this.analysisResult.experience_score || 0,
                        education_score: this.analysisResult.education_score || 0,
                        scoring_rationale: this.analysisResult.scoring_rationale || '',
                        matching_skills: this.analysisResult.matching_skills || [],
                        missing_skills: this.analysisResult.missing_skills || [],
                        recommendations: this.analysisResult.recommendations || [],
                        red_flags: this.analysisResult.red_flags || [],
                        detailed_analysis: this.analysisResult.detailed_analysis || null,
                        analysis_date: analysisRecord.analysis_date || analysisRecord.created_at,
                        ...this.analysisResult
                    };
                } else {
                    // Fallback if the structure is different
                    this.analysisResult = analysisRecord;
                }
                
                // Load the CV data - check if it's embedded in the analysis record first
                if (analysisRecord.cv_record) {
                    const cvRecord = analysisRecord.cv_record;
                    if (cvRecord.parsed_data) {
                        this.cvData = {
                            ...cvRecord.parsed_data,
                            id: cvRecord.id || analysisRecord.cv_record_id
                        };
                    } else {
                        // If parsed_data is not available, try to fetch it
                        if (analysisRecord.cv_record_id) {
                            await this.loadCVData(analysisRecord.cv_record_id);
                        }
                    }
                } else if (analysisRecord.cv_record_id) {
                    // If we only have cv_id, fetch the CV data
                    await this.loadCVData(analysisRecord.cv_record_id);
                }
                
                // Load the job data - check if it's embedded in the analysis record first
                if (analysisRecord.job_description) {
                    const jobRecord = analysisRecord.job_description;
                    if (jobRecord.job_data) {
                        this.selectedJob = {
                            id: jobRecord.id || analysisRecord.job_description_id,
                            title: jobRecord.job_data.job_title,
                            company: jobRecord.job_data.company,
                            location: jobRecord.job_data.location,
                            experience_level: jobRecord.job_data.experience_level,
                            required_skills: jobRecord.job_data.required_skills || [],
                            ...jobRecord.job_data
                        };
                    } else {
                        // Use the job record directly
                        this.selectedJob = {
                            id: jobRecord.id,
                            title: jobRecord.job_title,
                            company: jobRecord.company,
                            ...jobRecord
                        };
                    }
                } else if (analysisRecord.job_description_id) {
                    // If we only have job_id, fetch the job data
                    await this.loadJobData(analysisRecord.job_description_id);
                }
                
                // Don't automatically show detailed results - let user stay on the summary
                this.showDetailedResults = false;
                
                this.showNotification('Previous analysis loaded successfully', 'success');
                
            } catch (error) {
                console.error('Error loading analysis:', error);
                this.showNotification('Failed to load previous analysis', 'error');
            } finally {
                this.loading = false;
            }
        },
        
        // Helper method to load CV data
        async loadCVData(cvId) {
            try {
                const response = await fetch(`/api/cv/${cvId}`);
                if (response.ok) {
                    const result = await response.json();
                    const cvRecord = result.data || result;
                    
                    if (cvRecord.parsed_data) {
                        this.cvData = {
                            ...cvRecord.parsed_data,
                            id: cvRecord.id || cvId
                        };
                    } else {
                        // Fallback if structure is different
                        this.cvData = {
                            ...cvRecord,
                            id: cvRecord.id || cvId
                        };
                    }
                }
            } catch (error) {
                console.error('Error loading CV data:', error);
            }
        },
        
        // Helper method to load job data
        async loadJobData(jobId) {
            try {
                const jobResponse = await fetch(`/api/jobs/${jobId}`);
                if (jobResponse.ok) {
                    const jobResult = await jobResponse.json();
                    const jobRecord = jobResult.data || jobResult;
                    
                    if (jobRecord.job_data) {
                        this.selectedJob = {
                            id: jobRecord.id || jobId,
                            title: jobRecord.job_data.job_title,
                            company: jobRecord.job_data.company,
                            location: jobRecord.job_data.location,
                            experience_level: jobRecord.job_data.experience_level,
                            required_skills: jobRecord.job_data.required_skills || [],
                            ...jobRecord.job_data
                        };
                    } else {
                        this.selectedJob = {
                            id: jobRecord.id || jobId,
                            title: jobRecord.job_title,
                            company: jobRecord.company,
                            ...jobRecord
                        };
                    }
                }
            } catch (error) {
                console.error('Error loading job data:', error);
            }
        },
        
        async showAllRecentCVs() {
            this.showRecentCVsModal = true;
            this.loadingAllCVs = true;
            
            try {
                const response = await fetch('/api/cv/recent?limit=25');
                if (!response.ok) throw new Error('Failed to load CVs');
                
                const result = await response.json();
                this.allRecentCVs = (result.data || []).map(cv => {
                    if (cv.file_upload) {
                        return {
                            id: cv.id,
                            filename: cv.file_upload.original_filename || cv.file_upload.filename,
                            upload_date: cv.parsed_date || cv.file_upload.upload_date,
                            contact_name: cv.contact_name,
                            contact_email: cv.contact_email,
                            file_size: cv.file_upload.file_size
                        };
                    }
                    return {
                        id: cv.id,
                        filename: cv.filename || cv.original_filename || 'Unknown',
                        upload_date: cv.upload_date || cv.parsed_date || cv.created_at,
                        contact_name: cv.contact_name,
                        contact_email: cv.contact_email,
                        file_size: cv.file_size
                    };
                });
                
                this.filteredRecentCVs = this.allRecentCVs;
            } catch (error) {
                console.error('Error loading all CVs:', error);
                this.showNotification('Failed to load CVs', 'error');
            } finally {
                this.loadingAllCVs = false;
            }
        },
        
        filterRecentCVs() {
            if (!this.recentCVsSearch.trim()) {
                this.filteredRecentCVs = this.allRecentCVs;
                return;
            }
            
            const search = this.recentCVsSearch.toLowerCase();
            this.filteredRecentCVs = this.allRecentCVs.filter(cv => 
                cv.filename.toLowerCase().includes(search) ||
                (cv.contact_name && cv.contact_name.toLowerCase().includes(search)) ||
                (cv.contact_email && cv.contact_email.toLowerCase().includes(search))
            );
        },
        
        async showAllRecentAnalyses() {
            this.showRecentAnalysesModal = true;
            this.loadingAllAnalyses = true;
            
            try {
                const response = await fetch('/api/analyses/recent?limit=25');
                if (!response.ok) throw new Error('Failed to load analyses');
                
                const result = await response.json();
                this.allAnalyses = (result.data || []).map(analysis => {
                    const analysisData = analysis.analysis_data || {};
                    const cvRecord = analysis.cv_record || {};
                    const jobRecord = analysis.job_description || {};
                    
                    let jobTitle = 'Unknown Job';
                    let company = 'Unknown Company';
                    if (jobRecord.job_data) {
                        jobTitle = jobRecord.job_data.job_title || jobRecord.job_title || jobTitle;
                        company = jobRecord.job_data.company || jobRecord.company || company;
                    } else {
                        jobTitle = jobRecord.job_title || jobTitle;
                        company = jobRecord.company || company;
                    }
                    
                    let cvName = 'Unknown CV';
                    if (cvRecord.file_upload && cvRecord.file_upload.original_filename) {
                        cvName = cvRecord.file_upload.original_filename;
                    } else if (cvRecord.contact_name) {
                        cvName = cvRecord.contact_name;
                    } else if (cvRecord.parsed_data && cvRecord.parsed_data.contact_info && cvRecord.parsed_data.contact_info.name) {
                        cvName = cvRecord.parsed_data.contact_info.name;
                    }
                    
                    return {
                        id: analysis.id,
                        job_title: jobTitle,
                        company: company,
                        cv_name: cvName,
                        score: analysisData.suitability_score || analysis.suitability_score || 0,
                        technical_score: analysisData.technical_score || 0,
                        experience_score: analysisData.experience_score || 0,
                        education_score: analysisData.education_score || 0,
                        analysis_date: analysis.analysis_date || analysis.created_at || new Date().toISOString(),
                        _fullRecord: analysis
                    };
                });
                
                this.filteredAnalyses = this.allAnalyses;
                this.sortAnalyses();
            } catch (error) {
                console.error('Error loading all analyses:', error);
                this.showNotification('Failed to load analyses', 'error');
            } finally {
                this.loadingAllAnalyses = false;
            }
        },
        
        filterAnalyses() {
            let filtered = this.allAnalyses;
            
            // Search filter
            if (this.analysesSearch.trim()) {
                const search = this.analysesSearch.toLowerCase();
                filtered = filtered.filter(analysis => 
                    analysis.job_title.toLowerCase().includes(search) ||
                    analysis.company.toLowerCase().includes(search) ||
                    analysis.cv_name.toLowerCase().includes(search)
                );
            }
            
            // Score filter
            if (this.analysesScoreFilter) {
                switch (this.analysesScoreFilter) {
                    case 'high':
                        filtered = filtered.filter(a => a.score >= 70);
                        break;
                    case 'medium':
                        filtered = filtered.filter(a => a.score >= 50 && a.score < 70);
                        break;
                    case 'low':
                        filtered = filtered.filter(a => a.score < 50);
                        break;
                }
            }
            
            this.filteredAnalyses = filtered;
            this.sortAnalyses();
        },
        
        sortAnalyses() {
            switch (this.analysesSortBy) {
                case 'score':
                    this.filteredAnalyses.sort((a, b) => b.score - a.score);
                    break;
                case 'job':
                    this.filteredAnalyses.sort((a, b) => a.job_title.localeCompare(b.job_title));
                    break;
                case 'date':
                default:
                    this.filteredAnalyses.sort((a, b) => new Date(b.analysis_date) - new Date(a.analysis_date));
                    break;
            }
        },
        
        formatFileSize(bytes) {
            if (!bytes) return 'Unknown';
            const sizes = ['Bytes', 'KB', 'MB', 'GB'];
            if (bytes === 0) return '0 Bytes';
            const i = Math.floor(Math.log(bytes) / Math.log(1024));
            return Math.round(bytes / Math.pow(1024, i) * 100) / 100 + ' ' + sizes[i];
        },
        
        // ...existing code...
    };
}