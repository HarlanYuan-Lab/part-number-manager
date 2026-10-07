#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Entry point for the Part Number Manager desktop application.

Run from the source directory:
    python main.py
"""

import sys
import tkinter as tk

from part_manager.ui.main_window import PartNumberApp
from part_manager.ui.theme import setup_styles


def main() -> int:
    root = tk.Tk()
    setup_styles(root)
    PartNumberApp(root)
    root.mainloop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
