"""Visual theme: colour palette and ttk style setup for the whole UI.

Mirrors the Part Number Manager V1.0 theme so the V2 window looks the same.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

# --------------------------------------------------------------------------- palette
COLORS = {
    "bg": "#EEF2F7",
    "card": "#FFFFFF",
    "primary": "#3B5BDB",
    "primary_dark": "#1E3A8A",
    "primary_light": "#EEF2FF",
    "accent": "#10B981",
    "text": "#1F2937",
    "muted": "#6B7280",
    "border": "#E2E8F0",
    "row_alt": "#F6F8FB",
    "select": "#DBEAFE",
    "tab_inactive": "#E7EDF7",
    "danger": "#DC2626",
    "danger_light": "#FEE2E2",
    "success_light": "#ECFDF5",
}


def setup_styles(root: tk.Misc) -> None:
    """Apply the application theme to a Tk root (or any widget tree)."""
    c = COLORS
    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except Exception:
        pass

    # A global default font so every widget (including buttons) renders text.
    style.configure(".", font=("Segoe UI", 10), background=c["bg"],
                    foreground=c["text"])

    style.configure("TFrame", background=c["bg"])
    style.configure("Card.TFrame", background=c["card"])

    # Header banner
    style.configure("Header.TFrame", background=c["primary"])
    style.configure("HeaderTitle.TLabel", background=c["primary"],
                    foreground="#FFFFFF", font=("Segoe UI", 17, "bold"))
    style.configure("HeaderSub.TLabel", background=c["primary"],
                    foreground="#D6DEFF", font=("Segoe UI", 9))

    # Labels
    style.configure("TLabel", background=c["bg"], foreground=c["text"])
    style.configure("Card.TLabel", background=c["card"], foreground=c["text"])
    style.configure("Section.TLabel", background=c["card"], foreground=c["primary"],
                    font=("Segoe UI", 14, "bold"))
    style.configure("Field.TLabel", background=c["card"], foreground=c["text"])
    style.configure("Hint.TLabel", background=c["card"], foreground=c["muted"],
                    font=("Segoe UI", 9))
    style.configure("Status.TLabel", background=c["bg"], foreground=c["muted"])

    # Entries
    style.configure("Modern.TEntry", fieldbackground="#FFFFFF",
                    bordercolor=c["border"], lightcolor=c["border"],
                    darkcolor=c["border"], padding=7)
    style.map("Modern.TEntry",
              bordercolor=[("focus", c["primary"])],
              lightcolor=[("focus", c["primary"])],
              darkcolor=[("focus", c["primary"])])
    style.configure("Result.TEntry", fieldbackground="#ECFDF5",
                    foreground=c["primary_dark"], bordercolor="#A7F3D0",
                    lightcolor="#A7F3D0", darkcolor="#A7F3D0", padding=7)

    # Buttons
    style.configure("Primary.TButton", background=c["primary"], foreground="#FFFFFF",
                    borderwidth=0, focusthickness=0, padding=(16, 9),
                    font=("Segoe UI", 10, "bold"))
    style.map("Primary.TButton",
              background=[("active", c["primary_dark"]),
                          ("pressed", c["primary_dark"])],
              foreground=[("disabled", "#C7D2FE")])
    style.configure("Secondary.TButton", background=c["card"], foreground=c["text"],
                    borderwidth=1, relief="solid", padding=(12, 8),
                    font=("Segoe UI", 10))
    style.map("Secondary.TButton",
              background=[("active", "#EAF0FF"), ("pressed", "#DCE5FA")])
    style.configure("Danger.TButton", background="#FFFFFF", foreground=c["danger"],
                    borderwidth=1, relief="solid", padding=(12, 8),
                    font=("Segoe UI", 10))
    style.map("Danger.TButton",
              background=[("active", c["danger_light"]), ("pressed", "#FECACA")])

    # Radio buttons
    style.configure("TRadiobutton", background=c["card"], foreground=c["text"],
                    font=("Segoe UI", 10))
    style.map("TRadiobutton", background=[("active", c["card"])])

    # Treeview
    style.configure("Treeview", background=c["card"], fieldbackground=c["card"],
                    foreground=c["text"], rowheight=30, borderwidth=0,
                    font=("Segoe UI", 10))
    style.configure("Treeview.Heading", background="#EEF2F7", foreground=c["text"],
                    font=("Segoe UI", 10, "bold"), padding=6, relief="flat")
    style.map("Treeview.Heading", background=[("active", "#E3E9F5")])
    style.map("Treeview", background=[("selected", c["select"])],
              foreground=[("selected", c["text"])])

    # Scrollbar
    style.configure("Vertical.TScrollbar", background="#CBD5E1",
                    troughcolor=c["card"], borderwidth=0, arrowcolor="#64748B")

    # Combobox
    style.configure("TCombobox", fieldbackground="#FFFFFF", padding=5)
