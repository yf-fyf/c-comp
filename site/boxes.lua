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
--   7. 通常回の文法差分を表示し、累積全文と優先順位表を開閉欄へまとめる
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
local grammar = nil

local function literal_html(value)
  local hex = pandoc.utils.stringify(value)
  return (hex:gsub("..", function(byte) return string.char(tonumber(byte, 16)) end))
end

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
  if meta["grammar-view"] then
    local value = meta["grammar-view"]
    grammar = {
      code = literal_html(value.code),
      legend = literal_html(value.legend),
      label = pandoc.utils.stringify(value.label),
      expanded = value.expanded,
      precedence = {},
    }
    for _, state in ipairs(value.precedence) do
      grammar.precedence[#grammar.precedence + 1] = pandoc.utils.stringify(state)
    end
    meta["grammar-view"] = nil
  end
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
  if lang and no_highlight[lang] then
    el.attributes["data-lang"] = lang
    el.classes = pandoc.List({})
  elseif lang then
    el.attributes["data-lang"] = lang
    local alias = lang_alias[lang]
    if alias then el.classes[1] = alias end
  end
  return el
end

local function scrollable_code(el)
  local pane = pandoc.Div({el}, {
    class = "code-scroll scroll-pane", tabindex = "0", role = "region",
    ["aria-label"] = "コード（左右にスクロールできます）",
  })
  return pandoc.Div({pane}, {class = "code-example scroll-frame"})
end

function Image(el)
  -- 原稿は figures/... の相対参照で書かれている。PDF 時代の綴りも一応拾う。
  local src = el.src:gsub("%.pdf$", ".svg")
  src = src:gsub("^figures/", figbase .. "/")
  el.src = src
  return el
end

function Table(el)
  -- Markdownの区切り線の長さから推定された割合を外し、内容から列幅を決める。
  -- セルの配置・結合・列の整列は保つ。
  local columns = {}
  for _, spec in ipairs(el.colspecs) do columns[#columns + 1] = {spec[1]} end
  el.colspecs = columns
  local pane = pandoc.Div({el}, {
    class = "table-scroll scroll-pane", tabindex = "0", role = "region",
    ["aria-label"] = "表（左右にスクロールできます）",
  })
  return pandoc.Div({pane}, {class = "table-example scroll-frame"})
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

local function grammar_section(content)
  local inner = pandoc.List({ content[1] })
  local started = false
  local table_done = false
  for i = 2, #content do
    local block = content[i]
    if not started and block.t == "CodeBlock" and block.classes:includes("ebnf") then
      inner:insert(pandoc.RawBlock("html", grammar.legend))
      local expanded = grammar.expanded and " open" or ""
      inner:insert(pandoc.RawBlock("html",
        '<details class="grammar-full"' .. expanded .. '><summary>' .. grammar.label .. '</summary>'))
      inner:insert(pandoc.RawBlock("html", grammar.code))
      started = true
    else
      if started and not table_done and #grammar.precedence > 0 then
        block = block:walk({ Table = function(tbl)
          local index = 0
          for _, body in ipairs(tbl.bodies) do
            for _, row in ipairs(body.body) do
              index = index + 1
              local state = grammar.precedence[index]
              if not state then error("Unexpected grammar precedence row") end
              row.classes:insert("grammar-" .. state)
              -- Markdown's table escape is not part of the operator itself.
              -- Confine this repair to operator cells in this one table.
              if row.cells[2] then
                row.cells[2].contents = row.cells[2].contents:walk({ Code = function(code)
                  code.text = code.text:gsub("\\|", "|")
                  return code
                end })
              end
              if state == "added" or state == "changed" then
                local label = state == "added" and "追加" or "変更"
                local cell = row.cells[1]
                local badge = pandoc.Span({pandoc.Str(label)}, {class="grammar-badge"})
                cell.contents[1].content:insert(pandoc.Space())
                cell.contents[1].content:insert(badge)
              end
            end
          end
          if index ~= #grammar.precedence then error("Missing grammar precedence row") end
          table_done = true
          return tbl
        end })
      end
      inner:insert(block)
    end
  end
  if not started then error("Grammar section has no EBNF block") end
  if #grammar.precedence > 0 and not table_done then error("Grammar section has no precedence table") end
  inner:insert(pandoc.RawBlock("html", "</details>"))
  return pandoc.Div(inner, {class="grammar-section", ["data-grammar-heading"]=content[1].identifier})
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
    elseif grammar and block.t == "Header" and block.level == 3
       and pandoc.utils.stringify(block.content) == "この回までの言語仕様（EBNF）" then
      doc.meta["grammar-anchor"] = pandoc.MetaString(block.identifier)
      local section = pandoc.List({block})
      i = i + 1
      while i <= n do
        local nxt = doc.blocks[i]
        if nxt.t == "Header" and nxt.level <= 3 then break end
        section:insert(nxt)
        i = i + 1
      end
      blocks:insert(grammar_section(section))
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
  { CodeBlock = scrollable_code },
}
