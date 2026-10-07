"""Main application window (controller).

Builds the header, database toolbar, custom tab bar and the three panels,
holds the application state (the active database path), and wires user
actions to the service layer.
"""

from __future__ import annotations

import datetime
import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from .. import config
from ..exporter import export_parts_to_excel
from ..services import DatabaseService, PartNumberService
from .dialogs import ModifyDialog, NewDatabaseDialog
from .panels import CreatePanel, DatabasesPanel, ManagePanel
from .theme import COLORS, setup_styles

TAB_LABELS = (("Databases", 0), ("Create Part Number", 1), ("Manage Parts", 2))


class PartNumberApp:
    """The single application window; owns state and coordinates the panels."""

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title(f"{config.APP_NAME} - Multiple Databases")
        self.root.geometry("1080x820")
        self.root.minsize(920, 640)
        self.root.configure(bg=COLORS["bg"])

        self.active_db: str | None = None      # display name
        self.db_path: str | None = None        # absolute path (the real key)
        self.parts_service: PartNumberService | None = None
        self.db_service = DatabaseService()
        self._summary_by_name: dict[str, str] = {}

        setup_styles(root)
        self._build_header()
        self._build_toolbar()
        self._build_tabs()
        self._restore_last_db()
        self.refresh_all()

    # ------------------------------------------------------------------ header
    def _build_header(self):
        header = ttk.Frame(self.root, style="Header.TFrame", padding=(22, 12))
        header.pack(fill="x")
        left = ttk.Frame(header, style="Header.TFrame")
        left.pack(side="left")
        ttk.Label(left, text=config.APP_NAME, style="HeaderTitle.TLabel").pack(
            anchor="w")
        ttk.Label(left, text="Create & manage 6-digit part numbers across "
                             "multiple databases",
                  style="HeaderSub.TLabel").pack(anchor="w", pady=(1, 0))
        self.db_chip = tk.Label(header, text="Database: —", bg="#FFFFFF",
                                fg=COLORS["primary"], font=("Segoe UI", 9, "bold"),
                                padx=12, pady=4)
        self.db_chip.pack(side="right", padx=(10, 4))

    # ------------------------------------------------------------------ toolbar
    def _build_toolbar(self):
        bar = tk.Frame(self.root, bg=COLORS["card"],
                       highlightbackground=COLORS["border"], highlightthickness=1)
        bar.pack(fill="x", padx=16, pady=(12, 6))
        inner = ttk.Frame(bar, style="Card.TFrame", padding=(14, 10))
        inner.pack(fill="x")

        ttk.Label(inner, text="Database", style="Field.TLabel").pack(side="left")
        self.db_combo_var = tk.StringVar()
        self.db_combo = ttk.Combobox(inner, state="readonly", width=22,
                                     style="TCombobox", textvariable=self.db_combo_var)
        self.db_combo.pack(side="left", padx=(10, 8))
        self.db_combo.bind("<<ComboboxSelected>>", lambda e: self._on_combo_select())

        ttk.Button(inner, text="New…", style="Primary.TButton",
                   command=self.new_database).pack(side="left", padx=4)
        ttk.Button(inner, text="Import…", style="Secondary.TButton",
                   command=self.import_database).pack(side="left", padx=4)
        ttk.Button(inner, text="Open", style="Secondary.TButton",
                   command=self.open_database).pack(side="left", padx=4)
        ttk.Button(inner, text="Export…", style="Secondary.TButton",
                   command=self.export_database).pack(side="left", padx=4)
        ttk.Button(inner, text="Delete", style="Danger.TButton",
                   command=self.delete_database).pack(side="left", padx=4)
        ttk.Button(inner, text="Refresh", style="Secondary.TButton",
                   command=self.refresh_all).pack(side="left", padx=4)

        self.prefix_status = ttk.Label(inner, text="", style="Hint.TLabel")
        self.prefix_status.pack(side="right")

    # ------------------------------------------------------------------ tabs
    def _build_tabs(self):
        self._tab_bar = tk.Frame(self.root, bg=COLORS["card"])
        self._tab_bar.pack(fill="x", padx=16)
        self._tab_widgets = []
        for text, index in TAB_LABELS:
            holder = self._make_tab(text, lambda i=index: self.select_tab(i))
            holder.pack(side="left", padx=(0, 6))
            self._tab_widgets.append(holder)

        self._content = tk.Frame(self.root, bg=COLORS["bg"])
        self._content.pack(fill="both", expand=True, padx=16, pady=(0, 14))

        containers = [tk.Frame(self._content, bg=COLORS["bg"]) for _ in TAB_LABELS]
        self.databases_panel = DatabasesPanel(containers[0], self)
        self.create_panel = CreatePanel(containers[1], self)
        self.manage_panel = ManagePanel(containers[2], self)
        self._containers = containers
        self.select_tab(0)

    def _make_tab(self, text, callback) -> tk.Frame:
        holder = tk.Frame(self._tab_bar, bg=COLORS["card"], cursor="hand2")
        label = tk.Label(holder, text=text, cursor="hand2")
        label.pack()
        label.bind("<Button-1>", lambda e: callback())
        holder.bind("<Button-1>", lambda e: callback())
        return holder

    def select_tab(self, index: int):
        """Switch panels; the selected tab renders larger than the others."""
        for holder, (text, idx) in zip(self._tab_widgets, TAB_LABELS):
            selected = (idx == index)
            holder.configure(bg=COLORS["primary"] if selected else COLORS["tab_inactive"])
            inner = holder.winfo_children()[0]
            inner.configure(
                bg=COLORS["primary"] if selected else COLORS["tab_inactive"],
                fg="#FFFFFF" if selected else COLORS["muted"],
                font=("Segoe UI", 11, "bold") if selected else ("Segoe UI", 10),
                padx=26 if selected else 16,
                pady=11 if selected else 7,
            )
        for container in self._containers:
            container.pack_forget()
        self._containers[index].pack(fill="both", expand=True)

    # ------------------------------------------------------------------ state
    def set_active_db(self, path: str | None):
        """Activate a database by its file path (None clears the selection)."""
        if path:
            path = os.path.abspath(path)
            self.db_path = path
            self.active_db = self.db_service.get_name(path)
            self.parts_service = PartNumberService(path)
        else:
            self.db_path = None
            self.active_db = None
            self.parts_service = None
        self._save_last_db()
        self.refresh_all()

    def _save_last_db(self):
        cfg = config.load_config()
        cfg["last_db"] = self.db_path
        config.save_config(cfg)

    def _restore_last_db(self):
        path = config.load_config().get("last_db")
        if path and self.db_service.exists(path):
            self.set_active_db(path)

    # ------------------------------------------------------------------ refresh
    def refresh_all(self):
        summaries = self.db_service.list_databases()
        self._summary_by_name = {s.name: s.path for s in summaries}
        self.db_combo.configure(values=list(self._summary_by_name))
        self.db_combo_var.set(self.active_db or "")
        self.databases_panel.refresh()
        self.manage_panel.refresh()
        self.create_panel.update_preview()
        self._update_chip_and_prefix()

    def _update_chip_and_prefix(self):
        if self.db_path:
            prefixes = self.db_service.get_prefixes(self.db_path)
            self.prefix_status.config(
                text=f"Assembly {prefixes.get('Assembly')} · "
                     f"Part {prefixes.get('Part')} · "
                     f"Standard {prefixes.get('Standard')}")
            self.db_chip.config(text=f"Database: {self.active_db}")
        else:
            self.prefix_status.config(text="No database selected")
            self.db_chip.config(text="Database: —")

    def _on_combo_select(self):
        path = self._summary_by_name.get(self.db_combo_var.get())
        if path:
            self.set_active_db(path)

    # ------------------------------------------------------------------ actions
    def new_database(self):
        NewDatabaseDialog(self.root, self)

    def open_database(self):
        name = self.databases_panel.selected_name() or self.db_combo_var.get()
        path = self._summary_by_name.get(name)
        if not path:
            messagebox.showinfo("No Selection", "Select a database to open.",
                                parent=self.root)
            return
        self.set_active_db(path)
        self.select_tab(1)

    def import_database(self):
        path = filedialog.askopenfilename(
            parent=self.root, title="Import a Part Number Manager database",
            filetypes=[("Database", "*.db"), ("All files", "*.*")])
        if not path:
            return
        try:
            self.db_service.import_database(path)
        except ValueError as exc:
            messagebox.showerror("Import Failed", str(exc), parent=self.root)
            return
        self.set_active_db(path)
        self.select_tab(1)
        messagebox.showinfo("Database Imported",
                            f"'{self.active_db}' imported and opened.\n"
                            f"Numbering continues from the last part number.",
                            parent=self.root)

    def export_database(self):
        path = None
        name = self.databases_panel.selected_name()
        if name:
            path = self._summary_by_name.get(name)
        if path is None:
            path = self.db_path
        if not path:
            messagebox.showinfo("No Selection",
                                "Select a database to export.", parent=self.root)
            return
        dest = filedialog.asksaveasfilename(
            parent=self.root, title="Export Database (backup)",
            defaultextension=".db", initialfile=os.path.basename(path),
            filetypes=[("Database", "*.db")])
        if not dest:
            return
        try:
            self.db_service.export_database(path, dest)
        except Exception as exc:  # pragma: no cover
            messagebox.showerror("Export Failed", f"Could not export:\n{exc}",
                                 parent=self.root)
            return
        messagebox.showinfo("Export Complete",
                            f"Database exported to:\n{dest}", parent=self.root)

    def delete_database(self):
        name = self.databases_panel.selected_name()
        path = self._summary_by_name.get(name) if name else None
        if not path:
            messagebox.showinfo("No Selection", "Select a database to delete.",
                                parent=self.root)
            return
        count = next((s.part_count for s in self.db_service.list_databases()
                      if s.path == path), 0)
        ok = messagebox.askyesno(
            "Delete Database",
            f"Delete database '{name}'?\nIt contains {count} part(s).\n"
            f"This cannot be undone.", parent=self.root)
        if not ok:
            return
        self.db_service.delete(path)
        if self.db_path == path:
            self.set_active_db(None)
        self.refresh_all()

    def create_part(self):
        if self.parts_service is None:
            messagebox.showinfo("No Database", "Please select or create a database "
                                               "first.", parent=self.root)
            return
        name = self.create_panel.name_entry.get().strip()
        part_type = self.create_panel.type_var.get()
        material = self.create_panel.material_entry.get().strip()
        desc = self.create_panel.desc_text.get("1.0", "end").strip()
        if not name:
            messagebox.showwarning("Missing Input", "Please enter a part name.",
                                   parent=self.root)
            return
        try:
            number = self.parts_service.create(name, part_type, material, desc)
        except ValueError as exc:
            messagebox.showerror("Error", str(exc), parent=self.root)
            return
        except Exception as exc:  # pragma: no cover
            messagebox.showerror("Error", f"Failed to create part number:\n{exc}",
                                 parent=self.root)
            return
        # Inline, copyable result (no popup)
        self.create_panel.show_result(
            f"{number}  ·  {name}  ·  {part_type}  ·  {material or '—'}")
        self.create_panel.clear_fields()
        self.create_panel.update_preview()
        self.refresh_all()

    def modify_part(self):
        if self.parts_service is None:
            return
        numbers = self.manage_panel.selected_part_numbers()
        if not numbers:
            messagebox.showinfo("No Selection", "Please select part(s) to modify.",
                                parent=self.root)
            return
        parts = [self.parts_service.get(n) for n in numbers]
        parts = [p for p in parts if p is not None]
        if not parts:
            messagebox.showerror("Error", "Selected part(s) not found.",
                                parent=self.root)
            self.refresh_all()
            return
        ModifyDialog(self.root, parts, self.db_path,
                     on_saved=self.manage_panel.refresh)

    def delete_part(self):
        if self.parts_service is None:
            return
        numbers = self.manage_panel.selected_part_numbers()
        if not numbers:
            messagebox.showinfo("No Selection", "Please select part(s) to delete.",
                                parent=self.root)
            return
        ok = messagebox.askyesno(
            "Confirm Delete",
            f"Delete {len(numbers)} selected part number(s)?\n\n"
            + "\n".join(numbers)
            + "\n\nThis cannot be undone.", parent=self.root)
        if not ok:
            return
        for number in numbers:
            self.parts_service.delete(number)
        self.refresh_all()

    def export_parts(self):
        if self.parts_service is None:
            messagebox.showinfo("No Database", "Please select a database first.",
                                parent=self.root)
            return
        default_name = (f"{self.active_db}_"
                        f"{datetime.date.today().strftime('%Y%m%d')}.xlsx")
        path = filedialog.asksaveasfilename(
            parent=self.root, title="Export Parts to Excel",
            defaultextension=".xlsx", initialfile=default_name,
            filetypes=[("Excel Workbook", "*.xlsx")])
        if not path:
            return
        try:
            count = export_parts_to_excel(self.parts_service.search(""), path)
        except Exception as exc:  # pragma: no cover
            messagebox.showerror("Export Failed", f"Could not export:\n{exc}",
                                 parent=self.root)
            return
        messagebox.showinfo("Export Complete",
                            f"Exported {count} part(s) to:\n{path}", parent=self.root)
