// site/lightbox.js
// 本文中の図をクリックで画面いっぱいに拡大表示する。
//
// fit は「表示領域いっぱいまで縦横比を保って拡大・縮小」（contain 相当）。
// 原寸が表示領域に収まらない大きい画像（横長の AST 図など）だけは
// fit ⇄ 原寸のトグルで、原寸時のスクロールはブラウザに任せる。
// 原寸が収まる小さい画像（大半の TikZ 図）は fit が既に最大表示なので、
// クリックは拡大ではなく「閉じる」に割り当てる。
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

  // padding は CSS 側（.lightbox img）と揃える。border-box にしてあるので
  // 「枠の寸法 = 画像の描画寸法 + padding*2」で扱える。
  function paddingPx() {
    var p = parseFloat(getComputedStyle(view).paddingLeft);
    return isNaN(p) ? 0 : p;
  }

  // 原寸と表示領域を比べて fit 時の寸法を決める。
  // 縮小が要る（＝原寸が表示領域を超える）画像にだけ .oversized を付け、
  // クリックの意味（原寸トグル／閉じる）とカーソルをそれで切り替える。
  function layout() {
    var nw = view.naturalWidth, nh = view.naturalHeight;
    if (!nw || !nh) return;
    var pad = paddingPx();
    var availW = dialog.clientWidth - pad * 2;
    var availH = dialog.clientHeight - pad * 2;
    if (availW <= 0 || availH <= 0) return;
    var scale = Math.min(availW / nw, availH / nh);
    view.classList.toggle('oversized', scale < 1);
    if (view.classList.contains('actual')) return;
    view.style.width = (nw * scale + pad * 2) + 'px';
    view.style.height = (nh * scale + pad * 2) + 'px';
  }

  function open(img) {
    view.classList.remove('actual');
    view.classList.remove('oversized');
    view.style.width = '';
    view.style.height = '';
    view.src = img.currentSrc || img.src;
    view.alt = img.alt;
    // ダイアログの裏で本文がスクロールするのを止める
    document.documentElement.style.overflow = 'hidden';
    dialog.showModal();
    // 表示領域の寸法は showModal 後でないと取れない。画像が読み込み済みなら
    // ここで確定し、まだなら下の load ハンドラが受ける。
    layout();
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
    view.style.width = '';
    view.style.height = '';
  });

  view.addEventListener('load', layout);

  // ウィンドウが変われば「縮小が要るか」も変わるので測り直す
  window.addEventListener('resize', function () {
    if (dialog.open) layout();
  });

  // 大きい画像は fit ⇄ 原寸のトグル。小さい画像は fit が既に最大表示なので
  // 閉じる（背景クリック・× ボタン・Esc と同じ経路）。
  // stopPropagation を忘れると上の「背景クリックで閉じる」に食われ、
  // 拡大しようとして閉じる事故になる。
  view.addEventListener('click', function (e) {
    e.stopPropagation();
    if (!view.classList.contains('oversized')) {
      dialog.close();
      return;
    }
    if (view.classList.toggle('actual')) {
      // 原寸表示。.actual の width/height:auto をインライン指定に負けさせない
      view.style.width = '';
      view.style.height = '';
    } else {
      layout();
    }
  });
})();
