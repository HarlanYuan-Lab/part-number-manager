"""Modal dialogs: create a new database and modify an existing part."""

from __future__ import annotations

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from .. import config
from ..services import PartNumberService
from .theme import COLORS


def _card(parent: tk.Misc) -> tk.Frame:
    return tk.Frame(parent, bg=COLORS["card"], highlightbackground=COLORS["border"],
                    highlightthickness=1)


def _center(dialog: tk.Toplevel, parent: tk.Misc) -> None:
    dialog.update_idletasks()
    x = parent.winfo_rootx() + (parent.winfo_width() - dialog.winfo_width()) // 2
    y = parent.winfo_rooty() + (parent.winfo_height() - dialog.winfo_height()) // 2
    dialog.geometry(f"+{x}+{y}")


class NewDatabaseDialog(tk.Toplevel):
    """Collect a database name and the leading numbers for each part type."""

    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.title("New Database")
        self.resizable(False, False)
        self.configure(bg=COLORS["bg"])
        self.transient(parent)
        self.grab_set()

        card = _card(self)
        card.pack(fill="both", expand=True, padx=12, pady=12)
        body = ttk.Frame(card, style="Card.TFrame", padding=22)
        body.pack(fill="both", expand=True)
        body.columnconfigure(1, weight=1)

        ttk.Label(body, text="Create a New Database", style="Section.TLabel").grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 6))
        ttk.Label(body, text="Enter a name and choose the leading number for each "
                             "part type. Numbers are 6 digits: <leading><sequence>.",
                  style="Hint.TLabel").grid(row=1, column=0, columnspan=2,
                                            sticky="w", pady=(0, 14))

        ttk.Label(body, text="Database Name *", style="Field.TLabel").grid(
            row=2, column=0, sticky="w", pady=4)
        self.name_var = tk.StringVar()
        ttk.Entry(body, textvariable=self.name_var, width=30,
                  style="Modern.TEntry").grid(row=2, column=1, sticky="ew",
                                              padx=(14, 0), pady=4)

        ttk.Label(body, text="Save Location", style="Field.TLabel").grid(
            row=3, column=0, sticky="w", pady=4)
        folder_row = ttk.Frame(body, style="Card.TFrame")
        folder_row.grid(row=3, column=1, sticky="ew", padx=(14, 0), pady=4)
        folder_row.columnconfigure(0, weight=1)
        self.folder_var = tk.StringVar(value=config.databases_dir())
        ttk.Entry(folder_row, textvariable=self.folder_var, width=22,
                  style="Modern.TEntry").grid(row=0, column=0, sticky="ew",
                                              padx=(0, 6))
        ttk.Button(folder_row, text="Browse…", style="Secondary.TButton",
                   command=self._browse_folder).grid(row=0, column=1)

        self.prefix_vars = {}
        for i, part_type in enumerate(config.PART_TYPES):
            ttk.Label(body, text=f"  {part_type} leading number",
                      style="Field.TLabel").grid(row=4 + i, column=0, sticky="w",
                                                 pady=4)
            var = tk.StringVar(value=config.DEFAULT_PREFIXES[part_type])
            self.prefix_vars[part_type] = var
            ttk.Entry(body, textvariable=var, width=10,
                      style="Modern.TEntry").grid(row=4 + i, column=1, sticky="w",
                                                  padx=(14, 0), pady=4)

        ttk.Label(body, text="Tip: typical setup is Assembly=8, Part=2, Standard=9.",
                  style="Hint.TLabel").grid(row=8, column=0, columnspan=2,
                                            sticky="w", pady=(10, 0))

        buttons = ttk.Frame(body, style="Card.TFrame")
        buttons.grid(row=9, column=0, columnspan=2, sticky="e", pady=(18, 0))
        ttk.Button(buttons, text="Create & Open", style="Primary.TButton",
                   command=self._create).pack(side="left", padx=(0, 8))
        ttk.Button(buttons, text="Cancel", style="Secondary.TButton",
                   command=self.destroy).pack(side="left")

        self.bind("<Return>", lambda e: self._create())
        self.bind("<Escape>", lambda e: self.destroy())
        _center(self, parent)
        self.name_var.trace_add("write", lambda *a: None)

    def _browse_folder(self):
        folder = filedialog.askdirectory(
            parent=self, title="Choose where to save the database",
            initialdir=self.folder_var.get() or config.databases_dir())
        if folder:
            self.folder_var.set(folder)

    def _create(self):
        name = self.name_var.get().strip()
        prefixes = {t: self.prefix_vars[t].get() for t in config.PART_TYPES}
        folder = self.folder_var.get().strip() or config.databases_dir()
        try:
            path = self.app.db_service.create(name, prefixes, folder)
        except ValueError as exc:
            messagebox.showerror("Invalid Database", str(exc), parent=self)
            return
        except Exception as exc:  # pragma: no cover
            messagebox.showerror("Error", f"Could not create database:\n{exc}",
                                 parent=self)
            return
        self.app.set_active_db(path)
        self.app.select_tab(1)  # jump to Create Part Number
        self.app.databases_panel.show_result(
            f"{name}  ·  created  ·  {path}")
        self.destroy()


class ModifyDialog(tk.Toplevel):
    """Edit name / material / description of one part or a batch of parts.

    ``parts`` may be a single Part or a list of Parts; when it is a list, the
    entered values are applied to every selected part on save.
    """

    def __init__(self, parent, parts, db_path, on_saved):
        super().__init__(parent)
        if isinstance(parts, (list, tuple)):
            self.parts = list(parts)
        else:
            self.parts = [parts]
        self.db_path = db_path
        self.on_saved = on_saved
        self._service = PartNumberService(db_path)
        first = self.parts[0]
        self.multi = len(self.parts) > 1
        self.title(f"Modify Part {first.part_number}" if not self.multi
                   else f"Modify {len(self.parts)} Parts")
        self.resizable(False, False)
        self.configure(bg=COLORS["bg"])
        self.transient(parent)
        self.grab_set()

        card = _card(self)
        card.pack(fill="both", expand=True, padx=12, pady=12)
        body = ttk.Frame(card, style="Card.TFrame", padding=20)
        body.pack(fill="both", expand=True)
        body.columnconfigure(1, weight=1)

        if self.multi:
            numbers = ", ".join(p.part_number for p in self.parts)
            ttk.Label(body, text=f"Modify {len(self.parts)} selected parts",
                      style="Section.TLabel").grid(row=0, column=0, columnspan=2,
                                                   sticky="w", pady=(0, 14))
            ttk.Label(body, text=numbers, style="Hint.TLabel").grid(
                row=1, column=0, columnspan=2, sticky="w", pady=(0, 10))
            ttk.Label(body,
                      text="Values below will be applied to all selected parts.",
                      style="Hint.TLabel").grid(row=2, column=0, columnspan=2,
                                                sticky="w", pady=(0, 14))
            row = 3
        else:
            ttk.Label(body, text=f"Modify Part  {first.part_number}",
                      style="Section.TLabel").grid(row=0, column=0, columnspan=2,
                                                   sticky="w", pady=(0, 14))
            row = 1
            # Editable part number (uniqueness is enforced on save)
            ttk.Label(body, text="Part Number", style="Field.TLabel").grid(
                row=row, column=0, sticky="w", pady=4)
            self.number_var = tk.StringVar(value=first.part_number)
            ttk.Entry(body, textvariable=self.number_var, width=42,
                      style="Modern.TEntry").grid(row=row, column=1, sticky="ew",
                                                  padx=(14, 0), pady=4)
            row += 1
            for label, value in (("Part Type", first.part_type),
                                 ("Created Date", first.created_date)):
                ttk.Label(body, text=label, style="Field.TLabel").grid(
                    row=row, column=0, sticky="w", pady=4)
                ttk.Label(body, text=value, style="Field.TLabel",
                          foreground=COLORS["muted"]).grid(row=row, column=1,
                                                           sticky="w",
                                                           padx=(14, 0), pady=4)
                row += 1

        ttk.Label(body, text="Part Name", style="Field.TLabel").grid(
            row=row, column=0, sticky="w", pady=4)
        self.name_var = tk.StringVar(value=first.part_name)
        ttk.Entry(body, textvariable=self.name_var, width=42,
                  style="Modern.TEntry").grid(row=row, column=1, sticky="ew",
                                              padx=(14, 0), pady=4)
        row += 1

        ttk.Label(body, text="Material", style="Field.TLabel").grid(
            row=row, column=0, sticky="w", pady=4)
        self.material_var = tk.StringVar(value=first.material)
        ttk.Entry(body, textvariable=self.material_var, width=42,
                  style="Modern.TEntry").grid(row=row, column=1, sticky="ew",
                                              padx=(14, 0), pady=4)
        row += 1

        ttk.Label(body, text="Description", style="Field.TLabel").grid(
            row=row, column=0, sticky="nw", pady=4)
        self.desc_text = tk.Text(body, width=40, height=4, wrap="word",
                                 font=("Segoe UI", 10), bg="#FFFFFF", relief="flat",
                                 padx=8, pady=8, highlightbackground=COLORS["border"],
                                 highlightcolor=COLORS["primary"], highlightthickness=1)
        self.desc_text.grid(row=row, column=1, sticky="ew", padx=(14, 0), pady=4)
        self.desc_text.insert("1.0", first.description)
        row += 1

        buttons = ttk.Frame(body, style="Card.TFrame")
        buttons.grid(row=row, column=0, columnspan=2, sticky="e", pady=(16, 0))
        ttk.Button(buttons, text="Save", style="Primary.TButton",
                   command=self._save).pack(side="left", padx=(0, 8))
        ttk.Button(buttons, text="Cancel", style="Secondary.TButton",
                   command=self.destroy).pack(side="left")

        self.bind("<Return>", lambda e: self._save())
        self.bind("<Escape>", lambda e: self.destroy())
        _center(self, parent)

    def _save(self):
        new_name = self.name_var.get().strip()
        new_material = self.material_var.get().strip()
        new_desc = self.desc_text.get("1.0", "end").strip()
        if not new_name:
            messagebox.showwarning("Missing Input", "Part name must not be empty.",
                                   parent=self)
            return
        try:
            if self.multi:
                for part in self.parts:
                    self._service.update(part.part_number, new_name, new_material,
                                         new_desc)
                final_numbers = [p.part_number for p in self.parts]
            else:
                part = self.parts[0]
                new_number = self.number_var.get().strip() or part.part_number
                final_number = self._service.update_part(
                    part.part_number, new_number, new_name, new_material,
                    new_desc, part.part_type)
                final_numbers = [final_number]
                if final_number != new_number:
                    self._renumbered_note = (
                        f"The number {new_number} was already taken; "
                        f"this part was assigned {final_number} instead.")
        except ValueError as exc:
            messagebox.showerror("Invalid Input", str(exc), parent=self)
            return
        except Exception as exc:  # pragma: no cover
            messagebox.showerror("Error", f"Could not save changes:\n{exc}",
                                 parent=self)
            return
        if self.on_saved:
            self.on_saved()
        if self.multi:
            label = f"{len(self.parts)} parts updated"
        else:
            label = f"Part {final_numbers[0]} updated"
            if getattr(self, "_renumbered_note", None):
                label += "\n\n" + self._renumbered_note
        self.grab_release()
        # Show the confirmation while the dialog is still alive, then close it.
        messagebox.showinfo("Saved", label, parent=self.master)
        self.destroy()
