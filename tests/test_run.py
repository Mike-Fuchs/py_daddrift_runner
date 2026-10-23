from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from py_daddrift_runner import read_input_files, run_drift_model_direct

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture(scope="module")
def landscape_run(tmp_path_factory):
    folder = tmp_path_factory.mktemp("single_field")
    data = read_input_files(FIXTURES / "single_field" / "input")
    result = run_drift_model_direct(folder, data, save_file="result")
    return folder, result


@pytest.fixture(scope="module")
def curve_run(tmp_path_factory):
    folder = tmp_path_factory.mktemp("drift_curve")
    data = read_input_files(FIXTURES / "drift_curve" / "input")
    result = run_drift_model_direct(folder, data, save_file="result")
    return folder, result


class TestLandscapeMode:
    def test_returns_deposition(self, landscape_run):
        _, (deposition, transform) = landscape_run
        assert deposition.ndim == 2
        assert np.nanmax(deposition) > 0
        assert transform.a > 0

    def test_saves_result(self, landscape_run):
        folder, (deposition, _) = landscape_run
        saved = np.load(folder / "result.npz")
        assert np.array_equal(saved["deposition"], deposition)

    def test_keeps_run_folder(self, landscape_run):
        folder, _ = landscape_run
        assert (folder / "run" / "output" / "landscape_drift.asc").exists()
        assert (folder / "run" / "debug.txt").exists()


class TestDriftCurveMode:
    def test_returns_curve(self, curve_run):
        _, curve = curve_run
        assert isinstance(curve, pd.DataFrame)
        assert len(curve) > 0

    def test_saves_result(self, curve_run):
        folder, curve = curve_run
        saved = pd.read_csv(folder / "result.csv")
        assert list(saved.columns) == list(curve.columns)
        assert len(saved) == len(curve)


def test_keep_folder_false_removes_run(tmp_path):
    data = read_input_files(FIXTURES / "drift_curve" / "input")
    run_drift_model_direct(tmp_path, data, keep_folder=False)
    assert not (tmp_path / "run").exists()


def test_missing_output_raises(tmp_path):
    # an "executable" that exits cleanly without writing any output
    fake = tmp_path / "fake.cmd"
    fake.write_text("@exit /b 0\n")
    data = read_input_files(FIXTURES / "drift_curve" / "input")
    with pytest.raises(RuntimeError, match="missing"):
        run_drift_model_direct(tmp_path / "project", data, executable_source=fake)
