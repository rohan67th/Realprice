/* dashboard.js — Dashboard page renderers */

/* ---------- RENDER: STAT CARDS ---------- */
function renderStats(){
  $('#stat-grid').innerHTML = STATS.map((s,i)=>`
    <div class="card card-hover p-5 animate-fade-in-up stagger-${(i%6)+1}">
      <div class="flex items-start justify-between">
        <div class="h-11 w-11 rounded-xl grid place-items-center ${accentMap[s.accent]}"><i class="${s.icon} text-xl"></i></div>
        <span class="inline-flex items-center gap-1 text-xs font-bold px-2 py-1 rounded-lg ${s.up?'text-success-700 bg-success-50 dark:text-success-300 dark:bg-success-900/30':'text-danger-700 bg-danger-50 dark:text-danger-300 dark:bg-danger-900/30'}"><i class="${s.up?'ri-arrow-up-line':'ri-arrow-down-line'}"></i>${s.trend}%</span>
      </div>
      <p class="mt-4 text-3xl font-extrabold text-ink-900 dark:text-white tracking-tight stat-num" data-val="${s.value}" data-suffix="${s.suffix||''}">0${s.suffix||''}</p>
      <p class="mt-1 text-sm text-ink-500 dark:text-ink-400 font-medium">${s.label}</p>
    </div>`).join('');
  $$('.stat-num').forEach(el=>animateNumber(el,+el.dataset.val,1200,el.dataset.suffix));
}

/* ---------- DASHBOARD: recent properties ---------- */
function renderDashProps(){ $('#dash-properties').innerHTML = PROPERTIES.slice(0,4).map(p=>{const [l,v]=statusBadge(p.status);return `<div class="card card-hover overflow-hidden"><div class="relative h-32 overflow-hidden"><img src="${p.img}" class="h-full w-full object-cover"/><div class="absolute top-2 left-2"><span class="badge-${v} text-[10px]">${l}</span></div></div><div class="p-3"><p class="font-semibold text-sm text-ink-900 dark:text-white truncate">${p.title}</p><p class="text-xs text-ink-400 mt-0.5">${p.location}</p><div class="flex items-center justify-between mt-2"><span class="font-bold text-brand-600 dark:text-brand-400 text-sm">${fmtPrice(p.price)}</span><span class="text-xs text-ink-400"><i class="ri-eye-line"></i> ${fmtNum(p.views)}</span></div></div></div>`}).join(''); }

/* ---------- ACTIVITY TIMELINE ---------- */
function renderActivity(){ $('#activity-timeline').innerHTML = `<div class="absolute left-[18px] top-2 bottom-2 w-px bg-ink-200 dark:bg-ink-700"></div>`+ACTIVITIES.map(a=>`<div class="relative flex gap-3 pb-5 last:pb-0"><div class="relative z-10 h-9 w-9 rounded-xl grid place-items-center shrink-0 ${accentMap[a.accent]}"><i class="${a.icon}"></i></div><div class="pt-1"><p class="text-sm font-semibold text-ink-800 dark:text-ink-100">${a.text}</p><p class="text-xs text-ink-400 mt-0.5">${a.detail}</p><p class="text-[11px] text-ink-400 mt-1"><i class="ri-time-line"></i> ${a.time}</p></div></div>`).join(''); }

/* ---------- DASHBOARD: visits / messages / notifs ---------- */
function renderDashVisits(){
  const visits = window.REAL_DASH_VISITS || window.REAL_VISITS || [];
  const el = $('#dash-visits');
  if (!el) return;

  if (visits.length === 0) {
    el.innerHTML = `
      <div class="p-6 text-center text-ink-400 text-xs">
        <i class="ri-calendar-line text-2xl mb-1 text-ink-300 block"></i>
        No upcoming visits scheduled
      </div>
    `;
    return;
  }

  el.innerHTML = visits.slice(0, 4).map(v => {
    let badgeHtml = '';
    if (v.status === 'approved') {
      badgeHtml = `<span class="badge-success text-[10px]"><i class="ri-checkbox-circle-line"></i> Approved</span>`;
    } else if (v.status === 'completed') {
      badgeHtml = `<span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300"><i class="ri-check-double-line"></i> Completed</span>`;
    } else if (v.status === 'reschedule_proposed') {
      badgeHtml = `<span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-purple-100 text-purple-700 dark:bg-purple-900/40 dark:text-purple-300"><i class="ri-time-line"></i> Rescheduled</span>`;
    } else if (v.status === 'declined') {
      badgeHtml = `<span class="badge-danger text-[10px]"><i class="ri-close-circle-line"></i> Declined</span>`;
    } else if (v.status === 'cancelled') {
      badgeHtml = `<span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300"><i class="ri-forbid-line"></i> Cancelled</span>`;
    } else {
      badgeHtml = `<span class="badge-warning text-[10px]"><i class="ri-time-line"></i> Pending</span>`;
    }

    const avatarHtml = v.photo
      ? `<img src="${v.photo}" class="h-10 w-10 rounded-full object-cover shrink-0"/>`
      : `<div class="h-10 w-10 rounded-full bg-gradient-to-tr from-brand-600 to-brand-400 text-white font-bold text-xs grid place-items-center shrink-0">${v.initials || 'B'}</div>`;

    const chatActionHtml = (v.status === 'approved' || v.status === 'completed') && v.chat_url
      ? `<a href="${v.chat_url}" class="text-[11px] font-semibold text-brand-600 hover:text-brand-700 inline-flex items-center gap-1 mt-1"><i class="ri-chat-3-line"></i> Chat</a>`
      : `<span class="text-[10px] text-ink-400 dark:text-ink-500 inline-flex items-center gap-0.5 mt-1" title="Chat unlocks after approval"><i class="ri-lock-line"></i> Chat</span>`;

    return `
      <div class="flex items-center gap-3 p-3 rounded-xl hover:bg-ink-50 dark:hover:bg-ink-800/40 transition">
        ${avatarHtml}
        <div class="flex-1 min-w-0">
          <p class="text-sm font-semibold text-ink-900 dark:text-white truncate">${v.buyer || v.buyer_name}</p>
          <p class="text-xs text-ink-400 truncate">${v.property || v.property_title}</p>
        </div>
        <div class="text-right shrink-0">
          <p class="text-xs font-semibold text-ink-700 dark:text-ink-200">${v.date}</p>
          <p class="text-[11px] text-ink-400">${v.time}</p>
          <div class="flex items-center justify-end gap-2 mt-1">
            ${badgeHtml}
            ${chatActionHtml}
          </div>
        </div>
      </div>
    `;
  }).join('');
}

function renderDashMessages(){
  const el = $('#dash-messages');
  if (!el) return;
  const msgs = window.REAL_DASH_MESSAGES || [];
  if (msgs.length === 0) {
    el.innerHTML = `
      <div class="p-6 text-center text-ink-400 text-xs">
        <i class="ri-chat-3-line text-2xl mb-1 text-ink-300 block"></i>
        No messages yet.<br/>Messages for approved visits will appear here.
      </div>
    `;
    return;
  }

  el.innerHTML = msgs.slice(0, 4).map(c => {
    const avatarHtml = c.avatar
      ? `<img src="${c.avatar}" class="h-9 w-9 rounded-full object-cover shrink-0"/>`
      : `<div class="h-9 w-9 rounded-full bg-gradient-to-tr from-brand-600 to-brand-400 text-white font-bold text-xs grid place-items-center shrink-0">${c.initials || 'B'}</div>`;

    return `
      <a href="${c.chat_url}" class="w-full flex items-center gap-3 p-2.5 rounded-xl hover:bg-ink-50 dark:hover:bg-ink-800/40 transition text-left block">
        <div class="relative shrink-0">
          ${avatarHtml}
        </div>
        <div class="flex-1 min-w-0">
          <p class="text-sm font-semibold text-ink-900 dark:text-white truncate">${c.name}</p>
          <p class="text-xs text-ink-400 truncate">${c.last}</p>
        </div>
        <div class="text-right shrink-0">
          <p class="text-[10px] text-ink-400">${c.time}</p>
          <span class="inline-flex items-center gap-1 text-[10px] text-brand-600 font-semibold mt-1"><i class="ri-chat-3-line"></i> Chat</span>
        </div>
      </a>
    `;
  }).join('');
}
function renderDashNotifs(){ $('#dash-notifs').innerHTML = NOTIFS.slice(0,4).map(n=>`<div class="flex gap-3 p-2.5 rounded-xl hover:bg-ink-50 dark:hover:bg-ink-800/40 transition ${n.read?'opacity-60':''}"><div class="h-8 w-8 rounded-lg grid place-items-center shrink-0 ${accentMap[n.accent]}"><i class="${n.icon} text-sm"></i></div><div class="flex-1 min-w-0"><p class="text-sm font-semibold text-ink-800 dark:text-ink-100">${n.title}</p><p class="text-xs text-ink-400 truncate">${n.body}</p><p class="text-[10px] text-ink-400 mt-0.5">${n.time}</p></div>${n.read?'':'<span class="h-2 w-2 rounded-full bg-brand-500 mt-1.5 shrink-0"></span>'}</div>`).join(''); }
function renderTopbarNotifs(){ $('#topbar-notifs').innerHTML = NOTIFS.slice(0,4).map(n=>`<div class="flex gap-3 p-3 hover:bg-ink-50 dark:hover:bg-ink-800/40 transition cursor-pointer ${n.read?'opacity-60':''}"><div class="h-8 w-8 rounded-lg grid place-items-center shrink-0 ${accentMap[n.accent]}"><i class="${n.icon} text-sm"></i></div><div class="flex-1 min-w-0"><p class="text-sm font-semibold text-ink-800 dark:text-ink-100">${n.title}</p><p class="text-xs text-ink-400 truncate">${n.body}</p></div></div>`).join(''); }

/* ---------- RENDER CHARTS ---------- */
function renderCharts(){
  barChart($('#dash-revenue-chart'),[{label:'Jan',value:42},{label:'Feb',value:58},{label:'Mar',value:51},{label:'Apr',value:73},{label:'May',value:64},{label:'Jun',value:88},{label:'Jul',value:96}],'brand');
  donutChart($('#dash-donut'),[{label:'Views',value:24890,color:'brand'},{label:'Inquiries',value:3120,color:'warning'},{label:'Visits',value:480,color:'success'},{label:'Closed',value:31,color:'danger'}]);
  donutLegend($('#dash-donut-legend'),[{label:'Views',value:24890,color:'brand'},{label:'Inquiries',value:3120,color:'warning'},{label:'Visits',value:480,color:'success'},{label:'Closed',value:31,color:'danger'}]);
}

/* ---------- INIT ---------- */
document.addEventListener('DOMContentLoaded',function(){
  renderStats(); renderDashProps(); renderActivity(); renderDashVisits(); renderDashMessages(); renderDashNotifs(); renderTopbarNotifs(); renderCharts();
});
