-- session-boxes.lua
-- fenced div を LaTeX の tcolorbox 環境に変換する。
--
-- 自動整形:
--   - 先頭の H1 をタイトルボックスに変換し、以降の見出しレベルを1段上げる
--   - "今日のゴール" H2 から次の同階層見出しまでを goalBox で囲む
--
-- ユーザー明示用:
--   ::: note       → noteBox
--   ::: important  → importantBox
--   ::: warning    → warningBox
--   ::: exercise   → exerciseBox

local box_map = {
  note = "noteBox",
  important = "importantBox",
  warning = "warningBox",
  exercise = "exerciseBox",
}

-- タイトルは RawBlock として LaTeX に渡すので、特殊文字を自前でエスケープする
-- (例: 見出しに && や % が入っていても壊れないようにする)
local function escape_latex(s)
  s = s:gsub("\\", "\\textbackslash{}")
  s = s:gsub("([&%%%$#_{}])", "\\%1")
  s = s:gsub("~", "\\textasciitilde{}")
  s = s:gsub("%^", "\\textasciicircum{}")
  return s
end

local function promote_header(block)
  if block.t == "Header" and block.level >= 2 then
    block.level = block.level - 1
  end
  return block
end

function Div(el)
  for class, env in pairs(box_map) do
    if el.classes:includes(class) then
      local blocks = pandoc.List({})
      blocks:insert(pandoc.RawBlock("latex", "\\begin{" .. env .. "}"))
      blocks:extend(el.content)
      blocks:insert(pandoc.RawBlock("latex", "\\end{" .. env .. "}"))
      return blocks
    end
  end
  return nil
end

function Pandoc(doc)
  local blocks = pandoc.List({})
  local i = 1
  local n = #doc.blocks

  -- 先頭 H1 をタイトルボックス化
  local first = doc.blocks[1]
  if first and first.t == "Header" and first.level == 1 then
    local title_text = escape_latex(pandoc.utils.stringify(first.content))
    blocks:insert(pandoc.RawBlock(
      "latex",
      "\\begin{SessionTitleBox}\n"
      .. "{\\LARGE\\bfseries " .. title_text .. "}\n"
      .. "\\end{SessionTitleBox}"
    ))
    i = 2
  end

  while i <= n do
    local b = doc.blocks[i]

    -- "今日のゴール" H2 を goalBox で囲む
    if b.t == "Header" and b.level == 2
       and pandoc.utils.stringify(b.content) == "今日のゴール" then
      blocks:insert(pandoc.RawBlock("latex", "\\begin{goalBox}"))

      i = i + 1
      while i <= n do
        local inner = doc.blocks[i]
        if inner.t == "Header" and inner.level <= 2 then
          break
        end
        blocks:insert(promote_header(inner))
        i = i + 1
      end

      blocks:insert(pandoc.RawBlock("latex", "\\end{goalBox}"))
    else
      blocks:insert(promote_header(b))
      i = i + 1
    end
  end

  doc.blocks = blocks
  return doc
end
