// ==========================================================================
// SeriCare Super Admin Portal — Application Controller
// Real-Time Data Stream, Stage Climate Setpoint Configuration,
// IoT Actuators & Historical Analytics
// ==========================================================================

const API_BASE_URL = window.location.origin.includes('localhost') || window.location.origin.includes('127.0.0.1')
  ? `${window.location.origin}/api/v1`
  : 'http://localhost:8000/api/v1';

// Application State
let adminToken = localStorage.getItem('setu_admin_token') || null;
let currentTab = 'overview';
let selectedShedId = 'shed_01';
let stagesData = [];
let selectedStageId = 1;
let liveTelemetry = null;
let enrolledFarmers = [];
let auditLogs = [];
let autoRefreshTimer = null;
let tempChart = null;
let humidityChart = null;

// Initialize on Document Ready
document.addEventListener('DOMContentLoaded', () => {
  if (window.lucide) lucide.createIcons();

  if (adminToken) {
    checkAdminSession();
  } else {
    showAuthView();
  }
});

// ==========================================================================
// VIEW NAVIGATION & TAB CONTROLS
// ==========================================================================
function showAuthView() {
  document.getElementById('authView').classList.remove('hidden');
  document.getElementById('dashboardView').classList.add('hidden');
  if (autoRefreshTimer) clearInterval(autoRefreshTimer);
  if (window.lucide) lucide.createIcons();
}

function showDashboardView() {
  document.getElementById('authView').classList.add('hidden');
  document.getElementById('dashboardView').classList.remove('hidden');
  
  // Start 3-second live telemetry refresh stream
  if (autoRefreshTimer) clearInterval(autoRefreshTimer);
  autoRefreshTimer = setInterval(() => {
    syncLiveTelemetryStream();
  }, 3500);

  syncAllRealtimeData();
}

function switchNavTab(tabName) {
  currentTab = tabName;
  
  // Update sidebar links
  document.querySelectorAll('.app-sidebar .nav-item').forEach(item => {
    item.classList.remove('active');
  });
  
  const navMap = {
    overview: 0,
    stages: 1,
    telemetry: 2,
    analytics: 3,
    farmers: 4,
    emergency: 5,
    audit: 6
  };
  
  const navItems = document.querySelectorAll('.app-sidebar .nav-item');
  if (navItems[navMap[tabName]]) {
    navItems[navMap[tabName]].classList.add('active');
  }

  // Hide all sections
  document.querySelectorAll('.view-section').forEach(sec => sec.classList.add('hidden'));

  // Show selected section
  const targetSec = document.getElementById(`section-${tabName}`);
  if (targetSec) targetSec.classList.remove('hidden');

  // Update Top Bar titles
  const titles = {
    overview: { title: 'Cluster Operations Hub', breadcrumb: 'Live Real-Time Telemetry' },
    stages: { title: 'Rearing Stage Climate Levels', breadcrumb: 'Super Admin Auto-Mode Controls' },
    telemetry: { title: 'Shed IoT Sensors & Relays', breadcrumb: 'Active Hardware State' },
    analytics: { title: 'Microclimate Analytics (24h)', breadcrumb: 'Telemetry Curves vs Safe Zones' },
    farmers: { title: 'Enrolled Farmers Directory', breadcrumb: 'Global Sericulture Network' },
    emergency: { title: 'Emergency Actuator Overrides', breadcrumb: 'Manual Safety Interlocks' },
    audit: { title: 'Security & Action Audit Logs', breadcrumb: 'Traceable Administrative Log' }
  };

  const info = titles[tabName] || titles.overview;
  document.getElementById('topBarTitle').textContent = info.title;
  document.getElementById('topBarBreadcrumb').textContent = info.breadcrumb;

  // Initialize or resize charts if analytics tab opened
  if (tabName === 'analytics') {
    setTimeout(() => {
      initOrUpdateCharts();
    }, 100);
  }

  if (window.lucide) lucide.createIcons();
}

// ==========================================================================
// AUTHENTICATION & SESSION
// ==========================================================================
async function handleLogin(event) {
  event.preventDefault();
  const usernameInput = document.getElementById('username').value.trim();
  const passwordInput = document.getElementById('password').value;
  const errorEl = document.getElementById('loginError');
  const loginBtn = document.getElementById('loginBtn');

  errorEl.classList.add('hidden');
  loginBtn.disabled = true;
  loginBtn.innerHTML = '<span>Verifying Admin Authorization...</span>';

  try {
    const res = await fetch(`${API_BASE_URL}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username: usernameInput, password: passwordInput })
    });

    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.detail || 'Authorization failed. Please check credentials.');
    }

    const role = (data.user && data.user.role) || data.role;
    if (role !== 'admin' && role !== 'superadmin') {
      throw new Error('Access denied: Account lacks Super Admin command privileges.');
    }

    adminToken = data.access_token;
    localStorage.setItem('setu_admin_token', adminToken);
    localStorage.setItem('setu_admin_user', JSON.stringify(data.user || data));

    const displayName = (data.user && (data.user.full_name || data.user.username)) || 'Super Admin';
    document.getElementById('sidebarAdminName').textContent = displayName;

    showToast(`Welcome, ${displayName}! Authorized for Super Admin command.`, 'success');
    showDashboardView();

  } catch (err) {
    errorEl.textContent = err.message;
    errorEl.classList.remove('hidden');
  } finally {
    loginBtn.disabled = false;
    loginBtn.innerHTML = '<span>Authorize Access</span> <i data-lucide="arrow-right"></i>';
    if (window.lucide) lucide.createIcons();
  }
}

function togglePasswordVisibility() {
  const pwdInput = document.getElementById('password');
  const eyeBtn = document.getElementById('togglePasswordBtn');
  if (!pwdInput) return;

  const isPassword = pwdInput.type === 'password';
  pwdInput.type = isPassword ? 'text' : 'password';

  if (eyeBtn) {
    eyeBtn.innerHTML = isPassword 
      ? '<i data-lucide="eye-off" id="passwordEyeIcon"></i>' 
      : '<i data-lucide="eye" id="passwordEyeIcon"></i>';
    if (window.lucide) lucide.createIcons();
  }
}

async function checkAdminSession() {
  try {
    const res = await fetch(`${API_BASE_URL}/auth/me`, {
      headers: { 'Authorization': `Bearer ${adminToken}` }
    });
    if (!res.ok) throw new Error('Session expired');
    const user = await res.json();
    if (user.role !== 'admin' && user.role !== 'superadmin') {
      throw new Error('Unauthorized role');
    }
    document.getElementById('sidebarAdminName').textContent = user.full_name || user.username || 'Super Admin';
    showDashboardView();
  } catch (err) {
    handleLogout();
  }
}

function handleLogout() {
  adminToken = null;
  localStorage.removeItem('setu_admin_token');
  localStorage.removeItem('setu_admin_user');
  showAuthView();
}

// ==========================================================================
// REAL-TIME DATA STREAM & SYNC
// ==========================================================================
async function syncAllRealtimeData() {
  const syncBtn = document.getElementById('syncBtn');
  const syncIcon = document.getElementById('syncIcon');
  if (syncIcon) syncIcon.classList.add('spinning');
  
  try {
    await Promise.all([
      fetchStats(),
      fetchLiveTelemetry(),
      fetchStages(),
      fetchFarmers(),
      fetchAuditLogs()
    ]);
  } catch (err) {
    console.error('Data synchronization error:', err);
  } finally {
    if (syncIcon) syncIcon.classList.remove('spinning');
    if (window.lucide) lucide.createIcons();
  }
}

// Lighter interval sync for real-time telemetry stream
async function syncLiveTelemetryStream() {
  try {
    await fetchLiveTelemetry();
  } catch (err) {
    console.error('Live telemetry stream error:', err);
  }
}

// 1. Fetch Executive Stats
async function fetchStats() {
  try {
    const res = await fetch(`${API_BASE_URL}/admin/stats`, {
      headers: { 'Authorization': `Bearer ${adminToken}` }
    });
    if (!res.ok) return;
    const stats = await res.json();

    document.getElementById('kpiFarmers').textContent = stats.total_farmers ?? '--';
    document.getElementById('kpiActiveFarmers').textContent = stats.active_farmers ?? '--';
    document.getElementById('kpiDfl').textContent = stats.total_dfl_capacity ?? '--';
    document.getElementById('kpiSheds').textContent = stats.active_sheds_monitored ?? '1';
    document.getElementById('kpiActuators').textContent = stats.active_relays_count ?? '0';
    document.getElementById('navFarmerCount').textContent = stats.total_farmers ?? '--';

  } catch (err) {
    console.error('Error fetching admin stats:', err);
  }
}

// 2. Fetch Live Telemetry & Historical Readings
async function fetchLiveTelemetry() {
  try {
    const res = await fetch(`${API_BASE_URL}/admin/telemetry-live?shed_id=${selectedShedId}`, {
      headers: { 'Authorization': `Bearer ${adminToken}` }
    });
    if (!res.ok) return;
    const data = await res.json();
    liveTelemetry = data;

    const ov = data.overview;
    const targets = data.stage_targets;

    // KPI Badges & Outside Weather
    document.getElementById('kpiOutsideTemp').textContent = `${ov.outside_temp.toFixed(1)}°C`;
    document.getElementById('kpiOutsideHum').textContent = `Outside Humidity: ${ov.outside_humidity.toFixed(0)}%`;
    document.getElementById('kpiCompliance').textContent = `${data.compliance_index}%`;
    document.getElementById('weatherChipText').textContent = `${ov.region || 'Outside'}: ${ov.outside_temp.toFixed(1)}°C • ${ov.outside_humidity.toFixed(0)}% RH`;

    // Overview Microclimate Gauges
    document.getElementById('overviewShedLabel').textContent = `${ov.shed_id.toUpperCase()} • ${ov.farm_name}`;
    document.getElementById('dialIndoorTemp').textContent = `${ov.indoor_temp.toFixed(1)}°C`;
    document.getElementById('dialIndoorHum').textContent = `${ov.indoor_humidity.toFixed(0)}%`;
    document.getElementById('dialOutdoorTemp').textContent = `${ov.outside_temp.toFixed(1)}°C`;
    document.getElementById('dialOutdoorHum').textContent = `Humidity: ${ov.outside_humidity.toFixed(0)}%`;

    document.getElementById('dialTempTarget').textContent = `Target: ${targets.temp_min}°C – ${targets.temp_max}°C`;
    document.getElementById('dialHumTarget').textContent = `Target: ${targets.hum_min}% – ${targets.hum_max}%`;

    document.getElementById('overviewHeadline').textContent = ov.status_headline || 'Ideal for Silkworms';
    document.getElementById('overviewSubline').textContent = ov.status_subline || 'Microclimate is within biological tolerances.';

    // Health badge
    const healthBadge = document.getElementById('overviewHealthBadge');
    if (ov.overall_status === 'IDEAL') {
      healthBadge.className = 'badge badge-green';
      healthBadge.textContent = 'OPTIMAL ENVELOPE';
    } else if (ov.overall_status === 'TOO_WARM' || ov.overall_status === 'TOO_COOL') {
      healthBadge.className = 'badge badge-amber';
      healthBadge.textContent = ov.overall_status.replace('_', ' ');
    } else {
      healthBadge.className = 'badge badge-rose';
      healthBadge.textContent = 'CRITICAL ATTENTION';
    }

    // Active Stage Card
    document.getElementById('overviewStageBadge').textContent = `Instar ${ov.current_stage}`;
    document.getElementById('overviewStageName').textContent = ov.stage_name;
    document.getElementById('overviewStageDesc').textContent = targets.description || 'Silkworm rearing in progress.';

    // Auto-mode badge
    const autoBadge = document.getElementById('overviewAutoModeBadge');
    if (ov.is_auto_mode) {
      autoBadge.className = 'badge badge-green';
      autoBadge.textContent = 'AUTO-MODE ACTIVE';
    } else {
      autoBadge.className = 'badge badge-amber';
      autoBadge.textContent = 'MANUAL OVERRIDE ACTIVE';
    }
    const autoCheck = document.getElementById('autoModeToggle');
    if (autoCheck) autoCheck.checked = ov.is_auto_mode;

    // Mini Relays
    updateRelayUI('miniRelayCooler', 'miniStateCooler', ov.actuators.cooler);
    updateRelayUI('miniRelayFan', 'miniStateFan', ov.actuators.fan);
    updateRelayUI('miniRelayHeater', 'miniStateHeater', ov.actuators.heater);

    // Full Telemetry Tab Gauges
    document.getElementById('fullDialIndoorTemp').textContent = `${ov.indoor_temp.toFixed(1)}°C`;
    document.getElementById('fullDialIndoorHum').textContent = `${ov.indoor_humidity.toFixed(0)}%`;
    document.getElementById('fullDialOutdoorTemp').textContent = `${ov.outside_temp.toFixed(1)}°C`;
    document.getElementById('fullDialTempTarget').textContent = `Safe Band: ${targets.temp_min}°C – ${targets.temp_max}°C`;
    document.getElementById('fullDialHumTarget').textContent = `Safe Band: ${targets.hum_min}% – ${targets.hum_max}%`;
    document.getElementById('fullDialOutdoorHum').textContent = `Outside RH: ${ov.outside_humidity.toFixed(0)}%`;

    // Full Actuator Cards
    updateRelayUI('cardCooler', 'tagCooler', ov.actuators.cooler);
    updateRelayUI('cardFan', 'tagFan', ov.actuators.fan);
    updateRelayUI('cardHeater', 'tagHeater', ov.actuators.heater);

    // If on analytics tab, update charts
    if (currentTab === 'analytics') {
      initOrUpdateCharts();
    }

  } catch (err) {
    console.error('Error fetching live telemetry:', err);
  }
}

function updateRelayUI(cardId, tagId, isActive) {
  const card = document.getElementById(cardId);
  const tag = document.getElementById(tagId);
  if (!card || !tag) return;

  if (isActive) {
    card.classList.add('active');
    tag.textContent = 'ENGAGED / ON';
  } else {
    card.classList.remove('active');
    tag.textContent = 'OFF';
  }
}

function handleShedChange(shedId) {
  selectedShedId = shedId;
  syncAllRealtimeData();
}

// ==========================================================================
// SUPER ADMIN STAGE CLIMATE LEVELS & AUTO-MODE SETPOINTS
// ==========================================================================
async function fetchStages() {
  try {
    const res = await fetch(`${API_BASE_URL}/admin/stages`, {
      headers: { 'Authorization': `Bearer ${adminToken}` }
    });
    if (!res.ok) return;
    stagesData = await res.json();

    renderStageTabs();
    selectStageForEdit(selectedStageId);
    renderStageMatrixTable();

  } catch (err) {
    console.error('Error fetching stage thresholds:', err);
  }
}

function renderStageTabs() {
  const container = document.getElementById('stageTabsContainer');
  if (!container || !stagesData || stagesData.length === 0) return;

  container.innerHTML = stagesData.map(s => `
    <button type="button" class="stage-tab-btn ${s.stage_id === selectedStageId ? 'active' : ''}" onclick="selectStageForEdit(${s.stage_id})">
      <span>Level ${s.stage_id}: ${escapeHtml(s.name)}</span>
      <span class="tab-days">(${escapeHtml(s.days)})</span>
    </button>
  `).join('');
}

function selectStageForEdit(stageId) {
  selectedStageId = stageId;
  renderStageTabs();

  const stage = stagesData.find(s => s.stage_id === stageId) || stagesData[0];
  if (!stage) return;

  document.getElementById('editStageHeaderTitle').textContent = `Level ${stage.stage_id}: ${stage.name} — ${stage.days}`;
  document.getElementById('editStageHeaderDesc').textContent = stage.description || 'Silkworm microclimate threshold setpoints.';

  document.getElementById('inputTempMin').value = stage.temp_min;
  document.getElementById('inputTempMax').value = stage.temp_max;
  document.getElementById('inputHumMin').value = stage.hum_min;
  document.getElementById('inputHumMax').value = stage.hum_max;

  document.getElementById('inputHysteresisTemp').value = stage.hysteresis_temp ?? 0.5;
  document.getElementById('inputHysteresisHum').value = stage.hysteresis_hum ?? 3.0;
  document.getElementById('inputFanOffset').value = stage.fan_trigger_offset ?? 1.5;
  document.getElementById('inputStageDesc').value = stage.description || '';

  updateVisualRangeBars();
}

function handleStageInputChange() {
  updateVisualRangeBars();
}

function updateVisualRangeBars() {
  const tMin = parseFloat(document.getElementById('inputTempMin').value) || 20.0;
  const tMax = parseFloat(document.getElementById('inputTempMax').value) || 28.0;
  const hMin = parseFloat(document.getElementById('inputHumMin').value) || 60.0;
  const hMax = parseFloat(document.getElementById('inputHumMax').value) || 85.0;

  // Temperature range (15 to 38 C scale)
  const tScaleMin = 15.0;
  const tScaleMax = 38.0;
  const tRange = tScaleMax - tScaleMin;
  const tLeftPct = Math.max(0, Math.min(100, ((tMin - tScaleMin) / tRange) * 100));
  const tWidthPct = Math.max(4, Math.min(100 - tLeftPct, ((tMax - tMin) / tRange) * 100));

  const tFill = document.getElementById('tempRangeFill');
  if (tFill) {
    tFill.style.left = `${tLeftPct}%`;
    tFill.style.width = `${tWidthPct}%`;
  }
  document.getElementById('tempRangeBadge').textContent = `${tMin.toFixed(1)}°C – ${tMax.toFixed(1)}°C`;
  document.getElementById('tempRangeLabel').textContent = `Optimal: ${tMin.toFixed(1)}°C – ${tMax.toFixed(1)}°C`;

  // Humidity range (30 to 95 % scale)
  const hScaleMin = 30.0;
  const hScaleMax = 95.0;
  const hRange = hScaleMax - hScaleMin;
  const hLeftPct = Math.max(0, Math.min(100, ((hMin - hScaleMin) / hRange) * 100));
  const hWidthPct = Math.max(4, Math.min(100 - hLeftPct, ((hMax - hMin) / hRange) * 100));

  const hFill = document.getElementById('humRangeFill');
  if (hFill) {
    hFill.style.left = `${hLeftPct}%`;
    hFill.style.width = `${hWidthPct}%`;
  }
  document.getElementById('humRangeBadge').textContent = `${Math.round(hMin)}% – ${Math.round(hMax)}%`;
  document.getElementById('humRangeLabel').textContent = `Optimal: ${Math.round(hMin)}% – ${Math.round(hMax)}%`;
}

async function saveStageSetpoints() {
  const tMin = parseFloat(document.getElementById('inputTempMin').value);
  const tMax = parseFloat(document.getElementById('inputTempMax').value);
  const hMin = parseFloat(document.getElementById('inputHumMin').value);
  const hMax = parseFloat(document.getElementById('inputHumMax').value);
  const hystTemp = parseFloat(document.getElementById('inputHysteresisTemp').value) || 0.5;
  const hystHum = parseFloat(document.getElementById('inputHysteresisHum').value) || 3.0;
  const fanOffset = parseFloat(document.getElementById('inputFanOffset').value) || 1.5;
  const desc = document.getElementById('inputStageDesc').value.trim();

  if (tMin > tMax) {
    alert('Validation Error: Target Min Temperature cannot exceed Target Max Temperature.');
    return;
  }
  if (hMin > hMax) {
    alert('Validation Error: Target Min Humidity cannot exceed Target Max Humidity.');
    return;
  }

  const payload = {
    temp_min: tMin,
    temp_max: tMax,
    hum_min: hMin,
    hum_max: hMax,
    hysteresis_temp: hystTemp,
    hysteresis_hum: hystHum,
    fan_trigger_offset: fanOffset,
    description: desc
  };

  try {
    const res = await fetch(`${API_BASE_URL}/admin/stages/${selectedStageId}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${adminToken}`
      },
      body: JSON.stringify(payload)
    });

    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Failed to update stage thresholds');

    showToast(`Level ${selectedStageId} setpoints successfully updated and synchronized with auto-mode!`, 'success');
    await fetchStages();
    await fetchLiveTelemetry();
    await fetchAuditLogs();

  } catch (err) {
    alert('Failed to save setpoints: ' + err.message);
  }
}

async function applyCurrentStageToShed() {
  try {
    const res = await fetch(`${API_BASE_URL}/admin/sheds/${selectedShedId}/stage`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${adminToken}`
      },
      body: JSON.stringify({ stage: selectedStageId })
    });

    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Failed to apply stage to shed');

    showToast(`Active rearing stage for ${selectedShedId.toUpperCase()} updated to Level ${selectedStageId} (${data.stage_name})!`, 'success');
    await fetchLiveTelemetry();
    await fetchAuditLogs();

  } catch (err) {
    alert('Error applying stage: ' + err.message);
  }
}

async function resetStagesToStandards() {
  if (!confirm('Are you sure you want to restore all 5 rearing stage climate setpoints to Central Silk Board (CSB) scientific standards?')) {
    return;
  }

  try {
    const res = await fetch(`${API_BASE_URL}/admin/stages/reset`, {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${adminToken}` }
    });

    if (!res.ok) throw new Error('Reset failed');
    showToast('All stage setpoints restored to Central Silk Board standards.', 'success');
    await fetchStages();
    await fetchLiveTelemetry();
    await fetchAuditLogs();

  } catch (err) {
    alert('Failed to reset stages: ' + err.message);
  }
}

function renderStageMatrixTable() {
  const tbody = document.getElementById('stageMatrixTableBody');
  if (!tbody || !stagesData) return;

  const activeStageNum = (liveTelemetry && liveTelemetry.overview) ? liveTelemetry.overview.current_stage : 3;

  tbody.innerHTML = stagesData.map(s => {
    const isCurrentShedStage = s.stage_id === activeStageNum;
    return `
      <tr class="${isCurrentShedStage ? 'active-stage-row' : ''}">
        <td><strong>Level ${s.stage_id}</strong></td>
        <td>
          <strong>${escapeHtml(s.name)}</strong>
          ${isCurrentShedStage ? '<span class="badge badge-green" style="margin-left:6px;font-size:0.65rem;">ACTIVE ON SHED</span>' : ''}
        </td>
        <td><code>${escapeHtml(s.days)}</code></td>
        <td><strong style="color:var(--green-leaf);">${s.temp_min}°C – ${s.temp_max}°C</strong></td>
        <td><strong style="color:var(--blue);">${s.hum_min}% – ${s.hum_max}%</strong></td>
        <td>±${s.hysteresis_temp ?? 0.5}°C / ±${s.hysteresis_hum ?? 3.0}%</td>
        <td>
          <button class="btn btn-skin btn-sm" onclick="selectStageForEdit(${s.stage_id}); window.scrollTo({top: 300, behavior: 'smooth'});">
            <i data-lucide="edit-3"></i> Edit Setpoints
          </button>
        </td>
      </tr>
    `;
  }).join('');

  if (window.lucide) lucide.createIcons();
}

// ==========================================================================
// ACTUATOR OVERRIDES & EMERGENCY ACTIONS
// ==========================================================================
async function manualToggleActuator(actuatorName) {
  if (!liveTelemetry || !liveTelemetry.overview) return;
  const currentVal = liveTelemetry.overview.actuators[actuatorName];
  const nextVal = !currentVal;

  try {
    const res = await fetch(`${API_BASE_URL}/admin/sheds/${selectedShedId}/actuator`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${adminToken}`
      },
      body: JSON.stringify({
        actuator: actuatorName,
        state: nextVal
      })
    });

    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Manual actuator override failed');

    showToast(`${actuatorName.toUpperCase()} manually switched ${nextVal ? 'ON' : 'OFF'} on ${selectedShedId}!`, 'success');
    await fetchLiveTelemetry();
    await fetchStats();
    await fetchAuditLogs();

  } catch (err) {
    alert('Actuator command failed: ' + err.message);
  }
}

async function toggleAutoMode(isAuto) {
  try {
    const res = await fetch(`${API_BASE_URL}/admin/sheds/${selectedShedId}/auto-mode`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${adminToken}`
      },
      body: JSON.stringify({ is_auto_mode: isAuto })
    });

    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Failed to toggle auto mode');

    showToast(`Microclimate Auto-Mode ${isAuto ? 'ENABLED' : 'DISABLED'} on ${selectedShedId}!`, 'success');
    await fetchLiveTelemetry();
    await fetchAuditLogs();

  } catch (err) {
    alert('Auto-mode toggle failed: ' + err.message);
  }
}

async function triggerEmergency(action) {
  const confirmMsg = action === 'COOLDOWN_ALL'
    ? 'MASTER SAFETY SHUTDOWN: Are you certain you want to FORCE OFF all heating, cooling, and ventilation actuators?'
    : `Execute immediate emergency override: "${action}" on ${selectedShedId.toUpperCase()}?`;

  if (!confirm(confirmMsg)) return;

  try {
    const res = await fetch(`${API_BASE_URL}/admin/emergency-control`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${adminToken}`
      },
      body: JSON.stringify({
        shed_id: selectedShedId,
        action: action
      })
    });

    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Emergency command failed');

    showToast(`Emergency override executed: ${data.details}`, 'warning');
    await fetchLiveTelemetry();
    await fetchStats();
    await fetchAuditLogs();

  } catch (err) {
    alert('Emergency execution error: ' + err.message);
  }
}

// ==========================================================================
// INTERACTIVE CHARTS & ANALYTICS (Chart.js)
// ==========================================================================
function initOrUpdateCharts() {
  if (!liveTelemetry || !liveTelemetry.history || liveTelemetry.history.length === 0) return;

  const history = liveTelemetry.history;
  const targets = liveTelemetry.stage_targets;

  const labels = history.map(h => {
    const d = new Date(h.timestamp);
    return `${d.getHours()}:00`;
  });

  const indoorTemps = history.map(h => h.indoor_temp);
  const outdoorTemps = history.map(h => h.outside_temp);
  const indoorHums = history.map(h => h.indoor_hum);
  const outdoorHums = history.map(h => h.outside_hum);

  // Target safe zone lines
  const minTempLine = history.map(() => targets.temp_min);
  const maxTempLine = history.map(() => targets.temp_max);
  const minHumLine = history.map(() => targets.hum_min);
  const maxHumLine = history.map(() => targets.hum_max);

  // 1. Temperature Chart
  const tempCanvas = document.getElementById('temperatureChart');
  if (tempCanvas) {
    const ctx = tempCanvas.getContext('2d');
    if (tempChart) tempChart.destroy();

    tempChart = new Chart(ctx, {
      type: 'line',
      data: {
        labels: labels,
        datasets: [
          {
            label: 'Shed Indoor Temp (°C)',
            data: indoorTemps,
            borderColor: '#1C4D37',
            backgroundColor: 'rgba(28, 77, 55, 0.08)',
            fill: true,
            tension: 0.35,
            borderWidth: 2.5,
            pointRadius: 3,
            pointBackgroundColor: '#1C4D37'
          },
          {
            label: 'Outside Weather Temp (°C)',
            data: outdoorTemps,
            borderColor: '#C49768',
            borderDash: [4, 4],
            tension: 0.35,
            borderWidth: 1.8,
            pointRadius: 0
          },
          {
            label: `Target Min (${targets.temp_min}°C)`,
            data: minTempLine,
            borderColor: 'rgba(78, 149, 113, 0.6)',
            borderDash: [6, 4],
            borderWidth: 1.5,
            pointRadius: 0
          },
          {
            label: `Target Max (${targets.temp_max}°C)`,
            data: maxTempLine,
            borderColor: 'rgba(189, 52, 41, 0.6)',
            borderDash: [6, 4],
            borderWidth: 1.5,
            pointRadius: 0
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { position: 'top', labels: { boxWidth: 12, font: { family: "'Plus Jakarta Sans', sans-serif", size: 11 } } },
          tooltip: {
            backgroundColor: '#133323',
            titleFont: { family: "'JetBrains Mono', monospace" },
            bodyFont: { family: "'Plus Jakarta Sans', sans-serif" }
          }
        },
        scales: {
          y: {
            grid: { color: 'rgba(229, 218, 203, 0.5)' },
            ticks: { font: { family: "'JetBrains Mono', monospace", size: 11 }, callback: v => `${v}°C` }
          },
          x: {
            grid: { display: false },
            ticks: { font: { family: "'JetBrains Mono', monospace", size: 11 } }
          }
        }
      }
    });
  }

  // 2. Humidity Chart
  const humCanvas = document.getElementById('humidityChart');
  if (humCanvas) {
    const ctx = humCanvas.getContext('2d');
    if (humidityChart) humidityChart.destroy();

    humidityChart = new Chart(ctx, {
      type: 'line',
      data: {
        labels: labels,
        datasets: [
          {
            label: 'Shed Indoor Humidity (%)',
            data: indoorHums,
            borderColor: '#235B85',
            backgroundColor: 'rgba(35, 91, 133, 0.08)',
            fill: true,
            tension: 0.35,
            borderWidth: 2.5,
            pointRadius: 3,
            pointBackgroundColor: '#235B85'
          },
          {
            label: 'Outside Weather Humidity (%)',
            data: outdoorHums,
            borderColor: '#C49768',
            borderDash: [4, 4],
            tension: 0.35,
            borderWidth: 1.8,
            pointRadius: 0
          },
          {
            label: `Target Min (${targets.hum_min}%)`,
            data: minHumLine,
            borderColor: 'rgba(78, 149, 113, 0.6)',
            borderDash: [6, 4],
            borderWidth: 1.5,
            pointRadius: 0
          },
          {
            label: `Target Max (${targets.hum_max}%)`,
            data: maxHumLine,
            borderColor: 'rgba(189, 52, 41, 0.6)',
            borderDash: [6, 4],
            borderWidth: 1.5,
            pointRadius: 0
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { position: 'top', labels: { boxWidth: 12, font: { family: "'Plus Jakarta Sans', sans-serif", size: 11 } } },
          tooltip: {
            backgroundColor: '#133323',
            titleFont: { family: "'JetBrains Mono', monospace" }
          }
        },
        scales: {
          y: {
            grid: { color: 'rgba(229, 218, 203, 0.5)' },
            ticks: { font: { family: "'JetBrains Mono', monospace", size: 11 }, callback: v => `${v}%` }
          },
          x: {
            grid: { display: false },
            ticks: { font: { family: "'JetBrains Mono', monospace", size: 11 } }
          }
        }
      }
    });
  }
}

function exportCsvData() {
  window.open(`${API_BASE_URL}/telemetry/export/csv/${selectedShedId}?token=${adminToken}`, '_blank');
}

// ==========================================================================
// FARMERS & SHEDS MANAGEMENT
// ==========================================================================
async function fetchFarmers() {
  try {
    const res = await fetch(`${API_BASE_URL}/admin/farmers`, {
      headers: { 'Authorization': `Bearer ${adminToken}` }
    });
    if (!res.ok) return;
    enrolledFarmers = await res.json();
    renderFarmersTable(enrolledFarmers);
  } catch (err) {
    console.error('Error fetching farmers list:', err);
  }
}

function renderFarmersTable(farmers) {
  const tbody = document.getElementById('farmersTableBody');
  if (!tbody) return;

  if (!farmers || farmers.length === 0) {
    tbody.innerHTML = '<tr><td colspan="8" style="text-align:center; padding:32px;">No registered farmers found.</td></tr>';
    return;
  }

  tbody.innerHTML = farmers.map(f => {
    const isActive = f.is_active === 1 || f.is_active === true;
    return `
      <tr>
        <td>
          <div class="farmer-name-cell">${escapeHtml(f.full_name || f.username)}</div>
          <div class="farmer-sub-cell">@${escapeHtml(f.username)} • ${escapeHtml(f.phone || 'N/A')}</div>
        </td>
        <td><strong>${escapeHtml(f.farm_name || 'Main Shed')}</strong></td>
        <td>${escapeHtml(f.region || 'Local / Global')}</td>
        <td><code>${escapeHtml(f.batch_id || 'BATCH-2026')}</code></td>
        <td><strong>${escapeHtml(f.dfl_capacity || 'N/A')}</strong></td>
        <td><small>${escapeHtml(f.breed || 'Bivoltine')}</small></td>
        <td>
          <span class="badge-status ${isActive ? 'active' : 'inactive'}">
            <span class="pulse-dot" style="width:6px;height:6px;background:${isActive ? 'var(--green-leaf)':'#9E9284'}"></span>
            ${isActive ? 'Active Rearing' : 'Suspended'}
          </span>
        </td>
        <td>
          <div class="action-buttons-wrap">
            <button class="btn-icon" title="${isActive ? 'Suspend Farmer Account' : 'Activate Farmer Account'}" onclick="toggleFarmerStatus('${f.username}', ${!isActive})">
              <i data-lucide="${isActive ? 'user-x' : 'user-check'}"></i>
            </button>
            <button class="btn-icon danger" title="Remove Farmer Record" onclick="confirmDeleteFarmer('${f.username}')">
              <i data-lucide="trash-2"></i>
            </button>
          </div>
        </td>
      </tr>
    `;
  }).join('');

  if (window.lucide) lucide.createIcons();
}

function handleFarmerSearch() {
  const query = (document.getElementById('farmerSearchInput').value || '').toLowerCase();
  const filtered = enrolledFarmers.filter(f =>
    (f.username && f.username.toLowerCase().includes(query)) ||
    (f.full_name && f.full_name.toLowerCase().includes(query)) ||
    (f.farm_name && f.farm_name.toLowerCase().includes(query)) ||
    (f.batch_id && f.batch_id.toLowerCase().includes(query)) ||
    (f.region && f.region.toLowerCase().includes(query))
  );
  renderFarmersTable(filtered);
}

async function toggleFarmerStatus(farmerId, newStatus) {
  try {
    const res = await fetch(`${API_BASE_URL}/admin/farmers/${farmerId}/status`, {
      method: 'PATCH',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${adminToken}`
      },
      body: JSON.stringify({ is_active: newStatus })
    });
    if (!res.ok) throw new Error('Status modification failed');

    showToast(`Farmer account "${farmerId}" ${newStatus ? 'activated' : 'suspended'}.`, 'success');
    await fetchFarmers();
    await fetchStats();
    await fetchAuditLogs();
  } catch (err) {
    alert('Failed to update status: ' + err.message);
  }
}

async function confirmDeleteFarmer(farmerId) {
  if (!confirm(`Are you certain you want to remove farmer "${farmerId}"? This permanently unlinks their rearing batch history.`)) {
    return;
  }
  try {
    const res = await fetch(`${API_BASE_URL}/admin/farmers/${farmerId}`, {
      method: 'DELETE',
      headers: { 'Authorization': `Bearer ${adminToken}` }
    });
    if (!res.ok) throw new Error('Delete operation failed');

    showToast(`Farmer "${farmerId}" removed from system.`, 'success');
    await fetchFarmers();
    await fetchStats();
    await fetchAuditLogs();
  } catch (err) {
    alert('Failed to remove farmer: ' + err.message);
  }
}

function openEnrollFarmerModal() {
  document.getElementById('enrollModal').classList.remove('hidden');
  document.getElementById('enrollError').classList.add('hidden');
  document.getElementById('enrollFarmerForm').reset();
  if (window.lucide) lucide.createIcons();
}

function closeEnrollModal() {
  document.getElementById('enrollModal').classList.add('hidden');
}

async function handleEnrollFarmer(event) {
  event.preventDefault();
  const errEl = document.getElementById('enrollError');
  errEl.classList.add('hidden');

  const payload = {
    username: document.getElementById('enrollUsername').value.trim(),
    full_name: document.getElementById('enrollFullName').value.trim(),
    password: document.getElementById('enrollPassword').value,
    phone: document.getElementById('enrollPhone').value.trim(),
    farm_name: document.getElementById('enrollFarmName').value.trim(),
    region: document.getElementById('enrollRegion').value.trim(),
    batch_id: document.getElementById('enrollBatchId').value.trim(),
    dfl_capacity: document.getElementById('enrollDfl').value.trim(),
    breed: document.getElementById('enrollBreed').value,
    role: 'farmer'
  };

  try {
    const res = await fetch(`${API_BASE_URL}/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Farmer registration failed');

    closeEnrollModal();
    showToast(`Farmer "${payload.full_name}" registered and activated successfully!`, 'success');
    await fetchFarmers();
    await fetchStats();
    await fetchAuditLogs();

  } catch (err) {
    errEl.textContent = err.message;
    errEl.classList.remove('hidden');
  }
}

// ==========================================================================
// AUDIT LOGS TRAIL
// ==========================================================================
async function fetchAuditLogs() {
  try {
    const res = await fetch(`${API_BASE_URL}/admin/audit-logs`, {
      headers: { 'Authorization': `Bearer ${adminToken}` }
    });
    if (!res.ok) return;
    auditLogs = await res.json();

    const tbody = document.getElementById('auditTableBody');
    if (!tbody) return;

    if (!auditLogs || auditLogs.length === 0) {
      tbody.innerHTML = '<tr><td colspan="4" style="text-align:center; padding:32px;">No security actions recorded yet.</td></tr>';
      return;
    }

    tbody.innerHTML = auditLogs.map(l => {
      const dt = l.timestamp ? new Date(l.timestamp).toLocaleString() : '--';
      return `
        <tr>
          <td><code style="font-size:0.75rem;">${escapeHtml(dt)}</code></td>
          <td><strong>${escapeHtml(l.actor || l.user_id || 'system')}</strong></td>
          <td><span class="badge badge-skin">${escapeHtml(l.action || '')}</span></td>
          <td style="font-size:0.82rem;">${escapeHtml(l.details || '')}</td>
        </tr>
      `;
    }).join('');

    if (window.lucide) lucide.createIcons();

  } catch (err) {
    console.error('Error fetching audit logs:', err);
  }
}

// ==========================================================================
// TOAST NOTIFICATIONS & UTILITIES
// ==========================================================================
function showToast(message, type = 'info') {
  const container = document.getElementById('toastContainer');
  if (!container) return;

  const toast = document.createElement('div');
  toast.className = 'toast-item';
  toast.innerHTML = `
    <i data-lucide="${type === 'success' ? 'check-circle' : type === 'warning' ? 'alert-triangle' : 'info'}"></i>
    <span>${escapeHtml(message)}</span>
  `;

  container.appendChild(toast);
  if (window.lucide) lucide.createIcons();

  setTimeout(() => {
    toast.style.transition = 'opacity 0.3s ease, transform 0.3s ease';
    toast.style.opacity = '0';
    toast.style.transform = 'translateX(100%)';
    setTimeout(() => toast.remove(), 300);
  }, 4000);
}

function escapeHtml(str) {
  if (!str) return '';
  return String(str).replace(/[&<>"']/g, m => ({
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#039;'
  })[m]);
}
