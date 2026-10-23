# SPDX-FileCopyrightText: 2026 Mike Devin Fuchs
# SPDX-License-Identifier: GPL-3.0-or-later

"""The DAD-drift input data set and its file I/O.

The exe reads four text files from input/ (UTF-8) plus, in landscape mode, an
ESRI ASCII grid. It reads them list-directed (read(unit,*)), so only whitespace
between values matters; the 20-character columns are kept for readability.
Values are written in the units the exe expects at full precision; nothing is
converted here.
"""
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd
import rasterio

# (name, unit)
APPLICATION_COLUMNS = (
    ("tractor_speed", "[m/s]"),
    ("boom_width", "[m]"),
    ("boom_height", "[m]"),
    ("nozzle_angle", "[°]"),
    ("application_pres", "[kPa]"),
    ("app_rate_mh", "[m³/h]"),
    ("app_rate_mha", "[m³/ha]"),
    ("app_rate_kgha", "[kg/ha]"),
    ("sol_concentration", "[kg/m³]"),
    ("AI_density", "[kg/m³]"),
    ("AI_molar_mass", "[kg/mol]"),
    ("AI_vapor_pressure", "[Pa]"),
    ("swath_number", "[-]"),
    ("field_length", "[m]"),
)

ENVIRONMENT_COLUMNS = (
    ("temperature", "[°C]"),
    ("humidity", "[-]"),
    ("wind_speed", "[m/s]"),
    ("wind_height", "[m]"),
    ("wind_direction", "[°]"),
    ("ambient_pressure", "[kPa]"),
    ("sigma_horizontal", "[m]"),
    ("sigma_vertical", "[m]"),
    ("roughness_height", "[m]"),
    ("canopy_height", "[m]"),
    ("LAI", "m²/m²"),
    ("k_skew", "-"),
)

DROPLET_SPECTRUM_COLUMNS = (
    ("mean_size", "[m]"),
    ("cum_fract", "[-]"),
)

CONTROL_KEYS = ("mode", "dep_height", "max_dist", "dsd_file_name")

MODES = (0, 1)  # 0 = landscape, 1 = drift curve

APPLICATION_FILE = "application_input.txt"
ENVIRONMENT_FILE = "environment_input.txt"
CONTROL_FILE = "control_input.txt"


@dataclass
class DriftInput:
    """One DAD-drift input data set (cf. rdmfr::drift_model_input).

    Attributes:
        application (dict): The 14 values of APPLICATION_COLUMNS.
        droplet_spectrum (pandas.DataFrame): Columns mean_size [m] and cum_fract [-].
        environment (dict): The 12 values of ENVIRONMENT_COLUMNS.
        control (dict): mode (0 = landscape, 1 = drift curve), dep_height [m],
            max_dist [m], dsd_file_name.
        landscape (tuple): (array, affine transform) of the sprayed area,
            1 = sprayed, nodata -99. Required for mode 0, ignored for mode 1.
        landscape_file_name (str): File name the landscape is written to.
    """
    application: dict
    droplet_spectrum: pd.DataFrame
    environment: dict
    control: dict
    landscape: tuple = None
    landscape_file_name: str = field(default="landscape.asc")

    def validate(self):
        """Raise ValueError if a value is missing or the mode is inconsistent."""
        for label, given, columns in (
            ("application", self.application, [c[0] for c in APPLICATION_COLUMNS]),
            ("environment", self.environment, [c[0] for c in ENVIRONMENT_COLUMNS]),
            ("control", self.control, list(CONTROL_KEYS)),
            ("droplet_spectrum", self.droplet_spectrum, [c[0] for c in DROPLET_SPECTRUM_COLUMNS]),
        ):
            missing = [c for c in columns if c not in given]
            if missing:
                raise ValueError(f"{label} is missing {missing}.")
        if self.control["mode"] not in MODES:
            raise ValueError(f"mode must be one of {MODES}, got {self.control['mode']}.")
        if self.control["mode"] == 0 and self.landscape is None:
            raise ValueError("mode 0 (landscape) requires a landscape.")


# ---------------------------------------------------------------------------
# writing
# ---------------------------------------------------------------------------

def _fixed_row(values, width=20):
    """Right-align each value in a fixed-width column.

    Padding is counted in bytes, not characters: the reference files are
    written by Fortran, so a column holding a multi-byte character such as
    '°' or '³' carries one less space. At least one space is kept, so a value
    wider than the column stays separated from the previous one.
    """
    cells = []
    for value in values:
        text = f"{value}"
        cells.append(" " * max(width - len(text.encode("utf-8")), 1) + text)
    return "".join(cells)


def _fmt(value):
    """Shortest text that reads back as exactly the same float."""
    return repr(float(value))


def _write_lines(path, lines):
    with open(path, "w", encoding="utf-8", newline="\r\n") as f:
        f.write("\n".join(lines) + "\n")


def _write_table(path, columns, values):
    _write_lines(path, [
        _fixed_row([name for name, _ in columns]),
        _fixed_row([unit for _, unit in columns]),
        _fixed_row([_fmt(values[name]) for name, _ in columns]),
    ])


def _write_control(path, control, landscape_file_name):
    mode = int(control["mode"])
    field_count = 1 if mode == 0 else 0
    landscape_line = "{:<25}".format("landscape_file_name:")
    if mode == 0:
        landscape_line += "{:<25}".format(landscape_file_name)
    _write_lines(path, [
        _fixed_row(("mode", "dep_height", "max_dist", "field_count")),
        _fixed_row([
            f"{mode:d}",
            _fmt(control["dep_height"]),
            _fmt(control["max_dist"]),
            f"{field_count:d}",
        ]),
        "{:<25}{:<25}".format("dsd_file_name:", control["dsd_file_name"]),
        landscape_line,
    ])


def _write_droplet_spectrum(path, spectrum):
    lines = [
        _fixed_row([name for name, _ in DROPLET_SPECTRUM_COLUMNS]),
        _fixed_row([unit for _, unit in DROPLET_SPECTRUM_COLUMNS]),
    ]
    for row in spectrum[[c[0] for c in DROPLET_SPECTRUM_COLUMNS]].itertuples(index=False):
        lines.append(_fixed_row([_fmt(v) for v in row]))
    _write_lines(path, lines)


def _write_landscape(path, array, transform, nodata=-99):
    with rasterio.open(
        path, "w", driver="AAIGrid",
        height=array.shape[0], width=array.shape[1], count=1,
        dtype=array.dtype, transform=transform, nodata=nodata,
    ) as ds:
        ds.write(array, 1)


def write_input_files(input_data, folder):
    """Write the complete input folder for one DAD-drift run."""
    input_data.validate()
    folder = Path(folder)
    _write_table(folder / APPLICATION_FILE, APPLICATION_COLUMNS, input_data.application)
    _write_table(folder / ENVIRONMENT_FILE, ENVIRONMENT_COLUMNS, input_data.environment)
    _write_control(folder / CONTROL_FILE, input_data.control, input_data.landscape_file_name)
    _write_droplet_spectrum(folder / input_data.control["dsd_file_name"], input_data.droplet_spectrum)
    if input_data.control["mode"] == 0:
        array, transform = input_data.landscape
        _write_landscape(folder / input_data.landscape_file_name, np.asarray(array), transform)


# ---------------------------------------------------------------------------
# reading
# ---------------------------------------------------------------------------

def _read_lines(path):
    with open(path, encoding="utf-8") as f:
        return f.read().splitlines()


def _read_table(path, columns):
    values = _read_lines(path)[2].split()
    if len(values) != len(columns):
        raise ValueError(f"{path} has {len(values)} values, expected {len(columns)}.")
    return {name: float(v) for (name, _), v in zip(columns, values)}


def read_droplet_spectrum(path):
    """Read a DAD-drift droplet spectrum file (two header lines, then mean_size [m], cum_fract [-])."""
    rows = [line.split() for line in _read_lines(path)[2:] if line.strip()]
    return pd.DataFrame(
        np.array(rows, dtype=float),
        columns=[c[0] for c in DROPLET_SPECTRUM_COLUMNS],
    )


def read_input_files(input_folder):
    """Read an existing DAD-drift input folder into a DriftInput (cf. rdmfr::read_input_files)."""
    input_folder = Path(input_folder)
    control_lines = _read_lines(input_folder / CONTROL_FILE)
    mode, dep_height, max_dist, field_count = control_lines[1].split()
    dsd_file_name = control_lines[2].split()[1]
    landscape_files = control_lines[3].split()[1:]
    if int(field_count) > 1:
        raise NotImplementedError("Multi-field input (field_count > 1) is not supported.")

    spectrum = read_droplet_spectrum(input_folder / dsd_file_name)

    landscape = None
    landscape_file_name = "landscape.asc"
    if int(mode) == 0:
        landscape_file_name = landscape_files[0]
        with rasterio.open(input_folder / landscape_file_name) as ds:
            landscape = (ds.read(1), ds.transform)

    return DriftInput(
        application=_read_table(input_folder / APPLICATION_FILE, APPLICATION_COLUMNS),
        droplet_spectrum=spectrum,
        environment=_read_table(input_folder / ENVIRONMENT_FILE, ENVIRONMENT_COLUMNS),
        control={
            "mode": int(mode),
            "dep_height": float(dep_height),
            "max_dist": float(max_dist),
            "dsd_file_name": dsd_file_name,
        },
        landscape=landscape,
        landscape_file_name=landscape_file_name,
    )
