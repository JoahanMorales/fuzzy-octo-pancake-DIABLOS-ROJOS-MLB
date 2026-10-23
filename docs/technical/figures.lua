-- pandoc filter for the LaTeX build: use figures/<name>.pdf (pgfplots, figures.py) instead of a reports/ PNG.
function Image(el)
  local name = el.src:match("([^/]+)%.png$")
  if name then
    local pdf = "figures/" .. name .. ".pdf"
    local f = io.open(pdf, "r")
    if f then f:close(); el.src = pdf; el.attributes.width = "92%" end
  end
  return el
end
