from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from py_daddrift_runner import generate_dsd

# Reference output of rdmfr::generate_dsd 0.2.1 (R 4.5.0), one case per
# supported parameter combination.
REFERENCE = Path(__file__).parent / "fixtures" / "dsd"

CASES = {
    "c1_span": dict(vmd=200, rel_span=1.2),
    "c2_span_dv01": dict(vmd=200, rel_span=1.2, dv0_1=90),
    "c3_span_dv09": dict(vmd=200, rel_span=1.2, dv0_9=350),
    "c4_span_dsize": dict(vmd=200, rel_span=1.2, dsize=100, fract_dsize=0.15),
    "c5_dv01_dv09": dict(vmd=200, dv0_1=90, dv0_9=350),
    "c6_dv01_dv09_dsize": dict(vmd=200, dv0_1=90, dv0_9=350, dsize=100, fract_dsize=0.15),
    "c7_dv09_dsize": dict(vmd=200, dv0_9=350, dsize=100, fract_dsize=0.15),
    "c8_dv01_dsize": dict(vmd=200, dv0_1=90, dsize=100, fract_dsize=0.15),
    "c9_dsize": dict(vmd=200, dsize=100, fract_dsize=0.15),
    "c10_coarse": dict(vmd=450, rel_span=1.0),
}


@pytest.mark.parametrize("case", CASES)
def test_matches_rdmfr(case):
    expected = pd.read_csv(REFERENCE / f"{case}.csv")
    result = generate_dsd(**CASES[case])
    assert list(result.columns) == ["mean_size", "cum_fract"]
    np.testing.assert_allclose(result["mean_size"], expected["mean_size"], rtol=1e-12)
    np.testing.assert_allclose(result["cum_fract"], expected["cum_fract"], rtol=1e-6, atol=1e-9)


def test_ends_at_one():
    result = generate_dsd(vmd=200, rel_span=1.2)
    assert result["cum_fract"].iloc[-1] == pytest.approx(1.0)
    assert np.all(np.diff(result["cum_fract"]) > 0)


def test_unsupported_combination_raises():
    with pytest.raises(ValueError):
        generate_dsd(vmd=200)


def test_dsize_without_fraction_raises():
    with pytest.raises(ValueError):
        generate_dsd(vmd=200, rel_span=1.2, dsize=100)
