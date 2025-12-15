# Juicebox - Python TUI Web Browser

## Project Overview

Juicebox is a Python TUI (Terminal User Interface) web browser built with Textual. It's positioned as an alternative to Lynx for those who want a more modern terminal browsing experience.

**Core Stack:**
- **UI Framework:** Textual (with syntax highlighting support)
- **HTTP Client:** httpx
- **HTML Processing:** markdownify (converts HTML to markdown for terminal display)
- **Build System:** uv (fast Python package manager with uv_build backend)

## Python Version & Tooling

- **Python:** 3.14+ (strict minimum, not 3.13 or earlier)
- **Package Manager:** `uv` (NOT pip/poetry/conda)
  - Install dependencies: `uv sync`
  - Run code: `uv run python -m juicebox` or `uv run <script>`
  - Add packages: `uv add <package>`
  - Lock file: `uv.lock` is committed to version control

## Content Fetching Strategy

**Prefer native APIs over HTML scraping when available:**
- **WordPress sites:** WordPress REST API (`/wp-json/wp/v2/`) - posts, pages, media, categories
- **Ghost blogs:** Ghost Content API (`/ghost/api/v3/content/`) - posts, pages, tags, authors
- **Medium:** RSS feeds (`/@username/feed`) or official Medium API (requires API key)
- **Reddit:** JSON endpoints (append `.json` to any URL) - subreddits, posts, comments
- **GitHub:** REST API (`api.github.com`) and GraphQL - repos, issues, markdown rendering
- **Stack Overflow/Exchange:** Stack Exchange API - questions, answers, users
- **Hacker News:** Official Firebase API (`hacker-news.firebaseio.com/v0/`) - stories, comments
- **Wikipedia:** MediaWiki API (`/w/api.php`) - articles, search, summaries
- **YouTube:** Data API (requires key) or oEmbed for embeds
- **Twitter/X:** API (requires authentication) or nitter instances for public content
- **Mastodon:** REST API (`/api/v1/`) - timelines, toots, accounts (most instances are open)
- **Lemmy:** REST API (`/api/v3/`) - posts, communities, comments
- **RSS/Atom feeds:** Universal fallback for blogs and news sites

**Benefits:** Cleaner data, better performance, more reliable than HTML parsing

**Implementation approach:**
1. Check for API endpoints first
2. Look for `<link>` tags in HTML for API discovery (RSS, JSON Feed, etc.)
3. Fall back to HTML parsing only when no API is available or API fails

## Development Workflow

### Setup
```bash
uv sync  # Install all dependencies from uv.lock
```

### Running Tests
```bash
uv run pytest
```

### Code Quality (Pre-commit Hooks)
The project uses pre-commit with these tools:
- **Ruff:** Linter and formatter - runs `ruff check --fix` and `ruff format`
- **pyupgrade:** Enforces Python 3.11+ syntax (use `--py311-plus` despite 3.14 requirement)
- **add-trailing-comma:** Adds trailing commas for multi-line constructs
- Standard hooks: AST validation, TOML checks, EOF fixers, whitespace trimming

Run manually: `uv run pre-commit run --all-files`

### Textual Development Tools
```bash
uv run textual  # Access Textual dev tools
```

## Code Conventions

### Type Hints
- **Required:** All functions must have return type annotations (see [../src/juicebox/__init__.py](../src/juicebox/__init__.py))
- Example: `def hello() -> str:` not `def hello():`
- Include `py.typed` marker in packages for PEP 561 compliance

### Import Style
- Pre-commit enforces import organization via Ruff
- Trailing commas enforced on multi-line imports

### Test Naming
- Tests use pytest-style naming: `test_*.py` or `*_test.py` (checked by pre-commit)
- Place in project root or `tests/` directory (no tests exist yet)

## Project Structure

```
src/juicebox/
├── __init__.py      # Package entry point (currently placeholder)
└── py.typed         # PEP 561 type marker for mypy/pyright
```

**Current State:** Minimal skeleton - main browser implementation not yet created.

## Key Technical Patterns

### Textual TUI Architecture
- Use Textual's reactive programming model for UI updates
- Leverage Textual's built-in widgets (TextArea, RichLog, etc.)
- Enable syntax highlighting via `textual[syntax]` extra

### HTTP & Rendering Pipeline
1. **Fetch:** Check for native APIs first (WordPress REST API, etc.), fall back to httpx for HTML
2. **Convert:** Use markdownify to convert HTML → Markdown for terminal display (when scraping)
3. **Display:** Render markdown through Textual's Rich integration

## When Adding Dependencies

1. Use `uv add <package>` (updates both pyproject.toml and uv.lock)
2. For dev dependencies: `uv add --dev <package>`
3. Specify minimum versions with `>=` operator when needed
