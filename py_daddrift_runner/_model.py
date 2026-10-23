# SPDX-FileCopyrightText: 2026 Mike Devin Fuchs
# SPDX-License-Identifier: GPL-3.0-or-later

# The DAD-drift release this package is built for. setup.py downloads the
# executable from this tag at build time and refuses a file with another hash,
# so the package version fixes the model version.
DAD_DRIFT_VERSION = "v1.1"
EXE_NAME = "DAD-drift_v1.1.exe"
EXE_URL = (
    "https://raw.githubusercontent.com/Mike-Fuchs/DAD-drift/"
    f"{DAD_DRIFT_VERSION}/executable/{EXE_NAME}"
)
EXE_SHA256 = "0b2a9e11ca1a27dc28253a6ad713ee8612405e91dbeff48a87f83c1e62be21ed"
