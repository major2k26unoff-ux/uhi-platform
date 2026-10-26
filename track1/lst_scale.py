"""Colour range for the ground-temperature preview, chosen per area.

A fixed 25-45 C scale turned hot towns (Phalodi, Churu: 48-58 C) into one flat
yellow. Each area now uses its own 2nd to 98th percentile, rounded to whole
degrees and at least 6 degrees wide. The range is saved in meta.json as
lst_preview_c, so the website legend shows the same numbers.
"""
import math

import numpy as np

MIN_SPAN_C = 6


def lst_range(arr):
    """(low, high) in whole degrees C for one LST array with NaN as no data."""
    values = arr[np.isfinite(arr)]
    if values.size == 0:
        return 25, 45
    low, high = np.percentile(values, [2, 98])
    low, high = math.floor(low), math.ceil(high)
    if high - low < MIN_SPAN_C:
        mid = (low + high) / 2
        low, high = math.floor(mid - MIN_SPAN_C / 2), math.ceil(mid + MIN_SPAN_C / 2)
    return int(low), int(high)
