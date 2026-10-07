"""UI panels: Connect, Projects, Create Part Number, Manage Parts.

Built to match the Part Number Manager V1.0 look and feel. Each panel is placed
into a container frame owned by the main window and delegates actions back to
the application controller (``app``).
"""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from .. import config
from .dialogs import (CreateUserDialog, ModifyDialog, NewProjectDialog,
                      UserManagementDialog)
from .theme import COLORS


def _card(parent: tk.Misc) -> tk.Frame:
    """A white 'card' frame with a light border."""
    return tk.Frame(parent, bg=COLORS["card"], highlightbackground=COLORS["border"],
                    highlightthickness=1)


def _field_row(inner: ttk.Frame, row: int, label: str, var: tk.StringVar,
               show: str | None = None, width: int = 34, hint: str = ""):
    """A labelled field in the two-column card grid. Returns the next row."""
    ttk.Label(inner, text=label, style="Field.TLabel").grid(
        row=row, column=0, sticky="w", pady=4)
    frame = ttk.Frame(inner, style="Card.TFrame")
    frame.grid(row=row, column=1, sticky="ew", padx=(14, 0), pady=4)
    frame.columnconfigure(0, weight=1)
    ttk.Entry(frame, textvariable=var, width=width, show=show,
              style="Modern.TEntry").grid(row=0, column=0, sticky="ew")
    if hint:
        ttk.Label(frame, text=hint, style="Hint.TLabel").grid(
            row=1, column=0, sticky="w")
    return row + 1


class ConnectPanel:
    """Tab 0: log in / log out of the central server."""

    def __init__(self, container: tk.Misc, app):
        self.app = app
        self.container = container
        self._build()

    def _build(self):
        card = _card(self.container)
        card.pack(fill="both", expand=True)
        outer = ttk.Frame(card, style="Card.TFrame", padding=20)
        outer.pack(fill="both", expand=True)
        outer.columnconfigure(0, weight=1)

        ttk.Label(outer, text="Connect to Central Server",
                  style="Section.TLabel").grid(row=0, column=0, sticky="w",
                                               pady=(0, 6))
        ttk.Label(outer, text="Step 1: connect to the server. "
                              "Step 2: log in with your account.",
                  style="Hint.TLabel").grid(row=1, column=0, sticky="w",
                                            pady=(0, 12))

        # ---- 1. server connection card
        server = _card(outer)
        server.grid(row=2, column=0, sticky="ew")
        s_inner = ttk.Frame(server, style="Card.TFrame", padding=16)
        s_inner.pack(fill="both", expand=True)
        s_inner.columnconfigure(1, weight=1)
        ttk.Label(s_inner, text="1 · Server Connection",
                  style="Section.TLabel").grid(row=0, column=0, columnspan=2,
                                               sticky="w", pady=(0, 10))

        self._host = tk.StringVar(value=config.DEFAULT_HOST)
        self._port = tk.StringVar(value=str(config.DEFAULT_PORT))
        self._db = tk.StringVar(value=config.DEFAULT_DB)
        self._user = tk.StringVar()
        self._pass = tk.StringVar()
        self._remember = tk.BooleanVar(value=False)

        saved_user, saved_pass = config.get_remembered_login()
        if saved_user:
            self._user.set(saved_user)
            self._pass.set(saved_pass)
            self._remember.set(True)

        srow = 1
        srow = _field_row(s_inner, srow, "Server (Host)", self._host, width=28)
        srow = _field_row(s_inner, srow, "Port", self._port, width=28)
        srow = _field_row(s_inner, srow, "Database", self._db, width=28)
        sbtn = ttk.Frame(s_inner, style="Card.TFrame")
        sbtn.grid(row=srow, column=0, columnspan=2, sticky="w", pady=(12, 0))
        self.connect_btn = ttk.Button(sbtn, text="Connect to Server",
                                      style="Primary.TButton",
                                      command=self._connect)
        self.connect_btn.pack(side="left", padx=(0, 8))
        self.disconnect_btn = ttk.Button(sbtn, text="Disconnect",
                                         style="Secondary.TButton",
                                         command=self._disconnect,
                                         state="disabled")
        self.disconnect_btn.pack(side="left")

        # ---- 2. account login card
        account = _card(outer)
        account.grid(row=3, column=0, sticky="ew", pady=(12, 0))
        a_inner = ttk.Frame(account, style="Card.TFrame", padding=16)
        a_inner.pack(fill="both", expand=True)
        a_inner.columnconfigure(1, weight=1)
        ttk.Label(a_inner, text="2 · Account Login",
                  style="Section.TLabel").grid(row=0, column=0, columnspan=2,
                                               sticky="w", pady=(0, 10))

        arow = 1
        arow = _field_row(a_inner, arow, "Username", self._user, width=28)
        arow = _field_row(a_inner, arow, "Password", self._pass, show="*",
                          width=28)
        tk.Checkbutton(a_inner, text="Remember username & password",
                       variable=self._remember, bg=COLORS["card"],
                       fg=COLORS["text"], activebackground=COLORS["card"],
                       activeforeground=COLORS["text"],
                       font=("Segoe UI", 9), selectcolor=COLORS["card"],
                       highlightthickness=0, cursor="hand2").grid(
            row=arow, column=1, sticky="w", padx=(14, 0), pady=(2, 0))
        arow += 1
        abtn = ttk.Frame(a_inner, style="Card.TFrame")
        abtn.grid(row=arow, column=0, columnspan=2, sticky="w", pady=(12, 0))
        self.login_btn = ttk.Button(abtn, text="Login", style="Primary.TButton",
                                    command=self._login, state="disabled")
        self.login_btn.pack(side="left", padx=(0, 8))
        self.logout_btn = ttk.Button(abtn, text="Logout",
                                     style="Secondary.TButton",
                                     command=self._logout, state="disabled")
        self.logout_btn.pack(side="left")
        self.create_btn = ttk.Button(abtn, text="Create Account…",
                                     style="Secondary.TButton",
                                     command=self._create_account,
                                     state="disabled")
        self.create_btn.pack(side="left", padx=(8, 8))
        self.manage_btn = ttk.Button(abtn, text="Manage Users…",
                                     style="Secondary.TButton",
                                     command=self._manage_users,
                                     state="disabled")
        self.manage_btn.pack(side="left")

        # ---- status
        status = _card(outer)
        status.grid(row=4, column=0, sticky="ew", pady=(12, 0))
        status.columnconfigure(1, weight=1)
        ttk.Label(status, text="Status", style="Hint.TLabel").grid(
            row=0, column=0, sticky="w", padx=(16, 8), pady=12)
        self._result = ttk.Entry(status, state="readonly", width=60,
                                 style="Result.TEntry")
        self._result.grid(row=0, column=1, sticky="ew", padx=(0, 16), pady=12)

    def _connect(self):
        host = self._host.get().strip()
        port_s = self._port.get().strip()
        db = self._db.get().strip()
        if not host or not db:
            self._show("Host and Database are required.", "error")
            return
        try:
            port = int(port_s)
        except ValueError:
            self._show("Port must be a number.", "error")
            return
        try:
            self.app.connect_to_server(host, port, db)
        except Exception as exc:
            self._show(f"Connection failed: {exc}", "error")
            return
        self.set_state(True, False, False)
        self._show("Connected to server. Enter your account and log in.", "ok")

    def _disconnect(self):
        self.app.disconnect()
        self.set_state(False, False, False)
        self._show("Disconnected from server.", "ok")

    def _login(self):
        user = self._user.get().strip()
        password = self._pass.get()
        if not user or not password:
            self._show("Username and Password are required.", "error")
            return
        try:
            username, role = self.app.login(user, password)
        except Exception as exc:
            self._show(f"Login failed: {exc}", "error")
            return
        if self._remember.get():
            config.set_remembered_login(username, password)
        else:
            config.clear_remembered_login()
        self.set_state(True, True, role == "admin")
        self._show(f"Logged in as {username} ({role}).", "ok")

    def _logout(self):
        self.app.logout()
        self.set_state(True, False, False)
        self._show("Logged out. You are still connected to the server.", "ok")

    def set_state(self, connected: bool, logged_in: bool, admin: bool):
        self.connect_btn.configure(
            state="disabled" if connected else "normal")
        self.disconnect_btn.configure(
            state="normal" if connected else "disabled")
        acct = "normal" if connected else "disabled"
        self.login_btn.configure(
            state=acct if not logged_in else "disabled")
        self.logout_btn.configure(
            state="normal" if logged_in else "disabled")
        self.create_btn.configure(state=acct)
        self.manage_btn.configure(
            state="normal" if (logged_in and admin) else "disabled")

    def _create_account(self):
        if not self.app.is_connected():
            self._show("Connect to the server first.", "error")
            return
        CreateUserDialog(
            self.app.root, self.app,
            on_created=lambda u: self._show(
                f"User '{u}' created (role: user).", "ok"))

    def _manage_users(self):
        if not self.app.is_admin():
            self._show("Admin access required to manage users.", "error")
            return
        UserManagementDialog(self.app.root, self.app)

    def _show(self, text, kind):
        self._result.configure(state="normal")
        self._result.delete(0, "end")
        self._result.insert(0, text)
        self._result.configure(state="readonly")
        fg = COLORS["primary_dark"] if kind == "ok" else COLORS["danger"]
        self._result.configure(foreground=fg)


class ProjectsPanel:
    """Tab 1: list projects on the server; create / open / delete."""

    def __init__(self, container: tk.Misc, app):
        self.app = app
        self.container = container
        self._build()

    def _build(self):
        card = _card(self.container)
        card.pack(fill="both", expand=True)
        inner = ttk.Frame(card, style="Card.TFrame", padding=(20, 20, 20, 10))
        inner.pack(fill="both", expand=True)
        inner.columnconfigure(0, weight=1)

        ttk.Label(inner, text="Projects", style="Section.TLabel").grid(
            row=0, column=0, sticky="w", pady=(0, 6))
        ttk.Label(inner, text="Each project is an independent engineering "
                              "database with its own leading numbers and sequence.",
                  style="Hint.TLabel").grid(row=1, column=0, sticky="w", pady=(0, 12))

        table_frame = _card(inner)
        table_frame.grid(row=2, column=0, sticky="nsew")
        table_frame.columnconfigure(0, weight=1)
        table_frame.rowconfigure(0, weight=1)

        columns = ("name", "assembly", "part", "standard", "count", "created")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings",
                                 selectmode="browse")
        headers = {
            "name": ("Project Name", 200, "w"),
            "assembly": ("Assembly", 80, "center"),
            "part": ("Part", 80, "center"),
            "standard": ("Standard", 80, "center"),
            "count": ("Parts", 60, "center"),
            "created": ("Created", 100, "center"),
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
        self.tree.bind("<Double-1>", lambda e: self.app.open_project())

        actions = ttk.Frame(inner, style="Card.TFrame")
        actions.grid(row=3, column=0, sticky="w", pady=(12, 0))
        self.new_btn = ttk.Button(actions, text="New Project…",
                                  style="Primary.TButton",
                                  command=self._new_project)
        self.new_btn.pack(side="left", padx=(0, 8))
        ttk.Button(actions, text="Open Selected", style="Secondary.TButton",
                   command=self.app.open_project).pack(side="left", padx=(0, 8))
        self.del_btn = ttk.Button(actions, text="Delete Selected",
                                  style="Danger.TButton",
                                  command=self._delete_project)
        self.del_btn.pack(side="left")

        self.status = ttk.Label(inner, text="", style="Status.TLabel")
        self.status.grid(row=4, column=0, sticky="w", pady=(8, 0))

        result = tk.Frame(inner, bg=COLORS["success_light"],
                          highlightbackground="#A7F3D0", highlightthickness=1)
        result.grid(row=5, column=0, sticky="ew", pady=(10, 0))
        result.columnconfigure(1, weight=1)
        ttk.Label(result, text="Message", style="Hint.TLabel").grid(
            row=0, column=0, sticky="w", padx=(16, 8), pady=12)
        self._result = ttk.Entry(result, width=48, state="readonly",
                                 style="Result.TEntry")
        self._result.grid(row=0, column=1, sticky="ew", padx=(0, 16), pady=12)

        inner.rowconfigure(2, weight=1)
        self.tree.tag_configure("odd", background=COLORS["row_alt"])
        self.tree.tag_configure("even", background=COLORS["card"])

    def refresh(self):
        for i in self.tree.get_children():
            self.tree.delete(i)
        if not self.app.connected:
            self.status.config(text="Not connected.")
            return
        if not self.app.is_logged_in():
            self.status.config(text="Log in to view projects.")
            return
        projects = self.app.project_list()
        for idx, proj in enumerate(projects):
            tag = "even" if idx % 2 == 0 else "odd"
            self.tree.insert("", "end", tags=(tag,),
                             values=(proj.name, proj.prefixes["Assembly"],
                                     proj.prefixes["Part"],
                                     proj.prefixes["Standard"],
                                     self.app.project_part_count(proj.id),
                                     proj.created_date))
        self.status.config(text=f"{len(projects)} project(s) on the server.")

    def selected_name(self) -> str | None:
        sel = self.tree.selection()
        if not sel:
            return None
        return self.tree.item(sel[0], "values")[0]

    def select_name(self, name: str | None) -> None:
        for item in self.tree.get_children():
            if self.tree.item(item, "values")[0] == name:
                self.tree.selection_set(item)
                self.tree.focus(item)
                self.tree.see(item)
                break

    def _new_project(self):
        if not self.app.is_admin():
            self._show("Admin access required to create a project.", "error")
            return
        NewProjectDialog(self.app.root, self.app)

    def _delete_project(self):
        if not self.app.is_admin():
            self._show("Admin access required to delete a project.", "error")
            return
        name = self.selected_name()
        if not name:
            self._show("Select a project to delete.", "error")
            return
        proj = self.app.get_project_by_name(name)
        if proj is None:
            return
        if not messagebox.askyesno(
                "Delete Project",
                f"Delete project '{name}' and ALL its parts?\n"
                "This cannot be undone.", parent=self.container):
            return
        self.app.delete_project_by_id(proj.id)
        self.refresh()
        self._show(f"Project '{name}' deleted from the server.", "ok")

    def _show(self, text, kind):
        self._result.configure(state="normal")
        self._result.delete(0, "end")
        self._result.insert(0, text)
        self._result.configure(state="readonly")
        fg = COLORS["primary_dark"] if kind == "ok" else COLORS["danger"]
        self._result.configure(foreground=fg)

    def show_result(self, text: str):
        self._result.configure(state="normal")
        self._result.delete(0, "end")
        self._result.insert(0, text)
        self._result.configure(state="readonly")

    def set_admin(self, admin: bool):
        state = "normal" if admin else "disabled"
        self.new_btn.configure(state=state)
        self.del_btn.configure(state=state)


class CreatePanel:
    """Tab 2: create a new part number in the active project."""

    def __init__(self, container: tk.Misc, app):
        self.app = app
        self.container = container
        self._build()

    def _build(self):
        card = _card(self.container)
        card.pack(fill="both", expand=True)
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
        self.name_entry = ttk.Entry(inner, width=48, style="Modern.TEntry")
        self.name_entry.grid(row=1, column=1, sticky="ew", padx=(14, 0), pady=(4, 2))

        ttk.Label(inner, text="Material", style="Field.TLabel").grid(
            row=2, column=0, sticky="w", pady=(10, 2))
        self.material_entry = ttk.Entry(inner, width=48, style="Modern.TEntry")
        self.material_entry.grid(row=2, column=1, sticky="ew", padx=(14, 0), pady=(10, 2))

        ttk.Label(inner, text="Description", style="Field.TLabel").grid(
            row=3, column=0, sticky="nw", pady=(10, 2))
        self.desc_text = tk.Text(inner, width=48, height=4, wrap="word",
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

        result = tk.Frame(inner, bg=COLORS["success_light"],
                          highlightbackground="#A7F3D0", highlightthickness=1)
        result.grid(row=6, column=0, columnspan=2, sticky="ew", pady=(14, 6))
        result.columnconfigure(1, weight=1)
        ttk.Label(result, text="Created", style="Hint.TLabel").grid(
            row=0, column=0, sticky="nw", padx=(16, 8), pady=12)

        grid = tk.Frame(result, bg=COLORS["success_light"])
        grid.grid(row=0, column=1, sticky="ew", padx=(0, 16), pady=10)
        for col in range(4):
            grid.columnconfigure(col, weight=1)

        self._created_entries = []
        for col, (label, attr, width) in enumerate([
                ("Part Number", "created_pn_entry", 16),
                ("Part Name", "created_name_entry", 30),
                ("Material", "created_material_entry", 18),
                ("Description", "created_desc_entry", 26)]):
            blk = tk.Frame(grid, bg=COLORS["success_light"])
            blk.grid(row=0, column=col, sticky="n", padx=(0, 16))
            ttk.Label(blk, text=f"{label} (click to copy)",
                      style="Hint.TLabel").pack(anchor="w")
            entry = ttk.Entry(blk, width=width, state="readonly",
                              style="Result.TEntry")
            entry.pack(fill="x", pady=(2, 0))
            entry.bind("<Button-1>",
                       lambda e, a=attr: self._copy_value(
                           getattr(self, a).get()))
            setattr(self, attr, entry)
            self._created_entries.append(entry)

    def update_preview(self, *args):
        if not self.app.connected or not self.app.current_project:
            self.number_preview.config(text="—")
            return
        try:
            self.number_preview.config(
                text=self.app.peek_number(self.type_var.get()))
        except Exception:
            self.number_preview.config(text="")

    def clear_fields(self):
        self.name_entry.delete(0, "end")
        self.material_entry.delete(0, "end")
        self.desc_text.delete("1.0", "end")
        self.name_entry.focus_set()

    def show_result(self, number: str, name: str, material: str = "",
                    description: str = ""):
        values = (number, name, material, description)
        for entry in self._created_entries:
            entry.configure(state="normal")
        for entry, value in zip(self._created_entries, values):
            entry.delete(0, "end")
            entry.insert(0, value)
        for entry in self._created_entries:
            entry.configure(state="readonly")

    def _copy_pn(self, _event=None):
        self._copy_value(self.created_pn_entry.get())

    def _copy_name(self, _event=None):
        self._copy_value(self.created_name_entry.get())

    def _copy_value(self, text: str):
        if not text:
            return
        top = self.container.winfo_toplevel()
        top.clipboard_clear()
        top.clipboard_append(text)
        top.update_idletasks()

    def focus_name(self):
        self.name_entry.focus_set()


class ManagePanel:
    """Tab 3: search / modify / delete / export parts of the active project."""

    def __init__(self, container: tk.Misc, app):
        self.app = app
        self.container = container
        self._build()

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

    def show_all(self):
        self.search_var.set("")
        self.refresh()

    def selected_part_numbers(self) -> list[str]:
        """Numbers of all selected rows (supports Shift-range / Ctrl-multi)."""
        return [self.tree.item(i, "values")[0] for i in self.tree.selection()]

    def refresh(self):
        for i in self.tree.get_children():
            self.tree.delete(i)
        if not self.app.connected or not self.app.current_project:
            self.status.config(text="No project selected.")
            return
        parts = self.app.get_parts(self.search_var.get())
        for idx, part in enumerate(parts):
            tag = "even" if idx % 2 == 0 else "odd"
            self.tree.insert("", "end", tags=(tag,),
                             values=(part.part_number, part.part_name,
                                     part.part_type, part.material,
                                     part.description, part.created_date))
        self.status.config(text=f"{len(parts)} part(s) found in "
                                f"'{self.app.current_project.name}'.")
