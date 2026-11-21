/* properties.js — Property gallery + table renderers
   Uses REAL_PROPERTIES injected from Django context when available,
   falls back to PROPERTIES from common.js for backward compatibility. */

/* ---------- APPROVAL BADGE HELPER ---------- */
function approvalBadge(status) {
  const map = {
    'pending':            { label: 'Pending Review',     cls: 'badge-warning' },
    'approved':           { label: 'Approved',           cls: 'badge-success' },
    'rejected':           { label: 'Rejected',           cls: 'badge-danger' },
    'changes_requested':  { label: 'Changes Requested',  cls: 'badge-orange' },
  };
  const b = map[status] || { label: status || 'Unknown', cls: 'badge-neutral' };
  return `<span class="${b.cls}">${b.label}</span>`;
}

/* ---------- PROPERTY CARD ---------- */
function propCard(p){
  // Support both real data (from Django) and dummy data
  const title = p.property_type ? `${p.property_type} at ${p.location}` : (p.title || 'Property');
  const img = p.main_image || p.img || '';
  const price = typeof p.price === 'string' ? parseFloat(p.price) : (p.price || 0);
  const beds = p.bedrooms || p.beds || 0;
  const baths = p.bathrooms || p.baths || 0;
  const area = p.area_sqft || p.area || 0;
  const approval = p.approval_status || 'pending';
  const feedback = p.seller_feedback || '';
  const editUrl = p.edit_url || `/seller_properties/edit/${p.id}/`;
  const deleteUrl = p.delete_url || '';
  const posted = p.posted_at || p.updated || 'N/A';

  let feedbackHtml = '';
  if ((approval === 'changes_requested' || approval === 'rejected') && feedback) {
    feedbackHtml = `
      <div class="feedback-card ${approval}">
        <p class="font-bold text-[11px] uppercase tracking-wider mb-1">Admin Feedback</p>
        <p>${feedback}</p>
      </div>`;
  }

  let actionHtml = '';
  if (approval === 'changes_requested') {
    actionHtml = `<a href="${editUrl}" class="btn-primary text-xs px-3 py-1.5" style="background:#d97706;"><i class="ri-edit-line mr-1"></i>Edit Property</a>`;
  } else if (approval === 'approved') {
    actionHtml = `<div class="flex gap-1">
      <button class="act-btn" title="View"><i class="ri-eye-line"></i></button>
      <a href="${editUrl}" class="act-btn" title="Edit"><i class="ri-edit-line"></i></a>
    </div>`;
  } else {
    actionHtml = `<div class="flex gap-1">
      <button class="act-btn" title="View"><i class="ri-eye-line"></i></button>
      <a href="${editUrl}" class="act-btn" title="Edit"><i class="ri-edit-line"></i></a>
    </div>`;
  }

  return `<div class="card card-hover overflow-hidden gallery-card animate-fade-in-up">
    <div class="relative h-48 overflow-hidden">
      ${img ? `<img src="${img}" class="gallery-img h-full w-full object-cover" alt="${title}"/>` : `<div class="h-full w-full bg-ink-100 dark:bg-ink-800 grid place-items-center"><i class="ri-home-line text-4xl text-ink-300"></i></div>`}
      <div class="absolute inset-0 bg-gradient-to-t from-ink-950/50 to-transparent"></div>
      <div class="absolute top-3 left-3">${approvalBadge(approval)}</div>
      <div class="absolute bottom-3 left-3">
        <span class="px-2 py-1 rounded-lg bg-white/80 dark:bg-ink-900/70 backdrop-blur text-[11px] font-semibold text-ink-700 dark:text-ink-200">${p.property_type || p.type || ''}</span>
      </div>
    </div>
    <div class="p-5">
      <h3 class="font-bold text-ink-900 dark:text-white leading-snug">${title}</h3>
      <p class="text-sm text-ink-400 mt-1 flex items-center gap-1"><i class="ri-map-pin-line"></i>${p.location || ''}</p>
      <p class="text-2xl font-extrabold text-brand-600 dark:text-brand-400 mt-3">₹${price.toLocaleString('en-IN')}</p>
      <div class="flex items-center gap-4 mt-3 text-sm text-ink-500 dark:text-ink-400">
        ${beds ? `<span class="flex items-center gap-1"><i class="ri-bed-line"></i>${beds}</span>` : ''}
        ${baths ? `<span class="flex items-center gap-1"><i class="ri-bath-line"></i>${baths}</span>` : ''}
        ${area ? `<span class="flex items-center gap-1"><i class="ri-ruler-2-line"></i>${area.toLocaleString()} sqft</span>` : ''}
      </div>
      ${feedbackHtml}
      <div class="flex items-center justify-between mt-4 pt-4 border-t border-ink-100 dark:border-ink-800">
        <span class="text-xs text-ink-400">${posted}</span>
        ${actionHtml}
      </div>
    </div>
  </div>`;
}

/* ---------- PROPERTIES: gallery + table ---------- */
let propView='gallery', propFilter='all', propSortKey='property_type', propSortAsc=true, propPage=1, propSearch='';

function getPropertiesData() {
  // Use real data from Django if available, otherwise fall back to common.js dummy data
  return (typeof REAL_PROPERTIES !== 'undefined' && REAL_PROPERTIES.length > 0) ? REAL_PROPERTIES : (typeof PROPERTIES !== 'undefined' ? PROPERTIES : []);
}

function setPropView(v){
  propView=v;
  const gallery = document.querySelector('#props-gallery');
  const table = document.querySelector('#props-table');
  if (gallery) gallery.classList.toggle('hidden', v!=='gallery');
  if (table) table.classList.toggle('hidden', v!=='table');
  const gBtn = document.querySelector('#view-gallery-btn');
  const tBtn = document.querySelector('#view-table-btn');
  if (gBtn) gBtn.className='px-3 py-1.5 rounded-lg text-sm font-semibold transition '+(v==='gallery'?'bg-brand-50 text-brand-600 dark:bg-brand-900/30 dark:text-brand-400':'text-ink-400 hover:text-ink-600');
  if (tBtn) tBtn.className='px-3 py-1.5 rounded-lg text-sm font-semibold transition '+(v==='table'?'bg-brand-50 text-brand-600 dark:bg-brand-900/30 dark:text-brand-400':'text-ink-400 hover:text-ink-600');
}

function filteredProps(){
  const data = getPropertiesData();
  return data.filter(p => {
    const approval = p.approval_status || '';
    const matchFilter = propFilter === 'all' || approval === propFilter;
    const searchStr = ((p.property_type || p.title || '') + ' ' + (p.location || '') + ' ' + (p.address || '')).toLowerCase();
    const matchSearch = propSearch === '' || searchStr.includes(propSearch.toLowerCase());
    return matchFilter && matchSearch;
  });
}

function renderPropsGallery(){
  const list = filteredProps().slice(0, 6);
  const gallery = document.querySelector('#props-gallery');
  if (!gallery) return;
  if (list.length === 0) {
    gallery.innerHTML = `<div class="col-span-full py-12 text-center">
      <div class="flex flex-col items-center gap-3">
        <i class="ri-home-line text-4xl text-ink-300"></i>
        <p class="text-sm font-bold text-ink-900 dark:text-white">No properties found</p>
        <p class="text-xs text-ink-400">Try adjusting your filters or add a new property.</p>
      </div>
    </div>`;
  } else {
    gallery.innerHTML = list.map(propCard).join('');
  }
}

function sortProps(key){ if(propSortKey===key)propSortAsc=!propSortAsc; else{propSortKey=key;propSortAsc=true;} renderPropsTable(); }

function renderPropsTable(){
  const searchEl = document.querySelector('#props-search');
  propSearch = searchEl ? searchEl.value : '';
  const filterEl = document.querySelector('#props-filter');
  if (filterEl) propFilter = filterEl.value;

  let list = filteredProps();
  list.sort((a,b)=>{
    let av = a[propSortKey] || '', bv = b[propSortKey] || '';
    if(typeof av === 'string') return propSortAsc ? av.localeCompare(bv) : bv.localeCompare(av);
    return propSortAsc ? av-bv : bv-av;
  });

  const perPage = 5;
  const pages = Math.max(1, Math.ceil(list.length / perPage));
  if (propPage > pages) propPage = pages;
  const slice = list.slice((propPage-1)*perPage, propPage*perPage);

  const tbody = document.querySelector('#props-tbody');
  if (!tbody) return;

  if (slice.length === 0) {
    tbody.innerHTML = `<tr><td colspan="6" class="py-10 text-center text-ink-400 text-sm">No properties found</td></tr>`;
  } else {
    tbody.innerHTML = slice.map(p => {
      const title = p.property_type ? `${p.property_type} at ${p.location}` : (p.title || 'Property');
      const img = p.main_image || p.img || '';
      const price = typeof p.price === 'string' ? parseFloat(p.price) : (p.price || 0);
      const approval = p.approval_status || 'pending';
      const feedback = p.seller_feedback || '';
      const editUrl = p.edit_url || `/seller_properties/edit/${p.id}/`;
      const posted = p.posted_at || p.updated || 'N/A';

      let feedbackHtml = '';
      if ((approval === 'changes_requested' || approval === 'rejected') && feedback) {
        feedbackHtml = `<div class="mt-1 text-[10px] text-ink-500 dark:text-ink-400 truncate max-w-[180px]" title="${feedback}"><i class="ri-message-2-line mr-0.5"></i>${feedback}</div>`;
      }

      let actionHtml = '';
      if (approval === 'changes_requested') {
        actionHtml = `<a href="${editUrl}" class="btn-primary text-xs px-2 py-1" style="background:#d97706;font-size:11px;"><i class="ri-edit-line mr-0.5"></i>Edit</a>`;
      } else {
        actionHtml = `<div class="inline-flex gap-1">
          <button class="act-btn" title="View"><i class="ri-eye-line"></i></button>
          <a href="${editUrl}" class="act-btn" title="Edit"><i class="ri-edit-line"></i></a>
        </div>`;
      }

      return `<tr class="border-b border-ink-100 dark:border-ink-800 hover:bg-ink-50/60 dark:hover:bg-ink-800/30 transition">
        <td class="py-3 px-4"><div class="flex items-center gap-3">
          ${img ? `<img src="${img}" class="h-11 w-11 rounded-lg object-cover"/>` : `<div class="h-11 w-11 rounded-lg bg-ink-100 dark:bg-ink-800 grid place-items-center"><i class="ri-home-line text-ink-400"></i></div>`}
          <div><p class="font-semibold text-ink-900 dark:text-white text-sm">${title}</p><p class="text-xs text-ink-400 truncate max-w-[200px]">${p.address || p.location || ''}</p></div>
        </div></td>
        <td class="py-3 px-4 font-semibold text-ink-700 dark:text-ink-200">₹${price.toLocaleString('en-IN')}</td>
        <td class="py-3 px-4">${approvalBadge(approval)}${feedbackHtml}</td>
        <td class="py-3 px-4"><span class="text-xs text-ink-500">${p.status || 'Available'}</span></td>
        <td class="py-3 px-4 text-xs text-ink-500">${posted}</td>
        <td class="py-3 px-4 text-right">${actionHtml}</td>
      </tr>`;
    }).join('');
  }

  const countEl = document.querySelector('#props-count');
  if (countEl) countEl.textContent = `${list.length} properties`;
  const pageInfo = document.querySelector('#props-pageinfo');
  if (pageInfo) pageInfo.textContent = `Page ${propPage} of ${pages}`;

  let pg = '';
  for (let i = 1; i <= pages; i++) {
    pg += `<button onclick="propPage=${i};renderPropsTable()" class="px-3 py-1.5 rounded-lg text-xs font-semibold ${i===propPage?'bg-brand-600 text-white':'text-ink-500 hover:bg-ink-100 dark:hover:bg-ink-800'}">${i}</button>`;
  }
  const pagination = document.querySelector('#props-pagination');
  if (pagination) {
    pagination.innerHTML = `<button onclick="propPage=Math.max(1,propPage-1);renderPropsTable()" class="px-2 py-1.5 rounded-lg text-ink-400 hover:bg-ink-100 dark:hover:bg-ink-800"><i class="ri-arrow-left-s-line"></i></button>${pg}<button onclick="propPage=Math.min(${pages},propPage+1);renderPropsTable()" class="px-2 py-1.5 rounded-lg text-ink-400 hover:bg-ink-100 dark:hover:bg-ink-800"><i class="ri-arrow-right-s-line"></i></button>`;
  }

  // Also re-render gallery when filter changes
  renderPropsGallery();
}

/* ---------- INIT ---------- */
document.addEventListener('DOMContentLoaded', function(){
  const params = new URLSearchParams(window.location.search);
  const action = params.get('action');
  const filter = params.get('filter');
  if (filter) {
    propFilter = filter;
    const filterSelect = document.querySelector('#props-filter');
    if (filterSelect) filterSelect.value = filter;
    const subtitle = document.querySelector('#props-subtitle');
    if (subtitle) subtitle.textContent = 'Showing ' + filter + ' properties';
  }
  if (action === 'add') {
    window.location.href = '/add_property/';
  }

  // Set default view
  setPropView('gallery');
  renderPropsGallery();
  renderPropsTable();
});
