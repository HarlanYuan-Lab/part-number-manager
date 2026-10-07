"""Modal dialogs: create a new project, and modify one or more parts."""

from __future__ import annotations

import random

import tkinter as tk
from tkinter import messagebox, simpledialog, ttk

from PIL import Image, ImageDraw, ImageFont, ImageTk

from .. import config
from .theme import COLORS


def _card(parent: tk.Misc) -> tk.Frame:
    return tk.Frame(parent, bg=COLORS["card"], highlightbackground=COLORS["border"],
                    highlightthickness=1)


def _center(dialog: tk.Toplevel, parent: tk.Misc) -> None:
    dialog.update_idletasks()
    x = parent.winfo_rootx() + (parent.winfo_width() - dialog.winfo_width()) // 2
    y = parent.winfo_rooty() + (parent.winfo_height() - dialog.winfo_height()) // 2
    dialog.geometry(f"+{x}+{y}")


class NewProjectDialog(tk.Toplevel):
    """Create a new project on the server with per-type leading numbers."""

    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.title("New Project")
        self.resizable(False, False)
        self.configure(bg=COLORS["bg"])
        self.transient(parent)
        self.grab_set()

        card = _card(self)
        card.pack(fill="both", expand=True, padx=12, pady=12)
        body = ttk.Frame(card, style="Card.TFrame", padding=22)
        body.pack(fill="both", expand=True)
        body.columnconfigure(1, weight=1)

        ttk.Label(body, text="Create a New Project", style="Section.TLabel").grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 6))
        ttk.Label(body, text="Enter a name, the suffix digit count, and a "
                             "prefix for each part type. The first number of "
                             "each type is <prefix>00…001.",
                  style="Hint.TLabel").grid(row=1, column=0, columnspan=2,
                                            sticky="w", pady=(0, 14))

        ttk.Label(body, text="Project Name *", style="Field.TLabel").grid(
            row=2, column=0, sticky="w", pady=4)
        self.name_var = tk.StringVar()
        ttk.Entry(body, textvariable=self.name_var, width=30,
                  style="Modern.TEntry").grid(row=2, column=1, sticky="ew",
                                              padx=(14, 0), pady=4)

        ttk.Label(body, text="Suffix Digits", style="Field.TLabel").grid(
            row=3, column=0, sticky="w", pady=4)
        self.length_var = tk.StringVar(value="")
        ttk.Entry(body, textvariable=self.length_var, width=10,
                  style="Modern.TEntry").grid(row=3, column=1, sticky="w",
                                              padx=(14, 0), pady=4)

        self.prefix_vars = {}
        for i, part_type in enumerate(config.PART_TYPES):
            ttk.Label(body, text=f"  {part_type} prefix",
                      style="Field.TLabel").grid(row=4 + i, column=0, sticky="w",
                                                 pady=4)
            var = tk.StringVar(value="")
            self.prefix_vars[part_type] = var
            ttk.Entry(body, textvariable=var, width=10,
                      style="Modern.TEntry").grid(row=4 + i, column=1, sticky="w",
                                                  padx=(14, 0), pady=4)

        buttons = ttk.Frame(body, style="Card.TFrame")
        buttons.grid(row=7, column=0, columnspan=2, sticky="e", pady=(18, 0))
        ttk.Button(buttons, text="Create & Open", style="Primary.TButton",
                   command=self._create).pack(side="left", padx=(0, 8))
        ttk.Button(buttons, text="Cancel", style="Secondary.TButton",
                   command=self.destroy).pack(side="left")

        self.bind("<Return>", lambda e: self._create())
        self.bind("<Escape>", lambda e: self.destroy())
        _center(self, parent)

    def _create(self):
        name = self.name_var.get().strip()
        length = self.length_var.get()
        prefixes = {t: self.prefix_vars[t].get() for t in config.PART_TYPES}
        try:
            self.app.create_project_from_dialog(name, prefixes, length)
        except ValueError as exc:
            messagebox.showerror("Invalid Project", str(exc), parent=self)
            return
        except Exception as exc:  # pragma: no cover
            messagebox.showerror("Error", f"Could not create project:\n{exc}",
                                 parent=self)
            return
        self.destroy()


class ModifyDialog(tk.Toplevel):
    """Edit name / material / description of one part or a batch of parts."""

    def __init__(self, parent, app, parts):
        super().__init__(parent)
        self.app = app
        self.parts = list(parts)
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
            ttk.Label(body, text="Values below will be applied to all selected "
                                 "parts.", style="Hint.TLabel").grid(
                row=2, column=0, columnspan=2, sticky="w", pady=(0, 14))
            row = 3
        else:
            ttk.Label(body, text=f"Modify Part  {first.part_number}",
                      style="Section.TLabel").grid(row=0, column=0, columnspan=2,
                                                   sticky="w", pady=(0, 14))
            row = 1
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
        if self.multi:
            payload = {
                "numbers": [p.part_number for p in self.parts],
                "name": self.name_var.get().strip(),
                "material": self.material_var.get().strip(),
                "description": self.desc_text.get("1.0", "end").strip(),
            }
        else:
            part = self.parts[0]
            payload = {
                "old_number": part.part_number,
                "new_number": self.number_var.get().strip() or part.part_number,
                "name": self.name_var.get().strip(),
                "material": self.material_var.get().strip(),
                "description": self.desc_text.get("1.0", "end").strip(),
                "part_type": part.part_type,
            }
        if not payload["name"]:
            messagebox.showwarning("Missing Input", "Part name must not be empty.",
                                   parent=self)
            return
        try:
            label = self.app.modify_part_save(payload)
        except ValueError as exc:
            messagebox.showerror("Invalid Input", str(exc), parent=self)
            return
        except Exception as exc:  # pragma: no cover
            messagebox.showerror("Error", f"Could not save changes:\n{exc}",
                                 parent=self)
            return
        self.grab_release()
        messagebox.showinfo("Saved", label, parent=self.master)
        self.destroy()


class CreateUserDialog(tk.Toplevel):
    """Create a new account (anyone can use it after connecting).
    Requires entering an image verification code."""

    def __init__(self, parent, app, on_created=None):
        super().__init__(parent)
        self.app = app
        self.on_created = on_created
        self.title("Create Account")
        self.resizable(False, False)
        self.configure(bg=COLORS["bg"])
        self.transient(parent)
        self.grab_set()

        card = _card(self)
        card.pack(fill="both", expand=True, padx=12, pady=12)
        body = ttk.Frame(card, style="Card.TFrame", padding=22)
        body.pack(fill="both", expand=True)
        body.columnconfigure(1, weight=1)

        ttk.Label(body, text="Create a New Account", style="Section.TLabel").grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 6))
        ttk.Label(body, text="New accounts are created with 'user' permission. "
                             "An admin can change roles later.",
                  style="Hint.TLabel").grid(row=1, column=0, columnspan=2,
                                            sticky="w", pady=(0, 14))

        ttk.Label(body, text="Username *", style="Field.TLabel").grid(
            row=2, column=0, sticky="w", pady=4)
        self.user_var = tk.StringVar()
        ttk.Entry(body, textvariable=self.user_var, width=30,
                  style="Modern.TEntry").grid(row=2, column=1, sticky="ew",
                                              padx=(14, 0), pady=4)

        ttk.Label(body, text="Password *", style="Field.TLabel").grid(
            row=3, column=0, sticky="w", pady=4)
        self.pass_var = tk.StringVar()
        ttk.Entry(body, textvariable=self.pass_var, width=30, show="*",
                  style="Modern.TEntry").grid(row=3, column=1, sticky="ew",
                                              padx=(14, 0), pady=4)

        ttk.Label(body, text="Confirm Password *", style="Field.TLabel").grid(
            row=4, column=0, sticky="w", pady=4)
        self.confirm_var = tk.StringVar()
        ttk.Entry(body, textvariable=self.confirm_var, width=30, show="*",
                  style="Modern.TEntry").grid(row=4, column=1, sticky="ew",
                                              padx=(14, 0), pady=4)

        ttk.Label(body, text="Verification Code *", style="Field.TLabel").grid(
            row=5, column=0, sticky="w", pady=4)
        code_row = ttk.Frame(body, style="Card.TFrame")
        code_row.grid(row=5, column=1, sticky="ew", padx=(14, 0), pady=4)
        self._code_img = tk.Label(code_row, width=150, height=44, bg="#F4F7FB",
                                  relief="ridge")
        self._code_img.pack(side="left")
        ttk.Button(code_row, text="Refresh", style="Secondary.TButton",
                   command=self._new_code).pack(side="left", padx=(10, 0))
        self._code_var = tk.StringVar()
        ttk.Entry(code_row, textvariable=self._code_var, width=10,
                  style="Modern.TEntry").pack(side="left", padx=(10, 0))
        self._code = ""
        self._new_code()

        buttons = ttk.Frame(body, style="Card.TFrame")
        buttons.grid(row=6, column=0, columnspan=2, sticky="e", pady=(18, 0))
        ttk.Button(buttons, text="Create", style="Primary.TButton",
                   command=self._create).pack(side="left", padx=(0, 8))
        ttk.Button(buttons, text="Cancel", style="Secondary.TButton",
                   command=self.destroy).pack(side="left")

        self.bind("<Return>", lambda e: self._create())
        self.bind("<Escape>", lambda e: self.destroy())
        _center(self, parent)

    def _new_code(self):
        chars = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
        self._code = "".join(random.choice(chars) for _ in range(5))
        img = Image.new("RGB", (150, 44), (244, 247, 251))
        draw = ImageDraw.Draw(img)
        try:
            font = ImageFont.truetype("arial.ttf", 26)
        except Exception:
            font = ImageFont.load_default()
        for _ in range(6):  # noise lines
            x1, y1 = random.randint(0, 150), random.randint(0, 44)
            x2, y2 = random.randint(0, 150), random.randint(0, 44)
            draw.line((x1, y1, x2, y2),
                      fill=(random.randint(120, 220),) * 3, width=1)
        x = 8
        for ch in self._code:
            draw.text((x, random.randint(4, 12)), ch, font=font,
                      fill=(random.randint(20, 90), random.randint(20, 90),
                            random.randint(20, 90)))
            x += 27
        self._photo = ImageTk.PhotoImage(img)
        self._code_img.config(image=self._photo)

    def _create(self):
        username = self.user_var.get().strip()
        password = self.pass_var.get()
        confirm = self.confirm_var.get()
        entered = self._code_var.get().strip()
        if self._code.upper() != entered.upper():
            messagebox.showwarning("Verification",
                                   "Incorrect verification code. Try again.",
                                   parent=self)
            self._new_code()
            self._code_var.set("")
            return
        if password != confirm:
            messagebox.showwarning("Mismatch", "Passwords do not match.",
                                   parent=self)
            return
        try:
            self.app.create_user(username, password)
        except ValueError as exc:
            messagebox.showerror("Create Account", str(exc), parent=self)
            return
        except Exception as exc:  # pragma: no cover
            messagebox.showerror("Error", f"Could not create account:\n{exc}",
                                 parent=self)
            return
        self.grab_release()
        if self.on_created:
            self.on_created(username)
        self.destroy()


class UserManagementDialog(tk.Toplevel):
    """Admin panel: list users, change roles, reset passwords, delete users."""

    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.current_user = app.current_user
        self.title("User Management")
        self.geometry("820x600")
        self.configure(bg=COLORS["bg"])
        self.transient(parent)
        self.grab_set()

        card = _card(self)
        card.pack(fill="both", expand=True, padx=12, pady=12)
        inner = ttk.Frame(card, style="Card.TFrame", padding=18)
        inner.pack(fill="both", expand=True)
        inner.columnconfigure(0, weight=1)

        ttk.Label(inner, text="User Management", style="Section.TLabel").grid(
            row=0, column=0, sticky="w", pady=(0, 6))
        ttk.Label(inner, text="Manage accounts and set permissions "
                              "(Admin / User).",
                  style="Hint.TLabel").grid(row=1, column=0, sticky="w",
                                            pady=(0, 10))

        table = _card(inner)
        table.grid(row=2, column=0, sticky="nsew")
        table.rowconfigure(0, weight=1)
        table.columnconfigure(0, weight=1)
        cols = ("username", "role", "created")
        self.tree = ttk.Treeview(table, columns=cols, show="headings",
                                 selectmode="browse")
        for col, text, w, a in (("username", "Username", 190, "w"),
                                ("role", "Role", 100, "center"),
                                ("created", "Created", 110, "center")):
            self.tree.heading(col, text=text)
            self.tree.column(col, width=w, anchor=a)
        vsb = ttk.Scrollbar(table, orient="vertical", command=self.tree.yview,
                            style="Vertical.TScrollbar")
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        inner.rowconfigure(2, weight=1)

        actions = ttk.Frame(inner, style="Card.TFrame")
        actions.grid(row=3, column=0, sticky="ew", pady=(12, 0))
        ttk.Button(actions, text="Create User…", style="Primary.TButton",
                   command=self._create).pack(side="left", padx=(0, 8))
        ttk.Label(actions, text="Role:", style="Field.TLabel").pack(
            side="left", padx=(12, 4))
        self.role_var = tk.StringVar(value="user")
        ttk.Combobox(actions, textvariable=self.role_var,
                     values=("admin", "user"), state="readonly", width=8,
                     style="TCombobox").pack(side="left")
        ttk.Button(actions, text="Apply Role", style="Secondary.TButton",
                   command=self._apply_role).pack(side="left", padx=(6, 8))
        ttk.Button(actions, text="Reset Password", style="Secondary.TButton",
                   command=self._reset).pack(side="left", padx=(0, 8))
        ttk.Button(actions, text="Delete", style="Danger.TButton",
                   command=self._delete).pack(side="left")

        self.status = ttk.Label(inner, text="", style="Status.TLabel")
        self.status.grid(row=4, column=0, sticky="w", pady=(8, 0))

        _center(self, parent)
        self.refresh()

    def refresh(self):
        for i in self.tree.get_children():
            self.tree.delete(i)
        users = self.app.list_users()
        for u in users:
            self.tree.insert("", "end",
                             values=(u["username"], u["role"],
                                     u["created_date"]))
        self.status.config(text=f"{len(users)} user(s).")

    def _selected(self) -> str | None:
        sel = self.tree.selection()
        if not sel:
            return None
        return self.tree.item(sel[0], "values")[0]

    def _create(self):
        def created(username):
            self.refresh()
            self.status.config(text=f"User '{username}' created (role: user).")
        CreateUserDialog(self, self.app, on_created=created)

    def _apply_role(self):
        username = self._selected()
        if not username:
            messagebox.showinfo("No Selection", "Select a user.", parent=self)
            return
        role = self.role_var.get()
        try:
            self.app.set_user_role(username, role)
        except Exception as exc:
            messagebox.showerror("Error", str(exc), parent=self)
            return
        self.refresh()
        self.status.config(text=f"Role of '{username}' set to {role}.")

    def _reset(self):
        username = self._selected()
        if not username:
            messagebox.showinfo("No Selection", "Select a user.", parent=self)
            return
        new = simpledialog.askstring("Reset Password",
                                     f"New password for '{username}':",
                                     show="*", parent=self)
        if not new:
            return
        try:
            self.app.reset_password(username, new)
        except Exception as exc:
            messagebox.showerror("Error", str(exc), parent=self)
            return
        self.status.config(text=f"Password for '{username}' reset.")

    def _delete(self):
        username = self._selected()
        if not username:
            messagebox.showinfo("No Selection", "Select a user.", parent=self)
            return
        if username == self.current_user:
            messagebox.showwarning(
                "Cannot Delete",
                "You cannot delete the account you are logged in with.",
                parent=self)
            return
        if not messagebox.askyesno("Delete User",
                                   f"Delete account '{username}'?",
                                   parent=self):
            return
        try:
            self.app.delete_user(username)
        except Exception as exc:
            messagebox.showerror("Error", str(exc), parent=self)
            return
        self.refresh()
        self.status.config(text=f"User '{username}' deleted.")
