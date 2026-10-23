# py_daddrift_runner

Run the [DAD-drift](https://github.com/Mike-Fuchs/DAD-drift) spray drift model from Python.
A Python counterpart of the R package [rdmfr](https://github.com/Mike-Fuchs/rdmfr).

`py_daddrift_runner` 0.1 is built for **DAD-drift v1.1**. It currently provides the
single-run caller (`run_drift_model_direct`); the full `run_drift_model` with
parameter variation and parallel runs is not implemented yet.

---

## Installation

```bash
pip install git+https://github.com/Mike-Fuchs/py_daddrift_runner.git
```

Requires Python ≥ 3.10 and Windows (DAD-drift is a Windows executable).

The executable is **not** part of this repository. During installation it is downloaded
from the DAD-drift `v1.1` release tag, checked against its SHA-256 and bundled into the
installed package. Installation therefore needs internet access once and fails if the
download fails or the hash does not match. After that, runs work offline, also in an
environment copied to another machine.

---

## Quick start

```python
from py_daddrift_runner import read_input_files, run_drift_model_direct

data = read_input_files("examples/single_field/input")   # or build a DriftInput
deposition, transform = run_drift_model_direct("my_run", data, keep_folder=False)
```

---

## Functions

### `DriftInput`

One input data set (cf. `rdmfr::drift_model_input`). Values are given in the units the
exe expects — nothing is converted.

| Field | Contents |
|-------|----------|
| `application` | dict, 14 values: `tractor_speed` [m/s], `boom_width` [m], `boom_height` [m], `nozzle_angle` [°], `application_pres` [kPa], `app_rate_mh` [m³/h], `app_rate_mha` [m³/ha], `app_rate_kgha` [kg/ha], `sol_concentration` [kg/m³], `AI_density` [kg/m³], `AI_molar_mass` [kg/mol], `AI_vapor_pressure` [Pa], `swath_number` [-], `field_length` [m] |
| `droplet_spectrum` | DataFrame, columns `mean_size` [m], `cum_fract` [-] (e.g. from `generate_dsd`) |
| `environment` | dict, 12 values: `temperature` [°C], `humidity` [-], `wind_speed` [m/s], `wind_height` [m], `wind_direction` [°], `ambient_pressure` [kPa], `sigma_horizontal` [m], `sigma_vertical` [m], `roughness_height` [m], `canopy_height` [m], `LAI` [m²/m²], `k_skew` [-] |
| `control` | dict: `mode` (0 = landscape, 1 = drift curve), `dep_height` [m], `max_dist` [m], `dsd_file_name` |
| `landscape` | `(array, transform)`: 1 = sprayed, nodata `-99`. Required for mode 0. |
| `landscape_file_name` | File name for the landscape grid (default `landscape.asc`). |

`validate()` raises `ValueError` for missing values or an inconsistent mode.

### `run_drift_model_direct`

```python
run_drift_model_direct(project_folder, input_data, executable_source=None,
                       save_file=None, keep_folder=True)
```

Runs DAD-drift once (cf. `rdmfr::run_drift_model_direct`). The run happens in
`project_folder/run` (replaced if it exists); the exe's console output is kept in
`run/debug.txt`. Parallel runs need separate project folders.

| Name | Default | Description |
|------|---------|-------------|
| `project_folder` | *required* | Folder of this run. |
| `input_data` | *required* | `DriftInput`. |
| `executable_source` | `None` | Path to another DAD-drift exe. `None` = bundled v1.1. |
| `save_file` | `None` | Name (without extension) to save the result in `project_folder`: `.npz` (mode 0: `deposition`, `transform`) or `.csv` (mode 1). |
| `keep_folder` | `True` | Keep `project_folder/run`. `False` deletes it after the run. |

**Returns** — mode 0: `(deposition, transform)`, deposition in kg/m²; mode 1: drift curve
as DataFrame. Raises `RuntimeError` with the exe's output if it fails or writes no output.

### `read_input_files` / `write_input_files`

`read_input_files(folder)` reads an existing DAD-drift input folder into a `DriftInput`
(cf. `rdmfr::read_input_files`); `write_input_files(input_data, folder)` writes one.
Single-field input only.

### `generate_dsd`

```python
generate_dsd(vmd, rel_span=None, dv0_1=None, dv0_9=None, dsize=None, fract_dsize=None,
             min_size=10, min_width=5, max_width=50) -> DataFrame
```

Droplet size distribution from nozzle characteristics, port of `rdmfr::generate_dsd`
(sizes in µm, output `mean_size` in m). Give `vmd` plus `rel_span`, `dv0_1`, `dv0_9`
and/or `dsize` + `fract_dsize`; unsupported combinations raise `ValueError`. Tested
against rdmfr 0.2.1 for every supported combination.

---

## License

py_daddrift_runner — Copyright (C) 2026 Mike Devin Fuchs

Licensed under the **GNU General Public License, version 3 or (at your option) any later
version**. See [LICENSE](LICENSE). DAD-drift itself is distributed under its own license
(GPL-2.0); the test fixtures in `tests/fixtures/single_field` and `tests/fixtures/drift_curve`
are examples from the DAD-drift repository.
