"""UI panels: the three content screens of the main window.

Each panel is built into a container frame provided by the main window and
delegates business actions back to the application controller (``app``).
"""

from __future__ import annotations

import tkinter as tk
import os
from tkinter import ttk

from .. import config
from .theme import COLORS


def _card(parent: tk.Misc) -> tk.Frame:
    """A white 'card' frame with a light border."""
    return tk.Frame(parent, bg=COLORS["card"], highlightbackground=COLORS["border"],
                    highlightthickness=1)


class DatabasesPanel:
    """Lists all databases with their prefixes / part counts."""

    def __init__(self, container: tk.Misc, app):
        self.app = app
        self.container = container
        self._build()

    # ------------------------------------------------------------------ build
    def _build(self):
        card = _card(self.container)
        card.pack(fill="both", expand=True)

        inner = ttk.Frame(card, style="Card.TFrame", padding=(20, 20, 20, 10))
        inner.pack(fill="both", expand=True)
        inner.columnconfigure(0, weight=1)

        ttk.Label(inner, text="Databases", style="Section.TLabel").grid(
            row=0, column=0, sticky="w", pady=(0, 6))
        ttk.Label(inner, text="Each database is independent, with its own leading "
                              "numbers and sequence.",
                  style="Hint.TLabel").grid(row=1, column=0, sticky="w", pady=(0, 12))

        table_frame = _card(inner)
        table_frame.grid(row=2, column=0, sticky="nsew")
        table_frame.columnconfigure(0, weight=1)
        table_frame.rowconfigure(0, weight=1)

        columns = ("name", "assembly", "part", "standard", "count", "created",
                   "location")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings",
                                 selectmode="browse")
        headers = {
            "name": ("Database Name", 170, "w"),
            "assembly": ("Assembly", 70, "center"),
            "part": ("Part", 70, "center"),
            "standard": ("Standard", 70, "center"),
            "count": ("Parts", 60, "center"),
            "created": ("Created", 100, "center"),
            "location": ("Location", 260, "w"),
        }
        for col in columns:
            text, width, anchor = headers[col]
            self.tree.heading(col, text=text)
            self.tree.column(col, width=width, anchor=anchor)
        vsb = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview,
                            style="Vertical.TScrollbar")
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        self.tree.bind("<Double-1>", lambda e: self.app.open_database())

        actions = ttk.Frame(inner, style="Card.TFrame")
        actions.grid(row=3, column=0, sticky="w", pady=(12, 0))
        ttk.Button(actions, text="New Database…", style="Primary.TButton",
                   command=self.app.new_database).pack(side="left", padx=(0, 8))
        ttk.Button(actions, text="Open Selected", style="Secondary.TButton",
                   command=self.app.open_database).pack(side="left", padx=(0, 8))
        ttk.Button(actions, text="Delete Selected", style="Danger.TButton",
                   command=self.app.delete_database).pack(side="left")

        self.status = ttk.Label(inner, text="", style="Status.TLabel")
        self.status.grid(row=4, column=0, sticky="w", pady=(8, 0))

        # Inline, copyable result for database creation (no popup)
        result = tk.Frame(inner, bg=COLORS["success_light"],
                          highlightbackground="#A7F3D0", highlightthickness=1)
        result.grid(row=5, column=0, sticky="ew", pady=(10, 0))
        result.columnconfigure(1, weight=1)
        ttk.Label(result, text="Created", style="Hint.TLabel").grid(
            row=0, column=0, sticky="w", padx=(16, 8), pady=(12, 0))
        self.db_result_entry = ttk.Entry(result, width=48, state="readonly",
                                         font=("Segoe UI", 11),
                                         style="Result.TEntry")
        self.db_result_entry.grid(row=0, column=1, sticky="ew", padx=(0, 16),
                                  pady=(12, 0))

        inner.rowconfigure(2, weight=1)

        self.tree.tag_configure("odd", background=COLORS["row_alt"])
        self.tree.tag_configure("even", background=COLORS["card"])

    # ------------------------------------------------------------------ logic
    def refresh(self):
        summaries = self.app.db_service.list_databases()
        for i in self.tree.get_children():
            self.tree.delete(i)
        for idx, info in enumerate(summaries):
            tag = "even" if idx % 2 == 0 else "odd"
            self.tree.insert(
                "", "end", tags=(tag,),
                values=(info.name, info.prefixes.get("Assembly", ""),
                        info.prefixes.get("Part", ""),
                        info.prefixes.get("Standard", ""),
                        info.part_count, info.created_date,
                        os.path.dirname(info.path)))
        self.status.config(text=f"{len(summaries)} database(s).")

    def selected_name(self) -> str | None:
        sel = self.tree.selection()
        if not sel:
            return None
        return self.tree.item(sel[0], "values")[0]

    def show_result(self, text: str):
        self.db_result_entry.configure(state="normal")
        self.db_result_entry.delete(0, "end")
        self.db_result_entry.insert(0, text)
        self.db_result_entry.configure(state="readonly")


class CreatePanel:
    """Form to create a part number in the active database."""

    def __init__(self, container: tk.Misc, app):
        self.app = app
        self.container = container
        self._build()

    # ------------------------------------------------------------------ build
    def _build(self):
        card = _card(self.container)
        card.pack(fill="both", expand=True)   # <-- must be packed to show

        inner = ttk.Frame(card, style="Card.TFrame", padding=24)
        inner.pack(fill="both", expand=True)
        inner.columnconfigure(1, weight=1)


        title_row = ttk.Frame(inner, style="Card.TFrame")
        title_row.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 16))
        title_row.columnconfigure(0, weight=1)
        ttk.Label(title_row, text="Create a New Part Number",
                  style="Section.TLabel").pack(side="left")
        ttk.Button(title_row, text="Create Part Number", style="Primary.TButton",
                   command=self.app.create_part).pack(side="right")

        ttk.Label(inner, text="Part Name *", style="Field.TLabel").grid(
            row=1, column=0, sticky="w", pady=(4, 2))
        self.name_entry = ttk.Entry(inner, width=54, style="Modern.TEntry")
        self.name_entry.grid(row=1, column=1, sticky="ew", padx=(14, 0), pady=(4, 2))

        ttk.Label(inner, text="Material", style="Field.TLabel").grid(
            row=2, column=0, sticky="w", pady=(10, 2))
        self.material_entry = ttk.Entry(inner, width=54, style="Modern.TEntry")
        self.material_entry.grid(row=2, column=1, sticky="ew", padx=(14, 0), pady=(10, 2))

        ttk.Label(inner, text="Description", style="Field.TLabel").grid(
            row=3, column=0, sticky="nw", pady=(10, 2))
        self.desc_text = tk.Text(inner, width=54, height=4, wrap="word",
                                 font=("Segoe UI", 10), bg="#FFFFFF", relief="flat",
                                 padx=8, pady=8, highlightbackground=COLORS["border"],
                                 highlightcolor=COLORS["primary"], highlightthickness=1)
        self.desc_text.grid(row=3, column=1, sticky="ew", padx=(14, 0), pady=(10, 2))

        ttk.Label(inner, text="Part Type", style="Field.TLabel").grid(
            row=4, column=0, sticky="w", pady=(14, 2))
        type_frame = ttk.Frame(inner, style="Card.TFrame")
        type_frame.grid(row=4, column=1, sticky="w", padx=(14, 0), pady=(14, 2))
        self.type_var = tk.StringVar(value=config.PART_TYPES[0])
        self.type_var.trace_add("write", lambda *a: self.update_preview())
        for i, part_type in enumerate(config.PART_TYPES):
            ttk.Radiobutton(type_frame, text=part_type, variable=self.type_var,
                            value=part_type).pack(side="left", padx=(0, 20))

        # Number preview box
        preview = tk.Frame(inner, bg=COLORS["primary_light"],
                           highlightbackground="#C7D2FE", highlightthickness=1)
        preview.grid(row=5, column=0, columnspan=2, sticky="ew", pady=(20, 6))
        preview.columnconfigure(1, weight=1)
        ttk.Label(preview, text="Generated Number", style="Hint.TLabel").grid(
            row=0, column=0, sticky="w", padx=(16, 8), pady=(12, 0))
        ttk.Label(preview, text="Automatically assigned on creation",
                  style="Hint.TLabel").grid(row=1, column=0, sticky="w",
                                            padx=(16, 8), pady=(0, 12))
        self.number_preview = tk.Label(preview, text="—", font=("Consolas", 24, "bold"),
                                       fg=COLORS["primary"], bg=COLORS["primary_light"])
        self.number_preview.grid(row=0, column=1, rowspan=2, sticky="e",
                                 padx=(0, 18), pady=10)

        # Inline creation result (copyable, replaces popup notifications)
        result = tk.Frame(inner, bg=COLORS["success_light"],
                          highlightbackground="#A7F3D0", highlightthickness=1)
        result.grid(row=6, column=0, columnspan=2, sticky="ew", pady=(14, 6))
        result.columnconfigure(1, weight=1)
        ttk.Label(result, text="Created", style="Hint.TLabel").grid(
            row=0, column=0, sticky="w", padx=(16, 8), pady=(12, 0))
        self.result_entry = ttk.Entry(result, width=46, state="readonly",
                                      font=("Segoe UI", 11),
                                      justify="left", style="Result.TEntry")
        self.result_entry.grid(row=0, column=1, sticky="ew", padx=(0, 16),
                               pady=(12, 0))


    # ------------------------------------------------------------------ logic
    def update_preview(self, *args):
        service = self.app.parts_service
        if service is None:
            self.number_preview.config(text="—")
            return
        try:
            self.number_preview.config(
                text=service.peek_number(self.type_var.get()))
        except Exception:
            self.number_preview.config(text="")

    def clear_fields(self):
        self.name_entry.delete(0, "end")
        self.material_entry.delete(0, "end")
        self.desc_text.delete("1.0", "end")
        self.name_entry.focus_set()

    def show_result(self, text: str):
        """Show a creation result line in the copyable box."""
        self.result_entry.configure(state="normal")
        self.result_entry.delete(0, "end")
        self.result_entry.insert(0, text)
        self.result_entry.configure(state="readonly")
        self.result_entry.selection_clear()

    def focus_name(self):
        self.name_entry.focus_set()



class ManagePanel:
    """Search / modify / delete / export parts of the active database."""

    def __init__(self, container: tk.Misc, app):
        self.app = app
        self.container = container
        self._build()

    # ------------------------------------------------------------------ build
    def _build(self):
        card = _card(self.container)
        card.pack(fill="both", expand=True)

        inner = ttk.Frame(card, style="Card.TFrame", padding=(20, 20, 20, 10))
        inner.pack(fill="both", expand=True)
        inner.columnconfigure(0, weight=1)

        toolbar = ttk.Frame(inner, style="Card.TFrame")
        toolbar.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        toolbar.columnconfigure(1, weight=1)
        ttk.Label(toolbar, text="Search", style="Field.TLabel").grid(
            row=0, column=0, sticky="w")
        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(toolbar, textvariable=self.search_var, width=38,
                                 style="Modern.TEntry")
        search_entry.grid(row=0, column=1, sticky="ew", padx=(10, 0))
        search_entry.bind("<Return>", lambda e: self.refresh())
        ttk.Button(toolbar, text="Search", style="Secondary.TButton",
                   command=self.refresh).grid(row=0, column=2, padx=(8, 0))
        ttk.Button(toolbar, text="Show All", style="Secondary.TButton",
                   command=self.show_all).grid(row=0, column=3, padx=(6, 0))
        ttk.Label(toolbar, text="Search by part number, name or material.",
                  style="Hint.TLabel").grid(row=1, column=1, sticky="w",
                                            padx=(10, 0), pady=(2, 0))

        table_frame = _card(inner)
        table_frame.grid(row=1, column=0, sticky="nsew")
        table_frame.columnconfigure(0, weight=1)
        table_frame.rowconfigure(0, weight=1)

        columns = ("part_number", "part_name", "part_type", "material",
                   "description", "created_date")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings",
                                 selectmode="extended")
        headers = {
            "part_number": ("Part Number", 120, "center"),
            "part_name": ("Part Name", 190, "center"),
            "part_type": ("Part Type", 95, "center"),
            "material": ("Material", 140, "center"),
            "description": ("Description", 220, "w"),
            "created_date": ("Created", 100, "center"),
        }
        for col in columns:
            text, width, anchor = headers[col]
            self.tree.heading(col, text=text)
            self.tree.column(col, width=width, anchor=anchor)
        vsb = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview,
                            style="Vertical.TScrollbar")
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        self.tree.tag_configure("odd", background=COLORS["row_alt"])
        self.tree.tag_configure("even", background=COLORS["card"])
        self.tree.bind("<Double-1>", lambda e: self.app.modify_part())
        self.tree.bind("<Delete>", lambda e: self.app.delete_part())

        actions = ttk.Frame(inner, style="Card.TFrame")
        actions.grid(row=2, column=0, sticky="w", pady=(12, 0))
        ttk.Button(actions, text="Modify Selected", style="Secondary.TButton",
                   command=self.app.modify_part).pack(side="left", padx=(0, 8))
        ttk.Button(actions, text="Delete Selected", style="Danger.TButton",
                   command=self.app.delete_part).pack(side="left", padx=(0, 8))
        ttk.Button(actions, text="Export to Excel", style="Secondary.TButton",
                   command=self.app.export_parts).pack(side="left")

        self.status = ttk.Label(inner, text="", style="Status.TLabel")
        self.status.grid(row=3, column=0, sticky="w", pady=(8, 0))
        inner.rowconfigure(1, weight=1)

    # ------------------------------------------------------------------ logic
    def show_all(self):
        self.search_var.set("")
        self.refresh()

    def selected_part_number(self) -> str | None:
        sel = self.tree.selection()
        if not sel:
            return None
        return self.tree.item(sel[0], "values")[0]

    def selected_part_numbers(self) -> list[str]:
        """Numbers of all selected rows (supports Shift-range / Ctrl-multi)."""
        return [self.tree.item(i, "values")[0] for i in self.tree.selection()]

    def refresh(self):
        service = self.app.parts_service
        for i in self.tree.get_children():
            self.tree.delete(i)
        if service is None:
            self.status.config(text="No database selected.")
            return
        parts = service.search(self.search_var.get())
        for idx, part in enumerate(parts):
            tag = "even" if idx % 2 == 0 else "odd"
            self.tree.insert("", "end", tags=(tag,),
                             values=(part.part_number, part.part_name,
                                     part.part_type, part.material,
                                     part.description, part.created_date))
        self.status.config(
            text=f"{len(parts)} part(s) found in '{self.app.active_db}'.")
