import sys


def _print_menu():
    print("\nGlitch Hub")
    print("1) Data \u2192 Video (Tkinter app)")
    print("2) Tomato (AVI datamosh)")
    print("q) Quit")


def main():
    while True:
        _print_menu()
        choice = input("Select an option: ").strip().lower()

        if choice == "1":
            import app

            app.main()
        elif choice == "2":
            from glitch_hub import tomato

            tomato.main()
        elif choice in {"q", "quit"}:
            print("Goodbye!")
            return
        else:
            print("Unknown option, please try again.")


if __name__ == "__main__":
    sys.exit(main())
