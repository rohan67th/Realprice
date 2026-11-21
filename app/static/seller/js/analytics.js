/* analytics.js — Analytics page renderer */
function renderAnalytics(){
  barChart($('#ana-revenue'),[{label:'Jan',value:42},{label:'Feb',value:58},{label:'Mar',value:51},{label:'Apr',value:73},{label:'May',value:64},{label:'Jun',value:88},{label:'Jul',value:96}],'brand');
  lineChart($('#ana-views'),[{label:'Mon',value:320},{label:'Tue',value:480},{label:'Wed',value:410},{label:'Thu',value:620},{label:'Fri',value:740},{label:'Sat',value:890},{label:'Sun',value:720}]);
  barChart($('#ana-sales'),[{label:'Q1',value:151},{label:'Q2',value:225},{label:'Q3',value:188},{label:'Q4',value:274}],'success');
  donutChart($('#ana-donut'),[{label:'Views',value:24890,color:'brand'},{label:'Inquiries',value:3120,color:'warning'},{label:'Visits',value:480,color:'success'},{label:'Closed',value:31,color:'danger'}]);
  donutLegend($('#ana-donut-legend'),[{label:'Views',value:24890,color:'brand'},{label:'Inquiries',value:3120,color:'warning'},{label:'Visits',value:480,color:'success'},{label:'Closed',value:31,color:'danger'}]);
  // property performance (horizontal bars)
  const perf=[{t:'Bay View Modern Villa',v:100},{t:'Sunset Boulevard Estate',v:92},{t:'Garden View Family Home',v:72},{t:'Skyline Penthouse Loft',v:63},{t:'Marina waterfront Condo',v:53}];
  $('#ana-perf').innerHTML=perf.map(p=>`<div><div class="flex justify-between text-sm mb-1"><span class="text-ink-700 dark:text-ink-200 font-medium">${p.t}</span><span class="text-ink-400 text-xs">${p.v}%</span></div><div class="h-2 rounded-full bg-ink-100 dark:bg-ink-800 overflow-hidden"><div class="h-full bg-brand-500 rounded-full transition-all duration-700" style="width:${p.v}%"></div></div></div>`).join('');
  // popular properties
  const pop=[{t:'Sunset Boulevard Estate',v:3410,p:100},{t:'Bay View Modern Villa',v:2930,p:86},{t:'Garden View Family Home',v:2110,p:62},{t:'Skyline Penthouse Loft',v:1842,p:54},{t:'Marina waterfront Condo',v:1560,p:46}];
  $('#ana-popular').innerHTML=pop.map((p,i)=>`<div class="flex items-center gap-3"><span class="h-7 w-7 rounded-lg grid place-items-center text-xs font-bold ${i===0?'bg-warning-100 text-warning-700 dark:bg-warning-900/30 dark:text-warning-300':'bg-ink-100 text-ink-500 dark:bg-ink-800 dark:text-ink-400'}">${i+1}</span><div class="flex-1 min-w-0"><p class="text-sm font-semibold text-ink-800 dark:text-ink-100 truncate">${p.t}</p><div class="h-1.5 rounded-full bg-ink-100 dark:bg-ink-800 mt-1.5 overflow-hidden"><div class="h-full bg-gradient-to-r from-brand-400 to-brand-600 rounded-full" style="width:${p.p}%"></div></div></div><span class="text-xs font-bold text-ink-700 dark:text-ink-200 shrink-0"><i class="ri-eye-line"></i> ${fmtNum(p.v)}</span></div>`).join('');
}

document.addEventListener('DOMContentLoaded', function(){
  renderAnalytics();
});
