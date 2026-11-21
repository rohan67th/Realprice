/* visits.js — Real Scheduled Visits page renderer & action controller */

let currentVisitFilter = 'all';
let visitSearchQuery = '';
let visitSortBy = 'date-desc';

function getCsrfToken() {
  const cookieValue = document.cookie
    .split('; ')
    .find(row => row.startsWith('csrftoken='))
    ?.split('=')[1];
  return cookieValue || '';
}

function updateVisitCounts() {
  const visits = window.REAL_VISITS || [];
  const allCount = visits.length;
  const pendingCount = visits.filter(v => v.status === 'pending').length;
  const approvedCount = visits.filter(v => v.status === 'approved').length;
  const declinedCount = visits.filter(v => v.status === 'declined').length;

  const bAll = document.getElementById('badge-count-all');
  const bPending = document.getElementById('badge-count-pending');
  const bApproved = document.getElementById('badge-count-approved');
  const bDeclined = document.getElementById('badge-count-declined');

  if (bAll) bAll.textContent = allCount;
  if (bPending) bPending.textContent = pendingCount;
  if (bApproved) bApproved.textContent = approvedCount;
  if (bDeclined) bDeclined.textContent = declinedCount;
}

function setVisitFilter(filter, btn) {
  currentVisitFilter = filter;
  const tabs = document.querySelectorAll('#visit-filter-tabs .tab-pill');
  tabs.forEach(t => t.classList.remove('active'));
  if (btn) btn.classList.add('active');
  renderVisits();
}

function onVisitSearch(val) {
  visitSearchQuery = (val || '').toLowerCase().trim();
  renderVisits();
}

function onVisitSort(val) {
  visitSortBy = val || 'date-desc';
  renderVisits();
}

function renderVisits() {
  const grid = document.getElementById('visits-grid');
  if (!grid) return;

  const visits = window.REAL_VISITS || [];

  // Filter
  let filtered = visits.filter(v => {
    if (currentVisitFilter !== 'all' && v.status !== currentVisitFilter) {
      return false;
    }
    if (visitSearchQuery) {
      const q = visitSearchQuery;
      const matchBuyer = (v.buyer_name || '').toLowerCase().includes(q);
      const matchEmail = (v.buyer_email || '').toLowerCase().includes(q);
      const matchPhone = (v.buyer_phone || '').toLowerCase().includes(q);
      const matchProp = (v.property_title || '').toLowerCase().includes(q);
      const matchAddr = (v.property_address || '').toLowerCase().includes(q);
      if (!matchBuyer && !matchEmail && !matchPhone && !matchProp && !matchAddr) {
        return false;
      }
    }
    return true;
  });

  // Sort
  filtered.sort((a, b) => {
    if (visitSortBy === 'date-asc') {
      return (a.scheduled_date + a.scheduled_time).localeCompare(b.scheduled_date + b.scheduled_time);
    } else if (visitSortBy === 'name') {
      return (a.buyer_name || '').localeCompare(b.buyer_name || '');
    } else {
      // date-desc
      return (b.scheduled_date + b.scheduled_time).localeCompare(a.scheduled_date + a.scheduled_time);
    }
  });

  // Empty State
  if (filtered.length === 0) {
    let emptyMsg = "No scheduled visits match your current filter.";
    let emptySub = "When buyers request a visit or when you schedule a tour, they'll appear here.";
    if (visits.length === 0) {
      emptyMsg = "No Scheduled Visits Yet";
      emptySub = "You don't have any tour requests yet. You can also proactively schedule a visit with any buyer.";
    }

    grid.innerHTML = `
      <div class="col-span-full card p-12 text-center flex flex-col items-center justify-center animate-fade-in">
        <div class="h-16 w-16 rounded-2xl bg-brand-50 dark:bg-brand-900/30 text-brand-600 dark:text-brand-400 grid place-items-center text-3xl mb-4 shadow-sm">
          <i class="ri-calendar-2-line"></i>
        </div>
        <h3 class="text-lg font-bold text-ink-900 dark:text-white">${emptyMsg}</h3>
        <p class="text-sm text-ink-500 dark:text-ink-400 mt-1 max-w-md">${emptySub}</p>
        <button onclick="openModal('modal-visit')" class="btn-primary mt-6">
          <i class="ri-calendar-check-line"></i> Schedule a Visit
        </button>
      </div>
    `;
    return;
  }

  // Render cards
  grid.innerHTML = filtered.map(v => {
    // Status Badge
    let badgeHtml = '';
    if (v.status === 'approved') {
      badgeHtml = `<span class="badge-success"><i class="ri-checkbox-circle-line"></i> Approved</span>`;
    } else if (v.status === 'declined') {
      badgeHtml = `<span class="badge-danger"><i class="ri-close-circle-line"></i> Declined</span>`;
    } else {
      badgeHtml = `<span class="badge-warning"><i class="ri-time-line"></i> Pending</span>`;
    }

    // Avatar
    const avatarHtml = v.buyer_photo
      ? `<img src="${v.buyer_photo}" class="h-12 w-12 rounded-full object-cover ring-2 ring-white dark:ring-ink-800 shadow-sm" alt="${v.buyer_name}"/>`
      : `<div class="h-12 w-12 rounded-full bg-gradient-to-tr from-brand-600 to-brand-400 text-white font-extrabold text-sm grid place-items-center ring-2 ring-white dark:ring-ink-800 shadow-sm">${v.buyer_initials || 'B'}</div>`;

    // Notes
    let messageHtml = '';
    if (v.message) {
      messageHtml = `
        <div class="mt-3 p-3 rounded-xl bg-ink-50 dark:bg-ink-800/50 border border-ink-100 dark:border-ink-700/50 text-xs text-ink-600 dark:text-ink-300">
          <div class="flex items-center gap-1.5 font-semibold text-ink-800 dark:text-ink-100 mb-1">
            <i class="ri-chat-quote-line text-brand-500"></i> Buyer's Note:
          </div>
          <p class="italic line-clamp-3">"${v.message}"</p>
        </div>
      `;
    }

    // Actions
    let actionButtons = '';
    if (v.status === 'pending') {
      actionButtons = `
        <div class="grid grid-cols-2 gap-2 mt-4 pt-3 border-t border-ink-100 dark:border-ink-800">
          <button onclick="approveVisit(${v.id})" class="btn-primary text-xs py-2 bg-emerald-600 hover:bg-emerald-700 border-none shadow-sm" id="btn-approve-${v.id}">
            <i class="ri-check-line text-sm"></i> Approve
          </button>
          <button onclick="declineVisit(${v.id})" class="btn-outline text-xs py-2 text-rose-600 dark:text-rose-400 hover:bg-rose-50 dark:hover:bg-rose-900/20 border-rose-200 dark:border-rose-900/40" id="btn-decline-${v.id}">
            <i class="ri-close-line text-sm"></i> Decline
          </button>
        </div>
      `;
    } else if (v.status === 'approved') {
      actionButtons = `
        <div class="flex items-center gap-2 mt-4 pt-3 border-t border-ink-100 dark:border-ink-800">
          <a href="${v.chat_url || '#'}" class="btn-primary flex-1 text-xs py-2" ${!v.chat_url ? 'disabled' : ''}>
            <i class="ri-chat-3-line text-sm"></i> Chat with Buyer
          </a>
          <button onclick="declineVisit(${v.id})" title="Cancel / Decline visit" class="h-9 w-9 rounded-lg border border-ink-200 dark:border-ink-700 hover:bg-rose-50 dark:hover:bg-rose-900/20 text-ink-400 hover:text-rose-600 grid place-items-center transition">
            <i class="ri-close-line text-base"></i>
          </button>
        </div>
      `;
    } else {
      actionButtons = `
        <div class="mt-4 pt-3 border-t border-ink-100 dark:border-ink-800 flex items-center justify-between">
          <span class="text-xs text-rose-500 font-medium">Tour request declined</span>
          <button onclick="approveVisit(${v.id})" class="btn-outline text-xs py-1.5 px-3">
            <i class="ri-restart-line"></i> Re-approve
          </button>
        </div>
      `;
    }

    // Property image / thumb
    const propThumb = v.property_img
      ? `<img src="${v.property_img}" class="h-10 w-10 rounded-lg object-cover shrink-0" alt="Property"/>`
      : `<div class="h-10 w-10 rounded-lg bg-brand-50 dark:bg-brand-900/30 text-brand-600 dark:text-brand-400 grid place-items-center shrink-0"><i class="ri-home-4-line text-lg"></i></div>`;

    return `
      <div class="card card-hover p-5 flex flex-col justify-between animate-fade-in-up" id="visit-card-${v.id}">
        <div>
          <!-- Header: Buyer Info + Status -->
          <div class="flex items-start justify-between gap-3">
            <div class="flex items-center gap-3 min-w-0">
              ${avatarHtml}
              <div class="min-w-0">
                <p class="font-bold text-ink-900 dark:text-white truncate text-sm sm:text-base">${v.buyer_name}</p>
                <div class="flex items-center gap-2 mt-0.5 text-xs text-ink-400 truncate">
                  ${v.buyer_email ? `<a href="mailto:${v.buyer_email}" class="hover:text-brand-600 flex items-center gap-1"><i class="ri-mail-line"></i> ${v.buyer_email}</a>` : ''}
                  ${v.buyer_phone ? `<span class="hidden sm:inline">·</span><a href="tel:${v.buyer_phone}" class="hover:text-brand-600 flex items-center gap-1"><i class="ri-phone-line"></i> ${v.buyer_phone}</a>` : ''}
                </div>
              </div>
            </div>
            <div class="shrink-0" id="visit-badge-${v.id}">
              ${badgeHtml}
            </div>
          </div>

          <!-- Schedule Time & Date Banner -->
          <div class="mt-4 p-2.5 rounded-xl bg-brand-50/70 dark:bg-brand-900/20 border border-brand-100 dark:border-brand-800/40 flex items-center justify-between text-xs font-semibold text-brand-900 dark:text-brand-200">
            <div class="flex items-center gap-1.5">
              <i class="ri-calendar-line text-brand-600 dark:text-brand-400 text-sm"></i>
              <span>${v.date_display}</span>
            </div>
            <div class="flex items-center gap-1.5">
              <i class="ri-time-line text-brand-600 dark:text-brand-400 text-sm"></i>
              <span>${v.time_display}</span>
            </div>
          </div>

          <!-- Property block -->
          <div class="mt-3 p-3 rounded-xl bg-ink-50 dark:bg-ink-800/40 flex items-center gap-3">
            ${propThumb}
            <div class="min-w-0 flex-1">
              <p class="text-[11px] uppercase tracking-wider text-ink-400 font-semibold">Property</p>
              <p class="text-xs sm:text-sm font-bold text-ink-900 dark:text-white truncate">${v.property_title}</p>
              ${v.property_price ? `<p class="text-xs font-semibold text-brand-600 dark:text-brand-400">₹${v.property_price}</p>` : ''}
            </div>
          </div>

          <!-- Notes -->
          ${messageHtml}
        </div>

        <!-- Footer Actions -->
        <div id="visit-actions-${v.id}">
          ${actionButtons}
        </div>
      </div>
    `;
  }).join('');
}

async function approveVisit(visitId) {
  const visit = (window.REAL_VISITS || []).find(v => v.id === visitId);
  if (!visit) return;

  const btnApprove = document.getElementById(`btn-approve-${visitId}`);
  if (btnApprove) {
    btnApprove.disabled = true;
    btnApprove.innerHTML = `<i class="ri-loader-4-line animate-spin"></i> Approving…`;
  }

  try {
    const res = await fetch(visit.approve_url, {
      method: 'POST',
      headers: {
        'X-CSRFToken': getCsrfToken(),
        'X-Requested-With': 'XMLHttpRequest',
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      body: 'ajax=true',
    });

    if (res.ok) {
      const data = await res.json();
      visit.status = 'approved';
      if (data.chat_url) visit.chat_url = data.chat_url;
      updateVisitCounts();
      renderVisits();
    } else {
      // Fallback: standard POST navigation
      const form = document.createElement('form');
      form.method = 'POST';
      form.action = visit.approve_url;
      const csrfInput = document.createElement('input');
      csrfInput.type = 'hidden';
      csrfInput.name = 'csrfmiddlewaretoken';
      csrfInput.value = getCsrfToken();
      form.appendChild(csrfInput);
      document.body.appendChild(form);
      form.submit();
    }
  } catch (err) {
    console.error('Error approving visit:', err);
    window.location.reload();
  }
}

async function declineVisit(visitId) {
  const visit = (window.REAL_VISITS || []).find(v => v.id === visitId);
  if (!visit) return;

  if (!confirm(`Are you sure you want to decline this visit with ${visit.buyer_name}?`)) {
    return;
  }

  const btnDecline = document.getElementById(`btn-decline-${visitId}`);
  if (btnDecline) {
    btnDecline.disabled = true;
    btnDecline.innerHTML = `<i class="ri-loader-4-line animate-spin"></i> Declining…`;
  }

  try {
    const res = await fetch(visit.decline_url, {
      method: 'POST',
      headers: {
        'X-CSRFToken': getCsrfToken(),
        'X-Requested-With': 'XMLHttpRequest',
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      body: 'ajax=true',
    });

    if (res.ok) {
      visit.status = 'declined';
      updateVisitCounts();
      renderVisits();
    } else {
      // Fallback: standard POST navigation
      const form = document.createElement('form');
      form.method = 'POST';
      form.action = visit.decline_url;
      const csrfInput = document.createElement('input');
      csrfInput.type = 'hidden';
      csrfInput.name = 'csrfmiddlewaretoken';
      csrfInput.value = getCsrfToken();
      form.appendChild(csrfInput);
      document.body.appendChild(form);
      form.submit();
    }
  } catch (err) {
    console.error('Error declining visit:', err);
    window.location.reload();
  }
}

document.addEventListener('DOMContentLoaded', function() {
  updateVisitCounts();
  renderVisits();
});
