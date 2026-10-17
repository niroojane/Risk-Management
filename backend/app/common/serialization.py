"""Conversion of pandas / numpy objects to JSON-safe Python values"""
import datetime
import math
from typing import Any, Dict

import numpy as np
import pandas as pd


def to_json_value(value: Any) -> Any:
    """Convert a scalar to a JSON-safe value (NaN/inf -> None, dates -> ISO date)"""
    if value is None:
        return None
    if isinstance(value, (pd.Timestamp, datetime.datetime)):
        if pd.isna(value):
            return None
        if value.hour == value.minute == value.second == value.microsecond == 0:
            return value.strftime('%Y-%m-%d')
        return value.isoformat()
    if isinstance(value, datetime.date):
        return value.isoformat()
    if isinstance(value, (np.bool_, bool)):
        return bool(value)
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating, float)):
        value = float(value)
        return None if math.isnan(value) or math.isinf(value) else value
    if isinstance(value, complex) or isinstance(value, np.complexfloating):
        return to_json_value(np.real(value))
    if value is pd.NaT:
        return None
    return value


def series_to_dict(series: pd.Series) -> Dict[str, Any]:
    """{index label: value}"""
    return {str(to_json_value(k)): to_json_value(v) for k, v in series.items()}


def frame_to_dict(frame: pd.DataFrame) -> Dict[str, Dict[str, Any]]:
    """{row label: {column label: value}} -- same layout as the prices endpoint"""
    return {
        str(to_json_value(idx)): {str(col): to_json_value(val) for col, val in row.items()}
        for idx, row in frame.iterrows()
    }


def frame_to_split(frame: pd.DataFrame) -> Dict[str, Any]:
    """{'index': [...], 'columns': [...], 'data': [[row values]]} -- keeps row and column order"""
    return {
        'index': [str(to_json_value(i)) for i in frame.index],
        'columns': [str(c) for c in frame.columns],
        'data': [[to_json_value(v) for v in row] for row in frame.itertuples(index=False, name=None)],
    }


def to_payload(value: Any) -> Any:
    """Recursively convert analytics results (frames, series, dicts, lists, scalars) to JSON-safe values.

    DataFrames and Series use the split layout of `frame_to_split`.
    """
    if isinstance(value, pd.DataFrame):
        return frame_to_split(value)
    if isinstance(value, pd.Series):
        return frame_to_split(value.to_frame(value.name if value.name is not None else 'value'))
    if isinstance(value, dict):
        return {str(k): to_payload(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [to_payload(v) for v in value]
    if isinstance(value, np.ndarray):
        return [to_payload(v) for v in value.tolist()]
    return to_json_value(value)
