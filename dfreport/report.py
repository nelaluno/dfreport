"""Report builder — DataFrame → self-contained offline HTML."""
import json
import logging
import re
from pathlib import Path

import pandas as pd

from .columns import ColumnDefinition, detect_cols, _auto_label
from .charts import ScatterChart, LineChart, BarChart
from .plotly_bundle import inject_plotly

_TEMPLATE = Path(__file__).parent / "templates" / "base.html"

# Stat-table rows with this column set to True are rendered bold as totals.
# Use this constant when building your stat_df:
#   stat_df["_total"] = False
#   stat_df.loc[total_row_index, TOTAL_ROW_FLAG] = True
TOTAL_ROW_FLAG = "_total"

logger = logging.getLogger(__name__)


class Report:
    """Fluent builder for an offline interactive HTML report.

    Usage
    -----
    Report(df, title="My Report") \\
        .date_filter("Date") \\
        .filters(["Category", "Status"]) \\
        .chart(ScatterChart(x="x_col", y="y_col", title="Scatter")) \\
        .summary_panel("x_col", "y_col", label="XY stats") \\
        .stat_table(stat_df, cols=[{"key": "Date", "label": "Date", "fmt": "str"}, …]) \\
        .table(categorical_threshold=10) \\
        .save("report.html")
    """

    def __init__(self, df: pd.DataFrame, title: str = "Report") -> None:
        self._df = df
        self._title = title
        self._charts: list[ScatterChart | LineChart | BarChart] = []
        self._agg_table: dict | None = None
        self._summary_panels: list[dict] = []
        self._filter_keys: list[str] = []
        self._date_key: str | None = None
        self._stat_df: pd.DataFrame | None = None
        self._stat_cols: list[dict] = []
        self._stat_title = "Statistics"
        self._data_title = "Data"
        self._categorical_threshold = 10
        self._col_overrides: dict = {}
        self._col_exclude: list[str] = []
        self._col_defs: list[ColumnDefinition] | None = None

    # ------------------------------------------------------------------
    # Public builder methods
    # ------------------------------------------------------------------

    def date_filter(self, key: str) -> "Report":
        """Enable a date-range picker in the header bar.

        Parameters
        ----------
        key :
            DataFrame column containing ISO date strings (``YYYY-MM-DD``).
            The picker filters every chart, the summary panel, and the data
            table to the selected range.
        """
        self._date_key = key
        return self

    def filters(self, keys: list[str]) -> "Report":
        """Add categorical dropdown filters to the header bar.

        Parameters
        ----------
        keys :
            DataFrame column names to expose as exact-match ``<select>``
            dropdowns.  Columns should have low cardinality (≤
            ``categorical_threshold`` unique values) to render usefully.
        """
        self._filter_keys = list(keys)
        return self

    def chart(self, chart_cfg: ScatterChart | LineChart | BarChart) -> "Report":
        """Append a chart panel to the report.

        Parameters
        ----------
        chart_cfg :
            A configured :class:`ScatterChart`, :class:`LineChart`, or
            :class:`BarChart` instance.  Call this method multiple times
            to add multiple side-by-side chart panels.
        """
        self._charts.append(chart_cfg)
        return self

    def summary_panel(self, x_key: str, y_key: str, label: str = "") -> "Report":
        """Add a numeric summary panel (mean, std dev, min/max) for two columns.

        Parameters
        ----------
        x_key :
            First column to summarise (shown on the left).
        y_key :
            Second column to summarise (shown on the right).
        label :
            Optional heading displayed above the panel.
        """
        self._summary_panels.append({"xKey": x_key, "yKey": y_key, "label": label})
        return self

    def stat_table(
        self,
        stat_df: pd.DataFrame,
        cols: list[dict],
        title: str = "Statistics",
    ) -> "Report":
        """Attach a pre-aggregated statistics table.

        Parameters
        ----------
        stat_df :
            One row per group (e.g. per date).  Rows where the
            ``TOTAL_ROW_FLAG`` column is ``True`` are rendered with bold
            TOTAL styling.
        cols :
            Column definitions:
            ``[{"key": …, "label": …, "fmt": "str" | "int" | "pct"}]``
        title :
            Section heading.
        """
        self._stat_df = stat_df
        self._stat_cols = list(cols)
        self._stat_title = title
        return self

    def agg_table(
        self,
        group_by: str,
        metrics: list[dict],
        title: str = "Summary",
        group_by_label: str = "",
    ) -> "Report":
        """Dynamic aggregate table that recomputes from the filtered dataset on every filter change.

        Unlike :meth:`stat_table` (which uses pre-aggregated data), this sends an
        aggregation spec to the browser and JS re-runs it over ``filtered`` on every
        filter change.  All header filters — date, island, sex, etc. — are therefore
        reflected immediately, even when they don't match the grouping column.

        Parameters
        ----------
        group_by :
            DataFrame column to group rows by (e.g. ``'species'``).
        metrics :
            List of metric specs::

                {
                  "key":   "bill_length_mm",  # source column (ignored when agg='count')
                  "label": "Bill Len (mm)",   # column header
                  "agg":   "mean",            # "count" | "mean" | "sum" | "max"
                  "fmt":   "str",             # "str" | "int" | "pct"  (optional)
                }

        title :
            Card heading.
        group_by_label :
            Column header for the group-by column.  Defaults to the column key.
        """
        self._agg_table = {
            "groupBy":      group_by,
            "groupByLabel": group_by_label or group_by,
            "metrics":      metrics,
        }
        self._stat_title = title
        return self

    def table(
        self,
        categorical_threshold: int = 10,
        col_overrides: dict | None = None,
        exclude: list[str] | None = None,
        title: str = "Data",
    ) -> "Report":
        """Configure the interactive data table.

        Parameters
        ----------
        categorical_threshold :
            Maximum unique values for a column to be treated as categorical
            (rendered as a dropdown filter).  Columns above this threshold
            get a text substring filter instead.
        col_overrides :
            Per-column overrides:
            ``{col_name: {"is_categorical": True, "label": "…"}}``
        exclude :
            Column names to hide from the table entirely.
        title :
            Card heading.
        """
        self._categorical_threshold = categorical_threshold
        self._col_overrides = col_overrides or {}
        self._col_exclude = exclude or []
        self._data_title = title
        return self

    def columns(self, col_defs: list[ColumnDefinition]) -> "Report":
        """Provide explicit column definitions instead of auto-detecting from dtypes.

        Parameters
        ----------
        col_defs :
            List of :class:`~dfreport.ColumnDefinition` objects.  When set,
            :meth:`table` auto-detection is skipped entirely.
        """
        self._col_defs = col_defs
        return self

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def save(self, output_path: str | Path, template_path: str | Path | None = None) -> Path:
        """Generate the HTML report and write it to disk.

        Parameters
        ----------
        output_path :
            Destination file.  The parent directory must already exist.
        template_path :
            Override the built-in HTML template.  Uses the bundled
            ``base.html`` when omitted.

        Returns
        -------
        Path
            Resolved path to the written file.
        """
        output_path = Path(output_path)
        resolved_template = Path(template_path) if template_path else _TEMPLATE

        col_defs = self._resolve_col_defs()
        replacements = self._build_replacements(col_defs)
        html = self._render_template(resolved_template, replacements)
        return self._write(html, output_path)

    # ------------------------------------------------------------------
    # Private helpers — each operates at one abstraction level
    # ------------------------------------------------------------------

    def _resolve_col_defs(self) -> list[ColumnDefinition]:
        """Return explicit col_defs if provided, otherwise auto-detect from the DataFrame."""
        return self._col_defs or detect_cols(
            self._df,
            categorical_threshold=self._categorical_threshold,
            overrides=self._col_overrides,
            exclude=self._col_exclude,
        )

    def _serialize_data(self, col_defs: list[ColumnDefinition]) -> str:
        """Serialise the main DataFrame to a JSON array, keeping only displayed columns."""
        keep_keys = [c.key for c in col_defs if c.key in self._df.columns]
        display_df = self._df[keep_keys].where(pd.notnull(self._df[keep_keys]), None)
        return json.dumps(display_df.to_dict(orient="records"), default=str)

    def _serialize_stat_table(self) -> tuple[str, str]:
        """Serialise the stat table to ``(rows_json, col_defs_json)``.

        Returns ``("[]", "[]")`` when no stat table has been configured.
        """
        if self._stat_df is None or not self._stat_cols:
            return "[]", "[]"

        stat_keys = [c["key"] for c in self._stat_cols if c["key"] in self._stat_df.columns]

        # Preserve TOTAL_ROW_FLAG column so the JS renderer can apply bold styling
        displayed_cols = [
            k for k in self._stat_df.columns if k in stat_keys or k == TOTAL_ROW_FLAG
        ]
        stat_display_df = self._stat_df[displayed_cols].where(pd.notnull(self._stat_df), None)

        return (
            json.dumps(stat_display_df.to_dict(orient="records"), default=str),
            json.dumps(self._stat_cols),
        )

    def _build_replacements(self, col_defs: list[ColumnDefinition]) -> dict[str, str]:
        """Build the full placeholder → value mapping for template substitution."""
        stat_json, stat_cols_json = self._serialize_stat_table()
        global_filters = [
            {"key": key, "label": _auto_label(key)} for key in self._filter_keys
        ]
        return {
            "__TITLE__":              self._title,
            "__STAT_TABLE_TITLE__":   self._stat_title,
            "__DATA_TABLE_TITLE__":   self._data_title,
            "__DATA_JSON__":          self._serialize_data(col_defs),
            "__STAT_JSON__":          stat_json,
            "__STAT_COLS_JSON__":     stat_cols_json,
            "__COL_DEFS_JSON__":      json.dumps([c.to_dict() for c in col_defs]),
            "__CHARTS_JSON__":        json.dumps([
                c.to_dict(f"dfreport-chart-{i}") for i, c in enumerate(self._charts)
            ]),
            "__SUMMARY_PANELS_JSON__": json.dumps(self._summary_panels),
            "__GLOBAL_FILTERS_JSON__": json.dumps(global_filters),
            "__DATE_KEY_JSON__":       json.dumps(self._date_key),
            "__DYN_STAT_JSON__":       json.dumps(self._agg_table) if self._agg_table else "null",
        }

    def _render_template(self, template_path: Path, replacements: dict[str, str]) -> str:
        """Read the template and substitute all placeholders in a single pass.

        Single-pass substitution via ``re.sub`` prevents injected placeholder
        strings in user data (e.g. a title of ``"__DATA_JSON__"``) from being
        re-substituted in a later iteration.
        """
        html = template_path.read_text(encoding="utf-8")
        pattern = re.compile("|".join(re.escape(k) for k in replacements))
        html = pattern.sub(lambda m: replacements[m.group(0)], html)
        return inject_plotly(html)

    def _write(self, html: str, output_path: Path) -> Path:
        """Write the rendered HTML to disk and log the file size."""
        output_path.write_text(html, encoding="utf-8")
        file_size_kb = output_path.stat().st_size / 1024
        logger.info("Report saved → %s  (%.0f KB)", output_path, file_size_kb)
        return output_path
