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
            matches.forEach((match, matchIndex) => {
                if (match.confidence === 100) {
                    const buttonId = `resolve-${missing.node_id}-${missingIndex}-${matchIndex}`;
                    const button = this.contentElement.querySelector(`#${buttonId}`);
                    if (button) {
                        button.onclick = () => this.resolveModel(missing, match.model);
                    }
                }
            });
        });
    }
    
    renderMissingModel(missing) {
        const matches = missing.matches || [];
        const perfectMatches = matches.filter(m => m.confidence === 100);
        const otherMatches = matches.filter(m => m.confidence < 100 && m.confidence >= 70);
        
        let html = `<div style="border: 1px solid #444; padding: 12px; border-radius: 4px;">`;
        html += `<div><strong>Node:</strong> ${missing.node_type} (ID: ${missing.node_id})</div>`;
        html += `<div><strong>Missing Model:</strong> <code>${missing.original_path}</code></div>`;
        html += `<div><strong>Category:</strong> ${missing.category || 'unknown'}</div>`;
        
        if (matches.length > 0) {
            html += `<div style="margin-top: 12px;"><strong>Suggested Matches:</strong></div>`;
            html += '<ul style="margin: 8px 0; padding-left: 20px;">';
            
            const matchesToShow = perfectMatches.length > 0 ? perfectMatches : otherMatches.slice(0, 5);
            
            matchesToShow.forEach((match, matchIndex) => {
                const buttonId = `resolve-${missing.node_id}-${missing.widget_index || 0}-${matchIndex}`;
                html += `<li style="margin: 4px 0;">`;
                html += `<code>${match.model?.relative_path || match.filename}</code> `;
                html += `<span style="color: ${match.confidence === 100 ? 'green' : 'orange'};">
                    (${match.confidence}% confidence)
                </span>`;
                
                if (match.confidence === 100) {
                    html += ` <button id="${buttonId}" style="margin-left: 8px; padding: 4px 8px; background: #007acc; color: white; border: none; border-radius: 3px; cursor: pointer;">
                        Resolve
                    </button>`;
                }
                html += `</li>`;
            });
            
            html += '</ul>';
        } else {
            html += `<div style="color: orange; margin-top: 8px;">No matches found.</div>`;
        }
        
        html += '</div>';
        return html;
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