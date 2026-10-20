// ==========================================================================
// SeriCare Super Admin Portal — Application Controller
// Real-Time Data Stream, Stage Climate Setpoint Configuration,
// IoT Actuators & Historical Analytics
// ==========================================================================

const API_BASE_URL = (window.location.origin.includes('localhost') || window.location.origin.includes('127.0.0.1'))
  ? `${window.location.origin}/api/v1`
  : (window.location.hostname.includes('onrender.com')
      ? `${window.location.origin}/api/v1`
      : 'https://setu-8vh9.onrender.com/api/v1');

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
let lockoutCountdownTimer = null;
let tempChart = null;
let humidityChart = null;
let airQualityChart = null;
let lightChart = null;
let isPwmSliding = false;

// Security Policy Configurations
const MAX_FAILED_ATTEMPTS = 5;
const LOCKOUT_DURATION_MS = 30000; // 30s rate-limit cooldown
const INACTIVITY_TIMEOUT_MS = 30 * 60 * 1000; // 30-minute auto-logout
let lastActivityTime = Date.now();

// Initialize on Document Ready
document.addEventListener('DOMContentLoaded', () => {
  if (window.lucide) lucide.createIcons();

  // Setup security inactivity tracking
  setupInactivityMonitor();

  // Setup lockout monitoring
  setupLockoutMonitor();

  // Verify authentication with zero UI flash
  if (adminToken) {
    checkAdminSession();
  } else {
    showAuthView();
  }
});

// ==========================================================================
// ENTERPRISE SECURITY & INACTIVITY MONITORS
// ==========================================================================
function setupInactivityMonitor() {
  const resetTimer = () => { lastActivityTime = Date.now(); };
  ['mousemove', 'keydown', 'click', 'scroll', 'touchstart'].forEach(evt => {
    window.addEventListener(evt, resetTimer, { passive: true });
  });

  setInterval(() => {
    if (adminToken && document.getElementById('dashboardView') && !document.getElementById('dashboardView').classList.contains('hidden')) {
      if (Date.now() - lastActivityTime > INACTIVITY_TIMEOUT_MS) {
        console.warn('Session expired due to 30 minutes of inactivity.');
        handleLogout('Session expired due to 30 minutes of administrative inactivity.');
      }
    }
  }, 15000);
}

function checkBruteForceLockout() {
  const lockoutUntil = parseInt(localStorage.getItem('setu_admin_lockout_until') || '0', 10);
  const banner = document.getElementById('lockoutBanner');
  const timerText = document.getElementById('lockoutTimerText');
  const loginBtn = document.getElementById('loginBtn');
  const userInput = document.getElementById('username');
  const passInput = document.getElementById('password');

  if (Date.now() < lockoutUntil) {
    const remainingSec = Math.ceil((lockoutUntil - Date.now()) / 1000);
    if (banner) banner.classList.remove('hidden');
    if (timerText) timerText.textContent = `Security lockout active: Too many failed attempts. Try again in ${remainingSec}s.`;
    if (loginBtn) loginBtn.disabled = true;
    if (userInput) userInput.disabled = true;
    if (passInput) passInput.disabled = true;
    return true;
  } else {
    if (banner) banner.classList.add('hidden');
    if (loginBtn) loginBtn.disabled = false;
    if (userInput) userInput.disabled = false;
    if (passInput) passInput.disabled = false;
    localStorage.removeItem('setu_admin_lockout_until');
    return false;
  }
}

function setupLockoutMonitor() {
  checkBruteForceLockout();
  if (lockoutCountdownTimer) clearInterval(lockoutCountdownTimer);
  lockoutCountdownTimer = setInterval(() => {
    checkBruteForceLockout();
  }, 1000);
}

// Centralized Authenticated Request Interceptor
async function authenticatedFetch(endpoint, options = {}) {
  const headers = options.headers || {};
  if (adminToken && !headers['Authorization']) {
    headers['Authorization'] = `Bearer ${adminToken}`;
  }
  options.headers = headers;

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 12000);
  options.signal = controller.signal;

  try {
    const response = await fetch(endpoint, options);
    clearTimeout(timeoutId);

    if (response.status === 401 || response.status === 403) {
      console.warn('Unauthorized or forbidden API response. Terminating administrative session.');
      handleLogout('Your session has expired. Please re-authenticate.');
      throw new Error('Unauthorized');
    }
    return response;
  } catch (err) {
    clearTimeout(timeoutId);
    if (err.name === 'AbortError') {
      throw new Error('Network request timed out. Please check your connectivity.');
    }
    throw err;
  }
}

// ==========================================================================
// VIEW NAVIGATION & TAB CONTROLS
// ==========================================================================
function showAuthView() {
  const gateway = document.getElementById('loadingGateway');
  if (gateway) gateway.classList.add('hidden');

  document.getElementById('authView').classList.remove('hidden');
  document.getElementById('dashboardView').classList.add('hidden');
  if (autoRefreshTimer) clearInterval(autoRefreshTimer);
  checkBruteForceLockout();
  if (window.lucide) lucide.createIcons();
}

function showDashboardView() {
  const gateway = document.getElementById('loadingGateway');
  if (gateway) gateway.classList.add('hidden');

  document.getElementById('authView').classList.add('hidden');
  document.getElementById('dashboardView').classList.remove('hidden');
  lastActivityTime = Date.now();
  
  // Connect real-time WebSocket stream (falls back to polling timer)
  initTelemetryWebSocket();

  if (autoRefreshTimer) clearInterval(autoRefreshTimer);
  autoRefreshTimer = setInterval(() => {
    syncLiveTelemetryStream();
  }, 4000);

  syncAllRealtimeData();
}

let telemetryWs = null;
function initTelemetryWebSocket() {
  if (telemetryWs) {
    try { telemetryWs.close(); } catch (_) {}
    telemetryWs = null;
  }
  try {
    const wsProto = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host || 'localhost:8000';
    telemetryWs = new WebSocket(`${wsProto}//${host}/api/v1/telemetry/ws/${selectedShedId}`);
    telemetryWs.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        if (msg.data) {
          syncLiveTelemetryStream();
        }
      } catch (_) {}
    };
    telemetryWs.onclose = () => {
      if (adminToken && document.getElementById('dashboardView') && !document.getElementById('dashboardView').classList.contains('hidden')) {
        setTimeout(initTelemetryWebSocket, 5000);
      }
    };
  } catch (_) {}
}

function switchNavTab(tabName) {
  currentTab = tabName;
  closeSidebar();
  
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

function toggleSidebar() {
  const sidebar = document.getElementById('appSidebar');
  let backdrop = document.getElementById('sidebarBackdrop');
  if (!backdrop) {
    backdrop = document.createElement('div');
    backdrop.id = 'sidebarBackdrop';
    backdrop.className = 'sidebar-backdrop';
    backdrop.onclick = closeSidebar;
    document.body.appendChild(backdrop);
  }

  if (sidebar) {
    sidebar.classList.toggle('open');
    if (sidebar.classList.contains('open')) {
      backdrop.classList.add('active');
    } else {
      backdrop.classList.remove('active');
    }
  }
}

function closeSidebar() {
  const sidebar = document.getElementById('appSidebar');
  const backdrop = document.getElementById('sidebarBackdrop');
  if (sidebar) sidebar.classList.remove('open');
  if (backdrop) backdrop.classList.remove('active');
}

// ==========================================================================
// AUTHENTICATION & SESSION
// ==========================================================================
async function handleLogin(event) {
  event.preventDefault();

  if (checkBruteForceLockout()) {
    return;
  }

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
      // Record failed attempt for rate limiting
      let attempts = parseInt(localStorage.getItem('setu_admin_login_attempts') || '0', 10) + 1;
      localStorage.setItem('setu_admin_login_attempts', attempts);

      if (attempts >= MAX_FAILED_ATTEMPTS) {
        const lockoutUntil = Date.now() + LOCKOUT_DURATION_MS;
        localStorage.setItem('setu_admin_lockout_until', lockoutUntil);
        localStorage.setItem('setu_admin_login_attempts', '0');
        setupLockoutMonitor();
        throw new Error('Security alert: 5 consecutive failed logins. Portal locked for 30 seconds.');
      } else {
        const remainingAttempts = MAX_FAILED_ATTEMPTS - attempts;
        throw new Error(`${data.detail || 'Authorization failed.'} (${remainingAttempts} attempts remaining before lockout)`);
      }
    }

    const role = (data.user && data.user.role) || data.role;
    if (role !== 'admin' && role !== 'superadmin') {
      throw new Error('Access denied: Account lacks Super Admin command privileges.');
    }

    // Reset rate-limit tracker on valid login
    localStorage.removeItem('setu_admin_login_attempts');
    localStorage.removeItem('setu_admin_lockout_until');

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
    if (!checkBruteForceLockout()) {
      loginBtn.disabled = false;
      loginBtn.innerHTML = '<span>Authorize Access</span> <i data-lucide="arrow-right"></i>';
    }
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
    const res = await authenticatedFetch(`${API_BASE_URL}/auth/me`);
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

function handleLogout(reason) {
  adminToken = null;
  localStorage.removeItem('setu_admin_token');
  localStorage.removeItem('setu_admin_user');
  showAuthView();
  if (reason) {
    const errorEl = document.getElementById('loginError');
    if (errorEl) {
      errorEl.textContent = reason;
      errorEl.classList.remove('hidden');
    }
    showToast(reason, 'warning');
  }
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
      fetchSheds(),
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
    const res = await authenticatedFetch(`${API_BASE_URL}/admin/stats`);
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
    const res = await authenticatedFetch(`${API_BASE_URL}/admin/telemetry-live?shed_id=${selectedShedId}`);
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

    // Overview Air Quality (CO₂) & Light Lux Gauges
    const aqi = ov.indoor_air_quality !== undefined ? ov.indoor_air_quality : 88;
    const targetAqi = ov.air_quality_target !== undefined ? ov.air_quality_target : 80;
    const readingAQ = document.getElementById('dialAirQuality') || document.getElementById('readingAirQuality');
    const targetAQ = document.getElementById('dialAirTarget') || document.getElementById('targetAirQuality');
    if (readingAQ) {
      readingAQ.textContent = `${aqi.toFixed(0)}%`;
      readingAQ.style.color = aqi < targetAqi ? 'var(--amber)' : 'var(--green-deep)';
    }
    if (targetAQ) {
      targetAQ.textContent = aqi < targetAqi ? '⚠️ Stale Air (< 80%) • Fan Active' : 'Target: ≥ 80%';
    }

    const lux = ov.indoor_light_lux !== undefined ? ov.indoor_light_lux : 22;
    const readingL = document.getElementById('dialLightLux') || document.getElementById('readingLight');
    const targetL = document.getElementById('dialLightTarget') || document.getElementById('targetLight');
    if (readingL) {
      readingL.textContent = `${lux.toFixed(0)} Lux`;
    }
    if (targetL) {
      targetL.textContent = `${ov.photoperiod_mode || 'Day'} • Target: 15–30 Lux`;
    }

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
    updateRelayUI('miniRelayLight', 'miniStateLight', ov.actuators.light);

    // Full Telemetry Tab Gauges
    document.getElementById('fullDialIndoorTemp').textContent = `${ov.indoor_temp.toFixed(1)}°C`;
    document.getElementById('fullDialIndoorHum').textContent = `${ov.indoor_humidity.toFixed(0)}%`;
    document.getElementById('fullDialOutdoorTemp').textContent = `${ov.outside_temp.toFixed(1)}°C`;
    document.getElementById('fullDialTempTarget').textContent = `Safe Band: ${targets.temp_min}°C – ${targets.temp_max}°C`;
    document.getElementById('fullDialHumTarget').textContent = `Safe Band: ${targets.hum_min}% – ${targets.hum_max}%`;
    document.getElementById('fullDialOutdoorHum').textContent = `Outside RH: ${ov.outside_humidity.toFixed(0)}%`;

    if (document.getElementById('fullDialAirQuality')) {
      document.getElementById('fullDialAirQuality').textContent = `${aqi.toFixed(0)}%`;
      document.getElementById('fullDialAirTarget').textContent = aqi < targetAqi ? 'STALE AIR • Fan Engaged' : `Target: ≥ ${targetAqi.toFixed(0)}% (CO₂ < 1%)`;
      document.getElementById('fullDialAirQuality').style.color = aqi < targetAqi ? '#d97706' : 'inherit';
    }

    if (document.getElementById('fullDialLightLux')) {
      document.getElementById('fullDialLightLux').textContent = `${lux.toFixed(0)} Lux`;
      document.getElementById('fullDialLightTarget').textContent = `${ov.photoperiod_mode || 'DAY'} • Research: 15–30 Lux`;
    }

    // Full Actuator Cards
    updateRelayUI('cardCooler', 'tagCooler', ov.actuators.cooler);
    updateRelayUI('cardFan', 'tagFan', ov.actuators.fan);
    updateRelayUI('cardHeater', 'tagHeater', ov.actuators.heater);
    updateRelayUI('cardLight', 'tagLight', ov.actuators.light);
    if (document.getElementById('lightBrightnessInfo') && ov.actuators.light_brightness !== undefined) {
      document.getElementById('lightBrightnessInfo').textContent = ov.actuators.light 
        ? `GPIO Pin 25 • Dimmed at ${ov.actuators.light_brightness}% PWM`
        : 'GPIO Pin 25 • Standby (0% PWM)';
    }

    // Sync PWM Dimmer Slider if user is not actively interacting
    if (!isPwmSliding && ov.actuators.light_brightness !== undefined) {
      const pwmSlider = document.getElementById('pwmSlider');
      const pwmValueLabel = document.getElementById('pwmValueLabel');
      if (pwmSlider) pwmSlider.value = ov.actuators.light_brightness;
      if (pwmValueLabel) pwmValueLabel.textContent = `${ov.actuators.light_brightness}% PWM`;
    }

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

// ==========================================================================
// PWM PHOTOPERIOD BULB DIMMER CONTROLS
// ==========================================================================
function handlePwmInput(val) {
  isPwmSliding = true;
  const label = document.getElementById('pwmValueLabel');
  if (label) label.textContent = `${val}% PWM`;
}

async function handlePwmChange(val) {
  isPwmSliding = false;
  const intVal = parseInt(val, 10);
  await sendPwmDutyCycle(intVal);
}

async function setBulbPreset(val) {
  const slider = document.getElementById('pwmSlider');
  const label = document.getElementById('pwmValueLabel');
  if (slider) slider.value = val;
  if (label) label.textContent = `${val}% PWM`;
  await sendPwmDutyCycle(val);
}

async function sendPwmDutyCycle(val) {
  try {
    const res = await authenticatedFetch(`${API_BASE_URL}/admin/sheds/${selectedShedId}/actuator`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        actuator: 'light_brightness',
        state: val > 0,
        value: val
      })
    });
    const data = await res.json();
    showToast(`Bulb brightness adjusted to ${val}% PWM duty cycle`, 'success');
    await fetchLiveTelemetry();
  } catch (err) {
    showToast('Failed to adjust bulb PWM: ' + err.message, 'warning');
  }
}

let monitoredSheds = [];

async function fetchSheds() {
  try {
    const res = await authenticatedFetch(`${API_BASE_URL}/admin/sheds`);
    if (!res.ok) throw new Error('Shed list retrieval failed');
    let sheds = await res.json();

    // If enrolled farmers list is available, only show sheds belonging to actual enrolled farmers
    if (Array.isArray(enrolledFarmers) && enrolledFarmers.length > 0) {
      const allowedShedIds = new Set(enrolledFarmers.map(f => f.shed_id || `shed_${f.id || f.username}`));
      const allowedFarmerNames = new Set(enrolledFarmers.map(f => (f.full_name || f.username || '').toLowerCase()));
      const filtered = sheds.filter(s => 
        allowedShedIds.has(s.shed_id) || 
        (s.farmer_name && allowedFarmerNames.has(s.farmer_name.toLowerCase()))
      );
      if (filtered.length > 0) {
        sheds = filtered;
      }
    }

    monitoredSheds = sheds;
    renderShedSelector(monitoredSheds);
  } catch (err) {
    console.debug('Failed to fetch /admin/sheds, falling back to farmer sheds:', err);
    buildShedsFromFarmers();
  }
}

function buildShedsFromFarmers() {
  if (!Array.isArray(enrolledFarmers) || enrolledFarmers.length === 0) return;
  monitoredSheds = enrolledFarmers.map(f => {
    const sId = f.shed_id || `shed_${f.id || f.username}`;
    const farmName = f.farm_name || 'Rearing Shed';
    const farmerName = f.full_name || f.username || '';
    const display = farmerName ? `${farmName} (${farmerName})` : farmName;
    return {
      shed_id: sId,
      farm_name: farmName,
      farmer_name: farmerName,
      display_name: display
    };
  });
  renderShedSelector(monitoredSheds);
}

function renderShedSelector(sheds) {
  const select = document.getElementById('shedSelect');
  if (!select) return;
  if (!Array.isArray(sheds) || sheds.length === 0) return;

  const currentVal = selectedShedId || select.value || (sheds[0] && sheds[0].shed_id);
  select.innerHTML = sheds.map(s => {
    const sId = s.shed_id;
    const isSelected = sId === currentVal ? 'selected' : '';
    const label = s.display_name || s.farm_name || sId;
    return `<option value="${escapeHtml(sId)}" ${isSelected}>${escapeHtml(label)}</option>`;
  }).join('');

  const hasCurrent = sheds.some(s => s.shed_id === currentVal);
  if (!hasCurrent && sheds.length > 0) {
    selectedShedId = sheds[0].shed_id;
    select.value = selectedShedId;
  } else {
    selectedShedId = currentVal;
    select.value = currentVal;
  }
}

function handleShedChange(shedId) {
  selectedShedId = shedId;
  initTelemetryWebSocket();
  fetchLiveTelemetry();
  fetchStats();
}

function switchToFarmerShed(shedId) {
  if (!shedId) return;
  const select = document.getElementById('shedSelect');
  if (select) {
    select.value = shedId;
  }
  selectedShedId = shedId;
  initTelemetryWebSocket();
  fetchLiveTelemetry();
  fetchStats();
  switchTab('overview');
  showToast(`Switched active IoT monitoring to ${shedId.toUpperCase()}!`, 'info');
}

// ==========================================================================
// SUPER ADMIN STAGE CLIMATE LEVELS & AUTO-MODE SETPOINTS
// ==========================================================================
async function fetchStages() {
  try {
    const res = await authenticatedFetch(`${API_BASE_URL}/admin/stages`);
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
    const res = await authenticatedFetch(`${API_BASE_URL}/admin/stages/${selectedStageId}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json'
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
    const res = await authenticatedFetch(`${API_BASE_URL}/admin/sheds/${selectedShedId}/stage`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
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
    const res = await authenticatedFetch(`${API_BASE_URL}/admin/stages/reset`, {
      method: 'POST'
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
    const res = await authenticatedFetch(`${API_BASE_URL}/admin/sheds/${selectedShedId}/actuator`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
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
    const res = await authenticatedFetch(`${API_BASE_URL}/admin/sheds/${selectedShedId}/auto-mode`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
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
    const res = await authenticatedFetch(`${API_BASE_URL}/admin/emergency-control`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
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

  // 3. Air Quality Chart (CO₂ %)
  const aqiCanvas = document.getElementById('airQualityChart');
  if (aqiCanvas) {
    const ctx = aqiCanvas.getContext('2d');
    if (airQualityChart) airQualityChart.destroy();

    const indoorAqi = history.map(h => h.air_quality !== undefined ? h.air_quality : 88);
    const targetAqiLine = history.map(() => 80);

    airQualityChart = new Chart(ctx, {
      type: 'line',
      data: {
        labels: labels,
        datasets: [
          {
            label: 'Air Quality (CO₂ %)',
            data: indoorAqi,
            borderColor: '#2A6A4A',
            backgroundColor: 'rgba(42, 106, 74, 0.08)',
            fill: true,
            tension: 0.35,
            borderWidth: 2.5,
            pointRadius: 3,
            pointBackgroundColor: '#2A6A4A'
          },
          {
            label: 'Safe Threshold (≥ 80%)',
            data: targetAqiLine,
            borderColor: 'rgba(180, 108, 18, 0.8)',
            borderDash: [6, 4],
            borderWidth: 1.8,
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
            ticks: { font: { family: "'JetBrains Mono', monospace", size: 11 }, callback: v => `${v}%` },
            min: 50,
            max: 100
          },
          x: {
            grid: { display: false },
            ticks: { font: { family: "'JetBrains Mono', monospace", size: 11 } }
          }
        }
      }
    });
  }

  // 4. Light Intensity Chart (Lux)
  const lightCanvas = document.getElementById('lightChart');
  if (lightCanvas) {
    const ctx = lightCanvas.getContext('2d');
    if (lightChart) lightChart.destroy();

    const indoorLux = history.map(h => h.light_lux !== undefined ? h.light_lux : 22);
    const minLuxLine = history.map(() => 15);
    const maxLuxLine = history.map(() => 30);

    lightChart = new Chart(ctx, {
      type: 'line',
      data: {
        labels: labels,
        datasets: [
          {
            label: 'Light Intensity (Lux)',
            data: indoorLux,
            borderColor: '#B46C12',
            backgroundColor: 'rgba(180, 108, 18, 0.08)',
            fill: true,
            tension: 0.35,
            borderWidth: 2.5,
            pointRadius: 3,
            pointBackgroundColor: '#B46C12'
          },
          {
            label: 'Photoperiod Min (15 Lux)',
            data: minLuxLine,
            borderColor: 'rgba(78, 149, 113, 0.7)',
            borderDash: [6, 4],
            borderWidth: 1.5,
            pointRadius: 0
          },
          {
            label: 'Photoperiod Max (30 Lux)',
            data: maxLuxLine,
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
            ticks: { font: { family: "'JetBrains Mono', monospace", size: 11 }, callback: v => `${v} Lux` },
            min: 0,
            max: 60
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
    const res = await authenticatedFetch(`${API_BASE_URL}/admin/farmers`);
    if (!res.ok) return;
    enrolledFarmers = await res.json();
    renderFarmersTable(enrolledFarmers);
    await fetchSheds();
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

  // Ensure every farmer row in UI has a distinct shed_id
  const seenShedIds = new Set();
  let nextShedIndex = 1;
  farmers.forEach(f => {
    let sId = f.shed_id;
    if (!sId || seenShedIds.has(sId)) {
      while (seenShedIds.has(`shed_${String(nextShedIndex).padStart(2, '0')}`)) {
        nextShedIndex++;
      }
      sId = `shed_${String(nextShedIndex).padStart(2, '0')}`;
      f.shed_id = sId;
    }
    seenShedIds.add(sId);
  });

  tbody.innerHTML = farmers.map(f => {
    const isActive = f.is_active === 1 || f.is_active === true;
    const sId = f.shed_id || 'shed_01';
    return `
      <tr>
        <td>
          <div class="farmer-name-cell">${escapeHtml(f.full_name || f.username)}</div>
          <div class="farmer-sub-cell">@${escapeHtml(f.username)} • ${escapeHtml(f.phone || 'N/A')}</div>
        </td>
        <td>
          <div style="display:flex; flex-direction:column; gap:4px;">
            <strong>${escapeHtml(f.farm_name || 'Main Shed')}</strong>
            <div style="display:flex; align-items:center; gap:6px;">
              <span class="badge" style="font-size:0.68rem; padding:1px 6px; background:var(--bg-card); border:1px solid var(--border-light); font-weight:600;">
                ${escapeHtml(sId.toUpperCase())}
              </span>
              <button type="button" class="btn-text" style="font-size:0.75rem; color:var(--green-leaf); cursor:pointer; background:none; border:none; padding:0; text-decoration:underline;" onclick="switchToFarmerShed('${escapeHtml(sId)}')">
                Monitor &rarr;
              </button>
            </div>
          </div>
        </td>
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
            <button class="btn-icon" title="Monitor Shed Telemetry" onclick="switchToFarmerShed('${escapeHtml(sId)}')">
              <i data-lucide="radio"></i>
            </button>
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
    const res = await authenticatedFetch(`${API_BASE_URL}/admin/farmers/${farmerId}/status`, {
      method: 'PATCH',
      headers: {
        'Content-Type': 'application/json'
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
    const res = await authenticatedFetch(`${API_BASE_URL}/admin/farmers/${farmerId}`, {
      method: 'DELETE'
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
  const otherWrap = document.getElementById('enrollBreedOtherWrap');
  if (otherWrap) otherWrap.classList.add('hidden');
  const customInput = document.getElementById('enrollBreedCustom');
  if (customInput) {
    customInput.value = '';
    customInput.required = false;
  }
  const shedIdInput = document.getElementById('enrollShedId');
  if (shedIdInput) shedIdInput.value = '';
  if (window.lucide) lucide.createIcons();
}

function handleBreedSelectionChange(value) {
  const otherWrap = document.getElementById('enrollBreedOtherWrap');
  const customInput = document.getElementById('enrollBreedCustom');
  if (value === 'Other') {
    if (otherWrap) otherWrap.classList.remove('hidden');
    if (customInput) {
      customInput.required = true;
      customInput.focus();
    }
  } else {
    if (otherWrap) otherWrap.classList.add('hidden');
    if (customInput) {
      customInput.required = false;
      customInput.value = '';
    }
  }
}

function closeEnrollModal() {
  document.getElementById('enrollModal').classList.add('hidden');
}

async function handleEnrollFarmer(event) {
  event.preventDefault();
  const errEl = document.getElementById('enrollError');
  errEl.classList.add('hidden');

  const selectedBreed = document.getElementById('enrollBreed').value;
  let finalBreed = selectedBreed;
  if (selectedBreed === 'Other') {
    const customBreed = (document.getElementById('enrollBreedCustom')?.value || '').trim();
    finalBreed = customBreed || 'Other';
  }

  const shedIdVal = (document.getElementById('enrollShedId')?.value || '').trim();
  const payload = {
    username: document.getElementById('enrollUsername').value.trim(),
    full_name: document.getElementById('enrollFullName').value.trim(),
    password: document.getElementById('enrollPassword').value,
    phone: document.getElementById('enrollPhone').value.trim(),
    farm_name: document.getElementById('enrollFarmName').value.trim(),
    shed_id: shedIdVal || undefined,
    region: document.getElementById('enrollRegion').value.trim(),
    batch_id: document.getElementById('enrollBatchId').value.trim(),
    dfl_capacity: document.getElementById('enrollDfl').value.trim(),
    breed: finalBreed,
    role: 'farmer'
  };

  try {
    const res = await authenticatedFetch(`${API_BASE_URL}/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Farmer registration failed');

    closeEnrollModal();
    showToast(`Farmer "${payload.full_name}" registered and activated successfully!`, 'success');
    await fetchFarmers();
    await fetchSheds();
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
    const res = await authenticatedFetch(`${API_BASE_URL}/admin/audit-logs`);
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
