from typing import Any

def main() -> None:
    """
    Entry point for the yt2spotify package when run as a script.
    """
    # Import here to avoid circular import issues
    from .cli import main as cli_main  # type: ignore[import]
    cli_main()

if __name__ == "__main__":
    main()
