"""End-to-end tests for Report builder."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import json
import re
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

from dfreport import Report, ScatterChart, LineChart, BarChart, TOTAL_ROW_FLAG


def make_df(n=20):
    rng = np.random.default_rng(0)
    return pd.DataFrame({
        "date":     pd.date_range("2024-01-01", periods=n, freq="D").strftime("%Y-%m-%d"),
        "category": rng.choice(["A", "B", "C"], size=n),
        "status":   rng.choice(["hit", "miss"], size=n),
        "x":        rng.uniform(-1, 1, size=n).round(3),
        "y":        rng.uniform(-1, 1, size=n).round(3),
        "value":    rng.integers(1, 100, size=n).astype(float),
    })


def render(report):
    with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as f:
        path = Path(f.name)
    report.save(path)
    return path.read_text(encoding="utf-8")


def test_saves_html():
    html = render(Report(make_df(), title="Test"))
    assert "Test" in html
    assert "data-table" in html


def test_data_embedded():
    html = render(Report(make_df()))
    assert "category" in html


def test_col_defs_embedded():
    html = render(Report(make_df()).table())
    assert '"is_categorical"' in html


def test_chart_config_embedded():
    html = render(Report(make_df()).chart(ScatterChart(x="x", y="y", title="My Chart")))
    assert "My Chart" in html
    assert "xKey" in html


def test_global_filters_embedded():
    html = render(Report(make_df()).filters(["category", "status"]))
    assert "category" in html
    assert "status" in html


def test_date_filter_embedded():
    html = render(Report(make_df()).date_filter("date"))
    assert "f-date-start" in html


def test_stat_table_embedded():
    stat_df = pd.DataFrame([
        {"date": "2024-01-01", "total": 5, "rate": 0.6},
        {"date": "TOTAL", "total": 5, "rate": 0.6, TOTAL_ROW_FLAG: True},
    ])
    cols = [
        {"key": "date",  "label": "Date",  "fmt": "str"},
        {"key": "total", "label": "Total", "fmt": "int"},
        {"key": "rate",  "label": "Rate",  "fmt": "pct"},
    ]
    html = render(Report(make_df()).stat_table(stat_df, cols=cols, title="Daily Stats"))
    assert "Daily Stats" in html
    assert "stat-table-wrap" in html


def test_summary_panel_embedded():
    html = render(Report(make_df()).summary_panel("x", "y", label="XY summary"))
    assert "XY summary" in html
    assert "summary-container" in html


def test_no_charts_empty_array():
    html = render(Report(make_df()))
    assert re.search(r'const CHARTS\s*=\s*\[\s*\]', html)


def test_plotly_present():
    html = render(Report(make_df()).chart(ScatterChart(x="x", y="y")))
    assert "plotly" in html.lower()


def test_exclude_cols():
    html = render(Report(make_df()).table(exclude=["value"]))
    m = re.search(r'const DATA_COLS\s*=\s*(\[.*?\]);', html, re.DOTALL)
    assert m is not None
    col_defs = json.loads(m.group(1))
    keys = [c["key"] for c in col_defs]
    assert "value" not in keys


def test_col_override_label():
    html = render(Report(make_df()).table(col_overrides={"x": {"label": "X Axis", "is_numeric": True}}))
    assert "X Axis" in html


def test_no_unreplaced_placeholders():
    html = render(
        Report(make_df(), title="T")
        .date_filter("date")
        .filters(["category"])
        .chart(ScatterChart(x="x", y="y"))
        .summary_panel("x", "y")
    )
    remaining = re.findall(r'__[A-Z_]+__', html)
    assert remaining == [], f"Unreplaced placeholders: {remaining}"


def test_agg_table_embedded():
    html = render(
        Report(make_df())
        .agg_table(
            group_by='category',
            group_by_label='Category',
            metrics=[
                {'key': 'n',     'label': 'Count', 'agg': 'count', 'fmt': 'int'},
                {'key': 'value', 'label': 'Avg',   'agg': 'mean'},
            ],
            title='Category Stats',
        )
    )
    assert 'Category Stats' in html
    assert 'stat-section' in html
    m = re.search(r'const DYN_STAT\s*=\s*(\{.*?\});', html, re.DOTALL)
    assert m is not None, "DYN_STAT not found"
    spec = json.loads(m.group(1))
    assert spec['groupBy'] == 'category'
    assert spec['groupByLabel'] == 'Category'
    assert len(spec['metrics']) == 2
    assert spec['metrics'][0]['agg'] == 'count'


def test_agg_table_dyn_stat_null_without_call():
    html = render(Report(make_df()))
    assert 'const DYN_STAT' in html and 'null' in html


def test_line_chart_embedded():
    html = render(
        Report(make_df())
        .chart(LineChart(x="date", y="value", agg="sum", title="Daily Total", y_label="Total"))
    )
    assert "Daily Total" in html
    m = re.search(r'const CHARTS\s*=\s*(\[.*?\]);', html, re.DOTALL)
    charts = json.loads(m.group(1))
    assert len(charts) == 1
    assert charts[0]["type"] == "line"
    assert charts[0]["agg"] == "sum"
    assert charts[0]["xKey"] == "date"


def test_bar_chart_embedded():
    html = render(
        Report(make_df())
        .chart(BarChart(x="category", title="Count by Category", y_label="N"))
    )
    assert "Count by Category" in html
    m = re.search(r'const CHARTS\s*=\s*(\[.*?\]);', html, re.DOTALL)
    charts = json.loads(m.group(1))
    assert charts[0]["type"] == "bar"
    assert charts[0]["xKey"] == "category"
    assert charts[0]["yLabel"] == "N"


def test_mixed_chart_types():
    html = render(
        Report(make_df())
        .chart(ScatterChart(x="x", y="y", title="Scatter"))
        .chart(LineChart(x="date", title="Line"))
        .chart(BarChart(x="category", title="Bar"))
    )
    m = re.search(r'const CHARTS\s*=\s*(\[.*?\]);', html, re.DOTALL)
    charts = json.loads(m.group(1))
    assert len(charts) == 3
    types = [c.get("type") for c in charts]
    assert types[0] is None   # ScatterChart has no type field
    assert types[1] == "line"
    assert types[2] == "bar"


def test_multiple_charts():
    html = render(
        Report(make_df())
        .chart(ScatterChart(x="x", y="y", title="Chart A"))
        .chart(ScatterChart(x="y", y="x", title="Chart B"))
    )
    assert "Chart A" in html
    assert "Chart B" in html
    m = re.search(r'const CHARTS\s*=\s*(\[.*?\]);', html, re.DOTALL)
    charts = json.loads(m.group(1))
    assert len(charts) == 2
