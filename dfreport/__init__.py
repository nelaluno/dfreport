"""dfreport — DataFrame → self-contained offline HTML report.

Quick start
-----------
>>> from dfreport import Report, ScatterChart
>>>
>>> Report(df, title="My Report") \\
...     .date_filter("Date") \\
...     .filters(["Category", "Status"]) \\
...     .chart(ScatterChart(x="x_col", y="y_col", title="Scatter")) \\
...     .summary_panel("x_col", "y_col", label="XY stats") \\
...     .table(categorical_threshold=10) \\
...     .save("report.html")
"""
from .report import Report, TOTAL_ROW_FLAG
from .charts import ScatterChart, LineChart, BarChart
from .columns import ColumnDefinition, detect_cols
from .plotly_bundle import get_plotly_js, inject_plotly

__all__ = ["Report", "TOTAL_ROW_FLAG", "ScatterChart", "LineChart", "BarChart",
           "ColumnDefinition", "detect_cols", "get_plotly_js", "inject_plotly"]
__version__ = "0.1.0"
