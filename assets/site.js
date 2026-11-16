(function () {
  var body = document.body, tip = document.getElementById('tip');
  function store(k, v) { try { if (v === undefined) return localStorage.getItem(k); localStorage.setItem(k, v); } catch (e) { return null; } }

  // reading toggles
  var tn = document.getElementById('t-notes'), tm = document.getElementById('t-mask');
  if (tn) {
    if (store('hocr-notes') === '0') { tn.checked = false; body.classList.remove('notes'); }
    tn.addEventListener('change', function () { body.classList.toggle('notes', tn.checked); store('hocr-notes', tn.checked ? '1' : '0'); });
  }
  if (tm) {
    if (store('hocr-mask') === '1') { tm.checked = true; body.classList.add('mask'); }
    tm.addEventListener('change', function () { body.classList.toggle('mask', tm.checked); store('hocr-mask', tm.checked ? '1' : '0'); });
  }

  // footnote buttons open single notes when notes are hidden
  document.querySelectorAll('.nref').forEach(function (b) {
    b.addEventListener('click', function () {
      var n = document.getElementById(b.getAttribute('aria-controls'));
      if (!n) return;
      if (body.classList.contains('notes')) { n.scrollIntoView({ block: 'nearest', behavior: 'smooth' }); return; }
      n.style.display = n.style.display === 'block' ? '' : 'block';
    });
  });

  // highlight filters
  var fc = document.getElementById('f-cat'), fp = document.getElementById('f-per'),
      tr = document.getElementById('transcript'), cnt = document.getElementById('hl-count');
  function apply() {
    var c = fc.value, p = fp.value, n = 0;
    tr.querySelectorAll('.u').forEach(function (u) {
      var hit = (c || p) &&
        (!c || (' ' + u.dataset.ana + ' ').indexOf(' ' + c + ' ') > -1) &&
        (!p || (' ' + u.dataset.persons + ' ').indexOf(' ' + p + ' ') > -1);
      u.classList.toggle('hl', !!hit); if (hit) n++;
    });
    tr.classList.toggle('filtering', !!(c || p));
    cnt.textContent = (c || p) ? n + ' matching call' + (n === 1 ? '' : 's') : '';
    var first = tr.querySelector('.u.hl'); if (first) first.scrollIntoView({ block: 'center', behavior: 'smooth' });
  }
  if (fc && fp) { fc.addEventListener('change', apply); fp.addEventListener('change', apply); }

  // tooltips for glossary terms, people, and chart marks
  function show(el, x, y) {
    var t = el.getAttribute('data-term'), g = el.getAttribute('data-gloss'), d = el.getAttribute('data-tip');
    if (!g && !d) return;
    tip.innerHTML = '';
    if (t) { var b = document.createElement('b'); b.textContent = t; tip.appendChild(b); }
    tip.appendChild(document.createTextNode(g || d));
    var w = 310, left = Math.min(x + 14, window.innerWidth - w - 10);
    tip.style.left = Math.max(8, left) + 'px'; tip.style.top = (y + 16) + 'px'; tip.style.opacity = 1;
  }
  function hide() { tip.style.opacity = 0; }
  document.querySelectorAll('[data-gloss],[data-tip]').forEach(function (el) {
    el.addEventListener('mousemove', function (e) { show(el, e.clientX, e.clientY); });
    el.addEventListener('mouseleave', hide);
    el.addEventListener('focus', function () { var r = el.getBoundingClientRect(); show(el, r.left, r.bottom - 8); });
    el.addEventListener('blur', hide);
  });
  window.addEventListener('scroll', hide, { passive: true });
})();
