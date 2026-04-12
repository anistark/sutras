"""Progress indicators for long-running CLI operations."""

from __future__ import annotations

import sys
import threading
import time
from contextlib import contextmanager
from itertools import cycle

import click


@contextmanager
def spinner(message: str, done_message: str | None = None):
    """Display a spinner during a long-running operation.

    Args:
        message: Status message to display alongside the spinner.
        done_message: Message to show on completion. Defaults to "{message} done".

    Usage:
        with spinner("Installing skill"):
            do_long_operation()
    """
    frames = cycle(["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"])
    stop_event = threading.Event()
    is_tty = sys.stderr.isatty()

    if not is_tty:
        click.echo(f"  {message}...", err=True)
        yield
        if done_message:
            click.echo(f"  {done_message}", err=True)
        return

    def _animate():
        while not stop_event.is_set():
            frame = next(frames)
            click.echo(f"\r  {frame} {message}...", nl=False, err=True)
            stop_event.wait(0.08)

    t = threading.Thread(target=_animate, daemon=True)
    t.start()

    try:
        yield
    finally:
        stop_event.set()
        t.join()
        final = done_message or f"{message} done"
        click.echo(f"\r  {click.style('✓', fg='green')} {final}   ", err=True)


@contextmanager
def status(message: str):
    """Print a simple status line before and after an operation.

    Non-animated alternative to spinner for simpler output.

    Usage:
        with status("Validating skill"):
            validate()
    """
    click.echo(f"  {click.style('→', fg='blue')} {message}...")
    start = time.monotonic()
    yield
    elapsed = time.monotonic() - start
    if elapsed > 1.0:
        click.echo(f"  {click.style('✓', fg='green')} {message} ({elapsed:.1f}s)")
