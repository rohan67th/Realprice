/* calendar.js — Calendar page renderer with real visit events */
function renderCalendar(){
  const now = new Date();
  const currentYear = now.getFullYear();
  const currentMonth = now.getMonth(); // 0-indexed
  const today = now.getDate();

  // Set month & year title
  const calHeader = document.querySelector('#page-calendar h2 + p');
  if (calHeader) {
    calHeader.textContent = now.toLocaleDateString('en-US', { month: 'long', year: 'numeric' });
  }

  // Days calculation
  const firstDow = new Date(currentYear, currentMonth, 1).getDay();
  const daysInMonth = new Date(currentYear, currentMonth + 1, 0).getDate();

  const realEvents = window.REAL_CALENDAR_EVENTS || [];

  let html = '';
  for(let i = 0; i < firstDow; i++) {
    html += `<div class="cal-cell opacity-0"></div>`;
  }

  for(let d = 1; d <= daysInMonth; d++){
    const evs = realEvents.filter(e => (!e.month || e.month === (currentMonth + 1)) && (!e.year || e.year === currentYear) && e.day === d);
    const isToday = d === today;
    const dotMap = {
      visit: 'bg-brand-500',
      inspection: 'bg-warning-500',
      rent: 'bg-success-500',
      closing: 'bg-danger-500'
    };

    html += `
      <div class="cal-cell ${isToday ? 'ring-2 ring-brand-500 bg-brand-50/50 dark:bg-brand-900/20' : ''} ${evs.length ? 'has-event' : ''}">
        <span class="cal-day ${isToday ? 'text-brand-600 dark:text-brand-400 font-bold' : ''}">${d}</span>
        ${evs.slice(0, 2).map(e => `
          <div class="cal-event ${e.type || 'visit'}">
            <span class="cal-dot ${dotMap[e.type] || 'bg-brand-500'}"></span>
            <span class="truncate">${e.title}</span>
          </div>
        `).join('')}
        ${evs.length > 2 ? `<span class="text-[10px] text-ink-400 px-1">+${evs.length - 2} more</span>` : ''}
      </div>
    `;
  }

  const calGrid = document.getElementById('cal-grid');
  if (calGrid) calGrid.innerHTML = html;

  const todayEvs = realEvents.filter(e => (!e.month || e.month === (currentMonth + 1)) && (!e.year || e.year === currentYear) && e.day === today);
  const calToday = document.getElementById('cal-today');
  if (calToday) {
    if (todayEvs.length > 0) {
      calToday.innerHTML = todayEvs.map(e => {
        const c = { visit: 'brand', inspection: 'warning', rent: 'success', closing: 'danger' }[e.type] || 'brand';
        return `
          <div class="p-3 rounded-xl bg-ink-50 dark:bg-ink-800/40">
            <div class="flex items-center gap-2">
              <span class="h-2 w-2 rounded-full bg-${c}-500"></span>
              <p class="text-sm font-semibold text-ink-800 dark:text-ink-100">${e.title}</p>
            </div>
            <p class="text-xs text-ink-400 mt-1 pl-4">${e.time || 'All Day'}</p>
          </div>
        `;
      }).join('');
    } else {
      calToday.innerHTML = `<p class="text-sm text-ink-400 italic">No events scheduled for today</p>`;
    }
  }
}

document.addEventListener('DOMContentLoaded', function(){
  renderCalendar();
});
