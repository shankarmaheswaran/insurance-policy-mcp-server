// API endpoints
const API_BASE = "/api";

// Tab switching
function switchTab(tabName) {
    document.querySelectorAll(".tab-content").forEach(tab => {
        tab.classList.remove("active");
    });
    document.querySelectorAll(".tab-button").forEach(btn => {
        btn.classList.remove("active");
    });

    document.getElementById(tabName + "-tab").classList.add("active");
    event.target.classList.add("active");

    if (tabName === "policies") {
        loadPolicies();
        loadStats();
    } else if (tabName === "claims") {
        loadClaims();
        loadStats();
    } else if (tabName === "create-policy") {
        loadCoverageOptions();
    }
}

// Load statistics
async function loadStats() {
    try {
        const response = await fetch(`${API_BASE}/stats`);
        const data = await response.json();
        document.getElementById("totalPolicies").textContent = data.total_policies;
        document.getElementById("activePolicies").textContent = data.active_policies;
        document.getElementById("totalClaims").textContent = data.total_claims;
        document.getElementById("approvedClaims").textContent = data.approved_claims;
    } catch (error) {
        console.error("Error loading stats:", error);
    }
}

// Load policies
async function loadPolicies(customerId = null) {
    try {
        const url = customerId ? `${API_BASE}/policies?customer_id=${customerId}` : `${API_BASE}/policies`;
        const response = await fetch(url);
        const policies = await response.json();

        const container = document.getElementById("policiesList");
        if (policies.length === 0) {
            container.innerHTML = "<p class='loading'>No policies found</p>";
            return;
        }

        container.innerHTML = policies.map(policy => `
            <div class="list-item">
                <div class="list-item-header">
                    <div class="list-item-title">${policy.id}</div>
                    <span class="list-item-status status-${policy.status}">${policy.status.toUpperCase()}</span>
                </div>
                <div class="list-item-details">
                    <div class="detail">
                        <div class="detail-label">Customer</div>
                        <div class="detail-value">${policy.customer_id}</div>
                    </div>
                    <div class="detail">
                        <div class="detail-label">Type</div>
                        <div class="detail-value">${policy.policy_type}</div>
                    </div>
                    <div class="detail">
                        <div class="detail-label">Premium</div>
                        <div class="detail-value">$${policy.premium.toFixed(2)}</div>
                    </div>
                    <div class="detail">
                        <div class="detail-label">Period</div>
                        <div class="detail-value">${policy.start_date} to ${policy.end_date}</div>
                    </div>
                    <div class="detail">
                        <div class="detail-label">Deductible</div>
                        <div class="detail-value">$${policy.deductible.toFixed(2)}</div>
                    </div>
                    <div class="detail">
                        <div class="detail-label">Limit</div>
                        <div class="detail-value">$${policy.policy_limit.toFixed(2)}</div>
                    </div>
                </div>
            </div>
        `).join("");
    } catch (error) {
        console.error("Error loading policies:", error);
        document.getElementById("policiesList").innerHTML = "<p class='loading error'>Error loading policies</p>";
    }
}

// Filter policies
function filterPolicies() {
    const customerId = document.getElementById("customerFilter").value;
    if (customerId) {
        loadPolicies(customerId);
    } else {
        loadPolicies();
    }
}

// Load claims
async function loadClaims(policyId = null) {
    try {
        const url = policyId ? `${API_BASE}/claims?policy_id=${policyId}` : `${API_BASE}/claims`;
        const response = await fetch(url);
        const claims = await response.json();

        const container = document.getElementById("claimsList");
        if (claims.length === 0) {
            container.innerHTML = "<p class='loading'>No claims found</p>";
            return;
        }

        container.innerHTML = claims.map(claim => `
            <div class="list-item">
                <div class="list-item-header">
                    <div class="list-item-title">${claim.id}</div>
                    <span class="list-item-status status-${claim.status}">${claim.status.toUpperCase()}</span>
                </div>
                <div class="list-item-details">
                    <div class="detail">
                        <div class="detail-label">Policy</div>
                        <div class="detail-value">${claim.policy_id}</div>
                    </div>
                    <div class="detail">
                        <div class="detail-label">Type</div>
                        <div class="detail-value">${claim.claim_type}</div>
                    </div>
                    <div class="detail">
                        <div class="detail-label">Amount</div>
                        <div class="detail-value">$${claim.amount.toFixed(2)}</div>
                    </div>
                    <div class="detail">
                        <div class="detail-label">Date</div>
                        <div class="detail-value">${claim.claim_date}</div>
                    </div>
                    <div class="detail">
                        <div class="detail-label">Description</div>
                        <div class="detail-value">${claim.description}</div>
                    </div>
                </div>
            </div>
        `).join("");
    } catch (error) {
        console.error("Error loading claims:", error);
        document.getElementById("claimsList").innerHTML = "<p class='loading error'>Error loading claims</p>";
    }
}

// Filter claims
function filterClaims() {
    const policyId = document.getElementById("policyFilter").value;
    if (policyId) {
        loadClaims(policyId);
    } else {
        loadClaims();
    }
}

// Load coverage options
async function loadCoverageOptions() {
    try {
        const response = await fetch(`${API_BASE}/coverage-options`);
        const options = await response.json();

        const container = document.getElementById("coverageOptions");
        container.innerHTML = options.map(option => `
            <label>
                <input type="checkbox" name="coverage_options" value="${option.id}">
                ${option.name} <small>($${option.base_price}/mo, $${option.coverage_amount} coverage)</small>
            </label>
        `).join("");
    } catch (error) {
        console.error("Error loading coverage options:", error);
    }
}

// Create policy
document.getElementById("policyForm")?.addEventListener("submit", async (e) => {
    e.preventDefault();

    const coverageOptions = Array.from(document.querySelectorAll("input[name='coverage_options']:checked"))
        .map(input => input.value);

    const policyData = {
        customer_id: document.getElementById("customerId").value,
        policy_type: document.getElementById("policyType").value,
        start_date: document.getElementById("startDate").value,
        end_date: document.getElementById("endDate").value,
        premium: parseFloat(document.getElementById("premium").value),
        deductible: parseFloat(document.getElementById("deductible").value),
        policy_limit: parseFloat(document.getElementById("policyLimit").value),
        coverage_options: coverageOptions,
    };

    try {
        const response = await fetch(`${API_BASE}/policies`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(policyData),
        });

        const messageEl = document.getElementById("formMessage");
        if (response.ok) {
            messageEl.textContent = "✓ Policy created successfully!";
            messageEl.className = "message show success";
            document.getElementById("policyForm").reset();
            loadPolicies();
            loadStats();
            setTimeout(() => messageEl.classList.remove("show"), 5000);
        } else {
            const error = await response.json();
            messageEl.textContent = "✗ Error: " + error.error;
            messageEl.className = "message show error";
        }
    } catch (error) {
        console.error("Error creating policy:", error);
        const messageEl = document.getElementById("formMessage");
        messageEl.textContent = "✗ Error: " + error.message;
        messageEl.className = "message show error";
    }
});

// Initialize on page load
document.addEventListener("DOMContentLoaded", () => {
    loadPolicies();
    loadStats();
});
