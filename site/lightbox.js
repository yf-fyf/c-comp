// site/lightbox.js
// 本文中の図をクリックで画面いっぱいに拡大表示する。
//
// 表示は fit（画面に収める）⇄ 原寸のトグル。原寸時のスクロールはブラウザに任せ、
// パン・ズームは自前で実装しない。ダイアログは素の <dialog> + showModal() なので、
// Esc・フォーカストラップ・背景の inert 化・閉じたあとのフォーカス復帰は
// ブラウザ側が面倒を見る。
//
// <dialog> を持たないブラウザでは何もしない（素の画像のまま読める）。

(function () {
  if (!window.HTMLDialogElement || !HTMLDialogElement.prototype.showModal) return;

  var targets = document.querySelectorAll('.content figure img');
  if (targets.length === 0) return;

  var dialog = document.createElement('dialog');
  dialog.className = 'lightbox';
  dialog.innerHTML =
    '<button class="lightbox-close" type="button" aria-label="閉じる">×</button>'
    + '<img alt="">';
  document.body.appendChild(dialog);
  var view = dialog.querySelector('img');

  for (var i = 0; i < targets.length; i++) {
    var img = targets[i];
    img.classList.add('zoomable');
    img.tabIndex = 0;
    img.setAttribute('role', 'button');
    img.setAttribute('aria-label', (img.alt || '図') + ' を拡大表示');
  }

  function open(img) {
    view.src = img.currentSrc || img.src;
    view.alt = img.alt;
    view.classList.remove('actual');
    // ダイアログの裏で本文がスクロールするのを止める
    document.documentElement.style.overflow = 'hidden';
    dialog.showModal();
  }

  document.addEventListener('click', function (e) {
    if (!e.target.closest) return;
    var img = e.target.closest('.content figure img.zoomable');
    if (img) open(img);
  });

  // role="button" を名乗る以上、Enter と Space でも開けるようにする
  document.addEventListener('keydown', function (e) {
    if (e.key !== 'Enter' && e.key !== ' ') return;
    var active = document.activeElement;
    var img = active && active.closest
      ? active.closest('.content figure img.zoomable') : null;
    if (!img) return;
    e.preventDefault();
    open(img);
  });

  // 背景（ダイアログ本体）と × ボタンで閉じる
  dialog.addEventListener('click', function (e) {
    if (e.target === dialog || (e.target.closest && e.target.closest('.lightbox-close'))) {
      dialog.close();
    }
  });

  dialog.addEventListener('close', function () {
    document.documentElement.style.overflow = '';
    view.removeAttribute('src');
  });

  // 画像本体は fit ⇄ 原寸のトグル。stopPropagation を忘れると上の
  // 「背景クリックで閉じる」に食われ、拡大しようとして閉じる事故になる。
  view.addEventListener('click', function (e) {
    e.stopPropagation();
    view.classList.toggle('actual');
  });
})();
