# SPDX-FileCopyrightText: 2026 Mike Devin Fuchs
# SPDX-License-Identifier: GPL-3.0-or-later

"""Build hook: bundle the DAD-drift executable into the package.

The exe is not part of the repository. It is downloaded from the DAD-drift
release tag defined in py_daddrift_runner/_model.py, checked against its
SHA-256 and placed in py_daddrift_runner/bin/, from where it is packaged.
Without internet access or with a wrong hash the build fails.
"""
import hashlib
import urllib.request
from pathlib import Path

from setuptools import setup
from setuptools.command.build_py import build_py

HERE = Path(__file__).parent
MODEL = {}
exec((HERE / "py_daddrift_runner" / "_model.py").read_text(encoding="utf-8"), MODEL)


def _sha256(data):
    return hashlib.sha256(data).hexdigest()


def fetch_exe():
    target = HERE / "py_daddrift_runner" / "bin" / MODEL["EXE_NAME"]
    if target.exists() and _sha256(target.read_bytes()) == MODEL["EXE_SHA256"]:
        return
    try:
        with urllib.request.urlopen(MODEL["EXE_URL"], timeout=60) as response:
            data = response.read()
    except OSError as err:
        raise RuntimeError(
            f"Could not download DAD-drift {MODEL['DAD_DRIFT_VERSION']} from "
            f"{MODEL['EXE_URL']}: {err}"
        ) from err
    digest = _sha256(data)
    if digest != MODEL["EXE_SHA256"]:
        raise RuntimeError(
            f"Downloaded {MODEL['EXE_NAME']} has SHA-256 {digest}, "
            f"expected {MODEL['EXE_SHA256']}."
        )
    target.parent.mkdir(exist_ok=True)
    target.write_bytes(data)


class BuildPyWithExe(build_py):
    def run(self):
        fetch_exe()
        super().run()


setup(cmdclass={"build_py": BuildPyWithExe})
