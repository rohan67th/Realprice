/* =========================================================
   common.js — Shared data, helpers, theme, sidebar,
   navigation, dropdowns, ripple, modals, chart functions
   Loaded in seller/base.html via {% static %}
========================================================= */

var SELLER = window.CURRENT_SELLER || { name: 'Seller' };
const PROPERTIES = [
  {id:'p1',title:'Skyline Penthouse Loft',type:'Penthouse',location:'SoMa, San Francisco',price:2850000,status:'available',beds:3,baths:3,area:2450,views:1842,inquiries:34,visits:12,fav:true,img:'https://images.pexels.com/photos/1571055/pexels-photo-1571055.jpeg?auto=compress&cs=tinysrgb&w=900&h=620&fit=crop',updated:'2h ago'},
  {id:'p2',title:'Bay View Modern Villa',type:'Villa',location:'Pacific Heights, SF',price:4950000,status:'available',beds:5,baths:4,area:4100,views:2930,inquiries:58,visits:19,fav:false,img:'https://images.pexels.com/photos/1396122/pexels-photo-1396122.jpeg?auto=compress&cs=tinysrgb&w=900&h=620&fit=crop',updated:'5h ago'},
  {id:'p3',title:'Heritage Victorian Townhouse',type:'Townhouse',location:'Nob Hill, SF',price:1980000,status:'pending',beds:4,baths:3,area:3200,views:1240,inquiries:27,visits:8,fav:false,img:'https://images.pexels.com/photos/143453/pexels-photo-143453.jpeg?auto=compress&cs=tinysrgb&w=900&h=620&fit=crop',updated:'1d ago'},
  {id:'p4',title:'Minimalist Studio Apartment',type:'Apartment',location:'Mission District, SF',price:720000,status:'available',beds:1,baths:1,area:680,views:980,inquiries:15,visits:6,fav:true,img:'https://images.pexels.com/photos/164877/pexels-photo-164877.jpeg?auto=compress&cs=tinysrgb&w=900&h=620&fit=crop',updated:'3d ago'},
  {id:'p5',title:'Garden View Family Home',type:'House',location:'Noe Valley, SF',price:1650000,status:'sold',beds:3,baths:2,area:1850,views:2110,inquiries:41,visits:15,fav:false,img:'https://images.pexels.com/photos/1111360/pexels-photo-1111360.jpeg?auto=compress&cs=tinysrgb&w=900&h=620&fit=crop',updated:'1w ago'},
  {id:'p6',title:'Marina waterfront Condo',type:'Condo',location:'Marina District, SF',price:1320000,status:'available',beds:2,baths:2,area:1320,views:1560,inquiries:22,visits:9,fav:false,img:'https://images.pexels.com/photos/323780/pexels-photo-323780.jpeg?auto=compress&cs=tinysrgb&w=900&h=620&fit=crop',updated:'2w ago'},
  {id:'p7',title:'Industrial Loft Conversion',type:'Loft',location:'Dogpatch, SF',price:890000,status:'draft',beds:2,baths:1,area:1100,views:0,inquiries:0,visits:0,fav:false,img:'https://images.pexels.com/photos/53610/pexels-photo-53610.jpeg?auto=compress&cs=tinysrgb&w=900&h=620&fit=crop',updated:'3w ago'},
  {id:'p8',title:'Sunset Boulevard Estate',type:'Estate',location:'Sunset, SF',price:3200000,status:'available',beds:6,baths:5,area:5200,views:3410,inquiries:67,visits:21,fav:true,img:'https://images.pexels.com/photos/1396122/pexels-photo-1396122.jpeg?auto=compress&cs=tinysrgb&w=900&h=620&fit=crop',updated:'4w ago'},
];
const STATS = [
  {label:'Total Properties',value:48,trend:12.5,up:true,icon:'ri-building-2',accent:'brand'},
  {label:'Available',value:17,trend:4.2,up:true,icon:'ri-home-5',accent:'success'},
  {label:'Sold',value:31,trend:18.0,up:true,icon:'ri-checkbox-circle',accent:'warning'},
  {label:'Pending Requests',value:9,trend:3.1,up:false,icon:'ri-time',accent:'danger'},
  {label:'Property Views',value:24890,trend:22.4,up:true,icon:'ri-eye',accent:'brand'},
  {label:'Scheduled Visits',value:23,trend:8.7,up:true,icon:'ri-calendar-check',accent:'success'},
  {label:'Unread Chats',value:7,trend:2.0,up:false,icon:'ri-chat-3',accent:'warning'},
  {label:'Profile Completion',value:82,suffix:'%',trend:6.0,up:true,icon:'ri-user-check',accent:'brand'},
];
const ACTIVITIES = [
  {text:'Buyer viewed property',detail:'Marcus Lee viewed Bay View Modern Villa',time:'12 min ago',icon:'ri-eye',accent:'brand'},
  {text:'Property edited',detail:'Updated pricing for Skyline Penthouse Loft',time:'1 hour ago',icon:'ri-edit-2',accent:'warning'},
  {text:'Visit confirmed',detail:'Visit scheduled for Heritage Victorian',time:'3 hours ago',icon:'ri-calendar-check',accent:'success'},
  {text:'Rent request received',detail:'New rent request for Marina Condo',time:'6 hours ago',icon:'ri-wallet-3',accent:'danger'},
  {text:'Property listed',detail:'Sunset Boulevard Estate is now live',time:'1 day ago',icon:'ri-add-circle',accent:'brand'},
  {text:'Profile updated',detail:'Verification documents uploaded',time:'2 days ago',icon:'ri-user-check',accent:'success'},
];
const VISITS = window.REAL_VISITS || [];
const NOTIFS = [
  {id:'n1',title:'Property Inquiry',body:'New inquiry on Bay View Modern Villa from Olivia B.',time:'8 min ago',type:'inquiry',icon:'ri-question-answer',accent:'brand',read:false},
  {id:'n2',title:'Visit Request',body:'Marcus Lee requested a visit for Skyline Penthouse',time:'40 min ago',type:'visit',icon:'ri-calendar-todo',accent:'success',read:false},
  {id:'n3',title:'Rent Approval Needed',body:'Rent request for Marina Condo awaits your approval',time:'2h ago',type:'rent',icon:'ri-wallet-3',accent:'warning',read:false},
  {id:'n4',title:'Profile Verification',body:'Your government ID verification was approved',time:'5h ago',type:'verification',icon:'ri-shield-check',accent:'success',read:true},
  {id:'n5',title:'Document Uploaded',body:'New title deed uploaded for Sunset Estate',time:'1d ago',type:'document',icon:'ri-file-upload',accent:'brand',read:true},
];
const CALENDAR = [
  {day:8,title:'Property Tour',type:'visit',time:'10:30 AM'},{day:8,title:'Penthouse Visit',type:'visit',time:'2:00 PM'},
  {day:9,title:'Victorian Inspection',type:'inspection',time:'11:15 AM'},{day:11,title:'Rent Meeting',type:'rent',time:'4:45 PM'},
  {day:15,title:'Closing Date',type:'closing',time:'9:00 AM'},{day:18,title:'Estate Inspection',type:'inspection',time:'1:00 PM'},
  {day:22,title:'Condo Visit',type:'visit',time:'3:30 PM'},
];
const RENT = [
  {tenant:'Olivia Bennett',prop:'Bay View Modern Villa',amt:'$8,500',dur:'12 months',st:'pending'},
  {tenant:'James Carter',prop:'Marina waterfront Condo',amt:'$4,200',dur:'6 months',st:'pending'},
  {tenant:'Emma Wilson',prop:'Minimalist Studio',amt:'$2,800',dur:'12 months',st:'approved'},
  {tenant:'Marcus Lee',prop:'Skyline Penthouse',amt:'$12,000',dur:'24 months',st:'approved'},
];
const BILLS = [
  {inv:'INV-2026-014',date:'Jul 01, 2026',desc:'Premium subscription',amt:'$99.00',st:'paid'},
  {inv:'INV-2026-013',date:'Jun 03, 2026',desc:'Featured listing boost',amt:'$49.00',st:'paid'},
  {inv:'INV-2026-012',date:'May 28, 2026',desc:'Payout — Garden View Home',amt:'$1,650,000',st:'paid'},
  {inv:'INV-2026-011',date:'May 01, 2026',desc:'Premium subscription',amt:'$99.00',st:'paid'},
];

/* ---------- HELPERS ---------- */
const $ = (s,r=document)=>r.querySelector(s);
const $$ = (s,r=document)=>[...r.querySelectorAll(s)];
const fmtPrice = n => n>=1e6 ? '$'+(n/1e6).toFixed(2)+'M' : '$'+Math.round(n/1e3)+'K';
const fmtNum = n => n>=1e3 ? (n/1e3).toFixed(1)+'k' : ''+n;
const accentMap = {
  brand:'bg-brand-50 text-brand-600 dark:bg-brand-900/30 dark:text-brand-400',
  success:'bg-success-50 text-success-600 dark:bg-success-900/30 dark:text-success-400',
  warning:'bg-warning-50 text-warning-600 dark:bg-warning-900/30 dark:text-warning-400',
  danger:'bg-danger-50 text-danger-600 dark:bg-danger-900/30 dark:text-danger-400',
};
const statusBadge = s => ({available:['Available','success'],pending:['Pending','warning'],sold:['Sold','danger'],draft:['Draft','neutral']}[s]||['Unknown','neutral']);

/* ---------- THEME ---------- */
function applyTheme(t){ const r=document.documentElement; r.classList.toggle('dark',t==='dark'); localStorage.setItem('theme',t); $('#theme-icon').className = t==='dark'?'ri-sun-line text-lg':'ri-moon-line text-lg'; }
function toggleTheme(){ applyTheme(localStorage.getItem('theme')==='dark'?'light':'dark'); }
function setTheme(t){ applyTheme(t); }
(function initTheme(){ const t=localStorage.getItem('theme')||(matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light'); applyTheme(t); })();

/* ---------- SIDEBAR ---------- */
function toggleSidebar(){ const s=$('#sidebar'),o=$('#overlay'); s.classList.toggle('-translate-x-full'); o.classList.toggle('hidden'); }
function closeSidebarOnMobile(){ if(innerWidth<1024){ $('#sidebar').classList.add('-translate-x-full'); $('#overlay').classList.add('hidden'); } }

/* ---------- NAVIGATION ---------- */
/* NOTE: navigate() currently toggles .page sections client-side (SPA-style).
   When real Django URLs are wired up, replace navigate() calls with
   window.location or {% url %} links. For now, kept as-is for compatibility. */
const PAGE_TITLES = {dashboard:'Dashboard',properties:'My Properties',visits:'Scheduled Visits',calendar:'Calendar',chats:'Chats',notifications:'Notifications','rent-requests':'Rent Requests',billing:'Billing History',analytics:'Analytics',profile:'Profile',settings:'Settings','empty-states':'Empty States','loading-states':'Loading States'};
function navigate(page, action, filter){
  const target = $('#page-'+page);
  if(!target) {
    const sellerId = $('#sidebar')?.dataset?.userId || '';
    if (sellerId) {
      let pageSuffix = page;
      if (page === 'profile') pageSuffix = 'profile-details';
      let url = page === 'dashboard' ? `/seller_profile/${sellerId}/` : `/seller_profile/${sellerId}/${pageSuffix}/`;
      const query = [];
      if (action) query.push(`action=${action}`);
      if (filter) query.push(`filter=${filter}`);
      if (query.length > 0) url += '?' + query.join('&');
      window.location.href = url;
    }
    return;
  }
  $$('.page').forEach(p=>p.classList.remove('active'));
  target.classList.add('active');
  $$('.nav-item').forEach(n=>n.classList.remove('active'));
  $$(`.nav-item[data-page="${page}"]`).forEach(n=>n.classList.add('active'));
  $('#crumb').textContent = PAGE_TITLES[page]||page;
  closeSidebarOnMobile();
  scrollTo({top:0,behavior:'smooth'});
  // page-specific actions
  if(page==='properties'){ if(filter){ propFilter=filter; $('#props-filter').value=filter; $('#props-subtitle').textContent='Showing '+filter+' properties'; } else { propFilter='all'; $('#props-filter').value='all'; $('#props-subtitle').textContent='Manage and track all your listings'; } if(action==='add'){ window.location.href = '/add_property/'; } if(typeof renderPropsGallery==='function') renderPropsGallery(); if(typeof renderPropsTable==='function') renderPropsTable(); }
}
$$('.nav-item').forEach(n=>n.addEventListener('click',()=>navigate(n.dataset.page, n.dataset.action, n.dataset.filter)));

document.addEventListener('DOMContentLoaded', function(){
  const activePageEl = $('.page.active');
  if (activePageEl) {
    const pageName = activePageEl.id.replace('page-', '');
    $$('.nav-item').forEach(n=>n.classList.remove('active'));
    $$(`.nav-item[data-page="${pageName}"]`).forEach(n=>n.classList.add('active'));
    const crumbEl = $('#crumb');
    if (crumbEl) crumbEl.textContent = PAGE_TITLES[pageName]||pageName;
  }
});

/* ---------- DROPDOWNS ---------- */
function toggleDropdown(id,e){ e.stopPropagation(); const dd=$('#'+id); const open=!dd.classList.contains('hidden'); $$('.dropdown').forEach(d=>d.classList.add('hidden')); if(!open) dd.classList.remove('hidden'); }
document.addEventListener('click',()=>$$('.dropdown').forEach(d=>d.classList.add('hidden')));

/* ---------- RIPPLE ---------- */
document.addEventListener('click',e=>{ const b=e.target.closest('.btn-ripple'); if(!b)return; const c=document.createElement('span'); const d=Math.max(b.clientWidth,b.clientHeight); const r=b.getBoundingClientRect(); c.style.width=c.style.height=d+'px'; c.style.left=(e.clientX-r.left-d/2)+'px'; c.style.top=(e.clientY-r.top-d/2)+'px'; c.className='ripple'; const old=b.querySelector('.ripple'); if(old)old.remove(); b.appendChild(c); setTimeout(()=>c.remove(),600); });

/* ---------- MODALS ---------- */
function openModal(id){ $('#'+id).classList.remove('hidden'); document.body.style.overflow='hidden'; }
function closeModal(id){ $('#'+id).classList.add('hidden'); document.body.style.overflow=''; }
document.addEventListener('keydown',e=>{ if(e.key==='Escape')$$('.modal-wrap').forEach(m=>m.classList.add('hidden')); });

/* ---------- ANIMATED COUNTER ---------- */
function animateNumber(el,target,dur=1200,suffix=''){
  let started=false;
  const obs=new IntersectionObserver(entries=>{ if(entries[0].isIntersecting&&!started){started=true; const s=performance.now(); const tick=n=>{ const p=Math.min((n-s)/dur,1); const e=1-Math.pow(1-p,3); const v=Math.round(target*e); el.textContent=(target>999?fmtNum(v):v)+suffix; if(p<1)requestAnimationFrame(tick); }; requestAnimationFrame(tick); }},{threshold:.4}); obs.observe(el);
}

/* ---------- PLACEHOLDER CHARTS (pure CSS/SVG) ---------- */
function barChart(el,data,color='brand'){
  const max=Math.max(...data.map(d=>d.value));
  el.innerHTML = `<div class="flex items-end justify-between gap-2 h-full pt-4">${data.map((d,i)=>`<div class="flex-1 flex flex-col items-center justify-end h-full gap-2 group"><div class="w-full rounded-t-lg bg-${color}-100 dark:bg-${color}-900/40 relative overflow-hidden transition-all duration-500 group-hover:bg-${color}-200 dark:group-hover:bg-${color}-900/60" style="height:${(d.value/max*100)}%; animation:fade-in-up .6s ease-out ${i*60}ms both"><div class="absolute bottom-0 inset-x-0 bg-${color}-500 rounded-t-lg" style="height:${d.value/max*100}%"></div></div><span class="text-[10px] text-ink-400 font-medium">${d.label}</span></div>`).join('')}</div>`;
}
function lineChart(el,data){
  const max=Math.max(...data.map(d=>d.value)); const min=Math.min(...data.map(d=>d.value));
  const w=100,h=100; const pts=data.map((d,i)=>[ (i/(data.length-1))*w, h-((d.value-min)/(max-min))*h*0.85-7.5 ]);
  const path=pts.map((p,i)=>(i?'L':'M')+p[0].toFixed(1)+' '+p[1].toFixed(1)).join(' ');
  const area=path+` L${w} ${h} L0 ${h} Z`;
  el.innerHTML=`<svg viewBox="0 0 ${w} ${h}" preserveAspectRatio="none" class="w-full h-full"><defs><linearGradient id="lg${el.id}" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="#3b82f6" stop-opacity=".25"/><stop offset="100%" stop-color="#3b82f6" stop-opacity="0"/></linearGradient></defs><path d="${area}" fill="url(#lg${el.id})"/><path d="${path}" fill="none" stroke="#3b82f6" stroke-width="1.5" vector-effect="non-scaling-stroke" stroke-linecap="round" stroke-linejoin="round"/>${pts.map(p=>`<circle cx="${p[0]}" cy="${p[1]}" r="1.2" fill="#3b82f6" vector-effect="non-scaling-stroke"/>`).join('')}</svg><div class="flex justify-between mt-2">${data.map(d=>`<span class="text-[10px] text-ink-400">${d.label}</span>`).join('')}</div>`;
}
function donutChart(el,segments){
  const total=segments.reduce((s,x)=>s+x.value,0); const c=2*Math.PI*42; let off=0;
  const seg=segments.map(s=>{ const len=(s.value/total)*c; const dash=`${len} ${c-len}`; const dashOff=-off; off+=len; const col={brand:'#3b82f6',warning:'#f59e0b',success:'#10b981',danger:'#ef4444'}[s.color]; return `<circle cx="50" cy="50" r="42" fill="none" stroke="${col}" stroke-width="10" stroke-dasharray="${dash}" stroke-dashoffset="${dashOff}" stroke-linecap="round" transform="rotate(-90 50 50)" style="transition:stroke-dasharray 1s ease"/>`; }).join('');
  el.innerHTML=`<svg viewBox="0 0 100 100" class="w-full h-full">${seg}<circle cx="50" cy="50" r="42" fill="none" stroke="#e2e8f0" stroke-width="10" class="dark:stroke-ink-700" style="opacity:.0"/></svg><div class="absolute inset-0 grid place-items-center"><div class="text-center"><p class="text-2xl font-extrabold text-ink-900 dark:text-white">3.1%</p><p class="text-[10px] text-ink-400">Close rate</p></div></div>`;
}
function donutLegend(el,segments){
  const total=segments.reduce((s,x)=>s+x.value,0);
  el.innerHTML=segments.map(s=>{const col={brand:'bg-brand-500',warning:'bg-warning-500',success:'bg-success-500',danger:'bg-danger-500'}[s.color];return `<div class="flex items-center gap-2 text-sm"><span class="h-2.5 w-2.5 rounded-full ${col}"></span><span class="text-ink-600 dark:text-ink-300 flex-1">${s.label}</span><span class="font-semibold text-ink-800 dark:text-white text-xs">${fmtNum(s.value)}</span></div>`}).join('');
}
