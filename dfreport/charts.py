"""Chart configuration objects."""
from dataclasses import dataclass
from typing import Optional

from .columns import _auto_label


@dataclass
class LineChart:
    """A Plotly line chart for time series and trend data.

    Groups filtered rows by `x`, aggregates `y` (default: count), and renders a
    connected line — useful for events-per-day, totals-over-time, etc.

    Parameters
    ----------
    x     : DataFrame column to group by (x-axis); ISO date strings sort correctly
    y     : DataFrame column to aggregate; unused when agg="count"
    agg   : aggregation applied per x-group — "count" (default), "mean", "sum", "max"
    title : panel heading
    x_label, y_label : axis labels
    """

    x: str
    y: str = ""
    agg: str = "count"
    title: str = ""
    x_label: str = ""
    y_label: str = "Count"

    def to_dict(self, chart_id: str) -> dict:
        return {
            "id":     chart_id,
            "type":   "line",
            "title":  self.title,
            "xKey":   self.x,
            "yKey":   self.y,
            "agg":    self.agg,
            "xLabel": self.x_label,
            "yLabel": self.y_label,
        }


@dataclass
class BarChart:
    """A Plotly bar chart for categorical distributions.

    Groups filtered rows by `x`, aggregates `y` (default: count rows), and renders
    vertical bars — useful for species counts, event breakdowns, etc.

    Parameters
    ----------
    x     : DataFrame column to group by (x-axis categories)
    y     : DataFrame column to aggregate; unused when agg="count"
    agg   : aggregation — "count" (default), "mean", "sum", "max"
    title : panel heading
    x_label, y_label : axis labels
    """

    x: str
    y: str = ""
    agg: str = "count"
    title: str = ""
    x_label: str = ""
    y_label: str = "Count"
    color_key: Optional[str] = None  # Split bars by this column; one Plotly trace per value
    barmode: str = "group"           # "group" (side-by-side) or "stack"

    def to_dict(self, chart_id: str) -> dict:
        config = {
            "id":      chart_id,
            "type":    "bar",
            "title":   self.title,
            "xKey":    self.x,
            "yKey":    self.y,
            "agg":     self.agg,
            "xLabel":  self.x_label or _auto_label(self.x),
            "yLabel":  self.y_label,
            "barmode": self.barmode,
        }
        if self.color_key is not None:
            config["colorKey"] = self.color_key
        return config


@dataclass
class ScatterChart:
    """A Plotly scatter chart with average marker and origin→avg line.

    Parameters
    ----------
    x, y        : DataFrame column keys for the axes
    title       : panel heading
    x_label     : x-axis label (default "X")
    y_label     : y-axis label (default "Y")
    equal_axes  : whether to lock x/y scale ratio 1:1 (default True)
    annotations : list of Plotly annotation dicts (e.g. compass labels)
    hover_columns  : extra DataFrame columns to show in hover tooltip;
                  if None, auto-selects first 4 categorical columns
    """
    x: str
    y: str
    title: str = ""
    x_label: str = "X"
    y_label: str = "Y"
    equal_axes: bool = True
    annotations: Optional[list] = None
    hover_columns: Optional[list] = None
    color_key: Optional[str] = None  # Color points by this categorical column (one trace per value)
    show_avg: bool = False           # Show average marker + origin→avg line (opt-in, shot-dataset feature)

    def to_dict(self, chart_id: str) -> dict:
        config = {
            "id":          chart_id,
            "title":       self.title,
            "xKey":        self.x,
            "yKey":        self.y,
            "xLabel":      self.x_label,
            "yLabel":      self.y_label,
            "equalAxes":   self.equal_axes,
            "annotations": self.annotations or [],
        }
        if self.hover_columns is not None:
            config["hoverCols"] = self.hover_columns
        if self.color_key is not None:
            config["colorKey"] = self.color_key
        if self.show_avg:
            config["showAvg"] = True
        return config
