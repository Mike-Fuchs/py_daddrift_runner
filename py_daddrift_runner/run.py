# SPDX-FileCopyrightText: 2026 Mike Devin Fuchs
# SPDX-License-Identifier: GPL-3.0-or-later

import shutil
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd
import rasterio

from py_daddrift_runner._model import EXE_NAME
from py_daddrift_runner.inputs import write_input_files

LANDSCAPE_OUTPUT = "landscape_drift.asc"
DRIFT_CURVE_OUTPUT = "drift_curve_output.txt"
LOG_FILE = "debug.txt"


def bundled_exe():
    """Path of the DAD-drift executable bundled at build time."""
    exe = Path(__file__).parent / "bin" / EXE_NAME
    if not exe.exists():
        raise FileNotFoundError(
            f"Bundled DAD-drift executable not found at {exe}; reinstall py_daddrift_runner."
        )
    return exe


def _read_drift_curve(path):
    # line 1 = column names, line 2 = units, data from line 3 (cf. rdmfr::read_drift_curve)
    with open(path, encoding="utf-8") as f:
        names = f.readline().split()
    return pd.read_csv(path, sep=r"\s+", header=None, skiprows=2, names=names)


def _read_landscape_drift(path):
    with rasterio.open(path) as ds:
        return ds.read(1), ds.transform


def run_drift_model_direct(project_folder, input_data, executable_source=None,
                           save_file=None, keep_folder=True):
    """
    Run DAD-drift once for one input data set (cf. rdmfr::run_drift_model_direct).

    The run happens in project_folder/run: the input files are written to
    run/input, the exe is copied into run/ and executed there, because it
    resolves input/ and output/ relative to its working directory. An existing
    run/ folder is replaced. The exe's console output is kept in run/debug.txt.

    Args:
        project_folder: Folder of this run. Parallel runs need separate folders.
        input_data (DriftInput): The complete input data set.
        executable_source: Path to a DAD-drift executable. None = the bundled one.
        save_file (str, optional): Name (without extension) under which the result
            is saved in project_folder: .npz (mode 0, arrays deposition and
            transform) or .csv (mode 1).
        keep_folder (bool): Keep project_folder/run after the run. False deletes it.

    Returns:
        mode 0: (deposition, transform) — deposition array in kg/m² and its affine transform.
        mode 1: pandas.DataFrame — the drift curve.

    Raises:
        ValueError: If input_data is incomplete (see DriftInput.validate).
        RuntimeError: If the exe exits with an error or produces no output.
    """
    input_data.validate()
    mode = input_data.control["mode"]
    project_folder = Path(project_folder)
    run_dir = project_folder / "run"
    if run_dir.exists():
        shutil.rmtree(run_dir)
    (run_dir / "input").mkdir(parents=True)
    (run_dir / "output").mkdir()  # the exe does not create it

    write_input_files(input_data, run_dir / "input")

    exe_source = Path(executable_source) if executable_source is not None else bundled_exe()
    exe = run_dir / exe_source.name
    shutil.copy2(exe_source, exe)

    result = subprocess.run([str(exe)], cwd=run_dir, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    log = result.stdout.decode("utf-8", "replace")
    (run_dir / LOG_FILE).write_text(log, encoding="utf-8")

    output = run_dir / "output" / (LANDSCAPE_OUTPUT if mode == 0 else DRIFT_CURVE_OUTPUT)
    if result.returncode != 0 or not output.exists():
        raise RuntimeError(
            f"DAD-drift failed in {run_dir} (exit code {result.returncode}, "
            f"output {'found' if output.exists() else 'missing'}):\n{log}"
        )

    if mode == 0:
        deposition, transform = _read_landscape_drift(output)
        out = (deposition, transform)
        if save_file is not None:
            np.savez(project_folder / f"{save_file}.npz",
                     deposition=deposition, transform=np.array(tuple(transform)[:6]))
    else:
        out = _read_drift_curve(output)
        if save_file is not None:
            out.to_csv(project_folder / f"{save_file}.csv", index=False)

    if not keep_folder:
        shutil.rmtree(run_dir)
    return out
