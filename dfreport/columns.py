"""ColumnDefinition type auto-detection for filter UI rendering."""
import re
from dataclasses import dataclass
from typing import Optional

import pandas as pd

# Column-name suffixes that represent measurement units — moved to parentheses in labels.
_UNIT_SUFFIXES = frozenset({"mm", "g", "kg", "km", "m", "cm", "s", "ms"})


def _auto_label(key: str) -> str:
    """Generate a human-readable label from a column key.

    Transforms applied in order:
    1. Split camelCase     — ``magType``         → ``mag Type``
    2. Replace ``_`` / ``-``  — ``bill_length_mm`` → ``bill length mm``
    3. Capitalize words    — ``bill length mm``  → ``Bill Length Mm``
    4. Parenthesize unit   — last word in ``_UNIT_SUFFIXES`` → ``Bill Length (mm)``
    """
    # 1. Insert a space before each uppercase letter that follows a lowercase letter
    name = re.sub(r"([a-z])([A-Z])", r"\1 \2", key)
    # 2. Normalise separators
    name = name.replace("_", " ").replace("-", " ")
    words = name.split()
    if not words:
        return key
    # 3 & 4. Capitalize; pull trailing unit into parens
    if words[-1].lower() in _UNIT_SUFFIXES:
        unit = words.pop().lower()
        return " ".join(w.capitalize() for w in words) + f" ({unit})"
    return " ".join(w.capitalize() for w in words)


@dataclass
class ColumnDefinition:
    key: str
    label: str
    is_categorical: bool = False  # True → <select> dropdown, exact-match filter
    is_numeric: bool = False      # True → min/max range inputs; False → text substring filter

    def to_dict(self) -> dict:
        """Serialize to a JSON-safe dict consumed by the JS filter engine."""
        d = {"key": self.key, "label": self.label}
        if self.is_categorical:
            d["is_categorical"] = True
        if self.is_numeric:
            d["is_numeric"] = True
        return d


def detect_cols(
    df: pd.DataFrame,
    categorical_threshold: int = 10,
    overrides: Optional[dict] = None,
    exclude: Optional[list] = None,
) -> list:
    """Auto-detect column types from DataFrame dtypes.

    Rules:
      - numeric dtype (int/uint/float)               → is_numeric=True
      - non-numeric + nunique < categorical_threshold → is_categorical=True
      - else                                          → plain text (substring search)

    Parameters
    ----------
    df                    : source DataFrame
    categorical_threshold : max unique values for a column to be treated as categorical (default 10)
    overrides             : {col_name: {"is_categorical": True/False, "is_numeric": True/False, "label": "…"}}
    exclude               : column names to omit from output
    """
    overrides = overrides or {}
    exclude = set(exclude or [])
    cols = []

    for col in df.columns:
        if col in exclude:
            continue

        is_numeric = df[col].dtype.kind in ("i", "u", "f")
        nunique = df[col].nunique()
        is_categorical = (not is_numeric) and (nunique < categorical_threshold)
        label = _auto_label(col)

        column = ColumnDefinition(key=col, label=label, is_categorical=is_categorical, is_numeric=is_numeric)

        # Apply user overrides
        col_override = overrides.get(col, {})
        for attr, val in col_override.items():
            setattr(column, attr, val)

        cols.append(column)

    return cols
