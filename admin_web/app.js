// Setu Super Admin Command Portal Logic
const API_BASE_URL = window.location.origin.includes('localhost') || window.location.origin.includes('127.0.0.1')
  ? `${window.location.origin}/api/v1`
  : 'http://localhost:8000/api/v1';

let adminToken = localStorage.getItem('setu_admin_token') || null;
let enrolledFarmers = [];

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
  if (window.lucide) {
    lucide.createIcons();
  }
  
  if (adminToken) {
    checkAdminSession();
  } else {
    showAuthView();
  }
});

function showAuthView() {
  document.getElementById('authView').classList.remove('hidden');
  document.getElementById('dashboardView').classList.add('hidden');
  if (window.lucide) lucide.createIcons();
}

function showDashboardView() {
  document.getElementById('authView').classList.add('hidden');
  document.getElementById('dashboardView').classList.remove('hidden');
  if (window.lucide) lucide.createIcons();
  loadAllDashboardData();
}

// ================= AUTHENTICATION =================
async function handleLogin(event) {
  event.preventDefault();
  const usernameInput = document.getElementById('username').value.trim();
  const passwordInput = document.getElementById('password').value;
  const errorEl = document.getElementById('loginError');
  const loginBtn = document.getElementById('loginBtn');

  errorEl.classList.add('hidden');
  loginBtn.disabled = true;
  loginBtn.innerHTML = '<span>Verifying Admin Access...</span>';

  try {
    const response = await fetch(`${API_BASE_URL}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        username: usernameInput,
        password: passwordInput
      })
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.detail || 'Authentication failed. Check credentials.');
    }

    const role = (data.user && data.user.role) || data.role;
    if (role !== 'admin' && role !== 'superadmin') {
      throw new Error('Access denied: Account lacks Super Admin privileges.');
    }

    adminToken = data.access_token;
    localStorage.setItem('setu_admin_token', adminToken);
    localStorage.setItem('setu_admin_user', JSON.stringify(data.user || data));
    
    const displayName = (data.user && (data.user.full_name || data.user.username)) || data.full_name || data.username || 'Super Admin';
    document.getElementById('adminDisplayName').textContent = displayName;
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
    if (!res.ok) throw new Error('Token expired');
    const user = await res.json();
    if (user.role !== 'admin' && user.role !== 'superadmin') {
      throw new Error('Unauthorized role');
    }
    document.getElementById('adminDisplayName').textContent = user.full_name || user.username;
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

// ================= DATA FETCHING =================
async function loadAllDashboardData() {
  await Promise.all([
    fetchStats(),
    fetchFarmers(),
    fetchTelemetry(),
    fetchAuditLogs()
  ]);
}

async function fetchStats() {
  try {
    const res = await fetch(`${API_BASE_URL}/admin/stats`, {
      headers: { 'Authorization': `Bearer ${adminToken}` }
    });
    if (!res.ok) return;
    const stats = await res.json();

    document.getElementById('kpiTotalFarmers').textContent = stats.total_farmers ?? '--';
    document.getElementById('kpiActiveFarmers').textContent = stats.active_farmers ?? '--';
    document.getElementById('kpiDflCapacity').textContent = stats.total_dfl_capacity ?? '--';
    document.getElementById('kpiMonitoredSheds').textContent = stats.active_sheds_monitored ?? '1';
    document.getElementById('kpiActiveRelays').textContent = stats.active_relays_count ?? '0';

  } catch (err) {
    console.error('Error fetching admin stats:', err);
  }
}

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
  if (!farmers || farmers.length === 0) {
    tbody.innerHTML = '<tr><td colspan="8" class="text-center">No enrolled farmers found.</td></tr>';
    return;
  }

  tbody.innerHTML = farmers.map(f => {
    const isActive = f.is_active === 1 || f.is_active === true;
    return `
      <tr>
        <td>
          <div class="farmer-cell-name">${escapeHtml(f.full_name || f.username)}</div>
          <div class="farmer-cell-user">@${escapeHtml(f.username)} • ${escapeHtml(f.phone || 'N/A')}</div>
        </td>
        <td><strong>${escapeHtml(f.farm_name || 'Main Shed')}</strong></td>
        <td>${escapeHtml(f.region || 'Mulbagal, Kolar')}</td>
        <td><code>${escapeHtml(f.batch_id || 'BATCH-2026')}</code></td>
        <td>${escapeHtml(f.dfl_capacity || 'N/A')}</td>
        <td><small>${escapeHtml(f.breed || 'Bivoltine')}</small></td>
        <td>
          <span class="badge-status ${isActive ? 'active' : 'inactive'}">
            <span class="pulse-dot" style="width:6px;height:6px;background:${isActive ? '#10B981':'#94A3B8'}"></span>
            ${isActive ? 'Active' : 'Suspended'}
          </span>
        </td>
        <td>
          <div class="action-buttons">
            <button class="btn-icon" title="${isActive ? 'Deactivate Farmer' : 'Activate Farmer'}" onclick="toggleFarmerStatus('${f.username}', ${!isActive})">
              <i data-lucide="${isActive ? 'user-x' : 'user-check'}"></i>
            </button>
            <button class="btn-icon danger" title="Delete Farmer" onclick="confirmDeleteFarmer('${f.username}')">
              <i data-lucide="trash-2"></i>
            </button>
          </div>
        </td>
      </tr>
    `;
  }).join('');

  if (window.lucide) lucide.createIcons();
}

function filterFarmers() {
  const query = document.getElementById('farmerSearch').value.toLowerCase();
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
    if (!res.ok) throw new Error('Status update failed');
    await fetchFarmers();
    await fetchStats();
    await fetchAuditLogs();
  } catch (err) {
    alert('Failed to update farmer status: ' + err.message);
  }
}

async function confirmDeleteFarmer(farmerId) {
  if (!confirm(`Are you sure you want to remove farmer account "${farmerId}"? This will delete all rearing batch linkages.`)) {
    return;
  }
  try {
    const res = await fetch(`${API_BASE_URL}/admin/farmers/${farmerId}`, {
      method: 'DELETE',
      headers: { 'Authorization': `Bearer ${adminToken}` }
    });
    if (!res.ok) throw new Error('Failed to delete user');
    await fetchFarmers();
    await fetchStats();
    await fetchAuditLogs();
  } catch (err) {
    alert('Failed to delete farmer: ' + err.message);
  }
}

// ================= LIVE TELEMETRY =================
async function fetchTelemetry() {
  try {
    const res = await fetch(`${API_BASE_URL}/telemetry/shed_01`, {
      headers: { 'Authorization': `Bearer ${adminToken}` }
    });
    if (!res.ok) return;
    const data = await res.json();

    document.getElementById('shedTemp').textContent = `${data.inside.temperature.toFixed(1)}°C`;
    document.getElementById('shedHumidity').textContent = `${data.inside.humidity.toFixed(0)}%`;
    document.getElementById('outsideTemp').textContent = `${data.outside.temperature.toFixed(1)}°C`;
    document.getElementById('weatherCondition').textContent = data.outside.weather_condition || 'Clear';

    // Actuators
    const cooler = data.actuators.cooler;
    const fan = data.actuators.fan;
    const heater = data.actuators.heater;

    setRelay('relayCooler', 'stateCooler', cooler);
    setRelay('relayFan', 'stateFan', fan);
    setRelay('relayHeater', 'stateHeater', heater);

  } catch (err) {
    console.error('Error fetching live telemetry:', err);
  }
}

function setRelay(cardId, stateId, active) {
  const card = document.getElementById(cardId);
  const badge = document.getElementById(stateId);
  if (active) {
    card.classList.add('active');
    badge.textContent = 'RUNNING';
  } else {
    card.classList.remove('active');
    badge.textContent = 'OFF';
  }
}

// ================= EMERGENCY CONTROLS =================
async function triggerEmergency(action) {
  const feedback = document.getElementById('emergencyFeedback');
  feedback.classList.add('hidden');

  const confirmMsg = action === 'COOLDOWN_ALL' 
    ? 'Are you sure you want to execute EMERGENCY SHUTDOWN on all actuators?' 
    : `Execute immediate command "${action}" on Shed 01?`;

  if (!confirm(confirmMsg)) return;

  try {
    const res = await fetch(`${API_BASE_URL}/admin/emergency-control`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${adminToken}`
      },
      body: JSON.stringify({
        shed_id: 'shed_01',
        action: action
      })
    });

    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Emergency command failed');

    feedback.textContent = `Success: ${data.details}`;
    feedback.classList.remove('hidden');

    await fetchTelemetry();
    await fetchStats();
    await fetchAuditLogs();

    setTimeout(() => { feedback.classList.add('hidden'); }, 5000);

  } catch (err) {
    alert('Emergency control failed: ' + err.message);
  }
}

// ================= AUDIT LOGS =================
async function fetchAuditLogs() {
  try {
    const res = await fetch(`${API_BASE_URL}/admin/audit-logs`, {
      headers: { 'Authorization': `Bearer ${adminToken}` }
    });
    if (!res.ok) return;
    const logs = await res.json();
    const tbody = document.getElementById('auditTableBody');

    if (!logs || logs.length === 0) {
      tbody.innerHTML = '<tr><td colspan="4" class="text-center">No audit logs recorded yet.</td></tr>';
      return;
    }

    tbody.innerHTML = logs.map(l => `
      <tr>
        <td class="timestamp-cell">${escapeHtml(l.timestamp || '')}</td>
        <td><strong>${escapeHtml(l.user_id || 'system')}</strong></td>
        <td><span class="badge-action">${escapeHtml(l.action || '')}</span></td>
        <td>${escapeHtml(l.details || '')}</td>
      </tr>
    `).join('');

  } catch (err) {
    console.error('Error fetching audit logs:', err);
  }
}

// ================= ENROLL FARMER MODAL =================
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
    phone: document.getElementById('enrollPhone').value.trim() || undefined,
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
    if (!res.ok) throw new Error(data.detail || 'Farmer enrollment failed');

    closeEnrollModal();
    await fetchFarmers();
    await fetchStats();
    await fetchAuditLogs();
    alert(`Farmer "${payload.full_name}" (@${payload.username}) enrolled successfully!`);

  } catch (err) {
    errEl.textContent = err.message;
    errEl.classList.remove('hidden');
  }
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
