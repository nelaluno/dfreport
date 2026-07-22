"""Tests for column auto-detection."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
from dfreport.columns import detect_cols, ColumnDefinition


def make_df():
    return pd.DataFrame({
        "name":   ["Alice", "Bob", "Alice", "Carol"],
        "status": ["hit", "miss", "hit", "hit"],
        "value":  [1.2, 3.4, 5.6, 7.8],
        "count":  [1, 2, 3, 4],
        "notes":  ["a", "b", "c", "d"],
    })


def test_numeric_detected():
    cols = {c.key: c for c in detect_cols(make_df())}
    assert cols["value"].is_numeric
    assert cols["count"].is_numeric
    assert not cols["value"].is_categorical


def test_categorical_detected():
    cols = {c.key: c for c in detect_cols(make_df())}
    assert cols["name"].is_categorical
    assert cols["status"].is_categorical
    assert not cols["name"].is_numeric


def test_text_column():
    # with threshold=4, "notes" (4 unique) is NOT < 4 → plain text
    cols = {c.key: c for c in detect_cols(make_df(), categorical_threshold=4)}
    assert not cols["notes"].is_categorical
    assert not cols["notes"].is_numeric


def test_overrides():
    cols = {c.key: c for c in detect_cols(
        make_df(), overrides={"count": {"is_categorical": True, "is_numeric": False}}
    )}
    assert cols["count"].is_categorical
    assert not cols["count"].is_numeric


def test_exclude():
    cols = detect_cols(make_df(), exclude=["notes", "count"])
    keys = [c.key for c in cols]
    assert "notes" not in keys
    assert "count" not in keys
    assert "name" in keys


def test_to_dict_num():
    cd = ColumnDefinition(key="x", label="X value", is_numeric=True)
    assert cd.to_dict() == {"key": "x", "label": "X value", "is_numeric": True}


def test_to_dict_plain():
    cd = ColumnDefinition(key="y", label="Y")
    assert cd.to_dict() == {"key": "y", "label": "Y"}


def test_label_auto_format():
    from dfreport.columns import _auto_label
    # Basic capitalization and separator replacement
    assert _auto_label("my_col")     == "My Col"
    assert _auto_label("another-col") == "Another Col"
    # Unit suffix extraction
    assert _auto_label("bill_length_mm") == "Bill Length (mm)"
    assert _auto_label("body_mass_g")    == "Body Mass (g)"
    # camelCase splitting
    assert _auto_label("magType")        == "Mag Type"
    # detect_cols picks up the auto-label
    df = pd.DataFrame({"my_col": [1, 2], "bill_depth_mm": [3.0, 4.0]})
    cols = {c.key: c for c in detect_cols(df)}
    assert cols["my_col"].label      == "My Col"
    assert cols["bill_depth_mm"].label == "Bill Depth (mm)"
