// Policy Agent JavaScript

let availableTools = [];
let currentTool = null;
let logs = [];

// Load tools on page load
document.addEventListener("DOMContentLoaded", async () => {
    await loadTools();
});

// Load available tools
async function loadTools() {
    try {
        const response = await fetch("/api/agent/tools");
        availableTools = await response.json();

        const selector = document.getElementById("toolSelector");
        selector.innerHTML = '<option value="">-- Select an agent action --</option>';
        availableTools.forEach(tool => {
            const option = document.createElement("option");
            option.value = tool.name;
            option.textContent = `${tool.name} - ${tool.description}`;
            selector.appendChild(option);
        });

        addLog("✓ Tools loaded successfully", "success");
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
            headers: { "Content-Type": "application/json" },
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
