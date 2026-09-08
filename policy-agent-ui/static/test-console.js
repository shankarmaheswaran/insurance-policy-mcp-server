// Policy Agent JavaScript

let availableTools = [];
let currentTool = null;
let logs = [];
let loginOptions = [];
let agentSession = {
    username: localStorage.getItem("policyAgentUsername") || "consumer01",
    role: localStorage.getItem("policyAgentRole") || "consumer",
    customerId: localStorage.getItem("policyAgentCustomerId") || "CUST-001"
};

// Load tools on page load
document.addEventListener("DOMContentLoaded", async () => {
    restoreAgentSession();
    await loadLoginOptions();
    await verifyConnection();
    await loadTools();
});

function getAgentHeaders() {
    const headers = {
        "X-Policy-Agent-Role": agentSession.role
    };
    if (agentSession.customerId) {
        headers["X-Policy-Agent-Customer-Id"] = agentSession.customerId;
    }
    return headers;
}

function restoreAgentSession() {
    const roleInput = document.querySelector(`input[name="agentRole"][value="${agentSession.role}"]`);
    if (roleInput) {
        roleInput.checked = true;
    }
    document.getElementById("customerScope").value = agentSession.customerId;
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
        const customerText = login.customer_id ? ` (${login.customer_id})` : "";
        return `<option value="${login.username}">${login.username} - ${login.display_name}${customerText}</option>`;
    }).join("");

    const matchingLogin = roleLogins.find(login => login.username === agentSession.username) || roleLogins[0];
    if (matchingLogin) {
        selector.value = matchingLogin.username;
        applySelectedLogin(matchingLogin);
    }
}

function handleLoginSelection() {
    const selectedLogin = getSelectedLogin();
    if (selectedLogin) {
        applySelectedLogin(selectedLogin);
    }
}

function getSelectedLogin() {
    const username = document.getElementById("loginSelector").value;
    return loginOptions.find(login => login.username === username);
}

function applySelectedLogin(login) {
    agentSession.username = login.username;
    agentSession.role = login.role;
    agentSession.customerId = login.customer_id || "";
    document.getElementById("customerScope").value = agentSession.customerId;
    updateRoleDisplay();
}

function loginAgent() {
    const selectedRole = document.querySelector('input[name="agentRole"]:checked').value;
    const selectedLogin = getSelectedLogin();
    const customerId = document.getElementById("customerScope").value.trim();

    agentSession = {
        username: selectedLogin ? selectedLogin.username : `${selectedRole}-manual`,
        role: selectedRole,
        customerId: selectedRole === "consumer" && selectedLogin ? selectedLogin.customer_id : customerId
    };
    localStorage.setItem("policyAgentUsername", agentSession.username);
    localStorage.setItem("policyAgentRole", agentSession.role);
    localStorage.setItem("policyAgentCustomerId", agentSession.customerId);

    updateRoleDisplay();
    clearLogs();
    addLog(`[AUTH] Logged in as ${agentSession.role}${agentSession.customerId ? ` with customer scope ${agentSession.customerId}` : ""}`, "success");
    verifyConnection();
    loadTools();
}

function logoutAgent() {
    localStorage.removeItem("policyAgentUsername");
    localStorage.removeItem("policyAgentRole");
    localStorage.removeItem("policyAgentCustomerId");
    agentSession = { username: "consumer01", role: "consumer", customerId: "CUST-001" };
    restoreAgentSession();
    populateLoginSelect();
    clearLogs();
    addLog("[AUTH] Logged out. Defaulted to consumer role.", "info");
    verifyConnection();
    loadTools();
}

function updateRoleDisplay() {
    const activeRole = document.getElementById("activeRole");
    activeRole.textContent = agentSession.role === "consumer" && agentSession.customerId
        ? `Signed in: ${agentSession.username} / consumer (${agentSession.customerId})`
        : `Signed in: ${agentSession.username} / ${agentSession.role}`;
    document.getElementById("roleLoginSection").dataset.role = agentSession.role;
}

// Verify remote MCP backend connection
async function verifyConnection() {
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
    } else if (paramType === "number") {
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
            else if (currentTool.params[paramName] === "number") {
                value = value ? parseFloat(value) : 0;
            }

            params[paramName] = value;
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
            addLog("✅ Policy Agent completed successfully", "success");
        } else {
            outputEl.textContent = JSON.stringify({ error: data.error, result: data.result }, null, 2);
            outputEl.className = "output-content error";
            addLog(`❌ Policy Agent failed: ${data.error}`, "error");
        }
    } catch (error) {
        addLog(`❌ Network error: ${error.message}`, "error");
        const outputEl = document.getElementById("outputContent");
        outputEl.textContent = JSON.stringify({ error: error.message }, null, 2);
        outputEl.className = "output-content error";
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
