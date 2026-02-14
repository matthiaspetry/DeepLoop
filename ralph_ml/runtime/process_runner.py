"""Process runner utilities for Ralph ML Loop."""

import os
import selectors
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional


def run_with_heartbeat(
    command: list[str],
    cwd: Path,
    timeout_seconds: int,
    phase_label: str,
    heartbeat_seconds: int = 10,
    input_text: Optional[str] = None,
) -> tuple[int, str, str, float, bool]:
    """Run subprocess and print periodic progress until completion.

    Args:
        command: Command to run
        cwd: Working directory
        timeout_seconds: Timeout in seconds
        phase_label: Label for progress messages
        heartbeat_seconds: Seconds between progress updates
        input_text: Optional input to send to stdin

    Returns:
        Tuple of (returncode, stdout, stderr, elapsed_seconds, timed_out)
    """
    start = time.time()
    proc = subprocess.Popen(
        command,
        cwd=cwd,
        stdin=subprocess.PIPE if input_text is not None else None,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    timed_out = False
    while True:
        elapsed = time.time() - start
        remaining = timeout_seconds - elapsed

        if remaining <= 0:
            timed_out = True
            proc.kill()
            stdout, stderr = proc.communicate()
            break

        wait_chunk = min(heartbeat_seconds, max(1, int(remaining)))
        try:
            stdout, stderr = proc.communicate(input=input_text, timeout=wait_chunk)
            break
        except subprocess.TimeoutExpired:
            input_text = None
            elapsed = time.time() - start
            print(
                f"   ... {phase_label} still running ({elapsed:.0f}s / {timeout_seconds}s, pid={proc.pid})"
            )
            sys.stdout.flush()

    elapsed_total = time.time() - start
    return (proc.returncode or 0), stdout, stderr, elapsed_total, timed_out


def run_training_with_live_logs(
    command: list[str],
    cwd: Path,
    timeout_seconds: int,
    heartbeat_seconds: int = 10,
) -> tuple[int, str, str, float, bool]:
    """Run training and stream stdout/stderr lines live.

    Args:
        command: Command to run
        cwd: Working directory
        timeout_seconds: Timeout in seconds
        heartbeat_seconds: Seconds between progress updates

    Returns:
        Tuple of (returncode, stdout, stderr, elapsed_seconds, timed_out)
    """
    start = time.time()
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"

    proc = subprocess.Popen(
        command,
        cwd=cwd,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
    )

    stdout_lines: list[str] = []
    stderr_lines: list[str] = []
    timed_out = False
    last_heartbeat = start

    sel = selectors.DefaultSelector()
    if proc.stdout is not None:
        sel.register(proc.stdout, selectors.EVENT_READ)
    if proc.stderr is not None:
        sel.register(proc.stderr, selectors.EVENT_READ)

    while True:
        now = time.time()
        elapsed = now - start

        if elapsed > timeout_seconds:
            timed_out = True
            proc.kill()
            break

        events = sel.select(timeout=1.0)
        for key, _ in events:
            line = key.fileobj.readline()
            if not line:
                continue

            if proc.stdout is not None and key.fileobj is proc.stdout:
                stdout_lines.append(line)
                print(f"   [train] {line.rstrip()}")
            else:
                stderr_lines.append(line)
                print(f"   [train:err] {line.rstrip()}")
            sys.stdout.flush()

        if proc.poll() is not None:
            break

        if now - last_heartbeat >= heartbeat_seconds:
            print(
                f"   ... Phase 2 training still running ({elapsed:.0f}s / {timeout_seconds}s, pid={proc.pid})"
            )
            sys.stdout.flush()
            last_heartbeat = now

    if proc.stdout is not None:
        remainder = proc.stdout.read()
        if remainder:
            stdout_lines.append(remainder)
            for line in remainder.splitlines():
                print(f"   [train] {line}")
    if proc.stderr is not None:
        remainder = proc.stderr.read()
        if remainder:
            stderr_lines.append(remainder)
            for line in remainder.splitlines():
                print(f"   [train:err] {line}")

    sel.close()
    proc.wait()
    elapsed_total = time.time() - start
    return (
        proc.returncode or 0,
        "".join(stdout_lines),
        "".join(stderr_lines),
        elapsed_total,
        timed_out,
    )
