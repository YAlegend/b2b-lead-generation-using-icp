"""
Lead finding via the OpenOutreach CLI, isolated per-request in a temp dir.

This wraps the same `openoutreach init` / `openoutreach find` flow already
used by run.py and wizard.py, but non-interactively (via env vars) and
scoped to a throwaway working directory so concurrent web requests don't
clobber each other's config.
"""

import os
import shutil
import subprocess
import tempfile
from pathlib import Path


class LeadsError(RuntimeError):
    pass


def _openoutreach_available() -> bool:
    return shutil.which("openoutreach") is not None


def _install_openoutreach(timeout: int = 180) -> None:
    if shutil.which("uv") is None:
        subprocess.run(
            "curl -LsSf https://astral.sh/uv/install.sh | sh",
            shell=True, check=True, timeout=timeout,
        )
        os.environ["PATH"] = f"{Path.home()}/.local/bin:{os.environ.get('PATH', '')}"
    subprocess.run(["uv", "tool", "install", "openoutreach"], check=True, timeout=timeout)


def find_leads(product_md: str, target_md: str, bettercontact_key: str,
               count: int = 10, llm_env: dict | None = None,
               with_emails: bool = False, timeout: int = 120) -> str:
    """Run OpenOutreach end-to-end and return its raw stdout output."""
    if not bettercontact_key:
        raise LeadsError("A BetterContact API key is required to find leads.")

    if not _openoutreach_available():
        try:
            _install_openoutreach()
        except Exception as exc:
            raise LeadsError(f"Could not install OpenOutreach: {exc}") from exc

    if not _openoutreach_available():
        raise LeadsError("OpenOutreach installed but not on PATH.")

    work_dir = Path(tempfile.mkdtemp(prefix="outreach-"))
    try:
        (work_dir / "product.md").write_text(product_md)
        (work_dir / "target.md").write_text(target_md)

        env = {
            **os.environ,
            "OPENOUTFIND_BETTERCONTACT_API_KEY": bettercontact_key,
        }
        if llm_env:
            env.update(llm_env)

        init = subprocess.run(
            ["openoutreach", "init",
             "--product-docs", "product.md", "--target", "target.md"],
            cwd=work_dir, env=env, capture_output=True, text=True, timeout=timeout,
        )
        if init.returncode != 0:
            raise LeadsError(
                f"OpenOutreach setup failed:\n{init.stdout}\n{init.stderr}"
            )

        cmd = ["openoutreach", "find", str(count)]
        if with_emails:
            cmd.append("emails")

        find = subprocess.run(
            cmd, cwd=work_dir, env=env, capture_output=True, text=True, timeout=timeout,
        )
        if find.returncode != 0:
            raise LeadsError(f"Lead search failed:\n{find.stdout}\n{find.stderr}")

        return find.stdout.strip()
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)
