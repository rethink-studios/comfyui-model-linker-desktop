/**
 * ComfyUI Model Linker Extension - Desktop Compatible
 */

// Import ComfyUI APIs - these paths are relative to the ComfyUI web directory
// For ComfyUI Desktop, the web root is C:\ComfyUI\resources\ComfyUI\web_custom_versions\desktop_app
// So, scripts/app.js is at ../../../scripts/app.js
// And api.js is at ../../../scripts/api.js
import { app } from "../../../scripts/app.js";
import { api } from "../../../scripts/api.js";

console.log("🔗 Model Linker: JavaScript loading...");

// Simple dialog class for Model Linker
class ModelLinkerDialog {
    constructor() {
        this.element = null;
        this.contentElement = null;
        this.createDialog();
    }
    
    createDialog() {
        // Create modal backdrop
        this.element = document.createElement('div');
        this.element.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.8);
            z-index: 99999;
            display: none;
            align-items: center;
            justify-content: center;
        `;
        
        // Create dialog container
        const dialog = document.createElement('div');
        dialog.style.cssText = `
            background: #202020;
            color: #ffffff;
            border: 2px solid #555555;
            border-radius: 8px;
            width: 900px;
            height: 700px;
            max-width: 95vw;
            max-height: 95vh;
            display: flex;
            flex-direction: column;
            box-shadow: 0 4px 20px rgba(0,0,0,0.8);
        `;
        
        // Header
        const header = document.createElement('div');
        header.style.cssText = `
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 20px;
            border-bottom: 1px solid #555555;
        `;
        
        const title = document.createElement('h2');
        title.textContent = '🔗 Model Linker';
        title.style.cssText = 'margin: 0; font-size: 18px; font-weight: 600;';
        
        const closeBtn = document.createElement('button');
        closeBtn.textContent = '×';
        closeBtn.style.cssText = `
            background: none;
            border: none;
            font-size: 24px;
            cursor: pointer;
            color: #ffffff;
            padding: 0;
            width: 30px;
            height: 30px;
            border-radius: 4px;
            display: flex;
            align-items: center;
            justify-content: center;
        `;
        closeBtn.onclick = () => this.close();
        
        header.appendChild(title);
        header.appendChild(closeBtn);
        
        // Content area
        this.contentElement = document.createElement('div');
        this.contentElement.style.cssText = `
            padding: 16px;
            overflow-y: auto;
            flex: 1;
            min-height: 0;
        `;
        
        // Footer
        const footer = document.createElement('div');
        footer.style.cssText = `
            padding: 16px;
            border-top: 1px solid #555555;
            display: flex;
            justify-content: flex-end;
            gap: 8px;
        `;
        
        const autoResolveBtn = document.createElement('button');
        autoResolveBtn.textContent = 'Auto-Resolve 100% Matches';
        autoResolveBtn.style.cssText = `
            background: #007acc;
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 4px;
            cursor: pointer;
        `;
        autoResolveBtn.onclick = () => this.autoResolve100Percent();
        
        footer.appendChild(autoResolveBtn);
        
        // Assemble dialog
        dialog.appendChild(header);
        dialog.appendChild(this.contentElement);
        dialog.appendChild(footer);
        this.element.appendChild(dialog);
        
        // Add to page
        document.body.appendChild(this.element);
    }
    
    show() {
        this.element.style.display = 'flex';
        this.loadWorkflowData();
    }
    
    close() {
        this.element.style.display = 'none';
    }
    
    async loadWorkflowData() {
        this.contentElement.innerHTML = '<p>Analyzing workflow...</p>';
        
        try {
            // Get current workflow - try multiple methods
            let workflow = null;
            
            // Method 1: Try to get from global app object
            if (window.app && window.app.graph) {
                try {
                    workflow = window.app.graph.serialize();
                    console.log("🔗 Got workflow from app.graph.serialize()");
                } catch (e) {
                    console.log("🔗 app.graph.serialize() failed:", e);
                }
            }
            
            if (!workflow) {
                this.contentElement.innerHTML = '<p style="color: orange;">No workflow loaded. Please load a workflow first.</p>';
                return;
            }
            
            console.log("🔗 Analyzing workflow with", Object.keys(workflow).length, "nodes");
            
            // Call analyze endpoint - routes are at root level, not under /api
            // So we use direct fetch with api.api_base
            const analyzeUrl = `${api.api_base}/model_linker/analyze`;
            console.log("🔗 Calling analyze endpoint:", analyzeUrl);
            const response = await fetch(analyzeUrl, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ workflow })
            });
            
            if (!response.ok) {
                throw new Error(`API error: ${response.status}`);
            }
            
            const data = await response.json();
            console.log("🔗 Analysis result:", data);
            
            // Debug: Show what we found
            if (data.missing_models) {
                data.missing_models.forEach(missing => {
                    console.log(`🔗 Missing: ${missing.original_path}`);
                    console.log(`🔗 Category: ${missing.category}`);
                    console.log(`🔗 Matches found: ${missing.matches ? missing.matches.length : 0}`);
                    if (missing.matches) {
                        missing.matches.forEach(match => {
                            console.log(`  - ${match.model?.relative_path || match.filename} (${match.confidence}%)`);
                        });
                    }
                });
            }
            
            this.displayResults(data);
            
        } catch (error) {
            console.error('🔗 Model Linker error:', error);
            this.contentElement.innerHTML = `<p style="color: red;">Error: ${error.message}</p>`;
        }
    }
    
    displayResults(data) {
        const missingModels = data.missing_models || [];
        const totalMissing = data.total_missing || 0;
        
        if (totalMissing === 0) {
            this.contentElement.innerHTML = '<p style="color: green;">✓ No missing models found. All models are available!</p>';
            return;
        }
        
        let html = `<p><strong>Found ${totalMissing} missing model(s):</strong></p>`;
        html += '<div style="display: flex; flex-direction: column; gap: 16px;">';
        
        for (const missing of missingModels) {
            html += this.renderMissingModel(missing);
        }
        
        html += '</div>';
        this.contentElement.innerHTML = html;
        
        // Add event listeners for resolve buttons
        missingModels.forEach((missing, missingIndex) => {
            const matches = missing.matches || [];
            
            // Add listeners for high confidence (90-99%) matches
            const highConfidenceMatches = matches.filter(m => m.confidence >= 90 && m.confidence < 100)
                .sort((a, b) => b.confidence - a.confidence)
                .slice(0, 3);
            
            highConfidenceMatches.forEach((match, matchIndex) => {
                const buttonId = `resolve-${missing.node_id}-${missing.widget_index || 0}-high-${matchIndex}`;
                const button = this.contentElement.querySelector(`#${buttonId}`);
                if (button) {
                    button.onclick = () => this.resolveModel(missing, match.model);
                }
            });
            
            // Add listeners for medium confidence (70-89%) matches - radio button selection
            const mediumConfidenceMatches = matches.filter(m => m.confidence >= 70 && m.confidence < 90)
                .sort((a, b) => b.confidence - a.confidence)
                .slice(0, 3);
            
            if (mediumConfidenceMatches.length > 0) {
                const resolveButtonId = `resolve-medium-${missing.node_id}-${missing.widget_index || 0}`;
                const resolveButton = this.contentElement.querySelector(`#${resolveButtonId}`);
                
                if (resolveButton) {
                    resolveButton.onclick = () => {
                        // Find which radio button is selected
                        const radioGroupName = `medium-match-${missing.node_id}-${missing.widget_index || 0}`;
                        const selectedRadio = this.contentElement.querySelector(`input[name="${radioGroupName}"]:checked`);
                        
                        if (selectedRadio) {
                            const selectedIndex = parseInt(selectedRadio.value);
                            const selectedMatch = mediumConfidenceMatches[selectedIndex];
                            this.resolveModel(missing, selectedMatch.model);
                        } else {
                            alert('Please select a model first');
                        }
                    };
                }
            }
            
            // Add listeners for download buttons (< 70% confidence - no good matches)
            if (matches.length === 0 || matches.every(m => m.confidence < 70)) {
                const downloadBtnId = `download-${missing.node_id}-${missing.widget_index || 0}`;
                const urlInputId = `url-input-${missing.node_id}-${missing.widget_index || 0}`;
                const cancelBtnId = `cancel-${missing.node_id}-${missing.widget_index || 0}`;
                
                const downloadBtn = this.contentElement.querySelector(`#${downloadBtnId}`);
                const urlInput = this.contentElement.querySelector(`#${urlInputId}`);
                const cancelBtn = this.contentElement.querySelector(`#${cancelBtnId}`);
                
                if (downloadBtn && urlInput) {
                    downloadBtn.onclick = () => this.downloadModel(missing, urlInput.value);
                }
                
                if (cancelBtn) {
                    cancelBtn.onclick = () => this.cancelDownload(missing);
                }
            }
        });
    }
    
    renderMissingModel(missing) {
        const matches = missing.matches || [];
        
        // Separate matches by confidence level
        const perfectMatches = matches.filter(m => m.confidence === 100);
        const highConfidenceMatches = matches.filter(m => m.confidence >= 90 && m.confidence < 100);
        const mediumConfidenceMatches = matches.filter(m => m.confidence >= 70 && m.confidence < 90);
        const lowConfidenceMatches = matches.filter(m => m.confidence >= 50 && m.confidence < 70);
        
        let html = `<div style="border: 1px solid #444; padding: 12px; border-radius: 4px; margin-bottom: 12px;">`;
        html += `<div style="margin-bottom: 8px;"><strong>Node:</strong> ${missing.node_type} (ID: ${missing.node_id})</div>`;
        html += `<div style="margin-bottom: 8px;"><strong>Missing Model:</strong> <code style="background: #333; padding: 2px 6px; border-radius: 3px;">${missing.original_path}</code></div>`;
        html += `<div style="margin-bottom: 8px;"><strong>Category:</strong> ${missing.category || 'unknown'}</div>`;

        // Show matches based on confidence levels
        if (perfectMatches.length > 0) {
            // Perfect matches - will be auto-resolved
            html += `<div style="margin-top: 12px;"><strong>🟢 Perfect Match (Auto-Resolve):</strong></div>`;
            html += '<ul style="margin: 8px 0; padding-left: 20px; list-style: none;">';
            const match = perfectMatches[0];
            html += `<li style="margin: 4px 0; color: #4CAF50;">`;
            html += `✓ <code>${match.model?.relative_path || match.filename}</code> `;
            html += `<span style="color: #4CAF50; font-weight: 600;">(100% match)</span>`;
            html += `</li>`;
            html += '</ul>';
            
        } else if (highConfidenceMatches.length > 0) {
            // High confidence matches (90-99%) - show top 2-3 with resolve buttons
            html += `<div style="margin-top: 12px;"><strong>🟡 High Confidence Matches (Select One):</strong></div>`;
            html += `<div style="background: #2a2a2a; padding: 8px; border-radius: 4px; margin-top: 8px;">`;
            
            const topMatches = highConfidenceMatches.sort((a, b) => b.confidence - a.confidence).slice(0, 3);
            
            for (let matchIndex = 0; matchIndex < topMatches.length; matchIndex++) {
                const match = topMatches[matchIndex];
                const buttonId = `resolve-${missing.node_id}-${missing.widget_index || 0}-high-${matchIndex}`;
                
                html += `<div style="display: flex; align-items: center; justify-content: space-between; padding: 8px; margin: 4px 0; background: #353535; border-radius: 4px; border-left: 3px solid #FFA726;">`;
                html += `<div style="flex: 1;">`;
                html += `<code style="font-size: 13px;">${match.model?.relative_path || match.filename}</code><br>`;
                html += `<span style="color: #FFA726; font-size: 12px; font-weight: 600;">${match.confidence}% confidence</span>`;
                html += `</div>`;
                html += `<button id="${buttonId}" class="model-linker-resolve-btn" 
                    style="margin-left: 12px; padding: 6px 12px; background: #FFA726; color: #000; border: none; border-radius: 4px; cursor: pointer; font-weight: 600; white-space: nowrap;">
                    Resolve
                </button>`;
                html += `</div>`;
            }
            html += '</div>';
            
        } else if (mediumConfidenceMatches.length > 0) {
            // Medium confidence matches (70-89%) - show with radio buttons for user selection
            html += `<div style="margin-top: 12px;"><strong>⚪ Possible Matches (Select One):</strong></div>`;
            html += `<div style="background: #2a2a2a; padding: 8px; border-radius: 4px; margin-top: 8px;">`;
            html += `<div style="color: #FFA500; font-size: 11px; margin-bottom: 8px;">⚠️ Lower confidence - verify before resolving</div>`;
            
            const topMatches = mediumConfidenceMatches.sort((a, b) => b.confidence - a.confidence).slice(0, 3);
            const radioGroupName = `medium-match-${missing.node_id}-${missing.widget_index || 0}`;
            
            for (let matchIndex = 0; matchIndex < topMatches.length; matchIndex++) {
                const match = topMatches[matchIndex];
                const radioId = `radio-${missing.node_id}-${missing.widget_index || 0}-medium-${matchIndex}`;
                
                html += `<div style="display: flex; align-items: center; padding: 6px; margin: 4px 0; background: #353535; border-radius: 4px; border-left: 3px solid #999;">`;
                html += `<input type="radio" name="${radioGroupName}" id="${radioId}" value="${matchIndex}" style="margin-right: 8px; cursor: pointer;">`;
                html += `<label for="${radioId}" style="flex: 1; cursor: pointer; font-size: 13px;">`;
                html += `<code style="color: #ddd;">${match.model?.relative_path || match.filename}</code><br>`;
                html += `<span style="color: #999; font-size: 11px;">${match.confidence}% confidence</span>`;
                html += `</label>`;
                html += `</div>`;
            }
            
            const resolveButtonId = `resolve-medium-${missing.node_id}-${missing.widget_index || 0}`;
            html += `<button id="${resolveButtonId}" class="model-linker-resolve-medium-btn" 
                style="margin-top: 8px; padding: 6px 12px; background: #666; color: #fff; border: none; border-radius: 4px; cursor: pointer; width: 100%; font-weight: 600;">
                Resolve Selected
            </button>`;
            html += '</div>';
            
        } else {
            // No good matches (< 70% or no matches) - show download/search options
            const hasLowMatches = lowConfidenceMatches.length > 0;
            
            html += `<div style="margin-top: 12px;">`;
            html += `<strong style="color: #f44336;">❌ No Good Matches Found</strong>`;
            html += `<div style="background: #2a2a2a; padding: 12px; border-radius: 4px; margin-top: 8px; border-left: 3px solid #f44336;">`;
            
            if (hasLowMatches) {
                html += `<div style="color: #999; font-size: 12px; margin-bottom: 8px;">Found ${lowConfidenceMatches.length} low confidence match(es) (< 70%), but they're not recommended.</div>`;
            }
            
            html += `<div style="color: #ddd; margin-bottom: 12px;">`;
            html += `<strong>Missing:</strong> <code style="background: #333; padding: 2px 6px; border-radius: 3px;">${missing.original_path}</code>`;
            html += `</div>`;
            
            // Download/Search options
            html += `<div style="display: flex; gap: 8px; flex-wrap: wrap;">`;
            
            // Search on CivitAI button
            const civitSearchUrl = `https://civitai.com/search/models?query=${encodeURIComponent(missing.original_path.replace(/\.[^/.]+$/, ''))}`;
            html += `<a href="${civitSearchUrl}" target="_blank" style="text-decoration: none;">`;
            html += `<button style="padding: 8px 16px; background: #4CAF50; color: white; border: none; border-radius: 4px; cursor: pointer; font-weight: 600;">`;
            html += `🔍 Search CivitAI`;
            html += `</button>`;
            html += `</a>`;
            
            // Search on HuggingFace button
            const hfSearchUrl = `https://huggingface.co/models?search=${encodeURIComponent(missing.original_path.replace(/\.[^/.]+$/, ''))}`;
            html += `<a href="${hfSearchUrl}" target="_blank" style="text-decoration: none;">`;
            html += `<button style="padding: 8px 16px; background: #FF9800; color: white; border: none; border-radius: 4px; cursor: pointer; font-weight: 600;">`;
            html += `🤗 Search HuggingFace`;
            html += `</button>`;
            html += `</a>`;
            
            // Direct download button with URL input
            const downloadBtnId = `download-${missing.node_id}-${missing.widget_index || 0}`;
            const urlInputId = `url-input-${missing.node_id}-${missing.widget_index || 0}`;
            html += `<div style="display: flex; gap: 4px; flex: 1; min-width: 300px;">`;
            html += `<input id="${urlInputId}" type="text" placeholder="Paste download URL..." style="flex: 1; padding: 8px; background: #1a1a1a; color: #ddd; border: 1px solid #444; border-radius: 4px;">`;
            html += `<button id="${downloadBtnId}" class="download-btn" style="padding: 8px 16px; background: #2196F3; color: white; border: none; border-radius: 4px; cursor: pointer; font-weight: 600; white-space: nowrap;">`;
            html += `⬇️ Download`;
            html += `</button>`;
            html += `</div>`;
            
            html += `</div>`;
            
            // Progress bar placeholder (hidden initially)
            const progressId = `progress-${missing.node_id}-${missing.widget_index || 0}`;
            const cancelBtnId = `cancel-${missing.node_id}-${missing.widget_index || 0}`;
            html += `<div id="${progressId}" style="display: none; margin-top: 12px;">`;
            html += `<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">`;
            html += `<span style="color: #2196F3; font-size: 12px;">Downloading...</span>`;
            html += `<button id="${cancelBtnId}" style="padding: 4px 8px; background: #f44336; color: white; border: none; border-radius: 3px; cursor: pointer; font-size: 11px; font-weight: 600;">Cancel</button>`;
            html += `</div>`;
            html += `<div style="background: #1a1a1a; border-radius: 4px; overflow: hidden; height: 20px;">`;
            html += `<div class="download-progress-bar" style="background: linear-gradient(90deg, #2196F3, #21CBF3); height: 100%; width: 0%; transition: width 0.3s;"></div>`;
            html += `</div>`;
            html += `<div class="download-progress-text" style="color: #999; font-size: 11px; margin-top: 4px;">0% - 0 MB / 0 MB</div>`;
            html += `</div>`;
            
            html += `</div>`;
            html += `</div>`;
        }

        html += '</div>';
        return html;
    }
    
    updateDownloadProgress(nodeId, widgetIndex, progress) {
        const progressId = `progress-${nodeId}-${widgetIndex || 0}`;
        const progressContainer = this.contentElement.querySelector(`#${progressId}`);
        
        if (!progressContainer) return;
        
        // Show progress container
        progressContainer.style.display = 'block';
        
        // Update progress bar
        const progressBar = progressContainer.querySelector('.download-progress-bar');
        const progressText = progressContainer.querySelector('.download-progress-text');
        
        if (progressBar) {
            progressBar.style.width = `${progress.percent}%`;
        }
        
        if (progressText) {
            const downloadedMB = (progress.downloaded / 1024 / 1024).toFixed(2);
            const totalMB = (progress.total / 1024 / 1024).toFixed(2);
            progressText.textContent = `${progress.percent}% - ${downloadedMB} MB / ${totalMB} MB`;
        }
    }
    
    async resolveModel(missing, resolvedModel) {
        console.log("🔗 Resolving model:", missing, resolvedModel);
        
        try {
            // Get current workflow
            const workflow = this.getCurrentWorkflow();
            if (!workflow) {
                alert('No workflow loaded');
                return;
            }
            
            // Prepare resolution data
            const resolution = {
                node_id: missing.node_id,
                widget_index: missing.widget_index !== undefined ? missing.widget_index : missing.field_name,
                resolved_path: resolvedModel.relative_path || resolvedModel.filename,
                category: missing.category,
                resolved_model: resolvedModel
            };
            
            console.log("🔗 Sending resolution:", resolution);
            
            // Call resolve endpoint - routes are at root level
            const resolveUrl = `${api.api_base}/model_linker/resolve`;
            console.log("🔗 Calling resolve endpoint:", resolveUrl);
            const response = await fetch(resolveUrl, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    workflow: workflow,
                    resolutions: [resolution]
                })
            });
            
            if (!response.ok) {
                throw new Error(`API error: ${response.status}`);
            }
            
            const data = await response.json();
            console.log("🔗 Resolve response:", data);
            console.log("🔗 Resolve success:", data.success);
            console.log("🔗 Updated workflow from backend:", data.workflow);
            console.log("🔗 Updated workflow keys:", data.workflow ? Object.keys(data.workflow) : 'none');
            
            if (data.success) {
                console.log("🔗 About to update workflow in ComfyUI...");
                // Update workflow in ComfyUI
                await this.updateWorkflowInComfyUI(data.workflow);
                console.log("🔗 updateWorkflowInComfyUI() completed");
                
                // Force a UI refresh
                setTimeout(() => {
                    if (window.app && window.app.graph && window.app.graph.setDirtyCanvas) {
                        window.app.graph.setDirtyCanvas(true, true);
                    }
                }, 100);
                
                // Show success message
                alert(`✓ Model resolved successfully!\n${missing.original_path} → ${resolvedModel.relative_path || resolvedModel.filename}`);
                
                // Reload dialog to show updated status
                this.loadWorkflowData();
            } else {
                alert('Failed to resolve model: ' + (data.error || 'Unknown error'));
            }
            
        } catch (error) {
            console.error('🔗 Resolve error:', error);
            alert('Error resolving model: ' + error.message);
        }
    }
    
    async downloadModel(missing, url) {
        console.log("⬇️ Downloading model:", missing, url);
        
        if (!url || url.trim() === '') {
            alert('Please enter a download URL');
            return;
        }
        
        try {
            // Generate download ID
            const downloadId = `dl-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
            
            // Start download
            const downloadUrl = `${api.api_base}/model_linker/download`;
            const response = await fetch(downloadUrl, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    url: url.trim(),
                    category: missing.category || 'checkpoints',
                    filename: missing.original_path,
                    download_id: downloadId
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                // Store download ID for this missing model
                missing._downloadId = downloadId;
                
                // Start polling for progress
                this.pollDownloadProgress(missing);
                
                console.log("⬇️ Download started:", data);
            } else {
                alert('Failed to start download: ' + (data.error || 'Unknown error'));
            }
            
        } catch (error) {
            console.error('⬇️ Download error:', error);
            alert('Error starting download: ' + error.message);
        }
    }
    
    async cancelDownload(missing) {
        if (!missing._downloadId) {
            return;
        }
        
        try {
            const cancelUrl = `${api.api_base}/model_linker/download/${missing._downloadId}/cancel`;
            const response = await fetch(cancelUrl, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });
            
            const data = await response.json();
            
            if (data.success) {
                console.log("⬇️ Download cancelled");
                
                // Stop polling
                if (missing._pollInterval) {
                    clearInterval(missing._pollInterval);
                    missing._pollInterval = null;
                }
                
                // Hide progress bar
                const progressId = `progress-${missing.node_id}-${missing.widget_index || 0}`;
                const progressContainer = this.contentElement.querySelector(`#${progressId}`);
                if (progressContainer) {
                    progressContainer.style.display = 'none';
                }
                
                alert('Download cancelled');
            }
            
        } catch (error) {
            console.error('⬇️ Cancel error:', error);
            alert('Error cancelling download: ' + error.message);
        }
    }
    
    async pollDownloadProgress(missing) {
        if (!missing._downloadId) {
            return;
        }
        
        // Poll every 500ms
        missing._pollInterval = setInterval(async () => {
            try {
                const progressUrl = `${api.api_base}/model_linker/download/${missing._downloadId}/progress`;
                const response = await fetch(progressUrl);
                const data = await response.json();
                
                if (data.status === 'downloading') {
                    // Update progress bar
                    this.updateDownloadProgress(missing.node_id, missing.widget_index, data.progress);
                } else if (data.status === 'completed') {
                    // Stop polling
                    clearInterval(missing._pollInterval);
                    missing._pollInterval = null;
                    
                    // Update progress to 100%
                    this.updateDownloadProgress(missing.node_id, missing.widget_index, {
                        downloaded: data.result.size,
                        total: data.result.size,
                        percent: 100
                    });
                    
                    // Show success message
                    alert(`✓ Model downloaded successfully!\n${data.result.path}`);
                    
                    // Reload dialog to show updated status
                    this.loadWorkflowData();
                } else if (data.status === 'failed') {
                    // Stop polling
                    clearInterval(missing._pollInterval);
                    missing._pollInterval = null;
                    
                    alert('Download failed: ' + (data.error || 'Unknown error'));
                }
                
            } catch (error) {
                console.error('⬇️ Progress poll error:', error);
                // Don't alert on every poll error, just log it
            }
        }, 500);
    }
    
    async autoResolve100Percent() {
        console.log("🔗 Auto-resolving 100% matches");
        
        try {
            // Get current workflow
            const workflow = this.getCurrentWorkflow();
            if (!workflow) {
                alert('No workflow loaded');
                return;
            }
            
            // Analyze workflow to find 100% matches - routes are at root level
            const analyzeUrl = `${api.api_base}/model_linker/analyze`;
            console.log("🔗 Calling analyze endpoint for auto-resolve:", analyzeUrl);
            const analyzeResponse = await fetch(analyzeUrl, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ workflow })
            });
            
            if (!analyzeResponse.ok) {
                throw new Error(`Analyze API error: ${analyzeResponse.status}`);
            }
            
            const analyzeData = await analyzeResponse.json();
            const missingModels = analyzeData.missing_models || [];
            
            // Collect all 100% matches
            const resolutions = [];
            for (const missing of missingModels) {
                const matches = missing.matches || [];
                const perfectMatch = matches.find(m => m.confidence === 100);
                
                if (perfectMatch && perfectMatch.model) {
                    resolutions.push({
                        node_id: missing.node_id,
                        widget_index: missing.widget_index !== undefined ? missing.widget_index : missing.field_name,
                        resolved_path: perfectMatch.model.relative_path || perfectMatch.model.filename,
                        category: missing.category,
                        resolved_model: perfectMatch.model
                    });
                }
            }
            
            if (resolutions.length === 0) {
                alert('No 100% confidence matches found to auto-resolve.');
                return;
            }
            
            console.log("🔗 Auto-resolving:", resolutions);
            
            // Apply all resolutions - routes are at root level
            const resolveUrl = `${api.api_base}/model_linker/resolve`;
            console.log("🔗 Calling resolve endpoint for auto-resolve:", resolveUrl);
            const resolveResponse = await fetch(resolveUrl, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    workflow: workflow,
                    resolutions: resolutions
                })
            });
            
            if (!resolveResponse.ok) {
                throw new Error(`Resolve API error: ${resolveResponse.status}`);
            }
            
            const resolveData = await resolveResponse.json();
            console.log("🔗 Auto-resolve response:", resolveData);
            
            if (resolveData.success) {
                // Update workflow in ComfyUI
                await this.updateWorkflowInComfyUI(resolveData.workflow);
                
                // Force a UI refresh
                setTimeout(() => {
                    if (window.app && window.app.graph && window.app.graph.setDirtyCanvas) {
                        window.app.graph.setDirtyCanvas(true, true);
                    }
                }, 100);
                
                // Show success message
                alert(`✓ Successfully auto-resolved ${resolutions.length} model${resolutions.length > 1 ? 's' : ''}!`);
                
                // Reload dialog to show updated status
                this.loadWorkflowData();
            } else {
                alert('Failed to auto-resolve models: ' + (resolveData.error || 'Unknown error'));
            }
            
        } catch (error) {
            console.error('🔗 Auto-resolve error:', error);
            alert('Error auto-resolving: ' + error.message);
        }
    }
    
    async updateWorkflowInComfyUI(workflow) {
        console.log("🔗 Updating workflow in ComfyUI...");
        console.log("🔗 Workflow object:", workflow);
        console.log("🔗 Workflow keys:", Object.keys(workflow));
        
        if (!app || !app.graph) {
            console.warn('🔗 Model Linker: Could not update workflow - app or app.graph not available');
            return;
        }

        try {
            // Method 1: Try to directly update the current graph using configure
            if (app.graph && typeof app.graph.configure === 'function') {
                console.log("🔗 Using app.graph.configure()");
                app.graph.configure(workflow);
                
                // Force canvas redraw
                if (app.graph.setDirtyCanvas) {
                    console.log("🔗 Calling setDirtyCanvas()");
                    app.graph.setDirtyCanvas(true, true);
                }
                
                // Force graph change event
                if (app.graph.change) {
                    console.log("🔗 Calling graph.change()");
                    app.graph.change();
                }
                
                console.log("🔗 Workflow updated successfully via configure()");
                return;
            }

            // Method 2: Try deserialize to update the graph in place
            if (app.graph && typeof app.graph.deserialize === 'function') {
                console.log("🔗 Using app.graph.deserialize()");
                app.graph.deserialize(workflow);
                
                // Force canvas redraw
                if (app.graph.setDirtyCanvas) {
                    app.graph.setDirtyCanvas(true, true);
                }
                
                console.log("🔗 Workflow updated successfully via deserialize()");
                return;
            }

            // Method 3: Use loadGraphData with explicit parameters to update current tab
            if (app.loadGraphData) {
                console.log("🔗 Using app.loadGraphData()");
                await app.loadGraphData(workflow, false, false, null);
                console.log("🔗 Workflow updated successfully via loadGraphData()");
                return;
            }

            console.warn('🔗 Model Linker: No method available to update workflow');
        } catch (error) {
            console.error('🔗 Model Linker: Error updating workflow in ComfyUI:', error);
            console.error('🔗 Error stack:', error.stack);
            // Don't throw - allow the workflow update to continue even if UI update fails
        }
    }
    
    getCurrentWorkflow() {
        // Try to get workflow from global app object
        if (window.app && window.app.graph) {
            try {
                const workflow = window.app.graph.serialize();
                console.log("🔗 Got workflow from app.graph.serialize()");
                return workflow;
            } catch (e) {
                console.log("🔗 app.graph.serialize() failed:", e);
            }
        }
        return null;
    }
}

// Global dialog instance
let modelLinkerDialog = null;

// Button creation function with drag support
function createModelLinkerButton() {
    console.log("🔗 Model Linker: Creating button...");
    
    // Remove any existing button
    const existingButton = document.getElementById('model-linker-button');
    if (existingButton) {
        existingButton.remove();
    }
    
    // Load saved position from localStorage or use defaults
    const savedPosition = localStorage.getItem('modelLinkerButtonPosition');
    let position = { top: 10, right: 10 };
    if (savedPosition) {
        try {
            position = JSON.parse(savedPosition);
        } catch (e) {
            console.warn("🔗 Could not parse saved position:", e);
        }
    }
    
    // Create floating button
    const button = document.createElement('button');
    button.id = 'model-linker-button';
    button.innerHTML = '🔗 Model Linker';
    button.title = 'Open Model Linker (drag to move)';
    
    // Style the button
    Object.assign(button.style, {
        position: 'fixed',
        top: position.top + 'px',
        right: position.right + 'px',
        zIndex: '10000',
        backgroundColor: '#353535',
        color: '#ffffff',
        border: '2px solid #007acc',
        padding: '8px 16px',
        borderRadius: '6px',
        cursor: 'move',
        fontSize: '14px',
        fontWeight: '600',
        boxShadow: '0 4px 12px rgba(0,0,0,0.3)',
        transition: 'background-color 0.2s ease',
        userSelect: 'none'
    });
    
    // Drag functionality
    let isDragging = false;
    let dragStartX, dragStartY;
    let buttonStartTop, buttonStartRight;
    let hasMoved = false;
    
    button.addEventListener('mousedown', (e) => {
        isDragging = true;
        hasMoved = false;
        dragStartX = e.clientX;
        dragStartY = e.clientY;
        buttonStartTop = parseInt(button.style.top);
        buttonStartRight = parseInt(button.style.right);
        
        button.style.transition = 'none';
        button.style.cursor = 'grabbing';
        e.preventDefault();
    });
    
    document.addEventListener('mousemove', (e) => {
        if (!isDragging) return;
        
        const deltaX = e.clientX - dragStartX;
        const deltaY = e.clientY - dragStartY;
        
        // Consider it a drag if moved more than 5 pixels
        if (Math.abs(deltaX) > 5 || Math.abs(deltaY) > 5) {
            hasMoved = true;
        }
        
        // Calculate new position (note: right moves opposite to X)
        const newTop = buttonStartTop + deltaY;
        const newRight = buttonStartRight - deltaX;
        
        // Keep button within viewport
        const maxTop = window.innerHeight - button.offsetHeight - 10;
        const maxRight = window.innerWidth - button.offsetWidth - 10;
        
        button.style.top = Math.max(0, Math.min(newTop, maxTop)) + 'px';
        button.style.right = Math.max(0, Math.min(newRight, maxRight)) + 'px';
    });
    
    document.addEventListener('mouseup', (e) => {
        if (isDragging) {
            isDragging = false;
            button.style.transition = 'background-color 0.2s ease';
            button.style.cursor = 'move';
            
            // Save position to localStorage
            const newPosition = {
                top: parseInt(button.style.top),
                right: parseInt(button.style.right)
            };
            localStorage.setItem('modelLinkerButtonPosition', JSON.stringify(newPosition));
            
            // Only open dialog if it wasn't a drag
            if (!hasMoved) {
                console.log("🔗 Model Linker: Button clicked!");
                
                if (!modelLinkerDialog) {
                    modelLinkerDialog = new ModelLinkerDialog();
                }
                modelLinkerDialog.show();
            }
        }
    });
    
    // Add hover effects
    button.addEventListener('mouseenter', () => {
        if (!isDragging) {
            button.style.backgroundColor = '#007acc';
        }
    });
    
    button.addEventListener('mouseleave', () => {
        if (!isDragging) {
            button.style.backgroundColor = '#353535';
        }
    });
    
    // Add to page
    document.body.appendChild(button);
    console.log("🔗 Model Linker: Draggable button added to page");
}

// Initialize
console.log("🔗 Model Linker: Setting up initialization...");

// Try multiple methods to ensure the button gets created
if (document.readyState === 'complete') {
    createModelLinkerButton();
} else {
    document.addEventListener('DOMContentLoaded', createModelLinkerButton);
}

window.addEventListener('load', createModelLinkerButton);
setTimeout(createModelLinkerButton, 2000);
setTimeout(createModelLinkerButton, 5000);

console.log("🔗 Model Linker: JavaScript setup complete");