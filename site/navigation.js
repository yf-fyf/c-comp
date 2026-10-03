// CSS also provides an offset when JavaScript is unavailable. Measure the
// sticky header so changed fonts or viewport widths keep fragment targets clear.
(function () {
  var header = document.querySelector('.topbar');
  if (!header) return;
  function updateOffset() {
    document.documentElement.style.setProperty(
      '--anchor-offset', (header.getBoundingClientRect().height + 16) + 'px');
  }
  updateOffset();
  if ('ResizeObserver' in window) {
    new ResizeObserver(updateOffset).observe(header);
  } else {
    window.addEventListener('resize', updateOffset);
  }
})();
