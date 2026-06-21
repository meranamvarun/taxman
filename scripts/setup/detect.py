"""
OS and environment detection utilities.
Shared by setup.py and verify.py.
"""

from __future__ import annotations

import platform
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class EnvInfo:
    system: str           # "linux" | "macos" | "windows" | "unknown"
    distro: str           # "ubuntu" | "debian" | "fedora" | "arch" | "generic" | "macos" | "windows"
    pkg_manager: str      # "apt" | "dnf" | "pacman" | "brew" | "winget" | "choco" | "none"
    python_cmd: str       # "python3" | "python" | ""
    python_version: str   # "3.11.5" or ""
    python_ok: bool       # >= 3.11
    pip_cmd: str          # "pip3" | "pip" | ""
    has_venv: bool        # .venv/ exists with packages installed
    has_tesseract: bool
    has_playwright_browser: bool
    venv_python: str      # absolute path to .venv/bin/python (or .venv/Scripts/python.exe)
    project_root: Path
    missing: list[str] = field(default_factory=list)


def _run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, **kwargs)


def _exists(cmd: str) -> bool:
    return shutil.which(cmd) is not None


def detect(project_root: Path) -> EnvInfo:
    info = EnvInfo(
        system="unknown",
        distro="generic",
        pkg_manager="none",
        python_cmd="",
        python_version="",
        python_ok=False,
        pip_cmd="",
        has_venv=False,
        has_tesseract=False,
        has_playwright_browser=False,
        venv_python="",
        project_root=project_root,
    )

    # --- OS ---
    s = platform.system()
    if s == "Darwin":
        info.system = "macos"
        info.distro = "macos"
        info.pkg_manager = "brew" if _exists("brew") else "none"
    elif s == "Windows":
        info.system = "windows"
        info.distro = "windows"
        if _exists("winget"):
            info.pkg_manager = "winget"
        elif _exists("choco"):
            info.pkg_manager = "choco"
        else:
            info.pkg_manager = "none"
    elif s == "Linux":
        info.system = "linux"
        release = Path("/etc/os-release").read_text() if Path("/etc/os-release").exists() else ""
        if "ubuntu" in release.lower() or "debian" in release.lower():
            info.distro = "ubuntu" if "ubuntu" in release.lower() else "debian"
            info.pkg_manager = "apt"
        elif _exists("dnf"):
            info.distro = "fedora"
            info.pkg_manager = "dnf"
        elif _exists("pacman"):
            info.distro = "arch"
            info.pkg_manager = "pacman"
        else:
            info.distro = "generic"
            info.pkg_manager = "none"

    # --- Python ---
    for cmd in (["python3"], ["python"]):
        if _exists(cmd[0]):
            r = _run(cmd + ["--version"])
            ver_str = (r.stdout + r.stderr).strip()
            if "Python 3" in ver_str:
                parts = ver_str.split()[1].split(".")
                try:
                    major, minor = int(parts[0]), int(parts[1])
                    info.python_cmd = cmd[0]
                    info.python_version = ".".join(parts)
                    info.python_ok = (major, minor) >= (3, 11)
                    break
                except (ValueError, IndexError):
                    pass

    # --- pip ---
    for cmd in ("pip3", "pip"):
        if _exists(cmd):
            info.pip_cmd = cmd
            break

    # --- venv ---
    if info.system == "windows":
        venv_python = project_root / ".venv" / "Scripts" / "python.exe"
    else:
        venv_python = project_root / ".venv" / "bin" / "python"

    if venv_python.exists():
        r = _run([str(venv_python), "-c", "import pdfplumber, playwright, rich; print('ok')"])
        info.has_venv = r.returncode == 0
        info.venv_python = str(venv_python)
    else:
        info.venv_python = str(venv_python)

    # --- Tesseract ---
    if _exists("tesseract"):
        r = _run(["tesseract", "--version"])
        info.has_tesseract = r.returncode == 0

    # --- Playwright Chromium ---
    if info.has_venv:
        r = _run([info.venv_python, "-m", "playwright", "install", "--dry-run"])
        # If dry-run shows nothing to install, browser is present
        info.has_playwright_browser = "chromium" not in r.stdout.lower() and r.returncode == 0
        if not info.has_playwright_browser:
            # Check directly
            chromium_check = _run([info.venv_python, "-c",
                "from playwright.sync_api import sync_playwright; pw=sync_playwright().start(); b=pw.chromium.launch(); b.close(); pw.stop(); print('ok')"])
            info.has_playwright_browser = chromium_check.returncode == 0

    # --- Missing items ---
    if not info.python_ok:
        info.missing.append("python3.11+")
    if not info.has_venv:
        info.missing.append("pip_packages")
    if not info.has_playwright_browser:
        info.missing.append("playwright_browser")
    if not info.has_tesseract:
        info.missing.append("tesseract_ocr")

    return info
