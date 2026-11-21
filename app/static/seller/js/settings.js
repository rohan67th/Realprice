/* settings.js — Settings page renderer */
function renderSettingsLists(){
  const notifOpts=[{t:'Property inquiries',on:true},{t:'Visit requests',on:true},{t:'Rent approvals',on:true},{t:'Document uploads',on:false},{t:'Marketing tips',on:false}];
  $('#set-notif-list').innerHTML=notifOpts.map(o=>toggleRow(o.t,o.on)).join('');
  const privOpts=[{t:'Show profile to public',on:true},{t:'Allow buyer messages',on:true},{t:'Show contact details',on:false},{t:'Appear in search results',on:true}];
  $('#set-privacy-list').innerHTML=privOpts.map(o=>toggleRow(o.t,o.on)).join('');
  $$('.toggle').forEach(t=>t.addEventListener('click',()=>{t.classList.toggle('on'); t.querySelector('.knob').classList.toggle('translate-x-4');}));
}
function toggleRow(label,on){ return `<div class="flex items-center justify-between py-3 border-b border-ink-100 dark:border-ink-800 last:border-0"><span class="text-sm text-ink-700 dark:text-ink-200 font-medium">${label}</span><button class="toggle ${on?'on':''}"><span class="knob ${on?'translate-x-4':''}"></span></button></div>`; }

document.addEventListener('DOMContentLoaded', function(){
  // Bind set-tab clicks
  $$('.set-tab').forEach(t=>t.addEventListener('click',()=>{
    $$('.set-tab').forEach(x=>x.classList.remove('active'));
    t.classList.add('active');
    $$('.set-panel').forEach(p=>p.classList.toggle('hidden',p.dataset.panel!==t.dataset.tab));
  }));
  renderSettingsLists();
});
