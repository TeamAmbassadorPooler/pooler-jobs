/* Ambassador Personnel job list widget. Paste where the list should show:
   <div id="ambassador-jobs"></div>
   <script src="THIS-SITE/embed.js" defer></script>
   Optional on the div: data-state="GA" data-city="Savannah" data-limit="10" */
(function () {
  var s = document.currentScript, root = s.src.replace(/embed\.js.*$/, '');
  var box = document.getElementById('ambassador-jobs'); if (!box) { box = document.createElement('div'); s.parentNode.insertBefore(box, s); }
  function e(t) { return String(t == null ? '' : t).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); }
  fetch(root + 'jobs.json', { cache: 'no-cache' }).then(function (r) { return r.json(); }).then(function (d) {
    var st = (box.getAttribute('data-state') || '').toUpperCase(), ci = (box.getAttribute('data-city') || '').toLowerCase(), lim = parseInt(box.getAttribute('data-limit') || '0', 10);
    var jobs = d.jobs.filter(function (j) { return (!st || j.state === st) && (!ci || String(j.city).toLowerCase() === ci); });
    if (lim) jobs = jobs.slice(0, lim);
    box.innerHTML = jobs.length ? jobs.map(function (j) {
      var pay = j.payRange && j.payRange.length ? ' · $' + j.payRange.map(function (x) { return x.toFixed(2); }).join('–$') + '/hr' : '';
      return '<div style="border:1px solid #e1e5ec;border-radius:8px;padding:10px 12px;margin:8px 0;font-family:inherit"><a href="' + e(j.url) + '" style="font-weight:600;text-decoration:none">' + e(j.title) + '</a><div style="font-size:13px;opacity:.75">' + e(j.city + ', ' + j.state) + e(pay) + (j.shift ? ' · ' + e(j.shift) : '') + '</div></div>';
    }).join('') + '<a href="' + e(d.applyUrl) + '" style="display:inline-block;margin-top:6px">Apply online →</a>' : '<p>No open jobs right now.</p>';
  }).catch(function () { box.innerHTML = '<a href="' + e(root) + '">See open jobs</a>'; });
})();
