// TRAX-AI — app.js
// All backend integration points are marked with: // API:

const API = 'http://127.0.0.1:8000';

// ── STATE ────────────────────────────────────────────────
const state = {
  token: sessionStorage.getItem('trax_token') || null,
  user: JSON.parse(sessionStorage.getItem('trax_user') || 'null'),
  currentReport: null,
  pollTimer: null,
  charts: {},
};

// ── VIEW ROUTER ──────────────────────────────────────────
function showView(name) {
  document.getElementById('auth-view').classList.add('hidden');
  document.getElementById('app-shell').classList.add('hidden');
  document.getElementById('workspace-view').classList.add('hidden');
  document.getElementById('dashboard-view').classList.add('hidden');
  document.getElementById('progress-card').classList.add('hidden');

  if (name === 'auth') {
    document.getElementById('auth-view').classList.remove('hidden');
  } else {
    document.getElementById('app-shell').classList.remove('hidden');
    if (name === 'workspace') {
      document.getElementById('workspace-view').classList.remove('hidden');
    } else if (name === 'dashboard') {
      document.getElementById('dashboard-view').classList.remove('hidden');
    }
  }
}

// ── AUTH ─────────────────────────────────────────────────
document.querySelectorAll('.auth-tab').forEach(tab => {
  tab.addEventListener('click', () => {
    document.querySelectorAll('.auth-tab').forEach(t => t.classList.remove('active'));
    tab.classList.add('active');
    document.getElementById('login-form').classList.toggle('hidden', tab.dataset.tab !== 'login');
    document.getElementById('register-form').classList.toggle('hidden', tab.dataset.tab !== 'register');
    document.getElementById('auth-error').style.display = 'none';
  });
});

document.getElementById('login-form').addEventListener('submit', async (e) => {
  e.preventDefault();
  const email = document.getElementById('login-email').value.trim();
  const password = document.getElementById('login-password').value;
  const btn = e.target.querySelector('button');
  btn.disabled = true; btn.textContent = 'Signing in...';

  try {
    // API: POST /auth/login
    const res = await fetch(`${API}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Login failed');

    state.token = data.access_token;
    sessionStorage.setItem('trax_token', state.token);

    // API: GET /auth/me — get user profile
    const me = await authFetch('/auth/me');
    state.user = me;
    sessionStorage.setItem('trax_user', JSON.stringify(me));
    document.getElementById('nav-username').textContent = me.username;

    showView('workspace');
    loadHistory();
  } catch (err) {
    showAuthError(err.message);
  } finally {
    btn.disabled = false; btn.textContent = 'Sign in';
  }
});

document.getElementById('register-form').addEventListener('submit', async (e) => {
  e.preventDefault();
  const email    = document.getElementById('reg-email').value.trim();
  const username = document.getElementById('reg-username').value.trim();
  const password = document.getElementById('reg-password').value;
  const btn = e.target.querySelector('button');
  btn.disabled = true; btn.textContent = 'Creating account...';

  try {
    // API: POST /auth/register
    const res = await fetch(`${API}/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, username, password }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Registration failed');

    // Auto-login after register — switch to login tab
    document.querySelector('[data-tab="login"]').click();
    document.getElementById('login-email').value = email;
    showAuthError('Account created. Sign in below.', 'success');
  } catch (err) {
    showAuthError(err.message);
  } finally {
    btn.disabled = false; btn.textContent = 'Create account';
  }
});

function showAuthError(msg, type = 'error') {
  const el = document.getElementById('auth-error');
  el.textContent = msg;
  el.style.display = 'block';
  if (type === 'success') { el.style.color = 'var(--bull)'; el.style.borderColor = 'rgba(16,185,129,0.3)'; }
}

document.getElementById('logout-btn').addEventListener('click', () => {
  state.token = null; state.user = null;
  sessionStorage.clear();
  showView('auth');
});

// ── AUTHENTICATED FETCH HELPER ───────────────────────────
async function authFetch(path, options = {}) {
  const res = await fetch(`${API}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${state.token}`,
      ...(options.headers || {}),
    },
  });
  if (res.status === 401) { showView('auth'); throw new Error('Session expired'); }
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || 'Request failed');
  return data;
}

// ── TICKER SEARCH ─────────────────────────────────────────
function setupSearch() {
  const handleSubmit = (input) => {
    const ticker = input.value.trim().toUpperCase();
    if (!ticker) return;
    startAnalysis(ticker);
  };

  document.getElementById('workspace-search').addEventListener('keydown', (e) => {
    if (e.key === 'Enter') handleSubmit(e.target);
  });
  document.getElementById('search-submit-btn').addEventListener('click', () => {
    handleSubmit(document.getElementById('workspace-search'));
  });
  document.getElementById('nav-search-input').addEventListener('keydown', (e) => {
    if (e.key === 'Enter') handleSubmit(e.target);
  });
}

// ── ANALYSIS FLOW ─────────────────────────────────────────
const STEPS = [
  { id: 'step-sec',     label: 'Querying SEC EDGAR Core Data...' },
  { id: 'step-market',  label: 'Running Quantitative Technical Indicators...' },
  { id: 'step-finbert', label: 'Executing FinBERT News Sentiment Vectoring...' },
  { id: 'step-synth',   label: 'Synthesizing Final Portfolio Recommendation...' },
];
const STEP_TIMES = [8000, 18000, 30000, 50000]; // approx when each step lights up

async function startAnalysis(ticker) {
  document.getElementById('workspace-view').classList.remove('hidden');
  document.getElementById('dashboard-view').classList.add('hidden');
  document.getElementById('progress-card').classList.remove('hidden');

  // Reset stepper
  STEPS.forEach(s => {
    const row = document.getElementById(s.id);
    row.classList.remove('active', 'done');
    row.querySelector('.step-icon').textContent = '○';
    row.querySelector('.step-time').textContent = '';
  });

  document.getElementById('stepper-ticker').textContent = ticker;
  const startTime = Date.now();

  // Light up steps progressively based on time
  STEP_TIMES.forEach((ms, i) => {
    setTimeout(() => {
      if (i > 0) {
        const prev = document.getElementById(STEPS[i - 1].id);
        prev.classList.remove('active');
        prev.classList.add('done');
        prev.querySelector('.step-icon').textContent = '✓';
        prev.querySelector('.step-time').textContent = formatElapsed(Date.now() - startTime);
      }
      document.getElementById(STEPS[i].id).classList.add('active');
      document.getElementById(STEPS[i].id).querySelector('.step-icon').textContent = '◉';
    }, ms);
  });

  try {
    // API: POST /analysis/analyze — returns job_id instantly
    const job = await authFetch('/analysis/analyze', {
      method: 'POST',
      body: JSON.stringify({ ticker }),
    });

    pollJobStatus(job.job_id, ticker, startTime);
  } catch (err) {
    showToast('Analysis Failed', err.message);
  }
}

function pollJobStatus(jobId, ticker, startTime) {
  if (state.pollTimer) clearInterval(state.pollTimer);

  // API: GET /analysis/status/{job_id} — polled every 3 seconds
  state.pollTimer = setInterval(async () => {
    try {
      const status = await authFetch(`/analysis/status/${jobId}`);

      if (status.status === 'done') {
        clearInterval(state.pollTimer);

        // Mark all steps done
        STEPS.forEach(s => {
          const row = document.getElementById(s.id);
          row.classList.remove('active');
          row.classList.add('done');
          row.querySelector('.step-icon').textContent = '✓';
        });
        document.getElementById(STEPS[3].id).querySelector('.step-time').textContent =
          formatElapsed(Date.now() - startTime);

        // Small pause so user sees completion, then render dashboard
        setTimeout(() => renderDashboard(status.result, ticker), 600);

      } else if (status.status === 'error') {
        clearInterval(state.pollTimer);
        const errMsg = status.error || 'Unknown error';
        if (errMsg.toLowerCase().includes('sec') || errMsg.toLowerCase().includes('cik')) {
          showToast('International Ticker', 'SEC EDGAR handles US securities exclusively. Support for international exchanges is currently in development.');
        } else {
          showToast('Analysis Failed', errMsg);
        }
      }
    } catch (err) {
      clearInterval(state.pollTimer);
      showToast('Connection Error', err.message);
    }
  }, 3000);
}

function formatElapsed(ms) {
  const s = Math.floor(ms / 1000);
  return s < 60 ? `${s}s` : `${Math.floor(s/60)}m ${s%60}s`;
}

// ── DASHBOARD RENDER ──────────────────────────────────────
async function renderDashboard(report, ticker) {
  state.currentReport = report;

  document.getElementById('workspace-view').classList.add('hidden');
  document.getElementById('dashboard-view').classList.remove('hidden');

  // Destroy all existing charts to avoid canvas reuse errors
  Object.values(state.charts).forEach(c => c.destroy());
  state.charts = {};

  // ── HERO ──────────────────────────────────────────────
  document.getElementById('d-ticker').textContent = ticker;
  document.getElementById('d-company').textContent = report.company || ticker;
  document.getElementById('d-summary-text').textContent = report.summary || '';

  const rec = (report.recommendation || 'HOLD').toUpperCase();
  const risk = (report.risk_rating || 'MEDIUM').toUpperCase();
  const sentiment = report.sentiment || 'NEUTRAL';

  const recEl = document.getElementById('d-recommendation');
  recEl.textContent = rec;
  recEl.className = `badge badge-${rec.toLowerCase()}`;

  const riskEl = document.getElementById('d-risk');
  riskEl.textContent = `${risk} RISK`;
  riskEl.className = `badge badge-${risk.toLowerCase()}`;

  const sentEl = document.getElementById('d-sentiment-badge');
  sentEl.textContent = sentiment;
  const sentClass = sentiment === 'POSITIVE' ? 'bull' : sentiment === 'NEGATIVE' ? 'bear' : 'muted';
  sentEl.className = sentClass;

  // ── PRICE CHART ───────────────────────────────────────
  try {
    // API: GET /analysis/price-history/{ticker}
    const priceData = await authFetch(`/analysis/price-history/${ticker}`);
    renderPriceChart(priceData);
  } catch (_) {}

  // ── SEC CARD ──────────────────────────────────────────
  const secText = report.sec_analysis || '';
  document.getElementById('d-sec-text').textContent = secText;

  const metrics = report.metrics || {};
  document.getElementById('d-revenue').textContent   = metrics.revenue   || 'N/A';
  document.getElementById('d-netincome').textContent = metrics.net_income || 'N/A';
  document.getElementById('d-assets').textContent    = metrics.total_assets || 'N/A';
  document.getElementById('d-margin').textContent    = metrics.profit_margin || 'N/A';
  document.getElementById('d-debt').textContent      = metrics.debt_ratio || 'N/A';
  renderRevenueChart(metrics);

  // ── MARKET CARD ───────────────────────────────────────
  document.getElementById('d-market-text').textContent = report.market_analysis || '';
  renderMAChart(metrics);
  renderPEGauge(metrics.pe_ratio);

  document.getElementById('d-price').textContent = metrics.current_price || 'N/A';
  document.getElementById('d-marketcap').textContent = metrics.market_cap || 'N/A';
  document.getElementById('d-beta').textContent = metrics.beta || 'N/A';
  document.getElementById('d-roe').textContent = metrics.roe || 'N/A';
  document.getElementById('d-trend').textContent = metrics.trend || 'N/A';
  const trendEl = document.getElementById('d-trend');
  if ((metrics.trend || '').includes('UPTREND')) trendEl.classList.add('bull');
  else if ((metrics.trend || '').includes('DOWNTREND')) trendEl.classList.add('bear');

  // ── FINBERT CARD ──────────────────────────────────────
  document.getElementById('d-news-text').textContent = report.news_analysis || '';
  const score = typeof report.sentiment_score === 'number' ? report.sentiment_score : 0;
  renderSentimentGauge(score);
  renderEventBars(report.detected_events || []);

  // ── RISK CARD ─────────────────────────────────────────
  document.getElementById('d-risk-text').textContent = report.risk_analysis || '';
  renderRadarChart(metrics);
  renderRiskDimensions(metrics);

  // ── SYNTHESIS ─────────────────────────────────────────
  renderRisksOpps(report.risks || [], report.opportunities || []);

  // Load history sidebar
  loadHistory();
}

// ── CHART: PRICE LINE ─────────────────────────────────────
function renderPriceChart(data) {
  const ctx = document.getElementById('chart-price').getContext('2d');
  const labels = data.labels || [];
  const prices = data.prices || [];

  // Sample down for performance — show max 60 points
  const step = Math.max(1, Math.floor(labels.length / 60));
  const sampledLabels = labels.filter((_, i) => i % step === 0);
  const sampledPrices = prices.filter((_, i) => i % step === 0);

  state.charts.price = new Chart(ctx, {
    type: 'line',
    data: {
      labels: sampledLabels,
      datasets: [{
        data: sampledPrices,
        borderColor: '#7C3AED',
        borderWidth: 2,
        fill: true,
        backgroundColor: (ctx) => {
          const g = ctx.chart.ctx.createLinearGradient(0, 0, 0, 200);
          g.addColorStop(0, 'rgba(124,58,237,0.2)');
          g.addColorStop(1, 'rgba(124,58,237,0)');
          return g;
        },
        pointRadius: 0,
        tension: 0.3,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false }, tooltip: {
        callbacks: { label: (c) => `$${c.parsed.y.toFixed(2)}` }
      }},
      scales: {
        x: { display: false },
        y: {
          grid: { color: 'rgba(30,45,74,0.8)' },
          ticks: { color: '#64748B', font: { family: 'JetBrains Mono', size: 10 },
            callback: (v) => `$${v}` },
        },
      },
    },
  });

  // Show current price from last data point
  if (sampledPrices.length) {
    const last = sampledPrices[sampledPrices.length - 1];
    const first = sampledPrices[0];
    const change = last - first;
    const changePct = ((change / first) * 100).toFixed(2);
    document.getElementById('d-price').textContent = `$${last.toFixed(2)}`;
    const changeEl = document.getElementById('d-price-change');
    changeEl.textContent = `${change >= 0 ? '+' : ''}${change.toFixed(2)} (${changePct}%) YTD`;
    changeEl.className = `hero-change ${change >= 0 ? 'bull' : 'bear'}`;
  }
}

// ── CHART: MA OVERLAY ─────────────────────────────────────
function renderMAChart(metrics) {
  const ctx = document.getElementById('chart-ma').getContext('2d');
  // Build synthetic MA chart using known values + simulated curve
  const ma50  = parseFloat((metrics.ma50  || '0').replace('$','')) || 170;
  const ma200 = parseFloat((metrics.ma200 || '0').replace('$','')) || 160;

  const labels = Array.from({length: 20}, (_, i) => `W${i+1}`);
  const ma50Data  = labels.map((_, i) => ma50  + Math.sin(i * 0.3) * 3);
  const ma200Data = labels.map((_, i) => ma200 + Math.sin(i * 0.15) * 2);

  const isBull = ma50 > ma200;

  state.charts.ma = new Chart(ctx, {
    type: 'line',
    data: {
      labels,
      datasets: [
        {
          label: '50-day MA',
          data: ma50Data,
          borderColor: isBull ? '#10B981' : '#EF4444',
          borderWidth: 2,
          pointRadius: 0,
          tension: 0.4,
        },
        {
          label: '200-day MA',
          data: ma200Data,
          borderColor: '#64748B',
          borderWidth: 1.5,
          borderDash: [4, 4],
          pointRadius: 0,
          tension: 0.4,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { labels: { color: '#64748B', font: { size: 10 }, boxWidth: 12 } },
        tooltip: { mode: 'index' },
      },
      scales: {
        x: { ticks: { color: '#64748B', font: { size: 9 } }, grid: { color: 'rgba(30,45,74,0.8)' } },
        y: { ticks: { color: '#64748B', font: { size: 9 }, callback: v => `$${v.toFixed(0)}` },
             grid: { color: 'rgba(30,45,74,0.8)' } },
      },
    },
  });

  document.getElementById('d-cross-label').textContent = isBull ? '🚀 Golden Cross' : '☠️ Death Cross';
  document.getElementById('d-cross-label').className = isBull ? 'chip active' : 'chip';
  document.getElementById('d-ma50-val').textContent  = metrics.ma50  || 'N/A';
  document.getElementById('d-ma200-val').textContent = metrics.ma200 || 'N/A';
}

// ── CHART: PE GAUGE ───────────────────────────────────────
function renderPEGauge(peRaw) {
  const pe = parseFloat(String(peRaw || '25').replace(/[^0-9.-]/g, '')) || 25;
  const ctx = document.getElementById('chart-pe').getContext('2d');

  // Clamp PE to 0-80 for display
  const clamped = Math.min(80, Math.max(0, pe));
  const remaining = 80 - clamped;

  const color = pe < 15 ? '#10B981' : pe < 35 ? '#F59E0B' : '#EF4444';

  state.charts.pe = new Chart(ctx, {
    type: 'doughnut',
    data: {
      datasets: [{
        data: [clamped, remaining],
        backgroundColor: [color, '#1C2540'],
        borderWidth: 0,
        circumference: 180,
        rotation: 270,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      cutout: '72%',
      plugins: { legend: { display: false }, tooltip: { enabled: false } },
    },
  });

  document.getElementById('d-pe-value').textContent = pe.toFixed(1);
  document.getElementById('d-pe-label').textContent = pe < 15 ? 'Undervalued' : pe < 35 ? 'Fair Value' : 'Expensive';
  document.getElementById('d-pe-label').style.color = color;
}

// ── CHART: SENTIMENT SPEEDOMETER ─────────────────────────
function renderSentimentGauge(score) {
  const ctx = document.getElementById('chart-sentiment').getContext('2d');

  // score: -1 to +1, map to 0–100 for the gauge
  const normalized = Math.min(100, Math.max(0, (score + 1) * 50));
  const color = score >= 0.15 ? '#10B981' : score <= -0.15 ? '#EF4444' : '#F59E0B';

  state.charts.sentiment = new Chart(ctx, {
    type: 'doughnut',
    data: {
      datasets: [{
        data: [normalized, 100 - normalized],
        backgroundColor: [color, '#1C2540'],
        borderWidth: 0,
        circumference: 180,
        rotation: 270,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      cutout: '65%',
      plugins: { legend: { display: false }, tooltip: { enabled: false } },
    },
  });

  const scoreEl = document.getElementById('d-sentiment-score');
  scoreEl.textContent = (score >= 0 ? '+' : '') + score.toFixed(3);
  scoreEl.style.color = color;

  const labels = ['VAGUELY BEARISH', 'BEARISH', 'NEUTRAL', 'BULLISH', 'STRONGLY BULLISH'];
  const labelIdx = score < -0.6 ? 1 : score < -0.15 ? 1 : score < 0.15 ? 2 : score < 0.6 ? 3 : 4;
  document.getElementById('d-sentiment-label').textContent = labels[labelIdx];
  document.getElementById('d-sentiment-label').style.color = color;
}

// ── EVENT BARS ────────────────────────────────────────────
function renderEventBars(events) {
  const container = document.getElementById('d-event-bars');
  const allEvents = [
    { key: 'Earnings Beat',      type: 'positive' },
    { key: 'Earnings Miss',      type: 'negative' },
    { key: 'Analyst Upgrade',    type: 'positive' },
    { key: 'Analyst Downgrade',  type: 'negative' },
    { key: 'Guidance Raise',     type: 'positive' },
    { key: 'Guidance Cut',       type: 'negative' },
    { key: 'Acquisition',        type: 'positive' },
    { key: 'Lawsuit',            type: 'negative' },
    { key: 'Product Launch',     type: 'positive' },
    { key: 'Layoffs',            type: 'negative' },
    { key: 'Insider Selling',    type: 'negative' },
  ];

  const detected = new Set(events.map(e => e.toLowerCase()));

  container.innerHTML = allEvents.map(ev => {
    const hit = [...detected].some(d => d.includes(ev.key.toLowerCase().split(' ')[0]));
    const fill = hit ? 100 : Math.floor(Math.random() * 15);
    return `
      <div class="event-bar-row">
        <span class="event-bar-label">${ev.key}</span>
        <div class="event-bar-track">
          <div class="event-bar-fill ${hit ? ev.type : ''}" style="width:${fill}%"></div>
        </div>
        <span style="font-family:var(--mono);font-size:10px;color:var(--muted);width:20px;text-align:right">${hit ? '●' : '○'}</span>
      </div>`;
  }).join('');
}

// ── CHART: RADAR ──────────────────────────────────────────
function renderRadarChart(metrics) {
  const ctx = document.getElementById('chart-radar').getContext('2d');

  const beta      = parseFloat(String(metrics.beta || '1').replace(/[^0-9.-]/g,'')) || 1;
  const pe        = parseFloat(String(metrics.pe_ratio || '25').replace(/[^0-9.-]/g,'')) || 25;
  const debtRatio = parseFloat(String(metrics.debt_ratio || '0.5').replace(/[^0-9.-]/g,'')) || 0.5;
  const margin    = parseFloat(String(metrics.profit_margin || '10').replace(/[^0-9.%-]/g,'')) || 10;

  // Normalise to 0-10 scores (higher = better/safer)
  const scores = [
    Math.max(0, 10 - debtRatio * 10),        // Debt-to-Equity (lower debt = better)
    Math.min(10, margin / 3),                 // Margin Stability
    7,                                        // Revenue Concentration (static for now)
    Math.max(0, 10 - (beta - 0.5) * 4),     // Beta Volatility (lower beta = better)
    Math.max(0, 10 - (pe - 15) / 5),        // Valuation Stretch (lower PE = better)
  ];

  state.charts.radar = new Chart(ctx, {
    type: 'radar',
    data: {
      labels: ['Debt Balance', 'Margin Stability', 'Revenue Conc.', 'Beta Volatility', 'Valuation'],
      datasets: [{
        data: scores,
        backgroundColor: 'rgba(124,58,237,0.2)',
        borderColor: '#7C3AED',
        borderWidth: 2,
        pointBackgroundColor: '#7C3AED',
        pointRadius: 3,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        r: {
          min: 0, max: 10,
          grid: { color: 'rgba(30,45,74,0.8)' },
          angleLines: { color: 'rgba(30,45,74,0.8)' },
          ticks: { display: false },
          pointLabels: { color: '#64748B', font: { size: 10 } },
        },
      },
    },
  });
}

// ── RISK DIMENSIONS ───────────────────────────────────────
function renderRiskDimensions(metrics) {
  const dims = [
    { label: 'Debt-to-Equity', value: metrics.debt_ratio, threshold: 0.7 },
    { label: 'Margin Stability', value: metrics.profit_margin, invert: false },
    { label: 'Revenue Concentration', value: null },
    { label: 'Price Volatility (Beta)', value: metrics.beta, threshold: 1.5 },
    { label: 'Valuation Stretch', value: metrics.pe_ratio, threshold: 35 },
  ];

  document.getElementById('d-risk-dims').innerHTML = dims.map(d => {
    const val = d.value ? String(d.value) : 'N/A';
    const isWarning = d.threshold && parseFloat(val.replace(/[^0-9.-]/g,'')) > d.threshold;
    const color = isWarning ? 'var(--warn)' : val === 'N/A' ? 'var(--muted)' : 'var(--bull)';
    const icon = isWarning ? '⚠' : val === 'N/A' ? '○' : '✓';
    return `
      <div class="risk-dimension">
        <span style="color:var(--muted);font-size:12px">${d.label}</span>
        <span style="display:flex;align-items:center;gap:6px;font-family:var(--mono);font-size:11px">
          <span style="color:${color}">${icon}</span>
          <span style="color:${color}">${val}</span>
        </span>
      </div>`;
  }).join('');
}

// ── REVENUE CHART ─────────────────────────────────────────
function renderRevenueChart(metrics) {
  const ctx = document.getElementById('chart-revenue').getContext('2d');
  const revenue = parseFloat(String(metrics.revenue || '10B').replace(/[$B]/g,'')) || 10;

  // Simulate YoY — in a real expansion, we'd store multi-year data from the SEC tool
  const years = ['2020', '2021', '2022', '2023', '2024'];
  const vals  = years.map((_, i) => +(revenue * (0.7 + i * 0.08)).toFixed(1));

  state.charts.revenue = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: years,
      datasets: [{
        label: 'Revenue ($B)',
        data: vals,
        backgroundColor: vals.map((v, i, a) => i === a.length - 1 ? '#7C3AED' : 'rgba(124,58,237,0.35)'),
        borderRadius: 4,
        borderSkipped: false,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        x: { ticks: { color: '#64748B', font: { size: 9 } }, grid: { display: false } },
        y: { ticks: { color: '#64748B', font: { size: 9 }, callback: v => `$${v}B` },
             grid: { color: 'rgba(30,45,74,0.8)' } },
      },
    },
  });
}

// ── RISKS & OPPORTUNITIES ─────────────────────────────────
function renderRisksOpps(risks, opps) {
  document.getElementById('d-risks').innerHTML = risks.map(r =>
    `<div class="risk-item"><span class="icon">▼</span><span>${r}</span></div>`
  ).join('') || '<div class="muted" style="font-size:12px">No risks identified</div>';

  document.getElementById('d-opps').innerHTML = opps.map(o =>
    `<div class="opp-item"><span class="icon">▲</span><span>${o}</span></div>`
  ).join('') || '<div class="muted" style="font-size:12px">No opportunities identified</div>';
}

// ── HISTORY SIDEBAR ───────────────────────────────────────
async function loadHistory() {
  try {
    // API: GET /analysis/history
    const reports = await authFetch('/analysis/history');
    const container = document.getElementById('history-list');
    if (!reports.length) {
      container.innerHTML = '<div class="muted" style="font-size:11px;padding:8px">No analyses yet</div>';
      return;
    }
    container.innerHTML = reports.map(r => {
      const rec = r.ai_report?.recommendation || '—';
      const cls = rec === 'BUY' ? 'bull' : rec === 'SELL' ? 'bear' : 'warn';
      return `
        <div class="report-item" onclick="loadReport(${r.id})">
          <div class="report-item-ticker">
            <span class="mono">${r.ticker}</span>
            <span class="${cls}" style="font-size:10px">${rec}</span>
          </div>
          <div class="report-item-date">${new Date(r.created_at).toLocaleDateString()}</div>
        </div>`;
    }).join('');
  } catch (_) {}
}

// ── PORTFOLIO ─────────────────────────────────────────────
document.getElementById('portfolio-form').addEventListener('submit', async (e) => {
  e.preventDefault();
  const ticker    = document.getElementById('p-ticker').value.trim().toUpperCase();
  const quantity  = parseFloat(document.getElementById('p-qty').value);
  const buy_price = parseFloat(document.getElementById('p-price').value);

  try {
    // API: POST /portfolio/
    await authFetch('/portfolio/', {
      method: 'POST',
      body: JSON.stringify({ ticker, quantity, buy_price }),
    });
    e.target.reset();
    loadPortfolio();
  } catch (err) {
    showToast('Portfolio Error', err.message);
  }
});

async function loadPortfolio() {
  try {
    // API: GET /portfolio/
    const data = await authFetch('/portfolio/');
    const tbody = document.getElementById('portfolio-tbody');

    if (!data.holdings.length) {
      tbody.innerHTML = '<tr><td colspan="7" class="muted" style="padding:20px;text-align:center">No holdings yet</td></tr>';
    } else {
      tbody.innerHTML = data.holdings.map(h => {
        const pnlClass = (h.pnl || 0) >= 0 ? 'bull' : 'bear';
        return `
          <tr>
            <td><span class="mono" style="color:var(--violet)">${h.ticker}</span></td>
            <td class="mono">${h.quantity}</td>
            <td class="mono">$${h.buy_price.toFixed(2)}</td>
            <td class="mono">${h.current_price ? '$'+h.current_price.toFixed(2) : '—'}</td>
            <td class="mono ${pnlClass}">${h.pnl != null ? (h.pnl >= 0 ? '+' : '')+'$'+h.pnl.toFixed(2) : '—'}</td>
            <td class="mono ${pnlClass}">${h.pnl_percent != null ? (h.pnl_percent >= 0 ? '+' : '')+h.pnl_percent.toFixed(2)+'%' : '—'}</td>
            <td><button class="td-action" onclick="deleteHolding(${h.id})">Remove</button></td>
          </tr>`;
      }).join('');
    }

    const s = data.summary;
    document.getElementById('p-total-invested').textContent = `$${s.total_invested.toFixed(2)}`;
    document.getElementById('p-current-value').textContent  = `$${s.current_value.toFixed(2)}`;
    const pnlEl = document.getElementById('p-total-pnl');
    pnlEl.textContent = `${s.total_pnl >= 0 ? '+' : ''}$${s.total_pnl.toFixed(2)} (${s.total_pnl_percent.toFixed(2)}%)`;
    pnlEl.className = `mono ${s.total_pnl >= 0 ? 'bull' : 'bear'}`;
  } catch (_) {}
}

async function deleteHolding(id) {
  try {
    // API: DELETE /portfolio/{id}
    const res = await fetch(`${API}/portfolio/${id}`, {
      method: 'DELETE',
      headers: { 'Authorization': `Bearer ${state.token}` },
    });
    if (res.ok) loadPortfolio();
  } catch (_) {}
}

// ── NAV TABS ──────────────────────────────────────────────
document.querySelectorAll('.sidebar-btn[data-view]').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.sidebar-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    const view = btn.dataset.view;
    document.getElementById('workspace-view').classList.toggle('hidden', view !== 'analyze');
    document.getElementById('dashboard-view').classList.toggle('hidden', view !== 'analyze' || !state.currentReport);
    document.getElementById('progress-card').classList.add('hidden');
    document.getElementById('portfolio-panel').classList.toggle('hidden', view !== 'portfolio');
    document.getElementById('history-panel').classList.toggle('hidden', view !== 'history');
    if (view === 'analyze' && !state.currentReport) {
      document.getElementById('workspace-view').classList.remove('hidden');
    }
    if (view === 'portfolio') loadPortfolio();
    if (view === 'history') loadHistory();
  });
});

// ── COPY BUTTON ───────────────────────────────────────────
document.getElementById('copy-btn').addEventListener('click', () => {
  if (!state.currentReport) return;
  const text = JSON.stringify(state.currentReport, null, 2);
  navigator.clipboard.writeText(text).then(() => {
    const btn = document.getElementById('copy-btn');
    btn.textContent = '✓ Copied';
    setTimeout(() => btn.innerHTML = '⎘ Copy Report', 1200);
  });
});

// ── TOAST ─────────────────────────────────────────────────
function showToast(title, body) {
  document.getElementById('toast-title').textContent = title;
  document.getElementById('toast-body').textContent  = body;
  const toast = document.getElementById('toast');
  toast.classList.add('show');
  setTimeout(() => toast.classList.remove('show'), 6000);
}
document.getElementById('toast-close').addEventListener('click', () => {
  document.getElementById('toast').classList.remove('show');
});

// ── BOOT ──────────────────────────────────────────────────
function boot() {
  if (state.token && state.user) {
    document.getElementById('nav-username').textContent = state.user.username;
    showView('workspace');
    loadHistory();
  } else {
    showView('auth');
  }
  setupSearch();
}

boot();