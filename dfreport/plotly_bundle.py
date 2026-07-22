"""Inline Plotly.js bundling for offline-capable HTML reports."""
from pathlib import Path


_CDN_TAG = '<script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>'
_PLACEHOLDER = "<script>__PLOTLY_JS__</script>"


def get_plotly_js() -> str | None:
    """Return the content of plotly.min.js from the local plotly package.

    Returns None if plotly is not installed or the file cannot be found
    (caller should fall back to CDN).
    """
    try:
        import plotly as _plotly
        candidate = Path(_plotly.__file__).parent / "package_data" / "plotly.min.js"
        if candidate.exists():
            return candidate.read_text(encoding="utf-8")
    except Exception:
        pass
    return None


def inject_plotly(html: str) -> str:
    """Replace __PLOTLY_JS__ placeholder with inline bundle or CDN fallback."""
    js = get_plotly_js()
    if js:
        return html.replace(_PLACEHOLDER, f"<script>{js}</script>")
    # CDN fallback (requires internet)
    return html.replace(_PLACEHOLDER, _CDN_TAG)
