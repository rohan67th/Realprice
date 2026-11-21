/* notifications.js — Notifications page renderer */
function renderNotifList(){ $('#notif-list').innerHTML = NOTIFS.map(n=>`<div class="flex gap-4 p-4 hover:bg-ink-50/60 dark:hover:bg-ink-800/30 transition cursor-pointer ${n.read?'opacity-60':''}"><div class="h-10 w-10 rounded-xl grid place-items-center shrink-0 ${accentMap[n.accent]}"><i class="${n.icon}"></i></div><div class="flex-1 min-w-0"><div class="flex items-center gap-2"><p class="font-semibold text-ink-900 dark:text-white text-sm">${n.title}</p>${n.read?'':'<span class="h-2 w-2 rounded-full bg-brand-500"></span>'}</div><p class="text-sm text-ink-500 dark:text-ink-400 mt-0.5">${n.body}</p><p class="text-xs text-ink-400 mt-1">${n.time}</p></div></div>`).join(''); }

document.addEventListener('DOMContentLoaded', function(){
  renderNotifList();
});
