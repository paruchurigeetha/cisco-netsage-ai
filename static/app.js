// NetSage AI - Interactive Frontend Controller

// State variables
let casesList = [];
let activeCase = null;
let activeCaseDiagnosis = null; // Stores AI output for active case
let charts = {};

// DOM Elements
const elements = {
    tabs: document.querySelectorAll('.nav-item'),
    tabPanels: document.querySelectorAll('.tab-panel'),
    tabTitle: document.getElementById('tab-title'),
    tabSubtitle: document.getElementById('tab-subtitle'),
    
    // Metrics
    metricTotal: document.getElementById('metric-total-cases'),
    metricAgreement: document.getElementById('metric-agreement-rate'),
    metricCorrected: document.getElementById('metric-corrected-count'),
    metricReviewed: document.getElementById('metric-reviewed-count'),
    
    // Case Sidebar
    caseSearch: document.getElementById('case-search'),
    filterConcept: document.getElementById('filter-concept'),
    caseListContainer: document.getElementById('case-list-container'),
    
    // Active Case Console
    emptyCaseState: document.getElementById('empty-case-state'),
    activeCaseConsole: document.getElementById('active-case-console'),
    activeCaseId: document.getElementById('active-case-id'),
    activeCaseConcept: document.getElementById('active-case-concept'),
    activeCaseOsi: document.getElementById('active-case-osi'),
    activeCaseSeverity: document.getElementById('active-case-severity'),
    activeCaseSymptom: document.getElementById('active-case-symptom'),
    activeCaseTopology: document.getElementById('active-case-topology'),
    activeCaseOutputs: document.getElementById('active-case-outputs'),
    
    // Actions
    btnCopyCli: document.getElementById('btn-copy-cli'),
    btnRunRule: document.getElementById('btn-run-rule'),
    btnRunAI: document.getElementById('btn-run-ai'),
    geminiKeyInput: document.getElementById('gemini-key'),
    
    // Output Panels
    ruleCheckerPanel: document.getElementById('rule-checker-panel'),
    ruleStatus: document.getElementById('rule-status'),
    ruleOutputContent: document.getElementById('rule-output-content'),
    
    aiDiagnosisPanel: document.getElementById('ai-diagnosis-panel'),
    aiOutputSimulated: document.getElementById('ai-output-simulated'),
    aiOutputConfidence: document.getElementById('ai-output-confidence'),
    aiRootCause: document.getElementById('ai-root-cause'),
    aiOsiLayer: document.getElementById('ai-osi-layer'),
    aiNextCommand: document.getElementById('ai-next-command'),
    aiEvidence: document.getElementById('ai-evidence'),
    aiFixSteps: document.getElementById('ai-fix-steps'),
    
    // Review Panel
    reviewCurrentStatus: document.getElementById('review-current-status'),
    verdictAcceptRadio: document.getElementById('verdict-accept-radio'),
    verdictEditRadio: document.getElementById('verdict-edit-radio'),
    verdictRejectRadio: document.getElementById('verdict-reject-radio'),
    humanEditableFields: document.getElementById('human-editable-fields'),
    humanNotes: document.getElementById('human-notes'),
    btnSubmitReview: document.getElementById('btn-submit-review'),
    
    // Edit Fields
    editRootCause: document.getElementById('edit-root-cause'),
    editOsiLayer: document.getElementById('edit-osi-layer'),
    editConfidence: document.getElementById('edit-confidence'),
    editFixSteps: document.getElementById('edit-fix-steps'),
    
    // Markdown Displays
    responsibleMarkdown: document.getElementById('responsible-markdown-content'),
    responsibleSummaryBody: document.getElementById('responsible-summary-body'),
    promptFileContent: document.getElementById('prompt-file-content'),
    
    // Toast
    toast: document.getElementById('toast'),
    toastMessage: document.getElementById('toast-message'),
};

// Initialize Application
document.addEventListener('DOMContentLoaded', () => {
    initTabs();
    loadDashboardData();
    loadCasesList();
    setupWorkspaceListeners();
    loadStaticDocuments();
    
    // Try to load saved API Key from localStorage
    if (localStorage.getItem('gemini_api_key')) {
        elements.geminiKeyInput.value = localStorage.getItem('gemini_api_key');
    }
    
    elements.geminiKeyInput.addEventListener('change', (e) => {
        localStorage.setItem('gemini_api_key', e.target.value);
    });
});

// 1. Tab Management
function initTabs() {
    elements.tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            elements.tabs.forEach(t => t.classList.remove('active'));
            elements.tabPanels.forEach(p => p.classList.remove('active'));
            
            tab.classList.add('active');
            const targetTab = tab.getAttribute('data-tab');
            document.getElementById(`tab-${targetTab}`).classList.add('active');
            
            // Update Headers
            updateHeaderTitles(targetTab);
            
            // Reload dashboard if tab selected
            if (targetTab === 'dashboard') {
                loadDashboardData();
            }
        });
    });
}

function updateHeaderTitles(tabName) {
    const titles = {
        'dashboard': {
            title: "Dashboard Overview",
            subtitle: "Real-time metrics, diagnostics health, and human-in-the-loop review statistics."
        },
        'workspace': {
            title: "Diagnostics Lab & Verification Workspace",
            subtitle: "Select troubleshooting cases, run rule validation, trigger AI agent, and record verdicts."
        },
        'responsible-log': {
            title: "Responsible AI Oversight Log",
            subtitle: "Detailed notes on cases where human intervention corrected AI hallucinations or omissions."
        },
        'prompt-lib': {
            title: "AI Prompt Library",
            subtitle: "Structured system templates enforcing formatted network diagnostics."
        }
    };
    
    if (titles[tabName]) {
        elements.tabTitle.textContent = titles[tabName].title;
        elements.tabSubtitle.textContent = titles[tabName].subtitle;
    }
}

// 2. Fetch and Load Cases
async function loadCasesList() {
    try {
        const response = await fetch('/api/cases');
        casesList = await response.json();
        renderCaseList(casesList);
    } catch (error) {
        console.error("Failed to load cases", error);
        showToast("Error loading cases from server", "error");
    }
}

function renderCaseList(list) {
    elements.caseListContainer.innerHTML = '';
    
    if (list.length === 0) {
        elements.caseListContainer.innerHTML = '<p class="key-note">No cases match your filters.</p>';
        return;
    }
    
    list.forEach(c => {
        const item = document.createElement('button');
        item.className = `case-item ${activeCase && activeCase.id === c.id ? 'active' : ''}`;
        
        let statusBadgeClass = 'badge-pending';
        if (c.review_status === 'Accepted') statusBadgeClass = 'badge-success';
        else if (c.review_status === 'Edited') statusBadgeClass = 'badge-warning';
        else if (c.review_status === 'Rejected') statusBadgeClass = 'badge-danger';
        
        item.innerHTML = `
            <div class="case-item-header">
                <span class="case-item-id">Case #${String(c.id).padStart(2, '0')}</span>
                <span class="badge ${statusBadgeClass}">${c.review_status}</span>
            </div>
            <div class="case-item-symptom">${c.symptom}</div>
        `;
        
        item.addEventListener('click', () => selectCase(c.id));
        elements.caseListContainer.appendChild(item);
    });
}

// 3. Case Selection and Loading
async function selectCase(id) {
    try {
        // Highlight active sidebar item
        document.querySelectorAll('.case-item').forEach((item, index) => {
            if (casesList[index] && casesList[index].id === id) {
                item.classList.add('active');
            } else {
                item.classList.remove('active');
            }
        });
        
        // Fetch detailed case information
        const response = await fetch(`/api/cases/${id}`);
        activeCase = await response.json();
        
        // Clear outputs
        elements.ruleCheckerPanel.classList.add('hidden');
        elements.aiDiagnosisPanel.classList.add('hidden');
        activeCaseDiagnosis = null;
        
        // Update details
        elements.activeCaseId.textContent = `Case #${String(activeCase.id).padStart(2, '0')}`;
        elements.activeCaseConcept.textContent = activeCase.concept;
        elements.activeCaseOsi.textContent = activeCase.osi_layer;
        elements.activeCaseSeverity.textContent = activeCase.severity;
        elements.activeCaseSymptom.textContent = activeCase.symptom;
        elements.activeCaseTopology.textContent = activeCase.topology;
        elements.activeCaseOutputs.textContent = activeCase.show_outputs;
        
        // Severity color styling
        elements.activeCaseSeverity.className = 'badge';
        if (activeCase.severity === 'Critical') elements.activeCaseSeverity.classList.add('badge-danger');
        else if (activeCase.severity === 'High') elements.activeCaseSeverity.classList.add('badge-danger');
        else if (activeCase.severity === 'Medium') elements.activeCaseSeverity.classList.add('badge-warning');
        else elements.activeCaseSeverity.classList.add('badge-primary');
        
        // Concept badge styling
        elements.activeCaseConcept.className = 'badge badge-primary';
        
        // Load existing review state
        elements.reviewCurrentStatus.textContent = activeCase.review_status || "Pending Review";
        elements.reviewCurrentStatus.className = 'badge';
        if (activeCase.review_status === 'Accepted') elements.reviewCurrentStatus.classList.add('badge-success');
        else if (activeCase.review_status === 'Edited') elements.reviewCurrentStatus.classList.add('badge-warning');
        else if (activeCase.review_status === 'Rejected') elements.reviewCurrentStatus.classList.add('badge-danger');
        else elements.reviewCurrentStatus.classList.add('badge-pending');
        
        // Pre-populate review form
        elements.humanNotes.value = activeCase.human_notes || '';
        
        // Uncheck radio buttons initially
        elements.verdictAcceptRadio.checked = false;
        elements.verdictEditRadio.checked = false;
        elements.verdictRejectRadio.checked = false;
        elements.humanEditableFields.classList.add('hidden');
        
        // Show checked status if saved
        if (activeCase.review_status === 'Accepted') {
            elements.verdictAcceptRadio.checked = true;
        } else if (activeCase.review_status === 'Edited') {
            elements.verdictEditRadio.checked = true;
            loadEditFields(activeCase.expected_ai_output || {});
            elements.humanEditableFields.classList.remove('hidden');
        } else if (activeCase.review_status === 'Rejected') {
            elements.verdictRejectRadio.checked = true;
        }
        
        // Toggle view
        elements.emptyCaseState.classList.add('hidden');
        elements.activeCaseConsole.classList.remove('hidden');
        
    } catch (error) {
        console.error("Error loading case", error);
        showToast("Error loading case details", "error");
    }
}

function loadEditFields(diag) {
    elements.editRootCause.value = diag.root_cause || '';
    elements.editOsiLayer.value = diag.osi_layer || 'L3';
    elements.editConfidence.value = diag.confidence || 'Medium';
    elements.editFixSteps.value = diag.fix_steps || '';
}

// 4. Workspace Action Listeners
function setupWorkspaceListeners() {
    // Search symptom
    elements.caseSearch.addEventListener('input', applyFilters);
    elements.filterConcept.addEventListener('change', applyFilters);
    
    // Copy CLI show commands
    elements.btnCopyCli.addEventListener('click', () => {
        navigator.clipboard.writeText(elements.activeCaseOutputs.textContent);
        showToast("CLI configurations copied to clipboard!");
    });
    
    // Run Deterministic Rule Checker
    elements.btnRunRule.addEventListener('click', async () => {
        if (!activeCase) return;
        elements.btnRunRule.disabled = true;
        elements.btnRunRule.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Checking Configs...';
        
        try {
            const response = await fetch(`/api/cases/${activeCase.id}/rule-check`, {
                method: 'POST'
            });
            const result = await response.json();
            
            elements.ruleCheckerPanel.classList.remove('hidden');
            elements.ruleOutputContent.innerHTML = '';
            
            if (result.matched && result.anomalies.length > 0) {
                elements.ruleStatus.innerHTML = '<span class="badge badge-warning"><i class="fa-solid fa-triangle-exclamation"></i> Failures Caught</span>';
                result.anomalies.forEach(a => {
                    const div = document.createElement('div');
                    div.className = 'rule-item';
                    div.innerHTML = `
                        <div class="rule-item-header">
                            <span class="rule-item-title">${a.rule}</span>
                            <span class="badge badge-danger">${a.severity}</span>
                        </div>
                        <div class="rule-item-details">${a.details}</div>
                        <div class="rule-item-fix"><strong>Recommended Action:</strong> ${a.fix}</div>
                    `;
                    elements.ruleOutputContent.appendChild(div);
                });
            } else {
                elements.ruleStatus.innerHTML = '<span class="badge badge-success"><i class="fa-solid fa-circle-check"></i> Clean</span>';
                elements.ruleOutputContent.innerHTML = `
                    <div class="clean-rules-msg">
                        <i class="fa-solid fa-circle-check"></i> 
                        <span>No simple static config mismatches caught. Running deep LLM semantic diagnosis is recommended.</span>
                    </div>
                `;
            }
            
        } catch (error) {
            console.error("Rule checker failed", error);
            showToast("Failed to run rule checker", "error");
        } finally {
            elements.btnRunRule.disabled = false;
            elements.btnRunRule.innerHTML = '<i class="fa-solid fa-microchip"></i> Run Python Rule Checker';
        }
    });
    
    // Run AI Agent Diagnosis
    elements.btnRunAI.addEventListener('click', async () => {
        if (!activeCase) return;
        elements.btnRunAI.disabled = true;
        elements.btnRunAI.innerHTML = '<i class="fa-solid fa-circle-notch fa-spin"></i> Reasoning...';
        
        try {
            const apiKey = elements.geminiKeyInput.value.trim();
            const headers = {};
            if (apiKey) {
                headers['Authorization'] = `Bearer ${apiKey}`;
            }
            
            const response = await fetch(`/api/cases/${activeCase.id}/diagnose`, {
                method: 'POST',
                headers: headers
            });
            const result = await response.json();
            
            activeCaseDiagnosis = result.diagnosis;
            
            // Populate AI output UI
            elements.aiDiagnosisPanel.classList.remove('hidden');
            elements.aiOutputSimulated.textContent = result.simulated ? "Cached Diagnosis" : "Live Gemini AI";
            elements.aiOutputSimulated.className = result.simulated ? "badge badge-primary" : "badge badge-success";
            
            elements.aiOutputConfidence.textContent = `Confidence: ${activeCaseDiagnosis.confidence || 'Medium'}`;
            elements.aiRootCause.textContent = activeCaseDiagnosis.root_cause || 'N/A';
            elements.aiOsiLayer.textContent = activeCaseDiagnosis.osi_layer || 'L3';
            elements.aiNextCommand.textContent = activeCaseDiagnosis.next_command || 'N/A';
            elements.aiEvidence.textContent = activeCaseDiagnosis.evidence || 'N/A';
            elements.aiFixSteps.textContent = activeCaseDiagnosis.fix_steps || 'N/A';
            
            // Automatically fill the edit inputs with AI diagnosis as base
            loadEditFields(activeCaseDiagnosis);
            
        } catch (error) {
            console.error("AI diagnosis failed", error);
            showToast("Failed to run AI diagnosis", "error");
        } finally {
            elements.btnRunAI.disabled = false;
            elements.btnRunAI.innerHTML = '<i class="fa-solid fa-brain"></i> Diagnose with NetSage AI';
        }
    });
    
    // Toggle human edits inputs
    elements.verdictAcceptRadio.addEventListener('change', () => elements.humanEditableFields.classList.add('hidden'));
    elements.verdictRejectRadio.addEventListener('change', () => elements.humanEditableFields.classList.add('hidden'));
    elements.verdictEditRadio.addEventListener('change', () => {
        if (elements.verdictEditRadio.checked) {
            // Fill from active diagnosis if not already filled
            if (activeCaseDiagnosis) {
                loadEditFields(activeCaseDiagnosis);
            } else if (activeCase.expected_ai_output) {
                loadEditFields(activeCase.expected_ai_output);
            }
            elements.humanEditableFields.classList.remove('hidden');
        }
    });
    
    // Submit Human Review Verdict
    elements.btnSubmitReview.addEventListener('click', async () => {
        if (!activeCase) return;
        
        let verdict = "";
        if (elements.verdictAcceptRadio.checked) verdict = "Accepted";
        else if (elements.verdictEditRadio.checked) verdict = "Edited";
        else if (elements.verdictRejectRadio.checked) verdict = "Rejected";
        
        if (!verdict) {
            showToast("Please select a review verdict!", "warning");
            return;
        }
        
        const payload = {
            review_status: verdict,
            human_notes: elements.humanNotes.value.trim()
        };
        
        if (verdict === 'Edited') {
            payload.edited_diagnosis = {
                root_cause: elements.editRootCause.value.trim(),
                osi_layer: elements.editOsiLayer.value,
                confidence: elements.editConfidence.value,
                fix_steps: elements.editFixSteps.value.trim()
            };
        }
        
        elements.btnSubmitReview.disabled = true;
        
        try {
            const response = await fetch(`/api/cases/${activeCase.id}/review`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(payload)
            });
            const result = await response.json();
            
            if (result.success) {
                showToast("Oversight review submitted successfully!");
                // Reload list & active details
                await loadCasesList();
                await selectCase(activeCase.id);
            }
        } catch (error) {
            console.error("Submission failed", error);
            showToast("Failed to save review", "error");
        } finally {
            elements.btnSubmitReview.disabled = false;
        }
    });
}

function applyFilters() {
    const q = elements.caseSearch.value.toLowerCase().trim();
    const concept = elements.filterConcept.value;
    
    const filtered = casesList.filter(c => {
        const matchesQuery = c.symptom.toLowerCase().includes(q) || String(c.id) === q;
        const matchesConcept = !concept || c.concept === concept;
        return matchesQuery && matchesConcept;
    });
    
    renderCaseList(filtered);
}

// 5. Dashboard Charts
async function loadDashboardData() {
    try {
        const response = await fetch('/api/dashboard');
        const data = await response.json();
        
        // Update metric values
        elements.metricTotal.textContent = data.total_cases;
        elements.metricAgreement.textContent = `${(data.agreement_rate * 100).toFixed(1)}%`;
        
        const corrected = data.status_counts.Edited + data.status_counts.Rejected;
        elements.metricCorrected.textContent = corrected;
        
        const reviewed = data.total_cases - data.status_counts.Pending;
        elements.metricReviewed.textContent = `${reviewed}/${data.total_cases}`;
        
        // Render Charts
        renderAgreementChart(data.status_counts);
        renderConceptsChart(data.concepts);
        renderOsiChart(data.osi_layers);
        renderSeverityChart(data.severities);
        
        // Render the responsible AI logs summary table
        renderResponsibleSummary(data.responsible_logs);
        
    } catch (error) {
        console.error("Failed to load dashboard statistics", error);
    }
}

function renderAgreementChart(counts) {
    if (charts.agreement) charts.agreement.destroy();
    
    const ctx = document.getElementById('chart-agreement').getContext('2d');
    charts.agreement = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['Accepted', 'Edited', 'Rejected', 'Pending'],
            datasets: [{
                data: [counts.Accepted, counts.Edited, counts.Rejected, counts.Pending],
                backgroundColor: ['#10b981', '#f59e0b', '#ef4444', '#8b5cf6'],
                borderColor: '#111a30',
                borderWidth: 2
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: { color: '#f1f5f9', font: { family: 'Outfit' } }
                }
            }
        }
    });
}

function renderConceptsChart(concepts) {
    if (charts.concepts) charts.concepts.destroy();
    
    const ctx = document.getElementById('chart-concepts').getContext('2d');
    const labels = Object.keys(concepts);
    const data = Object.values(concepts);
    
    charts.concepts = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Cases',
                data: data,
                backgroundColor: '#00abec',
                borderRadius: 4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: { grid: { color: 'rgba(255, 255, 255, 0.05)' }, ticks: { color: '#94a3b8' } },
                x: { grid: { display: false }, ticks: { color: '#94a3b8' } }
            },
            plugins: {
                legend: { display: false }
            }
        }
    });
}

function renderOsiChart(osi) {
    if (charts.osi) charts.osi.destroy();
    
    const ctx = document.getElementById('chart-osi').getContext('2d');
    // Sort layers L1, L2, L3, L4, L7
    const order = ['L1', 'L2', 'L3', 'L4', 'L7'];
    const labels = order.filter(l => osi[l] !== undefined);
    const data = labels.map(l => osi[l]);
    
    charts.osi = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'OSI Fault Layer Distribution',
                data: data,
                backgroundColor: 'rgba(139, 92, 246, 0.65)',
                borderColor: '#8b5cf6',
                borderWidth: 1,
                borderRadius: 4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: { grid: { color: 'rgba(255, 255, 255, 0.05)' }, ticks: { color: '#94a3b8', stepSize: 1 } },
                x: { grid: { display: false }, ticks: { color: '#94a3b8' } }
            },
            plugins: {
                legend: { display: false }
            }
        }
    });
}

function renderSeverityChart(severities) {
    if (charts.severity) charts.severity.destroy();
    
    const ctx = document.getElementById('chart-severity').getContext('2d');
    const order = ['Low', 'Medium', 'High', 'Critical'];
    const labels = order;
    const data = order.map(s => severities[s] || 0);
    
    charts.severity = new Chart(ctx, {
        type: 'polarArea',
        data: {
            labels: labels,
            datasets: [{
                data: data,
                backgroundColor: [
                    'rgba(0, 171, 236, 0.5)',   // Low - light blue
                    'rgba(245, 158, 11, 0.5)',  // Medium - yellow
                    'rgba(239, 68, 68, 0.5)',   // High - red
                    'rgba(185, 28, 28, 0.7)'    // Critical - deep red
                ],
                borderColor: '#111a30'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                r: { grid: { color: 'rgba(255, 255, 255, 0.05)' }, angleLines: { color: 'rgba(255, 255, 255, 0.05)' } }
            },
            plugins: {
                legend: { position: 'bottom', labels: { color: '#f1f5f9' } }
            }
        }
    });
}

function renderResponsibleSummary(logs) {
    elements.responsibleSummaryBody.innerHTML = '';
    
    if (logs.length === 0) {
        elements.responsibleSummaryBody.innerHTML = '<tr><td colspan="6" class="key-note" style="text-align: center;">No human-corrected cases registered yet. Verify and edit a diagnosis in the Diagnostics Lab tab.</td></tr>';
        return;
    }
    
    logs.forEach(log => {
        const tr = document.createElement('tr');
        
        let statusBadge = '';
        if (log.review_status === 'Edited') statusBadge = '<span class="badge badge-warning">Edited</span>';
        else if (log.review_status === 'Rejected') statusBadge = '<span class="badge badge-danger">Rejected</span>';
        
        tr.innerHTML = `
            <td><strong>#${log.id}</strong></td>
            <td><span class="badge badge-primary">${log.concept}</span></td>
            <td><strong>${log.osi_layer}</strong></td>
            <td class="table-case-symptom"><em>${log.ai_output.root_cause || "Omission / Wrong layer"}</em></td>
            <td>${log.human_notes || "Corrected configuration steps."}</td>
            <td>${statusBadge}</td>
        `;
        elements.responsibleSummaryBody.appendChild(tr);
    });
}

// 6. Loading Markdown / Prompt Library Static Content
async function loadStaticDocuments() {
    try {
        // Fetch prompt file
        const promptRes = await fetch('/static_prompt');
        if (promptRes.ok) {
            elements.promptFileContent.textContent = await promptRes.text();
        } else {
            elements.promptFileContent.textContent = "Error loading prompt library from server.";
        }
        
        // Fetch responsible AI markdown log
        const logRes = await fetch('/static_log');
        if (logRes.ok) {
            const rawText = await logRes.text();
            // Basic markdown parser for display
            elements.responsibleMarkdown.innerHTML = parseMarkdown(rawText);
        } else {
            elements.responsibleMarkdown.innerHTML = "<p>Error loading responsible AI log from server.</p>";
        }
        
    } catch (error) {
        console.error("Static files loading failed", error);
    }
}

// Helper: Micro Markdown Parser to HTML
function parseMarkdown(md) {
    let html = md;
    
    // Tables parser
    html = html.replace(/\|(.+?)\|/g, (match) => {
        // Very basic conversion of markdown table lines
        return match;
    });

    // Headers
    html = html.replace(/^### (.*?)$/gm, '<h3>$1</h3>');
    html = html.replace(/^## (.*?)$/gm, '<h2>$1</h2>');
    html = html.replace(/^# (.*?)$/gm, '<h2>$1</h2>');
    
    // Lists
    html = html.replace(/^\*\s+(.*?)$/gm, '<li>$1</li>');
    html = html.replace(/^\-\s+(.*?)$/gm, '<li>$1</li>');
    
    // Bold
    html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    
    // Emphasis
    html = html.replace(/\*(.*?)\*/g, '<em>$1</em>');
    
    // Code
    html = html.replace(/`(.*?)`/g, '<code>$1</code>');
    
    // Clean orphan list tags (very simple parser, wrap list elements)
    // In a real app we'd use marked.js, but since we are offline and lightweight:
    
    return html;
}

// 7. Toast Alerts
function showToast(message, type = 'success') {
    elements.toastMessage.textContent = message;
    
    const icon = elements.toast.querySelector('.toast-icon');
    if (type === 'success') {
        elements.toast.style.backgroundColor = '#10b981';
        icon.className = 'fa-solid fa-circle-check toast-icon';
    } else if (type === 'warning') {
        elements.toast.style.backgroundColor = '#f59e0b';
        icon.className = 'fa-solid fa-triangle-exclamation toast-icon';
    } else {
        elements.toast.style.backgroundColor = '#ef4444';
        icon.className = 'fa-solid fa-circle-xmark toast-icon';
    }
    
    elements.toast.classList.remove('hidden');
    
    setTimeout(() => {
        elements.toast.classList.add('hidden');
    }, 3000);
}
