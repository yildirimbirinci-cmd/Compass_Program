from __future__ import annotations
import os
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

@dataclass
class ProcessResult:
    command: list[str]
    return_code: int
    elapsed_seconds: float
    stdout: str
    stderr: str

class ProcessFailure(RuntimeError):
    pass


def _decode_output(data: bytes) -> str:
    if not data:
        return ""
    if data.startswith(b"\xff\xfe") or b"\x00" in data[:200]:
        for encoding in ("utf-16", "utf-16-le"):
            try:
                return data.decode(encoding, errors="replace")
            except Exception:
                pass
    for encoding in ("utf-8", "cp1254", "cp1252"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


def run_process(command: list[str], cwd: Path, timeout: int, log_path: Path,
                extra_env: dict[str, str] | None = None,
                allow_failure: bool = False,
                hidden: bool = True) -> ProcessResult:
    started = time.monotonic()
    env = os.environ.copy()
    if extra_env:
        env.update({str(k): str(v) for k, v in extra_env.items()})

    creationflags = 0
    startupinfo = None
    if os.name == "nt" and hidden:
        creationflags |= getattr(subprocess, "CREATE_NO_WINDOW", 0)
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = 0

    proc = subprocess.run(
        command,
        cwd=str(cwd),
        capture_output=True,
        text=False,
        timeout=timeout,
        creationflags=creationflags,
        startupinfo=startupinfo,
        env=env,
    )
    stdout = _decode_output(proc.stdout)
    stderr = _decode_output(proc.stderr)
    result = ProcessResult(command, proc.returncode, time.monotonic() - started, stdout, stderr)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text(
        "COMMAND:\n" + subprocess.list2cmdline(command) +
        f"\n\nRETURN_CODE: {proc.returncode}\nELAPSED: {result.elapsed_seconds:.2f}s\n\nSTDOUT:\n{stdout}\n\nSTDERR:\n{stderr}",
        encoding="utf-8",
    )
    if proc.returncode != 0 and not allow_failure:
        raise ProcessFailure(f"External process failed ({proc.returncode}). See {log_path}")
    return result
