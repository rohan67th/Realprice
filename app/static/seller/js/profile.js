/* profile.js — Profile page renderer */
function renderProfileRing(){ const el=$('#profile-ring'); const pct=82; el.innerHTML=`<svg viewBox="0 0 100 100" class="w-full h-full -rotate-90"><circle cx="50" cy="50" r="42" fill="none" stroke="#e2e8f0" stroke-width="8" class="dark:stroke-ink-700"/><circle cx="50" cy="50" r="42" fill="none" stroke="#3b82f6" stroke-width="8" stroke-linecap="round" stroke-dasharray="${2*Math.PI*42}" stroke-dashoffset="${2*Math.PI*42*(1-pct/100)}" style="transition:stroke-dashoffset 1s ease"/></svg>`; }

document.addEventListener('DOMContentLoaded', function(){
  if ($('#profile-ring')) renderProfileRing();
});
