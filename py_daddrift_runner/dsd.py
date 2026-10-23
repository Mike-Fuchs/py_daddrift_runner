# SPDX-FileCopyrightText: 2026 Mike Devin Fuchs
# SPDX-License-Identifier: GPL-3.0-or-later

"""Droplet size distribution from nozzle characteristics (port of rdmfr::generate_dsd)."""
import numpy as np
import pandas as pd
from scipy.optimize import curve_fit
from scipy.stats import norm

FRACT_MIN = 0.001
PRED_STEP = 0.5  # µm, resolution of the fitted cumulative curve


def _seq(start, stop, step):
    # R's seq(start, stop, by = step), including its 1e-10 tolerance
    n = int(np.floor((stop - start) / step + 1e-10)) + 1
    return start + step * np.arange(n)


def generate_dsd(vmd, rel_span=None, dv0_1=None, dv0_9=None, dsize=None, fract_dsize=None,
                 min_size=10, min_width=5, max_width=50):
    """
    Generate a droplet size distribution for DAD-drift.

    A curve log10(F) + 3 = 3 * (1 - exp(-(a * d)^b)) is fitted through the given
    points of the cumulative volume fraction F, stretched to reach 1 at the
    maximum size and then split into droplet classes whose width grows linearly
    from min_width at 50 µm to max_width at 1000 µm.

    Args:
        vmd (float): Volume median diameter DV0.5 [µm].
        rel_span (float, optional): Relative span (DV0.9 - DV0.1) / VMD [-].
        dv0_1 (float, optional): DV0.1 [µm].
        dv0_9 (float, optional): DV0.9 [µm].
        dsize (float, optional): A further diameter [µm], given with fract_dsize.
        fract_dsize (float, optional): Cumulative volume fraction at dsize [-].
        min_size (float): Lower bound of the smallest droplet [µm].
        min_width (float): Class width at 50 µm, also the rounding step [µm].
        max_width (float): Class width at 1000 µm [µm].

    Returns:
        pandas.DataFrame: Columns mean_size [m] and cum_fract [-], as used by
        DriftInput.droplet_spectrum.

    Raises:
        ValueError: If the given combination of parameters is not supported.
    """
    s = rel_span is not None
    a = dv0_1 is not None
    b = dv0_9 is not None
    if (dsize is None) != (fract_dsize is None):
        raise ValueError("dsize and fract_dsize must be given together.")
    d = dsize is not None

    z_01 = norm.ppf(0.1)
    z_09 = norm.ppf(0.9)
    sd_low = sd_up = None

    # points (cum_fract, size) of the cumulative curve
    points = [(0.5, vmd)]
    if d:
        points.append((fract_dsize, dsize))
    if a:
        points.append((0.1, dv0_1))
    if b:
        points.append((0.9, dv0_9))

    if s and not a and not b and not d:
        dv01 = vmd - (rel_span * vmd) / 2
        dv09 = vmd + (rel_span * vmd) / 2
        points += [(0.1, dv01), (0.9, dv09)]
        sd_low = (dv01 - vmd) / z_01
    elif s and a and not b and not d:
        dv09 = dv0_1 + rel_span * vmd
        points.append((0.9, dv09))
        sd_low = (dv0_1 - vmd) / z_01
        sd_up = (dv09 - vmd) / z_09
    elif s and not a and b and not d:
        dv01 = dv0_9 - rel_span * vmd
        points.append((0.1, dv01))
        sd_low = (dv01 - vmd) / z_01
        sd_up = (dv0_9 - vmd) / z_09
    elif s and not a and not b and d:
        sd_low = (dsize - vmd) / norm.ppf(fract_dsize)
        dv01 = vmd + z_01 * sd_low
        dv09 = dv01 + rel_span * vmd
        points += [(0.1, dv01), (0.9, dv09)]
        sd_up = (dv09 - vmd) / z_09
    elif not s and a and b:
        # with or without dsize
        sd_low = (dv0_1 - vmd) / z_01
        sd_up = (dv0_9 - vmd) / z_09
    elif not s and not a and b and d:
        sd_low = (dsize - vmd) / norm.ppf(fract_dsize)
        dv01 = vmd + z_01 * sd_low
        points.append((0.1, dv01))
        sd_up = (dv0_9 - vmd) / z_09
    elif not s and a and not b and d:
        sd_low1 = (dsize - vmd) / norm.ppf(fract_dsize)
        sd_low2 = (dv0_1 - vmd) / z_01
        sd_low = (sd_low1 + sd_low2) / 2
        sd_up = sd_low
        dv09 = vmd + z_09 * sd_up
        points.append((0.9, dv09))
    elif not s and not a and not b and d:
        sd_low = (dsize - vmd) / norm.ppf(fract_dsize)
        sd_up = sd_low
        dv01 = vmd + z_01 * sd_low
        dv09 = vmd + z_09 * sd_up
        points += [(0.1, dv01), (0.9, dv09)]
    else:
        raise ValueError(
            "Unsupported parameter combination; give vmd with rel_span, dv0_1, dv0_9 "
            "and/or dsize + fract_dsize (see rdmfr::generate_dsd)."
        )

    if sd_up is None:
        sd_up = sd_low
    if sd_low is None:
        sd_low = sd_up

    # size range
    dv_max = vmd + norm.ppf(0.9999) * sd_up
    points.append((1.0, dv_max))
    dv_min = max(vmd + norm.ppf(FRACT_MIN) * sd_low, min_size)
    points.append((FRACT_MIN, dv_min))

    # fit, sizes shifted by dv_min and log10 fractions by 3
    cum_fract, size = np.array(points, dtype=float).T
    offset = abs(np.log10(FRACT_MIN))
    x = size - dv_min
    y = np.log10(cum_fract) + offset

    def model(x, a, b):
        # trial steps of the fit may leave the valid range (a < 0); they are rejected
        with np.errstate(invalid="ignore", divide="ignore"):
            return offset * (1 - np.exp(-(a * x) ** b))

    (fit_a, fit_b), _ = curve_fit(model, x, y, p0=(0.03, 0.8), method="lm")

    pred_size = _seq(dv_min, dv_max, PRED_STEP)
    pred_cum = 10 ** (model(pred_size - dv_min, fit_a, fit_b) - offset)

    # stretch linearly so the curve reaches 1 at dv_max
    pred_cum += (pred_size - dv_min) / (dv_max - dv_min) * (1 - pred_cum.max())

    # droplet classes, width linear between (50 µm, min_width) and (1000 µm, max_width)
    def class_width(size):
        width = min_width + (size - 50) * (max_width - min_width) / (1000 - 50)
        return max(np.round(width / min_width) * min_width, min_width)

    lower = [dv_min]
    upper = [dv_min + class_width(dv_min)]
    for _ in range(1, 100):
        lower.append(upper[-1])
        upper.append(lower[-1] + class_width(lower[-1]))
        if upper[-1] >= dv_max:
            break
    lower = np.array(lower)
    upper = np.array(upper)

    def cum_at(sizes):
        # class edges lie on the PRED_STEP grid starting at dv_min
        index = np.round((sizes - dv_min) / PRED_STEP).astype(int)
        return pred_cum[index]

    lower_fract = np.concatenate([[0.0], cum_at(lower[1:])])
    upper_fract = np.concatenate([cum_at(upper[:-1]), [1.0]])
    fract = upper_fract - lower_fract

    return pd.DataFrame({
        "mean_size": (lower + upper) / 2 * 1e-6,
        "cum_fract": np.cumsum(fract),
    })
