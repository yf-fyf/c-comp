// Native <details> stays operable without JavaScript. This script only reveals
// direct fragment targets and temporarily expands the full grammar for printing.
(function () {
  var sections = document.querySelectorAll('.grammar-section');
  if (!sections.length) return;

  function revealFragment() {
    if (!location.hash) return;
    var id;
    try { id = decodeURIComponent(location.hash.slice(1)); }
    catch (_) { return; }
    var target = document.getElementById(id);
    if (!target) return;
    var section = target.closest('.grammar-section');
    if (!section) return;
    var full = section.querySelector('.grammar-full');
    if (!full) return;
    if (target.closest('.grammar-full') || id === section.dataset.grammarHeading) {
      full.open = true;
      // Expansion may change the position computed for the browser's first jump.
      requestAnimationFrame(function () { target.scrollIntoView({behavior: 'instant'}); });
    }
  }
  window.addEventListener('hashchange', revealFragment);
  document.addEventListener('click', function (event) {
    var link = event.target.closest('a[href]');
    if (link && link.hash && link.hash === location.hash) revealFragment();
  });
  revealFragment();

  var printStates;
  window.addEventListener('beforeprint', function () {
    if (printStates) return;
    printStates = [];
    document.querySelectorAll('.grammar-full').forEach(function (full) {
      printStates.push([full, full.open]);
      full.open = true;
    });
  });
  window.addEventListener('afterprint', function () {
    (printStates || []).forEach(function (state) { state[0].open = state[1]; });
    printStates = null;
  });
})();
