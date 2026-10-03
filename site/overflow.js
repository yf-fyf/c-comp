// Show a scroll hint and a keyboard stop only where content exceeds its pane.
// Static panes remain focusable when JavaScript is unavailable.
(function () {
  var panes = document.querySelectorAll('.scroll-pane, .grammar-pre');
  var entries = [];
  for (var i = 0; i < panes.length; i++) {
    var pane = panes[i];
    var frame = pane.closest('.scroll-frame');
    if (!frame) {
      frame = document.createElement('div');
      frame.className = 'scroll-frame';
      pane.parentNode.insertBefore(frame, pane);
      frame.appendChild(pane);
      pane.setAttribute('role', 'region');
      pane.setAttribute('aria-label', '文法（左右にスクロールできます）');
    }
    var hint = document.createElement('p');
    hint.className = 'scroll-hint';
    hint.textContent = '横に続きがあります（左右にスクロール・← →キー）';
    hint.hidden = true;
    frame.appendChild(hint);
    entries.push({pane: pane, hint: hint});
  }
  function update() {
    entries.forEach(function (entry) {
      var overflow = entry.pane.clientWidth > 0
        && entry.pane.scrollWidth > entry.pane.clientWidth + 1;
      entry.hint.hidden = !overflow;
      entry.pane.tabIndex = overflow ? 0 : -1;
    });
  }
  update();
  if ('ResizeObserver' in window) {
    var observer = new ResizeObserver(update);
    entries.forEach(function (entry) { observer.observe(entry.pane); });
  }
  window.addEventListener('resize', update);
  window.addEventListener('load', update);
  document.addEventListener('toggle', update, true);
  if (document.fonts) document.fonts.ready.then(update);
})();
