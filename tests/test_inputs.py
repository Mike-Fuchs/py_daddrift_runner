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


def _numbers(line):
    return [float(v) for v in line.split()]


@pytest.mark.parametrize("example", EXAMPLES)
class TestRoundTrip:
    """Reading a DAD-drift example and writing it back reproduces its files.

    Values are compared numerically: the exe reads list-directed, and values
    are written at full precision, not in the examples' notation (e.g. 0.70e+00
    is written back as 0.7).
    """

    def test_control_identical(self, example, tmp_path):
        source = FIXTURES / example / "input"
        write_input_files(read_input_files(source), tmp_path)
        written, original = _lines(tmp_path / CONTROL_FILE), _lines(source / CONTROL_FILE)
        assert written[0] == original[0]
        assert _numbers(written[1]) == _numbers(original[1])
        assert [line.split() for line in written[2:]] == [line.split() for line in original[2:]]

    @pytest.mark.parametrize("file_name", [APPLICATION_FILE, ENVIRONMENT_FILE])
    def test_table_values_identical(self, example, file_name, tmp_path):
        # names and values lines; the exe skips the units line by count
        source = FIXTURES / example / "input"
        write_input_files(read_input_files(source), tmp_path)
        written, original = _lines(tmp_path / file_name), _lines(source / file_name)
        assert written[0] == original[0]
        assert _numbers(written[2]) == _numbers(original[2])

    def test_droplet_spectrum_identical(self, example, tmp_path):
        source = FIXTURES / example / "input"
        data = read_input_files(source)
        write_input_files(data, tmp_path)
        name = data.control["dsd_file_name"]
        written, original = _lines(tmp_path / name), _lines(source / name)
        assert written[0] == original[0]
        assert [_numbers(line) for line in written[2:]] == [_numbers(line) for line in original[2:]]


def test_values_written_at_full_precision(tmp_path):
    data = read_input_files(FIXTURES / "single_field" / "input")
    data.application["AI_molar_mass"] = 0.38136
    data.application["AI_vapor_pressure"] = 3.3e-10
    data.environment["canopy_height"] = 0.025
    data.control["dep_height"] = 0.0125
    data.control["max_dist"] = 150.5
    data.droplet_spectrum.loc[0, "mean_size"] = 5.678028123e-05
    write_input_files(data, tmp_path)
    reread = read_input_files(tmp_path)
    assert reread.application == data.application
    assert reread.environment == data.environment
    assert reread.control == data.control
    assert reread.droplet_spectrum.equals(data.droplet_spectrum)


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
