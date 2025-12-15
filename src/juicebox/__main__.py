from .app import JuiceboxApp


def main() -> None:
    """Run the Juicebox TUI application."""
    JuiceboxApp().run()


if __name__ == "__main__":
    main()
