#!/usr/bin/env python3
"""Silent bootstrap wrapper that suppresses all stderr output."""

import os
import subprocess
import sys


def main():
    """Run bootstrap with stderr completely suppressed."""
    # Set environment to suppress warnings
    env = os.environ.copy()
    env["PYTHONWARNINGS"] = "ignore"

    # Run bootstrap with stderr redirected to null
    process = subprocess.run(
        [sys.executable, "-m", "mopenstack.bootstrap"],
        env=env,
        stderr=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        text=True,
    )

    # Print stdout only
    if process.stdout:
        print(process.stdout.rstrip())

    return process.returncode


if __name__ == "__main__":
    sys.exit(main())
