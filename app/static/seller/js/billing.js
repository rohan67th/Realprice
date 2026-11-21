/* billing.js — Rent requests and billing history renderers */
function renderRent(){ $('#rent-tbody').innerHTML = RENT.map(r=>{const [l,v]=r.st==='pending'?['Pending','warning']:['Approved','success'];return `<tr class="border-b border-ink-100 dark:border-ink-800 hover:bg-ink-50/60 dark:hover:bg-ink-800/30"><td class="py-3 px-4 font-semibold text-ink-800 dark:text-ink-100">${r.tenant}</td><td class="py-3 px-4 text-ink-500">${r.prop}</td><td class="py-3 px-4 font-semibold text-ink-700 dark:text-ink-200">${r.amt}</td><td class="py-3 px-4 text-ink-500">${r.dur}</td><td class="py-3 px-4"><span class="badge-${v}">${l}</span></td><td class="py-3 px-4 text-right"><button class="btn-outline text-xs px-3 py-1.5">${r.st==='pending'?'Review':'View'}</button></td></tr>`}).join(''); }
function renderBills(){ $('#bill-tbody').innerHTML = BILLS.map(b=>`<tr class="border-b border-ink-100 dark:border-ink-800 hover:bg-ink-50/60 dark:hover:bg-ink-800/30"><td class="py-3 px-4 font-mono text-xs text-ink-600 dark:text-ink-300">${b.inv}</td><td class="py-3 px-4 text-ink-500">${b.date}</td><td class="py-3 px-4 text-ink-700 dark:text-ink-200">${b.desc}</td><td class="py-3 px-4 font-semibold text-ink-800 dark:text-white">${b.amt}</td><td class="py-3 px-4"><span class="badge-success">Paid</span></td><td class="py-3 px-4 text-right"><button class="act-btn"><i class="ri-download-line"></i></button></td></tr>`).join(''); }

document.addEventListener('DOMContentLoaded', function(){
  if ($('#rent-tbody')) renderRent();
  if ($('#bill-tbody')) renderBills();
});
