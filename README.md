# dfreport

Turn a pandas DataFrame into a self-contained offline HTML report with interactive filters and Plotly charts — one file, no server, no internet required.

A single `.html` file is a practical choice for sharing analytical results:

- **No setup for the recipient.** Anyone with a browser can open it — no Python, no dependencies, no accounts.
- **Works anywhere.** On a tablet in the field, on an air-gapped machine, over email, on a USB drive. No network required after the file is generated.
- **Nothing to host or maintain.** No server to keep running, no cloud storage to pay for, no API that can go down six months later and break the report.
- **Self-contained and archivable.** The file is the report. Data, charts, and interactivity are all bundled inline. It will open correctly years from now without any dependency changes.
- **Data stays local.** Nothing is uploaded. The report is generated from your data on your machine and shared as a file — suitable for environments where data cannot leave the network.

## Why not Plotly or Dash?

Plotly can produce multiple charts in a single offline HTML file and has built-in filter widgets (`updatemenus`, `sliders`) that work without a server. Those widgets are scoped to Plotly figures only — they can't drive a separate data table, numeric range inputs, or recomputed stat panels.

Dash solves that problem, but requires a running Python server. There is no "export to static HTML" mode. Opening a Dash app means running a process.

dfreport targets the gap between the two: fully offline, no server, everything in one `.html` file. A shared filter state connects Plotly charts, a live summary panel, and an interactive data table simultaneously:

- A **header filter bar** (date range + categorical dropdowns) that drives every chart, summary panel, and the data table at once
- **Plotly scatter charts** that re-render live as filters change
- **Summary stat panels** (mean, std dev, distance to origin) recomputed on each filter change
- A **paginated, sortable data table** with three filter types per column: exact-match dropdowns for categoricals, min/max range inputs for numerics, substring search for text
- A **pre-aggregated statistics table** with a sticky TOTAL row

Everything is injected into a single `.html` file at generation time — Plotly bundled inline, data embedded as JSON. The result opens in any browser with no dependencies.

## Examples

| Notebook | Live preview |
|---|---|
| [Palmer Penguins](examples/penguins/01_penguins.ipynb) | [penguins_report.html](https://htmlpreview.github.io/?https://github.com/nelaluno/dfreport/blob/main/examples/penguins/penguins_report.html) |
| [USGS Earthquakes](examples/earthquakes/02_earthquakes.ipynb) | [earthquakes_report.html](https://htmlpreview.github.io/?https://github.com/nelaluno/dfreport/blob/main/examples/earthquakes/earthquakes_report.html) |

## Inspiration

Column type auto-detection (categorical vs. numeric vs. text) is modelled on the approach used in [df2tables](https://github.com/pdolinic/df2tables). dfreport does not use df2tables code; the filter rendering is implemented in vanilla JS without DataTables.js.

## Install

```bash
pip install git+https://github.com/nelaluno/dfreport
```

Or in Colab:

```python
!pip install git+https://github.com/nelaluno/dfreport
```

## Quick start

```python
from dfreport import Report, ScatterChart

Report(df, title="My Report") \
    .date_filter("Date") \
    .filters(["Category", "Status"]) \
    .chart(ScatterChart(x="x_col", y="y_col", title="Scatter")) \
    .summary_panel("x_col", "y_col", label="XY stats") \
    .table(categorical_threshold=10) \
    .save("report.html")
```

## API

### `Report(df, title)`

Fluent builder. All methods return `self`.

| Method | Description |
|---|---|
| `.date_filter(key)` | Add a date-range filter in the header bar using `key` as the date column |
| `.filters(keys)` | Add categorical dropdowns to the header bar for the given column keys |
| `.chart(chart_cfg)` | Add a chart panel (`ScatterChart`, `LineChart`, or `BarChart`) |
| `.summary_panel(x_key, y_key, label)` | Add a live stats panel (mean, std dev, distance to origin) |
| `.agg_table(group_by, metrics, title, group_by_label)` | Dynamic aggregate table — JS re-runs aggregation over filtered rows on every filter change |
| `.stat_table(df, cols, title)` | Attach a pre-aggregated summary table (static; does not react to filters outside its grouping column) |
| `.table(categorical_threshold, col_overrides, exclude, title)` | Configure the interactive data table |
| `.columns(col_defs)` | Provide explicit `ColumnDefinition` objects instead of auto-detecting |
| `.save(output_path)` | Generate and write the HTML file |

### `ScatterChart(x, y, title, x_label, y_label, equal_axes, annotations, hover_columns, color_key, show_avg)`

Plotly scatter chart. Pass to `.chart()`.

| Parameter | Default | Description |
|---|---|---|
| `x`, `y` | — | DataFrame column keys for the axes |
| `title` | `""` | Panel heading |
| `x_label`, `y_label` | `"X"`, `"Y"` | Axis labels |
| `equal_axes` | `True` | Lock x/y scale ratio 1:1 |
| `annotations` | `None` | List of Plotly annotation dicts |
| `hover_columns` | `None` | Extra columns in hover tooltip; auto-selects first 4 categorical if omitted |
| `color_key` | `None` | Color points by this column (one trace per value) |
| `show_avg` | `False` | Show average marker and origin→avg line |

### `LineChart(x, y, agg, title, x_label, y_label)`

Plotly line chart for time series and trend data. Groups filtered rows by `x`, aggregates `y`.

| Parameter | Default | Description |
|---|---|---|
| `x` | — | Column to group by (x-axis); ISO date strings sort correctly |
| `y` | `""` | Column to aggregate; unused when `agg="count"` |
| `agg` | `"count"` | Aggregation: `"count"`, `"mean"`, `"sum"`, `"max"` |
| `title` | `""` | Panel heading |
| `x_label`, `y_label` | `""`, `"Count"` | Axis labels |

### `BarChart(x, y, agg, title, x_label, y_label, color_key, barmode)`

Plotly bar chart for categorical distributions.

| Parameter | Default | Description |
|---|---|---|
| `x` | — | Column to group by (x-axis categories) |
| `y` | `""` | Column to aggregate; unused when `agg="count"` |
| `agg` | `"count"` | Aggregation: `"count"`, `"mean"`, `"sum"`, `"max"` |
| `title` | `""` | Panel heading |
| `x_label`, `y_label` | auto | Axis labels (`x_label` defaults to auto-formatted column name) |
| `color_key` | `None` | Split bars by this column; one trace per value |
| `barmode` | `"group"` | `"group"` (side-by-side) or `"stack"` |

### `ColumnDefinition(key, label, is_categorical, is_numeric)`

Column metadata for the filter engine. Auto-detected by `detect_cols()`, or supply manually via `.columns()`.

### `detect_cols(df, categorical_threshold, overrides, exclude)`

Auto-detect column types from DataFrame dtypes. Returns a list of `ColumnDefinition` objects.

## Column type detection

| Condition | Filter rendered |
|---|---|
| Numeric dtype (int / float) | Min / max range inputs |
| Non-numeric, unique values < `categorical_threshold` | Exact-match dropdown |
| Everything else | Substring text search |

Override detection per column:

```python
.table(col_overrides={
    "status": {"is_categorical": True, "label": "Status"},
    "score":  {"is_numeric": True},
})
```

## Running tests

```bash
pip install pytest numpy
pytest tests/
```
