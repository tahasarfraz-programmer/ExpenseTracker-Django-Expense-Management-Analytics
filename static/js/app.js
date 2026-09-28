(function () {
  'use strict';
  var root = document.documentElement;

  // theme toggle
  var themeBtn = document.getElementById('theme');
  if (themeBtn) themeBtn.addEventListener('click', function () {
    var dark = getComputedStyle(root).getPropertyValue('--bg').trim() === '#0b1320';
    var next = dark ? 'light' : 'dark';
    root.dataset.theme = next;
    try { localStorage.setItem('theme', next); } catch (e) {}
    window.dispatchEvent(new Event('themechange'));
  });

  // mobile sidebar
  var sb = document.getElementById('sidebar'), scrim = document.getElementById('scrim'), menu = document.getElementById('menu');
  function toggle(open) { if (!sb) return; sb.classList.toggle('open', open); scrim.classList.toggle('show', open); }
  if (menu) menu.addEventListener('click', function () { toggle(!sb.classList.contains('open')); });
  if (scrim) scrim.addEventListener('click', function () { toggle(false); });

  // confirm destructive actions
  document.addEventListener('submit', function (e) {
    var msg = e.target.getAttribute('data-confirm');
    if (msg && !window.confirm(msg)) e.preventDefault();
  });

  // auto-dismiss toasts
  setTimeout(function () {
    document.querySelectorAll('.toast').forEach(function (t) { t.style.opacity = 0; setTimeout(function () { t.remove(); }, 400); });
  }, 4500);

  // charts (Chart.js loaded lazily only when a page has chart data)
  var dataEl = document.getElementById('chart-data');
  if (!dataEl) return;
  var data = JSON.parse(dataEl.textContent);
  var s = document.createElement('script');
  s.src = 'https://cdn.jsdelivr.net/npm/chart.js@4.4.3/dist/chart.umd.min.js';
  s.onload = draw;
  document.head.appendChild(s);

  var charts = [];
  function css(v) { return getComputedStyle(root).getPropertyValue(v).trim(); }
  function draw() {
    charts.forEach(function (c) { c.destroy(); }); charts = [];
    var grid = css('--line'), text = css('--muted');
    Chart.defaults.color = text; Chart.defaults.font.family = 'Inter, system-ui, sans-serif';
    var base = { responsive: true, maintainAspectRatio: false, plugins: { legend: { labels: { usePointStyle: true, boxWidth: 7 } } } };
    var axes = { y: { beginAtZero: true, grid: { color: grid } }, x: { grid: { display: false } } };
    var labels = data.months.map(function (m) { return m.label; });
    var money = { callbacks: { label: function (c) { return ' ' + c.dataset.label + ': Rs. ' + Math.round(c.parsed.y).toLocaleString(); } } };
    function make(id, cfg) { var el = document.getElementById(id); if (el) charts.push(new Chart(el, cfg)); }

    make('cashflow', { type: 'bar', data: { labels: labels, datasets: [
      { label: 'Income', data: data.months.map(function (m) { return m.income; }), backgroundColor: '#35c98a', borderRadius: 5 },
      { label: 'Expense', data: data.months.map(function (m) { return m.expense; }), backgroundColor: '#ef727c', borderRadius: 5 }] },
      options: Object.assign({}, base, { scales: axes, plugins: Object.assign({}, base.plugins, { tooltip: money }) }) });

    make('trend', { type: 'line', data: { labels: labels, datasets: [
      { label: 'Income', data: data.months.map(function (m) { return m.income; }), borderColor: '#35c98a', tension: .35, pointRadius: 3 },
      { label: 'Expense', data: data.months.map(function (m) { return m.expense; }), borderColor: '#ef727c', backgroundColor: 'rgba(239,114,124,.10)', fill: true, tension: .35, pointRadius: 3 }] },
      options: Object.assign({}, base, { scales: axes, plugins: Object.assign({}, base.plugins, { tooltip: money }) }) });

    var donut = { type: 'doughnut', data: { labels: data.categories.map(function (c) { return c.name; }),
      datasets: [{ data: data.categories.map(function (c) { return c.value; }), backgroundColor: data.categories.map(function (c) { return c.color; }), borderWidth: 0 }] },
      options: Object.assign({}, base, { cutout: '66%', plugins: { legend: { position: 'bottom', labels: { usePointStyle: true, boxWidth: 7 } } } }) };
    make('donut', donut); make('mix', JSON.parse(JSON.stringify(donut)));
  }
  window.addEventListener('themechange', function () { if (window.Chart) draw(); });
})();
