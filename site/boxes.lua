-- site/boxes.lua
-- 原稿の Markdown をサイト用の HTML へ寄せる pandoc フィルタ。
-- latex/session-boxes.lua（PDF 時代）の置き換え。
--
-- やること:
--   1. 先頭の H1 をページタイトルへ移す（本文からは外す）
--   2. "今日のゴール" H2 から次の同階層見出しまでを .goal で囲む
--   3. ::: note / important / warning / exercise を .adm へ変換し、見出し語を付ける
--   4. コードフェンスの言語別名を pandoc のハイライト名へ寄せる
--   5. 図の参照を .pdf から .svg へ、パスをページ深さに合わせて書き換える
--   6. .md へのリンクをサイト内 URL へ、サイトに無いものは GitHub へ逃がす
--
-- PDF 版と違い、見出しレベルの繰り上げはしない。HTML では H1 をそのまま
-- ページ見出しとして使うためである。

local box_title = {
  note      = "補足",
  important = "重要",
  warning   = "注意",
  exercise  = "作業",
}

-- pandoc が知らない綴りを、対応するハイライト名へ寄せる。
-- 原稿側の asm / lisp という綴りは読みやすさのため変えない。
local lang_alias = {
  asm  = "gnuassembler",  -- RV64 は GNU as 記法
  lisp = "commonlisp",    -- AST の S 式表示
}

-- ハイライトの対象にしないもの（pandoc に渡すと警告が出る）
local no_highlight = { text = true, plain = true }

local figbase  = "../../figures"
local blobbase = ""
local srcdir   = ""
local linkmap  = {}

--- "a/b/../c" のような相対パスを "a/c" に畳む
local function normalize(path)
  local parts = {}
  for part in path:gmatch("[^/]+") do
    if part == ".." then
      table.remove(parts)
    elseif part ~= "." then
      parts[#parts + 1] = part
    end
  end
  return table.concat(parts, "/")
end

function Meta(meta)
  if meta.figbase  then figbase  = pandoc.utils.stringify(meta.figbase)  end
  if meta.blobbase then blobbase = pandoc.utils.stringify(meta.blobbase) end
  if meta.srcdir   then srcdir   = pandoc.utils.stringify(meta.srcdir)   end
  if meta.linkmap then
    for key, value in pairs(meta.linkmap) do
      linkmap[key] = pandoc.utils.stringify(value)
    end
  end
  -- テンプレートへ渡す必要はないので落とす
  meta.linkmap = nil
  return meta
end

function Div(el)
  for class, title in pairs(box_title) do
    if el.classes:includes(class) then
      local head = pandoc.Div({ pandoc.Plain({ pandoc.Str(title) }) },
                              { class = "adm-title" })
      local body = pandoc.List({ head })
      body:extend(el.content)
      return pandoc.Div(body, { class = "adm adm-" .. class })
    end
  end
  return nil
end

function CodeBlock(el)
  local lang = el.classes[1]
  if not lang then return nil end
  if no_highlight[lang] then
    el.attributes["data-lang"] = lang
    el.classes = pandoc.List({})
    return el
  end
  el.attributes["data-lang"] = lang
  local alias = lang_alias[lang]
  if alias then
    el.classes[1] = alias
  end
  return el
end

function Image(el)
  local src = el.src
  if src:match("%.pdf$") then
    src = src:gsub("%.pdf$", ".svg")
  end
  -- 原稿は figures/... の相対参照で書かれている
  src = src:gsub("^figures/", figbase .. "/")
  el.src = src
  return el
end

function Table(el)
  -- 狭い画面では列が潰れて読めなくなる。横スクロールできる容器で包む。
  -- 包むだけでは table の width:100% が効いて縮むので、幅は CSS 側で与える。
  return pandoc.Div({ el }, { class = "table-scroll" })
end

function Link(el)
  local target, anchor = el.target:match("^([^#]*)(#?.*)$")
  if not target or not target:match("%.md$") then
    return nil
  end
  if target:match("^%a+://") then
    return nil
  end
  local resolved = normalize(srcdir .. "/" .. target)
  local site = linkmap[resolved]
  if site then
    el.target = site .. anchor
  elseif blobbase ~= "" then
    -- サイトに載せていない文書はリポジトリ側へ送る
    el.target = blobbase .. resolved .. anchor
  end
  return el
end

function Pandoc(doc)
  local blocks = pandoc.List({})

  -- 先頭 H1 をページタイトルへ移す
  local first = doc.blocks[1]
  local start = 1
  if first and first.t == "Header" and first.level == 1 then
    doc.meta.title = pandoc.MetaInlines(first.content)
    start = 2
  end

  local i = start
  local n = #doc.blocks
  while i <= n do
    local block = doc.blocks[i]

    if block.t == "Header" and block.level == 2
       and pandoc.utils.stringify(block.content) == "今日のゴール" then
      local inner = pandoc.List({ block })
      i = i + 1
      while i <= n do
        local nxt = doc.blocks[i]
        if nxt.t == "Header" and nxt.level <= 2 then break end
        inner:insert(nxt)
        i = i + 1
      end
      blocks:insert(pandoc.Div(inner, { class = "goal" }))
    else
      blocks:insert(block)
      i = i + 1
    end
  end

  doc.blocks = blocks
  return doc
end

-- Meta を先に走らせてから本体の要素を触る
return {
  { Meta = Meta },
  { Div = Div, CodeBlock = CodeBlock, Image = Image, Link = Link, Table = Table },
  { Pandoc = Pandoc },
}
