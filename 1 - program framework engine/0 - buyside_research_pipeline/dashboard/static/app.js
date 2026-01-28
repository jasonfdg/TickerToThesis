/**
 * TTT Pipeline Dashboard - Client Application
 *
 * Handles SSE connection, UI updates, and notifications.
 */

class PipelineDashboard {
    constructor() {
        this.eventSource = null;
        this.state = {
            ticker: '',
            status: 'idle',
            currentIteration: 0,
            totalIterations: 5,
            totalTokens: 0,
            startedAt: null,
            currentPhase: '',      // 'genesis', 'analysts', 'source_update', 'rd_reviews'
            completedAgents: 0,    // Counter for agents completed in current phase
        };
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 10;
        this.reconnectDelay = 1000;

        // DOM elements
        this.elements = {
            ticker: document.getElementById('ticker'),
            analysisDate: document.getElementById('analysis-date'),
            timestamp: document.getElementById('timestamp'),
            statusBadge: document.getElementById('status-badge'),
            progressFill: document.getElementById('progress-fill'),
            progressLabel: document.getElementById('progress-label'),
            elapsedTime: document.getElementById('elapsed-time'),
            estRemaining: document.getElementById('est-remaining'),
            totalTokens: document.getElementById('total-tokens'),
            thesisContent: document.getElementById('thesis-content'),
            analystList: document.getElementById('analyst-list'),
            rdList: document.getElementById('rd-list'),
            logContainer: document.getElementById('log-container'),
            costClaude: document.getElementById('cost-claude'),
            costOpenai: document.getElementById('cost-openai'),
            costGemini: document.getElementById('cost-gemini'),
            costTotal: document.getElementById('cost-total'),
            chime: document.getElementById('chime'),
            reportsPanel: document.getElementById('reports-panel'),
            reportEn: document.getElementById('report-en'),
            reportCn: document.getElementById('report-cn'),
        };

        this.analystNames = {
            1: 'Quality Compounders',
            2: 'Imaginative Growth',
            3: 'Fundamental L/S',
            4: 'Deep Value',
            5: 'Event-Driven',
            6: 'Macro-Tactical'
        };

        this.init();
    }

    init() {
        // Start clock update
        this.updateClock();
        setInterval(() => this.updateClock(), 1000);

        // Start elapsed time update
        setInterval(() => this.updateElapsedTime(), 1000);

        // Connect to SSE
        this.connect();

        // Request notification permission
        this.requestNotificationPermission();

        // Load initial state
        this.loadInitialState();
    }

    connect() {
        if (this.eventSource) {
            this.eventSource.close();
        }

        this.eventSource = new EventSource('/events');

        this.eventSource.onopen = () => {
            console.log('SSE connected');
            this.reconnectAttempts = 0;
            this.setConnectionStatus(true);
        };

        this.eventSource.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                this.handleEvent(data);
            } catch (e) {
                console.error('Failed to parse event:', e);
            }
        };

        this.eventSource.onerror = (error) => {
            console.error('SSE error:', error);
            this.setConnectionStatus(false);
            this.eventSource.close();

            // Reconnect with exponential backoff
            if (this.reconnectAttempts < this.maxReconnectAttempts) {
                const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts);
                this.reconnectAttempts++;
                console.log(`Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts})`);
                setTimeout(() => this.connect(), delay);
            }
        };
    }

    setConnectionStatus(connected) {
        let indicator = document.querySelector('.connection-status');
        if (!indicator) {
            indicator = document.createElement('div');
            indicator.className = 'connection-status';
            document.body.appendChild(indicator);
        }
        indicator.classList.toggle('disconnected', !connected);
    }

    async loadInitialState() {
        try {
            const response = await fetch('/state');
            const state = await response.json();
            this.applyState(state);
        } catch (e) {
            console.error('Failed to load initial state:', e);
        }
    }

    applyState(state) {
        if (state.ticker) {
            this.state.ticker = state.ticker;
            this.elements.ticker.textContent = state.ticker;
        }

        if (state.status) {
            this.updateStatus(state.status);
        }

        if (state.current_iteration !== undefined) {
            this.state.currentIteration = state.current_iteration;
        }

        if (state.total_iterations !== undefined) {
            this.state.totalIterations = state.total_iterations;
        }

        if (state.current_phase !== undefined) {
            this.state.currentPhase = state.current_phase;
        }

        if (state.completed_agents !== undefined) {
            this.state.completedAgents = state.completed_agents;
        }

        if (state.total_tokens !== undefined) {
            this.state.totalTokens = state.total_tokens;
            this.elements.totalTokens.textContent = `Tokens: ${this.formatNumber(state.total_tokens)}`;
        }

        if (state.started_at) {
            this.state.startedAt = new Date(state.started_at);
        }

        if (state.thesis_summary) {
            this.updateThesis(state.thesis_summary);
        }

        // Update agent statuses
        if (state.agent_status) {
            for (const [key, status] of Object.entries(state.agent_status)) {
                const [role, typeId] = key.split('_');
                this.updateAgentStatus(role, parseInt(typeId), status);
            }
        }

        // Update costs
        if (state.cost_total !== undefined) {
            this.updateCosts({
                claude_cli: state.cost_claude || 0,
                openai: state.cost_openai || 0,
                gemini: state.cost_gemini || 0,
                total: state.cost_total || 0
            });
        }

        // Show reports if pipeline is completed and PDFs are available
        if (state.status === 'completed' && (state.pdf_en || state.pdf_cn)) {
            this.showReports(state.pdf_en, state.pdf_cn);
        }

        this.updateProgress();
    }

    handleEvent(event) {
        const { type, data, timestamp } = event;

        switch (type) {
            case 'heartbeat':
                // Keep-alive, no action needed
                break;

            case 'pipeline_started':
                this.state.ticker = data.ticker;
                this.state.totalIterations = data.iterations || 5;
                this.state.startedAt = new Date();
                this.elements.ticker.textContent = data.ticker;
                // Display analysis date (from backend if provided, else current date)
                const dateStr = data.analysis_date || new Date().toLocaleDateString('en-US', {
                    year: 'numeric', month: 'long', day: 'numeric'
                });
                this.elements.analysisDate.textContent = `Analysis: ${dateStr}`;
                this.updateStatus('running');
                this.addLog(`Pipeline started for ${data.ticker}`, 'info');
                this.resetAgentStatuses();
                break;

            case 'pipeline_completed':
                this.state.status = 'completed';
                this.updateStatus('completed');
                this.updateProgress(); // Will now set to 100% and add completed class
                this.addLog('Pipeline completed successfully!', 'success');
                this.playChime();
                this.showNotification('Pipeline Complete', `${this.state.ticker} analysis finished.`);
                // Show final reports panel with PDF links
                if (data.pdf_en || data.pdf_cn) {
                    this.showReports(data.pdf_en, data.pdf_cn);
                }
                break;

            case 'pipeline_failed':
                this.updateStatus('failed');
                this.addLog(`Pipeline failed: ${data.error}`, 'error');
                this.showNotification('Pipeline Failed', data.error);
                break;

            case 'iteration_started':
                this.state.currentIteration = data.iteration;
                this.state.currentPhase = data.phase || '';
                this.state.completedAgents = 0; // Reset agent counter for new iteration/phase
                this.updateProgress();
                this.addLog(`Iteration ${data.iteration} started - ${data.phase || 'processing'}`);
                this.resetAgentStatusesForIteration();
                break;

            case 'iteration_completed':
                this.addLog(`Iteration ${data.iteration} completed (${this.formatNumber(data.tokens || 0)} tokens)`, 'success');
                break;

            case 'agent_started':
                this.updateAgentStatus(data.role, data.type_id, 'running');
                this.addLog(`${this.getAgentName(data.role, data.type_id)} started`);
                break;

            case 'agent_completed':
                const status = data.success ? 'completed' : 'failed';
                this.updateAgentStatus(data.role, data.type_id, status);
                this.state.totalTokens += data.tokens || 0;
                this.elements.totalTokens.textContent = `Tokens: ${this.formatNumber(this.state.totalTokens)}`;
                // Track agent completion for progress granularity
                if (data.role === 'analyst' || data.role === 'rd_review') {
                    this.state.completedAgents++;
                    this.updateProgress();
                }
                this.addLog(
                    `${this.getAgentName(data.role, data.type_id)} completed (${this.formatNumber(data.tokens || 0)} tokens)`,
                    data.success ? 'success' : 'error'
                );
                break;

            case 'agent_failed':
                this.updateAgentStatus(data.role, data.type_id, 'failed');
                this.addLog(`${this.getAgentName(data.role, data.type_id)} failed: ${data.error}`, 'error');
                break;

            case 'thesis_updated':
                this.updateThesis(data.summary);
                break;

            case 'cost_updated':
                this.updateCosts(data);
                break;

            case 'source_updated':
                // Source update phase complete - transition to rd_reviews
                this.state.currentPhase = 'rd_reviews';
                this.state.completedAgents = 0; // Reset for RD review phase
                this.updateProgress();
                this.addLog(`Source file updated with ${data.new_citations} new citations`, 'info');
                break;

            case 'source_scout_completed':
                this.addLog(`Source Scout completed (${this.formatNumber(data.tokens || 0)} tokens)`, 'success');
                break;

            case 'shutdown':
                this.addLog('Dashboard connection closed', 'info');
                break;

            default:
                console.log('Unknown event:', type, data);
        }
    }

    updateClock() {
        const now = new Date();
        this.elements.timestamp.textContent = now.toLocaleTimeString('en-US', { hour12: false });
    }

    updateElapsedTime() {
        if (!this.state.startedAt || this.state.status !== 'running') return;

        const elapsed = Math.floor((Date.now() - this.state.startedAt.getTime()) / 1000);
        this.elements.elapsedTime.textContent = `Elapsed: ${this.formatDuration(elapsed)}`;

        // Estimate remaining (rough: ~15 min per iteration)
        if (this.state.currentIteration > 0) {
            const avgPerIter = elapsed / this.state.currentIteration;
            const remaining = avgPerIter * (this.state.totalIterations - this.state.currentIteration);
            this.elements.estRemaining.textContent = `Est. Remaining: ~${this.formatDuration(Math.floor(remaining))}`;
        }
    }

    updateStatus(status) {
        this.state.status = status;
        const badge = this.elements.statusBadge;
        badge.textContent = status.toUpperCase();
        badge.className = 'status-badge ' + status;
    }

    updateProgress() {
        const { currentIteration, totalIterations, currentPhase, status, completedAgents } = this.state;

        // Completion state - always 100%
        if (status === 'completed') {
            this.elements.progressFill.style.width = '100%';
            this.elements.progressFill.classList.add('completed');
            this.elements.progressLabel.textContent = 'Pipeline Complete ✓';
            return;
        }

        // Remove completed class if not completed (for restart scenarios)
        this.elements.progressFill.classList.remove('completed');

        let progress = 0;

        // Progress breakdown:
        // - Genesis: 0-10% (iteration 0)
        // - Each of 5 iterations: 18% each (total 90%)
        //   Within each iteration:
        //   - Analysts (6 agents): 6% (1% per agent)
        //   - Source update: 3%
        //   - RD Reviews (6 agents): 6% (1% per RD)
        //   - Buffer: 3%

        if (currentIteration === 0) {
            // Genesis phase: 0-10%
            if (currentPhase === 'genesis' || currentPhase === '') {
                progress = 5;
            } else {
                progress = 10;
            }
        } else {
            // Base progress: 10% (genesis) + (iteration-1) * 18%
            let base = 10 + (currentIteration - 1) * 18;

            // Add phase progress within current iteration
            if (currentPhase === 'analysts') {
                // Analysts phase: 0-6% (1% per agent)
                base += Math.min(6, (completedAgents / 6) * 6);
            } else if (currentPhase === 'source_update') {
                // Source update: analysts done (6%) + 1.5% (mid source)
                base += 6 + 1.5;
            } else if (currentPhase === 'rd_reviews') {
                // RD reviews: analysts (6%) + source (3%) + RD progress
                base += 9 + Math.min(6, (completedAgents / 6) * 6);
            } else {
                // Unknown phase or iteration complete - show full iteration
                base += 15;
            }

            progress = Math.min(99, base);
        }

        this.elements.progressFill.style.width = `${progress}%`;

        let phaseLabel = currentPhase || 'Processing';
        if (currentIteration === 0) {
            phaseLabel = 'Genesis Scout';
        }

        this.elements.progressLabel.textContent =
            `Iteration ${currentIteration}/${totalIterations} • ${phaseLabel}`;
    }

    updateAgentStatus(role, typeId, status) {
        const list = role === 'analyst' ? this.elements.analystList : this.elements.rdList;
        const item = list.querySelector(`[data-id="${typeId}"]`);

        if (item) {
            const statusEl = item.querySelector('.agent-status');
            statusEl.className = 'agent-status ' + status;
            item.className = 'agent-item ' + status;
        }
    }

    resetAgentStatuses() {
        document.querySelectorAll('.agent-status').forEach(el => {
            el.className = 'agent-status pending';
        });
        document.querySelectorAll('.agent-item').forEach(el => {
            el.className = 'agent-item';
        });
        // Hide reports panel when starting new pipeline
        this.hideReports();
    }

    resetAgentStatusesForIteration() {
        // Reset only analyst statuses at the start of each iteration
        this.elements.analystList.querySelectorAll('.agent-status').forEach(el => {
            el.className = 'agent-status pending';
        });
        this.elements.analystList.querySelectorAll('.agent-item').forEach(el => {
            el.className = 'agent-item';
        });
    }

    updateThesis(summary) {
        if (summary) {
            this.elements.thesisContent.innerHTML = `<p>${this.escapeHtml(summary)}</p>`;
        }
    }

    updateCosts(data) {
        this.elements.costClaude.textContent = `$${(data.claude_cli || 0).toFixed(2)}`;
        this.elements.costOpenai.textContent = `$${(data.openai || 0).toFixed(2)}`;
        this.elements.costGemini.textContent = `$${(data.gemini || 0).toFixed(2)}`;
        this.elements.costTotal.textContent = `$${(data.total || 0).toFixed(2)}`;
    }

    addLog(message, level = '') {
        const entry = document.createElement('div');
        entry.className = 'log-entry' + (level ? ` ${level}` : '');

        const time = new Date().toLocaleTimeString('en-US', { hour12: false });
        entry.innerHTML = `
            <span class="log-time">${time}</span>
            <span class="log-message">${this.escapeHtml(message)}</span>
        `;

        // Insert at the top
        this.elements.logContainer.insertBefore(entry, this.elements.logContainer.firstChild);

        // Keep only last 50 entries
        while (this.elements.logContainer.children.length > 50) {
            this.elements.logContainer.removeChild(this.elements.logContainer.lastChild);
        }
    }

    getAgentName(role, typeId) {
        if (role === 'analyst') {
            return this.analystNames[typeId] || `Analyst ${typeId}`;
        } else if (role === 'rd_review') {
            return `RD Review ${typeId}`;
        }
        return `${role} ${typeId}`;
    }

    formatNumber(num) {
        return num.toLocaleString();
    }

    formatDuration(seconds) {
        const mins = Math.floor(seconds / 60);
        const secs = seconds % 60;
        return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    // Notifications
    requestNotificationPermission() {
        if ('Notification' in window && Notification.permission === 'default') {
            // Show permission prompt after a delay
            setTimeout(() => {
                Notification.requestPermission();
            }, 3000);
        }
    }

    showNotification(title, body) {
        if ('Notification' in window && Notification.permission === 'granted') {
            new Notification(title, {
                body: body,
                icon: '/static/icon.png',
                tag: 'ttt-pipeline'
            });
        }
    }

    playChime() {
        if (this.elements.chime) {
            this.elements.chime.currentTime = 0;
            this.elements.chime.play().catch(e => {
                console.log('Could not play chime:', e);
            });
        }
    }

    showReports(pdfEn, pdfCn) {
        // Show the reports panel
        if (this.elements.reportsPanel) {
            this.elements.reportsPanel.style.display = 'block';
        }

        // Set English PDF link
        // Use encodeURI (not encodeURIComponent) to preserve path separators (/)
        if (pdfEn && this.elements.reportEn) {
            this.elements.reportEn.href = `/reports/${encodeURI(pdfEn)}`;
            this.elements.reportEn.style.display = 'flex';
            this.addLog(`English PDF ready: ${pdfEn}`, 'success');
        }

        // Set Chinese PDF link
        if (pdfCn && this.elements.reportCn) {
            this.elements.reportCn.href = `/reports/${encodeURI(pdfCn)}`;
            this.elements.reportCn.style.display = 'flex';
            this.addLog(`Chinese PDF ready: ${pdfCn}`, 'success');
        }
    }

    hideReports() {
        if (this.elements.reportsPanel) {
            this.elements.reportsPanel.style.display = 'none';
        }
    }
}

// Initialize dashboard when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.dashboard = new PipelineDashboard();
});
