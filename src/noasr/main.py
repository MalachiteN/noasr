"""Main entry point for noasr."""

import argparse
import sys

from noasr.config import check_and_bootstrap


def main() -> int:
    """Run noasr voice input method."""
    parser = argparse.ArgumentParser(
        prog="noasr",
        description="Voice input method using Xiaomi MiMo Omni multimodal model",
        epilog="Example: noasr",
    )
    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s 0.1.0",
    )

    args = parser.parse_args()

    # Check if first run and bootstrap if needed
    is_first_run = check_and_bootstrap()
    if is_first_run:
        return 0

    # TODO: Continue with runtime initialization (Task 11)
    print("noasr v0.1.0 - Voice input using MiMo Omni", file=sys.stderr)
    print(
        "Bootstrap complete. Runtime implementation coming in subsequent tasks.",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
