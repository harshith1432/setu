/**
 * Setu Enterprise Table Engine
 * Universal Bulk Selection & Left-Corner Pagination across all platform tables.
 */

(function () {
  'use strict';

  function getAuthToken() {
    return window.adminToken ||
      sessionStorage.getItem('setu_tab_token') ||
      localStorage.getItem('setu_admin_token') ||
      '';
  }

  function getApiBaseUrl() {
    if (window.API_BASE_URL) return window.API_BASE_URL;
    const isLocalHost = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
    return isLocalHost
      ? `${window.location.origin}/api/v1`
      : 'https://setu-8vh9.onrender.com/api/v1';
  }


  const SetuTableManager = {
    tables: {},
    observers: {},

    PAGE_SIZES: [10, 20, 30, 50, 100, 'all'],

    // Table display names for official notifications & modal prompts
    tableNames: {
      tasksTable: 'Tasks & Queue',
      farmersTable: 'Enrolled Farmers',
      devicesTable: 'IoT Gateways',
      sensorsTable: 'Sensors',
      alertsTable: 'Incidents & Alerts',
      productsTable: 'Catalogue Products',
      ordersTable: 'Customer Orders',
      subsTable: 'Subscriptions',
      invoicesTable: 'Billing Invoices',
      ticketsTable: 'Support Tickets',
      installationsTable: 'Installation Jobs',
      teamTable: 'Field Technicians',
      usersTable: 'User Accounts',
      employeesTable: 'Corporate Employees',
      customRolesTable: 'Security Roles',
      departmentsTable: 'Departments',
      auditTable: 'Security Audit Logs'
    },

    getState(tableId) {
      if (!this.tables[tableId]) {
        this.tables[tableId] = {
          currentPage: 1,
          pageSize: 10,
          selectedIds: new Set(),
          isSyncing: false
        };
      }
      return this.tables[tableId];
    },

    extractRowId(tr, idx) {
      if (tr.dataset.id) return tr.dataset.id;
      const chk = tr.querySelector('.row-select-checkbox');
      if (chk && chk.dataset.rowId) return chk.dataset.rowId;

      // Extract from trigger button onclick attribute
      const trigger = tr.querySelector('.action-dots-trigger, .row-action-item');
      if (trigger) {
        const onclickAttr = trigger.getAttribute('onclick') || '';
        const match = onclickAttr.match(/['"](farmer-[^'"]+|prod-[^'"]+|order-[^'"]+|ticket-[^'"]+|job-[^'"]+|sensor-[^'"]+|dev-[^'"]+|alert-[^'"]+|emp-[^'"]+|role-[^'"]+|dept-[^'"]+|[^'"]+)['"]/);
        if (match && match[1]) {
          const rawId = match[1];
          return rawId.replace(/^(farmer-|prod-|order-|ticket-|job-|sensor-|dev-|alert-|emp-|role-|dept-)/, '');
        }
      }

      // Fallback: text from first data cell (skipping bulk select column)
      if (tr.cells && tr.cells.length > 0) {
        for (let i = 0; i < tr.cells.length; i++) {
          const cell = tr.cells[i];
          if (!cell.classList.contains('td-bulk-select')) {
            const text = cell.textContent.trim().replace(/\s+/g, '_');
            if (text) return text;
          }
        }
      }
      return `row_${idx}`;
    },

    extractRowName(tr) {
      if (!tr.cells || tr.cells.length === 0) return 'Record';
      // Look for cell with font-weight: 700 or first non-empty text cell
      for (let i = 0; i < Math.min(3, tr.cells.length); i++) {
        const cell = tr.cells[i];
        if (!cell.classList.contains('td-bulk-select')) {
          const txt = cell.textContent.trim();
          if (txt && txt !== '--') return txt;
        }
      }
      return 'Record';
    },

    syncTable(tableId) {
      const table = document.getElementById(tableId);
      if (!table) return;
      const tbody = table.querySelector('tbody');
      if (!tbody) return;

      const state = this.getState(tableId);
      if (state.isSyncing) return;
      state.isSyncing = true;

      try {
        const rows = Array.from(tbody.querySelectorAll('tr')).filter(r => {
          return !r.querySelector('.honest-empty-state') && !r.querySelector('td[colspan]');
        });

        const totalRows = rows.length;
        const paginationWrap = document.getElementById(`${tableId}_paginationWrap`);
        const bulkBar = document.getElementById(`${tableId}_bulkActionBar`);

        if (totalRows === 0) {
          if (paginationWrap) paginationWrap.style.display = 'none';
          if (bulkBar) bulkBar.classList.add('hidden');
          return;
        }

        if (paginationWrap) paginationWrap.style.display = 'flex';

        // Ensure header has the checkbox column at the first column (full left side)
        const theadTr = table.querySelector('thead tr');
        if (theadTr) {
          let thCheck = theadTr.querySelector('.th-bulk-select');
          if (!thCheck) {
            thCheck = document.createElement('th');
            thCheck.className = 'th-bulk-select';
            thCheck.style.width = '44px';
            thCheck.style.textAlign = 'center';
            thCheck.title = 'Select All Rows';
            thCheck.innerHTML = `<input type="checkbox" class="bulk-select-all" aria-label="Select All" onchange="SetuTableManager.toggleSelectAll('${tableId}', this.checked)">`;
            theadTr.insertBefore(thCheck, theadTr.firstElementChild);
          } else if (theadTr.firstElementChild !== thCheck) {
            theadTr.insertBefore(thCheck, theadTr.firstElementChild);
          }
        }

        // Ensure each row has the checkbox in the first column (full left side)
        rows.forEach((tr, idx) => {
          const rowId = this.extractRowId(tr, idx);
          tr.dataset.id = rowId;

          let checkCell = tr.querySelector('.td-bulk-select');
          if (!checkCell) {
            checkCell = document.createElement('td');
            checkCell.className = 'td-bulk-select';
            checkCell.style.textAlign = 'center';
            checkCell.style.verticalAlign = 'middle';
            checkCell.innerHTML = `<input type="checkbox" class="row-select-checkbox" data-row-id="${rowId}" aria-label="Select Row">`;
            tr.insertBefore(checkCell, tr.firstElementChild);
          } else if (tr.firstElementChild !== checkCell) {
            tr.insertBefore(checkCell, tr.firstElementChild);
          }

          const checkbox = checkCell.querySelector('input[type="checkbox"]');
          if (checkbox) {
            checkbox.checked = state.selectedIds.has(rowId);
            checkbox.onchange = (e) => {
              this.handleRowCheck(tableId, rowId, e.target);
            };
          }

          if (state.selectedIds.has(rowId)) {
            tr.classList.add('row-selected');
          } else {
            tr.classList.remove('row-selected');
          }
        });

        // Calculate pagination slices
        const effectivePageSize = state.pageSize === 'all' ? totalRows : parseInt(state.pageSize, 10);
        const totalPages = Math.ceil(totalRows / effectivePageSize) || 1;

        if (state.currentPage > totalPages) state.currentPage = totalPages;
        if (state.currentPage < 1) state.currentPage = 1;

        const startIdx = (state.currentPage - 1) * effectivePageSize;
        const endIdx = Math.min(startIdx + effectivePageSize, totalRows);

        // Apply slice visibility
        rows.forEach((tr, idx) => {
          if (idx >= startIdx && idx < endIdx) {
            tr.style.display = '';
          } else {
            tr.style.display = 'none';
          }
        });

        // Update pagination bar elements
        if (paginationWrap) {
          const currPageEl = paginationWrap.querySelector('.curr-page');
          const totalPagesEl = paginationWrap.querySelector('.total-pages');
          const pageStartEl = paginationWrap.querySelector('.page-start');
          const pageEndEl = paginationWrap.querySelector('.page-end');
          const pageTotalEl = paginationWrap.querySelector('.page-total');
          const prevBtn = paginationWrap.querySelector('.prev-btn');
          const nextBtn = paginationWrap.querySelector('.next-btn');
          const selectEl = paginationWrap.querySelector('.pagination-select');

          if (currPageEl) currPageEl.textContent = state.currentPage;
          if (totalPagesEl) totalPagesEl.textContent = totalPages;
          if (pageStartEl) pageStartEl.textContent = startIdx + 1;
          if (pageEndEl) pageEndEl.textContent = endIdx;
          if (pageTotalEl) pageTotalEl.textContent = totalRows;

          if (prevBtn) prevBtn.disabled = (state.currentPage <= 1);
          if (nextBtn) nextBtn.disabled = (state.currentPage >= totalPages);

          if (selectEl && selectEl.value !== String(state.pageSize)) {
            selectEl.value = String(state.pageSize);
          }
        }

        // Update bulk action toolbar
        if (bulkBar) {
          const selectedCount = state.selectedIds.size;
          const countEl = bulkBar.querySelector('.bulk-count');
          if (countEl) countEl.textContent = selectedCount;

          if (selectedCount > 0) {
            bulkBar.classList.remove('hidden');
          } else {
            bulkBar.classList.add('hidden');
          }
        }

        // Update header Select All checkbox
        const headerCheck = table.querySelector('thead .bulk-select-all');
        if (headerCheck) {
          const visibleRows = rows.slice(startIdx, endIdx);
          const allVisibleSelected = visibleRows.length > 0 && visibleRows.every(r => state.selectedIds.has(r.dataset.id));
          headerCheck.checked = allVisibleSelected;
        }

        if (window.lucide) lucide.createIcons();
      } finally {
        state.isSyncing = false;
      }
    },

    nextPage(tableId) {
      const state = this.getState(tableId);
      state.currentPage++;
      this.syncTable(tableId);
    },

    prevPage(tableId) {
      const state = this.getState(tableId);
      if (state.currentPage > 1) {
        state.currentPage--;
      }
      this.syncTable(tableId);
    },

    gotoPage(tableId, pageNumber) {
      const state = this.getState(tableId);
      state.currentPage = pageNumber;
      this.syncTable(tableId);
    },

    changePageSize(tableId, newSize) {
      const state = this.getState(tableId);
      state.pageSize = newSize === 'all' ? 'all' : parseInt(newSize, 10);
      state.currentPage = 1;
      this.syncTable(tableId);
    },

    toggleSelectAll(tableId, isChecked) {
      const table = document.getElementById(tableId);
      if (!table) return;
      const state = this.getState(tableId);
      const rows = Array.from(table.querySelectorAll('tbody tr')).filter(r => !r.querySelector('td[colspan]'));

      // If user checks select all, select all visible rows on current page
      const effectivePageSize = state.pageSize === 'all' ? rows.length : parseInt(state.pageSize, 10);
      const startIdx = (state.currentPage - 1) * effectivePageSize;
      const endIdx = Math.min(startIdx + effectivePageSize, rows.length);
      const currentRows = rows.slice(startIdx, endIdx);

      currentRows.forEach(r => {
        const id = r.dataset.id;
        if (id) {
          if (isChecked) {
            state.selectedIds.add(id);
          } else {
            state.selectedIds.delete(id);
          }
        }
      });

      this.syncTable(tableId);
    },

    handleRowCheck(tableId, rowId, checkbox) {
      const state = this.getState(tableId);
      if (checkbox.checked) {
        state.selectedIds.add(rowId);
      } else {
        state.selectedIds.delete(rowId);
      }
      this.syncTable(tableId);
    },

    clearSelection(tableId) {
      const state = this.getState(tableId);
      state.selectedIds.clear();
      this.syncTable(tableId);
    },

    exportSelected(tableId) {
      const table = document.getElementById(tableId);
      if (!table) return;
      const state = this.getState(tableId);
      const rows = Array.from(table.querySelectorAll('tbody tr')).filter(r => !r.querySelector('td[colspan]'));

      const exportRows = state.selectedIds.size > 0
        ? rows.filter(r => state.selectedIds.has(r.dataset.id))
        : rows;

      if (!exportRows.length) {
        if (typeof showToast === 'function') showToast('No rows available to export', 'warning');
        return;
      }

      // Extract headers (ignoring checkbox and actions)
      const headers = Array.from(table.querySelectorAll('thead th'))
        .filter(th => !th.classList.contains('th-bulk-select') && !th.textContent.toLowerCase().includes('action'))
        .map(th => `"${th.textContent.trim().replace(/"/g, '""')}"`);

      const csvLines = [headers.join(',')];

      exportRows.forEach(tr => {
        const cells = Array.from(tr.cells)
          .filter(td => !td.classList.contains('td-bulk-select') && !td.querySelector('.action-dots-trigger') && !td.querySelector('.row-action-dropdown'))
          .map(td => `"${td.textContent.trim().replace(/\s+/g, ' ').replace(/"/g, '""')}"`);
        csvLines.push(cells.join(','));
      });

      const csvContent = 'data:text/csv;charset=utf-8,\uFEFF' + encodeURIComponent(csvLines.join('\n'));
      const link = document.createElement('a');
      link.setAttribute('href', csvContent);
      link.setAttribute('download', `${tableId}_export_${Date.now()}.csv`);
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);

      if (typeof showToast === 'function') {
        showToast(`Exported ${exportRows.length} records to CSV`, 'success');
      }
    },

    archiveSelected(tableId) {
      return this.bulkArchiveSelected(tableId);
    },

    deleteSelected(tableId) {
      return this.bulkDeleteSelected(tableId);
    },

    async bulkArchiveSelected(tableId) {
      const state = this.getState(tableId);
      const count = state.selectedIds.size;
      if (count === 0) {
        if (typeof showToast === 'function') showToast('No rows selected', 'warning');
        return;
      }

      const name = this.tableNames[tableId] || 'Records';
      const promptConfirm = typeof window.showConfirmActionModal === 'function'
        ? window.showConfirmActionModal
        : (typeof showConfirmActionModal === 'function' ? showConfirmActionModal : null);

      const doArchive = async () => {
        const ids = Array.from(state.selectedIds);
        let successCount = 0;
        const token = getAuthToken();
        const base = getApiBaseUrl();

        for (const id of ids) {
          try {
            if (tableId === 'productsTable') {
              const res = await fetch(`${base}/products/${id}/toggle-archive`, {
                method: 'POST',
                headers: { 'Authorization': `Bearer ${token}` }
              });
              if (res.ok) successCount++;
            } else if (tableId === 'farmersTable') {
              const res = await fetch(`${base}/admin/farmers/${id}/status`, {
                method: 'PATCH',
                headers: {
                  'Authorization': `Bearer ${token}`,
                  'Content-Type': 'application/json'
                },
                body: JSON.stringify({ is_active: false })
              });
              if (res.ok) successCount++;
            } else if (tableId === 'ticketsTable') {
              const res = await fetch(`${base}/support/tickets/${id}/status`, {
                method: 'PUT',
                headers: {
                  'Authorization': `Bearer ${token}`,
                  'Content-Type': 'application/json'
                },
                body: JSON.stringify({ status: 'RESOLVED' })
              });
              if (res.ok) successCount++;
            } else if (tableId === 'employeesTable') {
              const res = await fetch(`${base}/employees/${id}/status`, {
                method: 'PATCH',
                headers: {
                  'Authorization': `Bearer ${token}`,
                  'Content-Type': 'application/json'
                },
                body: JSON.stringify({ status: 'SUSPENDED' })
              });
              if (res.ok) successCount++;
            } else {
              const row = document.querySelector(`#${tableId} tr[data-id="${id}"]`);
              if (row) {
                const badge = row.querySelector('.badge');
                if (badge) {
                  badge.className = 'badge badge-warning';
                  badge.textContent = 'ARCHIVED';
                }
              }
              successCount++;
            }
          } catch (e) {
            console.error('Error archiving record:', id, e);
          }
        }

        state.selectedIds.clear();
        if (typeof showToast === 'function') {
          showToast(`Successfully archived / deactivated ${successCount} ${name}`, 'success');
        }

        // Refresh table data
        if (tableId === 'productsTable' && typeof loadProducts === 'function') loadProducts();
        else if (tableId === 'farmersTable' && typeof loadFarmers === 'function') loadFarmers();
        else if (tableId === 'ticketsTable' && typeof loadSupportTickets === 'function') loadSupportTickets();
        else if (tableId === 'employeesTable' && typeof loadEmployeesList === 'function') loadEmployeesList();
        else this.syncTable(tableId);
      };

      if (promptConfirm) {
        promptConfirm({
          title: `Archive / Deactivate ${count} ${name}`,
          subtitle: 'Batch status operation',
          message: `Are you sure you want to deactivate or archive the ${count} selected records?`,
          confirmText: `Archive ${count} Items`,
          confirmDanger: false,
          onConfirm: doArchive
        });
      } else {
        if (confirm(`Archive ${count} selected ${name}?`)) {
          await doArchive();
        }
      }
    },

    async bulkDeleteSelected(tableId) {
      const state = this.getState(tableId);
      const count = state.selectedIds.size;
      if (count === 0) {
        if (typeof showToast === 'function') showToast('No rows selected', 'warning');
        return;
      }

      const name = this.tableNames[tableId] || 'Records';
      const promptConfirm = typeof window.showConfirmActionModal === 'function'
        ? window.showConfirmActionModal
        : (typeof showConfirmActionModal === 'function' ? showConfirmActionModal : null);

      const doDelete = async () => {
        const ids = Array.from(state.selectedIds);
        let successCount = 0;
        const token = getAuthToken();
        const base = getApiBaseUrl();

        for (const id of ids) {
          try {
            let endpoint = '';
            if (tableId === 'productsTable') {
              endpoint = `${base}/products/${id}`;
            } else if (tableId === 'farmersTable') {
              endpoint = `${base}/admin/farmers/${id}`;
            } else if (tableId === 'employeesTable') {
              endpoint = `${base}/employees/${id}`;
            } else if (tableId === 'customRolesTable') {
              endpoint = `${base}/roles/${id}`;
            } else if (tableId === 'departmentsTable') {
              endpoint = `${base}/departments/${id}`;
            } else if (tableId === 'sensorsTable') {
              endpoint = `${base}/sensors/${id}`;
            } else if (tableId === 'usersTable') {
              endpoint = `${base}/admin/farmers/${id}`;
            }

            if (endpoint) {
              const res = await fetch(endpoint, {
                method: 'DELETE',
                headers: { 'Authorization': `Bearer ${token}` }
              });
              if (res.ok) successCount++;
            } else {
              const row = document.querySelector(`#${tableId} tr[data-id="${id}"]`);
              if (row) row.remove();
              successCount++;
            }
          } catch (e) {
            console.error('Error deleting record:', id, e);
          }
        }

        state.selectedIds.clear();
        if (typeof showToast === 'function') {
          showToast(`Successfully deleted ${successCount} ${name}`, 'success');
        }

        // Refresh table data
        if (tableId === 'productsTable' && typeof loadProducts === 'function') loadProducts();
        else if (tableId === 'farmersTable' && typeof loadFarmers === 'function') loadFarmers();
        else if (tableId === 'employeesTable' && typeof loadEmployeesList === 'function') loadEmployeesList();
        else if (tableId === 'customRolesTable' && typeof loadRolesAndPermissions === 'function') loadRolesAndPermissions();
        else if (tableId === 'departmentsTable' && typeof loadDepartmentsList === 'function') loadDepartmentsList();
        else if (tableId === 'sensorsTable' && typeof loadSensors === 'function') loadSensors();
        else this.syncTable(tableId);
      };

      if (promptConfirm) {
        promptConfirm({
          title: `Delete ${count} ${name}`,
          subtitle: 'Irreversible batch deletion',
          message: `Are you sure you want to permanently delete ${count} selected items? This operation cannot be undone.`,
          confirmText: `Permanently Delete ${count} Records`,
          confirmDanger: true,
          onConfirm: doDelete
        });
      } else {
        if (confirm(`Permanently delete ${count} selected ${name}?`)) {
          await doDelete();
        }
      }
    },

    observeAllTables() {
      const allTables = document.querySelectorAll('.data-table');
      allTables.forEach(table => {
        const tableId = table.id;
        if (!tableId) return;

        const tbody = table.querySelector('tbody');
        if (!tbody) return;

        // Initial sync
        this.syncTable(tableId);

        // Setup observer if not already watching
        if (!this.observers[tableId]) {
          const obs = new MutationObserver(() => {
            this.syncTable(tableId);
          });
          obs.observe(tbody, { childList: true });
          this.observers[tableId] = obs;
        }
      });
    }
  };

  window.SetuTableManager = SetuTableManager;

  // Auto-init on page load and view transitions
  window.addEventListener('DOMContentLoaded', () => {
    SetuTableManager.observeAllTables();
  });

})();
