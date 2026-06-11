document.addEventListener('DOMContentLoaded', () => {
    const token = localStorage.getItem('access_token');
    if (token) showDashboard();
});

let isLoginMode = true;
const API_URL = 'http://localhost:8000';
let sentimentChartInstance = null;

// Auth Toggles
function toggleAuthMode() {
    isLoginMode = !isLoginMode;
    const usernameGroup = document.getElementById('username-group');
    const authBtn = document.getElementById('auth-btn');
    const toggleLink = document.querySelector('.auth-toggle a');
    
    document.getElementById('auth-error').classList.add('hidden');

    if (isLoginMode) {
        usernameGroup.classList.add('hidden');
        authBtn.innerText = "Authenticate";
        toggleLink.innerText = "Request Access";
    } else {
        usernameGroup.classList.remove('hidden');
        authBtn.innerText = "Register Institutional Profile";
        toggleLink.innerText = "Sign in here";
    }
}

// Workflow Toggles
function toggleWorkflow(id) {
    const el = document.getElementById(id);
    el.classList.toggle('hidden');
}

// Authentication
async function handleAuth() {
    const emailInput = document.getElementById('auth-email').value.trim();
    const passwordInput = document.getElementById('auth-password').value.trim();
    const usernameInput = document.getElementById('auth-username').value.trim();
    const errorDisplay = document.getElementById('auth-error');
    
    errorDisplay.classList.add('hidden');

    try {
        if (isLoginMode) {
            // Login
            // Backend schema: email and password (json)
            const payload = { 
                email: emailInput, 
                password: passwordInput 
            };

            const response = await fetch(`${API_URL}/auth/login`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            if (!response.ok) {
                const err = await response.json();
                throw new Error(err.detail || "Invalid credentials.");
            }
            
            const data = await response.json();
            localStorage.setItem('access_token', data.access_token);
            showDashboard();

        } else {
            // Signuo
            // Backend schema - email, username, password (json)
            const payload = { 
                email: emailInput, 
                username: usernameInput, 
                password: passwordInput 
            };

            const response = await fetch(`${API_URL}/auth/register`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            if (!response.ok) {
                const err = await response.json();
                // Extract Pydantic validation errors nicely
                let errMsg = "Registration failed.";
                if (err.detail && Array.isArray(err.detail)) {
                    errMsg = err.detail[0].msg; // Catch Pydantic length/format errors
                } else if (err.detail) {
                    errMsg = err.detail; // Catch 409 Conflict duplicate errors
                }
                throw new Error(errMsg);
            }

            // Auto-login after successful register
            isLoginMode = true; 
            await handleAuth(); 
        }

    } catch (error) {
        errorDisplay.innerText = error.message;
        errorDisplay.classList.remove('hidden');
    }
}

function handleLogout() {
    localStorage.removeItem('access_token');
    document.getElementById('dashboard-view').classList.add('hidden');
    document.getElementById('auth-view').classList.remove('hidden');
}

function showDashboard() {
    document.getElementById('auth-view').classList.add('hidden');
    document.getElementById('dashboard-view').classList.remove('hidden');
}

// Analysis & Polling
let pollingInterval;

async function startAnalysis() {
    const ticker = document.getElementById('ticker-input').value.trim().toUpperCase();
    if (!ticker) return alert("Please specify a ticker.");

    const token = localStorage.getItem('access_token');
    if (!token) { handleLogout(); return; }

    document.getElementById('dashboard-content').classList.add('hidden');
    document.getElementById('loading-state').classList.remove('hidden');
    document.getElementById('status-headline').innerText = `Compiling Report: ${ticker}`;
    
    clearInterval(pollingInterval);

    try {
        const response = await fetch(`${API_URL}/analysis/analyze`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
            body: JSON.stringify({ ticker: ticker })
        });

        if (response.status === 401) throw new Error("Unauthorized");
        if (!response.ok) throw new Error("Execution failed.");

        const data = await response.json();
        pollAnalysisStatus(data.job_id, token);

    } catch (error) {
        document.getElementById('loading-state').classList.add('hidden');
        if (error.message === "Unauthorized") handleLogout();
    }
}

async function pollAnalysisStatus(jobId, token) {
    const statusHeadline = document.getElementById('status-headline');
    const statusSubtext = document.getElementById('status-subtext');

    pollingInterval = setInterval(async () => {
        try {
            const response = await fetch(`${API_URL}/analysis/status/${jobId}`, {
                headers: { 'Authorization': `Bearer ${token}` }
            });

            if (!response.ok) throw new Error("Polling failed");
            
            const data = await response.json();

            if (data.status === "running") {
                statusHeadline.innerText = "Agents Executing...";
                statusSubtext.innerText = "SEC, Market, Risk, and Sentiment agents are processing data.";
            } 
            else if (data.status === "done") {
                // 1. Stop polling
                clearInterval(pollingInterval);
                
                // 2. Populate the UI with the backend JSON result
                populateDashboard(data.result);
                
                // 3. Hide loading, show dashboard
                document.getElementById('loading-state').classList.add('hidden');
                document.getElementById('dashboard-content').classList.remove('hidden');
            }
            else if (data.status === "error") {
                clearInterval(pollingInterval);
                document.getElementById('loading-state').classList.add('hidden');
                alert(`Analysis Error: ${data.error}`);
            }

        } catch (error) {
            console.error("Polling error:", error);
        }
    }, 3000); // Poll every 3 seconds
}

// Render Data
function populateDashboard(data) {
    const fill = (id, val) => document.getElementById(id).innerText = val || "--";

    fill('ticker-display', data.ticker);
    fill('company-display', data.company);
    fill('recommendation-display', data.recommendation);
    fill('risk-display', data.risk_rating);
    fill('sentiment-display', data.sentiment);
    
    fill('sec-analysis-display', data.sec_analysis);
    fill('revenue-display', data.revenue);
    fill('net-income-display', data.net_income);
    fill('assets-display', data.total_assets);
    fill('margin-display', data.profit_margin);

    fill('market-analysis-display', data.market_analysis);
    fill('market-cap-display', data.market_cap);
    fill('trend-display', data.trend);
    fill('beta-display', data.beta);
    fill('roe-display', data.roe);

    fill('risk-analysis-display', data.risk_analysis);
    fill('news-analysis-display', data.news_analysis);
    fill('summary-display', data.summary);

    const fullSummary = data.summary || "Report generation complete. Review metrics above.";
    if (fullSummary.length > 0) {
        document.getElementById('summary-dropcap').innerText = fullSummary.charAt(0);
        document.getElementById('summary-display').innerText = fullSummary.substring(1);
    }

    // Populate Bull / Bear Lists
    const makeList = (id, items) => {
        const el = document.getElementById(id);
        el.innerHTML = '';
        if (!items || items.length === 0) {
            el.innerHTML = '<li>No significant catalysts flagged in current dataset.</li>';
            return;
        }
        items.forEach(i => {
            let li = document.createElement('li'); 
            li.innerText = i; 
            el.appendChild(li);
        });
    };
    makeList('risks-list', data.risks);
    makeList('opportunities-list', data.opportunities);

    // Populate Final Verdict Strip dynamically based on AI recommendation
    const verdictEl = document.getElementById('verdict-display');
    const rec = data.recommendation ? data.recommendation.toUpperCase() : "HOLD";
    
    // verdict
    if (rec === "BUY") {
        verdictEl.innerText = "INITIATE / MAINTAIN LONG POSITION";
        verdictEl.style.color = "#84cc94";
    } else if (rec === "SELL") {
        verdictEl.innerText = "LIQUIDATE / MAINTAIN SHORT POSITION";
        verdictEl.style.color = "#cc8484"; 
    } else {
        verdictEl.innerText = "MAINTAIN CURRENT HOLDINGS";
        verdictEl.style.color = "#e5cd78";
    }
}


// Render Final Visual Chart (Bar Chart mapping to -1 to 1 Sentiment Score)
function renderChart(sentimentScore) {
    const ctx = document.getElementById('sentimentChart').getContext('2d');
    
    if (sentimentChartInstance) { sentimentChartInstance.destroy(); }

    const isPositive = sentimentScore >= 0;
    const color = isPositive ? '#79977c' : '#e5cd78';

    sentimentChartInstance = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: ['Sentiment NLP Score (-1 to 1)'],
            datasets: [{
                label: 'AI Confidence',
                data: [sentimentScore],
                backgroundColor: color,
                borderColor: '#222',
                borderWidth: 2
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: { min: -1, max: 1, grid: { color: '#ccc' } }
            },
            plugins: {
                legend: { display: false }
            }
        }
    });
}