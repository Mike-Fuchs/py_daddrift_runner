from pathlib import Path

import numpy as np
import pytest

from py_daddrift_runner import DriftInput, read_input_files, write_input_files
from py_daddrift_runner.inputs import (
    APPLICATION_FILE, CONTROL_FILE, ENVIRONMENT_FILE,
)

FIXTURES = Path(__file__).parent / "fixtures"
EXAMPLES = ["single_field", "drift_curve"]


def _lines(path):
    with open(path, encoding="utf-8") as f:
        return f.read().splitlines()


@pytest.mark.parametrize("example", EXAMPLES)
class TestRoundTrip:
    """Reading a DAD-drift example and writing it back reproduces its files."""

    def test_control_identical(self, example, tmp_path):
        source = FIXTURES / example / "input"
        write_input_files(read_input_files(source), tmp_path)
        assert _lines(tmp_path / CONTROL_FILE) == _lines(source / CONTROL_FILE)

    @pytest.mark.parametrize("file_name", [APPLICATION_FILE, ENVIRONMENT_FILE])
    def test_table_values_identical(self, example, file_name, tmp_path):
        # names and values lines; the exe skips the units line by count. Values
        # are compared numerically: the examples hold hand-written notation
        # such as 0.70e+00, which is written back as 7.00e-01.
        source = FIXTURES / example / "input"
        write_input_files(read_input_files(source), tmp_path)
        written, original = _lines(tmp_path / file_name), _lines(source / file_name)
        assert written[0] == original[0]
        assert [float(v) for v in written[2].split()] == [float(v) for v in original[2].split()]

    def test_droplet_spectrum_identical(self, example, tmp_path):
        source = FIXTURES / example / "input"
        data = read_input_files(source)
        write_input_files(data, tmp_path)
        name = data.control["dsd_file_name"]
        assert _lines(tmp_path / name) == _lines(source / name)


def test_landscape_identical(tmp_path):
    source = FIXTURES / "single_field" / "input"
    data = read_input_files(source)
    write_input_files(data, tmp_path)
    reread = read_input_files(tmp_path)
    assert np.array_equal(reread.landscape[0], data.landscape[0])
    assert reread.landscape[1] == data.landscape[1]


class TestValidate:
    def _input(self):
        return read_input_files(FIXTURES / "drift_curve" / "input")

    def test_missing_value_raises(self):
        data = self._input()
        del data.application["boom_height"]
        with pytest.raises(ValueError, match="boom_height"):
            data.validate()

    def test_unknown_mode_raises(self):
        data = self._input()
        data.control["mode"] = 2
        with pytest.raises(ValueError, match="mode"):
            data.validate()

    def test_landscape_mode_requires_landscape(self):
        data = self._input()
        data.control["mode"] = 0
        with pytest.raises(ValueError, match="landscape"):
            data.validate()
