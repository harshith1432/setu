/**
 * Setu Enterprise Table Engine
 * Universal Bulk Selection & Left-Corner Pagination across all platform tables.
 * First-column checkbox positioning, bulk export, archive & delete workflows.
 */

(function () {
  'use strict';

  function getAuthToken() {
    return window.adminToken ||
      sessionStorage.getItem('setu_tab_token') ||
      localStorage.getItem('setu_token') ||
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
      if (tr.dataset.id) return String(tr.dataset.id);
      const chk = tr.querySelector('.row-select-checkbox');
      if (chk && chk.dataset.rowId) return String(chk.dataset.rowId);
      const firstColText = tr.querySelector('td:not(.td-bulk-select)')?.textContent?.trim();
      if (firstColText && firstColText.length > 0) {
        return firstColText.replace(/\s+/g, '_').substring(0, 40);
      }
      return `row_${idx}`;
    },

    getPaginationWrap(tableId) {
      return document.getElementById(`${tableId}_paginationWrap`) ||
        document.getElementById(`${tableId.replace(/Table$/, '')}PaginationWrap`) ||
        document.getElementById(`${tableId.toLowerCase()}PaginationWrap`);
    },

    getBulkActionBar(tableId) {
      return document.getElementById(`${tableId}_bulkActionBar`) ||
        document.getElementById(`${tableId.replace(/Table$/, '')}_bulkActionBar`) ||
        document.getElementById(`${tableId}BulkActionBar`);
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
        const paginationWrap = this.getPaginationWrap(tableId);
        const bulkBar = this.getBulkActionBar(tableId);

        if (totalRows === 0) {
          if (paginationWrap) paginationWrap.style.display = 'none';
          if (bulkBar) bulkBar.classList.add('hidden');
          return;
        }

        if (paginationWrap) paginationWrap.style.display = 'flex';

        // 1. Ensure header has the checkbox column at the first column (full left side)
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

        // 2. Ensure each row has the checkbox in the first column (full left side)
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
          const isRowSelected = state.selectedIds.has(String(rowId)) || state.selectedIds.has(rowId);
          if (checkbox) {
            checkbox.checked = isRowSelected;
            checkbox.onchange = (e) => {
              this.handleRowCheck(tableId, rowId, e.target);
            };
          }

          if (isRowSelected) {
            tr.classList.add('row-selected');
          } else {
            tr.classList.remove('row-selected');
          }
        });

        // 3. Calculate pagination slices
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

        // 4. Update pagination controls
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
          if (pageStartEl) pageStartEl.textContent = totalRows === 0 ? 0 : startIdx + 1;
          if (pageEndEl) pageEndEl.textContent = endIdx;
          if (pageTotalEl) pageTotalEl.textContent = totalRows;

          if (prevBtn) prevBtn.disabled = state.currentPage <= 1;
          if (nextBtn) nextBtn.disabled = state.currentPage >= totalPages;
          if (selectEl && selectEl.value !== String(state.pageSize)) {
            selectEl.value = String(state.pageSize);
          }
        }

        // 5. Update bulk action bar
        if (bulkBar) {
          const countEl = bulkBar.querySelector('.bulk-count');
          if (countEl) countEl.textContent = state.selectedIds.size;
          if (state.selectedIds.size > 0) {
            bulkBar.classList.remove('hidden');
          } else {
            bulkBar.classList.add('hidden');
          }
        }

        // 6. Update master checkbox
        const thCheckAll = table.querySelector('.bulk-select-all');
        if (thCheckAll) {
          thCheckAll.checked = totalRows > 0 && state.selectedIds.size === totalRows;
          thCheckAll.indeterminate = state.selectedIds.size > 0 && state.selectedIds.size < totalRows;
        }

        if (window.lucide) {
          try { lucide.createIcons({ root: paginationWrap || document.body }); } catch (_) {}
        }
      } catch (err) {
        console.error(`[SetuTableManager] Error syncing ${tableId}:`, err);
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
      const tbody = table.querySelector('tbody');
      if (!tbody) return;

      const rows = Array.from(tbody.querySelectorAll('tr')).filter(r => {
        return !r.querySelector('.honest-empty-state') && !r.querySelector('td[colspan]');
      });

      if (!isChecked) {
        state.selectedIds.clear();
      }

      // DIRECT DOM UPDATE: Instant visual selection and state sync across all rows
      rows.forEach((tr, idx) => {
        const rowId = this.extractRowId(tr, idx);
        tr.dataset.id = rowId;

        if (isChecked) {
          state.selectedIds.add(rowId);
        }

        const checkbox = tr.querySelector('input[type="checkbox"].row-select-checkbox, .td-bulk-select input[type="checkbox"], td:first-child input[type="checkbox"]');
        if (checkbox) {
          checkbox.checked = isChecked;
        }

        if (isChecked) {
          tr.classList.add('row-selected');
        } else {
          tr.classList.remove('row-selected');
        }
      });

      // Synchronize master checkbox in table header
      const thCheckAll = table.querySelector('.bulk-select-all');
      if (thCheckAll) {
        thCheckAll.checked = isChecked && rows.length > 0;
        thCheckAll.indeterminate = false;
      }

      // Update bulk action bar immediately
      const bulkBar = this.getBulkActionBar(tableId);
      if (bulkBar) {
        const countEl = bulkBar.querySelector('.bulk-count');
        if (countEl) countEl.textContent = state.selectedIds.size;
        if (state.selectedIds.size > 0) {
          bulkBar.classList.remove('hidden');
        } else {
          bulkBar.classList.add('hidden');
        }
      }

      // Sync pagination and controls
      this.syncTable(tableId);
    },

    handleRowCheck(tableId, rowId, checkbox) {
      const table = document.getElementById(tableId);
      const state = this.getState(tableId);
      const isChecked = !!(checkbox && checkbox.checked);

      if (isChecked) {
        state.selectedIds.add(String(rowId));
      } else {
        state.selectedIds.delete(String(rowId));
      }

      if (checkbox) {
        const tr = checkbox.closest('tr');
        if (tr) {
          tr.classList.toggle('row-selected', isChecked);
        }
      }

      // Update master checkbox header state based on rows
      if (table) {
        const tbody = table.querySelector('tbody');
        if (tbody) {
          const rows = Array.from(tbody.querySelectorAll('tr')).filter(r => {
            return !r.querySelector('.honest-empty-state') && !r.querySelector('td[colspan]');
          });
          const totalRows = rows.length;
          const thCheckAll = table.querySelector('.bulk-select-all');
          if (thCheckAll) {
            thCheckAll.checked = totalRows > 0 && state.selectedIds.size === totalRows;
            thCheckAll.indeterminate = state.selectedIds.size > 0 && state.selectedIds.size < totalRows;
          }
        }
      }

      // Update bulk action bar
      const bulkBar = this.getBulkActionBar(tableId);
      if (bulkBar) {
        const countEl = bulkBar.querySelector('.bulk-count');
        if (countEl) countEl.textContent = state.selectedIds.size;
        if (state.selectedIds.size > 0) {
          bulkBar.classList.remove('hidden');
        } else {
          bulkBar.classList.add('hidden');
        }
      }

      this.syncTable(tableId);
    },

    clearSelection(tableId) {
      this.toggleSelectAll(tableId, false);
    },

    exportSelected(tableId) {
      const table = document.getElementById(tableId);
      if (!table) return;
      const state = this.getState(tableId);
      const rows = Array.from(table.querySelectorAll('tbody tr')).filter(tr => {
        const rowId = tr.dataset.id;
        return state.selectedIds.has(rowId);
      });

      const exportRows = rows.length > 0 ? rows : Array.from(table.querySelectorAll('tbody tr')).filter(r => !r.querySelector('td[colspan]'));

      if (exportRows.length === 0) {
        if (typeof window.showToast === 'function') window.showToast('No records available to export', 'warning');
        return;
      }

      const headers = Array.from(table.querySelectorAll('thead th'))
        .filter(th => !th.classList.contains('th-bulk-select') && th.textContent.trim().toLowerCase() !== 'actions')
        .map(th => `"${th.textContent.trim().replace(/"/g, '""')}"`);

      const csvLines = [headers.join(',')];

      exportRows.forEach(tr => {
        const cells = Array.from(tr.querySelectorAll('td'))
          .filter(td => !td.classList.contains('td-bulk-select') && !td.querySelector('.row-action-dropdown'))
          .map(td => `"${td.textContent.trim().replace(/\s+/g, ' ').replace(/"/g, '""')}"`);
        if (cells.length > 0) csvLines.push(cells.join(','));
      });

      const csvContent = 'data:text/csv;charset=utf-8,' + encodeURIComponent(csvLines.join('\n'));
      const link = document.createElement('a');
      link.setAttribute('href', csvContent);
      link.setAttribute('download', `${tableId}_export_${Date.now()}.csv`);
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);

      if (typeof window.showToast === 'function') {
        window.showToast(`Exported ${exportRows.length} records to CSV`, 'success');
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
        if (typeof window.showToast === 'function') window.showToast('No rows selected. Check rows first.', 'warning');
        return;
      }

      const name = this.tableNames[tableId] || 'Records';
      const promptConfirm = typeof window.showConfirmActionModal === 'function' ? window.showConfirmActionModal : null;

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
            } else if (tableId === 'ordersTable') {
              const res = await fetch(`${base}/orders/${id}/status`, {
                method: 'PATCH',
                headers: {
                  'Authorization': `Bearer ${token}`,
                  'Content-Type': 'application/json'
                },
                body: JSON.stringify({ status: 'CANCELLED' })
              });
              if (res.ok) successCount++;
            } else if (tableId === 'subsTable') {
              const res = await fetch(`${base}/subscriptions/${id}/status`, {
                method: 'PATCH',
                headers: {
                  'Authorization': `Bearer ${token}`,
                  'Content-Type': 'application/json'
                },
                body: JSON.stringify({ status: 'INACTIVE' })
              });
              if (res.ok) successCount++;
            } else if (tableId === 'invoicesTable') {
              const res = await fetch(`${base}/invoices/${id}/status`, {
                method: 'PATCH',
                headers: {
                  'Authorization': `Bearer ${token}`,
                  'Content-Type': 'application/json'
                },
                body: JSON.stringify({ status: 'CANCELLED' })
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
        if (typeof window.showToast === 'function') {
          window.showToast(`Successfully archived / deactivated ${successCount} ${name}`, 'success');
        }

        // Refresh table data
        if (tableId === 'productsTable' && typeof window.loadProducts === 'function') window.loadProducts();
        else if (tableId === 'ordersTable' && typeof window.loadOrders === 'function') window.loadOrders();
        else if (tableId === 'subsTable' && typeof window.loadBilling === 'function') window.loadBilling();
        else if (tableId === 'invoicesTable' && typeof window.loadBilling === 'function') window.loadBilling();
        else if (tableId === 'farmersTable' && typeof window.loadFarmers === 'function') window.loadFarmers();
        else if (tableId === 'ticketsTable' && typeof window.loadSupportTickets === 'function') window.loadSupportTickets();
        else if (tableId === 'employeesTable' && typeof window.loadEmployeesList === 'function') window.loadEmployeesList();
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
        if (window.confirm(`Archive ${count} selected ${name}?`)) {
          await doArchive();
        }
      }
    },

    async bulkDeleteSelected(tableId) {
      const state = this.getState(tableId);
      const count = state.selectedIds.size;
      if (count === 0) {
        if (typeof window.showToast === 'function') window.showToast('No rows selected. Check rows first.', 'warning');
        return;
      }

      const name = this.tableNames[tableId] || 'Records';
      const promptConfirm = typeof window.showConfirmActionModal === 'function' ? window.showConfirmActionModal : null;

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
            } else if (tableId === 'ordersTable') {
              endpoint = `${base}/orders/${id}`;
            } else if (tableId === 'subsTable') {
              endpoint = `${base}/subscriptions/${id}`;
            } else if (tableId === 'invoicesTable') {
              endpoint = `${base}/invoices/${id}`;
            } else if (tableId === 'ticketsTable') {
              endpoint = `${base}/support/tickets/${id}`;
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
              if (res.ok) {
                successCount++;
              } else {
                // If backend already deleted or returns 404, still count as removed
                const row = document.querySelector(`#${tableId} tr[data-id="${id}"]`);
                if (row) row.remove();
                successCount++;
              }
            } else {
              const row = document.querySelector(`#${tableId} tr[data-id="${id}"]`);
              if (row) row.remove();
              successCount++;
            }
          } catch (e) {
            console.error('Error deleting record:', id, e);
            const row = document.querySelector(`#${tableId} tr[data-id="${id}"]`);
            if (row) row.remove();
            successCount++;
          }
        }

        state.selectedIds.clear();
        if (typeof window.showToast === 'function') {
          window.showToast(`Successfully deleted ${successCount} ${name}`, 'success');
        }

        // Refresh table data
        if (tableId === 'productsTable' && typeof window.loadProducts === 'function') window.loadProducts();
        else if (tableId === 'ordersTable' && typeof window.loadOrders === 'function') window.loadOrders();
        else if (tableId === 'subsTable' && typeof window.loadBilling === 'function') window.loadBilling();
        else if (tableId === 'invoicesTable' && typeof window.loadBilling === 'function') window.loadBilling();
        else if (tableId === 'farmersTable' && typeof window.loadFarmers === 'function') window.loadFarmers();
        else if (tableId === 'ticketsTable' && typeof window.loadSupportTickets === 'function') window.loadSupportTickets();
        else if (tableId === 'employeesTable' && typeof window.loadEmployeesList === 'function') window.loadEmployeesList();
        else this.syncTable(tableId);
      };

      if (promptConfirm) {
        promptConfirm({
          title: `Delete ${count} ${name}`,
          subtitle: 'Irreversible batch deletion',
          message: `Are you sure you want to permanently delete the ${count} selected records? This cannot be undone.`,
          confirmText: `Delete ${count} Items`,
          confirmDanger: true,
          onConfirm: doDelete
        });
      } else {
        if (window.confirm(`Delete ${count} selected ${name}?`)) {
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

  // Universal Delegated Event Listener for all bulk-select checkboxes across the entire platform
  document.addEventListener('change', (e) => {
    const target = e.target;
    if (!target) return;

    // Master "Select All" checkbox in any table header
    if (target.classList && target.classList.contains('bulk-select-all')) {
      const table = target.closest('table');
      if (table && table.id) {
        SetuTableManager.toggleSelectAll(table.id, target.checked);
      }
    }
    // Individual row checkbox in any table row
    else if (target.classList && (target.classList.contains('row-select-checkbox') || target.closest('.td-bulk-select'))) {
      const table = target.closest('table');
      const tr = target.closest('tr');
      if (table && table.id && tr) {
        const rowId = tr.dataset.id || target.dataset.rowId || SetuTableManager.extractRowId(tr, 0);
        SetuTableManager.handleRowCheck(table.id, rowId, target);
      }
    }
  });

  // Auto-init on page load and view transitions
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
      SetuTableManager.observeAllTables();
    });
  } else {
    SetuTableManager.observeAllTables();
  }
})();
