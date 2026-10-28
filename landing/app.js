// ==========================================================================
// SeriCare Enterprise IoT Platform - Public Landing Application Controller
// Dynamic REST Ingestion, Database Catalog, Telemetry Stream & Enquiry CRM
// ==========================================================================

const API_BASE_URL = `${window.location.origin}/api/v1`;

let allProductsCache = [];
let activeCategory = 'ALL';

document.addEventListener('DOMContentLoaded', () => {
  if (window.lucide) lucide.createIcons();

  // Core Data Initializers
  initMobileMenu();
  initModals();
  fetchCategories();
  fetchProducts();
  fetchFaqs();
  fetchLiveTelemetry();
  initEnquiryForm();

  // Polling intervals
  setInterval(fetchLiveTelemetry, 10000);

  // Active navigation highlight on scroll
  setupScrollSpy();
});

// ==========================================================================
// 1. MOBILE NAVIGATION DRAWER
// ==========================================================================
function initMobileMenu() {
  const menuBtn = document.getElementById('mobileMenuBtn');
  const drawer = document.getElementById('mobileNavDrawer');
  if (!menuBtn || !drawer) return;

  menuBtn.addEventListener('click', () => {
    drawer.classList.toggle('open');
    const isOpen = drawer.classList.contains('open');
    menuBtn.setAttribute('aria-expanded', isOpen);
  });

  // Close drawer when clicking any link inside it
  drawer.querySelectorAll('a').forEach(link => {
    link.addEventListener('click', () => {
      drawer.classList.remove('open');
      menuBtn.setAttribute('aria-expanded', 'false');
    });
  });
}

// ==========================================================================
// 2. LIVE TELEMETRY & GATEWAY INGESTION
// ==========================================================================
async function fetchLiveTelemetry() {
  const fetchLandingTelemetry = fetchLiveTelemetry;
  try {
    const res = await fetch(`${API_BASE_URL}/sheds/shed_01/overview`);
    if (!res.ok) return;
    const data = await res.json();

    // Dials in Hero
    const tempEl = document.getElementById('heroDialTemp');
    const humEl = document.getElementById('heroDialHum');
    const aqEl = document.getElementById('heroDialAq');
    const luxEl = document.getElementById('heroDialLux');
    const stageBadge = document.getElementById('heroStageBadge');
    const statusText = document.getElementById('heroStatusText');

    if (tempEl) tempEl.textContent = `${data.indoor_temp.toFixed(1)}°C`;
    if (humEl) humEl.textContent = `${data.indoor_humidity.toFixed(1)}%`;
    if (aqEl) aqEl.textContent = `${data.indoor_air_quality.toFixed(1)}%`;
    if (luxEl) luxEl.textContent = `${Math.round(data.indoor_light_lux)} Lux`;
    if (stageBadge) stageBadge.textContent = `Instar ${data.current_stage}`;
    if (statusText) statusText.textContent = `${data.shed_id.toUpperCase()} · ${data.stage_name.toUpperCase()}`;

    // Target Range Indicators
    const tempRange = document.getElementById('heroRangeTemp');
    const humRange = document.getElementById('heroRangeHum');
    if (tempRange) tempRange.textContent = `Target: ${data.temp_target.toFixed(1)}°C`;
    if (humRange) humRange.textContent = `Target: ${data.humidity_target.toFixed(1)}%`;

    // Actuators
    if (data.actuators) {
      updateActuatorChip('chipCooler', data.actuators.cooler, 'Cooling Active', 'Cooler Standby');
      updateActuatorChip('chipHeater', data.actuators.heater, 'Heating Active', 'Heater Standby');
      updateActuatorChip('chipFan', data.actuators.fan, 'Vent Active', 'Vent Standby');
      const pwmChip = document.getElementById('chipPwm');
      if (pwmChip) pwmChip.textContent = `PWM ${data.actuators.light_brightness}%`;
    }

    const lastUp = document.getElementById('heroLastUpdate');
    if (lastUp) {
      lastUp.textContent = `PostgreSQL Sync: ${new Date().toLocaleTimeString()} (Active)`;
    }

    // Append to live terminal console
    appendTerminalLog(data);
  } catch (err) {
    console.debug('Telemetry sync standby:', err);
  }
}

function updateActuatorChip(id, isOn, onText, offText) {
  const el = document.getElementById(id);
  if (!el) return;
  if (isOn) {
    el.className = 'actuator-badge active';
    el.textContent = onText;
  } else {
    el.className = 'actuator-badge standby';
    el.textContent = offText;
  }
}

function appendTerminalLog(data) {
  const consoleLog = document.getElementById('liveConsoleStream');
  if (!consoleLog) return;

  const now = new Date().toTimeString().split(' ')[0];
  const line = document.createElement('div');
  line.className = 'terminal-line';
  line.innerHTML = `<span class="t-ts">[${now}]</span> <span class="t-tag">SHED_01</span>: SHT31 Temp: <span class="t-val">${data.indoor_temp.toFixed(1)}°C</span> | RH: <span class="t-val">${data.indoor_humidity.toFixed(1)}%</span> | Fan: <span class="${data.actuators?.fan ? 't-ok' : ''}">${data.actuators?.fan ? 'ON' : 'OFF'}</span> | Heater: <span>${data.actuators?.heater ? 'ON' : 'OFF'}</span>`;

  consoleLog.appendChild(line);
  if (consoleLog.children.length > 8) {
    consoleLog.removeChild(consoleLog.children[0]);
  }
}

// ==========================================================================
// 3. PRODUCT CATALOGUE & CATEGORY FILTERING (DATABASE-BACKED)
// ==========================================================================
async function fetchCategories() {
  try {
    const res = await fetch(`${API_BASE_URL}/public/categories`);
    if (!res.ok) return;
    const categories = await res.json();
    renderCategories(categories);
  } catch (err) {
    console.error('Failed to load categories:', err);
  }
}

function renderCategories(categories) {
  const filterBar = document.getElementById('categoryFilters');
  if (!filterBar) return;

  // Clear existing except "All"
  filterBar.innerHTML = `<button class="cat-pill-btn active" data-category="ALL" role="tab" aria-selected="true">All Products</button>`;

  categories.forEach(item => {
    const btn = document.createElement('button');
    btn.className = 'cat-pill-btn';
    btn.setAttribute('data-category', item.category);
    btn.setAttribute('role', 'tab');
    btn.setAttribute('aria-selected', 'false');
    btn.textContent = `${item.category} (${item.count})`;
    btn.addEventListener('click', () => {
      document.querySelectorAll('.cat-pill-btn').forEach(b => {
        b.classList.remove('active');
        b.setAttribute('aria-selected', 'false');
      });
      btn.classList.add('active');
      btn.setAttribute('aria-selected', 'true');
      activeCategory = item.category;
      filterAndRenderProducts();
    });
    filterBar.appendChild(btn);
  });

  // Re-wire "All" button
  const allBtn = filterBar.querySelector('[data-category="ALL"]');
  if (allBtn) {
    allBtn.addEventListener('click', () => {
      document.querySelectorAll('.cat-pill-btn').forEach(b => {
        b.classList.remove('active');
        b.setAttribute('aria-selected', 'false');
      });
      allBtn.classList.add('active');
      allBtn.setAttribute('aria-selected', 'true');
      activeCategory = 'ALL';
      filterAndRenderProducts();
    });
  }
}

async function fetchProducts() {
  try {
    const res = await fetch(`${API_BASE_URL}/public/products`);
    if (!res.ok) throw new Error('Product catalog unreachable');
    allProductsCache = await res.json();
    filterAndRenderProducts();
    populateProductDropdown(allProductsCache);
  } catch (err) {
    console.error('Failed to load products:', err);
    const grid = document.getElementById('productsCatalogGrid');
    if (grid) {
      grid.innerHTML = `
        <div class="product-card" style="grid-column: 1 / -1; text-align: center; padding: 48px;">
          <p style="color: var(--rose-600); font-weight: 600;">Unable to connect to product catalog database.</p>
          <button class="btn btn-outline btn-sm" style="margin-top: 12px;" onclick="fetchProducts()">Retry Connection</button>
        </div>
      `;
    }
  }
}

function filterAndRenderProducts() {
  const grid = document.getElementById('productsCatalogGrid');
  if (!grid) return;

  const filtered = activeCategory === 'ALL'
    ? allProductsCache
    : allProductsCache.filter(p => p.category === activeCategory);

  if (filtered.length === 0) {
    grid.innerHTML = `
      <div class="product-card" style="grid-column: 1 / -1; text-align: center; padding: 48px;">
        <p style="color: var(--slate-500);">No products found in category "${escapeHtml(activeCategory)}".</p>
      </div>
    `;
    return;
  }

  grid.innerHTML = filtered.map(p => {
    const priceText = p.price_minor_units && p.price_minor_units > 0
      ? `₹${(p.price_minor_units / 100).toLocaleString('en-IN')}`
      : 'Enterprise Quote';

    const specs = p.specifications || {};
    const specEntries = Object.entries(specs).slice(0, 3);
    const specPills = specEntries.map(([k, v]) => `
      <span class="spec-chip" title="${escapeHtml(k)}: ${escapeHtml(v)}">
        <strong>${escapeHtml(k)}:</strong> ${escapeHtml(String(v).substring(0, 24))}
      </span>
    `).join('');

    // Determine preview icon based on category/name
    let iconName = 'cpu';
    const lowerName = p.name.toLowerCase();
    if (lowerName.includes('gateway')) iconName = 'router';
    else if (lowerName.includes('temp') || lowerName.includes('sensor')) iconName = 'thermometer';
    else if (lowerName.includes('air') || lowerName.includes('co2')) iconName = 'wind';
    else if (lowerName.includes('light') || lowerName.includes('lux')) iconName = 'sun';
    else if (lowerName.includes('fan') || lowerName.includes('exhaust')) iconName = 'fan';
    else if (lowerName.includes('dimmer') || lowerName.includes('pwm')) iconName = 'sliders';
    else if (lowerName.includes('fogger') || lowerName.includes('mist')) iconName = 'droplets';
    else if (lowerName.includes('install') || lowerName.includes('service')) iconName = 'wrench';
    else if (lowerName.includes('app') || lowerName.includes('platform')) iconName = 'smartphone';

    // Support uploaded product photo if available
    const hasImage = p.images && Array.isArray(p.images) && p.images.length > 0 && p.images[0];
    const visualContent = hasImage
      ? `<img src="${escapeHtml(p.images[0])}" alt="${escapeHtml(p.name)}" class="product-card-img" onerror="this.onerror=null;this.parentElement.classList.remove('has-image');this.parentElement.innerHTML='<i data-lucide=\'${iconName}\'></i>';if(window.lucide)lucide.createIcons();">`
      : `<i data-lucide="${iconName}"></i>`;

    return `
      <article class="product-card" id="card-${escapeHtml(p.id)}" onclick="openProductDetails('${escapeHtml(p.slug || p.id)}')" title="Click to view ${escapeHtml(p.name)} specifications" role="button" tabindex="0">
        <div class="product-card-top">
          <span class="product-badge-cat">${escapeHtml(p.category)}</span>
          <span class="product-badge-avail in-stock">${escapeHtml(p.availability_status || 'AVAILABLE')}</span>
        </div>

        <div class="product-visual-preview ${hasImage ? 'has-image' : ''}">
          ${visualContent}
        </div>

        <span class="product-sku">${escapeHtml(p.sku)}</span>
        <h3 class="product-name">${escapeHtml(p.name)}</h3>
        <p class="product-desc">${escapeHtml(p.short_description || p.description || '')}</p>

        <div class="product-specs-pills">
          ${specPills}
        </div>

        <div class="product-card-footer">
          <div class="product-price-wrap">
            <span class="product-price-val">${priceText}</span>
            <span class="product-price-unit">Per Unit · GST extra</span>
          </div>

          <div class="product-card-actions">
            <button type="button" class="btn btn-outline btn-sm btn-product-view" onclick="event.stopPropagation(); openProductDetails('${escapeHtml(p.slug || p.id)}')">
              <i data-lucide="eye" style="width: 14px; height: 14px; margin-right: 4px;"></i>
              <span>View</span>
            </button>
            <button type="button" class="btn btn-primary btn-sm btn-product-buy" onclick="event.stopPropagation(); openBuyProductModal('${escapeHtml(p.id)}')">
              <i data-lucide="shopping-bag" style="width: 14px; height: 14px; margin-right: 4px;"></i>
              <span>Buy Now</span>
            </button>
          </div>
        </div>
      </article>
    `;
  }).join('');

  if (window.lucide) lucide.createIcons();
}

function populateProductDropdown(products) {
  const select = document.getElementById('productSelect');
  if (!select) return;

  // Preserve first default option
  select.innerHTML = '<option value="">General Platform / Full Shed Setup</option>';

  products.forEach(p => {
    const opt = document.createElement('option');
    opt.value = p.id;
    opt.textContent = `${p.name} (${p.sku})`;
    select.appendChild(opt);
  });
}

function selectProductForQuote(productId, productName) {
  const select = document.getElementById('productSelect');
  if (select) {
    select.value = productId;
  }
  const formSection = document.getElementById('demo-request');
  if (formSection) {
    formSection.scrollIntoView({ behavior: 'smooth' });
    setTimeout(() => {
      const nameInput = document.getElementById('fullName');
      if (nameInput) nameInput.focus();
    }, 600);
  }
}

// Function callable from footer links
window.filterCategoryFromFooter = function(category) {
  activeCategory = category;
  document.querySelectorAll('.cat-pill-btn').forEach(b => {
    b.classList.remove('active');
    if (b.getAttribute('data-category') === category) {
      b.classList.add('active');
    }
  });
  filterAndRenderProducts();
  const prodSec = document.getElementById('products');
  if (prodSec) prodSec.scrollIntoView({ behavior: 'smooth' });
};

// ==========================================================================
// 4. PRODUCT DETAILS MODAL (SPECIFICATIONS TABLE)
// ==========================================================================
async function openProductDetails(idOrSlug) {
  const modal = document.getElementById('productDetailModal');
  if (!modal) return;

  try {
    const res = await fetch(`${API_BASE_URL}/public/products/${encodeURIComponent(idOrSlug)}`);
    if (!res.ok) throw new Error('Product not found');
    const p = await res.json();
    currentModalProduct = p;

    document.getElementById('modalProductCategory').textContent = p.category;
    document.getElementById('modalProductTitle').textContent = p.name;
    document.getElementById('modalProductSku').textContent = p.sku;
    document.getElementById('modalProductDesc').textContent = p.description || p.short_description || '';

    // Product Photo in modal
    const modalImgWrap = document.getElementById('modalProductImageWrap');
    const modalImg = document.getElementById('modalProductImage');
    if (modalImgWrap && modalImg) {
      if (p.images && Array.isArray(p.images) && p.images.length > 0 && p.images[0]) {
        modalImg.src = p.images[0];
        modalImgWrap.classList.remove('hidden');
      } else {
        modalImgWrap.classList.add('hidden');
        modalImg.src = '';
      }
    }

    // Price
    const priceEl = document.getElementById('modalProductPrice');
    if (priceEl) {
      priceEl.textContent = p.price_minor_units && p.price_minor_units > 0
        ? `₹${(p.price_minor_units / 100).toLocaleString('en-IN')}`
        : 'Enterprise Quote Required';
    }

    // Compatibility
    const compatEl = document.getElementById('modalProductCompat');
    if (compatEl) {
      compatEl.textContent = p.compatibility || 'Engineered for standard agricultural shed enclosures and SeriCare Setu IoT Gateway infrastructure.';
    }

    // Specs table
    const tableEl = document.getElementById('modalSpecsTable');
    if (tableEl) {
      const specs = p.specifications || {};
      if (Object.keys(specs).length === 0) {
        tableEl.innerHTML = '<tr><td colspan="2" style="color: var(--slate-500);">Standard industrial IoT specifications apply.</td></tr>';
      } else {
        tableEl.innerHTML = Object.entries(specs).map(([key, value]) => `
          <tr>
            <th>${escapeHtml(key)}</th>
            <td>${escapeHtml(String(value))}</td>
          </tr>
        `).join('');
      }
    }

    // Wire quote button in modal
    const quoteBtn = document.getElementById('modalProductQuoteBtn');
    if (quoteBtn) {
      quoteBtn.onclick = () => {
        closeAllModals();
        selectProductForQuote(p.id, p.name);
      };
    }

    modal.classList.add('open');
    if (window.lucide) lucide.createIcons();
  } catch (err) {
    alert('Unable to load specifications for the requested product.');
  }
}

// ==========================================================================
// 5. FAQS ACCORDION (DATABASE-BACKED HYDRATION)
// ==========================================================================
async function fetchFaqs() {
  try {
    const res = await fetch(`${API_BASE_URL}/public/faqs`);
    if (!res.ok) return;
    const faqs = await res.json();
    if (faqs && faqs.length > 0) {
      renderFaqs(faqs);
    } else {
      wireAccordionItems();
    }
  } catch (err) {
    // If backend unreachable, wire existing SSR elements
    wireAccordionItems();
  }
}

function sanitizeFaqHtml(raw) {
  if (!raw) return '';
  // Whitelist safe semantic tags for formatted answers
  return raw
    .replace(/<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>/gi, '')
    .replace(/on\w+="[^"]*"/gi, '')
    .replace(/javascript:[^"']*/gi, '');
}

function formatFaqAnswer(rawAnswer) {
  if (!rawAnswer) return '';

  // If answer already has rich HTML markup, sanitize and render
  if (/<(p|ul|li|div|strong|span|em)\b[^>]*>/i.test(rawAnswer)) {
    return sanitizeFaqHtml(rawAnswer);
  }

  // Parse structured text: (1) ... (2) ... (3) ...
  const numPointRegex = /\(([0-9]+)\)\s*([^()]+?)(?=\s*\([0-9]+\)|$|\.\s+[A-Z])/g;
  const matches = [...rawAnswer.matchAll(numPointRegex)];

  if (matches.length >= 2) {
    const firstIndex = rawAnswer.indexOf(matches[0][0]);
    const leadText = rawAnswer.substring(0, firstIndex).trim();
    const lastMatch = matches[matches.length - 1];
    const afterIndex = rawAnswer.indexOf(lastMatch[0]) + lastMatch[0].length;
    const trailingText = rawAnswer.substring(afterIndex).trim();

    let html = '';
    if (leadText) {
      html += `<p>${escapeHtml(leadText)}</p>`;
    }

    html += '<ul class="faq-list">';
    matches.forEach(m => {
      let itemContent = m[2].trim();
      const colonMatch = itemContent.match(/^([^:()]{2,30}):\s*(.*)$/);
      if (colonMatch) {
        html += `<li><strong>${escapeHtml(colonMatch[1])}:</strong> ${escapeHtml(colonMatch[2])}</li>`;
      } else {
        html += `<li>${escapeHtml(itemContent)}</li>`;
      }
    });
    html += '</ul>';

    if (trailingText) {
      html += `<div class="faq-highlight-note">${escapeHtml(trailingText)}</div>`;
    }
    return html;
  }

  // Split multiple paragraphs if any
  const paragraphs = rawAnswer.split(/\n\s*\n/);
  return paragraphs.map(p => `<p>${escapeHtml(p.trim())}</p>`).join('');
}

function renderFaqs(faqs) {
  const wrap = document.getElementById('faqsAccordionWrap');
  if (!wrap) return;

  wrap.innerHTML = faqs.map((faq, index) => `
    <div class="faq-accordion-item ${index === 0 ? 'open' : ''}">
      <button class="faq-header-btn" type="button" aria-expanded="${index === 0 ? 'true' : 'false'}">
        <span>${escapeHtml(faq.question)}</span>
        <i data-lucide="chevron-down" class="faq-chevron"></i>
      </button>
      <div class="faq-body-content">
        ${formatFaqAnswer(faq.answer)}
      </div>
    </div>
  `).join('');

  if (window.lucide) lucide.createIcons();
  wireAccordionItems();
}

function wireAccordionItems() {
  const items = document.querySelectorAll('.faq-accordion-item');
  items.forEach(item => {
    const headerBtn = item.querySelector('.faq-header-btn');
    if (!headerBtn) return;

    headerBtn.onclick = () => {
      const wasOpen = item.classList.contains('open');
      // Close other accordions
      items.forEach(other => {
        other.classList.remove('open');
        const otherBtn = other.querySelector('.faq-header-btn');
        if (otherBtn) otherBtn.setAttribute('aria-expanded', 'false');
      });

      if (!wasOpen) {
        item.classList.add('open');
        headerBtn.setAttribute('aria-expanded', 'true');
      }
    };
  });
}

// ==========================================================================
// 6. ENQUIRY / DEMO FORM SUBMISSION (RFC VALIDATED + DATABASE CRM)
// ==========================================================================
function initEnquiryForm() {
  const form = document.getElementById('enquiryForm');
  const successCard = document.getElementById('enquirySuccessCard');
  const resetBtn = document.getElementById('resetEnquiryBtn');
  const errorBox = document.getElementById('formErrorMessage');
  const submitBtn = document.getElementById('submitEnquiryBtn');

  if (!form) return;

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    errorBox.style.display = 'none';
    errorBox.textContent = '';

    // Values
    const fullName = document.getElementById('fullName').value.trim();
    const organization = document.getElementById('organization').value.trim();
    const email = document.getElementById('email').value.trim();
    const phone = document.getElementById('phone').value.trim();
    const stateRegion = document.getElementById('stateRegion').value;
    const enquiryType = document.getElementById('enquiryType').value;
    const productId = document.getElementById('productSelect').value;
    const message = document.getElementById('message').value.trim();
    const privacyConsent = document.getElementById('privacyConsent').checked;

    // Client-side Validations
    if (!fullName || !organization || !email || !phone || !stateRegion || !message) {
      showError('Please fill in all mandatory fields marked with an asterisk (*).');
      return;
    }

    const emailPattern = /^[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-zA-Z0-9-]+(?:\.[a-zA-Z0-9-]+)+$/;
    if (!emailPattern.test(email)) {
      showError('Please enter a valid RFC-compliant corporate or personal email address.');
      return;
    }

    const cleanPhone = phone.replace(/[^0-9]/g, '');
    if (cleanPhone.length < 10) {
      showError('Please enter a valid phone or WhatsApp number containing at least 10 digits.');
      return;
    }

    if (!privacyConsent) {
      showError('Please consent to the privacy policy so our engineers can contact you regarding your shed.');
      return;
    }

    // Prepare payload
    let selectedProductName = null;
    if (productId) {
      const match = allProductsCache.find(p => p.id === productId);
      if (match) selectedProductName = match.name;
    }

    const payload = {
      full_name: fullName,
      organization: organization,
      email: email,
      phone: phone,
      state_region: stateRegion,
      product_id: productId || null,
      product_name: selectedProductName,
      enquiry_type: enquiryType,
      message: message,
      privacy_consent: true
    };

    submitBtn.disabled = true;
    submitBtn.innerHTML = '<span>Submitting to CRM...</span>';

    try {
      const res = await fetch(`${API_BASE_URL}/public/enquiries`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || 'Failed to submit inquiry. Please try again.');
      }

      // Display Confirmation Card with Reference ID
      document.getElementById('enquiryReferenceBadge').textContent = data.enquiry_reference;
      form.style.display = 'none';
      successCard.style.display = 'block';
      if (window.lucide) lucide.createIcons();

      // Scroll into view
      successCard.scrollIntoView({ behavior: 'smooth', block: 'center' });
    } catch (err) {
      showError(err.message || 'Network error while submitting enquiry. Please try again.');
    } finally {
      submitBtn.disabled = false;
      submitBtn.innerHTML = '<i data-lucide="send"></i><span>Submit Official Inquiry</span>';
      if (window.lucide) lucide.createIcons();
    }
  });

  if (resetBtn) {
    resetBtn.addEventListener('click', () => {
      form.reset();
      form.style.display = 'block';
      successCard.style.display = 'none';
      errorBox.style.display = 'none';
    });
  }

  function showError(msg) {
    errorBox.textContent = msg;
    errorBox.style.display = 'block';
    errorBox.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }
}

// ==========================================================================
// 7. MODALS & LEGAL POLICIES (ACCESSIBILITY & KEYBOARD HANDLERS)
// ==========================================================================
function initModals() {
  const closeBtns = [
    document.getElementById('modalProductCloseBtn'),
    document.getElementById('privacyModalCloseBtn'),
    document.getElementById('termsModalCloseBtn')
  ];

  closeBtns.forEach(btn => {
    if (btn) btn.addEventListener('click', closeAllModals);
  });

  // Backdrop click
  document.querySelectorAll('.modal-overlay').forEach(overlay => {
    overlay.addEventListener('click', (e) => {
      if (e.target === overlay) {
        closeAllModals();
      }
    });
  });

  // ESC key
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      closeAllModals();
    }
  });

  // Triggers for Privacy & Terms
  const privTrigger = document.getElementById('privacyModalTrigger');
  if (privTrigger) {
    privTrigger.addEventListener('click', () => {
      document.getElementById('privacyModal').classList.add('open');
      if (window.lucide) lucide.createIcons();
    });
  }

  const termsTrigger = document.getElementById('termsModalTrigger');
  if (termsTrigger) {
    termsTrigger.addEventListener('click', () => {
      document.getElementById('termsModal').classList.add('open');
      if (window.lucide) lucide.createIcons();
    });
  }
}

function closeAllModals() {
  document.querySelectorAll('.modal-overlay').forEach(modal => {
    modal.classList.remove('open');
  });
}

// ==========================================================================
// 8. SCROLL SPY FOR NAVIGATION
// ==========================================================================
function setupScrollSpy() {
  const sections = document.querySelectorAll('section[id]');
  const navLinks = document.querySelectorAll('.nav-desktop .nav-item-link');

  window.addEventListener('scroll', () => {
    let currentId = '';
    const scrollPos = window.scrollY + 100;

    sections.forEach(sec => {
      const top = sec.offsetTop;
      const height = sec.offsetHeight;
      if (scrollPos >= top && scrollPos < top + height) {
        currentId = sec.getAttribute('id');
      }
    });

    if (currentId) {
      navLinks.forEach(link => {
        link.classList.remove('active');
        if (link.getAttribute('href') === `#${currentId}`) {
          link.classList.add('active');
        }
      });
    }
  }, { passive: true });
}

// ==========================================================================
// 9. SECURITY & SANITIZATION UTILITIES
// ==========================================================================
function escapeHtml(str) {
  if (str === null || str === undefined) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}


// ==========================================================================
// 10. PRODUCT BUY & CHECKOUT SYSTEM
// ==========================================================================
let activeCheckoutProduct = null;
let checkoutQuantity = 1;
let selectedPaymentMethod = 'UPI';
let currentModalProduct = null;
let currentAuthenticatedUser = null;

async function checkUserAuth() {
  const token = sessionStorage.getItem('setu_tab_token') || localStorage.getItem('setu_token');
  if (!token) {
    currentAuthenticatedUser = null;
    return null;
  }
  try {
    const res = await fetch(`${API_BASE_URL}/auth/me`, {
      headers: { 'Authorization': `Bearer ${token}` }
    });
    if (res.ok) {
      currentAuthenticatedUser = await res.json();
      return currentAuthenticatedUser;
    } else {
      currentAuthenticatedUser = null;
      return null;
    }
  } catch (e) {
    currentAuthenticatedUser = null;
    return null;
  }
}

async function openBuyProductModal(productId) {
  const modal = document.getElementById('productCheckoutModal');
  if (!modal) return;

  // Find product from memory or fetch
  let p = (typeof allProducts !== 'undefined' && Array.isArray(allProducts))
    ? allProducts.find(item => item.id === productId || item.slug === productId)
    : null;
  if (!p) {
    try {
      const res = await fetch(`${API_BASE_URL}/public/products/${encodeURIComponent(productId)}`);
      if (res.ok) p = await res.json();
    } catch (e) {}
  }
  if (!p) {
    alert('Product details could not be retrieved.');
    return;
  }

  activeCheckoutProduct = p;
  checkoutQuantity = 1;
  selectedPaymentMethod = 'UPI';

  // Reset form views
  const formView = document.getElementById('checkoutFormView');
  const successView = document.getElementById('checkoutSuccessView');
  const errBox = document.getElementById('checkoutErrorBox');
  if (formView) {
    formView.style.display = 'block';
    formView.classList.remove('hidden');
  }
  if (successView) {
    successView.style.display = 'none';
    successView.classList.add('hidden');
  }
  if (errBox) {
    errBox.style.display = 'none';
    errBox.classList.add('hidden');
    errBox.textContent = '';
  }

  // Populate product details
  const nameEl = document.getElementById('checkoutProductName');
  const skuEl = document.getElementById('checkoutProductSku');
  const catEl = document.getElementById('checkoutProductCategory');
  const qtyEl = document.getElementById('checkoutQuantity');
  const imgEl = document.getElementById('checkoutProductImg');
  const imgWrap = document.getElementById('checkoutProductImgWrap');

  if (nameEl) nameEl.textContent = p.name;
  if (skuEl) skuEl.textContent = p.sku;
  if (catEl) catEl.textContent = p.category;
  if (qtyEl) qtyEl.value = '1';

  if (imgEl && imgWrap) {
    if (p.images && Array.isArray(p.images) && p.images.length > 0 && p.images[0]) {
      imgEl.src = p.images[0];
      imgWrap.style.display = 'flex';
    } else {
      imgWrap.style.display = 'none';
      imgEl.src = '';
    }
  }

  selectPaymentMethod('UPI');
  updateCheckoutCalculation();

  // Check auth and render
  await checkUserAuth();
  renderCheckoutAuthSection();

  // If user is logged in and farm_name or region exists, prefill address if empty
  const addrInput = document.getElementById('checkoutShippingAddress');
  if (addrInput && !addrInput.value.trim() && currentAuthenticatedUser) {
    const parts = [];
    if (currentAuthenticatedUser.farm_name) parts.push(`Shed: ${currentAuthenticatedUser.farm_name}`);
    if (currentAuthenticatedUser.region) parts.push(`Region: ${currentAuthenticatedUser.region}`);
    if (parts.length > 0) addrInput.value = parts.join(', ');
  }

  modal.classList.add('open');
  if (window.lucide) lucide.createIcons();
}

function closeCheckoutModal() {
  const modal = document.getElementById('productCheckoutModal');
  if (modal) modal.classList.remove('open');
}

function adjustCheckoutQty(delta) {
  const input = document.getElementById('checkoutQuantity');
  if (!input) return;
  let val = parseInt(input.value, 10) || 1;
  val = Math.max(1, Math.min(99, val + delta));
  input.value = val;
  checkoutQuantity = val;
  updateCheckoutCalculation();
}

function updateCheckoutCalculation() {
  if (!activeCheckoutProduct) return;
  const input = document.getElementById('checkoutQuantity');
  if (input) {
    checkoutQuantity = parseInt(input.value, 10) || 1;
  }
  const unitMinor = activeCheckoutProduct.price_minor_units || 0;
  const unitRupees = unitMinor / 100;
  const subtotal = unitRupees * checkoutQuantity;
  const gst = subtotal * 0.18;
  const total = subtotal + gst;

  const unitPriceEl = document.getElementById('checkoutUnitUnitPrice');
  const qtySummaryEl = document.getElementById('checkoutQtySummary');
  const subtotalEl = document.getElementById('checkoutCostSubtotal');
  const gstEl = document.getElementById('checkoutCostGst');
  const totalEl = document.getElementById('checkoutCostTotal');
  const submitBtnText = document.getElementById('checkoutSubmitBtnText');

  if (unitPriceEl) unitPriceEl.textContent = `\u20B9${unitRupees.toLocaleString('en-IN', {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
  if (qtySummaryEl) qtySummaryEl.textContent = `${checkoutQuantity} unit${checkoutQuantity > 1 ? 's' : ''}`;
  if (subtotalEl) subtotalEl.textContent = `\u20B9${subtotal.toLocaleString('en-IN', {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
  if (gstEl) gstEl.textContent = `\u20B9${gst.toLocaleString('en-IN', {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
  if (totalEl) totalEl.textContent = `\u20B9${total.toLocaleString('en-IN', {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;

  if (submitBtnText) {
    const formattedTotal = `\u20B9${total.toLocaleString('en-IN', {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
    if (!currentAuthenticatedUser) {
      submitBtnText.textContent = `Sign In & Place Order \u00B7 ${formattedTotal}`;
    } else {
      submitBtnText.textContent = `Place Order \u00B7 ${formattedTotal}`;
    }
  }
}

function selectPaymentMethod(method) {
  selectedPaymentMethod = method;
  ['UPI', 'CARD', 'COD'].forEach(m => {
    const card = document.getElementById(`payMethodCard-${m}`);
    if (card) {
      if (m === method) card.classList.add('active');
      else card.classList.remove('active');
    }
  });
}

function renderCheckoutAuthSection() {
  const userBox = document.getElementById('checkoutUserStatusBox');
  const userText = document.getElementById('checkoutLoggedInUserText');
  
  if (currentAuthenticatedUser) {
    if (userBox) {
      userBox.style.display = 'flex';
      userBox.classList.remove('hidden');
    }
    if (userText) {
      const name = currentAuthenticatedUser.full_name || currentAuthenticatedUser.username || 'Farmer';
      const farm = currentAuthenticatedUser.farm_name ? ` ? ${currentAuthenticatedUser.farm_name}` : '';
      userText.textContent = `Logged in as ${name}${farm}`;
    }
  } else {
    if (userBox) {
      userBox.style.display = 'none';
      userBox.classList.add('hidden');
    }
  }
  updateCheckoutCalculation();
  if (window.lucide) lucide.createIcons();
}

function switchCheckoutAuthTab(tab) {
  const tabSignIn = document.getElementById('tabBtnSignIn');
  const tabReg = document.getElementById('tabBtnRegister');
  const formSignIn = document.getElementById('checkoutSignInFormWrap');
  const formReg = document.getElementById('checkoutRegisterFormWrap');

  if (tab === 'signin') {
    if (tabSignIn) tabSignIn.classList.add('active');
    if (tabReg) tabReg.classList.remove('active');
    if (formSignIn) formSignIn.classList.remove('hidden');
    if (formReg) formReg.classList.add('hidden');
  } else {
    if (tabReg) tabReg.classList.add('active');
    if (tabSignIn) tabSignIn.classList.remove('active');
    if (formReg) formReg.classList.remove('hidden');
    if (formSignIn) formSignIn.classList.add('hidden');
  }
}

async function handleCheckoutLogin() {
  const userEl = document.getElementById('checkoutLoginUser');
  const passEl = document.getElementById('checkoutLoginPass');
  const msgEl = document.getElementById('checkoutLoginMsg');
  const btn = document.getElementById('checkoutBtnDoLogin');

  const username = userEl ? userEl.value.trim() : '';
  const password = passEl ? passEl.value : '';

  if (!username || !password) {
    if (msgEl) {
      msgEl.className = 'checkout-auth-msg error';
      msgEl.textContent = 'Please enter your phone number / username and password.';
      msgEl.classList.remove('hidden');
    }
    return;
  }

  if (btn) {
    btn.disabled = true;
    btn.textContent = 'Authenticating...';
  }

  try {
    const res = await fetch(`${API_BASE_URL}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password })
    });
    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.detail || 'Invalid phone/username or password');
    }

    const token = data.access_token || data.token;
    sessionStorage.setItem('setu_tab_token', token);
    localStorage.setItem('setu_token', token);
    if (data.user) {
      localStorage.setItem('setu_user', JSON.stringify(data.user));
    }

    await checkUserAuth();
    renderCheckoutAuthSection();
  } catch (err) {
    if (msgEl) {
      msgEl.className = 'checkout-auth-msg error';
      msgEl.textContent = err.message || 'Login failed';
      msgEl.classList.remove('hidden');
    }
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.textContent = 'Sign In & Continue';
    }
  }
}

async function handleCheckoutRegister() {
  const nameEl = document.getElementById('checkoutRegName');
  const phoneEl = document.getElementById('checkoutRegPhone');
  const farmEl = document.getElementById('checkoutRegFarm');
  const stateEl = document.getElementById('checkoutRegState');
  const passEl = document.getElementById('checkoutRegPass');
  const msgEl = document.getElementById('checkoutRegMsg');
  const btn = document.getElementById('checkoutBtnDoRegister');

  const fullName = nameEl ? nameEl.value.trim() : '';
  const phone = phoneEl ? phoneEl.value.trim().replace(/\D/g, '') : '';
  const farmName = farmEl ? farmEl.value.trim() : '';
  const state = stateEl ? stateEl.value : 'Karnataka';
  const password = passEl ? passEl.value : '';

  if (!fullName || !phone || !farmName || !password) {
    if (msgEl) {
      msgEl.className = 'checkout-auth-msg error';
      msgEl.textContent = 'Please fill all required fields.';
      msgEl.classList.remove('hidden');
    }
    return;
  }

  if (phone.length < 10) {
    if (msgEl) {
      msgEl.className = 'checkout-auth-msg error';
      msgEl.textContent = 'Please enter a valid 10-digit mobile number.';
      msgEl.classList.remove('hidden');
    }
    return;
  }

  if (password.length < 8) {
    if (msgEl) {
      msgEl.className = 'checkout-auth-msg error';
      msgEl.textContent = 'Password must be at least 8 characters.';
      msgEl.classList.remove('hidden');
    }
    return;
  }

  if (btn) {
    btn.disabled = true;
    btn.textContent = 'Creating Account...';
  }

  try {
    const regPayload = {
      full_name: fullName,
      phone_number: phone,
      username: phone,
      password: password,
      role: 'farmer',
      farm_name: farmName,
      region: state
    };

    const regRes = await fetch(`${API_BASE_URL}/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(regPayload)
    });
    const regData = await regRes.json();
    if (!regRes.ok) {
      throw new Error(regData.detail || 'Registration failed');
    }

    // Now auto-login with credentials
    const loginRes = await fetch(`${API_BASE_URL}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username: phone, password: password })
    });
    const loginData = await loginRes.json();
    if (loginRes.ok) {
      const token = loginData.access_token || loginData.token;
      sessionStorage.setItem('setu_tab_token', token);
      localStorage.setItem('setu_token', token);
      if (loginData.user) {
        localStorage.setItem('setu_user', JSON.stringify(loginData.user));
      }
    }

    await checkUserAuth();
    renderCheckoutAuthSection();
  } catch (err) {
    if (msgEl) {
      msgEl.className = 'checkout-auth-msg error';
      msgEl.textContent = err.message || 'Registration failed';
      msgEl.classList.remove('hidden');
    }
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.textContent = 'Register & Continue';
    }
  }
}

function logoutFromCheckout() {
  sessionStorage.removeItem('setu_tab_token');
  localStorage.removeItem('setu_token');
  localStorage.removeItem('setu_user');
  currentAuthenticatedUser = null;
  renderCheckoutAuthSection();
}

async function submitCheckoutOrder() {
  const errBox = document.getElementById('checkoutErrorBox');
  if (errBox) {
    errBox.classList.add('hidden');
    errBox.textContent = '';
  }

  // 1. Check Product
  if (!activeCheckoutProduct) {
    if (errBox) {
      errBox.textContent = 'No product selected. Please select a product to buy.';
      errBox.classList.remove('hidden');
    }
    return;
  }

  // 2. Validate Shipping Address
  const addrEl = document.getElementById('checkoutShippingAddress');
  const shippingAddress = addrEl ? addrEl.value.trim() : '';

  // 3. Check Authentication
  const token = sessionStorage.getItem('setu_tab_token') || localStorage.getItem('setu_token');
  let user = null;
  if (token) {
    user = await checkUserAuth();
  }

  // IF USER IS NOT LOGGED IN -> Redirect directly to login page!
  if (!user || !token) {
    // Save pending checkout state
    const pendingCheckout = {
      product_id: activeCheckoutProduct.id,
      quantity: checkoutQuantity,
      shipping_address: shippingAddress,
      payment_method: selectedPaymentMethod
    };
    sessionStorage.setItem('setu_pending_checkout', JSON.stringify(pendingCheckout));
    sessionStorage.setItem('setu_checkout_product_id', activeCheckoutProduct.id);
    localStorage.setItem('setu_pending_checkout', JSON.stringify(pendingCheckout));

    // Redirect directly to login page
    window.location.href = `/login?redirect=checkout&product_id=${encodeURIComponent(activeCheckoutProduct.id)}&qty=${checkoutQuantity}`;
    return;
  }

  // USER IS LOGGED IN -> Validate Shipping Address
  if (!shippingAddress || shippingAddress.length < 5) {
    if (addrEl) addrEl.focus();
    if (errBox) {
      errBox.textContent = 'Please enter your complete rearing shed or delivery address.';
      errBox.classList.remove('hidden');
    }
    return;
  }

  const submitBtn = document.getElementById('checkoutSubmitOrderBtn');
  const submitBtnText = document.getElementById('checkoutSubmitBtnText');
  if (submitBtn) submitBtn.disabled = true;
  if (submitBtnText) submitBtnText.textContent = 'Placing verified order...';

  try {
    const orderPayload = {
      items: [
        {
          product_id: activeCheckoutProduct.id,
          quantity: checkoutQuantity
        }
      ],
      shipping_address: shippingAddress,
      payment_method: selectedPaymentMethod,
      notes: `Direct purchase from Setu Web Portal (${selectedPaymentMethod})`
    };

    const res = await fetch(`${API_BASE_URL}/orders`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify(orderPayload)
    });

    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.detail || 'Unable to process order. Please try again.');
    }

    // Clear pending checkout on successful purchase
    sessionStorage.removeItem('setu_pending_checkout');
    sessionStorage.removeItem('setu_checkout_product_id');
    localStorage.removeItem('setu_pending_checkout');

    // Show Confirmation View
    const formView = document.getElementById('checkoutFormView');
    const successView = document.getElementById('checkoutSuccessView');
    if (formView) {
      formView.style.display = 'none';
      formView.classList.add('hidden');
    }
    if (successView) {
      successView.style.display = 'block';
      successView.classList.remove('hidden');
    }

    const orderNumEl = document.getElementById('receiptOrderNum');
    const invNumEl = document.getElementById('receiptInvoiceNum');
    const purchaserEl = document.getElementById('receiptPurchaser');
    const amountEl = document.getElementById('receiptAmountPaid');
    const payModeEl = document.getElementById('receiptPaymentMethod');
    const statusEl = document.getElementById('receiptStatus');

    if (orderNumEl) orderNumEl.textContent = data.order_number || data.id;
    if (invNumEl) {
      const invNum = data.invoices && data.invoices.length > 0 ? data.invoices[0].invoice_number : `INV-${data.order_number || ''}`;
      invNumEl.textContent = invNum;
    }
    if (purchaserEl) {
      purchaserEl.textContent = `${user.full_name || user.username} (${user.phone_number || user.username})`;
    }
    if (amountEl) {
      const totalRupees = (data.total_amount_minor_units || 0) / 100;
      amountEl.textContent = `\u20B9${totalRupees.toLocaleString('en-IN', {minimumFractionDigits: 2})}`;
    }
    if (payModeEl) payModeEl.textContent = selectedPaymentMethod;
    if (statusEl) statusEl.textContent = 'CONFIRMED \u00B7 DISPATCH PREP';

    if (window.lucide) lucide.createIcons();
  } catch (err) {
    if (errBox) {
      errBox.textContent = err.message || 'Error occurred while placing order.';
      errBox.classList.remove('hidden');
    }
    if (submitBtn) submitBtn.disabled = false;
    updateCheckoutCalculation();
  }
}

// Window exports
window.openBuyProductModal = openBuyProductModal;
window.closeCheckoutModal = closeCheckoutModal;
window.buyCurrentModalProduct = function() {
  if (!currentModalProduct) return;
  closeAllModals();
  openBuyProductModal(currentModalProduct.id);
};
window.adjustCheckoutQty = adjustCheckoutQty;
window.selectPaymentMethod = selectPaymentMethod;
window.switchCheckoutAuthTab = switchCheckoutAuthTab;
window.handleCheckoutLogin = handleCheckoutLogin;
window.handleCheckoutRegister = handleCheckoutRegister;
window.logoutFromCheckout = logoutFromCheckout;
window.submitCheckoutOrder = submitCheckoutOrder;

async function checkPendingCheckoutOnLoad() {
  const urlParams = new URLSearchParams(window.location.search);
  const buyParam = urlParams.get('buy');
  const pendingRaw = sessionStorage.getItem('setu_pending_checkout') || localStorage.getItem('setu_pending_checkout');
  let pending = null;
  if (pendingRaw) {
    try { pending = JSON.parse(pendingRaw); } catch (e) {}
  }

  const targetProductId = buyParam || (pending ? pending.product_id : null);
  if (!targetProductId) return;

  // Clean URL query param so refresh doesn't reopen indefinitely
  if (buyParam) {
    const cleanUrl = window.location.pathname + window.location.hash;
    window.history.replaceState({}, document.title, cleanUrl);
  }

  // Ensure products are loaded first
  if (typeof allProducts === 'undefined' || allProducts.length === 0) {
    if (typeof fetchProducts === 'function') await fetchProducts();
  }

  // Open the checkout modal directly for that product
  await openBuyProductModal(targetProductId);

  // Restore saved quantity and address if available
  if (pending) {
    if (pending.quantity) {
      const qtyEl = document.getElementById('checkoutQuantity');
      if (qtyEl) {
        qtyEl.value = pending.quantity;
        checkoutQuantity = pending.quantity;
        updateCheckoutCalculation();
      }
    }
    if (pending.shipping_address) {
      const addrEl = document.getElementById('checkoutShippingAddress');
      if (addrEl && pending.shipping_address) {
        addrEl.value = pending.shipping_address;
      }
    }
    if (pending.payment_method) {
      selectPaymentMethod(pending.payment_method);
    }
  }
}

// Check pending checkout after initialization
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => {
    setTimeout(checkPendingCheckoutOnLoad, 400);
  });
} else {
  setTimeout(checkPendingCheckoutOnLoad, 400);
}
