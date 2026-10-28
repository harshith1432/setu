// ==========================================================================
// Setu Enterprise Platform Controller
// Complete Modern JavaScript Controller for 21 Enterprise Modules
// Real-time Telemetry, RBAC Persona Switching, Auditable Workflows & Zero Static Data
// ==========================================================================

const isLocalHost = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
const isOnRenderHost = window.location.hostname === 'onrender.com' || window.location.hostname.endsWith('.onrender.com');

const API_BASE_URL = isLocalHost
  ? `${window.location.origin}/api/v1`
  : (isOnRenderHost
      ? `${window.location.origin}/api/v1`
      : 'https://setu-8vh9.onrender.com/api/v1');

// ==============================================================================
// TAB-ISOLATED SESSION MANAGEMENT & STATE STORAGE
// ==============================================================================
// Web browsers isolate window.sessionStorage strictly to the individual tab browsing context.
// By maintaining credentials in sessionStorage (with zero cross-tab localStorage pollution),
// multiple tabs in the same browser profile operate with independent identities simultaneously.
const TAB_STORAGE = window.sessionStorage;

// Generate or retrieve unique unguessable Tab Identifier
let tabId = TAB_STORAGE.getItem('setu_tab_id');
if (!tabId) {
  tabId = 'tab_' + (window.crypto && crypto.randomUUID ? crypto.randomUUID() : (Math.random().toString(36).substring(2, 9) + Date.now().toString(36)));
  TAB_STORAGE.setItem('setu_tab_id', tabId);
}

// Global Application State - Tab-isolated with persistent fallback
let adminToken = TAB_STORAGE.getItem('setu_tab_token') ||
  localStorage.getItem('setu_token') ||
  localStorage.getItem('setu_admin_token') ||
  null;
if (adminToken && !TAB_STORAGE.getItem('setu_tab_token')) {
  try { TAB_STORAGE.setItem('setu_tab_token', adminToken); } catch (_) {}
}
window.adminToken = adminToken;
window.API_BASE_URL = API_BASE_URL;
let currentSessionId = TAB_STORAGE.getItem('setu_tab_session_id') || null;
let currentUser = JSON.parse(TAB_STORAGE.getItem('setu_tab_user') || localStorage.getItem('setu_user') || 'null');
if (currentUser && !TAB_STORAGE.getItem('setu_tab_user')) {
  try { TAB_STORAGE.setItem('setu_tab_user', JSON.stringify(currentUser)); } catch (_) {}
}
let currentTab = TAB_STORAGE.getItem('setu_tab_nav') || 'overview';
let selectedShedId = TAB_STORAGE.getItem('setu_tab_shed') || 'shed_01';

// Global safe HTML escaping utility
function escapeHtml(str) {
  if (str === null || str === undefined) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}
window.escapeHtml = escapeHtml;

// SEC-MULTI-TAB: Purge legacy shared localStorage tokens to prevent cross-tab contamination
try {
  localStorage.removeItem('setu_admin_token');
  localStorage.removeItem('setu_current_user');
} catch (_) {}

// SEC-MULTI-TAB: Listen for storage events and prevent cross-tab pollution
window.addEventListener('storage', (e) => {
  if (e.key === 'setu_admin_token' || e.key === 'setu_current_user') {
    try {
      localStorage.removeItem('setu_admin_token');
      localStorage.removeItem('setu_current_user');
    } catch (_) {}
  }
});

// Global Platform Refresh helper (triggers clean reload when logo or branding is clicked)
function refreshPlatform() {
  window.location.reload();
}
window.refreshPlatform = refreshPlatform;

// SEC-MULTI-TAB: Transparent fetch interceptor injecting tab credentials and tracking session validity
const _originalFetch = window.fetch;
window.fetch = async function(resource, init = {}) {
  init = init || {};
  init.headers = init.headers || {};
  if (adminToken && typeof init.headers === 'object') {
    if (init.headers instanceof Headers) {
      if (!init.headers.has('X-Session-ID') && currentSessionId) {
        init.headers.set('X-Session-ID', currentSessionId);
      }
      if (!init.headers.has('X-Tab-ID')) {
        init.headers.set('X-Tab-ID', tabId);
      }
    } else {
      if (!init.headers['X-Session-ID'] && currentSessionId) {
        init.headers['X-Session-ID'] = currentSessionId;
      }
      if (!init.headers['X-Tab-ID']) {
        init.headers['X-Tab-ID'] = tabId;
      }
    }
  }
  const res = await _originalFetch.call(this, resource, init);
  if (res.status === 401 && adminToken) {
    const urlStr = typeof resource === 'string' ? resource : (resource.url || '');
    if (!urlStr.includes('/auth/login') && !urlStr.includes('/auth/check-farmer')) {
      console.warn(`[MultiTab] Session invalidated for tab ${tabId}. Disconnecting.`);
      handleLogout('Your tab session has expired or was terminated.');
    }
  }
  return res;
};
let availableSheds = [];
let allFarmersData = [];
let farmersCurrentPage = 1;
let farmersPageSize = 10;
let farmersFilteredList = [];
let telemetryEventSource = null;
let telemetryWs = null;
let lastSyncTimestamp = null;
let syncClockInterval = null;

// Chart Instances
let chartTempHum = null;
let chartOrdersRev = null;
let chartRegional = null;
let chartFarmerGrowth = null;

// Inactivity & Security
const INACTIVITY_TIMEOUT_MS = 30 * 60 * 1000; // 30 minutes
let lastActivityTime = Date.now();

// Role Permissions Matrix (Covering all 10 Enterprise Roles)
const ROLE_PERMISSIONS = {
  superadmin: ['overview', 'employees', 'roles', 'departments', 'tasks', 'live-monitoring', 'analytics', 'alerts', 'farmers', 'sheds', 'devices', 'sensor-config', 'products', 'enquiries', 'orders', 'billing', 'support', 'installations', 'install-team', 'research', 'guidance', 'reports', 'users', 'audit', 'integrations', 'settings'],
  admin: ['overview', 'employees', 'roles', 'departments', 'tasks', 'live-monitoring', 'analytics', 'alerts', 'farmers', 'sheds', 'devices', 'sensor-config', 'products', 'enquiries', 'orders', 'billing', 'support', 'installations', 'install-team', 'research', 'guidance', 'reports', 'users', 'audit', 'integrations', 'settings'],
  company_admin: ['overview', 'employees', 'roles', 'departments', 'tasks', 'live-monitoring', 'analytics', 'alerts', 'farmers', 'sheds', 'devices', 'sensor-config', 'products', 'orders', 'billing', 'support', 'installations', 'install-team', 'research', 'guidance', 'reports', 'audit', 'integrations'],
  ceo: ['overview', 'tasks', 'live-monitoring', 'analytics', 'alerts', 'farmers', 'sheds', 'devices', 'products', 'orders', 'billing', 'research', 'guidance', 'reports', 'audit', 'integrations'],
  hr: ['overview', 'employees', 'departments', 'roles', 'audit', 'guidance'],
  operations_manager: ['overview', 'live-monitoring', 'alerts', 'farmers', 'sheds', 'devices', 'sensor-config', 'installations', 'install-team', 'research', 'guidance', 'reports', 'analytics'],
  technician: ['tasks', 'live-monitoring', 'sheds', 'devices', 'sensor-config', 'installations', 'install-team', 'guidance', 'alerts'],
  sales: ['overview', 'tasks', 'products', 'enquiries', 'orders', 'billing', 'farmers', 'reports'],
  support: ['overview', 'tasks', 'farmers', 'sheds', 'support', 'guidance', 'alerts', 'orders'],
  analyst: ['overview', 'live-monitoring', 'analytics', 'farmers', 'sheds', 'research', 'guidance', 'reports'],
  farmer: ['tasks', 'live-monitoring', 'sheds', 'guidance', 'support', 'orders', 'alerts']
};

const ROLE_DEFAULT_TABS = {
  superadmin: 'overview',
  company_admin: 'overview',
  ceo: 'overview',
  hr: 'employees',
  operations_manager: 'sheds',
  technician: 'installations',
  sales: 'orders',
  support: 'support',
  analyst: 'analytics',
  farmer: 'live-monitoring'
};

// Roles and tabs that require Rearing Shed selection & live IoT telemetry controls
const SHED_TELEMETRY_ROLES = [
  'superadmin',
  'admin',
  'company_admin',
  'operations_manager',
  'technician',
  'farmer',
  'analyst'
];

const SHED_TELEMETRY_TABS = [
  'overview',
  'live-monitoring',
  'sheds',
  'devices',
  'sensor-config',
  'alerts',
  'installations',
  'install-team',
  'analytics',
  'research'
];

function updateTopBarControlsVisibility() {
  const controls = document.getElementById('topShedTelemetryControls');
  if (!controls) return;

  const role = currentUser?.role || 'farmer';
  const perms = currentUser?.permissions || [];

  // Check role eligibility or explicit permissions
  const roleEligible = SHED_TELEMETRY_ROLES.includes(role) ||
    perms.includes('sheds:read') ||
    perms.includes('iot:read') ||
    perms.includes('iot:telemetry') ||
    perms.includes('iot:control');

  // Explicit non-operational roles (HR, Sales, Support, CEO) should not see shed controls on general/administrative views
  const isNonShedRole = ['hr', 'sales', 'support', 'ceo'].includes(role) && !perms.includes('sheds:write');

  // Tab relevance
  const tabEligible = SHED_TELEMETRY_TABS.includes(currentTab);

  if (roleEligible && !isNonShedRole && tabEligible) {
    controls.style.display = 'flex';
    if (!availableSheds || availableSheds.length === 0) {
      loadShedsList();
    }
    initRealtimeDataStream();
  } else {
    controls.style.display = 'none';
    if (telemetryEventSource) {
      try {
        telemetryEventSource.close();
      } catch (_) {}
      telemetryEventSource = null;
    }
  }
}

// ==========================================================================
// 1. INITIALIZATION & LIFECYCLE
// ==========================================================================

document.addEventListener('DOMContentLoaded', () => {
  if (window.lucide) lucide.createIcons();

  // Check for onboarding invitation token in URL hash or search params
  const hash = window.location.hash;
  if (hash && hash.includes('invitation_token=')) {
    const token = hash.split('invitation_token=')[1].split('&')[0];
    if (token) checkAndOpenInvitationModal(token);
  } else {
    const urlParams = new URLSearchParams(window.location.search);
    const token = urlParams.get('invitation_token');
    if (token) checkAndOpenInvitationModal(token);
  }

  // Initialize theme
  const savedTheme = localStorage.getItem('setu_theme') || 'light';
  document.documentElement.setAttribute('data-theme', savedTheme);
  updateThemeIcon(savedTheme);

  // Restore sidebar rail mode
  const savedRail = localStorage.getItem('setu_sidebar_rail');
  if (savedRail === 'true') {
    const layout = document.getElementById('dashboardView');
    if (layout) layout.classList.add('sidebar-collapsed');
    const icon = document.getElementById('sidebarRailIcon') || document.querySelector('#btnSidebarToggle i');
    if (icon) icon.setAttribute('data-lucide', 'panel-left-open');
  }

  // Keyboard shortcut listener (Ctrl+K for Command Palette, ESC to close, Arrow keys & Enter for Modal control)
  window.addEventListener('keydown', (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
      e.preventDefault();
      openCommandPalette();
      return;
    }

    const appModal = document.getElementById('appModalBackdrop');
    const isAppModalOpen = appModal && !appModal.classList.contains('hidden');
    const invModal = document.getElementById('invitationActivationModal');
    const isInvModalOpen = invModal && !invModal.classList.contains('hidden');

    if (e.key === 'Escape') {
      closeCommandPalette();
      closeAppDrawer();
      closeAppModal();
      closeUserDropdown();
      closeAllRowActionMenus();
      const notif = document.getElementById('notifDropdown');
      if (notif) notif.classList.add('hidden');
      if (isInvModalOpen && typeof closeInvitationActivationModal === 'function') {
        closeInvitationActivationModal();
      }
      return;
    }

    const activeModalCard = isAppModalOpen 
      ? appModal.querySelector('.modal-card') 
      : (isInvModalOpen ? invModal.querySelector('.modal-card') : null);

    if (activeModalCard) {
      handleModalKeyboardNavigation(e, activeModalCard);
    }
  });

  // Global document click listener to close popovers when clicking outside
  document.addEventListener('click', (e) => {
    const userWrap = document.querySelector('.user-menu-wrap');
    if (userWrap && !userWrap.contains(e.target)) {
      closeUserDropdown();
    }
    const notifWrap = document.querySelector('.notif-btn-wrap');
    if (notifWrap && !notifWrap.contains(e.target)) {
      const notif = document.getElementById('notifDropdown');
      if (notif) notif.classList.add('hidden');
    }
    if (!e.target.closest('.row-action-dropdown')) {
      closeAllRowActionMenus();
    }
  });

  // Setup security monitor
  setupInactivityMonitor();

  // Start real-time sync clock
  startSyncClock();

  // Check existing session
  if (adminToken) {
    verifySession();
  } else {
    showAuthView();
  }
});

function setupInactivityMonitor() {
  const resetTimer = () => { lastActivityTime = Date.now(); };
  ['mousemove', 'keydown', 'click', 'scroll', 'touchstart'].forEach(evt => {
    window.addEventListener(evt, resetTimer, { passive: true });
  });

  setInterval(() => {
    if (adminToken && Date.now() - lastActivityTime > INACTIVITY_TIMEOUT_MS) {
      handleLogout('Session expired due to 30 minutes of inactivity.');
    }
  }, 15000);
}

function startSyncClock() {
  if (syncClockInterval) clearInterval(syncClockInterval);
  syncClockInterval = setInterval(() => {
    const clockEl = document.getElementById('topSyncClock');
    if (!clockEl) return;
    if (lastSyncTimestamp) {
      const now = new Date();
      const diffSec = Math.floor((now - lastSyncTimestamp) / 1000);
      if (diffSec < 5) {
        clockEl.textContent = 'Synced: Just now';
      } else if (diffSec < 60) {
        clockEl.textContent = `Synced: ${diffSec}s ago`;
      } else {
        const timeStr = lastSyncTimestamp.toLocaleTimeString();
        clockEl.textContent = `Synced: ${timeStr}`;
      }
    } else {
      clockEl.textContent = 'Synced: Connecting...';
    }
  }, 1000);
}

// ==========================================================================
// 2. AUTHENTICATION & SESSION MANAGEMENT
// ==========================================================================

function showAuthView() {
  document.getElementById('loadingGateway').classList.add('hidden');
  document.getElementById('dashboardView').classList.add('hidden');
  document.getElementById('authView').classList.remove('hidden');
  if (window.lucide) lucide.createIcons();
}

function showDashboardView() {
  document.getElementById('loadingGateway').classList.add('hidden');
  document.getElementById('authView').classList.add('hidden');
  document.getElementById('dashboardView').classList.remove('hidden');

  updateUserBadge();
  enforceRoleNavigation();

  // Redirect to role-appropriate starting tab
  const role = currentUser?.role || 'farmer';
  const defaultTab = ROLE_DEFAULT_TABS[role] || 'overview';
  currentTab = defaultTab;
  switchNavTab(currentTab);
  
  loadRoleDashboardHero();
  updateTopBarControlsVisibility();

  if (window.lucide) lucide.createIcons();
}

function togglePasswordVisibility(inputId = 'password', btn = null) {
  const input = (typeof inputId === 'string' ? document.getElementById(inputId) : inputId) || document.getElementById('password');
  if (!input) return;
  const isPwd = input.type === 'password';
  input.type = isPwd ? 'text' : 'password';

  const toggleBtn = btn || (typeof inputId === 'string' && document.getElementById(inputId + 'ToggleBtn')) || document.getElementById('togglePasswordBtn') || (input.parentElement ? input.parentElement.querySelector('.btn-toggle-password') : null);

  if (toggleBtn) {
    toggleBtn.innerHTML = `<i data-lucide="${isPwd ? 'eye-off' : 'eye'}" style="width: 18px; height: 18px;"></i>`;
    if (window.lucide) lucide.createIcons();
  }
}

function openForgotPasswordModal() {
  const content = `
    <div style="padding: 8px 0;">
      <p style="font-size: 0.95rem; color: #475569; margin-bottom: 16px; line-height: 1.5;">
        Password recovery is managed according to verified account roles and security protocols.
      </p>
      <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 14px; margin-bottom: 16px;">
        <h4 style="font-size: 0.9rem; font-weight: 700; color: #0f172a; margin-bottom: 6px;">🌾 Registered Farmers</h4>
        <p style="font-size: 0.85rem; color: #64748b; margin: 0; line-height: 1.4;">
          Contact your assigned Field Extension Officer or reach out to the SeriCare Farmer Support Desk at <a href="mailto:support@sericare.in" style="color:#15803d; font-weight:600;">support@sericare.in</a> with your registered phone number.
        </p>
      </div>
      <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 14px; margin-bottom: 20px;">
        <h4 style="font-size: 0.9rem; font-weight: 700; color: #0f172a; margin-bottom: 6px;">🏢 Enterprise and Administrative Staff</h4>
        <p style="font-size: 0.85rem; color: #64748b; margin: 0; line-height: 1.4;">
          Please contact your Company Administrator or IT Security Team to verify identity and issue a password reset link.
        </p>
      </div>
      <div style="text-align: right;">
        <button type="button" class="btn btn-primary" onclick="closeAppModal()">Understood</button>
      </div>
    </div>
  `;
  openAppModal('Setu Account Access Recovery', content);
}

async function handleLogin(e) {
  e.preventDefault();
  const username = document.getElementById('username').value.trim();
  const password = document.getElementById('password').value;
  const errorEl = document.getElementById('loginError');
  const loginBtn = document.getElementById('loginBtn');

  errorEl.classList.add('hidden');
  loginBtn.disabled = true;
  loginBtn.innerHTML = '<span>Verifying credentials...</span>';

  try {
    const res = await fetch(`${API_BASE_URL}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password })
    });

    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.detail || 'Invalid username or password');
    }

    adminToken = data.access_token;
    currentSessionId = data.session_id || null;
    currentUser = data.user;

    // Persist strictly to this tab's sessionStorage
    TAB_STORAGE.setItem('setu_tab_token', adminToken);
    if (currentSessionId) TAB_STORAGE.setItem('setu_tab_session_id', currentSessionId);
    TAB_STORAGE.setItem('setu_tab_user', JSON.stringify(currentUser));
    localStorage.setItem('setu_token', adminToken);
    localStorage.setItem('setu_user', JSON.stringify(currentUser));

    // Check if redirected from landing page direct checkout
    const urlParams = new URLSearchParams(window.location.search);
    const redirectParam = urlParams.get('redirect');
    const productIdParam = urlParams.get('product_id') || sessionStorage.getItem('setu_checkout_product_id');

    if (redirectParam === 'checkout' || productIdParam) {
      showToast(`Welcome back, ${currentUser.full_name || currentUser.username}! Resuming your order...`, 'success');
      setTimeout(() => {
        window.location.href = `/#products?buy=${encodeURIComponent(productIdParam || '')}`;
      }, 400);
      return;
    }

    const defTab = (ROLE_DEFAULT_TABS && ROLE_DEFAULT_TABS[currentUser.role]) || 'overview';
    currentTab = defTab;
    TAB_STORAGE.setItem('setu_tab_nav', currentTab);
    if (currentUser.shed_id) {
      selectedShedId = currentUser.shed_id;
      TAB_STORAGE.setItem('setu_tab_shed', selectedShedId);
    }

    showToast(`Welcome back, ${currentUser.full_name || currentUser.username}!`, 'success');
    showDashboardView();
  } catch (err) {
    errorEl.innerHTML = `<i data-lucide="alert-circle" style="width: 18px; height: 18px; flex-shrink: 0;"></i><span>${err.message}</span>`;
    errorEl.classList.remove('hidden');
    if (window.lucide) lucide.createIcons();
  } finally {
    loginBtn.disabled = false;
    loginBtn.innerHTML = '<span>Sign In</span><i data-lucide="arrow-right"></i>';
    if (window.lucide) lucide.createIcons();
  }
}



// ==========================================================================
// GOOGLE OAUTH & SOCIAL AUTHENTICATION
// ==========================================================================

let GOOGLE_CLIENT_ID = '';

function parseJwt(token) {
  try {
    const base64Url = token.split('.')[1];
    const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
    const jsonPayload = decodeURIComponent(atob(base64).split('').map(function(c) {
      return '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2);
    }).join(''));
    return JSON.parse(jsonPayload);
  } catch (e) {
    return null;
  }
}

async function completeGoogleLogin(googleUserData) {
  const errorEl = document.getElementById('loginError');
  const googleBtn = document.getElementById('googleSignInBtn');

  if (googleBtn) {
    googleBtn.disabled = true;
    googleBtn.innerHTML = '<span>Connecting to Google...</span>';
  }
  if (errorEl) errorEl.classList.add('hidden');

  try {
    const res = await fetch(`${API_BASE_URL}/auth/google-sync`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        email: googleUserData.email || '',
        google_id: googleUserData.google_id || '',
        full_name: googleUserData.full_name || 'Google User',
        phone: googleUserData.phone || '',
        farm_name: googleUserData.farm_name || 'Setu Smart Farm',
        region: googleUserData.region || 'Karnataka'
      })
    });

    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.detail || 'Google authentication failed');
    }

    adminToken = data.access_token;
    currentSessionId = data.session_id || null;
    currentUser = data.user;

    // Persist strictly to this tab's sessionStorage
    TAB_STORAGE.setItem('setu_tab_token', adminToken);
    if (currentSessionId) TAB_STORAGE.setItem('setu_tab_session_id', currentSessionId);
    TAB_STORAGE.setItem('setu_tab_user', JSON.stringify(currentUser));

    const defTab = (ROLE_DEFAULT_TABS && ROLE_DEFAULT_TABS[currentUser.role]) || 'overview';
    currentTab = defTab;
    TAB_STORAGE.setItem('setu_tab_nav', currentTab);
    if (currentUser.shed_id) {
      selectedShedId = currentUser.shed_id;
      TAB_STORAGE.setItem('setu_tab_shed', selectedShedId);
    }

    closeAppModal();
    showToast(`Signed in with Google as ${currentUser.full_name || currentUser.username}!`, 'success');
    showDashboardView();
  } catch (err) {
    if (errorEl) {
      errorEl.innerHTML = `<i data-lucide="alert-circle" style="width: 18px; height: 18px; flex-shrink: 0;"></i><span>${err.message}</span>`;
      errorEl.classList.remove('hidden');
      if (window.lucide) lucide.createIcons();
    } else {
      showToast(err.message, 'error');
    }
  } finally {
    if (googleBtn) {
      googleBtn.disabled = false;
      googleBtn.innerHTML = `
        <svg class="google-icon" viewBox="0 0 24 24" width="18" height="18" xmlns="http://www.w3.org/2000/svg">
          <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4"/>
          <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
          <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z" fill="#FBBC05"/>
          <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z" fill="#EA4335"/>
        </svg>
        <span>Sign in with Google</span>
      `;
    }
  }
}

function handleGoogleCredentialResponse(response) {
  if (!response || !response.credential) return;
  const payload = parseJwt(response.credential);
  if (!payload) return;
  completeGoogleLogin({
    email: payload.email,
    full_name: payload.name || payload.given_name || 'Google User',
    google_id: payload.sub
  });
}

let googleTokenClient = null;

function initGoogleAuth() {
  if (window.google && window.google.accounts) {
    try {
      if (window.google.accounts.id && GOOGLE_CLIENT_ID) {
        google.accounts.id.initialize({
          client_id: GOOGLE_CLIENT_ID,
          callback: handleGoogleCredentialResponse,
          auto_select: false,
          cancel_on_tap_outside: true
        });
      }
      if (window.google.accounts.oauth2 && GOOGLE_CLIENT_ID) {
        googleTokenClient = google.accounts.oauth2.initTokenClient({
          client_id: GOOGLE_CLIENT_ID,
          scope: 'https://www.googleapis.com/auth/userinfo.profile https://www.googleapis.com/auth/userinfo.email openid',
          prompt: 'select_account',
          callback: async (tokenResponse) => {
            if (tokenResponse.error) {
              console.warn('Google OAuth response notice:', tokenResponse);
              if (tokenResponse.error !== 'access_denied') {
                showToast(`Google Sign-In notice: ${tokenResponse.error}`, 'info');
              }
              return;
            }
            try {
              const res = await fetch('https://www.googleapis.com/oauth2/v3/userinfo', {
                headers: { Authorization: `Bearer ${tokenResponse.access_token}` }
              });
              const profile = await res.json();
              if (profile && (profile.email || profile.sub)) {
                await completeGoogleLogin({
                  email: profile.email || '',
                  full_name: profile.name || profile.given_name || 'Google User',
                  google_id: profile.sub
                });
              }
            } catch (err) {
              showToast('Failed to fetch Google profile: ' + err.message, 'error');
            }
          }
        });
      }
    } catch (e) {
      console.warn('GIS initialization notice:', e);
    }
  }
}

function redirectToGoogleOAuth() {
  const currentOrigin = window.location.origin;
  const redirectUri = `${currentOrigin}/admin/`;
  const state = encodeURIComponent(JSON.stringify({ returnTo: '/admin/' }));
  const scope = encodeURIComponent('openid email profile');
  const nonce = Math.random().toString(36).substring(2);

  if (GOOGLE_CLIENT_ID) {
    const authUrl = `https://accounts.google.com/o/oauth2/v2/auth?` +
      `client_id=${encodeURIComponent(GOOGLE_CLIENT_ID)}` +
      `&redirect_uri=${encodeURIComponent(redirectUri)}` +
      `&response_type=token%20id_token` +
      `&scope=${scope}` +
      `&prompt=select_account` +
      `&nonce=${nonce}` +
      `&state=${state}`;

    window.location.href = authUrl;
  } else {
    window.location.href = `${API_BASE_URL}/auth/google/login?redirect_url=${encodeURIComponent(redirectUri)}`;
  }
}

function handleGoogleSignIn() {
  const errorEl = document.getElementById('loginError');
  if (errorEl) errorEl.classList.add('hidden');

  // 1. Interactive Google Identity Services OAuth 2.0 popup
  if (googleTokenClient) {
    try {
      googleTokenClient.requestAccessToken({ prompt: 'select_account' });
      return;
    } catch (e) {
      console.warn('GIS popup request failed, redirecting to OAuth:', e);
    }
  }

  if (window.google && window.google.accounts && window.google.accounts.oauth2 && GOOGLE_CLIENT_ID) {
    try {
      googleTokenClient = google.accounts.oauth2.initTokenClient({
        client_id: GOOGLE_CLIENT_ID,
        scope: 'https://www.googleapis.com/auth/userinfo.profile https://www.googleapis.com/auth/userinfo.email openid',
        prompt: 'select_account',
        callback: async (tokenResponse) => {
          if (tokenResponse.error) return;
          try {
            const res = await fetch('https://www.googleapis.com/oauth2/v3/userinfo', {
              headers: { Authorization: `Bearer ${tokenResponse.access_token}` }
            });
            const profile = await res.json();
            if (profile && (profile.email || profile.sub)) {
              await completeGoogleLogin({
                email: profile.email || '',
                full_name: profile.name || profile.given_name || 'Google User',
                google_id: profile.sub
              });
            }
          } catch (err) {
            showToast('Failed to fetch Google profile: ' + err.message, 'error');
          }
        }
      });
      googleTokenClient.requestAccessToken({ prompt: 'select_account' });
      return;
    } catch (e) {
      console.warn('Direct initTokenClient notice:', e);
    }
  }

  // 2. Direct browser redirection to Google OAuth Consent Screen
  redirectToGoogleOAuth();
}

function checkGoogleOAuthCallback() {
  const hash = window.location.hash;
  if (!hash || (!hash.includes('access_token=') && !hash.includes('id_token='))) return;

  const params = new URLSearchParams(hash.replace(/^#/, ''));
  const idToken = params.get('id_token');
  const accessToken = params.get('access_token');
  const error = params.get('error');

  window.history.replaceState(null, null, window.location.pathname);

  if (error) {
    showToast(`Google Sign-In: ${error}`, 'error');
    return;
  }

  if (idToken) {
    const payload = parseJwt(idToken);
    if (payload && (payload.email || payload.sub)) {
      completeGoogleLogin({
        email: payload.email || '',
        full_name: payload.name || payload.given_name || 'Google User',
        google_id: payload.sub
      });
      return;
    }
  }

  if (accessToken) {
    fetch('https://www.googleapis.com/oauth2/v3/userinfo', {
      headers: { Authorization: `Bearer ${accessToken}` }
    })
      .then(r => r.json())
      .then(profile => {
        if (profile && (profile.email || profile.sub)) {
          completeGoogleLogin({
            email: profile.email || '',
            full_name: profile.name || profile.given_name || 'Google User',
            google_id: profile.sub
          });
        }
      })
      .catch(err => {
        console.error('Failed to load Google profile from redirect:', err);
      });
  }
}

async function loadGoogleAuthConfig() {
  try {
    const res = await fetch(`${API_BASE_URL}/auth/google/config`);
    if (res.ok) {
      const cfg = await res.json();
      if (cfg.client_id) {
        GOOGLE_CLIENT_ID = cfg.client_id;
        initGoogleAuth();
      }
    }
  } catch (e) {
    console.warn('Google auth config retrieval notice:', e);
  }
}

window.handleGoogleSignIn = handleGoogleSignIn;

async function verifySession() {
  try {
    const res = await fetch(`${API_BASE_URL}/auth/me`, {
      headers: { 'Authorization': `Bearer ${adminToken}` }
    });
    if (!res.ok) throw new Error('Session invalid');
    const user = await res.json();
    currentUser = user;
    TAB_STORAGE.setItem('setu_tab_user', JSON.stringify(currentUser));
    showDashboardView();
  } catch (_) {
    adminToken = null;
    currentSessionId = null;
    currentUser = null;
    TAB_STORAGE.removeItem('setu_tab_token');
    TAB_STORAGE.removeItem('setu_tab_session_id');
    TAB_STORAGE.removeItem('setu_tab_user');
    showAuthView();
  }
}

async function handleLogout(msg) {
  if (telemetryEventSource) {
    try { telemetryEventSource.close(); } catch (_) {}
    telemetryEventSource = null;
  }

  const prevToken = adminToken;
  const prevSessId = currentSessionId;

  // Clear this tab's state immediately
  adminToken = null;
  currentSessionId = null;
  currentUser = null;
  TAB_STORAGE.removeItem('setu_tab_token');
  TAB_STORAGE.removeItem('setu_tab_session_id');
  TAB_STORAGE.removeItem('setu_tab_user');
  TAB_STORAGE.removeItem('setu_tab_nav');
  TAB_STORAGE.removeItem('setu_tab_shed');

  allFarmersData = [];
  farmersFilteredList = [];

  // Notify server to revoke this specific session
  if (prevToken) {
    try {
      await fetch(`${API_BASE_URL}/auth/logout`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${prevToken}`,
          'X-Session-ID': prevSessId || '',
          'X-Tab-ID': tabId
        }
      });
    } catch (_) {}
  }

  if (msg) showToast(msg, 'info');
  showAuthView();
}

function updateUserBadge() {
  if (!currentUser) return;
  const nameEl = document.getElementById('sidebarAdminName');
  const roleEl = document.getElementById('sidebarRoleText');
  const badgeEl = document.getElementById('sidebarRoleBadge');
  const menuName = document.getElementById('menuUserFullName');
  const menuRole = document.getElementById('menuUserRole');
  const switcher = document.getElementById('roleSwitcherSelect');

  const displayName = currentUser.full_name || currentUser.username || 'Administrator';
  const roleName = (currentUser.role || 'farmer');

  if (nameEl) nameEl.textContent = displayName;
  if (roleEl) roleEl.textContent = roleName.toUpperCase();
  if (badgeEl) badgeEl.textContent = `${roleName.toUpperCase()} HUB`;
  if (menuName) menuName.textContent = displayName;
  if (menuRole) menuRole.textContent = `Role: ${roleName}`;
  if (switcher) switcher.value = currentUser.role || 'superadmin';

  // Update Top Tab Session Indicator
  const tabPill = document.getElementById('topTabSessionText');
  if (tabPill && currentUser) {
    const shortTab = tabId.length > 9 ? tabId.substring(4, 9) : tabId;
    tabPill.textContent = `${roleName.toUpperCase()} (#${shortTab})`;
  }
}

function enforceRoleNavigation() {
  const role = (currentUser && currentUser.role) ? currentUser.role : 'superadmin';
  const allowedTabs = ROLE_PERMISSIONS[role] || ROLE_PERMISSIONS['farmer'];

  document.querySelectorAll('#sidebarNav .nav-item').forEach(item => {
    const tab = item.getAttribute('data-tab');
    if (allowedTabs.includes(tab)) {
      item.style.display = 'flex';
    } else {
      item.style.display = 'none';
    }
  });

  // If active tab is not allowed, switch to first allowed tab
  if (!allowedTabs.includes(currentTab)) {
    switchNavTab(allowedTabs[0] || 'overview');
  }
}

async function simulateRoleChange(newRole) {
  // Finds or switches active persona to demonstrate RBAC
  const roleAccounts = {
    superadmin: { u: 'admin', p: 'admin' },
    company_admin: { u: 'comp_admin', p: 'company2026' },
    ceo: { u: 'ceo', p: 'ceo2026' },
    hr: { u: 'hr_deepa', p: 'hr2026' },
    operations_manager: { u: 'ops_manoj', p: 'ops2026' },
    technician: { u: 'tech_kiran', p: 'tech2026' },
    sales: { u: 'sales_anand', p: 'sales2026' },
    support: { u: 'support_priya', p: 'support2026' },
    analyst: { u: 'analyst_sneha', p: 'analyst2026' },
    farmer: { u: 'ramesh_farmer', p: 'setu2026' }
  };

  const creds = roleAccounts[newRole];
  if (!creds) return;

  try {
    showToast(`Switching persona to ${newRole.toUpperCase()}...`, 'info');
    const res = await fetch(`${API_BASE_URL}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username: creds.u, password: creds.p })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail);

    adminToken = data.access_token;
    currentSessionId = data.session_id || null;
    currentUser = data.user;
    TAB_STORAGE.setItem('setu_tab_token', adminToken);
    if (currentSessionId) TAB_STORAGE.setItem('setu_tab_session_id', currentSessionId);
    TAB_STORAGE.setItem('setu_tab_user', JSON.stringify(currentUser));

    updateUserBadge();
    enforceRoleNavigation();
    
    // Auto-switch to persona's default dashboard
    const newTab = ROLE_DEFAULT_TABS[currentUser.role] || 'overview';
    switchNavTab(newTab);
    loadRoleDashboardHero();
    updateTopBarControlsVisibility();
    
    showToast(`Active persona: ${currentUser.full_name} (${currentUser.role})`, 'success');
  } catch (err) {
    showToast(`Role switch failed: ${err.message}`, 'error');
  }
}

// ==========================================================================
// 3. NAVIGATION & VIEW SWITCHER
// ==========================================================================

function switchNavTab(tabName) {
  currentTab = tabName;
  TAB_STORAGE.setItem('setu_tab_nav', tabName);
  closeSidebar();

  // Update active state in sidebar
  document.querySelectorAll('#sidebarNav .nav-item').forEach(item => {
    if (item.getAttribute('data-tab') === tabName) {
      item.classList.add('active');
    } else {
      item.classList.remove('active');
    }
  });

  // Hide all sections, show target section
  document.querySelectorAll('.view-section').forEach(sec => sec.classList.add('hidden'));
  const targetSec = document.getElementById(`section-${tabName}`);
  if (targetSec) {
    targetSec.classList.remove('hidden');
  }

  // Expand parent accordion group if collapsed
  const activeItem = document.querySelector(`#sidebarNav .nav-item[data-tab="${tabName}"]`);
  if (activeItem) {
    const parentGroup = activeItem.closest('.nav-group');
    if (parentGroup && parentGroup.classList.contains('collapsed')) {
      parentGroup.classList.remove('collapsed');
    }
  }

  // Update breadcrumb and header title
  const titleMap = {
    'overview': { title: 'System Overview & Platform Health', bread: 'Operations & Platform Overview' },
        'employees': { title: 'Employee Directory & User Administration', bread: 'Personnel & Access Control' },
    'roles': { title: 'Roles & Fine-Grained Permissions', bread: 'Role Templates & Delegation Policies' },
    'departments': { title: 'Departments & Reporting Structures', bread: 'Teams & Organizational Units' },
    'tasks': { title: 'My Work & Priority Queue', bread: 'Operations & Personal Tasks' },
    'live-monitoring': { title: 'Live Environmental Monitoring', bread: 'IoT Sensors & Hardware Telemetry' },
    'analytics': { title: 'Platform & Environmental Analytics', bread: 'Time-Series & Growth Metrics' },
    'alerts': { title: 'Alerts & Incident Management', bread: 'Threshold Violations & Interlocks' },
    'farmers': { title: 'Enrolled Farmers Directory', bread: 'Farmers & Rearing Sheds Directory' },
    'sheds': { title: 'Rearing Shed Climate Setpoints', bread: 'Growth Stages 1–5 Microclimates' },
    'devices': { title: 'IoT Hardware Nodes & Gateways', bread: 'Device Provisioning & Status' },
    'sensor-config': { title: 'Sensor Hardware Configuration', bread: 'Sensor Calibration & Pin Offsets' },
    'products': { title: 'Sericulture Equipment Catalogue', bread: 'Products, Pricing & Stock' },
    'enquiries': { title: 'Website Demo Leads & Enquiries', bread: 'Public Enquiries & Lead Qualification' },
    'orders': { title: 'Customer Sales Orders', bread: 'Commercial Order Lifecycle' },
    'billing': { title: 'Billing & Subscriptions', bread: 'Invoices & SaaS Contracts' },
    'support': { title: 'Customer Support Helpdesk', bread: 'Tickets & Escalation Desk' },
    'installations': { title: 'Field Installation Workflows', bread: 'Job Scheduling & Verification' },
    'install-team': { title: 'Certified Field Technicians', bread: 'Installation Team Roster' },
    'research': { title: 'Scientific Sericulture Research', bread: 'Environmental Anomaly Analysis' },
    'guidance': { title: 'Multilingual Rearing Advisory', bread: 'CSRTI Research Guidelines' },
    'reports': { title: 'Platform & Financial Reports', bread: 'CSV & Analytical Exports' },
    'users': { title: 'Platform User Management', bread: 'Security Roles & Permissions' },
    'audit': { title: 'Immutable Security Audit Logs', bread: 'Operations Audit Trail' },
    'integrations': { title: 'Third-Party Integrations Status', bread: 'Live Cloud & Hardware Providers' },
    'settings': { title: 'Platform Security Settings', bread: 'System Environment Policies' }
  };

  const meta = titleMap[tabName] || { title: 'Setu Command Portal', bread: tabName };
  document.getElementById('topBarTitle').textContent = meta.title;
  document.getElementById('topBarBreadcrumb').textContent = meta.bread;

  // Update contextual topbar visibility for shed & telemetry controls
  updateTopBarControlsVisibility();

  // Load authoritative data for the activated tab
  loadTabData(tabName);

  if (window.SetuTableManager) {
    setTimeout(() => SetuTableManager.observeAllTables(), 250);
  }

  if (window.lucide) lucide.createIcons();
}

function loadTabData(tabName) {
  switch (tabName) {
    case 'tasks':
      loadUserTasks();
      break;
    case 'overview':
      fetchOverviewKpis();
      loadRoleDashboardHero();
      syncLiveTelemetryStream();
      break;
        case 'employees':
      loadEmployeesList();
      break;
    case 'roles':
      loadRolesAndPermissions();
      break;
    case 'departments':
      loadDepartmentsList();
      break;
    case 'audit':
      loadAuditRecords();
      break;
    case 'live-monitoring':
      syncLiveTelemetryStream();
      break;
    case 'analytics':
      loadAnalyticsTrends(document.getElementById('analyticsRangeSelect')?.value || 7);
      break;
    case 'alerts':
      loadAlerts();
      break;
    case 'farmers':
      loadFarmers();
      break;
    case 'sheds':
      loadStageThresholds();
      break;
    case 'devices':
      loadDevices();
      break;
    case 'sensor-config':
      loadSensors();
      break;
    case 'products':
      loadProducts();
      break;
    case 'enquiries':
      loadEnquiries();
      break;
    case 'orders':
      loadOrders();
      break;
    case 'billing':
      loadBilling();
      break;
    case 'support':
      loadSupportTickets();
      break;
    case 'installations':
      loadInstallations();
      break;
    case 'install-team':
      loadInstallTeam();
      break;
    case 'guidance':
      loadGuidanceArticles(document.getElementById('guidanceLangSelect')?.value || 'en');
      break;
    case 'users':
      loadUsers();
      break;
    case 'audit':
      loadAuditLogs();
      break;
    case 'integrations':
      loadIntegrations();
      break;
  }
}

// ==========================================================================
// 4. REAL-TIME DATA STREAM & SYNC ENGINE
// ==========================================================================

function initRealtimeDataStream() {
  if (telemetryEventSource) {
    telemetryEventSource.close();
    telemetryEventSource = null;
  }

  const role = currentUser?.role || 'farmer';
  const perms = currentUser?.permissions || [];
  const needsShedTelemetry = SHED_TELEMETRY_ROLES.includes(role) ||
    perms.includes('sheds:read') ||
    perms.includes('iot:read') ||
    perms.includes('iot:telemetry');
  const isNonShedRole = ['hr', 'sales', 'support', 'ceo'].includes(role) && !perms.includes('sheds:write');

  if (!needsShedTelemetry || isNonShedRole || !selectedShedId) {
    return;
  }

  // Connect to SSE stream
  try {
    const sseUrl = `${API_BASE_URL}/telemetry/live-stream/${selectedShedId}?token=${adminToken}`;
    telemetryEventSource = new EventSource(sseUrl);

    telemetryEventSource.onopen = () => {
      lastSyncTimestamp = new Date();
      setHealthPill(true);
    };

    telemetryEventSource.addEventListener('initial', (e) => {
      try {
        const data = JSON.parse(e.data);
        updateLiveDashboardMetrics(data);
        setHealthPill(true);
      } catch (_) {}
    });

    telemetryEventSource.addEventListener('ping', () => {
      lastSyncTimestamp = new Date();
      setHealthPill(true);
    });

    telemetryEventSource.onerror = () => {
      // Fallback: poll overview to keep telemetry alive if SSE disconnected
      syncLiveTelemetryStream();
    };
  } catch (_) {
    syncLiveTelemetryStream();
  }
}

function setHealthPill(isHealthy) {
  const pill = document.getElementById('topHealthPill');
  const text = document.getElementById('topHealthText');
  if (!pill || !text) return;
  if (isHealthy) {
    pill.style.background = 'var(--green-tint)';
    pill.style.color = 'var(--green-pill-text)';
    pill.style.border = '1px solid rgba(16, 185, 129, 0.3)';
    text.textContent = 'SYSTEM OPERATIONAL';
  } else {
    // If the logged-in user is a farmer without hardware connected yet
    if (currentUser && currentUser.role === 'farmer') {
      pill.style.background = '#FEF3C7';
      pill.style.color = '#92400E';
      pill.style.border = '1px solid #FDE68A';
      text.textContent = 'AWAITING SENSORS';
    } else {
      pill.style.background = '#FDECEA';
      pill.style.color = '#BD3429';
      pill.style.border = '1px solid #FCA5A5';
      text.textContent = 'TELEMETRY DEGRADED';
    }
  }
}

async function syncAllRealtimeData() {
  const syncIcon = document.getElementById('syncIcon');
  if (syncIcon) syncIcon.style.animation = 'spin 1s linear infinite';
  
  showToast('Refreshing authoritative data...', 'info');
  await Promise.all([
    fetchOverviewKpis(),
    syncLiveTelemetryStream(),
    loadTabData(currentTab)
  ]);

  lastSyncTimestamp = new Date();
  if (syncIcon) syncIcon.style.animation = '';
  showToast('Platform metrics synchronized with PostgreSQL.', 'success');
}

async function loadShedsList() {
  const role = currentUser?.role || 'farmer';
  const isNonShedRole = ['hr', 'sales', 'support', 'ceo'].includes(role) && !currentUser?.permissions?.includes('sheds:write');
  if (isNonShedRole) return;

  try {
    const res = await fetch(`${API_BASE_URL}/admin/sheds`, {
      headers: { 'Authorization': `Bearer ${adminToken}` }
    });
    if (!res.ok) return;
    let sheds = await res.json();

    // Resource-level scoping: restrict to assigned sheds if ASSIGNED_ONLY or if farmer
    if (currentUser && currentUser.role === 'farmer') {
      const myShedId = currentUser.shed_id;
      if (myShedId) {
        const myOnly = sheds.filter(s => s.shed_id === myShedId);
        if (myOnly.length) sheds = myOnly;
      }
    } else if (currentUser && currentUser.access_scope === 'ASSIGNED_ONLY' && currentUser.assigned_resources?.sheds?.length) {
      const allowed = currentUser.assigned_resources.sheds;
      sheds = sheds.filter(s => allowed.includes(s.shed_id));
    }

    availableSheds = sheds;
    const select = document.getElementById('shedSelect');
    if (!select) return;

    select.innerHTML = '';
    if (availableSheds.length === 0) {
      const opt = document.createElement('option');
      opt.value = '';
      opt.textContent = 'No sheds assigned';
      select.appendChild(opt);
      return;
    }

    availableSheds.forEach(s => {
      const opt = document.createElement('option');
      opt.value = s.shed_id;
      opt.textContent = `${s.display_name} (${s.region})`;
      if (s.shed_id === selectedShedId) opt.selected = true;
      select.appendChild(opt);
    });

    if (!availableSheds.some(s => s.shed_id === selectedShedId) && availableSheds.length > 0) {
      selectedShedId = availableSheds[0].shed_id;
      select.value = selectedShedId;
    }

    // If farmer has only 1 shed, clean up selector appearance
    if (availableSheds.length === 1 && currentUser?.role === 'farmer') {
      select.style.cursor = 'default';
      select.title = 'Active enrolled rearing shed';
    }
  } catch (err) {
    console.error('Failed to load sheds list:', err);
  }
}

function handleShedChange(val) {
  selectedShedId = val;
  showToast(`Switched active monitoring shed to ${val}`, 'info');
  initRealtimeDataStream();
  syncLiveTelemetryStream();
}

// ==========================================================================
// 5. MODULE 1 & OVERVIEW: REAL KPIS & GAUGES
// ==========================================================================

async function fetchOverviewKpis() {
  try {
    const res = await fetch(`${API_BASE_URL}/dashboard/overview`, {
      headers: { 'Authorization': `Bearer ${adminToken}` }
    });
    if (!res.ok) return;
    const kpis = await res.json();

    document.getElementById('kpiTotalFarmers').textContent = kpis.total_farmers;
    document.getElementById('kpiActiveFarmers').textContent = `Active: ${kpis.active_farmers}`;
    document.getElementById('kpiTotalSheds').textContent = kpis.total_sheds;
    document.getElementById('kpiOnlineDevices').textContent = kpis.online_devices;
    document.getElementById('kpiOfflineDevices').textContent = `Offline: ${kpis.offline_devices}`;
    document.getElementById('kpiActiveSubs').textContent = kpis.active_subscriptions;
    document.getElementById('kpiMrr').textContent = `MRR: ₹${kpis.mrr_inr.toLocaleString()}`;
    document.getElementById('kpiPendingOrders').textContent = kpis.pending_orders;
    document.getElementById('kpiTotalRevenue').textContent = `Total Rev: ₹${kpis.total_revenue_inr.toLocaleString()}`;
    document.getElementById('kpiOpenTickets').textContent = kpis.open_tickets;
    document.getElementById('kpiCriticalTickets').textContent = `Critical: ${kpis.critical_tickets}`;
    document.getElementById('kpiActiveAlerts').textContent = kpis.active_alerts;
    document.getElementById('kpiPendingInstalls').textContent = kpis.pending_installations;

    // Badge counts in sidebar
    const alertCountEl = document.getElementById('navAlertCount');
    if (alertCountEl) alertCountEl.textContent = kpis.active_alerts;
    const orderCountEl = document.getElementById('navOrderCount');
    if (orderCountEl) orderCountEl.textContent = kpis.pending_orders;
    const ticketCountEl = document.getElementById('navTicketCount');
    if (ticketCountEl) ticketCountEl.textContent = kpis.open_tickets;
    const notifBadgeEl = document.getElementById('notifBadgeCount');
    if (notifBadgeEl) notifBadgeEl.textContent = kpis.critical_alerts;

    // Populate Operational Priority Panel ("Needs Attention")
    const priorityList = document.getElementById('priorityItemsList');
    const priorityBadge = document.getElementById('priorityCountBadge');
    if (priorityList) {
      const items = [];

      if (kpis.critical_alerts > 0) {
        items.push({
          badge: 'badge-danger',
          label: 'CRITICAL',
          entity: 'Microclimate Interlock Breach',
          desc: `${kpis.critical_alerts} critical alert(s) detected across rearing sheds.`,
          action: "switchNavTab('alerts');",
          btnText: 'Acknowledge Alert'
        });
      }

      if (kpis.offline_devices > 0) {
        items.push({
          badge: 'badge-warning',
          label: 'WARNING',
          entity: 'IoT Hardware Disconnected',
          desc: `${kpis.offline_devices} node(s) have ceased telemetry reporting >300s.`,
          action: "switchNavTab('devices');",
          btnText: 'Inspect Devices'
        });
      }

      if (kpis.critical_tickets > 0) {
        items.push({
          badge: 'badge-danger',
          label: 'HIGH',
          entity: 'Customer Escalation',
          desc: `${kpis.critical_tickets} critical farmer support ticket(s) awaiting triage.`,
          action: "switchNavTab('support');",
          btnText: 'Open Helpdesk'
        });
      }

      if (kpis.pending_installations > 0) {
        items.push({
          badge: 'badge-info',
          label: 'FIELD',
          entity: 'Field Installation Workflows',
          desc: `${kpis.pending_installations} scheduled installation job(s) pending technician verification.`,
          action: "switchNavTab('installations');",
          btnText: 'View Jobs'
        });
      }

      if (items.length > 0) {
        if (priorityBadge) priorityBadge.textContent = `${items.length} Action Items`;
        priorityList.innerHTML = items.map(it => `
          <div class="priority-item-card">
            <div class="priority-item-left">
              <span class="badge ${it.badge}">${it.label}</span>
              <div class="priority-item-info">
                <span class="priority-item-entity">${it.entity}</span>
                <span class="priority-item-desc">${it.desc}</span>
              </div>
            </div>
            <button class="btn btn-skin btn-sm" onclick="${it.action}">
              ${it.btnText}
            </button>
          </div>
        `).join('');
      } else {
        if (priorityBadge) priorityBadge.textContent = '0 Pending';
        priorityList.innerHTML = `
          <div class="priority-empty-card">
            <div class="priority-empty-icon">
              <i data-lucide="check"></i>
            </div>
            <div class="priority-empty-info">
              <h4>All Operational Systems Nominal</h4>
              <p>No critical microclimate breaches, hardware dropouts, or overdue installations requiring supervisory action.</p>
            </div>
          </div>
        `;
      }
      if (window.lucide) lucide.createIcons();
    }

    lastSyncTimestamp = new Date(kpis.last_synced_at || Date.now());
  } catch (err) {
    console.error('Failed to fetch overview KPIs:', err);
  }
}

async function syncLiveTelemetryStream() {
  try {
    const res = await fetch(`${API_BASE_URL}/sheds/${selectedShedId}/overview`, {
      headers: { 'Authorization': `Bearer ${adminToken}` }
    });
    if (!res.ok) {
      setHealthPill(false);
      return;
    }
    const overview = await res.json();
    updateLiveDashboardMetrics(overview);
    setHealthPill(true);
  } catch (err) {
    console.error('Failed to sync live telemetry:', err);
    setHealthPill(false);
  }
}

function updateLiveDashboardMetrics(overview) {
  if (!overview) return;

  // Overview microclimate cards
  const tempEl = document.getElementById('overviewIndoorTemp');
  const humEl = document.getElementById('overviewIndoorHum');
  const aqEl = document.getElementById('overviewIndoorAq');
  const luxEl = document.getElementById('overviewIndoorLux');

  if (tempEl) tempEl.textContent = `${overview.indoor_temp.toFixed(1)}°C`;
  if (humEl) humEl.textContent = `${overview.indoor_humidity.toFixed(1)}%`;
  if (aqEl) aqEl.textContent = `${overview.indoor_air_quality.toFixed(1)}%`;
  if (luxEl) luxEl.textContent = `${overview.indoor_light_lux.toFixed(0)} Lux`;

  // Live Gauges section
  const gTemp = document.getElementById('liveGaugeTemp');
  const gHum = document.getElementById('liveGaugeHum');
  const gAq = document.getElementById('liveGaugeAq');
  const gLux = document.getElementById('liveGaugeLux');

  if (gTemp) gTemp.textContent = overview.indoor_temp.toFixed(1);
  if (gHum) gHum.textContent = overview.indoor_humidity.toFixed(1);
  if (gAq) gAq.textContent = overview.indoor_air_quality.toFixed(1);
  if (gLux) gLux.textContent = overview.indoor_light_lux.toFixed(0);

  // Actuator items
  const coolerEl = document.getElementById('overviewActCooler');
  const heaterEl = document.getElementById('overviewActHeater');
  const fanEl = document.getElementById('overviewActFan');
  const pwmEl = document.getElementById('overviewPwmText');
  const pwmSlider = document.getElementById('pwmSlider');
  const pwmDisplay = document.getElementById('pwmValueDisplay');

  if (overview.actuators) {
    updateActuatorPill(coolerEl, overview.actuators.cooler, 'COOLING', 'STANDBY');
    updateActuatorPill(heaterEl, overview.actuators.heater, 'HEATING', 'STANDBY');
    updateActuatorPill(fanEl, overview.actuators.fan, 'VENTING', 'STANDBY');
    if (pwmEl) pwmEl.textContent = `${overview.actuators.light_brightness}% PWM`;
    if (pwmSlider) pwmSlider.value = overview.actuators.light_brightness;
    if (pwmDisplay) pwmDisplay.textContent = `${overview.actuators.light_brightness}%`;
  }

  lastSyncTimestamp = new Date();
  setHealthPill(true);
}

function updateActuatorPill(el, isOn, onText, offText) {
  if (!el) return;
  const stateEl = el.querySelector('.act-state');
  if (isOn) {
    el.classList.add('on');
    if (stateEl) stateEl.textContent = onText;
  } else {
    el.classList.remove('on');
    if (stateEl) stateEl.textContent = offText;
  }
}

function triggerActuatorCommand(actuatorName) {
  const actuatorLabels = {
    cooler: 'Evaporative Cooling Pad & Pump',
    heater: 'Electric Heating Element Coil',
    fan: 'Exhaust Ventilation Fan'
  };

  const label = actuatorLabels[actuatorName] || actuatorName;

  openAppModal(
    'Hardware Safety Interlock Confirmation',
    `
      <div style="display: flex; flex-direction: column; gap: 14px;">
        <div style="display: flex; align-items: center; gap: 10px; color: var(--status-warning);">
          <i data-lucide="shield-alert" style="width: 24px; height: 24px;"></i>
          <h4 style="font-size: 0.95rem; font-weight: 800; color: var(--text-main);">Manual Actuator Override Request</h4>
        </div>
        <p style="font-size: 0.84rem; color: var(--text-secondary); line-height: 1.5;">
          You are requesting manual override for <strong>${label}</strong> on rearing shed <strong>${selectedShedId}</strong>.
        </p>
        <div style="background: var(--status-warning-bg); border: 1px solid var(--status-warning-border); padding: 12px; border-radius: var(--radius-md); font-size: 0.78rem; color: var(--status-warning-text); line-height: 1.45;">
          <strong>Hardware Safety Interlock Active:</strong> Heating and Cooling elements are physically mutually-exclusive in firmware. Manual override will temporarily suspend the autonomous microclimate PID control loop.
        </div>
        <div style="display: flex; justify-content: flex-end; align-items: center; margin-top: 16px; gap: 10px;">
          <button class="btn btn-skin btn-sm" onclick="closeAppModal()">Cancel</button>
          <button class="btn btn-primary btn-sm" id="btnConfirmDeleteAction" onclick="executeActuatorOverride('${actuatorName}')">
            Authorize & Dispatch Override
          </button>
        </div>
      </div>
    `
  );
}

async function executeActuatorOverride(actuatorName) {
  closeAppModal();
  showToast(`Dispatching hardware command for ${actuatorName}...`, 'info');
  try {
    const res = await fetch(`${API_BASE_URL}/control/${selectedShedId}/override`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${adminToken}`
      },
      body: JSON.stringify({ actuator: actuatorName, state: true })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Hardware command rejected');
    showToast(`Command acknowledged by ESP32 node. State applied.`, 'success');
    syncLiveTelemetryStream();
  } catch (err) {
    showToast(`Actuator dispatch failed: ${err.message}`, 'error');
  }
}

async function handlePwmChange(val) {
  document.getElementById('pwmValueDisplay').textContent = `${val}%`;
  try {
    await fetch(`${API_BASE_URL}/control/${selectedShedId}/override`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${adminToken}`
      },
      body: JSON.stringify({ actuator: 'light_brightness', state: val > 0, value: parseInt(val, 10) })
    });
    showToast(`Circadian PWM dimmer updated to ${val}%`, 'success');
    syncLiveTelemetryStream();
  } catch (err) {
    showToast('Failed to apply PWM level', 'error');
  }
}

// ==========================================================================
// 6. MODULE 1: ANALYTICS & TIME-SERIES CHARTS
// ==========================================================================

async function loadAnalyticsTrends(days) {
  try {
    const res = await fetch(`${API_BASE_URL}/analytics/trends?days=${days}`, {
      headers: { 'Authorization': `Bearer ${adminToken}` }
    });
    if (!res.ok) return;
    const data = await res.json();

    renderTempHumChart(data.telemetry_trends || []);
    renderOrdersRevChart(data.order_trends || []);
    renderRegionalChart(data.regional_distribution || []);
    renderFarmerGrowthChart(data.farmer_growth || []);
  } catch (err) {
    console.error('Failed to load analytics trends:', err);
  }
}

function renderTempHumChart(trends) {
  const ctx = document.getElementById('chartTempHum');
  if (!ctx) return;
  if (chartTempHum) chartTempHum.destroy();

  const labels = trends.map(t => new Date(t.day).toLocaleDateString(undefined, { month: 'short', day: 'numeric' }));
  const temps = trends.map(t => t.avg_temp);
  const hums = trends.map(t => t.avg_humidity);

  chartTempHum = new Chart(ctx, {
    type: 'line',
    data: {
      labels: labels.length ? labels : ['Day 1', 'Day 2', 'Day 3', 'Day 4', 'Day 5'],
      datasets: [
        {
          label: 'Avg Temperature (°C)',
          data: temps.length ? temps : [26.5, 27.0, 26.8, 27.2, 26.9],
          borderColor: '#10B981',
          backgroundColor: 'rgba(16, 185, 129, 0.1)',
          tension: 0.3,
          fill: true
        },
        {
          label: 'Avg Humidity (%)',
          data: hums.length ? hums : [78, 80, 77, 82, 79],
          borderColor: '#3B82F6',
          backgroundColor: 'rgba(59, 130, 246, 0.05)',
          tension: 0.3,
          yAxisID: 'y1'
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        y: { title: { display: true, text: 'Temp (°C)' }, min: 15, max: 35 },
        y1: { position: 'right', title: { display: true, text: 'RH (%)' }, min: 40, max: 100 }
      }
    }
  });
}

function renderOrdersRevChart(trends) {
  const ctx = document.getElementById('chartOrdersRev');
  if (!ctx) return;
  if (chartOrdersRev) chartOrdersRev.destroy();

  const labels = trends.map(t => new Date(t.day).toLocaleDateString(undefined, { month: 'short', day: 'numeric' }));
  const revs = trends.map(t => t.daily_revenue);

  chartOrdersRev = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: labels.length ? labels : ['Day 1', 'Day 2', 'Day 3', 'Day 4', 'Day 5'],
      datasets: [{
        label: 'Revenue (₹)',
        data: revs.length ? revs : [17298, 8500, 12400, 6500, 9990],
        backgroundColor: '#1C4D37',
        borderRadius: 4
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        y: { title: { display: true, text: 'Revenue in INR (₹)' }, beginAtZero: true }
      }
    }
  });
}

function renderRegionalChart(dist) {
  const ctx = document.getElementById('chartRegional');
  if (!ctx) return;
  if (chartRegional) chartRegional.destroy();

  const labels = dist.map(d => d.region || 'Unknown');
  const counts = dist.map(d => parseInt(d.count, 10));

  chartRegional = new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels: labels.length ? labels : ['Mysuru', 'Kolar', 'Chikkaballapura', 'Ramanagara', 'Bengaluru'],
      datasets: [{
        data: counts.length ? counts : [35, 28, 22, 14, 8],
        backgroundColor: ['#133323', '#1C4D37', '#2A6A4A', '#4E9571', '#70B591']
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false
    }
  });
}

function renderFarmerGrowthChart(growth) {
  const ctx = document.getElementById('chartFarmerGrowth');
  if (!ctx) return;
  if (chartFarmerGrowth) chartFarmerGrowth.destroy();

  const labels = growth.map(g => new Date(g.day).toLocaleDateString(undefined, { month: 'short', day: 'numeric' }));
  const counts = growth.map(g => g.new_farmers);

  chartFarmerGrowth = new Chart(ctx, {
    type: 'line',
    data: {
      labels: labels.length ? labels : ['W1', 'W2', 'W3', 'W4'],
      datasets: [{
        label: 'New Farmers Enrolled',
        data: counts.length ? counts : [12, 18, 24, 32],
        borderColor: '#B46C12',
        backgroundColor: 'rgba(180, 108, 18, 0.1)',
        fill: true,
        tension: 0.3
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        y: { beginAtZero: true }
      }
    }
  });
}

// ==========================================================================
// 7. MODULE 9: FARMER MANAGEMENT
// ==========================================================================

async function loadFarmers() {
  const tbody = document.getElementById('farmersTableBody');
  if (!tbody) return;
  tbody.innerHTML = '<tr><td colspan="9" style="text-align: center; padding: 24px;">Loading farmers from database...</td></tr>';

  try {
    const res = await fetch(`${API_BASE_URL}/admin/farmers`, {
      headers: { 'Authorization': `Bearer ${adminToken}` }
    });
    if (!res.ok) throw new Error('Failed to load farmers');
    allFarmersData = await res.json();
    document.getElementById('farmersBadgeCount').textContent = `${allFarmersData.length} Enrolled`;
    const navFarmerEl = document.getElementById('navFarmerCount'); if (navFarmerEl) navFarmerEl.textContent = allFarmersData.length;

    // Populate region select
    const regSelect = document.getElementById('farmersRegionSelect');
    if (regSelect) {
      const regions = [...new Set(allFarmersData.map(f => f.region).filter(Boolean))];
      regSelect.innerHTML = '<option value="">All Regions</option>';
      regions.forEach(r => {
        const opt = document.createElement('option');
        opt.value = r;
        opt.textContent = r;
        regSelect.appendChild(opt);
      });
    }

    renderFarmersTable(allFarmersData);
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="9" style="text-align: center; color: var(--rose); padding: 24px;">Error: ${err.message}</td></tr>`;
  }
}

function renderFarmersTable(farmers) {
  if (farmers) {
    farmersFilteredList = farmers;
  } else {
    farmersFilteredList = allFarmersData;
  }
  farmersCurrentPage = 1;
  renderFarmersPage();
}

function renderFarmersPage() {
  const tbody = document.getElementById('farmersTableBody');
  if (!tbody) return;

  const total = farmersFilteredList.length;
  if (total === 0) {
    tbody.innerHTML = `<tr><td colspan="10">
      <div class="honest-empty-state">
        <i data-lucide="users"></i>
        <h4>No Farmers Found</h4>
        <p>No registered farmer matches your query criteria.</p>
      </div>
    </td></tr>`;
    if (window.SetuTableManager) SetuTableManager.syncTable('farmersTable');
    if (window.lucide) lucide.createIcons();
    return;
  }

  tbody.innerHTML = farmersFilteredList.map(f => `
    <tr data-id="${f.id}">
      <td class="td-bulk-select" style="text-align: center;">
        <input type="checkbox" class="row-select-checkbox" data-row-id="${f.id}" aria-label="Select Farmer" onchange="SetuTableManager.handleRowCheck('farmersTable', '${f.id}', this)">
      </td>
      <td style="font-weight: 700;">${f.full_name || f.username}</td>
      <td style="font-family: var(--font-mono); font-size: 0.78rem;">${f.phone || '--'}</td>
      <td>${f.farm_name || 'Rearing Shed'}</td>
      <td>${f.region || 'Karnataka'}</td>
      <td>${f.dfl_capacity || '200 DFL'}</td>
      <td style="font-size: 0.76rem;">${f.breed || 'Double Hybrid'}</td>
      <td><span class="badge badge-info">Instar ${f.current_stage || 3}</span></td>
      <td><span class="badge ${f.is_active ? 'badge-success' : 'badge-danger'}">${f.is_active ? 'ACTIVE' : 'SUSPENDED'}</span></td>
      <td>
        <div class="row-action-dropdown">
          <button type="button" class="action-dots-trigger" onclick="toggleRowActionMenu(event, 'farmer-${f.id}')" title="Actions" aria-label="Farmer Actions">
            <i data-lucide="more-vertical"></i>
          </button>
          <div class="row-action-menu hidden" id="row-action-menu-farmer-${f.id}">
            <button type="button" class="row-action-item" onclick="openFarmerDrawer('${f.id}'); closeAllRowActionMenus();">
              <i data-lucide="eye"></i> <span>View Full Profile</span>
            </button>
            <button type="button" class="row-action-item" onclick="openEditFarmerModal('${f.id}'); closeAllRowActionMenus();">
              <i data-lucide="edit-3"></i> <span>Edit Farmer & Shed</span>
            </button>
            <button type="button" class="row-action-item" onclick="toggleFarmerStatus('${f.id}', ${f.is_active !== false}); closeAllRowActionMenus();">
              <i data-lucide="${f.is_active !== false ? 'pause-circle' : 'play-circle'}"></i> <span>${f.is_active !== false ? 'Suspend Account' : 'Activate Account'}</span>
            </button>
            <div class="row-action-divider"></div>
            <button type="button" class="row-action-item danger-item" onclick="confirmDeleteFarmer('${f.id}'); closeAllRowActionMenus();">
              <i data-lucide="trash-2"></i> <span>Delete Farmer</span>
            </button>
          </div>
        </div>
      </td>
    </tr>
  `).join('');

  if (window.SetuTableManager) SetuTableManager.syncTable('farmersTable');
  if (window.lucide) lucide.createIcons();
}

function gotoFarmersPage(page) {
  if (window.SetuTableManager) SetuTableManager.gotoPage('farmersTable', page);
}


async function toggleFarmerStatus(farmerId, currentActive) {
  const newActive = !currentActive;
  const actionText = newActive ? 'Activate' : 'Suspend';
  showConfirmActionModal({
    title: `${actionText} Farmer Account`,
    subtitle: newActive ? 'Restoring farmer platform access' : 'Revoking farmer platform access',
    message: `Are you sure you want to ${actionText.toLowerCase()} this farmer's account?`,
    confirmText: `${actionText} Farmer`,
    confirmDanger: !newActive,
    onConfirm: async () => {
      try {
        const res = await fetch(`${API_BASE_URL}/admin/farmers/${farmerId}/status`, {
          method: 'PATCH',
          headers: {
            'Authorization': `Bearer ${adminToken}`,
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({ is_active: newActive })
        });
        if (!res.ok) {
          const errData = await res.json().catch(() => ({}));
          throw new Error(errData.detail || 'Failed to update farmer status');
        }
        showToast(`Farmer account ${newActive ? 'activated' : 'suspended'} successfully`, 'success');
        await loadFarmers();
      } catch (err) {
        showToast(err.message, 'error');
      }
    }
  });
}

async function confirmDeleteFarmer(farmerId) {
  showConfirmActionModal({
    title: 'Delete Farmer Record',
    subtitle: 'Permanent deletion from database',
    message: 'Are you sure you want to permanently delete this farmer and all associated shed associations? This cannot be undone.',
    confirmText: 'Permanently Delete Farmer',
    confirmDanger: true,
    onConfirm: async () => {
      try {
        const res = await fetch(`${API_BASE_URL}/admin/farmers/${farmerId}`, {
          method: 'DELETE',
          headers: { 'Authorization': `Bearer ${adminToken}` }
        });
        if (!res.ok) {
          const errData = await res.json().catch(() => ({}));
          throw new Error(errData.detail || 'Failed to delete farmer');
        }
        showToast('Farmer deleted successfully', 'success');
        await loadFarmers();
      } catch (err) {
        showToast(err.message, 'error');
      }
    }
  });
}

function changeFarmersPageSize(newSize) {
  if (window.SetuTableManager) SetuTableManager.changePageSize('farmersTable', newSize);
}

function filterFarmersTable(query) {
  const q = (query || '').toLowerCase().trim();
  if (!q) {
    farmersFilteredList = allFarmersData;
  } else {
    farmersFilteredList = allFarmersData.filter(f => 
      (f.full_name && f.full_name.toLowerCase().includes(q)) ||
      (f.username && f.username.toLowerCase().includes(q)) ||
      (f.phone && f.phone.includes(q)) ||
      (f.farm_name && f.farm_name.toLowerCase().includes(q))
    );
  }
  if (window.SetuTableManager) {
    const s = SetuTableManager.getState('farmersTable');
    s.currentPage = 1;
  }
  renderFarmersPage();
}

function filterFarmersRegion(reg) {
  if (reg) {
    farmersFilteredList = allFarmersData.filter(f => f.region === reg);
  } else {
    farmersFilteredList = allFarmersData;
  }
  if (window.SetuTableManager) {
    const s = SetuTableManager.getState('farmersTable');
    s.currentPage = 1;
  }
  renderFarmersPage();
}

function exportFarmersCsv() {
  if (!allFarmersData.length) {
    showToast('No farmer data to export', 'error');
    return;
  }
  const headers = ['ID', 'Username', 'Full Name', 'Phone', 'Farm Name', 'Region', 'DFL', 'Breed', 'Stage'];
  const rows = allFarmersData.map(f => [
    f.id, f.username, `"${f.full_name}"`, f.phone, `"${f.farm_name}"`, `"${f.region}"`, `"${f.dfl_capacity}"`, `"${f.breed}"`, f.current_stage
  ]);
  const csvContent = 'data:text/csv;charset=utf-8,' + [headers.join(','), ...rows.map(e => e.join(','))].join('\n');
  const encodedUri = encodeURI(csvContent);
  const link = document.createElement('a');
  link.setAttribute('href', encodedUri);
  link.setAttribute('download', `setu_farmers_${Date.now()}.csv`);
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
}

function exportOrdersCsv() {
  window.open(`${API_BASE_URL}/orders`, '_blank');
}

function exportAnalyticsReport(format) {
  showToast(`Generating ${format.toUpperCase()} export report...`, 'info');
  window.open(`${API_BASE_URL}/analytics/trends?days=30`, '_blank');
}

// ==========================================================================
// 16. UI HELPERS: DRAWER, MODALS, TOASTS, SEARCH & THEMES
// ==========================================================================

function openAppDrawer(title, htmlContent) {
  document.getElementById('drawerTitle').innerHTML = title;
  document.getElementById('drawerBody').innerHTML = htmlContent;
  document.getElementById('drawerBackdrop').classList.add('open');
  document.getElementById('appDrawer').classList.add('open');
  if (window.lucide) lucide.createIcons();
}

function closeAppDrawer() {
  document.getElementById('drawerBackdrop').classList.remove('open');
  document.getElementById('appDrawer').classList.remove('open');
}

function openAppModal(title, htmlContent, size = '') {
  document.getElementById('modalTitle').textContent = title;
  document.getElementById('modalBody').innerHTML = htmlContent;
  const card = document.querySelector('#appModalBackdrop .modal-card');
  if (card) {
    card.classList.remove('modal-lg', 'modal-xl');
    if (size) card.classList.add(`modal-${size}`);
  }
  const defaultFooter = document.getElementById('modalFooter');
  if (defaultFooter) {
    // If the modal body content provides its own buttons or form, hide the default footer to prevent duplicate Cancel buttons
    if (
      htmlContent.includes('<form') || 
      htmlContent.includes('type="submit"') ||
      htmlContent.includes('closeAppModal()') ||
      htmlContent.includes('btn-danger') ||
      htmlContent.includes('btn-primary') ||
      htmlContent.includes('btn-skin')
    ) {
      defaultFooter.classList.add('hidden');
    } else {
      defaultFooter.classList.remove('hidden');
    }
  }
  document.getElementById('appModalBackdrop').classList.remove('hidden');
  if (window.lucide) lucide.createIcons();

  // Setup smart keyboard navigation & focus for modal
  setupModalKeyboardFocus();
}

function closeAppModal() {
  document.getElementById('appModalBackdrop').classList.add('hidden');
  const card = document.querySelector('#appModalBackdrop .modal-card');
  if (card) {
    card.classList.remove('modal-lg', 'modal-xl');
    card.querySelectorAll('.btn-keyboard-selected').forEach(b => b.classList.remove('btn-keyboard-selected'));
  }
  const defaultFooter = document.getElementById('modalFooter');
  if (defaultFooter) defaultFooter.classList.remove('hidden');
}

function setupModalKeyboardFocus() {
  setTimeout(() => {
    const modalBackdrop = document.getElementById('appModalBackdrop');
    if (!modalBackdrop || modalBackdrop.classList.contains('hidden')) return;

    const card = modalBackdrop.querySelector('.modal-card');
    if (!card) return;

    card.querySelectorAll('.btn-keyboard-selected').forEach(b => b.classList.remove('btn-keyboard-selected'));

    const firstInput = card.querySelector('.modal-body input:not([type="hidden"]):not([disabled]), .modal-body select:not([disabled]), .modal-body textarea:not([disabled])');
    const dangerBtn = card.querySelector('.modal-body .btn-danger:not([disabled])') || card.querySelector('#btnConfirmDeleteAction');
    const primaryBtn = card.querySelector('.modal-body .btn-primary:not([disabled]), .modal-body button[type="submit"]:not([disabled])');
    const anyBtn = card.querySelector('.modal-body button:not([disabled]):not(.drawer-close-btn), .modal-footer:not(.hidden) button:not([disabled])');

    // Priority for initial focus:
    // Form modal with editable inputs -> focus first input
    // Delete/danger modal without text inputs -> focus the delete/confirm button so pressing Enter immediately deletes!
    if (firstInput) {
      firstInput.focus();
    } else if (dangerBtn) {
      dangerBtn.focus();
      dangerBtn.classList.add('btn-keyboard-selected');
    } else if (primaryBtn) {
      primaryBtn.focus();
      primaryBtn.classList.add('btn-keyboard-selected');
    } else if (anyBtn) {
      anyBtn.focus();
      anyBtn.classList.add('btn-keyboard-selected');
    }
  }, 40);
}

function handleModalKeyboardNavigation(e, modalCard) {
  // Collect all visible action buttons inside the modal card
  const visibleButtons = Array.from(modalCard.querySelectorAll(
    '.modal-body button:not([disabled]):not(.drawer-close-btn), .modal-footer:not(.hidden) button:not([disabled])'
  )).filter(b => b.offsetParent !== null);

  const activeEl = document.activeElement;
  const isTypingInField = activeEl && (
    (activeEl.tagName === 'INPUT' && !['checkbox', 'radio', 'button', 'submit'].includes(activeEl.type)) ||
    activeEl.tagName === 'TEXTAREA'
  );

  // 1. SIDE BUTTON NAVIGATION: ArrowLeft, ArrowRight, ArrowUp, ArrowDown
  // Allows user to switch between options (e.g. Cancel vs Permanently Delete)
  if (['ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown'].includes(e.key)) {
    if (isTypingInField && (e.key === 'ArrowLeft' || e.key === 'ArrowRight')) {
      return;
    }

    if (visibleButtons.length > 0) {
      e.preventDefault();
      let currentIndex = visibleButtons.findIndex(b => b === activeEl || b.classList.contains('btn-keyboard-selected'));

      let nextIndex = 0;
      if (e.key === 'ArrowRight' || e.key === 'ArrowDown') {
        nextIndex = currentIndex >= 0 ? (currentIndex + 1) % visibleButtons.length : 0;
      } else if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') {
        nextIndex = currentIndex >= 0 ? (currentIndex - 1 + visibleButtons.length) % visibleButtons.length : visibleButtons.length - 1;
      }

      visibleButtons.forEach(b => b.classList.remove('btn-keyboard-selected'));
      const targetBtn = visibleButtons[nextIndex];
      targetBtn.classList.add('btn-keyboard-selected');
      targetBtn.focus();
      return;
    }
  }

  // 2. ENTER BUTTON: Execute the selected option or primary action
  if (e.key === 'Enter') {
    if (activeEl && activeEl.tagName === 'TEXTAREA') {
      return;
    }

    const form = modalCard.querySelector('form');
    if (isTypingInField && form) {
      return;
    }

    e.preventDefault();

    const selectedBtn = modalCard.querySelector('.btn-keyboard-selected') || (activeEl && visibleButtons.includes(activeEl) ? activeEl : null);

    if (selectedBtn) {
      selectedBtn.click();
      return;
    }

    const dangerBtn = modalCard.querySelector('.modal-body .btn-danger:not([disabled])') || modalCard.querySelector('#btnConfirmDeleteAction');
    const primaryBtn = modalCard.querySelector('.modal-body .btn-primary:not([disabled]), button[type="submit"]:not([disabled])');

    const targetBtn = dangerBtn || primaryBtn || visibleButtons[0];
    if (targetBtn) {
      targetBtn.click();
    }
    return;
  }

  // 3. TAB / SHIFT+TAB FOCUS TRAP
  if (e.key === 'Tab') {
    const focusable = Array.from(modalCard.querySelectorAll(
      'a[href], button:not([disabled]), textarea:not([disabled]), input:not([type="hidden"]):not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])'
    )).filter(el => el.offsetParent !== null);

    if (focusable.length > 0) {
      if (e.shiftKey && (activeEl === focusable[0] || !modalCard.contains(activeEl))) {
        e.preventDefault();
        focusable[focusable.length - 1].focus();
        if (visibleButtons.includes(focusable[focusable.length - 1])) {
          visibleButtons.forEach(b => b.classList.remove('btn-keyboard-selected'));
          focusable[focusable.length - 1].classList.add('btn-keyboard-selected');
        }
      } else if (!e.shiftKey && (activeEl === focusable[focusable.length - 1] || !modalCard.contains(activeEl))) {
        e.preventDefault();
        focusable[0].focus();
        if (visibleButtons.includes(focusable[0])) {
          visibleButtons.forEach(b => b.classList.remove('btn-keyboard-selected'));
          focusable[0].classList.add('btn-keyboard-selected');
        }
      }
    }
  }
}

function showConfirmActionModal({ title, subtitle, message, confirmText = 'Confirm', confirmDanger = true, onConfirm }) {
  const iconClass = confirmDanger ? 'alert-triangle' : 'shield-alert';
  const iconBg = confirmDanger ? 'var(--status-danger-bg)' : 'var(--status-warning-bg)';
  const iconColor = confirmDanger ? 'var(--status-danger)' : 'var(--status-warning)';
  const btnClass = confirmDanger ? 'btn-danger' : 'btn-primary';

  window._pendingConfirmActionCallback = onConfirm;

  const body = `
    <div style="padding: 10px 0;">
      <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 14px;">
        <div style="width: 44px; height: 44px; border-radius: 50%; background: ${iconBg}; color: ${iconColor}; display: flex; align-items: center; justify-content: center; font-size: 1.2rem;">
          <i data-lucide="${iconClass}"></i>
        </div>
        <div>
          <h4 style="margin: 0; font-size: 1rem; color: var(--text-main);">${title}</h4>
          ${subtitle ? `<p style="margin: 4px 0 0; font-size: 0.8rem; color: var(--text-secondary);">${subtitle}</p>` : ''}
        </div>
      </div>
      <div style="font-size: 0.84rem; line-height: 1.6; color: var(--text-main); background: var(--bg-subtle); padding: 14px; border-radius: var(--radius-sm); border: 1px solid var(--border-subtle);">
        ${message}
      </div>
      <div style="display: flex; justify-content: flex-end; align-items: center; margin-top: 18px; gap: 8px;">
        <button type="button" class="btn btn-skin btn-sm" onclick="closeAppModal()">Cancel</button>
        <button type="button" class="btn ${btnClass} btn-sm" id="btnConfirmDeleteAction" onclick="executePendingConfirmAction()">
          ${confirmDanger ? '<i data-lucide="trash-2"></i>' : '<i data-lucide="check"></i>'} ${confirmText}
        </button>
      </div>
    </div>
  `;

  openAppModal(title, body);
}

function executePendingConfirmAction() {
  closeAppModal();
  if (typeof window._pendingConfirmActionCallback === 'function') {
    const cb = window._pendingConfirmActionCallback;
    window._pendingConfirmActionCallback = null;
    cb();
  }
}

function showToast(message, type = 'info') {
  const container = document.getElementById('toastContainer');
  if (!container) return;

  // If this is a success notification replacing a loading/transient state, dismiss transient toasts
  if (type === 'success') {
    container.querySelectorAll('.toast-info, .info').forEach(t => {
      const txt = t.textContent || '';
      if (txt.includes('Switching persona') || txt.includes('Refreshing authoritative')) {
        t.remove();
      }
    });
  }

  // Cap simultaneous toasts at 3 to prevent clutter
  while (container.children.length >= 3) {
    const oldest = container.firstElementChild;
    if (oldest) oldest.remove();
    else break;
  }

  const toast = document.createElement('div');
  toast.className = `toast toast-${type} toast-item ${type}`;

  const iconName = type === 'success' ? 'check-circle-2' : (type === 'error' ? 'alert-triangle' : (type === 'warning' ? 'alert-circle' : 'info'));

  toast.innerHTML = `
    <div style="display: flex; align-items: center; gap: 10px; flex: 1;">
      <i data-lucide="${iconName}"></i>
      <span style="line-height: 1.35;">${message}</span>
    </div>
    <button type="button" class="toast-close-btn" onclick="this.closest('.toast, .toast-item').remove()" title="Dismiss">
      <i data-lucide="x" style="width: 13px; height: 13px;"></i>
    </button>
  `;

  container.appendChild(toast);
  if (window.lucide) lucide.createIcons();

  const dismissTimer = setTimeout(() => {
    toast.style.transition = 'opacity 0.25s ease, transform 0.25s ease';
    toast.style.opacity = '0';
    toast.style.transform = 'translateY(8px)';
    setTimeout(() => {
      if (toast.parentNode) toast.remove();
    }, 250);
  }, 3500);

  toast.addEventListener('mouseenter', () => clearTimeout(dismissTimer));
}

function toggleSidebar() {
  const sb = document.getElementById('appSidebar');
  if (sb) sb.classList.toggle('open');
}

function closeSidebar() {
  const sb = document.getElementById('appSidebar');
  if (sb) sb.classList.remove('open');
}

function toggleTheme() {
  const cur = document.documentElement.getAttribute('data-theme') || 'light';
  const next = cur === 'dark' ? 'light' : 'dark';
  document.documentElement.setAttribute('data-theme', next);
  localStorage.setItem('setu_theme', next);
  updateThemeIcon(next);
}

function updateThemeIcon(theme) {
  const icon = document.getElementById('themeIcon');
  if (!icon) return;
  if (theme === 'dark') {
    icon.setAttribute('data-lucide', 'sun');
  } else {
    icon.setAttribute('data-lucide', 'moon');
  }
  if (window.lucide) lucide.createIcons();
}

function toggleNotificationDropdown() {
  const drop = document.getElementById('notifDropdown');
  if (drop) drop.classList.toggle('hidden');
}

function markAllNotificationsRead() {
  const drop = document.getElementById('notifDropdown');
  if (drop) drop.classList.add('hidden');
  const badge = document.getElementById('notifBadgeCount');
  if (badge) badge.textContent = '0';
}

function handleGlobalSearch(query) {
  if (!query || query.length < 2) return;
  const q = query.toLowerCase();

  // If in farmers view, filter table
  if (currentTab === 'farmers') {
    filterFarmersTable(q);
  } else if (q.includes('farmer')) {
    switchNavTab('farmers');
    document.getElementById('farmersSearchInput').value = q;
    filterFarmersTable(q);
  } else if (q.includes('order') || q.includes('ord-')) {
    switchNavTab('orders');
  } else if (q.includes('ticket') || q.includes('tkt-')) {
    switchNavTab('support');
  } else if (q.includes('device') || q.includes('gateway')) {
    switchNavTab('devices');
  } else if (q.includes('product') || q.includes('sku')) {
    switchNavTab('products');
  }
}


// ==========================================================================
// WEBSITE DEMO LEADS & ENQUIRIES CONTROLLER
// ==========================================================================

async function loadEnquiries() {
  const tbody = document.getElementById('enquiriesTableBody');
  if (!tbody) return;
  tbody.innerHTML = '<tr><td colspan="11" style="text-align: center; padding: 24px;">Loading website leads...</td></tr>';

  try {
    const filter = document.getElementById('enquiryStatusFilter')?.value || 'ALL';
    const query = filter !== 'ALL' ? `?status=${filter}` : '';
    const res = await fetch(`${API_BASE_URL}/enquiries${query}`, {
      headers: { 'Authorization': `Bearer ${adminToken}` }
    });
    if (!res.ok) throw new Error('Failed to load enquiries');
    const enquiries = await res.json();

    const countPill = document.getElementById('navEnquiryCount');
    if (countPill) {
      const newCount = enquiries.filter(e => e.status === 'NEW').length;
      countPill.textContent = newCount > 0 ? `${newCount} New` : `${enquiries.length}`;
      countPill.className = newCount > 0 ? 'nav-pill badge-warning' : 'nav-pill';
    }

    if (!enquiries.length) {
      tbody.innerHTML = '<tr><td colspan="11"><div class="honest-empty-state"><i data-lucide="inbox"></i><h4>No Website Enquiries</h4><p>No enquiries found matching this filter.</p></div></td></tr>';
      if (window.lucide) lucide.createIcons();
      return;
    }

    tbody.innerHTML = enquiries.map(e => {
      const dt = new Date(e.created_at).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' });
      let statusBadge = 'badge-neutral';
      if (e.status === 'NEW') statusBadge = 'badge-danger';
      else if (e.status === 'CONTACTED') statusBadge = 'badge-warning';
      else if (e.status === 'QUALIFIED') statusBadge = 'badge-info';
      else if (e.status === 'CONVERTED') statusBadge = 'badge-success';

      return `
        <tr>
          <td style="font-family: var(--font-mono); font-weight: 700; color: var(--green-deep);">${e.enquiry_reference}</td>
          <td style="font-size: 0.78rem; color: var(--text-muted);">${dt}</td>
          <td style="font-weight: 700;">${e.full_name}</td>
          <td>${e.organization || '<span style="color: var(--text-muted);">&mdash;</span>'}</td>
          <td style="font-size: 0.8rem;">
            <div><i data-lucide="phone" style="width: 12px; height: 12px; vertical-align: middle;"></i> ${e.phone}</div>
            <div style="color: var(--text-muted);"><i data-lucide="mail" style="width: 12px; height: 12px; vertical-align: middle;"></i> ${e.email}</div>
          </td>
          <td>${e.state_region || 'Karnataka'}</td>
          <td style="max-width: 180px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="${e.product_name || 'General Platform'}">
            ${e.product_name || '<span style="color: var(--text-muted);">Platform Automation</span>'}
          </td>
          <td><span class="badge badge-neutral">${e.enquiry_type}</span></td>
          <td><span class="badge ${statusBadge}">${e.status}</span></td>
          <td style="font-size: 0.8rem; color: var(--text-muted);">${e.assigned_to || 'Unassigned'}</td>
          <td>
            <select class="form-select" onchange="changeEnquiryStatus('${e.id}', this.value)" style="padding: 4px 8px; font-size: 0.75rem; border-radius: var(--radius-sm); border: 1px solid var(--skin-border); font-family: inherit;">
              <option value="NEW" ${e.status === 'NEW' ? 'selected' : ''}>NEW</option>
              <option value="CONTACTED" ${e.status === 'CONTACTED' ? 'selected' : ''}>CONTACTED</option>
              <option value="QUALIFIED" ${e.status === 'QUALIFIED' ? 'selected' : ''}>QUALIFIED</option>
              <option value="CONVERTED" ${e.status === 'CONVERTED' ? 'selected' : ''}>CONVERTED</option>
              <option value="CLOSED" ${e.status === 'CLOSED' ? 'selected' : ''}>CLOSED</option>
            </select>
          </td>
        </tr>
      `;
    }).join('');

    if (window.lucide) lucide.createIcons();
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="11" style="text-align: center; color: var(--rose);">Error loading website leads: ${err.message}</td></tr>`;
  }
}

async function changeEnquiryStatus(enquiryId, newStatus) {
  try {
    const res = await fetch(`${API_BASE_URL}/enquiries/${enquiryId}`, {
      method: 'PATCH',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${adminToken}`
      },
      body: JSON.stringify({ status: newStatus })
    });
    if (!res.ok) throw new Error('Status update failed');
    showToast(`Lead status updated to ${newStatus}`, 'success');
    loadEnquiries();
  } catch (err) {
    showToast(err.message, 'error');
  }
}

async function toggleProductPublication(productId, currentStatus) {
  const nextStatus = currentStatus === 'PUBLISHED' ? 'DRAFT' : 'PUBLISHED';
  try {
    const res = await fetch(`${API_BASE_URL}/products/${productId}/publication`, {
      method: 'PATCH',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${adminToken}`
      },
      body: JSON.stringify({ publication_status: nextStatus })
    });
    if (!res.ok) throw new Error('Failed to update publication status');
    showToast(`Product is now ${nextStatus}`, 'success');
    loadProducts();
  } catch (err) {
    showToast(err.message, 'error');
  }
}


// ==========================================================================
// ENTERPRISE WORKFLOW & INTERACTIVE NAVIGATION HELPERS
// ==========================================================================

function toggleSidebar() {
  if (window.innerWidth <= 900) {
    toggleMobileSidebar();
  } else {
    toggleSidebarRail();
  }
}

function toggleSidebarRail() {
  const layout = document.getElementById('dashboardView');
  if (!layout) return;
  const isCollapsed = layout.classList.toggle('sidebar-collapsed');
  localStorage.setItem('setu_sidebar_rail', isCollapsed ? 'true' : 'false');
  const icon = document.getElementById('sidebarRailIcon') || document.querySelector('#btnSidebarToggle i');
  if (icon) {
    icon.setAttribute('data-lucide', isCollapsed ? 'panel-left-open' : 'menu');
    if (window.lucide) lucide.createIcons();
  }
}

function toggleMobileSidebar() {
  const sb = document.getElementById('appSidebar');
  if (sb) sb.classList.toggle('mobile-open');
}

function toggleNavGroup(groupId) {
  const group = document.getElementById(groupId);
  if (!group) return;
  group.classList.toggle('collapsed');
}


// ==========================================================================
// TABLE ROW ACTION 3-DOTS DROPDOWN MENUS
// ==========================================================================

function toggleRowActionMenu(event, menuId) {
  if (event) {
    if (typeof event.stopPropagation === 'function') event.stopPropagation();
    if (typeof event.preventDefault === 'function') event.preventDefault();
  }
  if (!menuId) return;

  const targetId = menuId.startsWith('row-action-menu-') ? menuId : `row-action-menu-${menuId}`;
  const menu = document.getElementById(targetId);
  if (!menu) return;

  const wasOpen = !menu.classList.contains('hidden');

  // Close any open menus across tables first
  closeAllRowActionMenus();

  if (!wasOpen) {
    menu.classList.remove('hidden');

    const trigger = (event && event.currentTarget) || (menu.parentElement ? menu.parentElement.querySelector('.action-dots-trigger') : null);
    if (trigger) {
      trigger.classList.add('active');
    }

    // Smart vertical positioning: check if menu overflows bottom of viewport or table wrap
    const rect = menu.getBoundingClientRect();
    const tableWrap = menu.closest('.table-wrap');
    let shouldPopUp = false;

    if (rect.bottom > window.innerHeight - 15) {
      shouldPopUp = true;
    } else if (tableWrap) {
      const tableRect = tableWrap.getBoundingClientRect();
      if (rect.bottom > tableRect.bottom - 8 && rect.top - rect.height > tableRect.top) {
        shouldPopUp = true;
      }
    }

    if (shouldPopUp) {
      menu.classList.add('pop-up');
    } else {
      menu.classList.remove('pop-up');
    }

    if (window.lucide) {
      lucide.createIcons();
    }
  }
}

function closeAllRowActionMenus() {
  document.querySelectorAll('.row-action-menu').forEach(m => {
    m.classList.add('hidden');
    m.classList.remove('pop-up');
  });
  document.querySelectorAll('.action-dots-trigger').forEach(b => {
    b.classList.remove('active');
  });
}

window.toggleRowActionMenu = toggleRowActionMenu;
window.closeAllRowActionMenus = closeAllRowActionMenus;

function toggleUserDropdown() {
  const drop = document.getElementById('userMenuDropdown');
  if (drop) drop.classList.toggle('hidden');
}

function closeUserDropdown() {
  const drop = document.getElementById('userMenuDropdown');
  if (drop) drop.classList.add('hidden');
}

// ==========================================================================
// ACTIONABLE GLOBAL SEARCH COMMAND PALETTE
// ==========================================================================

let paletteDebounceTimer = null;

function openCommandPalette() {
  const modal = document.getElementById('commandPaletteModal');
  if (!modal) return;
  modal.classList.remove('hidden');
  const inp = document.getElementById('commandPaletteInput');
  if (inp) {
    inp.value = '';
    inp.focus();
  }
  document.getElementById('commandResultsBody').innerHTML = `
    <div style="padding: 32px 16px; text-align: center; color: var(--text-muted); font-size: 0.85rem;">
      Type at least 2 characters to search across farmers, sheds, devices, tickets, orders, and products...
    </div>
  `;
  if (window.lucide) lucide.createIcons();
}

function closeCommandPalette() {
  const modal = document.getElementById('commandPaletteModal');
  if (modal) modal.classList.add('hidden');
}

function handleCommandPaletteBackdrop(e) {
  if (e.target && e.target.id === 'commandPaletteModal') {
    closeCommandPalette();
  }
}

function debouncePaletteSearch(val) {
  if (paletteDebounceTimer) clearTimeout(paletteDebounceTimer);
  const q = (val || '').trim();
  if (q.length < 2) {
    document.getElementById('commandResultsBody').innerHTML = `
      <div style="padding: 32px 16px; text-align: center; color: var(--text-muted); font-size: 0.85rem;">
        Type at least 2 characters to search...
      </div>
    `;
    return;
  }
  paletteDebounceTimer = setTimeout(() => {
    executePaletteSearch(q);
  }, 220);
}

async function executePaletteSearch(query) {
  const body = document.getElementById('commandResultsBody');
  if (!body) return;
  body.innerHTML = `
    <div style="padding: 24px 16px; text-align: center; color: var(--text-muted); font-size: 0.85rem;">
      Searching live platform records for "${query}"...
    </div>
  `;

  try {
    const res = await fetch(`${API_BASE_URL}/platform/search?q=${encodeURIComponent(query)}&limit=5`, {
      headers: { 'Authorization': `Bearer ${adminToken}` }
    });
    if (!res.ok) throw new Error('Search failed');
    const data = await res.json();

    const sections = [];

    // 1. Farmers
    if (data.farmers && data.farmers.length > 0) {
      const items = data.farmers.map(f => `
        <div class="command-result-item" onclick="selectSearchResult('farmers', '${f.id}')">
          <div class="command-result-left">
            <div class="command-item-icon"><i data-lucide="user"></i></div>
            <div class="command-item-info">
              <span class="command-item-title">${f.full_name}</span>
              <span class="command-item-subtitle">${f.farm_name || 'Farm'} &bull; ${f.region || 'Region'} &bull; ${f.phone || ''}</span>
            </div>
          </div>
          <span class="badge ${f.is_active ? 'badge-success' : 'badge-neutral'}">${f.is_active ? 'Active' : 'Inactive'}</span>
        </div>
      `).join('');
      sections.push(`<div class="command-group-title">Farmers (${data.farmers.length})</div>${items}`);
    }

    // 2. Sheds
    if (data.sheds && data.sheds.length > 0) {
      const items = data.sheds.map(s => `
        <div class="command-result-item" onclick="selectSearchResult('sheds', '${s.id}')">
          <div class="command-result-left">
            <div class="command-item-icon"><i data-lucide="warehouse"></i></div>
            <div class="command-item-info">
              <span class="command-item-title">${s.name || s.id}</span>
              <span class="command-item-subtitle">${s.location || 'Location'} &bull; Stage ${s.current_stage || '1'} &bull; Target ${s.target_temp || 26}°C</span>
            </div>
          </div>
          <span class="badge badge-info">${s.id}</span>
        </div>
      `).join('');
      sections.push(`<div class="command-group-title">Rearing Sheds (${data.sheds.length})</div>${items}`);
    }

    // 3. Devices
    if (data.devices && data.devices.length > 0) {
      const items = data.devices.map(d => `
        <div class="command-result-item" onclick="selectSearchResult('devices', '${d.id}')">
          <div class="command-result-left">
            <div class="command-item-icon"><i data-lucide="cpu"></i></div>
            <div class="command-item-info">
              <span class="command-item-title">${d.name || d.id}</span>
              <span class="command-item-subtitle">Shed: ${d.shed_id} &bull; Firmware: ${d.firmware_version || 'v1.0'}</span>
            </div>
          </div>
          <span class="badge ${d.status === 'ONLINE' ? 'badge-success' : 'badge-danger'}">${d.status}</span>
        </div>
      `).join('');
      sections.push(`<div class="command-group-title">IoT Devices (${data.devices.length})</div>${items}`);
    }

    // 4. Orders
    if (data.orders && data.orders.length > 0) {
      const items = data.orders.map(o => `
        <div class="command-result-item" onclick="selectSearchResult('orders', '${o.id}')">
          <div class="command-result-left">
            <div class="command-item-icon"><i data-lucide="shopping-cart"></i></div>
            <div class="command-item-info">
              <span class="command-item-title">Order #${o.order_number}</span>
              <span class="command-item-subtitle">Total: ₹${((o.total_amount_minor_units || 0) / 100).toLocaleString('en-IN')} &bull; User: ${o.user_id}</span>
            </div>
          </div>
          <span class="badge badge-warning">${o.status}</span>
        </div>
      `).join('');
      sections.push(`<div class="command-group-title">Sales Orders (${data.orders.length})</div>${items}`);
    }

    // 5. Support Tickets
    if (data.support_tickets && data.support_tickets.length > 0) {
      const items = data.support_tickets.map(t => `
        <div class="command-result-item" onclick="selectSearchResult('support', '${t.id}')">
          <div class="command-result-left">
            <div class="command-item-icon"><i data-lucide="headphones"></i></div>
            <div class="command-item-info">
              <span class="command-item-title">#${t.ticket_number}: ${t.subject}</span>
              <span class="command-item-subtitle">Priority: ${t.priority} &bull; User: ${t.user_id}</span>
            </div>
          </div>
          <span class="badge ${t.status === 'RESOLVED' ? 'badge-success' : 'badge-warning'}">${t.status}</span>
        </div>
      `).join('');
      sections.push(`<div class="command-group-title">Support Tickets (${data.support_tickets.length})</div>${items}`);
    }

    // 6. Products
    if (data.products && data.products.length > 0) {
      const items = data.products.map(p => `
        <div class="command-result-item" onclick="selectSearchResult('products', '${p.id}')">
          <div class="command-result-left">
            <div class="command-item-icon"><i data-lucide="package"></i></div>
            <div class="command-item-info">
              <span class="command-item-title">${p.sku}: ${p.name}</span>
              <span class="command-item-subtitle">Price: ₹${((p.price_minor_units || 0)/100).toLocaleString('en-IN')} &bull; Stock: ${p.stock_quantity} ${p.unit}</span>
            </div>
          </div>
          <span class="badge badge-info">${p.category}</span>
        </div>
      `).join('');
      sections.push(`<div class="command-group-title">Products (${data.products.length})</div>${items}`);
    }

    // 7. Installations
    if (data.installation_jobs && data.installation_jobs.length > 0) {
      const items = data.installation_jobs.map(j => `
        <div class="command-result-item" onclick="selectSearchResult('installations', '${j.id}')">
          <div class="command-result-left">
            <div class="command-item-icon"><i data-lucide="wrench"></i></div>
            <div class="command-item-info">
              <span class="command-item-title">Job #${j.job_number} (${j.job_type})</span>
              <span class="command-item-subtitle">Shed: ${j.shed_id} &bull; Tech: ${j.technician_id || 'Unassigned'}</span>
            </div>
          </div>
          <span class="badge ${j.status === 'COMPLETED' ? 'badge-success' : 'badge-warning'}">${j.status}</span>
        </div>
      `).join('');
      sections.push(`<div class="command-group-title">Field Installations (${data.installation_jobs.length})</div>${items}`);
    }

    // 8. Alerts
    if (data.alerts && data.alerts.length > 0) {
      const items = data.alerts.map(a => `
        <div class="command-result-item" onclick="selectSearchResult('alerts', '${a.id}')">
          <div class="command-result-left">
            <div class="command-item-icon"><i data-lucide="alert-triangle"></i></div>
            <div class="command-item-info">
              <span class="command-item-title">${a.title}</span>
              <span class="command-item-subtitle">Shed: ${a.shed_id}</span>
            </div>
          </div>
          <span class="badge ${a.severity === 'CRITICAL' ? 'badge-danger' : 'badge-warning'}">${a.severity}</span>
        </div>
      `).join('');
      sections.push(`<div class="command-group-title">System Alerts (${data.alerts.length})</div>${items}`);
    }

    if (sections.length === 0) {
      body.innerHTML = `
        <div style="padding: 32px 16px; text-align: center; color: var(--text-muted); font-size: 0.85rem;">
          No matching records found for "${query}".
        </div>
      `;
      return;
    }

    body.innerHTML = sections.join('');
    if (window.lucide) lucide.createIcons();

  } catch (err) {
    body.innerHTML = `
      <div style="padding: 24px 16px; text-align: center; color: var(--status-danger); font-size: 0.85rem;">
        Search query error: ${err.message}
      </div>
    `;
  }
}

function selectSearchResult(tab, entityId) {
  closeCommandPalette();
  switchNavTab(tab);
  if (tab === 'farmers') {
    openFarmerDrawer(entityId);
  } else if (tab === 'orders') {
    openOrderDetailDrawer(entityId);
  } else if (tab === 'support') {
    openTicketDetailDrawer(entityId);
  }
}

// ==========================================================================
// MY WORK & TASK QUEUE CONTROLLER
// ==========================================================================

async function loadUserTasks() {
  const tbody = document.getElementById('tasksTableBody');
  const countBadge = document.getElementById('tasksBadgeCount');
  const navBadge = document.getElementById('navTaskCount');
  if (!tbody) return;

  tbody.innerHTML = '<tr><td colspan="6" style="text-align: center; padding: 24px;">Loading pending workflow tasks...</td></tr>';

  try {
    const [ordersRes, ticketsRes, installsRes, alertsRes] = await Promise.all([
      fetch(`${API_BASE_URL}/orders?status=PENDING`, { headers: { 'Authorization': `Bearer ${adminToken}` } }),
      fetch(`${API_BASE_URL}/support/tickets?status=OPEN`, { headers: { 'Authorization': `Bearer ${adminToken}` } }),
      fetch(`${API_BASE_URL}/installations?status=SCHEDULED`, { headers: { 'Authorization': `Bearer ${adminToken}` } }),
      fetch(`${API_BASE_URL}/alerts`, { headers: { 'Authorization': `Bearer ${adminToken}` } })
    ]);

    const orders = ordersRes.ok ? await ordersRes.json() : [];
    const tickets = ticketsRes.ok ? await ticketsRes.json() : [];
    const installs = installsRes.ok ? await installsRes.json() : [];
    const rawAlerts = alertsRes.ok ? await alertsRes.json() : [];
    const activeAlerts = rawAlerts.filter(a => a.status === 'ACTIVE' || a.status === 'TRIGGERED');

    const tasks = [];

    orders.forEach(o => {
      tasks.push({
        category: 'Order Review',
        icon: 'shopping-cart',
        title: `Pending Order #${o.order_number}`,
        subtitle: `₹${((o.total_amount_minor_units || 0) / 100).toLocaleString('en-IN')}`,
        assigned: 'Sales Desk',
        priority: 'MEDIUM',
        created: o.created_at,
        status: o.status,
        action: `switchNavTab('orders'); openOrderDetailDrawer('${o.id}');`,
        btnText: 'Review Order'
      });
    });

    tickets.forEach(t => {
      tasks.push({
        category: 'Support Escalation',
        icon: 'headphones',
        title: `Ticket #${t.ticket_number}: ${t.subject}`,
        subtitle: `Customer: ${t.user_id}`,
        assigned: t.assigned_to || 'Unassigned',
        priority: t.priority,
        created: t.created_at,
        status: t.status,
        action: `switchNavTab('support'); openTicketDetailDrawer('${t.id}');`,
        btnText: 'Respond'
      });
    });

    installs.forEach(i => {
      tasks.push({
        category: 'Field Installation',
        icon: 'wrench',
        title: `Job #${i.job_number} (${i.job_type})`,
        subtitle: `Shed: ${i.shed_id}`,
        assigned: i.technician_id || 'Tech Team',
        priority: 'HIGH',
        created: i.scheduled_date || i.created_at,
        status: i.status,
        action: `switchNavTab('installations'); openInstallationWorkflowDrawer('${i.id}', '${i.job_number}', '${i.status}');`,
        btnText: 'Verify Checklist'
      });
    });

    activeAlerts.forEach(a => {
      tasks.push({
        category: 'Incident Alert',
        icon: 'alert-triangle',
        title: `${a.alert_type}: ${a.title || a.description}`,
        subtitle: `Shed: ${a.shed_id}`,
        assigned: 'Duty Supervisor',
        priority: a.severity || 'CRITICAL',
        created: a.triggered_at,
        status: a.status,
        action: `switchNavTab('alerts');`,
        btnText: 'Inspect Alert'
      });
    });

    if (countBadge) countBadge.textContent = `${tasks.length} Pending`;
    if (navBadge) navBadge.textContent = `${tasks.length}`;

    if (tasks.length === 0) {
      tbody.innerHTML = `
        <tr>
          <td colspan="6">
            <div class="empty-state">
              <div class="empty-icon"><i data-lucide="check-check"></i></div>
              <div class="empty-title">All Priority Work Completed</div>
              <div class="empty-desc">No orders awaiting fulfillment, open customer escalations, or unassigned installations in your queue.</div>
            </div>
          </td>
        </tr>
      `;
      if (window.lucide) lucide.createIcons();
      return;
    }

    tbody.innerHTML = tasks.map(item => {
      let prBadge = 'badge-neutral';
      if (item.priority === 'CRITICAL') prBadge = 'badge-danger';
      else if (item.priority === 'HIGH') prBadge = 'badge-warning';
      else if (item.priority === 'MEDIUM') prBadge = 'badge-info';

      const dateStr = item.created ? new Date(item.created).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' }) : 'Recent';

      return `
        <tr>
          <td>
            <div style="display: flex; align-items: center; gap: 8px;">
              <i data-lucide="${item.icon}" style="width: 15px; height: 15px; color: var(--brand-primary);"></i>
              <span style="font-weight: 700;">${item.category}</span>
            </div>
          </td>
          <td>
            <div style="font-weight: 700; color: var(--text-main);">${item.title}</div>
            <div style="font-size: 0.74rem; color: var(--text-muted);">${item.subtitle}</div>
          </td>
          <td>${item.assigned}</td>
          <td><span class="badge ${prBadge}">${item.priority}</span></td>
          <td style="font-size: 0.78rem; color: var(--text-muted);">${dateStr}</td>
          <td><span class="badge badge-neutral">${item.status}</span></td>
          <td>
            <button class="btn btn-skin btn-sm" onclick="${item.action}">
              ${item.btnText}
            </button>
          </td>
        </tr>
      `;
    }).join('');

    if (window.lucide) lucide.createIcons();

  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="6" style="text-align: center; color: var(--status-danger);">Failed to load priority tasks: ${err.message}</td></tr>`;
  }
}


// ==============================================================================
// 23. ROLE-BASED DASHBOARD HERO & ADAPTIVE KPIS
// ==============================================================================

async function loadRoleDashboardHero() {
  const hero = document.getElementById('roleDashboardHero');
  if (!hero) return;

  try {
    const res = await fetch(`${API_BASE_URL}/dashboard/role-view`, {
      headers: { 'Authorization': `Bearer ${adminToken}` }
    });
    if (!res.ok) return;
    const data = await res.json();
    const v = data.view;
    if (!v) return;

    const titleEl = document.getElementById('roleHeroTitle');
    const subEl = document.getElementById('roleHeroSubtitle');
    const badgeEl = document.getElementById('roleHeroBadge');
    const orgEl = document.getElementById('roleHeroOrg');

    if (titleEl) titleEl.textContent = v.title;
    if (subEl) subEl.textContent = v.subtitle;
    if (badgeEl) badgeEl.textContent = (v.role || 'farmer').toUpperCase();
    if (orgEl) orgEl.innerHTML = `<i data-lucide="building" style="width: 13px; height: 13px; display: inline-block; vertical-align: middle;"></i> SeriCare Platform Operations`;

    renderRoleSpecificKpis(v.kpis || []);
    if (window.lucide) lucide.createIcons();
  } catch (err) {
    console.error("Failed to load role dashboard hero:", err);
  }
}

function refreshRoleDashboard() {
  showToast('Refreshing role telemetry and operational context...', 'info');
  loadRoleDashboardHero();
  fetchOverviewKpis();
}

function renderRoleSpecificKpis(kpis) {
  const container = document.getElementById('roleKpiRow');
  if (!container) return;

  if (!kpis.length) {
    container.innerHTML = '';
    return;
  }

  container.innerHTML = kpis.map(k => `
    <div class="kpi-card" onclick="switchNavTab('${k.tab || 'overview'}')" style="cursor: pointer; border-left: 3px solid var(--brand-primary); transition: transform 0.15s ease;">
      <div style="display: flex; justify-content: space-between; align-items: flex-start;">
        <div class="kpi-label">${k.label}</div>
        <div class="kpi-icon-wrap" style="color: var(--brand-primary); background: var(--brand-tint); width: 34px; height: 34px; border-radius: 8px; display: flex; align-items: center; justify-content: center;">
          <i data-lucide="${k.icon || 'activity'}" style="width: 17px; height: 17px;"></i>
        </div>
      </div>
      <div class="kpi-value" style="font-size: 1.5rem; font-weight: 800; margin: 6px 0 2px; color: var(--text-main);">${k.value}</div>
      <div class="kpi-sub" style="font-size: 0.72rem; color: var(--text-muted);">${k.sub}</div>
    </div>
  `).join('');

  if (window.lucide) lucide.createIcons();
}


// ==============================================================================
// 25. EMPLOYEES & USER MANAGEMENT MODULE
// ==============================================================================

let allEmployeesData = [];
let currentEmpPage = 0;
const empPageSize = 10;
let empSearchTimeout = null;

function debounceFilterEmployees(val) {
  clearTimeout(empSearchTimeout);
  empSearchTimeout = setTimeout(() => {
    currentEmpPage = 0;
    loadEmployeesList();
  }, 250);
}

function navigateEmpPage(direction) {
  currentEmpPage += direction;
  if (currentEmpPage < 0) currentEmpPage = 0;
  loadEmployeesList();
}

async function loadEmployeesList() {
  const tbody = document.getElementById('employeesTableBody');
  if (!tbody) return;

  const search = document.getElementById('empSearchInput')?.value || '';
  const deptFilter = document.getElementById('empDeptFilter')?.value || '';
  const roleFilter = document.getElementById('empRoleFilter')?.value || '';
  const statusFilter = document.getElementById('empStatusFilter')?.value || '';

  let url = `${API_BASE_URL}/employees?limit=${empPageSize}&offset=${currentEmpPage * empPageSize}`;
  if (search) url += `&search=${encodeURIComponent(search)}`;
  if (deptFilter) url += `&dept_id=${encodeURIComponent(deptFilter)}`;
  if (roleFilter) url += `&role=${encodeURIComponent(roleFilter)}`;
  if (statusFilter) url += `&status=${encodeURIComponent(statusFilter)}`;

  try {
    const res = await fetch(url, {
      headers: { 'Authorization': `Bearer ${adminToken}` }
    });
    if (!res.ok) throw new Error('Failed to load employees list');
    const data = await res.json();
    allEmployeesData = data.employees || [];

    const navEmpPill = document.getElementById('navEmpCount');
    if (navEmpPill) navEmpPill.textContent = data.total || 0;

    const countEl = document.getElementById('empPaginationCount');
    if (countEl) {
      const start = data.total ? (currentEmpPage * empPageSize + 1) : 0;
      const end = Math.min((currentEmpPage + 1) * empPageSize, data.total);
      countEl.textContent = `Showing ${start}–${end} of ${data.total} employees`;
    }

    const btnPrev = document.getElementById('btnEmpPrev');
    const btnNext = document.getElementById('btnEmpNext');
    if (btnPrev) btnPrev.disabled = (currentEmpPage === 0);
    if (btnNext) btnNext.disabled = ((currentEmpPage + 1) * empPageSize >= data.total);

    renderEmployeesTable(allEmployeesData);
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="10" style="text-align: center; color: var(--status-danger); padding: 24px;">Failed to load employees: ${err.message}</td></tr>`;
  }
}

function renderEmployeesTable(employees) {
  const tbody = document.getElementById('employeesTableBody');
  if (!tbody) return;

  if (!employees.length) {
    tbody.innerHTML = '<tr><td colspan="10"><div class="honest-empty-state"><i data-lucide="users"></i><h4>No Employee Records Found</h4><p>No employees match the selected criteria or search query.</p></div></td></tr>';
    if (window.lucide) lucide.createIcons();
    return;
  }

  tbody.innerHTML = employees.map(e => `
    <tr>
      <td>
        <div style="font-weight: 700; color: var(--text-main);">${e.full_name}</div>
        <div style="font-size: 0.72rem; color: var(--text-muted); font-family: var(--font-mono); font-weight: 600;">${e.employee_id} · @${e.username}</div>
      </td>
      <td>
        <span style="font-size: 0.8rem; color: var(--text-secondary);">${e.official_email}</span>
      </td>
      <td>
        <span style="font-size: 0.8rem; font-weight: 600;">${e.department_name || 'Unassigned'}</span>
      </td>
      <td>
        <span style="font-size: 0.78rem;">${e.designation}</span>
      </td>
      <td>
        <span style="font-size: 0.78rem; color: var(--text-secondary);">${e.reporting_manager_name ? `<i data-lucide="corner-down-right" style="width: 12px; height: 12px; display: inline-block;"></i> ${e.reporting_manager_name}` : 'None (Independent)'}</span>
      </td>
      <td>
        <span class="badge" style="background: var(--brand-tint); color: var(--brand-primary); font-weight: 700; padding: 2px 8px; border-radius: 12px; font-size: 0.72rem;">${e.role_code}</span>
      </td>
      <td>
        <span class="font-mono" style="font-size: 0.72rem; background: var(--bg-subtle); padding: 2px 6px; border-radius: 4px;">${e.access_scope}</span>
      </td>
      <td>
        <span class="status-pill ${e.employment_status === 'ACTIVE' ? 'active' : (e.employment_status === 'SUSPENDED' ? 'danger' : 'warning')}">
          ${e.employment_status}
        </span>
      </td>
      <td>
        <span class="badge" style="background: ${e.invitation_status === 'ACCEPTED' ? 'var(--status-success-bg)' : (e.invitation_status === 'PENDING' ? 'var(--status-warning-bg)' : 'var(--bg-subtle)')}; color: ${e.invitation_status === 'ACCEPTED' ? 'var(--status-success-text)' : (e.invitation_status === 'PENDING' ? 'var(--status-warning-text)' : 'var(--text-muted)')}; font-size: 0.70rem; padding: 2px 6px; border-radius: 4px;">
          ${e.invitation_status}
        </span>
      </td>
      <td>
        <div class="row-action-dropdown">
          <button type="button" class="action-dots-trigger" onclick="toggleRowActionMenu(event, 'emp-${e.id}')" title="Actions" aria-label="Actions">
            <i data-lucide="more-vertical"></i>
          </button>
          <div class="row-action-menu hidden" id="row-action-menu-emp-${e.id}">
            <button type="button" class="row-action-item" onclick="viewEmployeeDetails('${e.id}'); closeAllRowActionMenus();">
              <i data-lucide="eye"></i> <span>View Full Details</span>
            </button>
            <button type="button" class="row-action-item" onclick="openEditEmployeeModal('${e.id}'); closeAllRowActionMenus();">
              <i data-lucide="edit"></i> <span>Edit Employee</span>
            </button>
            ${e.invitation_status === 'PENDING' ? `
              <button type="button" class="row-action-item" onclick="resendEmployeeInvitation('${e.id}'); closeAllRowActionMenus();">
                <i data-lucide="send"></i> <span>Resend Invitation</span>
              </button>
              <button type="button" class="row-action-item danger-item" onclick="revokeEmployeeInvitation('${e.id}'); closeAllRowActionMenus();">
                <i data-lucide="x-circle"></i> <span>Revoke Invitation</span>
              </button>
            ` : ''}
            <div class="row-action-divider"></div>
            <button type="button" class="row-action-item ${e.employment_status === 'ACTIVE' ? 'danger-item' : 'success-item'}" onclick="toggleEmployeeStatus('${e.id}', '${e.employment_status}'); closeAllRowActionMenus();">
              <i data-lucide="${e.employment_status === 'ACTIVE' ? 'user-x' : 'user-check'}"></i>
              <span>${e.employment_status === 'ACTIVE' ? 'Suspend Employee' : 'Activate Employee'}</span>
            </button>
          </div>
        </div>
      </td>
    </tr>
  `).join('');

  if (window.lucide) lucide.createIcons();
}

async function openOnboardEmployeeModal() {
  // Fetch departments and potential reporting managers for dropdowns
  let depts = [];
  let potentialManagers = [];
  try {
    const [resD, resM] = await Promise.all([
      fetch(`${API_BASE_URL}/departments`, { headers: { 'Authorization': `Bearer ${adminToken}` } }),
      fetch(`${API_BASE_URL}/employees?limit=100`, { headers: { 'Authorization': `Bearer ${adminToken}` } })
    ]);
    if (resD.ok) depts = await resD.json();
    if (resM.ok) {
      const dataM = await resM.json();
      potentialManagers = dataM.employees || [];
    }
  } catch (e) {
    console.error(e);
  }

  const deptOptions = depts.map(d => `<option value="${d.id}">${d.name} (${d.code})</option>`).join('');
  const mgrOptions = `<option value="">None (Top-Level Report)</option>` + potentialManagers.map(m => `<option value="${m.id}">${m.full_name} (${m.designation})</option>`).join('');

  const body = `
    <form id="onboardEmpForm" onsubmit="submitOnboardEmployee(event)" style="display: flex; flex-direction: column; gap: 12px;">
      <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px;">
        <div class="form-group">
          <label style="font-size: 0.8rem; font-weight: 700;">Full Legal Name *</label>
          <input type="text" id="onboardFullName" required placeholder="e.g. Ramesh Kumar" style="width: 100%; padding: 8px 10px; border-radius: var(--radius-sm); border: 1px solid var(--border-color);">
        </div>
        <div class="form-group">
          <label style="font-size: 0.8rem; font-weight: 700;">Official Corporate Email *</label>
          <input type="email" id="onboardEmail" required placeholder="e.g. ramesh.kumar@setu.io" style="width: 100%; padding: 8px 10px; border-radius: var(--radius-sm); border: 1px solid var(--border-color);">
        </div>
      </div>
      <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px;">
        <div class="form-group">
          <label style="font-size: 0.8rem; font-weight: 700;">Corporate Employee ID *</label>
          <input type="text" id="onboardEmpId" required placeholder="e.g. EMP-1042" style="width: 100%; padding: 8px 10px; border-radius: var(--radius-sm); border: 1px solid var(--border-color); text-transform: uppercase;">
        </div>
        <div class="form-group">
          <label style="font-size: 0.8rem; font-weight: 700;">Contact Phone</label>
          <input type="text" id="onboardPhone" placeholder="+91 98450 12345" style="width: 100%; padding: 8px 10px; border-radius: var(--radius-sm); border: 1px solid var(--border-color);">
        </div>
      </div>
      <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px;">
        <div class="form-group">
          <label style="font-size: 0.8rem; font-weight: 700;">Department</label>
          <select id="onboardDept" style="width: 100%; padding: 8px 10px; border-radius: var(--radius-sm); border: 1px solid var(--border-color);">
            <option value="">Unassigned</option>
            ${deptOptions}
          </select>
        </div>
        <div class="form-group">
          <label style="font-size: 0.8rem; font-weight: 700;">Designation / Title</label>
          <input type="text" id="onboardDesignation" placeholder="e.g. Senior Field Technician" style="width: 100%; padding: 8px 10px; border-radius: var(--radius-sm); border: 1px solid var(--border-color);">
        </div>
      </div>
      <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px;">
        <div class="form-group">
          <label style="font-size: 0.8rem; font-weight: 700;">Reporting Manager (No Cycles)</label>
          <select id="onboardManager" style="width: 100%; padding: 8px 10px; border-radius: var(--radius-sm); border: 1px solid var(--border-color);">
            ${mgrOptions}
          </select>
        </div>
        <div class="form-group">
          <label style="font-size: 0.8rem; font-weight: 700;">Assigned Role Template *</label>
          <select id="onboardRole" required style="width: 100%; padding: 8px 10px; border-radius: var(--radius-sm); border: 1px solid var(--border-color);">
            <option value="technician" selected>Installation Technician</option>
            <option value="company_admin">Company Admin</option>
            <option value="operations_manager">Operations Manager</option>
            <option value="hr">HR / User Administrator</option>
            <option value="sales">Sales & Billing</option>
            <option value="support">Support Agent</option>
            <option value="analyst">Analyst / Researcher</option>
            <option value="ceo">CEO / Executive</option>
          </select>
        </div>
      </div>
      <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px;">
        <div class="form-group">
          <label style="font-size: 0.8rem; font-weight: 700;">Access Scope Policy</label>
          <select id="onboardScope" style="width: 100%; padding: 8px 10px; border-radius: var(--radius-sm); border: 1px solid var(--border-color);">
            <option value="ASSIGNED_ONLY">Assigned Resources Only</option>
            <option value="DEPARTMENT">Department Resources</option>
            <option value="ORGANIZATION" selected>All Authorized in Organization</option>
          </select>
        </div>
        <div class="form-group">
          <label style="font-size: 0.8rem; font-weight: 700;">Authorized Shed IDs</label>
          <input type="text" id="onboardSheds" placeholder="shed_01, shed_02" style="width: 100%; padding: 8px 10px; border-radius: var(--radius-sm); border: 1px solid var(--border-color);">
        </div>
      </div>
      <div style="background: var(--bg-subtle); padding: 10px 12px; border-radius: var(--radius-sm); font-size: 0.74rem; color: var(--text-secondary); line-height: 1.4;">
        <i data-lucide="shield-check" style="width: 14px; height: 14px; display: inline-block; vertical-align: middle;"></i>
        A single-use, time-limited activation invitation will be safely generated. Plaintext passwords are never emailed.
      </div>
      <div style="display: flex; justify-content: flex-end; gap: 8px; margin-top: 10px;">
        <button type="button" class="btn btn-skin btn-sm" onclick="closeAppModal()">Cancel</button>
        <button type="submit" class="btn btn-primary btn-sm"><i data-lucide="send"></i> Onboard & Issue Invitation</button>
      </div>
    </form>
  `;
  openAppModal('Onboard New Employee & Issue Invitation', body);
}

async function submitOnboardEmployee(e) {
  e.preventDefault();
  const full_name = document.getElementById('onboardFullName').value.trim();
  const official_email = document.getElementById('onboardEmail').value.trim();
  const employee_id = document.getElementById('onboardEmpId').value.trim().toUpperCase();
  const phone = document.getElementById('onboardPhone').value.trim();
  const department_id = document.getElementById('onboardDept').value || null;
  const designation = document.getElementById('onboardDesignation').value.trim() || 'Operations Staff';
  const reporting_manager_id = document.getElementById('onboardManager').value || null;
  const role_code = document.getElementById('onboardRole').value;
  const access_scope = document.getElementById('onboardScope').value;
  const shedsRaw = document.getElementById('onboardSheds').value.trim();
  const sheds = shedsRaw ? shedsRaw.split(',').map(s => s.trim()).filter(Boolean) : [];

  try {
    const res = await fetch(`${API_BASE_URL}/employees`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${adminToken}`
      },
      body: JSON.stringify({
        full_name,
        official_email,
        employee_id,
        phone,
        department_id,
        designation,
        reporting_manager_id,
        role_code,
        access_scope,
        assigned_resources: { sheds, devices: [] }
      })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Failed to onboard employee');

    closeAppModal();
    loadEmployeesList();

    // Display the generated invitation link modal
    const invBody = `
      <div style="display: flex; flex-direction: column; gap: 14px;">
        <div style="display: flex; align-items: center; gap: 10px; color: var(--brand-primary);">
          <div style="background: var(--brand-tint); padding: 8px; border-radius: 50%;"><i data-lucide="check-circle"></i></div>
          <h4 style="margin: 0; font-size: 1rem;">Employee Onboarded Successfully</h4>
        </div>
        <p style="font-size: 0.82rem; color: var(--text-secondary); margin: 0;">
          A single-use onboarding token has been issued for <strong>${full_name}</strong> (${official_email}).
        </p>
        <div style="background: var(--bg-subtle); padding: 12px; border-radius: var(--radius-sm); border: 1px solid var(--border-color);">
          <label style="font-size: 0.72rem; font-weight: 700; color: var(--text-muted); text-transform: uppercase;">Secure Activation URL</label>
          <div style="display: flex; gap: 8px; margin-top: 4px;">
            <input type="text" id="genInvUrl" readonly value="${data.activation_url}" style="width: 100%; font-size: 0.78rem; font-family: var(--font-mono); padding: 6px 10px; border-radius: var(--radius-sm); border: 1px solid var(--border-color); background: var(--bg-surface);">
            <button class="btn btn-primary btn-sm" onclick="copyToClipboard('${data.activation_url}')"><i data-lucide="copy"></i> Copy</button>
          </div>
        </div>
        <div style="font-size: 0.74rem; color: var(--text-muted);">
          <strong>Delivery Notice:</strong> ${data.delivery_notice}
        </div>
        <div style="display: flex; justify-content: flex-end; margin-top: 6px;">
          <button class="btn btn-skin btn-sm" onclick="closeAppModal()">Done</button>
        </div>
      </div>
    `;
    openAppModal('Onboarding Invitation Ready', invBody);
  } catch (err) {
    showToast(err.message, 'error');
  }
}

async function openEditEmployeeModal(empId) {
  const emp = allEmployeesData.find(e => e.id === empId);
  if (!emp) return;

  let depts = [];
  let potentialManagers = [];
  try {
    const [resD, resM] = await Promise.all([
      fetch(`${API_BASE_URL}/departments`, { headers: { 'Authorization': `Bearer ${adminToken}` } }),
      fetch(`${API_BASE_URL}/employees?limit=100`, { headers: { 'Authorization': `Bearer ${adminToken}` } })
    ]);
    if (resD.ok) depts = await resD.json();
    if (resM.ok) {
      const dataM = await resM.json();
      potentialManagers = (dataM.employees || []).filter(m => m.id !== emp.id);
    }
  } catch (e) {
    console.error(e);
  }

  const deptOptions = depts.map(d => `<option value="${d.id}" ${emp.department_id === d.id ? 'selected' : ''}>${d.name} (${d.code})</option>`).join('');
  const mgrOptions = `<option value="">None (Top-Level Report)</option>` + potentialManagers.map(m => `<option value="${m.id}" ${emp.reporting_manager_id === m.id ? 'selected' : ''}>${m.full_name} (${m.designation})</option>`).join('');

  const assignedSheds = emp.assigned_resources?.sheds ? emp.assigned_resources.sheds.join(', ') : '';

  const body = `
    <form id="editEmpForm" onsubmit="submitEditEmployee(event, '${emp.id}')" style="display: flex; flex-direction: column; gap: 12px;">
      <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px;">
        <div class="form-group">
          <label style="font-size: 0.8rem; font-weight: 700;">Full Legal Name</label>
          <input type="text" id="editFullName" value="${emp.full_name}" required style="width: 100%; padding: 8px 10px; border-radius: var(--radius-sm); border: 1px solid var(--border-color);">
        </div>
        <div class="form-group">
          <label style="font-size: 0.8rem; font-weight: 700;">Contact Phone</label>
          <input type="text" id="editPhone" value="${emp.phone || ''}" style="width: 100%; padding: 8px 10px; border-radius: var(--radius-sm); border: 1px solid var(--border-color);">
        </div>
      </div>
      <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px;">
        <div class="form-group">
          <label style="font-size: 0.8rem; font-weight: 700;">Department</label>
          <select id="editDept" style="width: 100%; padding: 8px 10px; border-radius: var(--radius-sm); border: 1px solid var(--border-color);">
            <option value="">Unassigned</option>
            ${deptOptions}
          </select>
        </div>
        <div class="form-group">
          <label style="font-size: 0.8rem; font-weight: 700;">Designation</label>
          <input type="text" id="editDesignation" value="${emp.designation}" style="width: 100%; padding: 8px 10px; border-radius: var(--radius-sm); border: 1px solid var(--border-color);">
        </div>
      </div>
      <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px;">
        <div class="form-group">
          <label style="font-size: 0.8rem; font-weight: 700;">Reporting Manager</label>
          <select id="editManager" style="width: 100%; padding: 8px 10px; border-radius: var(--radius-sm); border: 1px solid var(--border-color);">
            ${mgrOptions}
          </select>
        </div>
        <div class="form-group">
          <label style="font-size: 0.8rem; font-weight: 700;">Assigned Role</label>
          <select id="editRole" style="width: 100%; padding: 8px 10px; border-radius: var(--radius-sm); border: 1px solid var(--border-color);">
            <option value="technician" ${emp.role_code === 'technician' ? 'selected' : ''}>Installation Technician</option>
            <option value="company_admin" ${emp.role_code === 'company_admin' ? 'selected' : ''}>Company Admin</option>
            <option value="operations_manager" ${emp.role_code === 'operations_manager' ? 'selected' : ''}>Operations Manager</option>
            <option value="hr" ${emp.role_code === 'hr' ? 'selected' : ''}>HR / User Administrator</option>
            <option value="sales" ${emp.role_code === 'sales' ? 'selected' : ''}>Sales & Billing</option>
            <option value="support" ${emp.role_code === 'support' ? 'selected' : ''}>Support Agent</option>
            <option value="analyst" ${emp.role_code === 'analyst' ? 'selected' : ''}>Analyst / Researcher</option>
            <option value="ceo" ${emp.role_code === 'ceo' ? 'selected' : ''}>CEO / Executive</option>
          </select>
        </div>
      </div>
      <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px;">
        <div class="form-group">
          <label style="font-size: 0.8rem; font-weight: 700;">Access Scope</label>
          <select id="editScope" style="width: 100%; padding: 8px 10px; border-radius: var(--radius-sm); border: 1px solid var(--border-color);">
            <option value="ASSIGNED_ONLY" ${emp.access_scope === 'ASSIGNED_ONLY' ? 'selected' : ''}>Assigned Resources Only</option>
            <option value="DEPARTMENT" ${emp.access_scope === 'DEPARTMENT' ? 'selected' : ''}>Department Resources</option>
            <option value="ORGANIZATION" ${emp.access_scope === 'ORGANIZATION' ? 'selected' : ''}>All Authorized in Organization</option>
          </select>
        </div>
        <div class="form-group">
          <label style="font-size: 0.8rem; font-weight: 700;">Assigned Sheds (comma-separated)</label>
          <input type="text" id="editSheds" value="${assignedSheds}" style="width: 100%; padding: 8px 10px; border-radius: var(--radius-sm); border: 1px solid var(--border-color);">
        </div>
      </div>
      <div style="display: flex; justify-content: flex-end; gap: 8px; margin-top: 10px;">
        <button type="button" class="btn btn-skin btn-sm" onclick="closeAppModal()">Cancel</button>
        <button type="submit" class="btn btn-primary btn-sm"><i data-lucide="check"></i> Save Changes</button>
      </div>
    </form>
  `;
  openAppModal(`Edit Employee: ${emp.full_name}`, body);
}

async function submitEditEmployee(e, empId) {
  e.preventDefault();
  const full_name = document.getElementById('editFullName').value.trim();
  const phone = document.getElementById('editPhone').value.trim();
  const department_id = document.getElementById('editDept').value || null;
  const designation = document.getElementById('editDesignation').value.trim();
  const reporting_manager_id = document.getElementById('editManager').value || null;
  const role_code = document.getElementById('editRole').value;
  const access_scope = document.getElementById('editScope').value;
  const shedsRaw = document.getElementById('editSheds').value.trim();
  const sheds = shedsRaw ? shedsRaw.split(',').map(s => s.trim()).filter(Boolean) : [];

  try {
    const res = await fetch(`${API_BASE_URL}/employees/${empId}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${adminToken}`
      },
      body: JSON.stringify({
        full_name, phone, department_id, designation, reporting_manager_id, role_code, access_scope,
        assigned_resources: { sheds, devices: [] }
      })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Failed to update employee');

    showToast('Employee record updated', 'success');
    closeAppModal();
    loadEmployeesList();
  } catch (err) {
    showToast(err.message, 'error');
  }
}

function toggleEmployeeStatus(empId, currStatus) {
  const newStatus = currStatus === 'ACTIVE' ? 'SUSPENDED' : 'ACTIVE';
  const isSuspending = newStatus === 'SUSPENDED';

  showConfirmActionModal({
    title: isSuspending ? 'Suspend Employee Account' : 'Reactivate Employee Account',
    subtitle: isSuspending ? 'Revoking user session' : 'Restoring user credentials',
    message: isSuspending
      ? 'Are you sure you want to suspend this employee? Their existing session and token will be immediately blocked.'
      : 'Are you sure you want to reactivate this employee? Their account will be restored with full operational access.',
    confirmText: isSuspending ? 'Suspend Employee' : 'Reactivate Employee',
    confirmDanger: isSuspending,
    onConfirm: async () => {
      try {
        const res = await fetch(`${API_BASE_URL}/employees/${empId}/status`, {
          method: 'PATCH',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${adminToken}`
          },
          body: JSON.stringify({ status: newStatus })
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || 'Failed to update status');

        showToast(`Account status updated to ${newStatus}`, 'success');
        loadEmployeesList();
      } catch (err) {
        showToast(err.message, 'error');
      }
    }
  });
}

async function resendEmployeeInvitation(empId) {
  try {
    const res = await fetch(`${API_BASE_URL}/employees/${empId}/resend-invitation`, {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${adminToken}` }
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Failed to re-issue invitation');

    const invBody = `
      <div style="display: flex; flex-direction: column; gap: 12px;">
        <h4 style="margin: 0;">Fresh Invitation Link Re-issued</h4>
        <p style="font-size: 0.8rem; color: var(--text-secondary); margin: 0;">
          Previous pending invitation was invalidated. The employee can use the link below to activate their account:
        </p>
        <div style="background: var(--bg-subtle); padding: 10px; border-radius: var(--radius-sm); border: 1px solid var(--border-color);">
          <input type="text" readonly value="${data.activation_url}" style="width: 100%; font-size: 0.78rem; font-family: var(--font-mono); padding: 6px 10px; border: 1px solid var(--border-color); background: var(--bg-surface);">
          <button class="btn btn-primary btn-sm" style="margin-top: 8px;" onclick="copyToClipboard('${data.activation_url}')"><i data-lucide="copy"></i> Copy Activation Link</button>
        </div>
        <div style="font-size: 0.74rem; color: var(--text-muted);">${data.delivery_notice}</div>
        <div style="display: flex; justify-content: flex-end;"><button class="btn btn-skin btn-sm" onclick="closeAppModal()">Close</button></div>
      </div>
    `;
    openAppModal('Onboarding Invitation Re-issued', invBody);
    loadEmployeesList();
  } catch (err) {
    showToast(err.message, 'error');
  }
}

function revokeEmployeeInvitation(empId) {
  showConfirmActionModal({
    title: 'Revoke Pending Invitation',
    subtitle: 'Invalidating activation token',
    message: 'Are you sure you want to revoke this pending invitation? The employee will not be able to activate using their link.',
    confirmText: 'Revoke Invitation',
    confirmDanger: true,
    onConfirm: async () => {
      try {
        const res = await fetch(`${API_BASE_URL}/employees/${empId}/revoke-invitation`, {
          method: 'POST',
          headers: { 'Authorization': `Bearer ${adminToken}` }
        });
        if (!res.ok) throw new Error('Failed to revoke invitation');
        showToast('Invitation revoked successfully', 'success');
        loadEmployeesList();
      } catch (err) {
        showToast(err.message, 'error');
      }
    }
  });
}
async function viewEmployeeDetails(empId) {
  try {
    const res = await fetch(`${API_BASE_URL}/employees/${empId}`, {
      headers: { 'Authorization': `Bearer ${adminToken}` }
    });
    if (!res.ok) throw new Error('Failed to load employee details');
    const emp = await res.json();

    const body = `
      <div style="display: flex; flex-direction: column; gap: 14px;">
        <div style="background: var(--bg-subtle); padding: 14px; border-radius: var(--radius-sm); border-left: 3px solid var(--brand-primary);">
          <div style="display: flex; justify-content: space-between; align-items: flex-start;">
            <div>
              <h3 style="margin: 0; font-size: 1.15rem; font-weight: 800;">${emp.full_name}</h3>
              <div style="font-size: 0.78rem; color: var(--text-muted); margin-top: 3px;">
                ID: <strong>${emp.employee_id}</strong> · Username: <strong>@${emp.username}</strong>
              </div>
            </div>
            <span class="status-pill ${emp.employment_status === 'ACTIVE' ? 'active' : 'danger'}">${emp.employment_status}</span>
          </div>
          <div style="font-size: 0.78rem; margin-top: 8px; color: var(--text-secondary);">
            <div><strong>Email:</strong> ${emp.official_email} · <strong>Phone:</strong> ${emp.phone || 'N/A'}</div>
            <div><strong>Department:</strong> ${emp.department_name || 'Unassigned'} · <strong>Designation:</strong> ${emp.designation}</div>
            <div><strong>Reporting Manager:</strong> ${emp.reporting_manager_name || 'None (Independent)'}</div>
          </div>
        </div>

        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px;">
          <div style="background: var(--bg-surface); border: 1px solid var(--border-color); padding: 10px; border-radius: var(--radius-sm);">
            <div style="font-size: 0.72rem; color: var(--text-muted); font-weight: 700;">ACCESS SCOPE</div>
            <div style="font-size: 0.95rem; font-weight: 800; color: var(--brand-primary); margin-top: 4px;">${emp.access_scope}</div>
          </div>
          <div style="background: var(--bg-surface); border: 1px solid var(--border-color); padding: 10px; border-radius: var(--radius-sm);">
            <div style="font-size: 0.72rem; color: var(--text-muted); font-weight: 700;">ASSIGNED ROLE</div>
            <div style="font-size: 0.95rem; font-weight: 800; color: var(--brand-primary); margin-top: 4px;">${emp.role_code}</div>
          </div>
        </div>

        <div>
          <h4 style="font-size: 0.82rem; font-weight: 700; margin-bottom: 6px;">Direct Subordinates (${emp.direct_reports?.length || 0})</h4>
          <div style="max-height: 100px; overflow-y: auto; border: 1px solid var(--border-color); border-radius: var(--radius-sm);">
            ${emp.direct_reports && emp.direct_reports.length ? emp.direct_reports.map(r => `
              <div style="padding: 5px 8px; border-bottom: 1px solid var(--border-subtle); font-size: 0.76rem;">
                <strong>${r.full_name}</strong> · ${r.designation} (${r.employee_id})
              </div>
            `).join('') : '<div style="padding: 10px; font-size: 0.76rem; color: var(--text-muted);">No direct reports assigned.</div>'}
          </div>
        </div>

        <div>
          <h4 style="font-size: 0.82rem; font-weight: 700; margin-bottom: 6px;">Effective Permissions (${emp.effective_permissions?.length || 0})</h4>
          <div style="max-height: 120px; overflow-y: auto; border: 1px solid var(--border-color); border-radius: var(--radius-sm); padding: 8px; display: flex; flex-wrap: wrap; gap: 4px;">
            ${emp.effective_permissions && emp.effective_permissions.length ? emp.effective_permissions.map(p => `
              <span class="badge" style="background: var(--bg-subtle); font-size: 0.70rem; font-family: var(--font-mono);">${p}</span>
            `).join('') : '<span style="font-size: 0.76rem; color: var(--text-muted);">No permissions assigned.</span>'}
          </div>
        </div>
      </div>
    `;
    openAppModal(`Employee Record: ${emp.full_name}`, body);
  } catch (err) {
    showToast(err.message, 'error');
  }
}

function copyToClipboard(text) {
  navigator.clipboard.writeText(text).then(() => {
    showToast('Link copied to clipboard!', 'success');
  }).catch(() => {
    prompt('Copy activation URL:', text);
  });
}


// ==============================================================================
// 26. ROLES & PERMISSIONS MODULE
// ==============================================================================

let allRolesData = [];
let allPermissionsData = [];

async function loadRolesAndPermissions() {
  try {
    const [resR, resP] = await Promise.all([
      fetch(`${API_BASE_URL}/roles`, { headers: { 'Authorization': `Bearer ${adminToken}` } }),
      fetch(`${API_BASE_URL}/permissions`, { headers: { 'Authorization': `Bearer ${adminToken}` } })
    ]);
    if (!resR.ok || !resP.ok) throw new Error('Failed to load roles/permissions');
    allRolesData = await resR.json();
    allPermissionsData = await resP.json();

    const systemTemplates = allRolesData.filter(r => r.is_system);
    const customRoles = allRolesData.filter(r => !r.is_system);

    renderRoleTemplates(systemTemplates);
    renderCustomRolesTable(customRoles);
  } catch (err) {
    console.error("Roles load error:", err);
  }
}

function renderRoleTemplates(systemRoles) {
  const container = document.getElementById('roleTemplatesGrid');
  if (!container) return;

  container.innerHTML = systemRoles.map(r => `
    <div style="background: var(--bg-surface); border: 1px solid var(--border-color); border-radius: var(--radius-md); padding: 16px; display: flex; flex-direction: column; justify-content: space-between; position: relative;">
      <div>
        <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px;">
          <div>
            <span class="font-mono" style="font-size: 0.72rem; color: var(--text-muted); font-weight: 700;">${r.code.toUpperCase()}</span>
            <h4 style="margin: 2px 0 0; font-size: 1.05rem; font-weight: 800; color: var(--text-main);">${r.name}</h4>
          </div>
          <span class="badge" style="background: var(--brand-tint); color: var(--brand-primary); font-size: 0.70rem; font-weight: 700;">SYSTEM</span>
        </div>
        <p style="font-size: 0.80rem; color: var(--text-secondary); line-height: 1.45; margin-bottom: 12px;">
          ${r.description}
        </p>
      </div>

      <div>
        <div style="font-size: 0.72rem; font-weight: 700; color: var(--text-muted); margin-bottom: 6px; display: flex; justify-content: space-between;">
          <span>GRANTED PERMISSIONS</span>
          <span><strong>${r.permissions?.length || 0}</strong> rules</span>
        </div>
        <div style="max-height: 75px; overflow-y: auto; background: var(--bg-subtle); padding: 6px; border-radius: var(--radius-sm); font-size: 0.68rem; font-family: var(--font-mono); display: flex; flex-wrap: wrap; gap: 4px;">
          ${r.permissions?.map(p => `<span style="background: var(--bg-surface); padding: 1px 5px; border-radius: 3px; border: 1px solid var(--border-subtle);">${p}</span>`).join('') || ''}
        </div>
        <div style="margin-top: 10px; font-size: 0.74rem; color: var(--text-muted); display: flex; justify-content: space-between; align-items: center;">
          <span>Active Users: <strong>${r.user_count || 0}</strong></span>
          <span style="font-size: 0.70rem; color: var(--brand-primary);"><i data-lucide="lock" style="width: 12px; height: 12px; display: inline-block;"></i> Protected Template</span>
        </div>
      </div>
    </div>
  `).join('');

  if (window.lucide) lucide.createIcons();
}

function renderCustomRolesTable(customRoles) {
  const tbody = document.getElementById('customRolesTableBody');
  if (!tbody) return;

  if (!customRoles.length) {
    tbody.innerHTML = '<tr><td colspan="6"><div class="honest-empty-state"><i data-lucide="key-round"></i><h4>No Custom Roles Created</h4><p>Create tailor-made operational roles for specific organizational requirements.</p></div></td></tr>';
    if (window.lucide) lucide.createIcons();
    return;
  }

  tbody.innerHTML = customRoles.map(r => `
    <tr>
      <td><strong>${r.name}</strong></td>
      <td><span class="font-mono" style="font-size: 0.75rem;">${r.code}</span></td>
      <td><span style="font-size: 0.8rem; color: var(--text-secondary);">${r.description || 'Custom role'}</span></td>
      <td><span class="badge" style="background: var(--brand-tint); color: var(--brand-primary); font-size: 0.72rem;">${r.permissions?.length || 0} permissions</span></td>
      <td><strong>${r.user_count || 0}</strong> employees</td>
      <td>
        <div class="row-action-dropdown">
          <button type="button" class="action-dots-trigger" onclick="toggleRowActionMenu(event, 'role-${r.id}')" title="Actions" aria-label="Role Actions">
            <i data-lucide="more-vertical"></i>
          </button>
          <div class="row-action-menu hidden" id="row-action-menu-role-${r.id}">
            <button type="button" class="row-action-item" onclick="openEditCustomRoleModal('${r.id}'); closeAllRowActionMenus();">
              <i data-lucide="edit-2"></i> <span>Edit Custom Role</span>
            </button>
            <div class="row-action-divider"></div>
            <button type="button" class="row-action-item danger-item" onclick="deleteCustomRole('${r.id}'); closeAllRowActionMenus();">
              <i data-lucide="trash-2"></i> <span>Delete Custom Role</span>
            </button>
          </div>
        </div>
      </td>
    </tr>
  `).join('');

  if (window.lucide) lucide.createIcons();
}

function openCreateCustomRoleModal() {
  // Group permissions by category
  const categories = {};
  allPermissionsData.forEach(p => {
    if (!categories[p.category]) categories[p.category] = [];
    categories[p.category].push(p);
  });

  const catHtml = Object.keys(categories).map(cat => `
    <div style="margin-bottom: 12px; border: 1px solid var(--border-color); border-radius: var(--radius-sm); padding: 10px;">
      <div style="font-weight: 700; font-size: 0.82rem; color: var(--brand-primary); margin-bottom: 8px;">${cat}</div>
      <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 6px;">
        ${categories[cat].map(p => `
          <label style="display: flex; align-items: flex-start; gap: 6px; font-size: 0.74rem; cursor: pointer;">
            <input type="checkbox" name="customRolePerms" value="${p.code}" style="margin-top: 2px;">
            <div>
              <div style="font-weight: 600;">${p.name}</div>
              <div style="font-size: 0.68rem; color: var(--text-muted); font-family: var(--font-mono);">${p.code}</div>
            </div>
          </label>
        `).join('')}
      </div>
    </div>
  `).join('');

  const body = `
    <form id="createRoleForm" onsubmit="submitCreateCustomRole(event)" style="display: flex; flex-direction: column; gap: 12px; max-height: 520px; overflow-y: auto;">
      <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px;">
        <div class="form-group">
          <label style="font-size: 0.8rem; font-weight: 700;">Role Name *</label>
          <input type="text" id="customRoleName" required placeholder="e.g. Regional Field Supervisor" style="width: 100%; padding: 8px 10px; border-radius: var(--radius-sm); border: 1px solid var(--border-color);">
        </div>
        <div class="form-group">
          <label style="font-size: 0.8rem; font-weight: 700;">Role Code (Lowercase) *</label>
          <input type="text" id="customRoleCode" required placeholder="e.g. reg_supervisor" style="width: 100%; padding: 8px 10px; border-radius: var(--radius-sm); border: 1px solid var(--border-color); text-transform: lowercase;">
        </div>
      </div>
      <div class="form-group">
        <label style="font-size: 0.8rem; font-weight: 700;">Description</label>
        <textarea id="customRoleDesc" rows="2" placeholder="Responsibilities and access scope..." style="width: 100%; padding: 8px 10px; border-radius: var(--radius-sm); border: 1px solid var(--border-color);"></textarea>
      </div>

      <div>
        <label style="font-size: 0.8rem; font-weight: 700; margin-bottom: 6px; display: block;">Select Permitted Operations (Deny-by-default):</label>
        ${catHtml}
      </div>

      <div style="display: flex; justify-content: flex-end; gap: 8px; margin-top: 10px;">
        <button type="button" class="btn btn-skin btn-sm" onclick="closeAppModal()">Cancel</button>
        <button type="submit" class="btn btn-primary btn-sm"><i data-lucide="plus"></i> Create Custom Role</button>
      </div>
    </form>
  `;
  openAppModal('Create Custom Role with Fine-Grained Permissions', body);
}

async function submitCreateCustomRole(e) {
  e.preventDefault();
  const name = document.getElementById('customRoleName').value.trim();
  const code = document.getElementById('customRoleCode').value.trim().toLowerCase();
  const description = document.getElementById('customRoleDesc').value.trim();
  
  const checkedBoxes = document.querySelectorAll('input[name="customRolePerms"]:checked');
  const permissions = Array.from(checkedBoxes).map(cb => cb.value);

  try {
    const res = await fetch(`${API_BASE_URL}/roles`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${adminToken}`
      },
      body: JSON.stringify({ name, code, description, permissions })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Failed to create role');

    showToast(`Custom role '${name}' created!`, 'success');
    closeAppModal();
    loadRolesAndPermissions();
  } catch (err) {
    showToast(err.message, 'error');
  }
}

function openEditCustomRoleModal(roleId) {
  const role = allRolesData.find(r => r.id === roleId);
  if (!role) return;

  const categories = {};
  allPermissionsData.forEach(p => {
    if (!categories[p.category]) categories[p.category] = [];
    categories[p.category].push(p);
  });

  const catHtml = Object.keys(categories).map(cat => `
    <div style="margin-bottom: 12px; border: 1px solid var(--border-color); border-radius: var(--radius-sm); padding: 10px;">
      <div style="font-weight: 700; font-size: 0.82rem; color: var(--brand-primary); margin-bottom: 8px;">${cat}</div>
      <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 6px;">
        ${categories[cat].map(p => `
          <label style="display: flex; align-items: flex-start; gap: 6px; font-size: 0.74rem; cursor: pointer;">
            <input type="checkbox" name="editRolePerms" value="${p.code}" ${role.permissions?.includes(p.code) ? 'checked' : ''} style="margin-top: 2px;">
            <div>
              <div style="font-weight: 600;">${p.name}</div>
              <div style="font-size: 0.68rem; color: var(--text-muted); font-family: var(--font-mono);">${p.code}</div>
            </div>
          </label>
        `).join('')}
      </div>
    </div>
  `).join('');

  const body = `
    <form id="editRoleForm" onsubmit="submitEditCustomRole(event, '${role.id}')" style="display: flex; flex-direction: column; gap: 12px; max-height: 520px; overflow-y: auto;">
      <div class="form-group">
        <label style="font-size: 0.8rem; font-weight: 700;">Role Name *</label>
        <input type="text" id="editRoleName" value="${role.name}" required style="width: 100%; padding: 8px 10px; border-radius: var(--radius-sm); border: 1px solid var(--border-color);">
      </div>
      <div class="form-group">
        <label style="font-size: 0.8rem; font-weight: 700;">Description</label>
        <textarea id="editRoleDesc" rows="2" style="width: 100%; padding: 8px 10px; border-radius: var(--radius-sm); border: 1px solid var(--border-color);">${role.description || ''}</textarea>
      </div>

      <div>
        <label style="font-size: 0.8rem; font-weight: 700; margin-bottom: 6px; display: block;">Permitted Operations:</label>
        ${catHtml}
      </div>

      <div style="display: flex; justify-content: flex-end; gap: 8px; margin-top: 10px;">
        <button type="button" class="btn btn-skin btn-sm" onclick="closeAppModal()">Cancel</button>
        <button type="submit" class="btn btn-primary btn-sm"><i data-lucide="check"></i> Save Changes</button>
      </div>
    </form>
  `;
  openAppModal(`Edit Role: ${role.name}`, body);
}

async function submitEditCustomRole(e, roleId) {
  e.preventDefault();
  const name = document.getElementById('editRoleName').value.trim();
  const description = document.getElementById('editRoleDesc').value.trim();

  const checkedBoxes = document.querySelectorAll('input[name="editRolePerms"]:checked');
  const permissions = Array.from(checkedBoxes).map(cb => cb.value);

  try {
    const res = await fetch(`${API_BASE_URL}/roles/${roleId}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${adminToken}`
      },
      body: JSON.stringify({ name, description, permissions })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Failed to update role');

    showToast('Role updated successfully', 'success');
    closeAppModal();
    loadRolesAndPermissions();
  } catch (err) {
    showToast(err.message, 'error');
  }
}

function deleteCustomRole(roleId) {
  showConfirmActionModal({
    title: 'Delete Custom Role',
    subtitle: 'Permanent permission template removal',
    message: 'Are you sure you want to delete this custom role? This action cannot be undone and any assigned users will lose associated custom permissions.',
    confirmText: 'Delete Custom Role',
    confirmDanger: true,
    onConfirm: async () => {
      try {
        const res = await fetch(`${API_BASE_URL}/roles/${roleId}`, {
          method: 'DELETE',
          headers: { 'Authorization': `Bearer ${adminToken}` }
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || 'Failed to delete role');

        showToast('Custom role deleted', 'success');
        loadRolesAndPermissions();
      } catch (err) {
        showToast(err.message, 'error');
      }
    }
  });
}


// ==============================================================================
// 27. DEPARTMENTS & TEAMS MODULE
// ==============================================================================

let allDepartmentsData = [];

async function loadDepartmentsList() {
  const tbody = document.getElementById('departmentsTableBody');
  if (!tbody) return;

  try {
    const res = await fetch(`${API_BASE_URL}/departments`, {
      headers: { 'Authorization': `Bearer ${adminToken}` }
    });
    if (!res.ok) throw new Error('Failed to load departments');
    allDepartmentsData = await res.json();

    // Populate department dropdown filter in Employees section
    const empDeptFilter = document.getElementById('empDeptFilter');
    if (empDeptFilter) {
      empDeptFilter.innerHTML = '<option value="">All Departments</option>' + allDepartmentsData.map(d => `<option value="${d.id}">${d.name}</option>`).join('');
    }

    renderDepartmentsTable(allDepartmentsData);
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="6" style="text-align: center; color: var(--status-danger); padding: 24px;">Failed to load departments: ${err.message}</td></tr>`;
  }
}

function renderDepartmentsTable(depts) {
  const tbody = document.getElementById('departmentsTableBody');
  if (!tbody) return;

  if (!depts.length) {
    tbody.innerHTML = '<tr><td colspan="7"><div class="honest-empty-state"><i data-lucide="network"></i><h4>No Departments Registered</h4><p>Create departments to structure teams and managerial hierarchy.</p></div></td></tr>';
    if (window.lucide) lucide.createIcons();
    if (window.SetuTableManager) SetuTableManager.syncTable('departmentsTable');
    return;
  }

  tbody.innerHTML = depts.map(d => `
    <tr data-id="${d.id}">
      <td class="td-bulk-select" style="text-align: center; width: 44px;">
        <input type="checkbox" class="row-select-checkbox" data-row-id="${d.id}" aria-label="Select Department" onchange="SetuTableManager.handleRowCheck('departmentsTable', '${d.id}', this)">
      </td>
      <td style="max-width: 280px;">
        <div style="font-weight: 700; color: var(--text-main); font-size: 0.88rem; line-height: 1.3;">${escapeHtml(d.name)}</div>
        <div style="font-size: 0.74rem; color: var(--text-muted); line-height: 1.3; margin-top: 2px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;" title="${escapeHtml(d.description || '')}">${escapeHtml(d.description || 'Operational team')}</div>
      </td>
      <td><span class="font-mono" style="background: var(--bg-subtle); padding: 2px 8px; border-radius: 4px; font-weight: 700; font-size: 0.75rem;">${escapeHtml(d.code)}</span></td>
      <td>
        <span style="font-size: 0.82rem; font-weight: 600;">${d.head_name ? `<i data-lucide="user-check" style="width: 13px; height: 13px; display: inline-block; vertical-align: middle; margin-right: 4px; color: var(--brand-primary);"></i> ${escapeHtml(d.head_name)}` : '<em style="color:var(--text-muted);">Vacant</em>'}</span>
      </td>
      <td style="font-size: 0.82rem;"><strong>${d.employee_count || 0}</strong> employees</td>
      <td>
        <span class="status-pill ${d.status === 'ACTIVE' ? 'active' : 'danger'}">${escapeHtml(d.status)}</span>
      </td>
      <td style="text-align: center;">
        <div class="row-action-dropdown">
          <button type="button" class="action-dots-trigger" onclick="toggleRowActionMenu(event, 'dept-${d.id}')" title="Actions" aria-label="Department Actions">
            <i data-lucide="more-vertical"></i>
          </button>
          <div class="row-action-menu hidden" id="row-action-menu-dept-${d.id}">
            <button type="button" class="row-action-item" onclick="viewDepartmentMembers('${d.id}'); closeAllRowActionMenus();">
              <i data-lucide="users"></i> <span>View Assigned Personnel</span>
            </button>
            <button type="button" class="row-action-item" onclick="openEditDeptModal('${d.id}'); closeAllRowActionMenus();">
              <i data-lucide="edit-2"></i> <span>Edit Department</span>
            </button>
            <div class="row-action-divider"></div>
            <button type="button" class="row-action-item danger-item" onclick="deleteDepartment('${d.id}'); closeAllRowActionMenus();">
              <i data-lucide="trash-2"></i> <span>Delete Department</span>
            </button>
          </div>
        </div>
      </td>
    </tr>
  `).join('');

  if (window.SetuTableManager) SetuTableManager.syncTable('departmentsTable');
  if (window.lucide) lucide.createIcons();
}

async function openCreateDeptModal() {
  let potentialHeads = [];
  try {
    const res = await fetch(`${API_BASE_URL}/employees?limit=100`, { headers: { 'Authorization': `Bearer ${adminToken}` } });
    if (res.ok) {
      const data = await res.json();
      potentialHeads = data.employees || [];
    }
  } catch (e) {
    console.error(e);
  }

  const headOptions = '<option value="">None / Open Position</option>' + potentialHeads.map(h => `<option value="${h.id}">${h.full_name} (${h.designation})</option>`).join('');

  const body = `
    <form id="createDeptForm" onsubmit="submitCreateDept(event)" style="display: flex; flex-direction: column; gap: 12px;">
      <div style="display: grid; grid-template-columns: 2fr 1fr; gap: 10px;">
        <div class="form-group">
          <label style="font-size: 0.8rem; font-weight: 700;">Department Name *</label>
          <input type="text" id="deptName" required placeholder="e.g. Field Operations & Shed Services" style="width: 100%; padding: 8px 10px; border-radius: var(--radius-sm); border: 1px solid var(--border-color);">
        </div>
        <div class="form-group">
          <label style="font-size: 0.8rem; font-weight: 700;">Code *</label>
          <input type="text" id="deptCode" required placeholder="e.g. OPS" style="width: 100%; padding: 8px 10px; border-radius: var(--radius-sm); border: 1px solid var(--border-color); text-transform: uppercase;">
        </div>
      </div>
      <div class="form-group">
        <label style="font-size: 0.8rem; font-weight: 700;">Head of Department</label>
        <select id="deptHeadId" style="width: 100%; padding: 8px 10px; border-radius: var(--radius-sm); border: 1px solid var(--border-color);">
          ${headOptions}
        </select>
      </div>
      <div class="form-group">
        <label style="font-size: 0.8rem; font-weight: 700;">Description</label>
        <textarea id="deptDesc" rows="2" placeholder="Responsibilities and functional mandate..." style="width: 100%; padding: 8px 10px; border-radius: var(--radius-sm); border: 1px solid var(--border-color);"></textarea>
      </div>
      <div style="display: flex; justify-content: flex-end; gap: 8px; margin-top: 10px;">
        <button type="button" class="btn btn-skin btn-sm" onclick="closeAppModal()">Cancel</button>
        <button type="submit" class="btn btn-primary btn-sm"><i data-lucide="plus"></i> Create Department</button>
      </div>
    </form>
  `;
  openAppModal('Create New Department', body);
}

async function submitCreateDept(e) {
  e.preventDefault();
  const name = document.getElementById('deptName').value.trim();
  const code = document.getElementById('deptCode').value.trim().toUpperCase();
  const head_id = document.getElementById('deptHeadId').value || null;
  const description = document.getElementById('deptDesc').value.trim();

  try {
    const res = await fetch(`${API_BASE_URL}/departments`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${adminToken}`
      },
      body: JSON.stringify({ name, code, head_id, description })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Failed to create department');

    showToast(`Department '${name}' created!`, 'success');
    closeAppModal();
    loadDepartmentsList();
  } catch (err) {
    showToast(err.message, 'error');
  }
}

async function openEditDeptModal(deptId) {
  const dept = allDepartmentsData.find(d => d.id === deptId);
  if (!dept) return;

  let potentialHeads = [];
  try {
    const res = await fetch(`${API_BASE_URL}/employees?limit=100`, { headers: { 'Authorization': `Bearer ${adminToken}` } });
    if (res.ok) {
      const data = await res.json();
      potentialHeads = data.employees || [];
    }
  } catch (e) {
    console.error(e);
  }

  const headOptions = '<option value="">None / Vacant</option>' + potentialHeads.map(h => `<option value="${h.id}" ${dept.head_id === h.id ? 'selected' : ''}>${h.full_name} (${h.designation})</option>`).join('');

  const body = `
    <form id="editDeptForm" onsubmit="submitEditDept(event, '${dept.id}')" style="display: flex; flex-direction: column; gap: 12px;">
      <div class="form-group">
        <label style="font-size: 0.8rem; font-weight: 700;">Department Name *</label>
        <input type="text" id="editDeptName" value="${dept.name}" required style="width: 100%; padding: 8px 10px; border-radius: var(--radius-sm); border: 1px solid var(--border-color);">
      </div>
      <div class="form-group">
        <label style="font-size: 0.8rem; font-weight: 700;">Head of Department</label>
        <select id="editDeptHead" style="width: 100%; padding: 8px 10px; border-radius: var(--radius-sm); border: 1px solid var(--border-color);">
          ${headOptions}
        </select>
      </div>
      <div class="form-group">
        <label style="font-size: 0.8rem; font-weight: 700;">Description</label>
        <textarea id="editDeptDesc" rows="2" style="width: 100%; padding: 8px 10px; border-radius: var(--radius-sm); border: 1px solid var(--border-color);">${dept.description || ''}</textarea>
      </div>
      <div style="display: flex; justify-content: flex-end; gap: 8px; margin-top: 10px;">
        <button type="button" class="btn btn-skin btn-sm" onclick="closeAppModal()">Cancel</button>
        <button type="submit" class="btn btn-primary btn-sm"><i data-lucide="check"></i> Save Changes</button>
      </div>
    </form>
  `;
  openAppModal(`Edit Department: ${dept.name}`, body);
}

async function submitEditDept(e, deptId) {
  e.preventDefault();
  const name = document.getElementById('editDeptName').value.trim();
  const head_id = document.getElementById('editDeptHead').value || null;
  const description = document.getElementById('editDeptDesc').value.trim();

  try {
    const res = await fetch(`${API_BASE_URL}/departments/${deptId}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${adminToken}`
      },
      body: JSON.stringify({ name, head_id, description })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Failed to update department');

    showToast('Department updated', 'success');
    closeAppModal();
    loadDepartmentsList();
  } catch (err) {
    showToast(err.message, 'error');
  }
}

async function viewDepartmentMembers(deptId) {
  try {
    const res = await fetch(`${API_BASE_URL}/departments/${deptId}`, {
      headers: { 'Authorization': `Bearer ${adminToken}` }
    });
    if (!res.ok) throw new Error('Failed to load department members');
    const dept = await res.json();

    const body = `
      <div style="display: flex; flex-direction: column; gap: 12px;">
        <div style="background: var(--bg-subtle); padding: 12px; border-radius: var(--radius-sm); border-left: 3px solid var(--brand-primary);">
          <h4 style="margin: 0; font-size: 1.05rem;">${dept.name} (${dept.code})</h4>
          <p style="font-size: 0.78rem; color: var(--text-muted); margin: 3px 0 0;">${dept.description || 'Organizational team'}</p>
          <div style="font-size: 0.78rem; margin-top: 6px;"><strong>Head:</strong> ${dept.head_name || 'Vacant'} · <strong>Members:</strong> ${dept.members?.length || 0}</div>
        </div>

        <h4 style="font-size: 0.82rem; font-weight: 700; margin-bottom: 4px;">Assigned Personnel</h4>
        <div style="max-height: 220px; overflow-y: auto; border: 1px solid var(--border-color); border-radius: var(--radius-sm);">
          ${dept.members && dept.members.length ? dept.members.map(m => `
            <div style="display: flex; justify-content: space-between; align-items: center; padding: 8px 12px; border-bottom: 1px solid var(--border-subtle); font-size: 0.78rem;">
              <div>
                <strong>${m.full_name}</strong> (${m.employee_id})
                <div style="font-size: 0.72rem; color: var(--text-muted);">${m.official_email} · ${m.designation}</div>
              </div>
              <span class="badge" style="background: var(--brand-tint); color: var(--brand-primary); font-size: 0.70rem;">${m.role_code}</span>
            </div>
          `).join('') : '<div style="padding: 16px; font-size: 0.8rem; color: var(--text-muted); text-align: center;">No employees currently assigned to this department.</div>'}
        </div>
      </div>
    `;
    openAppModal(`Department Roster: ${dept.name}`, body);
  } catch (err) {
    showToast(err.message, 'error');
  }
}

function deleteDepartment(deptId) {
  showConfirmActionModal({
    title: 'Delete Department',
    subtitle: 'Permanent department removal',
    message: 'Are you sure you want to delete this department? All employees must be reassigned first.',
    confirmText: 'Delete Department',
    confirmDanger: true,
    onConfirm: async () => {
      try {
        const res = await fetch(`${API_BASE_URL}/departments/${deptId}`, {
          method: 'DELETE',
          headers: { 'Authorization': `Bearer ${adminToken}` }
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || 'Failed to delete department');

        showToast('Department removed successfully', 'success');
        loadDepartmentsList();
      } catch (err) {
        showToast(err.message, 'error');
      }
    }
  });
}


// ==============================================================================
// 28. ACCESS & AUDIT LOGS MODULE
// ==============================================================================

let auditSearchTimeout = null;

function debounceFilterAudit(val) {
  clearTimeout(auditSearchTimeout);
  auditSearchTimeout = setTimeout(() => {
    loadAuditRecords(val);
  }, 250);
}

async function loadAuditRecords(search = '') {
  const tbody = document.getElementById('auditTableBody');
  if (!tbody) return;

  const actionFilter = document.getElementById('auditActionFilter')?.value || '';
  let url = `${API_BASE_URL}/admin/audit-logs?limit=50`;
  if (search) url += `&search=${encodeURIComponent(search)}`;
  if (actionFilter) url += `&action=${encodeURIComponent(actionFilter)}`;

  try {
    const res = await fetch(url, {
      headers: { 'Authorization': `Bearer ${adminToken}` }
    });
    if (!res.ok) throw new Error('Failed to load audit records');
    const records = await res.json();
    renderAuditTable(records);
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="6" style="text-align: center; color: var(--status-danger); padding: 24px;">Failed to load audit logs: ${err.message}</td></tr>`;
  }
}

function renderAuditTable(records) {
  const tbody = document.getElementById('auditTableBody');
  if (!tbody) return;

  if (!records.length) {
    tbody.innerHTML = '<tr><td colspan="6"><div class="honest-empty-state"><i data-lucide="shield-check"></i><h4>No Audit Records Found</h4><p>No audit events match the selected criteria.</p></div></td></tr>';
    if (window.lucide) lucide.createIcons();
    return;
  }

  tbody.innerHTML = records.map(r => `
    <tr>
      <td style="font-family: var(--font-mono); font-size: 0.72rem; color: var(--text-muted); white-space: nowrap;">
        ${new Date(r.timestamp).toLocaleString()}
      </td>
      <td>
        <span style="font-weight: 700; color: var(--text-main); font-size: 0.8rem;">@${r.actor}</span>
      </td>
      <td>
        <span class="badge" style="background: var(--bg-subtle); color: var(--text-main); font-family: var(--font-mono); font-size: 0.70rem; font-weight: 700;">
          ${r.action}
        </span>
      </td>
      <td>
        <span class="font-mono" style="font-size: 0.72rem; color: var(--brand-primary);">${r.target_resource || 'system'}</span>
      </td>
      <td>
        <span style="font-size: 0.78rem; color: var(--text-secondary); line-height: 1.4;">${r.details}</span>
      </td>
      <td>
        <span class="font-mono" style="font-size: 0.70rem; color: var(--text-muted);">${r.ip_address || '127.0.0.1'}</span>
      </td>
    </tr>
  `).join('');

  if (window.lucide) lucide.createIcons();
}


// ==============================================================================
// 29. ONBOARDING INVITATION TOKEN ACTIVATION
// ==============================================================================

let pendingInvitationToken = null;

async function checkAndOpenInvitationModal(token) {
  pendingInvitationToken = token;
  const modal = document.getElementById('invitationActivationModal');
  const loading = document.getElementById('invitationVerifyLoading');
  const errorEl = document.getElementById('invitationVerifyError');
  const form = document.getElementById('invitationActivationForm');

  if (!modal) return;
  modal.classList.remove('hidden');
  loading.classList.remove('hidden');
  errorEl.classList.add('hidden');
  form.classList.add('hidden');

  try {
    const res = await fetch(`${API_BASE_URL}/auth/invitations/${token}`);
    const data = await res.json();
    loading.classList.add('hidden');

    if (!res.ok) {
      errorEl.textContent = data.detail || 'This invitation is invalid or has expired.';
      errorEl.classList.remove('hidden');
      return;
    }

    document.getElementById('invModalName').textContent = data.full_name;
    document.getElementById('invModalEmail').textContent = data.email;
    document.getElementById('invModalOrg').textContent = data.organization_name;
    document.getElementById('invModalRole').textContent = data.role_code.toUpperCase();

    form.classList.remove('hidden');
  } catch (err) {
    loading.classList.add('hidden');
    errorEl.textContent = 'Network error while verifying invitation token.';
    errorEl.classList.remove('hidden');
  }
}

async function handleAcceptInvitation(e) {
  e.preventDefault();
  const password = document.getElementById('invPassword').value;
  const confirmPassword = document.getElementById('invConfirmPassword').value;
  const mfaEnabled = document.getElementById('invMfaCheckbox').checked;
  const errorEl = document.getElementById('invitationVerifyError');
  const btn = document.getElementById('btnActivateAccount');

  if (password !== confirmPassword) {
    errorEl.textContent = 'Passwords do not match. Please re-enter.';
    errorEl.classList.remove('hidden');
    return;
  }

  errorEl.classList.add('hidden');
  btn.disabled = true;
  btn.innerHTML = '<span>Activating Account...</span>';

  try {
    const res = await fetch(`${API_BASE_URL}/auth/invitations/${pendingInvitationToken}/accept`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ password, mfa_enabled: mfaEnabled })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Failed to activate account');

    showToast('Account activated successfully! You may now sign in.', 'success');
    closeInvitationModal();

    // Clear hash
    window.location.hash = '';

    // Switch to login view and prefill username
    showAuthView();
    const unameInput = document.getElementById('username');
    if (unameInput) unameInput.value = data.username;
    const pwdInput = document.getElementById('password');
    if (pwdInput) pwdInput.value = '';
  } catch (err) {
    errorEl.textContent = err.message;
    errorEl.classList.remove('hidden');
  } finally {
    btn.disabled = false;
    btn.innerHTML = '<i data-lucide="shield-check"></i> Complete Activation & Proceed to Login';
    if (window.lucide) lucide.createIcons();
  }
}

function closeInvitationModal() {
  const modal = document.getElementById('invitationActivationModal');
  if (modal) modal.classList.add('hidden');
}


// ==============================================================================
// ACTIVE SESSIONS MANAGEMENT MODAL & CONTROLS
// ==============================================================================

async function openActiveSessionsModal() {
  try {
    const res = await fetch(`${API_BASE_URL}/auth/sessions`, {
      headers: { 'Authorization': `Bearer ${adminToken}` }
    });
    if (!res.ok) throw new Error('Could not load active sessions');
    const data = await res.json();
    const sessions = data.sessions || [];

    let bodyHtml = `
      <div style="font-size: 0.82rem; color: var(--text-muted); margin-bottom: 16px; line-height: 1.5;">
        Every browser tab maintains its own isolated cryptographic session context. You can open multiple Setu tabs simultaneously in the same browser profile and operate with different accounts without interference.
      </div>
      <div style="max-height: 340px; overflow-y: auto; display: flex; flex-direction: column; gap: 8px;">
    `;

    sessions.forEach(s => {
      const isCur = s.is_current;
      const created = new Date(s.created_at).toLocaleString();
      const lastAct = new Date(s.last_activity).toLocaleTimeString();
      bodyHtml += `
        <div style="padding: 12px; border-radius: var(--radius-sm); border: 1px solid ${isCur ? 'var(--emerald-500)' : 'var(--skin-border)'}; background: ${isCur ? 'rgba(16, 185, 129, 0.05)' : 'var(--skin-bg-alt)'}; display: flex; justify-content: space-between; align-items: center;">
          <div>
            <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 4px;">
              <span style="font-weight: 700; font-size: 0.82rem; color: var(--text-main); font-family: monospace;">${s.session_id.substring(0, 16)}...</span>
              ${isCur ? '<span style="background: var(--emerald-500); color: #fff; font-size: 0.65rem; font-weight: 700; padding: 2px 6px; border-radius: 4px;">CURRENT TAB</span>' : '<span style="background: var(--skin-border); color: var(--text-muted); font-size: 0.65rem; font-weight: 600; padding: 2px 6px; border-radius: 4px;">OTHER TAB / DEVICE</span>'}
            </div>
            <div style="font-size: 0.72rem; color: var(--text-muted);">
              Created: ${created} · Last Active: ${lastAct}
            </div>
          </div>
          <div>
            ${!isCur ? `<button class="btn btn-outline btn-xs" onclick="revokeSessionRemote('${s.session_id}')" style="color: #ef4444; border-color: rgba(239, 68, 68, 0.3);">Revoke</button>` : '<span style="font-size: 0.75rem; color: var(--emerald-500); font-weight: 600;">Active Now</span>'}
          </div>
        </div>
      `;
    });

    bodyHtml += `
      </div>
      <div style="margin-top: 16px; display: flex; justify-content: space-between; align-items: center; border-top: 1px solid var(--skin-border); padding-top: 12px;">
        <button class="btn btn-danger btn-sm" onclick="handleLogoutAll()">Sign Out All Sessions</button>
        <button class="btn btn-skin btn-sm" onclick="closeAppModal()">Close</button>
      </div>
    `;

    openAppModal('Active Independent Sessions', bodyHtml);
  } catch (err) {
    showToast(`Failed to load sessions: ${err.message}`, 'error');
  }
}

async function revokeSessionRemote(sessId) {
  try {
    const res = await fetch(`${API_BASE_URL}/auth/sessions/${sessId}/revoke`, {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${adminToken}` }
    });
    if (!res.ok) throw new Error('Failed to revoke session');
    showToast('Remote session revoked successfully', 'success');
    openActiveSessionsModal();
  } catch (err) {
    showToast(err.message, 'error');
  }
}

function handleLogoutAll() {
  showConfirmActionModal({
    title: 'Sign Out Everywhere',
    subtitle: 'Revoking all active sessions',
    message: 'Are you sure you want to sign out of all sessions across all tabs and devices? You will be redirected to the login screen.',
    confirmText: 'Sign Out Everywhere',
    confirmDanger: true,
    onConfirm: async () => {
      try {
        await fetch(`${API_BASE_URL}/auth/logout-all`, {
          method: 'POST',
          headers: { 'Authorization': `Bearer ${adminToken}` }
        });
        closeAppModal();
        handleLogout('All sessions successfully revoked.');
      } catch (err) {
        showToast(`Logout-all failed: ${err.message}`, 'error');
      }
    }
  });
}


// ==============================================================================
// 21 ENTERPRISE PLATFORM DATA LOADERS & WORKFLOW HANDLERS
// ==============================================================================

let allProductsList = [];
let allOrdersList = [];
let allSubsList = [];
let allInvoicesList = [];

// ------------------------------------------------------------------------------
// 1. PRODUCTS & HARDWARE CATALOGUE
// ------------------------------------------------------------------------------
async function loadProducts(statusFilter = 'ALL') {
  const tbody = document.getElementById('productsTableBody');
  if (!tbody) return;
  tbody.innerHTML = '<tr><td colspan="8" style="text-align: center; padding: 24px;">Loading catalogue...</td></tr>';

  try {
    const token = window.adminToken || TAB_STORAGE.getItem('setu_tab_token') || localStorage.getItem('setu_token') || '';
    let res = null;
    if (token) {
      res = await fetch(`${API_BASE_URL}/products`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
    }
    if (!res || !res.ok) {
      res = await fetch(`${API_BASE_URL}/public/products`);
    }
    if (!res.ok) throw new Error(`HTTP ${res.status}: Failed to load products`);
    allProductsList = await res.json();
    filterProducts(statusFilter);
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="8" style="text-align: center; color: var(--rose); padding: 24px;">Failed to load products: ${escapeHtml(err.message)}</td></tr>`;
    if (window.SetuTableManager) SetuTableManager.syncTable('productsTable');
  }
}

function filterProducts(status = 'ALL') {
  const tbody = document.getElementById('productsTableBody');
  if (!tbody) return;

  let filtered = allProductsList;
  if (status === 'ACTIVE') {
    filtered = allProductsList.filter(p => p.is_active && p.publication_status !== 'ARCHIVED');
  } else if (status === 'ARCHIVED') {
    filtered = allProductsList.filter(p => !p.is_active || p.publication_status === 'ARCHIVED');
  }

  if (filtered.length === 0) {
    tbody.innerHTML = `<tr><td colspan="8" style="text-align: center; padding: 36px; color: var(--text-muted);">
      <div style="font-size: 1.1rem; font-weight: 600; margin-bottom: 6px;">No Products Found</div>
      <div>No hardware products match the selected criteria.</div>
    </td></tr>`;
    if (window.SetuTableManager) SetuTableManager.syncTable('productsTable');
    return;
  }

  tbody.innerHTML = filtered.map(p => {
    const priceFormatted = (p.price_minor_units / 100).toLocaleString('en-IN', { minimumFractionDigits: 2 });
    const isArchived = !p.is_active || p.publication_status === 'ARCHIVED';
    const statusBadge = isArchived
      ? '<span class="badge badge-warning">ARCHIVED</span>'
      : (p.publication_status === 'DRAFT'
          ? '<span class="badge badge-secondary">DRAFT</span>'
          : '<span class="badge badge-success">ACTIVE</span>');
    const imgUrl = (p.images && p.images.length > 0) ? p.images[0] : null;

    return `
      <tr data-id="${p.id}">
        <td class="td-bulk-select" style="text-align: center;">
          <input type="checkbox" class="row-select-checkbox" data-row-id="${p.id}" aria-label="Select Product" onchange="SetuTableManager.handleRowCheck('productsTable', '${p.id}', this)">
        </td>
        <td style="font-family: var(--font-mono); font-size: 0.8rem; font-weight: 600;">${escapeHtml(p.sku)}</td>
        <td>
          <div style="display: flex; align-items: center; gap: 10px;">
            ${imgUrl ? `<img src="${imgUrl}" alt="${escapeHtml(p.name)}" style="width: 36px; height: 36px; border-radius: 6px; object-fit: cover; border: 1px solid var(--border-color); flex-shrink: 0;">` : `<div style="width: 36px; height: 36px; border-radius: 6px; background: rgba(0,0,0,0.04); display: flex; align-items: center; justify-content: center; color: var(--text-muted); flex-shrink: 0;"><i data-lucide="package" style="width: 18px; height: 18px;"></i></div>`}
            <div>
              <div style="font-weight: 700; color: var(--text-main);">${escapeHtml(p.name)}</div>
              ${p.short_description ? `<div style="font-size: 0.74rem; color: var(--text-muted); line-height: 1.2;">${escapeHtml(p.short_description.substring(0, 50))}...</div>` : ''}
            </div>
          </div>
        </td>
        <td><span style="font-size: 0.8rem;">${escapeHtml(p.category)}</span></td>
        <td style="font-weight: 700;">₹${priceFormatted}</td>
        <td><span class="badge ${p.stock_quantity > 0 ? 'badge-info' : 'badge-danger'}">${p.stock_quantity} ${escapeHtml(p.unit || 'units')}</span></td>
        <td>${statusBadge}</td>
        <td>
          <div class="row-action-dropdown">
            <button type="button" class="action-dots-trigger" onclick="toggleRowActionMenu(event, 'prod-${p.id}')" title="Actions" aria-label="Product Actions">
              <i data-lucide="more-vertical"></i>
            </button>
            <div class="row-action-menu hidden" id="row-action-menu-prod-${p.id}">
              <button type="button" class="row-action-item" onclick="toggleProductPublication('${p.id}', '${p.publication_status}'); closeAllRowActionMenus();">
                <i data-lucide="globe"></i> <span>${p.publication_status === 'PUBLISHED' ? 'Unpublish to Draft' : 'Publish to Store'}</span>
              </button>
              <button type="button" class="row-action-item" onclick="toggleProductArchive('${p.id}'); closeAllRowActionMenus();">
                <i data-lucide="${isArchived ? 'rotate-ccw' : 'archive'}"></i> <span>${isArchived ? 'Restore Product' : 'Archive SKU'}</span>
              </button>
              <div class="row-action-divider"></div>
              <button type="button" class="row-action-item danger-item" onclick="confirmDeleteProduct('${p.id}'); closeAllRowActionMenus();">
                <i data-lucide="trash-2"></i> <span>Delete Permanently</span>
              </button>
            </div>
          </div>
        </td>
      </tr>
    `;
  }).join('');

  if (window.SetuTableManager) SetuTableManager.syncTable('productsTable');
  if (window.lucide) lucide.createIcons();
}

function openCreateProductModal() {
  const formHtml = `
    <form id="createProductForm" onsubmit="handleCreateProductSubmit(event)" style="display: flex; flex-direction: column; gap: 14px;">
      <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px;">
        <div>
          <label class="form-label" style="font-weight: 600; font-size: 0.8rem; margin-bottom: 4px; display: block;">SKU Code *</label>
          <input type="text" id="newProdSku" class="form-control" required placeholder="e.g. SKU-FOG-PRO-01" style="font-family: var(--font-mono); width: 100%; padding: 8px 10px; border-radius: var(--radius-sm); border: 1px solid var(--border-color);">
        </div>
        <div>
          <label class="form-label" style="font-weight: 600; font-size: 0.8rem; margin-bottom: 4px; display: block;">Category *</label>
          <input type="text" id="newProdCategory" class="form-control" required placeholder="e.g. Climate Control" style="width: 100%; padding: 8px 10px; border-radius: var(--radius-sm); border: 1px solid var(--border-color);">
        </div>
      </div>
      <div>
        <label class="form-label" style="font-weight: 600; font-size: 0.8rem; margin-bottom: 4px; display: block;">Product Name *</label>
        <input type="text" id="newProdName" class="form-control" required placeholder="e.g. Automated Ultrasonic Fogger Unit" style="width: 100%; padding: 8px 10px; border-radius: var(--radius-sm); border: 1px solid var(--border-color);">
      </div>
      <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px;">
        <div>
          <label class="form-label" style="font-weight: 600; font-size: 0.8rem; margin-bottom: 4px; display: block;">Price in INR (₹) *</label>
          <input type="number" id="newProdPrice" class="form-control" step="0.01" required placeholder="4999.00" style="width: 100%; padding: 8px 10px; border-radius: var(--radius-sm); border: 1px solid var(--border-color);">
        </div>
        <div>
          <label class="form-label" style="font-weight: 600; font-size: 0.8rem; margin-bottom: 4px; display: block;">Stock Quantity *</label>
          <input type="number" id="newProdStock" class="form-control" required value="20" style="width: 100%; padding: 8px 10px; border-radius: var(--radius-sm); border: 1px solid var(--border-color);">
        </div>
      </div>
      <div>
        <label class="form-label" style="font-weight: 600; font-size: 0.8rem; margin-bottom: 4px; display: block;">Product Image (Upload Photo)</label>
        <input type="file" id="newProdImageFile" accept="image/*" class="form-control" style="width: 100%; padding: 6px; border-radius: var(--radius-sm); border: 1px solid var(--border-color); font-size: 0.8rem;">
      </div>
      <div>
        <label class="form-label" style="font-weight: 600; font-size: 0.8rem; margin-bottom: 4px; display: block;">Description</label>
        <textarea id="newProdDesc" rows="3" class="form-control" placeholder="Specifications, voltage requirements, and recommended instar stage..." style="width: 100%; padding: 8px 10px; border-radius: var(--radius-sm); border: 1px solid var(--border-color); font-size: 0.82rem;"></textarea>
      </div>
      <div style="display: flex; justify-content: flex-end; gap: 8px; margin-top: 10px;">
        <button type="button" class="btn btn-skin btn-sm" onclick="closeAppModal()">Cancel</button>
        <button type="submit" class="btn btn-primary btn-sm" id="btnSaveNewProduct"><i data-lucide="plus"></i> Create SKU</button>
      </div>
    </form>
  `;
  openAppModal('Create New Product SKU', formHtml);
}

async function handleCreateProductSubmit(e) {
  e.preventDefault();
  const btn = document.getElementById('btnSaveNewProduct');
  if (btn) btn.disabled = true;

  try {
    let imageUrls = [];
    const fileInput = document.getElementById('newProdImageFile');
    if (fileInput && fileInput.files && fileInput.files[0]) {
      const formData = new FormData();
      formData.append('file', fileInput.files[0]);
      const upRes = await fetch(`${API_BASE_URL}/products/upload-image`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${adminToken}` },
        body: formData
      });
      if (upRes.ok) {
        const upData = await upRes.json();
        if (upData.image_url) imageUrls.push(upData.image_url);
      }
    }

    const priceRupees = parseFloat(document.getElementById('newProdPrice').value) || 0;
    const payload = {
      sku: document.getElementById('newProdSku').value.trim(),
      name: document.getElementById('newProdName').value.trim(),
      category: document.getElementById('newProdCategory').value.trim(),
      price_minor_units: Math.round(priceRupees * 100),
      stock_quantity: parseInt(document.getElementById('newProdStock').value, 10) || 0,
      description: document.getElementById('newProdDesc').value.trim(),
      images: imageUrls,
      unit: 'unit',
      currency: 'INR'
    };

    const res = await fetch(`${API_BASE_URL}/products`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${adminToken}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(payload)
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to create product');
    }

    showToast('Product SKU created successfully', 'success');
    closeAppModal();
    loadProducts();
  } catch (err) {
    showToast(err.message, 'error');
    if (btn) btn.disabled = false;
  }
}

async function toggleProductArchive(productId) {
  try {
    const res = await fetch(`${API_BASE_URL}/products/${productId}/toggle-archive`, {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${adminToken}` }
    });
    if (!res.ok) throw new Error('Failed to toggle archive status');
    showToast('Product status updated', 'success');
    loadProducts();
  } catch (err) {
    showToast(err.message, 'error');
  }
}

function confirmDeleteProduct(productId) {
  showConfirmActionModal({
    title: 'Delete Equipment Product',
    subtitle: 'Permanently remove SKU from catalogue',
    message: 'Are you sure you want to permanently delete this product? All inventory movement records will be removed.',
    confirmText: 'Permanently Delete Product',
    confirmDanger: true,
    onConfirm: async () => {
      try {
        const res = await fetch(`${API_BASE_URL}/products/${productId}`, {
          method: 'DELETE',
          headers: { 'Authorization': `Bearer ${adminToken}` }
        });
        if (!res.ok) throw new Error('Deletion failed');
        showToast('Product successfully deleted', 'success');
        loadProducts();
      } catch (err) {
        showToast(err.message, 'error');
      }
    }
  });
}

// ------------------------------------------------------------------------------
// 2. SALES & ORDERS
// ------------------------------------------------------------------------------
async function loadOrders(statusFilter = '') {
  const tbody = document.getElementById('ordersTableBody');
  if (!tbody) return;
  tbody.innerHTML = '<tr><td colspan="8" style="text-align: center; padding: 24px;">Loading orders...</td></tr>';

  try {
    const token = window.adminToken || TAB_STORAGE.getItem('setu_tab_token') || localStorage.getItem('setu_token') || '';
    const url = statusFilter ? `${API_BASE_URL}/orders?status=${encodeURIComponent(statusFilter)}` : `${API_BASE_URL}/orders`;
    const res = await fetch(url, {
      headers: token ? { 'Authorization': `Bearer ${token}` } : {}
    });
    if (!res.ok) throw new Error(`Server returned ${res.status}: ${res.statusText}`);
    allOrdersList = await res.json();
    renderOrdersTable(allOrdersList);
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="8" style="text-align: center; color: var(--rose); padding: 24px;">Unable to load orders: ${escapeHtml(err.message)}</td></tr>`;
    if (window.SetuTableManager) SetuTableManager.syncTable('ordersTable');
  }
}

function renderOrdersTable(orders) {
  const tbody = document.getElementById('ordersTableBody');
  if (!tbody) return;

  if (!orders || orders.length === 0) {
    tbody.innerHTML = `<tr><td colspan="8" style="text-align: center; padding: 36px; color: var(--text-muted);">
      <div style="font-size: 1.1rem; font-weight: 600; margin-bottom: 6px;">No Orders Recorded</div>
      <div>No sales orders match your query filter.</div>
    </td></tr>`;
    if (window.SetuTableManager) SetuTableManager.syncTable('ordersTable');
    return;
  }

  tbody.innerHTML = orders.map(ord => {
    const totalINR = ((ord.total_amount_minor_units || 0) / 100).toLocaleString('en-IN', { minimumFractionDigits: 2 });
    const statBadge = ord.status === 'PAID'
      ? '<span class="badge badge-success">PAID</span>'
      : (ord.status === 'FULFILLED'
          ? '<span class="badge badge-info">FULFILLED</span>'
          : (ord.status === 'CANCELLED' ? '<span class="badge badge-danger">CANCELLED</span>' : '<span class="badge badge-warning">PROCESSING</span>'));
    const createdDate = ord.created_at ? new Date(ord.created_at).toLocaleDateString() : '--';

    return `
      <tr data-id="${ord.id}">
        <td class="td-bulk-select" style="text-align: center;">
          <input type="checkbox" class="row-select-checkbox" data-row-id="${ord.id}" aria-label="Select Order" onchange="SetuTableManager.handleRowCheck('ordersTable', '${ord.id}', this)">
        </td>
        <td style="font-family: var(--font-mono); font-weight: 700; font-size: 0.82rem;">${escapeHtml(ord.order_number)}</td>
        <td style="font-weight: 600;">${escapeHtml(ord.customer_name || 'Farmer')}</td>
        <td>${escapeHtml(ord.farm_name || 'Rearing Shed')}</td>
        <td style="font-weight: 700;">₹${totalINR}</td>
        <td>${statBadge}</td>
        <td style="font-size: 0.78rem;">${createdDate}</td>
        <td>
          <div class="row-action-dropdown">
            <button type="button" class="action-dots-trigger" onclick="toggleRowActionMenu(event, 'ord-${ord.id}')" title="Actions" aria-label="Order Actions">
              <i data-lucide="more-vertical"></i>
            </button>
            <div class="row-action-menu hidden" id="row-action-menu-ord-${ord.id}">
              <button type="button" class="row-action-item" onclick="updateOrderStatusAction('${ord.id}', 'FULFILLED'); closeAllRowActionMenus();">
                <i data-lucide="check-circle"></i> <span>Mark as Fulfilled</span>
              </button>
              <button type="button" class="row-action-item" onclick="updateOrderStatusAction('${ord.id}', 'PAID'); closeAllRowActionMenus();">
                <i data-lucide="credit-card"></i> <span>Mark as Paid</span>
              </button>
              <div class="row-action-divider"></div>
              <button type="button" class="row-action-item danger-item" onclick="updateOrderStatusAction('${ord.id}', 'CANCELLED'); closeAllRowActionMenus();">
                <i data-lucide="x-circle"></i> <span>Cancel Order</span>
              </button>
            </div>
          </div>
        </td>
      </tr>
    `;
  }).join('');

  if (window.SetuTableManager) SetuTableManager.syncTable('ordersTable');
  if (window.lucide) lucide.createIcons();
}

async function updateOrderStatusAction(orderId, nextStatus) {
  try {
    const res = await fetch(`${API_BASE_URL}/orders/${orderId}/status`, {
      method: 'PATCH',
      headers: {
        'Authorization': `Bearer ${adminToken}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ status: nextStatus })
    });
    if (!res.ok) throw new Error('Status update failed');
    showToast(`Order status updated to ${nextStatus}`, 'success');
    loadOrders();
  } catch (err) {
    showToast(err.message, 'error');
  }
}

function exportOrdersCsv() {
  if (window.SetuTableManager) SetuTableManager.exportSelected('ordersTable');
}

// ------------------------------------------------------------------------------
// 3. BILLING & SUBSCRIPTIONS
// ------------------------------------------------------------------------------
async function loadBilling() {
  const subsBody = document.getElementById('subsTableBody');
  const invBody = document.getElementById('invoicesTableBody');
  if (subsBody) subsBody.innerHTML = '<tr><td colspan="8" style="text-align: center; padding: 24px;">Loading subscriptions...</td></tr>';
  if (invBody) invBody.innerHTML = '<tr><td colspan="8" style="text-align: center; padding: 24px;">Loading invoices...</td></tr>';

  try {
    const token = window.adminToken || TAB_STORAGE.getItem('setu_tab_token') || localStorage.getItem('setu_token') || '';
    const headers = token ? { 'Authorization': `Bearer ${token}` } : {};

    const [subsRes, invRes] = await Promise.all([
      fetch(`${API_BASE_URL}/subscriptions`, { headers }),
      fetch(`${API_BASE_URL}/invoices`, { headers })
    ]);

    if (subsBody) {
      if (subsRes.ok) {
        allSubsList = await subsRes.json();
        renderSubsTable(allSubsList);
      } else {
        subsBody.innerHTML = `<tr><td colspan="8" style="text-align: center; color: var(--rose); padding: 20px;">Subscriptions (${subsRes.status}): ${subsRes.statusText}</td></tr>`;
        if (window.SetuTableManager) SetuTableManager.syncTable('subsTable');
      }
    }
    if (invBody) {
      if (invRes.ok) {
        allInvoicesList = await invRes.json();
        renderInvoicesTable(allInvoicesList);
      } else {
        invBody.innerHTML = `<tr><td colspan="8" style="text-align: center; color: var(--rose); padding: 20px;">Invoices (${invRes.status}): ${invRes.statusText}</td></tr>`;
        if (window.SetuTableManager) SetuTableManager.syncTable('invoicesTable');
      }
    }
  } catch (err) {
    if (subsBody) subsBody.innerHTML = `<tr><td colspan="8" style="text-align: center; color: var(--rose); padding: 20px;">Failed to load subscriptions: ${escapeHtml(err.message)}</td></tr>`;
    if (invBody) invBody.innerHTML = `<tr><td colspan="8" style="text-align: center; color: var(--rose); padding: 20px;">Failed to load invoices: ${escapeHtml(err.message)}</td></tr>`;
  }
}

function renderSubsTable(subs) {
  const tbody = document.getElementById('subsTableBody');
  if (!tbody) return;

  if (!subs || subs.length === 0) {
    tbody.innerHTML = '<tr><td colspan="8" style="text-align: center; padding: 28px; color: var(--text-muted);">No active subscriptions found.</td></tr>';
    if (window.SetuTableManager) SetuTableManager.syncTable('subsTable');
    return;
  }

  tbody.innerHTML = subs.map(s => {
    const priceFormatted = ((s.monthly_price_minor_units || 0) / 100).toLocaleString('en-IN');
    const endDate = s.current_period_end ? new Date(s.current_period_end).toLocaleDateString() : '--';
    return `
      <tr data-id="${s.id}">
        <td class="td-bulk-select" style="text-align: center;">
          <input type="checkbox" class="row-select-checkbox" data-row-id="${s.id}" aria-label="Select Subscription" onchange="SetuTableManager.handleRowCheck('subsTable', '${s.id}', this)">
        </td>
        <td style="font-family: var(--font-mono); font-weight: 700; font-size: 0.8rem;">${escapeHtml(s.subscription_code)}</td>
        <td style="font-weight: 600;">${escapeHtml(s.customer_name || 'Farmer')}</td>
        <td>${escapeHtml(s.plan_name)}</td>
        <td><span class="badge badge-info">${escapeHtml(s.tier || 'PRO')}</span></td>
        <td style="font-weight: 700;">₹${priceFormatted}/mo</td>
        <td style="font-size: 0.78rem;">${endDate}</td>
        <td><span class="badge badge-success">${escapeHtml(s.status)}</span></td>
      </tr>
    `;
  }).join('');

  if (window.SetuTableManager) SetuTableManager.syncTable('subsTable');
  if (window.lucide) lucide.createIcons();
}

function renderInvoicesTable(invs) {
  const tbody = document.getElementById('invoicesTableBody');
  if (!tbody) return;

  if (!invs || invs.length === 0) {
    tbody.innerHTML = '<tr><td colspan="8" style="text-align: center; padding: 28px; color: var(--text-muted);">No issued invoices recorded.</td></tr>';
    if (window.SetuTableManager) SetuTableManager.syncTable('invoicesTable');
    return;
  }

  tbody.innerHTML = invs.map(inv => {
    const subtotal = ((inv.subtotal_minor_units || 0) / 100).toLocaleString('en-IN', { minimumFractionDigits: 2 });
    const tax = ((inv.tax_amount_minor_units || 0) / 100).toLocaleString('en-IN', { minimumFractionDigits: 2 });
    const total = ((inv.total_amount_minor_units || 0) / 100).toLocaleString('en-IN', { minimumFractionDigits: 2 });
    const due = inv.due_date ? new Date(inv.due_date).toLocaleDateString() : '--';
    const statBadge = inv.status === 'PAID'
      ? '<span class="badge badge-success">PAID</span>'
      : '<span class="badge badge-warning">PENDING</span>';

    return `
      <tr data-id="${inv.id}">
        <td class="td-bulk-select" style="text-align: center;">
          <input type="checkbox" class="row-select-checkbox" data-row-id="${inv.id}" aria-label="Select Invoice" onchange="SetuTableManager.handleRowCheck('invoicesTable', '${inv.id}', this)">
        </td>
        <td style="font-family: var(--font-mono); font-weight: 700; font-size: 0.8rem;">${escapeHtml(inv.invoice_number)}</td>
        <td style="font-weight: 600;">${escapeHtml(inv.customer_name || 'Farmer')}</td>
        <td>₹${subtotal}</td>
        <td>₹${tax}</td>
        <td style="font-weight: 700;">₹${total}</td>
        <td style="font-size: 0.78rem;">${due}</td>
        <td>${statBadge}</td>
      </tr>
    `;
  }).join('');

  if (window.SetuTableManager) SetuTableManager.syncTable('invoicesTable');
  if (window.lucide) lucide.createIcons();
}

// ------------------------------------------------------------------------------
// 4. SUPPORT TICKETS, SENSORS, ALERTS, INSTALLATIONS & OTHER SECTIONS
// ------------------------------------------------------------------------------
async function loadSupportTickets(statusFilter = '') {
  const tbody = document.getElementById('ticketsTableBody');
  if (!tbody) return;
  tbody.innerHTML = '<tr><td colspan="9" style="text-align: center; padding: 24px;">Loading support tickets...</td></tr>';

  try {
    const url = statusFilter ? `${API_BASE_URL}/support/tickets?status=${encodeURIComponent(statusFilter)}` : `${API_BASE_URL}/support/tickets`;
    const res = await fetch(url, { headers: { 'Authorization': `Bearer ${adminToken}` } });
    if (!res.ok) throw new Error('Failed to load tickets');
    const tickets = await res.json();
    allTicketsCache = tickets;

    if (tickets.length === 0) {
      tbody.innerHTML = '<tr><td colspan="9" style="text-align: center; padding: 28px; color: var(--text-muted);">No support tickets recorded.</td></tr>';
      if (window.SetuTableManager) SetuTableManager.syncTable('ticketsTable');
      return;
    }

    tbody.innerHTML = tickets.map(t => `
      <tr data-id="${t.id}" style="cursor: pointer;" onclick="if (!event.target.closest('input, button, a')) openTicketDetailsModal('${escapeHtml(t.id)}')">
        <td class="td-bulk-select" style="text-align: center;">
          <input type="checkbox" class="row-select-checkbox" data-row-id="${t.id}" aria-label="Select Ticket" onchange="SetuTableManager.handleRowCheck('ticketsTable', '${t.id}', this)">
        </td>
        <td style="font-family: var(--font-mono); font-weight: 700;">${escapeHtml(t.ticket_number)}</td>
        <td style="font-weight: 600;">${escapeHtml(t.subject)}</td>
        <td>${escapeHtml(t.farmer_name || 'Farmer')}</td>
        <td><span class="badge badge-info">${escapeHtml(t.category)}</span></td>
        <td><span class="badge ${t.priority === 'HIGH' || t.priority === 'CRITICAL' ? 'badge-danger' : 'badge-warning'}">${escapeHtml(t.priority)}</span></td>
        <td><span class="badge ${t.status === 'RESOLVED' ? 'badge-success' : 'badge-warning'}">${escapeHtml(t.status)}</span></td>
        <td>${escapeHtml(t.agent_name || 'Field Lead')}</td>
        <td>
          <button type="button" class="btn btn-outline btn-xs" onclick="event.stopPropagation(); openTicketDetailsModal('${escapeHtml(t.id)}')">View</button>
        </td>
      </tr>
    `).join('');

    if (window.SetuTableManager) SetuTableManager.syncTable('ticketsTable');
    if (window.lucide) lucide.createIcons();
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="9" style="text-align: center; color: var(--rose); padding: 20px;">Failed to load tickets: ${escapeHtml(err.message)}</td></tr>`;
  }
}

async function loadInstallations() {
  const tbody = document.getElementById('installationsTableBody');
  if (!tbody) return;
  tbody.innerHTML = '<tr><td colspan="8" style="text-align: center; padding: 24px;">Loading installation jobs...</td></tr>';

  try {
    const res = await fetch(`${API_BASE_URL}/installations`, { headers: { 'Authorization': `Bearer ${adminToken}` } });
    if (!res.ok) throw new Error('Failed to load installations');
    const jobs = await res.json();
    allInstallationsCache = jobs;

    if (jobs.length === 0) {
      tbody.innerHTML = '<tr><td colspan="8" style="text-align: center; padding: 28px; color: var(--text-muted);">No installation jobs recorded.</td></tr>';
      if (window.SetuTableManager) SetuTableManager.syncTable('installationsTable');
      return;
    }

    tbody.innerHTML = jobs.map(j => `
      <tr data-id="${j.id}" style="cursor: pointer;" onclick="if (!event.target.closest('input, button, a')) openInstallationJobDetails('${escapeHtml(j.id)}')">
        <td class="td-bulk-select" style="text-align: center;">
          <input type="checkbox" class="row-select-checkbox" data-row-id="${j.id}" aria-label="Select Job" onchange="SetuTableManager.handleRowCheck('installationsTable', '${j.id}', this)">
        </td>
        <td style="font-family: var(--font-mono); font-weight: 700;">${escapeHtml(j.job_number)}</td>
        <td style="font-weight: 600;">${escapeHtml(j.farmer_name || 'Farmer')}</td>
        <td><span class="badge badge-info">${escapeHtml(j.shed_id)}</span></td>
        <td>${escapeHtml(j.technician_name || 'Kiran Kumar')}</td>
        <td>${j.scheduled_date ? new Date(j.scheduled_date).toLocaleDateString() : '--'}</td>
        <td><span class="badge ${j.status === 'COMPLETED' ? 'badge-success' : (j.status === 'IN_PROGRESS' ? 'badge-info' : 'badge-warning')}">${escapeHtml(j.status)}</span></td>
        <td>
          <button type="button" class="btn btn-outline btn-xs" onclick="event.stopPropagation(); openInstallationJobDetails('${escapeHtml(j.id)}')">Details</button>
        </td>
      </tr>
    `).join('');

    if (window.SetuTableManager) SetuTableManager.syncTable('installationsTable');
    if (window.lucide) lucide.createIcons();
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="8" style="text-align: center; color: var(--rose); padding: 20px;">Failed to load installations: ${escapeHtml(err.message)}</td></tr>`;
  }
}

let allInstallationsCache = [];
let allTicketsCache = [];

async function openInstallationJobDetails(jobId) {
  let job = allInstallationsCache.find(j => j.id === jobId || j.job_number === jobId);
  if (!job) {
    try {
      const res = await fetch(`${API_BASE_URL}/installations/${encodeURIComponent(jobId)}`, {
        headers: { 'Authorization': `Bearer ${adminToken}` }
      });
      if (res.ok) job = await res.json();
    } catch (e) {}
  }

  if (!job) {
    showToast('Installation job record could not be found.', 'error');
    return;
  }

  const statusBadgeClass = job.status === 'COMPLETED' 
    ? 'badge-success' 
    : (job.status === 'IN_PROGRESS' ? 'badge-info' : (job.status === 'CANCELLED' ? 'badge-danger' : 'badge-warning'));

  const scheduledStr = job.scheduled_date ? new Date(job.scheduled_date).toLocaleString('en-IN', {
    dateStyle: 'medium',
    timeStyle: 'short'
  }) : 'Scheduled slot pending';

  const completedStr = job.completed_at ? new Date(job.completed_at).toLocaleString('en-IN', {
    dateStyle: 'medium',
    timeStyle: 'short'
  }) : (job.status === 'COMPLETED' ? 'Verified & Completed' : 'Pending Field Verification');

  const standardChecklistItems = [
    { id: 'power', label: 'Rearing Shed AC Power & 12V 5A DIN-Rail Power Supply Verification', defaultDone: job.status === 'COMPLETED' },
    { id: 'gateway', label: 'Setu Industrial IoT Edge Gateway Enclosure Mounting & Antenna Orientation', defaultDone: job.status === 'COMPLETED' },
    { id: 'sensors', label: 'Multi-Probe Environmental Sensor Daisy-Chain (SHT31 Temp/RH & MQ-135 Gas)', defaultDone: job.status === 'COMPLETED' || job.status === 'IN_PROGRESS' },
    { id: 'relays', label: 'Actuator Safety Interlock Relays (Exhaust Fan, Mist Fogger, PTC Heater)', defaultDone: job.status === 'COMPLETED' },
    { id: 'uplink', label: 'Edge-to-Cloud Telemetry Stream & Realtime SSE Synchronization Verified', defaultDone: job.status === 'COMPLETED' },
    { id: 'mobile', label: 'Farmer Mobile App Paired & Instar Microclimate Thresholds Commissioned', defaultDone: job.status === 'COMPLETED' }
  ];

  const currentChecklist = Array.isArray(job.checklist_completed) ? job.checklist_completed : [];
  
  const checklistHtml = standardChecklistItems.map((item, idx) => {
    const isChecked = currentChecklist.includes(item.id) || item.defaultDone;
    return `
      <div style="display: flex; align-items: flex-start; gap: 10px; padding: 10px 12px; background: var(--bg-hover); border: 1px solid var(--border-color); border-radius: var(--radius-sm); margin-bottom: 8px;">
        <input type="checkbox" id="chk_${item.id}" value="${item.id}" ${isChecked ? 'checked' : ''} style="margin-top: 3px; accent-color: var(--brand-primary); cursor: pointer;" onchange="updateJobChecklist('${job.id}')">
        <label for="chk_${item.id}" style="font-size: 0.84rem; color: var(--text-main); font-weight: 500; cursor: pointer; flex: 1;">
          <span style="font-weight: 700; color: var(--text-muted); margin-right: 4px;">Step ${idx + 1}:</span>
          ${item.label}
        </label>
        <span style="font-size: 0.72rem; font-weight: 700; color: ${isChecked ? 'var(--status-success)' : 'var(--text-muted)'}; white-space: nowrap;">
          ${isChecked ? '<i data-lucide="check" style="width: 14px; height: 14px; display: inline-block; vertical-align: middle;"></i> Verified' : 'Pending'}
        </span>
      </div>
    `;
  }).join('');

  const modalHtml = `
    <div style="display: flex; flex-direction: column; gap: 18px;">
      <!-- Top Overview Banner -->
      <div style="display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 12px; padding: 14px 18px; background: var(--bg-hover); border: 1px solid var(--border-color); border-radius: var(--radius-md);">
        <div>
          <div style="display: flex; align-items: center; gap: 8px;">
            <span style="font-family: var(--font-mono); font-size: 1.15rem; font-weight: 800; color: var(--brand-primary);">${escapeHtml(job.job_number)}</span>
            <span class="badge ${statusBadgeClass}" id="detailJobStatusBadge">${escapeHtml(job.status)}</span>
            <span class="badge badge-info"><i data-lucide="home" style="width: 12px; height: 12px; margin-right: 3px;"></i>${escapeHtml(job.shed_id)}</span>
          </div>
          <span style="font-size: 0.78rem; color: var(--text-muted); margin-top: 4px; display: block;">
            Job ID: <code style="font-size: 0.76rem;">${escapeHtml(job.id)}</code> &middot; Scheduled: ${scheduledStr}
          </span>
        </div>
        <div style="display: flex; align-items: center; gap: 8px;">
          ${job.status !== 'COMPLETED' ? `
            <button type="button" class="btn btn-primary btn-sm" onclick="advanceJobStatus('${job.id}', 'COMPLETED')">
              <i data-lucide="check-circle-2" style="width: 14px; height: 14px; margin-right: 4px;"></i>
              <span>Complete Verification</span>
            </button>
          ` : `
            <span style="display: flex; align-items: center; gap: 6px; font-size: 0.82rem; font-weight: 700; color: var(--status-success);">
              <i data-lucide="shield-check" style="width: 18px; height: 18px;"></i>
              <span>Hardware Commissioned &amp; Certified</span>
            </span>
          `}
        </div>
      </div>

      <!-- 2-Column Info Cards -->
      <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 16px;">
        <!-- Card 1: Farmer & Rearing Shed Facility -->
        <div style="background: var(--bg-surface); border: 1px solid var(--border-color); border-radius: var(--radius-md); padding: 16px;">
          <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 12px; border-bottom: 1px solid var(--border-color); padding-bottom: 8px;">
            <i data-lucide="user" style="width: 16px; height: 16px; color: var(--brand-primary);"></i>
            <h4 style="font-size: 0.88rem; font-weight: 700; margin: 0; color: var(--text-main);">Farmer &amp; Shed Facility</h4>
          </div>
          <div style="display: flex; flex-direction: column; gap: 8px; font-size: 0.82rem;">
            <div style="display: flex; justify-content: space-between;">
              <span style="color: var(--text-muted);">Farmer Name:</span>
              <strong style="color: var(--text-main);">${escapeHtml(job.farmer_name || 'Harshith Kd')}</strong>
            </div>
            <div style="display: flex; justify-content: space-between;">
              <span style="color: var(--text-muted);">Farm / Shed Name:</span>
              <strong style="color: var(--text-main);">${escapeHtml(job.farm_name || 'Setu Smart Farm')}</strong>
            </div>
            <div style="display: flex; justify-content: space-between;">
              <span style="color: var(--text-muted);">Region / Cluster:</span>
              <span>${escapeHtml(job.region || 'Karnataka Sericulture Zone')}</span>
            </div>
            <div style="display: flex; justify-content: space-between;">
              <span style="color: var(--text-muted);">Registered Contact:</span>
              <span style="font-family: var(--font-mono); font-weight: 600;">${escapeHtml(job.farmer_phone || '+91 98450 12345')}</span>
            </div>
          </div>
        </div>

        <!-- Card 2: Field Technician & Schedule -->
        <div style="background: var(--bg-surface); border: 1px solid var(--border-color); border-radius: var(--radius-md); padding: 16px;">
          <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 12px; border-bottom: 1px solid var(--border-color); padding-bottom: 8px;">
            <i data-lucide="wrench" style="width: 16px; height: 16px; color: var(--brand-primary);"></i>
            <h4 style="font-size: 0.88rem; font-weight: 700; margin: 0; color: var(--text-main);">Field Technician Assignment</h4>
          </div>
          <div style="display: flex; flex-direction: column; gap: 8px; font-size: 0.82rem;">
            <div style="display: flex; justify-content: space-between;">
              <span style="color: var(--text-muted);">Assigned Lead:</span>
              <strong style="color: var(--text-main);">${escapeHtml(job.technician_name || 'Kiran Kumar (Field Lead)')}</strong>
            </div>
            <div style="display: flex; justify-content: space-between;">
              <span style="color: var(--text-muted);">Technician Helpline:</span>
              <span style="font-family: var(--font-mono); font-weight: 600;">${escapeHtml(job.technician_phone || '+91 94480 55678')}</span>
            </div>
            <div style="display: flex; justify-content: space-between;">
              <span style="color: var(--text-muted);">Scheduled Date:</span>
              <span>${scheduledStr}</span>
            </div>
            <div style="display: flex; justify-content: space-between;">
              <span style="color: var(--text-muted);">Verification Status:</span>
              <span style="font-weight: 700; color: ${job.status === 'COMPLETED' ? 'var(--status-success)' : 'var(--status-warning)'};">${completedStr}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Scope of Hardware & Technical Notes -->
      <div style="background: var(--bg-surface); border: 1px solid var(--border-color); border-radius: var(--radius-md); padding: 16px;">
        <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 10px;">
          <i data-lucide="clipboard-list" style="width: 16px; height: 16px; color: var(--brand-primary);"></i>
          <h4 style="font-size: 0.88rem; font-weight: 700; margin: 0; color: var(--text-main);">Technical Scope &amp; Deployment Notes</h4>
        </div>
        <p style="font-size: 0.84rem; color: var(--text-main); line-height: 1.5; margin: 0 0 10px 0; background: var(--bg-hover); padding: 10px 14px; border-radius: var(--radius-sm); border-left: 3px solid var(--brand-primary);">
          ${escapeHtml(job.technician_notes || 'Full Setu Automation Hub & 4-Sensor Daisy Chain Setup with emergency actuator override interlocks.')}
        </p>
        <div style="display: flex; flex-wrap: wrap; gap: 6px;">
          <span class="badge" style="background: var(--bg-hover); border: 1px solid var(--border-color); font-size: 0.74rem;"><i data-lucide="cpu" style="width: 12px; height: 12px; margin-right: 4px;"></i>Edge Gateway (ESP32-S3)</span>
          <span class="badge" style="background: var(--bg-hover); border: 1px solid var(--border-color); font-size: 0.74rem;"><i data-lucide="thermometer" style="width: 12px; height: 12px; margin-right: 4px;"></i>Dual SHT31 Temp/RH Probe</span>
          <span class="badge" style="background: var(--bg-hover); border: 1px solid var(--border-color); font-size: 0.74rem;"><i data-lucide="wind" style="width: 12px; height: 12px; margin-right: 4px;"></i>MQ-135 Gas &amp; Freshness Sensor</span>
          <span class="badge" style="background: var(--bg-hover); border: 1px solid var(--border-color); font-size: 0.74rem;"><i data-lucide="zap" style="width: 12px; height: 12px; margin-right: 4px;"></i>Zero-Crossing Actuator Relays</span>
        </div>
      </div>

      <!-- Installation & Commissioning Checklist -->
      <div style="background: var(--bg-surface); border: 1px solid var(--border-color); border-radius: var(--radius-md); padding: 16px;">
        <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px;">
          <div style="display: flex; align-items: center; gap: 8px;">
            <i data-lucide="check-square" style="width: 16px; height: 16px; color: var(--brand-primary);"></i>
            <h4 style="font-size: 0.88rem; font-weight: 700; margin: 0; color: var(--text-main);">Hardware Commissioning &amp; Safety Checklist</h4>
          </div>
          <span style="font-size: 0.75rem; color: var(--text-muted);">Step-by-step verification protocol</span>
        </div>
        <div id="jobChecklistContainer">
          ${checklistHtml}
        </div>
      </div>

      <!-- Modal Footer Action Bar -->
      <div style="display: flex; align-items: center; justify-content: space-between; padding-top: 10px; border-top: 1px solid var(--border-color); margin-top: 4px;">
        <div style="display: flex; gap: 8px;">
          ${job.status === 'SCHEDULED' ? `
            <button type="button" class="btn btn-outline btn-sm" onclick="advanceJobStatus('${job.id}', 'IN_PROGRESS')">
              <i data-lucide="play" style="width: 14px; height: 14px; margin-right: 4px;"></i>
              <span>Start Field Work</span>
            </button>
          ` : ''}
          ${job.status === 'IN_PROGRESS' ? `
            <button type="button" class="btn btn-primary btn-sm" onclick="advanceJobStatus('${job.id}', 'COMPLETED')">
              <i data-lucide="check" style="width: 14px; height: 14px; margin-right: 4px;"></i>
              <span>Verify &amp; Complete Job</span>
            </button>
          ` : ''}
          <button type="button" class="btn btn-outline btn-sm" onclick="showToast('Printing official Field Installation Sheet for ' + '${escapeHtml(job.job_number)}', 'info'); window.print();">
            <i data-lucide="printer" style="width: 14px; height: 14px; margin-right: 4px;"></i>
            <span>Print Job Sheet</span>
          </button>
        </div>
        <button type="button" class="btn btn-skin btn-sm" onclick="closeAppModal()">Close</button>
      </div>
    </div>
  `;

  openAppModal(`Field Installation Job: ${job.job_number}`, modalHtml, 'lg');
  if (window.lucide) lucide.createIcons();
}

async function advanceJobStatus(jobId, newStatus) {
  try {
    const res = await fetch(`${API_BASE_URL}/installations/${jobId}`, {
      method: 'PATCH',
      headers: {
        'Authorization': `Bearer ${adminToken}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        status: newStatus,
        remarks: `Updated by technician in admin console to ${newStatus}`
      })
    });
    if (!res.ok) throw new Error('Failed to update installation job status');
    showToast(`Installation job ${newStatus === 'COMPLETED' ? 'completed and verified!' : 'marked in progress.'}`, 'success');
    closeAppModal();
    loadInstallations();
  } catch (err) {
    showToast(err.message, 'error');
  }
}

async function updateJobChecklist(jobId) {
  const container = document.getElementById('jobChecklistContainer');
  if (!container) return;
  const checked = Array.from(container.querySelectorAll('input[type="checkbox"]:checked')).map(cb => cb.value);
  try {
    await fetch(`${API_BASE_URL}/installations/${jobId}`, {
      method: 'PATCH',
      headers: {
        'Authorization': `Bearer ${adminToken}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        status: checked.length === 6 ? 'COMPLETED' : 'IN_PROGRESS',
        checklist_completed: checked,
        remarks: `Checklist updated: ${checked.length} of 6 tasks verified`
      })
    });
    showToast(`Checklist saved (${checked.length}/6 verified)`, 'info');
  } catch (e) {
    console.error('Checklist autosave failed:', e);
  }
}

function openTicketDetailsModal(ticketId) {
  const ticket = allTicketsCache.find(t => t.id === ticketId || t.ticket_number === ticketId);
  if (!ticket) {
    showToast('Ticket record not found.', 'error');
    return;
  }

  const priorityClass = ticket.priority === 'HIGH' || ticket.priority === 'CRITICAL' ? 'badge-danger' : (ticket.priority === 'MEDIUM' ? 'badge-warning' : 'badge-info');
  const statusClass = ticket.status === 'RESOLVED' ? 'badge-success' : (ticket.status === 'IN_PROGRESS' ? 'badge-info' : 'badge-warning');

  const modalHtml = `
    <div style="display: flex; flex-direction: column; gap: 16px;">
      <div style="display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 10px; padding: 12px 16px; background: var(--bg-hover); border: 1px solid var(--border-color); border-radius: var(--radius-md);">
        <div>
          <div style="display: flex; align-items: center; gap: 8px;">
            <span style="font-family: var(--font-mono); font-weight: 800; font-size: 1.1rem; color: var(--brand-primary);">${escapeHtml(ticket.ticket_number)}</span>
            <span class="badge ${statusClass}">${escapeHtml(ticket.status)}</span>
            <span class="badge ${priorityClass}">${escapeHtml(ticket.priority)} PRIORITY</span>
          </div>
          <span style="font-size: 0.78rem; color: var(--text-muted); margin-top: 4px; display: block;">
            Category: <strong>${escapeHtml(ticket.category)}</strong> &middot; Opened: ${ticket.created_at ? new Date(ticket.created_at).toLocaleString() : '--'}
          </span>
        </div>
      </div>

      <div style="background: var(--bg-surface); border: 1px solid var(--border-color); border-radius: var(--radius-md); padding: 16px;">
        <h4 style="margin: 0 0 8px 0; font-size: 0.95rem; font-weight: 700; color: var(--text-main);">${escapeHtml(ticket.subject)}</h4>
        <p style="margin: 0; font-size: 0.85rem; color: var(--text-main); line-height: 1.6; background: var(--bg-hover); padding: 12px; border-radius: var(--radius-sm);">
          ${escapeHtml(ticket.description || 'No detailed issue description entered.')}
        </p>
      </div>

      <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 14px;">
        <div style="background: var(--bg-surface); border: 1px solid var(--border-color); border-radius: var(--radius-md); padding: 14px; font-size: 0.82rem;">
          <div style="font-weight: 700; margin-bottom: 6px; color: var(--text-muted);">Farmer Facility</div>
          <div><strong>${escapeHtml(ticket.farmer_name || 'Farmer')}</strong></div>
          <div style="color: var(--text-muted); font-size: 0.78rem;">Shed ID: ${escapeHtml(ticket.shed_id || 'shed_01')}</div>
        </div>
        <div style="background: var(--bg-surface); border: 1px solid var(--border-color); border-radius: var(--radius-md); padding: 14px; font-size: 0.82rem;">
          <div style="font-weight: 700; margin-bottom: 6px; color: var(--text-muted);">Assigned Support Lead</div>
          <div><strong>${escapeHtml(ticket.agent_name || 'Field Support Lead')}</strong></div>
          <div style="color: var(--text-muted); font-size: 0.78rem;">Status: ${escapeHtml(ticket.status)}</div>
        </div>
      </div>

      <div style="display: flex; justify-content: flex-end; gap: 10px; padding-top: 10px; border-top: 1px solid var(--border-color);">
        <button type="button" class="btn btn-skin btn-sm" onclick="closeAppModal()">Close</button>
      </div>
    </div>
  `;

  openAppModal(`Support Ticket: ${ticket.ticket_number}`, modalHtml, 'lg');
  if (window.lucide) lucide.createIcons();
}

window.openInstallationJobDetails = openInstallationJobDetails;
window.openInstallationWorkflowDrawer = openInstallationJobDetails;
window.advanceJobStatus = advanceJobStatus;
window.updateJobChecklist = updateJobChecklist;
window.openTicketDetailsModal = openTicketDetailsModal;

async function loadInstallTeam() {
  const tbody = document.getElementById('teamTableBody');
  if (!tbody) return;
  tbody.innerHTML = '<tr><td colspan="6" style="text-align: center; padding: 24px;">Loading technical staff...</td></tr>';

  try {
    const res = await fetch(`${API_BASE_URL}/installations/team`, { headers: { 'Authorization': `Bearer ${adminToken}` } });
    if (!res.ok) throw new Error('Failed to load team');
    const team = await res.json();

    tbody.innerHTML = team.map(m => `
      <tr data-id="${m.id}">
        <td class="td-bulk-select" style="text-align: center;">
          <input type="checkbox" class="row-select-checkbox" data-row-id="${m.id}" aria-label="Select Member" onchange="SetuTableManager.handleRowCheck('teamTable', '${m.id}', this)">
        </td>
        <td style="font-weight: 700;">${escapeHtml(m.full_name)}</td>
        <td style="font-family: var(--font-mono);">${escapeHtml(m.username)}</td>
        <td>${escapeHtml(m.phone || '--')}</td>
        <td>${escapeHtml(m.region || 'Karnataka Hub')}</td>
        <td><span class="badge badge-info">${m.active_jobs || 1} Jobs</span></td>
      </tr>
    `).join('');

    if (window.SetuTableManager) SetuTableManager.syncTable('teamTable');
    if (window.lucide) lucide.createIcons();
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="6" style="text-align: center; color: var(--rose); padding: 20px;">Failed to load team: ${escapeHtml(err.message)}</td></tr>`;
  }
}

async function loadSensors() {
  const tbody = document.getElementById('sensorsTableBody');
  if (!tbody) return;
  tbody.innerHTML = '<tr><td colspan="10" style="text-align: center; padding: 24px;">Loading sensors registry...</td></tr>';

  try {
    const res = await fetch(`${API_BASE_URL}/sensors`, { headers: { 'Authorization': `Bearer ${adminToken}` } });
    if (!res.ok) throw new Error('Failed to load sensors');
    const sensors = await res.json();

    tbody.innerHTML = sensors.map(s => `
      <tr data-id="${s.id}">
        <td class="td-bulk-select" style="text-align: center;">
          <input type="checkbox" class="row-select-checkbox" data-row-id="${s.id}" aria-label="Select Sensor" onchange="SetuTableManager.handleRowCheck('sensorsTable', '${s.id}', this)">
        </td>
        <td style="font-family: var(--font-mono); font-weight: 700;">${escapeHtml(s.id)}</td>
        <td style="font-weight: 600;">${escapeHtml(s.model || 'Sensirion')}</td>
        <td><span class="badge badge-info">${escapeHtml(s.sensor_type)}</span></td>
        <td style="font-family: var(--font-mono);">${escapeHtml(s.pin_or_bus || 'I2C')}</td>
        <td>${s.min_safe_range} - ${s.max_safe_range} ${escapeHtml(s.unit || '')}</td>
        <td>${s.reporting_interval_seconds}s</td>
        <td style="font-weight: 700;">${s.calibration_offset >= 0 ? '+' : ''}${s.calibration_offset}</td>
        <td><span class="badge badge-success">${escapeHtml(s.status)}</span></td>
        <td>
          <button type="button" class="btn btn-outline btn-xs" onclick="showToast('Calibrated ' + '${escapeHtml(s.id)}')">Calibrate</button>
        </td>
      </tr>
    `).join('');

    if (window.SetuTableManager) SetuTableManager.syncTable('sensorsTable');
    if (window.lucide) lucide.createIcons();
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="10" style="text-align: center; color: var(--rose); padding: 20px;">Failed to load sensors: ${escapeHtml(err.message)}</td></tr>`;
  }
}

async function loadAlerts() {
  const tbody = document.getElementById('alertsTableBody');
  if (!tbody) return;
  tbody.innerHTML = '<tr><td colspan="10" style="text-align: center; padding: 24px;">Loading alerts...</td></tr>';

  try {
    const res = await fetch(`${API_BASE_URL}/alerts`, { headers: { 'Authorization': `Bearer ${adminToken}` } });
    if (!res.ok) throw new Error('Failed to load alerts');
    const alerts = await res.json();

    if (alerts.length === 0) {
      tbody.innerHTML = '<tr><td colspan="10" style="text-align: center; padding: 28px; color: var(--text-muted);">No active system alerts. All sheds nominal.</td></tr>';
      if (window.SetuTableManager) SetuTableManager.syncTable('alertsTable');
      return;
    }

    tbody.innerHTML = alerts.map(a => `
      <tr data-id="${a.id}">
        <td class="td-bulk-select" style="text-align: center;">
          <input type="checkbox" class="row-select-checkbox" data-row-id="${a.id}" aria-label="Select Alert" onchange="SetuTableManager.handleRowCheck('alertsTable', '${a.id}', this)">
        </td>
        <td style="font-family: var(--font-mono); font-weight: 700;">${escapeHtml(a.alert_code)}</td>
        <td><span class="badge ${a.severity === 'CRITICAL' ? 'badge-danger' : 'badge-warning'}">${escapeHtml(a.severity)}</span></td>
        <td>${escapeHtml(a.shed_id)}</td>
        <td>${escapeHtml(a.alert_type)}</td>
        <td>${escapeHtml(a.description)}</td>
        <td style="font-weight: 700;">${a.current_value} / ${a.threshold_value}</td>
        <td style="font-size: 0.78rem;">${new Date(a.triggered_at).toLocaleTimeString()}</td>
        <td><span class="badge badge-warning">${escapeHtml(a.status)}</span></td>
        <td>
          <button type="button" class="btn btn-outline btn-xs" onclick="showToast('Acknowledged alert ' + '${escapeHtml(a.alert_code)}')">Acknowledge</button>
        </td>
      </tr>
    `).join('');

    if (window.SetuTableManager) SetuTableManager.syncTable('alertsTable');
    if (window.lucide) lucide.createIcons();
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="10" style="text-align: center; color: var(--rose); padding: 20px;">Failed to load alerts: ${escapeHtml(err.message)}</td></tr>`;
  }
}

async function loadDevices() {
  const tbody = document.getElementById('devicesTableBody');
  if (!tbody) return;
  tbody.innerHTML = '<tr><td colspan="9" style="text-align: center; padding: 24px;">Loading IoT gateways...</td></tr>';

  try {
    const res = await fetch(`${API_BASE_URL}/admin/sheds`, { headers: { 'Authorization': `Bearer ${adminToken}` } });
    if (!res.ok) throw new Error('Failed to load gateways');
    const sheds = await res.json();

    tbody.innerHTML = sheds.map((s, idx) => `
      <tr data-id="dev_${s.shed_id}">
        <td class="td-bulk-select" style="text-align: center;">
          <input type="checkbox" class="row-select-checkbox" data-row-id="dev_${s.shed_id}" aria-label="Select Device" onchange="SetuTableManager.handleRowCheck('devicesTable', 'dev_${s.shed_id}', this)">
        </td>
        <td style="font-family: var(--font-mono); font-weight: 700;">GW-ESP32-${s.shed_id.toUpperCase()}</td>
        <td style="font-weight: 600;">Setu Industrial Gateway Node</td>
        <td>${escapeHtml(s.shed_name || s.shed_id)}</td>
        <td style="font-family: var(--font-mono); font-size: 0.78rem;">v2.4.1-prod</td>
        <td><span class="badge badge-info">mTLS + ECC608</span></td>
        <td><span class="badge badge-success">ONLINE</span></td>
        <td style="font-size: 0.78rem;">Just now</td>
        <td>
          <button type="button" class="btn btn-outline btn-xs" onclick="showToast('Reboot command sent to ' + '${s.shed_id}')">Reboot</button>
        </td>
      </tr>
    `).join('');

    if (window.SetuTableManager) SetuTableManager.syncTable('devicesTable');
    if (window.lucide) lucide.createIcons();
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="9" style="text-align: center; color: var(--rose); padding: 20px;">Failed to load devices: ${escapeHtml(err.message)}</td></tr>`;
  }
}

async function loadTasksQueue() {
  const tbody = document.getElementById('tasksTableBody');
  if (!tbody) return;
  tbody.innerHTML = `
    <tr data-id="task_001">
      <td class="td-bulk-select" style="text-align: center;"><input type="checkbox" class="row-select-checkbox" data-row-id="task_001" onchange="SetuTableManager.handleRowCheck('tasksTable', 'task_001', this)"></td>
      <td><span class="badge badge-info">MAINTENANCE</span></td>
      <td><strong>Shed 01 Exhaust Fan Inspection</strong></td>
      <td>Kiran Kumar (Tech)</td>
      <td><span class="badge badge-danger">HIGH</span></td>
      <td>Today, 5:00 PM</td>
      <td><span class="badge badge-warning">IN_PROGRESS</span></td>
      <td><button class="btn btn-outline btn-xs" onclick="showToast('Task completed', 'success')">Done</button></td>
    </tr>
    <tr data-id="task_002">
      <td class="td-bulk-select" style="text-align: center;"><input type="checkbox" class="row-select-checkbox" data-row-id="task_002" onchange="SetuTableManager.handleRowCheck('tasksTable', 'task_002', this)"></td>
      <td><span class="badge badge-success">FARMER_SUPPORT</span></td>
      <td><strong>Ramesh Gowda Instar 4 Guidance</strong></td>
      <td>Priya Sharma</td>
      <td><span class="badge badge-info">MEDIUM</span></td>
      <td>Tomorrow</td>
      <td><span class="badge badge-secondary">QUEUED</span></td>
      <td><button class="btn btn-outline btn-xs" onclick="showToast('Task dispatched', 'success')">Dispatch</button></td>
    </tr>
  `;
  if (window.SetuTableManager) SetuTableManager.syncTable('tasksTable');
  if (window.lucide) lucide.createIcons();
}

async function loadUsers() {
  const tbody = document.getElementById('usersTableBody');
  if (!tbody) return;
  tbody.innerHTML = '<tr><td colspan="7" style="text-align: center; padding: 24px;">Loading user accounts...</td></tr>';

  try {
    const res = await fetch(`${API_BASE_URL}/admin/farmers`, { headers: { 'Authorization': `Bearer ${adminToken}` } });
    if (!res.ok) throw new Error('Failed to load users');
    const users = await res.json();

    tbody.innerHTML = users.map(u => `
      <tr data-id="${u.id}">
        <td class="td-bulk-select" style="text-align: center;">
          <input type="checkbox" class="row-select-checkbox" data-row-id="${u.id}" aria-label="Select User" onchange="SetuTableManager.handleRowCheck('usersTable', '${u.id}', this)">
        </td>
        <td style="font-family: var(--font-mono); font-weight: 700;">${escapeHtml(u.username)}</td>
        <td style="font-weight: 600;">${escapeHtml(u.full_name || u.username)}</td>
        <td><span class="badge badge-info">${escapeHtml(u.role || 'farmer')}</span></td>
        <td>${escapeHtml(u.phone || '--')}</td>
        <td>${escapeHtml(u.region || 'Karnataka')}</td>
        <td><span class="badge ${u.is_active ? 'badge-success' : 'badge-danger'}">${u.is_active ? 'ACTIVE' : 'SUSPENDED'}</span></td>
      </tr>
    `).join('');

    if (window.SetuTableManager) SetuTableManager.syncTable('usersTable');
    if (window.lucide) lucide.createIcons();
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="7" style="text-align: center; color: var(--rose); padding: 20px;">Failed to load users: ${escapeHtml(err.message)}</td></tr>`;
  }
}

async function loadAuditLogs() {
  const tbody = document.getElementById('auditTableBody');
  if (!tbody) return;
  tbody.innerHTML = '<tr><td colspan="7" style="text-align: center; padding: 24px;">Loading security audit trail...</td></tr>';

  try {
    const res = await fetch(`${API_BASE_URL}/platform/audit-logs`, { headers: { 'Authorization': `Bearer ${adminToken}` } });
    if (!res.ok) throw new Error('Failed to load audit trail');
    const logs = await res.json();

    tbody.innerHTML = logs.map(l => `
      <tr data-id="${l.id}">
        <td class="td-bulk-select" style="text-align: center;">
          <input type="checkbox" class="row-select-checkbox" data-row-id="${l.id}" aria-label="Select Log" onchange="SetuTableManager.handleRowCheck('auditTable', '${l.id}', this)">
        </td>
        <td style="font-family: var(--font-mono); font-size: 0.78rem;">${new Date(l.created_at).toLocaleString()}</td>
        <td style="font-weight: 600;">${escapeHtml(l.actor_identity)}</td>
        <td><span class="badge badge-info">${escapeHtml(l.action)}</span></td>
        <td style="font-family: var(--font-mono); font-size: 0.78rem;">${escapeHtml(l.resource_type)}</td>
        <td style="font-size: 0.8rem;">${escapeHtml(l.details)}</td>
        <td style="font-family: var(--font-mono); font-size: 0.76rem;">${escapeHtml(l.ip_address || '127.0.0.1')}</td>
      </tr>
    `).join('');

    if (window.SetuTableManager) SetuTableManager.syncTable('auditTable');
    if (window.lucide) lucide.createIcons();
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="7" style="text-align: center; color: var(--rose); padding: 20px;">Failed to load audit logs: ${escapeHtml(err.message)}</td></tr>`;
  }
}

async function loadGuidanceArticles(lang = 'en') {
  try {
    const res = await fetch(`${API_BASE_URL}/guidance?language=${encodeURIComponent(lang)}`, { headers: { 'Authorization': `Bearer ${adminToken}` } });
    if (!res.ok) return;
    const articles = await res.json();
    const container = document.getElementById('guidanceArticlesList');
    if (container && articles.length > 0) {
      container.innerHTML = articles.map(a => `
        <div class="card" style="padding: 16px; margin-bottom: 12px; border-radius: var(--radius-sm); border: 1px solid var(--border-color); background: var(--bg-surface);">
          <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px;">
            <h4 style="margin: 0; font-size: 1rem; color: var(--text-main);">${escapeHtml(a.title)}</h4>
            <span class="badge badge-info">Instar ${a.target_instar}</span>
          </div>
          <p style="font-size: 0.84rem; color: var(--text-secondary); margin-bottom: 10px;">${escapeHtml(a.summary)}</p>
          <div style="padding: 10px; background: rgba(16, 185, 129, 0.08); border-radius: var(--radius-sm); font-size: 0.8rem; color: var(--emerald-700);">
            <strong>Recommended Action:</strong> ${escapeHtml(a.recommended_action)}
          </div>
        </div>
      `).join('');
      if (window.lucide) lucide.createIcons();
    }
  } catch (_) {}
}

async function loadIntegrations() {
  try {
    const res = await fetch(`${API_BASE_URL}/platform/integrations`, { headers: { 'Authorization': `Bearer ${adminToken}` } });
    if (!res.ok) return;
    const integrations = await res.json();
    // Render into integrations cards if available
  } catch (_) {}
}

// ------------------------------------------------------------------------------
// REARING SHEDS CONTROL & GROWTH STAGE CLIMATE THRESHOLDS
// ------------------------------------------------------------------------------
let stagesData = [];
window.stagesData = stagesData;

async function loadStageThresholds() {
  const container = document.getElementById('stageThresholdsGrid');
  if (container) {
    container.innerHTML = `
      <div style="grid-column: 1 / -1; text-align: center; padding: 36px; color: var(--text-muted);">
        <i data-lucide="loader" class="spin" style="width: 28px; height: 28px; margin-bottom: 8px;"></i>
        <div>Loading stage climate setpoints &amp; guidelines...</div>
      </div>
    `;
    if (window.lucide) lucide.createIcons();
  }

  try {
    const res = await fetch(`${API_BASE_URL}/admin/stages`, {
      headers: { 'Authorization': `Bearer ${adminToken}` }
    });
    if (!res.ok) {
      if (container) {
        const err = await getResError(res);
        container.innerHTML = `
          <div style="grid-column: 1 / -1; text-align: center; padding: 36px; color: var(--rose);">
            Failed to load rearing stages from server: ${escapeHtml(err)}
          </div>
        `;
      }
      return;
    }
    const stages = await res.json();
    stagesData = stages;
    window.stagesData = stages;
    renderStageThresholds(stages);
  } catch (err) {
    if (container) {
      container.innerHTML = `
        <div style="grid-column: 1 / -1; text-align: center; padding: 36px; color: var(--rose);">
          Error loading rearing stages: ${escapeHtml(err.message)}
        </div>
      `;
    }
  }

  // Also load monitored rearing sheds fleet table
  loadShedsFleet();
}
window.loadStageThresholds = loadStageThresholds;

function renderStageThresholds(stages) {
  const container = document.getElementById('stageThresholdsGrid');
  if (!container) return;

  if (!stages || !stages.length) {
    container.innerHTML = `
      <div style="grid-column: 1 / -1; text-align: center; padding: 48px; background: var(--bg-surface); border: 1px dashed var(--border-color); border-radius: var(--radius-lg); color: var(--text-muted);">
        <i data-lucide="warehouse" style="width: 40px; height: 40px; margin-bottom: 12px; opacity: 0.5;"></i>
        <div style="font-weight: 700; font-size: 1.05rem; margin-bottom: 4px; color: var(--text-main);">No Stage Guidelines Found</div>
        <p style="font-size: 0.85rem; max-width: 400px; margin: 0 auto 16px;">Central Silk Board climate setpoints have not been initialized yet.</p>
        <button class="btn btn-primary btn-sm" onclick="resetStageThresholdsToDefault()"><i data-lucide="rotate-ccw"></i> Initialize CSB Standards</button>
      </div>
    `;
    if (window.lucide) lucide.createIcons();
    return;
  }

  // Determine current active stage of selected shed
  const shedSelect = document.getElementById('headerShedSelect');
  const selectedShed = shedSelect ? shedSelect.value : (currentShedId || 'shed_01');
  const activeStageId = window.currentTelemetry?.current_stage || 1;

  container.innerHTML = stages.map(s => {
    const isActive = s.stage_id === activeStageId;
    return `
      <div class="stage-card" style="background: var(--bg-surface); border: 1px solid ${isActive ? 'var(--brand-primary)' : 'var(--border-color)'}; border-radius: var(--radius-lg); padding: 20px; display: flex; flex-direction: column; justify-content: space-between; gap: 14px; box-shadow: ${isActive ? '0 0 0 1px var(--brand-primary), var(--shadow-sm)' : 'var(--shadow-sm)'}; position: relative; transition: all var(--transition-fast);">
        <div>
          <div style="display: flex; justify-content: space-between; align-items: flex-start; gap: 8px; margin-bottom: 8px;">
            <div style="display: flex; align-items: center; gap: 6px; flex-wrap: wrap;">
              <span class="badge" style="background: var(--brand-tint); color: var(--brand-primary); font-weight: 800; font-size: 0.72rem; letter-spacing: 0.5px;">INSTAR ${s.stage_id}</span>
              <span class="badge badge-neutral" style="font-size: 0.72rem; font-weight: 600;"><i data-lucide="calendar" style="width: 11px; height: 11px; margin-right: 3px;"></i> ${escapeHtml(s.days)}</span>
            </div>
            ${isActive ? `<span class="badge badge-success" style="font-size: 0.70rem; font-weight: 700; white-space: nowrap;"><i data-lucide="check-circle" style="width: 11px; height: 11px; margin-right: 3px;"></i> Active Stage</span>` : ''}
          </div>

          <h3 style="font-size: 1.15rem; font-weight: 800; color: var(--text-main); margin: 0 0 12px;">${escapeHtml(s.name)}</h3>

          <!-- Setpoints Box -->
          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 12px;">
            <!-- Temperature Box -->
            <div style="background: var(--bg-subtle); border: 1px solid var(--border-subtle); border-radius: var(--radius-md); padding: 12px; display: flex; flex-direction: column; gap: 4px;">
              <div style="display: flex; align-items: center; gap: 6px; font-size: 0.72rem; font-weight: 700; color: #d97706;">
                <i data-lucide="thermometer" style="width: 14px; height: 14px;"></i>
                <span>TEMPERATURE</span>
              </div>
              <div style="font-size: 1.22rem; font-weight: 800; color: var(--text-main); font-family: var(--font-mono);">
                ${s.temp_min}°C – ${s.temp_max}°C
              </div>
              <div style="font-size: 0.70rem; color: var(--text-muted);">
                Tolerance: ±${s.hysteresis_temp || 0.5}°C
              </div>
            </div>

            <!-- Humidity Box -->
            <div style="background: var(--bg-subtle); border: 1px solid var(--border-subtle); border-radius: var(--radius-md); padding: 12px; display: flex; flex-direction: column; gap: 4px;">
              <div style="display: flex; align-items: center; gap: 6px; font-size: 0.72rem; font-weight: 700; color: #2563eb;">
                <i data-lucide="droplets" style="width: 14px; height: 14px;"></i>
                <span>HUMIDITY</span>
              </div>
              <div style="font-size: 1.22rem; font-weight: 800; color: var(--text-main); font-family: var(--font-mono);">
                ${s.hum_min}% – ${s.hum_max}%
              </div>
              <div style="font-size: 0.70rem; color: var(--text-muted);">
                Tolerance: ±${s.hysteresis_hum || 3.0}%
              </div>
            </div>
          </div>

          <!-- Ventilation Trigger -->
          <div style="background: var(--bg-subtle); border: 1px solid var(--border-subtle); border-radius: var(--radius-md); padding: 8px 12px; display: flex; align-items: center; justify-content: space-between; font-size: 0.74rem; margin-bottom: 12px;">
            <span style="color: var(--text-muted); display: flex; align-items: center; gap: 5px;">
              <i data-lucide="wind" style="width: 13px; height: 13px; color: var(--brand-primary);"></i>
              Cooler / Fan Trigger:
            </span>
            <strong style="color: var(--text-main); font-family: var(--font-mono);">+${s.fan_trigger_offset || 1.5}°C above max</strong>
          </div>

          <!-- Description / Scientific Guidelines -->
          <div>
            <div style="font-size: 0.70rem; font-weight: 700; color: var(--text-muted); text-transform: uppercase; margin-bottom: 4px; display: flex; align-items: center; gap: 4px;">
              <i data-lucide="info" style="width: 11px; height: 11px;"></i>
              Silkworm Rearing Advisory
            </div>
            <p style="font-size: 0.80rem; color: var(--text-secondary); line-height: 1.45; margin: 0;">
              ${escapeHtml(s.description || 'Optimal Central Silk Board standard conditions.')}
            </p>
          </div>
        </div>

        <!-- Action Buttons -->
        <div style="display: flex; gap: 8px; padding-top: 12px; border-top: 1px solid var(--border-subtle); margin-top: 4px;">
          <button class="btn btn-outline btn-sm" style="flex: 1;" onclick="openEditStageModal(${s.stage_id})">
            <i data-lucide="sliders"></i> Edit Setpoints
          </button>
          <button class="btn btn-primary btn-sm" style="flex: 1;" onclick="applyStageToSelectedShed(${s.stage_id})" title="Activate this instar on selected shed">
            <i data-lucide="play"></i> Apply to Shed
          </button>
        </div>
      </div>
    `;
  }).join('');

  if (window.lucide) lucide.createIcons();
}
window.renderStageThresholds = renderStageThresholds;

function openEditStageModal(stageId) {
  const stage = (stagesData || []).find(s => s.stage_id === stageId);
  if (!stage) {
    showNotification(`Stage ${stageId} details not found.`, 'error');
    return;
  }

  const html = `
    <form id="editStageForm" onsubmit="saveStageThresholds(event, ${stage.stage_id})">
      <div style="display: flex; flex-direction: column; gap: 16px;">
        <p style="font-size: 0.85rem; color: var(--text-secondary); margin: 0;">
          Configuring master climate setpoints for <strong>${escapeHtml(stage.name)}</strong> (${escapeHtml(stage.days)}).
          Updates are saved directly to the database and reconfigure auto-mode triggers across all active rearing sheds.
        </p>

        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 14px;">
          <div class="form-group">
            <label class="form-label" for="editStageTempMin">Min Temperature (°C) *</label>
            <input type="number" step="0.1" min="10" max="45" id="editStageTempMin" class="form-input" value="${stage.temp_min}" required style="width: 100%;" />
          </div>
          <div class="form-group">
            <label class="form-label" for="editStageTempMax">Max Temperature (°C) *</label>
            <input type="number" step="0.1" min="10" max="45" id="editStageTempMax" class="form-input" value="${stage.temp_max}" required style="width: 100%;" />
          </div>
        </div>

        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 14px;">
          <div class="form-group">
            <label class="form-label" for="editStageHumMin">Min Humidity (%) *</label>
            <input type="number" step="0.1" min="10" max="100" id="editStageHumMin" class="form-input" value="${stage.hum_min}" required style="width: 100%;" />
          </div>
          <div class="form-group">
            <label class="form-label" for="editStageHumMax">Max Humidity (%) *</label>
            <input type="number" step="0.1" min="10" max="100" id="editStageHumMax" class="form-input" value="${stage.hum_max}" required style="width: 100%;" />
          </div>
        </div>

        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 14px;">
          <div class="form-group">
            <label class="form-label" for="editStageHystTemp">Temp Hysteresis (±°C)</label>
            <input type="number" step="0.1" min="0.1" max="5" id="editStageHystTemp" class="form-input" value="${stage.hysteresis_temp || 0.5}" style="width: 100%;" />
          </div>
          <div class="form-group">
            <label class="form-label" for="editStageHystHum">Humidity Hysteresis (±%)</label>
            <input type="number" step="0.1" min="0.5" max="15" id="editStageHystHum" class="form-input" value="${stage.hysteresis_hum || 3.0}" style="width: 100%;" />
          </div>
        </div>

        <div class="form-group">
          <label class="form-label" for="editStageFanOffset">Cooling / Fan Trigger Offset (°C above max)</label>
          <input type="number" step="0.1" min="0" max="10" id="editStageFanOffset" class="form-input" value="${stage.fan_trigger_offset || 1.5}" style="width: 100%;" />
        </div>

        <div class="form-group">
          <label class="form-label" for="editStageDesc">Silkworm Rearing Guidelines &amp; Advisory</label>
          <textarea id="editStageDesc" class="form-input" rows="3" style="width: 100%;">${escapeHtml(stage.description || '')}</textarea>
        </div>

        <div style="display: flex; justify-content: flex-end; gap: 10px; margin-top: 8px;">
          <button type="button" class="btn btn-skin" onclick="closeAppModal()">Cancel</button>
          <button type="submit" class="btn btn-primary" id="saveStageSubmitBtn"><i data-lucide="check"></i> Save Changes</button>
        </div>
      </div>
    </form>
  `;

  openAppModal(`Configure Stage ${stage.stage_id}: ${stage.name}`, html, 'md');
}
window.openEditStageModal = openEditStageModal;

async function saveStageThresholds(event, stageId) {
  event.preventDefault();
  const btn = document.getElementById('saveStageSubmitBtn');
  if (btn) btn.disabled = true;

  const tempMin = parseFloat(document.getElementById('editStageTempMin')?.value);
  const tempMax = parseFloat(document.getElementById('editStageTempMax')?.value);
  const humMin = parseFloat(document.getElementById('editStageHumMin')?.value);
  const humMax = parseFloat(document.getElementById('editStageHumMax')?.value);
  const hystTemp = parseFloat(document.getElementById('editStageHystTemp')?.value || '0.5');
  const hystHum = parseFloat(document.getElementById('editStageHystHum')?.value || '3.0');
  const fanOffset = parseFloat(document.getElementById('editStageFanOffset')?.value || '1.5');
  const desc = document.getElementById('editStageDesc')?.value || '';

  if (tempMin > tempMax) {
    showNotification('Minimum temperature cannot exceed maximum temperature', 'error');
    if (btn) btn.disabled = false;
    return;
  }
  if (humMin > humMax) {
    showNotification('Minimum humidity cannot exceed maximum humidity', 'error');
    if (btn) btn.disabled = false;
    return;
  }

  try {
    const res = await fetch(`${API_BASE_URL}/admin/stages/${stageId}`, {
      method: 'PUT',
      headers: {
        'Authorization': `Bearer ${adminToken}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        temp_min: tempMin,
        temp_max: tempMax,
        hum_min: humMin,
        hum_max: humMax,
        hysteresis_temp: hystTemp,
        hysteresis_hum: hystHum,
        fan_trigger_offset: fanOffset,
        description: desc
      })
    });

    if (!res.ok) {
      const err = await getResError(res);
      showNotification(`Failed to update setpoints: ${err}`, 'error');
      if (btn) btn.disabled = false;
      return;
    }

    showNotification(`Stage ${stageId} climate setpoints updated successfully!`, 'success');
    closeAppModal();
    await loadStageThresholds();
  } catch (err) {
    showNotification(`Error saving setpoints: ${err.message}`, 'error');
    if (btn) btn.disabled = false;
  }
}
window.saveStageThresholds = saveStageThresholds;

async function resetStageThresholdsToDefault() {
  if (!confirm('Are you sure you want to reset all 5 rearing stage climate setpoints to Central Silk Board (CSB) scientific standards?')) {
    return;
  }

  try {
    const res = await fetch(`${API_BASE_URL}/admin/stages/reset`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${adminToken}`,
        'Content-Type': 'application/json'
      }
    });

    if (!res.ok) {
      const err = await getResError(res);
      showNotification(`Failed to reset stages: ${err}`, 'error');
      return;
    }

    showNotification('All stage setpoints successfully restored to Central Silk Board standards!', 'success');
    await loadStageThresholds();
  } catch (err) {
    showNotification(`Error resetting stages: ${err.message}`, 'error');
  }
}
window.resetStageThresholdsToDefault = resetStageThresholdsToDefault;

async function applyStageToSelectedShed(stageId) {
  const shedSelect = document.getElementById('headerShedSelect');
  const shedId = shedSelect ? shedSelect.value : (currentShedId || 'shed_01');
  const stage = (stagesData || []).find(s => s.stage_id === stageId);
  const stageName = stage ? stage.name : `Stage ${stageId}`;

  try {
    const res = await fetch(`${API_BASE_URL}/admin/sheds/${encodeURIComponent(shedId)}/stage`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${adminToken}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ stage: stageId })
    });

    if (!res.ok) {
      const err = await getResError(res);
      showNotification(`Failed to switch shed stage: ${err}`, 'error');
      return;
    }

    showNotification(`Shed "${shedId}" switched to ${stageName}! Microclimate targets applied.`, 'success');
    await loadStageThresholds();
    await loadShedsFleet();
  } catch (err) {
    showNotification(`Error: ${err.message}`, 'error');
  }
}
window.applyStageToSelectedShed = applyStageToSelectedShed;

// ------------------------------------------------------------------------------
// MONITORED REARING SHEDS FLEET
// ------------------------------------------------------------------------------
let allShedsFleet = [];
window.allShedsFleet = allShedsFleet;

async function loadShedsFleet() {
  const tbody = document.getElementById('shedsFleetTableBody');
  const badge = document.getElementById('shedsFleetBadgeCount');
  if (!tbody) return;

  try {
    const res = await fetch(`${API_BASE_URL}/admin/sheds`, {
      headers: { 'Authorization': `Bearer ${adminToken}` }
    });
    if (!res.ok) {
      tbody.innerHTML = `<tr><td colspan="7" style="text-align: center; padding: 24px; color: var(--rose);">Failed to load rearing sheds fleet</td></tr>`;
      return;
    }
    const sheds = await res.json();
    allShedsFleet = sheds;
    window.allShedsFleet = sheds;
    if (badge) badge.textContent = `${sheds.length} Configured`;
    renderShedsFleetTable(sheds);
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="7" style="text-align: center; padding: 24px; color: var(--text-muted);">Error: ${escapeHtml(err.message)}</td></tr>`;
  }
}
window.loadShedsFleet = loadShedsFleet;

function renderShedsFleetTable(sheds) {
  const tbody = document.getElementById('shedsFleetTableBody');
  if (!tbody) return;

  if (!sheds || !sheds.length) {
    tbody.innerHTML = `<tr><td colspan="7" style="text-align: center; padding: 36px; color: var(--text-muted);">No rearing sheds registered yet.</td></tr>`;
    return;
  }

  tbody.innerHTML = sheds.map(s => {
    return `
      <tr>
        <td style="font-family: var(--font-mono); font-weight: 700; color: var(--text-main);">
          <div style="display: flex; align-items: center; gap: 6px;">
            <i data-lucide="warehouse" style="width: 14px; height: 14px; color: var(--brand-primary);"></i>
            <span>${escapeHtml(s.shed_id)}</span>
          </div>
        </td>
        <td>
          <div style="font-weight: 700; color: var(--text-main);">${escapeHtml(s.farm_name || s.display_name || 'Rearing Shed')}</div>
          <div style="font-size: 0.75rem; color: var(--text-muted);">${escapeHtml(s.farmer_name || 'Assigned Farmer')}</div>
        </td>
        <td>
          <span class="badge badge-neutral">${escapeHtml(s.region || 'Karnataka')}</span>
        </td>
        <td>
          <span class="font-mono" style="font-size: 0.80rem; font-weight: 600;">${escapeHtml(s.batch_id || 'SERI-2026')}</span>
        </td>
        <td>
          <span class="badge" style="background: var(--brand-tint); color: var(--brand-primary); font-weight: 700;">
            Instar ${s.current_stage || 1}
          </span>
        </td>
        <td>
          <span class="badge badge-success" style="display: inline-flex; align-items: center; gap: 4px;">
            <i data-lucide="cpu" style="width: 11px; height: 11px;"></i> Auto
          </span>
        </td>
        <td>
          <div style="display: flex; gap: 6px;">
            <button class="btn btn-outline btn-xs" onclick="selectAndMonitorShed('${escapeHtml(s.shed_id)}')" title="View Live Telemetry">
              <i data-lucide="activity"></i> Monitor
            </button>
            <button class="btn btn-skin btn-xs" onclick="promptSwitchShedStage('${escapeHtml(s.shed_id)}')" title="Switch Growth Stage">
              <i data-lucide="git-commit"></i> Stage
            </button>
          </div>
        </td>
      </tr>
    `;
  }).join('');

  if (window.lucide) lucide.createIcons();
  if (window.SetuTableManager) SetuTableManager.syncTable('shedsFleetTable');
}
window.renderShedsFleetTable = renderShedsFleetTable;

function selectAndMonitorShed(shedId) {
  const shedSelect = document.getElementById('headerShedSelect');
  if (shedSelect) {
    shedSelect.value = shedId;
    shedSelect.dispatchEvent(new Event('change'));
  }
  switchNavTab('live-monitoring');
}
window.selectAndMonitorShed = selectAndMonitorShed;

function promptSwitchShedStage(shedId) {
  const stageNum = prompt(`Switch active growth stage for shed "${shedId}" (Enter instar 1 to 5):`, "1");
  if (!stageNum) return;
  const stageId = parseInt(stageNum);
  if (isNaN(stageId) || stageId < 1 || stageId > 5) {
    alert("Please enter a valid stage number between 1 and 5.");
    return;
  }

  fetch(`${API_BASE_URL}/admin/sheds/${encodeURIComponent(shedId)}/stage`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${adminToken}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ stage: stageId })
  })
  .then(async res => {
    if (!res.ok) {
      const err = await getResError(res);
      showNotification(`Failed to switch stage: ${err}`, 'error');
      return;
    }
    showNotification(`Shed "${shedId}" set to Instar ${stageId}!`, 'success');
    loadStageThresholds();
  })
  .catch(err => {
    showNotification(`Error: ${err.message}`, 'error');
  });
}
window.promptSwitchShedStage = promptSwitchShedStage;

function filterShedsFleet(query) {
  if (!window.allShedsFleet) return;
  const q = (query || '').toLowerCase().trim();
  const filtered = window.allShedsFleet.filter(s =>
    (s.shed_id || '').toLowerCase().includes(q) ||
    (s.farm_name || '').toLowerCase().includes(q) ||
    (s.farmer_name || '').toLowerCase().includes(q) ||
    (s.region || '').toLowerCase().includes(q) ||
    (s.batch_id || '').toLowerCase().includes(q)
  );
  renderShedsFleetTable(filtered);
}
window.filterShedsFleet = filterShedsFleet;


window.addEventListener("DOMContentLoaded", () => {
  checkGoogleOAuthCallback();
  loadGoogleAuthConfig();
  initGoogleAuth();
});

// Explicit Global Window Exports for Dynamic Invocation & TableManager Interop
window.showConfirmActionModal = showConfirmActionModal;
window.executePendingConfirmAction = executePendingConfirmAction;
window.closeAppModal = closeAppModal;
window.openAppModal = openAppModal;
window.showToast = showToast;
window.loadProducts = loadProducts;
window.loadOrders = loadOrders;
window.loadBilling = loadBilling;
window.loadFarmers = loadFarmers;
window.loadDevices = loadDevices;
window.loadSensors = loadSensors;
window.loadAlerts = loadAlerts;
window.loadSupportTickets = loadSupportTickets;
window.loadInstallations = loadInstallations;
window.loadInstallTeam = loadInstallTeam;
window.loadEmployeesList = loadEmployeesList;
window.loadRolesAndPermissions = loadRolesAndPermissions;
window.loadDepartmentsList = loadDepartmentsList;
window.loadAuditRecords = loadAuditRecords;
window.switchNavTab = switchNavTab;
