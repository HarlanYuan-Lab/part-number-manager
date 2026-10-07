"""Entry point for Part Number Manager V2 (centralized PostgreSQL server)."""

import tkinter as tk

from part_manager.ui.main_window import PartNumberApp


def main() -> None:
    root = tk.Tk()
    app = PartNumberApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
