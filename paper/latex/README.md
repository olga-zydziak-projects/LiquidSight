# Building the preprint

Self-contained LaTeX source for **"Where Liquid Networks Help, Hurt, and Fail to
Train: A Pre-Registered Boundary Map"**.

## Files
- `main.tex` — the article (single-column `article`, `natbib`, `graphicx`).
- `references.bib` — bibliography (13 entries; one `[BIB:verify]` on
  `panerati2021gym` page range).
- Figures are pulled from `../figures/*.pdf` via `\graphicspath`.

## Compile

**Tectonic (recommended; engine = XeTeX, auto-fetches packages):**
```bash
tectonic -X compile main.tex
```

**pdfLaTeX (arXiv default):**
```bash
pdflatex main.tex && bibtex main && pdflatex main.tex && pdflatex main.tex
```

The preamble uses `iftex`: under pdfLaTeX it loads `inputenc`/`fontenc`; under
XeTeX/LuaTeX it loads `fontspec`. Unicode glyphs in the prose (Δ, τ, μ, ±, ≈, ≥,
→, ×, °, Ż) are mapped to portable macros via `newunicodechar`, so both engines
compile the same source.

The build was verified with tectonic 0.15.0 → `main.pdf`, 13 pages, zero
undefined citations/references. A copy of the built PDF is at
`../PREPRINT_v1.pdf`.
