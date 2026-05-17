# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Repository Is

**自学是门手艺** (*The Craft of Self-Teaching*) is a Chinese-language book by 李笑来 (Li Xiaolai) that teaches self-learning skills using Python programming as the primary vehicle. The entire book is authored as Jupyter Notebooks (`.ipynb`) at the root level, with mirrored Markdown exports in `markdown/`.

The book is bilingual in spirit: all prose is Chinese, all code is Python 3.

## Working With the Notebooks

The primary way to read and edit this book is via **JupyterLab**. Install it with:

```bash
pip install jupyterlab
jupyter lab
```

Then open any `.ipynb` file from the JupyterLab interface. Code cells can be executed in-place with `Ctrl+Enter` (or `^+Enter` on Mac).

To run a single notebook from the command line (non-interactively):

```bash
jupyter nbconvert --to notebook --execute Part.1.E.1.entrance.ipynb
```

There are no build scripts, test runners, or linters — the "tests" in this repo are inline code cells within the notebooks themselves (especially the TDD chapter: `Part.2.D.7-tdd.ipynb`).

## Repository Structure

| Path | Purpose |
|------|---------|
| `*.ipynb` (root) | The book itself — one notebook per chapter/section |
| `markdown/` | Markdown exports of every notebook (auto-mirrored) |
| `images/` | All images referenced from notebooks and markdown |
| `from-readers/` | Reader-submitted self-teaching stories (collected via PR) |
| `my-notes/` | Space for the reader's personal notes |
| `mycode.py` | Example module from Part 2 (`is_prime`, `say_hi`) |
| `that.py` | ROT13 example from Part 2.D.8 (reveals the Zen of Python when run) |
| `words_alpha.txt` | Large English word list used in string/file exercises |
| `regex-target-text-sample.txt` | Sample text for the regex chapter |
| `hdi-china-1870-2015.txt`, `life-expectancy-china-1960-2016.txt` | Data files used in file-handling examples |

## Notebook Naming Convention

Files follow a strict prefix scheme that reflects the book's three-part structure:

- `00.` / `01.` / `02.` — cover, preface, proof-of-work
- `Part.1.*` — Part 1: self-teaching philosophy + Python basics
- `Part.2.*` — Part 2: deliberate practice + functions deep-dive
- `Part.3.*` — Part 3: advanced Python + self-teaching mastery
- `Q.` / `R.` / `S.` — epilogue chapters
- `T-appendix.*` — appendices (editor setup, git intro, Jupyter setup, symbols)

## Contribution Workflow

The book uses git history as a "proof of work" for readers. The intended workflow:

1. Fork the repo and clone locally
2. Create a `study` branch for personal reading/modification tracking
3. Commit changes to `study` after reading each chapter (`git commit -am 'my study result'`)
4. For corrections to the book itself: branch from `master`, make minimal targeted changes, submit a PR

Reader stories go in `from-readers/` as a separate branch + PR; they require community approval (upvotes) to merge into `master`.

## Kernelspec

All notebooks target **Python 3** (`kernelspec: python3`). There is no `requirements.txt`; the book intentionally uses only the Python standard library so readers can follow along without extra dependencies.
