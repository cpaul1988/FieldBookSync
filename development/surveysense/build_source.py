"""Reconstruct reviewable SurveySense source from the verified v8.1.14 payload.

No installer is executed. The old native executable is removed; rebuild it from
installer/app_launcher.go before packaging a Windows application.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import shutil
import struct
import subprocess
import tempfile
import urllib.request
import zipfile
from pathlib import Path, PurePosixPath

BASELINE_URL = "https://github.com/cpaul1988/FieldBookSync/releases/download/v8.1.14/FieldBookSync_Setup_8.1.14.exe"
BASELINE_SHA256 = "6c5f59f70633acb2774fd93f9ccd8c7f40854cbcdc49b32848fd9f9455ab1456"
BASELINE_SIZE = 6605312


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None


def extract(data, destination):
    starts, ends, pos = [], [], 0
    while (pos := data.find(b"PK\x03\x04", pos)) >= 0:
        starts.append(pos)
        pos += 1
    pos = 0
    while (pos := data.find(b"PK\x05\x06", pos)) >= 0:
        ends.append(pos)
        pos += 1
    for start in starts:
        for eocd in reversed(ends):
            if eocd <= start or eocd + 22 > len(data):
                continue
            end = eocd + 22 + struct.unpack_from("<H", data, eocd + 20)[0]
            try:
                with zipfile.ZipFile(io.BytesIO(data[start:end])) as archive:
                    if not {"fieldbook_sync/app.py", "installer/setup_ui.ps1"}.issubset(archive.namelist()):
                        continue
                    if sum(item.file_size for item in archive.infolist()) > 200 * 1024 * 1024:
                        raise ValueError("Unexpectedly large baseline payload")
                    for item in archive.infolist():
                        p = PurePosixPath(item.filename)
                        if p.is_absolute() or ".." in p.parts or "\\" in item.filename or ":" in item.filename:
                            raise ValueError("Unsafe baseline archive path")
                    if archive.testzip() is not None:
                        raise ValueError("Baseline ZIP integrity check failed")
                    archive.extractall(destination)
                    return
            except zipfile.BadZipFile:
                continue
    raise ValueError("The verified installer does not contain the expected payload")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--installer", type=Path, help="Use an already downloaded, verified v8.1.14 installer")
    parser.add_argument("--out", type=Path, required=True, help="New output directory; existing paths are never overwritten")
    args = parser.parse_args()
    output = args.out.resolve()
    if output.exists():
        raise SystemExit(f"Output already exists: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    package = Path(__file__).resolve().parent
    manifest = json.loads((package / "source_hashes.json").read_text(encoding="utf-8"))
    with tempfile.TemporaryDirectory(prefix="surveysense-build-", dir=output.parent) as temp:
        temp = Path(temp)
        installer = args.installer.resolve() if args.installer else temp / "baseline.exe"
        if args.installer is None:
            with urllib.request.urlopen(BASELINE_URL, timeout=60) as source, installer.open("wb") as target:
                shutil.copyfileobj(source, target)
        if installer.stat().st_size != BASELINE_SIZE or digest(installer) != BASELINE_SHA256:
            raise SystemExit("Baseline installer size/SHA-256 mismatch; no source was changed")
        staging = temp / "source"
        staging.mkdir()
        extract(installer.read_bytes(), staging)
        for relative, hashes in manifest["files"].items():
            if digest(staging / relative) != hashes["before"]:
                raise SystemExit(f"Unexpected baseline source: {relative}")
        subprocess.run(["git", "init", "--quiet", str(staging)], check=True)
        for flag in ("--check", None):
            cmd = ["git", "-c", "core.autocrlf=false", "apply"]
            if flag:
                cmd.append(flag)
            cmd.append(str(package / "surveysense.patch"))
            subprocess.run(cmd, cwd=staging, check=True)
        for relative, hashes in manifest["files"].items():
            if digest(staging / relative) != hashes["after"]:
                raise SystemExit(f"Patched source hash mismatch: {relative}")
        shutil.rmtree(staging / ".git")
        (staging / "FieldBookSync.exe").unlink(missing_ok=True)
        staging.rename(output)
    print(f"SurveySense source reconstructed and verified: {output}")
    print("The legacy executable was removed. Run desktop.py from a configured environment or rebuild the native launcher.")


if __name__ == "__main__":
    main()
