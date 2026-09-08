// Policy Agent JavaScript

let availableTools = [];
let currentTool = null;
let logs = [];
let loginOptions = [];
let coverageCatalog = [];
let agentSession = {
    username: "",
    role: ""
};

// Load tools on page load
document.addEventListener("DOMContentLoaded", async () => {
    restoreAgentSession();
    await loadLoginOptions();
    if (isLoggedIn()) {
        showProtectedAgentSections();
        await verifyConnection();
        await loadTools();
    } else {
        hideProtectedAgentSections();
    }
});

function isLoggedIn() {
    return Boolean(agentSession.role && agentSession.username);
}

function showProtectedAgentSections() {
    document.querySelectorAll(".agent-protected").forEach(section => {
        section.classList.remove("hidden");
    });
}

function hideProtectedAgentSections() {
    document.querySelectorAll(".agent-protected").forEach(section => {
        section.classList.add("hidden");
    });
}

function getAgentHeaders() {
    const headers = {};
    if (agentSession.role) {
        headers["X-Policy-Agent-Role"] = agentSession.role;
    }
    if (agentSession.username) {
        headers["X-Policy-Agent-Username"] = agentSession.username;
    }
    return headers;
}

function restoreAgentSession() {
    const roleValue = agentSession.role || "consumer";
    const roleInput = document.querySelector(`input[name="agentRole"][value="${roleValue}"]`);
    if (roleInput) {
        roleInput.checked = true;
    }
    updateRoleDisplay();
}

async function loadLoginOptions() {
    try {
        const response = await fetch("/api/agent/logins");
        loginOptions = await response.json();
        populateLoginSelect();
        addLog(`✓ Loaded ${loginOptions.length} demo login accounts from remote MCP backend`, "success");
    } catch (error) {
        addLog(`✗ Error loading demo logins: ${error.message}`, "error");
    }
}

function populateLoginSelect() {
    const selector = document.getElementById("loginSelector");
    const selectedRole = document.querySelector('input[name="agentRole"]:checked').value;
    const roleLogins = loginOptions.filter(login => login.role === selectedRole);

    selector.innerHTML = roleLogins.map(login => {
        return `<option value="${login.username}">${login.username}</option>`;
    }).join("");

    const matchingLogin = roleLogins.find(login => login.username === agentSession.username) || roleLogins[0];
    if (matchingLogin) {
        selector.value = matchingLogin.username;
        if (isLoggedIn() && matchingLogin.username === agentSession.username) {
            applySelectedLogin(matchingLogin);
        }
    }
}

function handleLoginSelection() {
    return getSelectedLogin();
}

function getSelectedLogin() {
    const username = document.getElementById("loginSelector").value;
    return loginOptions.find(login => login.username === username);
}

function applySelectedLogin(login) {
    agentSession.username = login.username;
    agentSession.role = login.role;
    updateRoleDisplay();
}

function loginAgent() {
    const selectedRole = document.querySelector('input[name="agentRole"]:checked').value;
    const selectedLogin = getSelectedLogin();

    agentSession = {
        username: selectedLogin ? selectedLogin.username : `${selectedRole}-manual`,
        role: selectedRole
    };

    updateRoleDisplay();
    showProtectedAgentSections();
    clearLogs();
    addLog(`[AUTH] Logged in as ${agentSession.username} / ${agentSession.role}`, "success");
    verifyConnection();
    loadCoverageCatalog();
    loadTools();
}

function logoutAgent() {
    agentSession = { username: "", role: "" };
    restoreAgentSession();
    populateLoginSelect();
    hideProtectedAgentSections();
    availableTools = [];
    currentTool = null;
    document.getElementById("toolSelector").innerHTML = '<option value="">-- Login required --</option>';
    document.getElementById("inputForm").innerHTML = "";
    document.getElementById("outputContent").textContent = JSON.stringify({ result: null, message: "Login required" }, null, 2);
}

function updateRoleDisplay() {
    const activeRole = document.getElementById("activeRole");
    if (!isLoggedIn()) {
        activeRole.textContent = "Not signed in";
        document.getElementById("roleLoginSection").dataset.role = "signed-out";
        return;
    }
    activeRole.textContent = `Signed in: ${agentSession.username} / ${agentSession.role}`;
    document.getElementById("roleLoginSection").dataset.role = agentSession.role;
}

// Verify remote MCP backend connection
async function verifyConnection() {
    if (!isLoggedIn()) {
        hideProtectedAgentSections();
        return;
    }

    const section = document.getElementById("connectionSection");
    const statusEl = document.getElementById("connectionStatus");
    const messageEl = document.getElementById("connectionMessage");
    const ipEl = document.getElementById("connectionIp");
    const urlEl = document.getElementById("connectionUrl");
    const toolsEl = document.getElementById("connectionTools");
    const logEl = document.getElementById("connectionLog");

    section.className = "connection-section checking";
    statusEl.textContent = "Checking";
    messageEl.textContent = "Checking remote MCP backend...";
    ipEl.textContent = "Pending";
    urlEl.textContent = "Pending";
    toolsEl.textContent = "Pending";
    logEl.innerHTML = '<div class="connection-log-entry">Starting connection validation...</div>';

    try {
        const response = await fetch("/api/agent/connection", {
            headers: getAgentHeaders()
        });
        const data = await response.json();

        ipEl.textContent = data.backend_host || "Unknown";
        urlEl.textContent = data.backend_url || "Not configured";
        toolsEl.textContent = Number.isInteger(data.tool_count) ? `${data.tool_count} actions` : "Unknown";
        renderConnectionLogs(data.logs || []);

        if (data.connected) {
            section.className = "connection-section connected";
            statusEl.textContent = "Connected";
            messageEl.textContent = `Connected to remote MCP backend at ${data.backend_host}`;
            addLog(`[SUCCESS] Verified remote MCP backend: ${data.backend_url}`, "success");
        } else {
            section.className = "connection-section disconnected";
            statusEl.textContent = "Disconnected";
            messageEl.textContent = data.error || "Remote MCP backend validation failed";
            addLog(`[ERROR] Remote MCP backend validation failed: ${data.error || "unknown error"}`, "error");
        }
    } catch (error) {
        section.className = "connection-section disconnected";
        statusEl.textContent = "Disconnected";
        messageEl.textContent = `Connection verification failed: ${error.message}`;
        ipEl.textContent = "Unknown";
        urlEl.textContent = "Unavailable";
        toolsEl.textContent = "Unavailable";
        renderConnectionLogs([`[ERROR] ${error.message}`]);
        addLog(`[ERROR] Connection verification failed: ${error.message}`, "error");
    }
}

function renderConnectionLogs(connectionLogs) {
    const logEl = document.getElementById("connectionLog");
    if (!connectionLogs.length) {
        logEl.innerHTML = '<div class="connection-log-entry">No validation logs returned.</div>';
        return;
    }

    logEl.innerHTML = connectionLogs.map(log => {
        const level = log.includes("[ERROR]") ? "error" :
            log.includes("[SUCCESS]") || log.includes("[COMPLETE]") ? "success" :
            log.includes("[CHECK]") ? "info" : "muted";
        return `<div class="connection-log-entry ${level}">${log}</div>`;
    }).join("");
}

// Load available tools
async function loadTools() {
    if (!isLoggedIn()) {
        availableTools = [];
        return;
    }

    try {
        const response = await fetch("/api/agent/tools", {
            headers: getAgentHeaders()
        });
        availableTools = await response.json();

        const selector = document.getElementById("toolSelector");
        selector.innerHTML = '<option value="">-- Select an agent action --</option>';
        availableTools.forEach(tool => {
            const option = document.createElement("option");
            option.value = tool.name;
            option.textContent = `${tool.name} - ${tool.description}`;
            selector.appendChild(option);
        });

        addLog(`✓ Tools loaded successfully for ${agentSession.role}`, "success");
    } catch (error) {
        addLog(`✗ Error loading tools: ${error.message}`, "error");
    }
}

async function loadCoverageCatalog() {
    try {
        const response = await fetch("/api/coverage-options", {
            headers: getAgentHeaders()
        });
        coverageCatalog = await response.json();
        addLog(`✓ Loaded ${coverageCatalog.length} coverage definitions from remote MCP backend`, "success");
    } catch (error) {
        coverageCatalog = [];
        addLog(`✗ Error loading coverage definitions: ${error.message}`, "error");
    }
}

// Load tool schema and create form
function loadToolSchema() {
    const toolName = document.getElementById("toolSelector").value;
    if (!toolName) {
        document.getElementById("inputForm").innerHTML = "";
        document.getElementById("toolDocs").innerHTML =
            '<p class="loading">Select an agent action to view details</p>';
        return;
    }

    currentTool = availableTools.find(t => t.name === toolName);
    if (!currentTool) return;

    // Create input form
    createInputForm();

    // Display documentation
    displayToolDocs();

    addLog(`📋 Tool selected: ${toolName}`, "info");
}

// Create input form dynamically
function createInputForm() {
    const formHTML = Object.entries(currentTool.params).map(([paramName, paramType]) => `
        <div class="form-group-inline">
            <label for="param_${paramName}">
                ${paramName} 
                <small style="color: #999;">(${paramType})</small>
            </label>
            ${getInputElement(paramName, paramType)}
        </div>
    `).join("");

    document.getElementById("inputForm").innerHTML = formHTML;
}

// Get appropriate input element based on type
function getInputElement(paramName, paramType) {
    if (paramType.includes("array")) {
        return `<textarea id="param_${paramName}" placeholder="[&quot;option1&quot;, &quot;option2&quot;]"></textarea>`;
    } else if (paramType.startsWith("number")) {
        return `<input type="number" id="param_${paramName}" step="0.01" placeholder="0">`;
    } else if (paramType.includes("|")) {
        const options = paramType.split("|").map(opt => opt.trim());
        return `
            <select id="param_${paramName}">
                <option value="">-- Select --</option>
                ${options.map(opt => `<option value="${opt}">${opt}</option>`).join("")}
            </select>
        `;
    } else {
        return `<input type="text" id="param_${paramName}" placeholder="${paramType}">`;
    }
}

// Display tool documentation
function displayToolDocs() {
    const docHTML = `
        <div class="tool-doc">
            <div class="tool-doc-title">${currentTool.name}</div>
            <div class="tool-doc-description">${currentTool.description}</div>
            <div class="tool-doc-params">
                <pre>${JSON.stringify(currentTool.params, null, 2)}</pre>
            </div>
        </div>
    `;
    document.getElementById("toolDocs").innerHTML = docHTML;
}

function escapeHtml(value) {
    return String(value ?? "")
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#39;");
}

function formatCurrency(value) {
    const amount = Number(value || 0);
    return amount.toLocaleString("en-US", { style: "currency", currency: "USD" });
}

function normalizePolicies(result) {
    const rows = Array.isArray(result) ? result : result ? [result] : [];
    return rows.filter(item => item && item.id && item.customer_id && item.policy_type);
}

function getCoverageDetails(coverageIds) {
    const selectedCoverage = coverageIds || [];
    if (!selectedCoverage.length) {
        return '<p class="coverage-empty">No optional coverage selected for this policy.</p>';
    }

    return selectedCoverage.map(coverageId => {
        const coverage = coverageCatalog.find(item => item.id === coverageId);
        if (!coverage) {
            return `
                <div class="coverage-detail-card">
                    <strong>${escapeHtml(coverageId)}</strong>
                    <span>Coverage definition not found in the remote catalog.</span>
                </div>
            `;
        }

        return `
            <div class="coverage-detail-card">
                <strong>${escapeHtml(coverage.name)} <em>${escapeHtml(coverage.id)}</em></strong>
                <span>${escapeHtml(coverage.description)}</span>
                <small>Amount: ${formatCurrency(coverage.coverage_amount)} | Base price: ${formatCurrency(coverage.base_price)}</small>
            </div>
        `;
    }).join("");
}

function renderPolicyTable(result) {
    const policies = normalizePolicies(result);
    const container = document.getElementById("policyTableContent");

    if (!policies.length) {
        container.innerHTML = '<p class="loading">No policy table available for this MCP result. Review the raw output.</p>';
        return;
    }

    container.innerHTML = `
        <div class="policy-table-toolbar">
            <span>${policies.length} policy record${policies.length === 1 ? "" : "s"}</span>
            <input type="search" id="policyTableFilter" placeholder="Filter policy table" oninput="filterPolicyTable()">
        </div>
        <div class="policy-table-wrap">
            <table class="policy-table" id="policyTable">
                <thead>
                    <tr>
                        <th>Policy ID</th>
                        <th>Customer</th>
                        <th>Type</th>
                        <th>Status</th>
                        <th>Premium</th>
                        <th>Period</th>
                        <th>Limit</th>
                        <th>Details</th>
                    </tr>
                </thead>
                <tbody>
                    ${policies.map((policy, index) => `
                        <tr class="policy-row" data-policy-text="${escapeHtml(JSON.stringify(policy).toLowerCase())}">
                            <td>${escapeHtml(policy.id)}</td>
                            <td>${escapeHtml(policy.customer_id)}</td>
                            <td>${escapeHtml(policy.policy_type)}</td>
                            <td><span class="policy-status status-${escapeHtml(policy.status)}">${escapeHtml(policy.status)}</span></td>
                            <td>${formatCurrency(policy.premium)}</td>
                            <td>${escapeHtml(policy.start_date)} to ${escapeHtml(policy.end_date)}</td>
                            <td>${formatCurrency(policy.policy_limit)}</td>
                            <td><button class="btn btn-small" onclick="togglePolicyDetails(${index})">View</button></td>
                        </tr>
                        <tr class="policy-detail-row hidden" id="policyDetail${index}">
                            <td colspan="8">
                                <div class="policy-detail-grid">
                                    <div><strong>Deductible</strong><span>${formatCurrency(policy.deductible)}</span></div>
                                    <div class="coverage-detail-section"><strong>Coverage Details</strong>${getCoverageDetails(policy.coverage_options)}</div>
                                    <div><strong>Raw Policy</strong><pre>${escapeHtml(JSON.stringify(policy, null, 2))}</pre></div>
                                </div>
                            </td>
                        </tr>
                    `).join("")}
                </tbody>
            </table>
        </div>
    `;
}

function togglePolicyDetails(index) {
    document.getElementById(`policyDetail${index}`).classList.toggle("hidden");
}

function filterPolicyTable() {
    const filterText = document.getElementById("policyTableFilter").value.toLowerCase();
    document.querySelectorAll("#policyTable .policy-row").forEach(row => {
        const isMatch = row.dataset.policyText.includes(filterText);
        row.classList.toggle("hidden", !isMatch);
        const detailRow = row.nextElementSibling;
        if (detailRow && detailRow.classList.contains("policy-detail-row") && !isMatch) {
            detailRow.classList.add("hidden");
        }
    });
}

// Execute Policy Agent action
async function executeAgent() {
    if (!currentTool) {
        alert("Please select an agent action first");
        return;
    }

    // Collect parameters
    const params = {};
    Object.keys(currentTool.params).forEach(paramName => {
        const input = document.getElementById(`param_${paramName}`);
        if (input) {
            let value = input.value;

            // Parse JSON arrays
            if (currentTool.params[paramName].includes("array")) {
                try {
                    value = JSON.parse(value || "[]");
                } catch {
                    value = [];
                }
            }
            // Parse numbers
            else if (currentTool.params[paramName].startsWith("number")) {
                value = value ? parseFloat(value) : undefined;
            }

            if (value !== undefined) {
                params[paramName] = value;
            }
        }
    });

    clearLogs();
    addLog(`🚀 Policy Agent running: ${currentTool.name}`, "info");
    addLog(`📊 Parameters: ${JSON.stringify(params, null, 2)}`, "info");

    try {
        const response = await fetch("/api/agent/execute", {
            method: "POST",
            headers: { "Content-Type": "application/json", ...getAgentHeaders() },
            body: JSON.stringify({
                tool_name: currentTool.name,
                params: params
            })
        });

        const data = await response.json();

        // Add backend logs
        if (data.logs && Array.isArray(data.logs)) {
            data.logs.forEach(logMsg => {
                const level = logMsg.includes("[ERROR]") ? "error" :
                    logMsg.includes("[SUCCESS]") ? "success" :
                    logMsg.includes("[WARNING]") ? "warning" : "info";
                addLog(logMsg, level);
            });
        }

        // Display result
        const outputEl = document.getElementById("outputContent");
        if (data.success) {
            outputEl.textContent = JSON.stringify(data.result, null, 2);
            outputEl.className = "output-content success";
            renderPolicyTable(data.result);
            addLog("✅ Policy Agent completed successfully", "success");
        } else {
            outputEl.textContent = JSON.stringify({ error: data.error, result: data.result }, null, 2);
            outputEl.className = "output-content error";
            renderPolicyTable(null);
            addLog(`❌ Policy Agent failed: ${data.error}`, "error");
        }
    } catch (error) {
        addLog(`❌ Network error: ${error.message}`, "error");
        const outputEl = document.getElementById("outputContent");
        outputEl.textContent = JSON.stringify({ error: error.message }, null, 2);
        outputEl.className = "output-content error";
        renderPolicyTable(null);
    }
}

// Add log entry
function addLog(message, level = "info") {
    const timestamp = new Date().toLocaleTimeString();
    logs.push({ message, level, timestamp });

    const logsContainer = document.getElementById("logsContent");
    const logEntry = document.createElement("div");
    logEntry.className = `log-entry log-${level}`;
    logEntry.innerHTML = `
        <span class="log-timestamp">${timestamp}</span>
        <span class="log-message">${message}</span>
    `;
    logsContainer.appendChild(logEntry);
    logsContainer.scrollTop = logsContainer.scrollHeight;
}

// Clear logs
function clearLogs() {
    logs = [];
    document.getElementById("logsContent").innerHTML = "";
    addLog("Logs cleared. Policy Agent ready.", "info");
}

// Copy input to clipboard
function copyInput() {
    const params = {};
    Object.keys(currentTool.params).forEach(paramName => {
        const input = document.getElementById(`param_${paramName}`);
        if (input) params[paramName] = input.value;
    });
    copyToClipboard(JSON.stringify(params, null, 2));
}

// Copy output to clipboard
function copyOutput() {
    copyToClipboard(document.getElementById("outputContent").textContent);
}

// Copy to clipboard utility
function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(() => {
        alert("Copied to clipboard!");
    }).catch(err => {
        console.error("Failed to copy:", err);
    });
}
