"""Main application window (controller) for Part Number Manager V2.

Mirrors the V1.0 layout (blue header, project toolbar, custom growing tab bar,
card-based panels) while connecting to the central PostgreSQL server and adding
an account-based login (admin / user accounts, see part_manager.auth).
"""

from __future__ import annotations

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from .. import config
from ..auth import UserService
from ..db import ConnectionManager
from ..exporter import export_parts_to_excel
from ..services import PartNumberService, ProjectService
from .dialogs import ModifyDialog, NewProjectDialog
from .panels import ConnectPanel, CreatePanel, ManagePanel, ProjectsPanel
from .theme import COLORS, setup_styles

TAB_LABELS = (("Connect to Server", 0), ("Projects", 1),
              ("Create Part Number", 2), ("Manage Parts", 3))


class PartNumberApp:
    """The single application window; owns state and coordinates the panels."""

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title(f"{config.APP_NAME} - Central Server")
        self.root.geometry("1380x920")
        self.root.minsize(1200, 760)
        self.root.minsize(960, 640)
        self.root.configure(bg=COLORS["bg"])

        # --- server-side state ---
        self.db: ConnectionManager | None = None
        self.user_service: UserService | None = None
        self.current_user: str | None = None
        self.role: str | None = None
        self.project_service: ProjectService | None = None
        self.current_project = None
        self.parts_service: PartNumberService | None = None
        self._summary_by_name: dict[str, object] = {}

        setup_styles(root)
        self._build_header()
        self._build_toolbar()
        self._build_tabs()
        self.refresh_all()

    # ---------------------------------------------------------------- properties
    @property
    def connected(self) -> bool:
        return self.db is not None and self.db.connected

    def is_admin(self) -> bool:
        return self.role == "admin"

    # ------------------------------------------------------------------ header
    def _build_header(self):
        header = ttk.Frame(self.root, style="Header.TFrame", padding=(22, 12))
        header.pack(fill="x")
        left = ttk.Frame(header, style="Header.TFrame")
        left.pack(side="left")
        ttk.Label(left, text=config.APP_NAME, style="HeaderTitle.TLabel").pack(
            anchor="w")
        ttk.Label(left, text="Centralized part number management "
                             "(PostgreSQL server)",
                  style="HeaderSub.TLabel").pack(anchor="w", pady=(1, 0))
        self.user_chip = tk.Label(header, text="Not connected", bg="#FFFFFF",
                                  fg=COLORS["primary"],
                                  font=("Segoe UI", 9, "bold"), padx=12, pady=4)
        self.user_chip.pack(side="right", padx=(10, 4))

    # ------------------------------------------------------------------ toolbar
    def _build_toolbar(self):
        bar = tk.Frame(self.root, bg=COLORS["card"],
                       highlightbackground=COLORS["border"], highlightthickness=1)
        bar.pack(fill="x", padx=16, pady=(12, 6))
        inner = ttk.Frame(bar, style="Card.TFrame", padding=(14, 10))
        inner.pack(fill="x")

        ttk.Label(inner, text="Project", style="Field.TLabel").pack(side="left")
        self.project_combo_var = tk.StringVar()
        self.project_combo = ttk.Combobox(inner, state="readonly", width=22,
                                          style="TCombobox",
                                          textvariable=self.project_combo_var)
        self.project_combo.pack(side="left", padx=(10, 8))
        self.project_combo.bind("<<ComboboxSelected>>",
                                lambda e: self._on_combo_select())

        self.new_btn = ttk.Button(inner, text="New…", style="Primary.TButton",
                                  command=self.new_project)
        self.new_btn.pack(side="left", padx=4)
        self.import_btn = ttk.Button(inner, text="Import…",
                                     style="Secondary.TButton",
                                     command=self.import_v1)
        self.import_btn.pack(side="left", padx=4)
        self.del_btn = ttk.Button(inner, text="Delete", style="Danger.TButton",
                                  command=self.delete_project)
        self.del_btn.pack(side="left", padx=4)
        ttk.Button(inner, text="Export…", style="Secondary.TButton",
                   command=self.export_project).pack(side="left", padx=4)
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

        containers = [tk.Frame(self._content, bg=COLORS["bg"])
                      for _ in TAB_LABELS]
        self.connect_panel = ConnectPanel(containers[0], self)
        self.projects_panel = ProjectsPanel(containers[1], self)
        self.create_panel = CreatePanel(containers[2], self)
        self.manage_panel = ManagePanel(containers[3], self)
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
            holder.configure(bg=COLORS["primary"] if selected
                             else COLORS["tab_inactive"])
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

    # ------------------------------------------------------------------ server
    def is_connected(self) -> bool:
        return self.db is not None

    def is_logged_in(self) -> bool:
        return self.current_user is not None

    def connect_to_server(self, host: str, port: int, dbname: str) -> None:
        mgr = ConnectionManager()
        mgr.connect(host, port, dbname, config.DEFAULT_USER,
                    config.DEFAULT_PASSWORD)
        self.db = mgr
        self.user_service = UserService(mgr)
        self.user_service.ensure_default_users()
        self.project_service = ProjectService(mgr)
        self.current_project = None
        self.current_user = None
        self.role = None
        self.parts_service = None
        self.set_admin_state()
        self.refresh_all()

    def login(self, user: str, password: str) -> tuple[str, str]:
        if not self.is_connected():
            raise ValueError("Connect to the server first.")
        username, role = self.user_service.login(user, password)
        self.current_user = username
        self.role = role
        self.set_admin_state()
        self.refresh_all()
        return username, role

    def logout(self) -> None:
        """Clear the logged-in account but keep the server connection."""
        self.current_user = None
        self.role = None
        self.current_project = None
        self.set_admin_state()
        self.refresh_all()

    def disconnect(self) -> None:
        if self.db is not None:
            self.db.close()
        self.db = None
        self.user_service = None
        self.project_service = None
        self.parts_service = None
        self.current_user = None
        self.role = None
        self.current_project = None
        self.set_admin_state()
        self.refresh_all()

    # ------------------------------------------------------------------ users
    def create_user(self, username: str, password: str) -> None:
        if self.user_service is None:
            raise ValueError("Not connected to server.")
        self.user_service.create_user(username, password)

    def list_users(self) -> list:
        if not self.is_admin():
            raise ValueError("Admin access required.")
        if self.user_service is None:
            return []
        return self.user_service.list_users()

    def set_user_role(self, username: str, role: str) -> None:
        if not self.is_admin():
            raise ValueError("Admin access required.")
        self.user_service.set_role(username, role)

    def reset_password(self, username: str, new_password: str) -> None:
        if not self.is_admin():
            raise ValueError("Admin access required.")
        self.user_service.reset_password(username, new_password)

    def delete_user(self, username: str) -> None:
        if not self.is_admin():
            raise ValueError("Admin access required.")
        self.user_service.delete_user(username)

    def set_admin_state(self):
        admin = self.is_admin()
        state = "normal" if admin else "disabled"
        self.new_btn.configure(state=state)
        self.import_btn.configure(state=state)
        self.del_btn.configure(state=state)
        self.projects_panel.set_admin(admin)
        self.connect_panel.set_state(self.is_connected(),
                                     self.is_logged_in(), admin)

    # ------------------------------------------------------------------ state
    def set_active_project(self, name: str):
        proj = self.get_project_by_name(name)
        if proj is None:
            return
        self.current_project = proj
        self.parts_service = PartNumberService(self.db, proj)
        self.create_panel.update_preview()
        self.manage_panel.refresh()
        self._update_chip_and_prefix()

    def clear_active_if(self, name: str):
        if self.current_project and self.current_project.name == name:
            self.current_project = None
            self.parts_service = None

    def _on_combo_select(self):
        name = self.project_combo_var.get()
        if name:
            self.set_active_project(name)

    # ------------------------------------------------------------------ refresh
    def refresh_all(self):
        if not self.connected or self.project_service is None:
            self.project_combo.configure(values=[])
            self.project_combo_var.set("")
            self.current_project = None
            self.parts_service = None
            self.user_chip.config(text="Not connected")
            self.connect_panel.set_state(False, False, False)
            self.projects_panel.refresh()
            self.manage_panel.refresh()
            self.create_panel.update_preview()
            self.prefix_status.config(text="No project selected")
            self.set_admin_state()
            return
        if not self.is_logged_in():
            # Connected but not logged in: show no database information.
            self.current_project = None
            self._summary_by_name = {}
            self.project_combo.configure(values=[])
            self.project_combo_var.set("")
            self.user_chip.config(text="Not logged in")
            self.connect_panel.set_state(True, False, False)
            self.projects_panel.refresh()
            self.manage_panel.refresh()
            self.create_panel.update_preview()
            self.prefix_status.config(text="No project selected")
            self.set_admin_state()
            return
        summaries = self.project_service.list_projects()
        self._summary_by_name = {p.name: p.id for p in summaries}
        self.project_combo.configure(values=list(self._summary_by_name))
        self.project_combo_var.set(
            self.current_project.name if self.current_project else "")
        self.user_chip.config(text=f"User: {self.current_user} ({self.role})"
                              if self.current_user else "Not logged in")
        self.connect_panel.set_state(True, self.is_logged_in(),
                                     self.is_admin())
        self.projects_panel.refresh()
        if self.current_project:
            self.projects_panel.select_name(self.current_project.name)
        self.manage_panel.refresh()
        self.create_panel.update_preview()
        self._update_chip_and_prefix()
        self.set_admin_state()

    def _update_chip_and_prefix(self):
        if self.current_project:
            prefixes = self.current_project.prefixes
            self.prefix_status.config(
                text=f"Assembly {prefixes.get('Assembly')} · "
                     f"Part {prefixes.get('Part')} · "
                     f"Standard {prefixes.get('Standard')}")
        else:
            self.prefix_status.config(text="No project selected")

    # ------------------------------------------------------------------ projects
    def project_list(self):
        if not self.connected or self.project_service is None:
            return []
        return self.project_service.list_projects()

    def project_part_count(self, project_id: int) -> int:
        if not self.connected or self.project_service is None:
            return 0
        return self.project_service.part_count(project_id)

    def get_project_by_name(self, name: str):
        if not self.connected or self.project_service is None:
            return None
        return self.project_service.get_by_name(name)

    def create_project_from_dialog(self, name: str, prefixes: dict,
                                   length=None):
        if not self.is_admin():
            raise ValueError("Admin access required to create a project.")
        if self.project_service is None:
            raise ValueError("Not connected to server.")
        if length is None or str(length).strip() == "":
            length = config.NUMBER_LENGTH
        proj = self.project_service.create(name, prefixes, length)
        self.set_active_project(proj.name)
        self.select_tab(1)
        self.projects_panel.show_result(
            f"{name}  ·  created on server  ·  now active")
        self.refresh_all()
        return proj

    def new_project(self):
        if not self.is_admin():
            messagebox.showinfo("Permission",
                                "Admin access required to create a project.",
                                parent=self.root)
            return
        NewProjectDialog(self.root, self)

    def import_v1(self):
        if not self.is_admin():
            messagebox.showinfo("Permission",
                                "Admin access required to import a project.",
                                parent=self.root)
            return
        if not self.connected or self.project_service is None:
            messagebox.showinfo("Not Connected", "Log in to the server first.",
                                parent=self.root)
            return
        path = filedialog.askopenfilename(
            parent=self.root, title="Import a V1.0 database file",
            filetypes=[("Part Number Manager database", "*.db"),
                       ("All files", "*.*")])
        if not path:
            return
        try:
            from .. import local_transfer
            proj, count, seqs = local_transfer.import_v1_to_server(
                self.db, self.project_service, path)
        except ValueError as exc:
            messagebox.showerror("Import Failed", str(exc), parent=self.root)
            return
        except Exception as exc:  # pragma: no cover
            messagebox.showerror("Import Failed", f"Could not import:\n{exc}",
                                 parent=self.root)
            return
        self.set_active_project(proj.name)
        self.project_combo_var.set(proj.name)
        self.refresh_all()
        self.select_tab(2)
        messagebox.showinfo(
            "Database Imported",
            f"'{proj.name}' imported ({count} part(s)).\n"
            f"Numbering continues from the last number "
            f"(Assembly {seqs['Assembly']}, Part {seqs['Part']}, "
            f"Standard {seqs['Standard']}).",
            parent=self.root)

    def export_project(self):
        if not self.connected or self.current_project is None:
            messagebox.showinfo("No Project", "Select a project to export.",
                                parent=self.root)
            return
        path = filedialog.asksaveasfilename(
            parent=self.root, title="Export project to a V1.0 database file",
            defaultextension=".db",
            initialfile=f"{self.current_project.name}.db",
            filetypes=[("Part Number Manager database", "*.db")])
        if not path:
            return
        try:
            parts = self._require_parts().search("")
            from .. import local_transfer
            dest = local_transfer.export_project_to_v1(
                self.db, self.current_project, parts, path)
        except Exception as exc:  # pragma: no cover
            messagebox.showerror("Export Failed", f"Could not export:\n{exc}",
                                 parent=self.root)
            return
        messagebox.showinfo(
            "Export Complete",
            f"Exported {len(parts)} part(s) to:\n{dest}", parent=self.root)

    def open_project(self):
        name = self.projects_panel.selected_name() or self.project_combo_var.get()
        proj = self.get_project_by_name(name)
        if not proj:
            messagebox.showinfo("No Selection", "Select a project to open.",
                                parent=self.root)
            return
        self.set_active_project(proj.name)
        self.project_combo_var.set(proj.name)
        self.select_tab(2)
        self.create_panel.focus_name()

    def delete_project(self):
        if not self.is_admin():
            messagebox.showinfo("Permission",
                                "Admin access required to delete a project.",
                                parent=self.root)
            return
        name = self.projects_panel.selected_name()
        if not name and self.current_project:
            name = self.current_project.name
        proj = self.get_project_by_name(name) if name else None
        if not proj:
            messagebox.showinfo("No Selection", "Select a project to delete.",
                                parent=self.root)
            return
        ok = messagebox.askyesno(
            "Delete Project",
            f"Delete project '{name}'?\nIt contains "
            f"{self.project_part_count(proj.id)} part(s).\n"
            f"This cannot be undone.", parent=self.root)
        if not ok:
            return
        self._delete(proj)

    def delete_project_by_id(self, project_id: int):
        """Delete by id (already confirmed by the calling panel)."""
        if not self.is_admin():
            return
        proj = self.project_service.get(project_id)
        if proj is not None:
            self._delete(proj)

    def _delete(self, proj):
        self.project_service.delete(proj.id)
        self.clear_active_if(proj.name)
        self.refresh_all()

    # -------------------------------------------------------------- part numbers
    def _require_parts(self) -> PartNumberService:
        if not self.connected or self.parts_service is None:
            raise ValueError("No project selected. Connect and pick a project.")
        return self.parts_service

    def peek_number(self, part_type: str) -> str:
        return self._require_parts().peek_number(part_type)

    def create_part(self):
        if not self.is_logged_in():
            messagebox.showinfo("Login Required",
                                "Please log in to create part numbers.",
                                parent=self.root)
            return
        if not self.connected or self.current_project is None:
            messagebox.showinfo("No Project",
                                "Please select a project first.",
                                parent=self.root)
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
            number = self._require_parts().create(name, part_type, material, desc)
        except ValueError as exc:
            messagebox.showerror("Error", str(exc), parent=self.root)
            return
        except Exception as exc:  # pragma: no cover
            messagebox.showerror("Error", f"Failed to create part number:\n{exc}",
                                 parent=self.root)
            return
        self.create_panel.show_result(number, name, material, desc)
        self.create_panel.clear_fields()
        self.create_panel.update_preview()
        self.refresh_all()

    def get_parts(self, keyword: str):
        return self._require_parts().search(keyword)

    def modify_part(self):
        if not self.is_logged_in():
            messagebox.showinfo("Login Required",
                                "Please log in to modify parts.",
                                parent=self.root)
            return
        if not self.connected or self.parts_service is None:
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
        ModifyDialog(self.root, self, parts)

    def modify_part_save(self, payload: dict) -> str:
        if not self.is_logged_in():
            raise ValueError("Please log in to modify parts.")
        svc = self._require_parts()
        if "numbers" in payload:  # batch
            for num in payload["numbers"]:
                svc.update(num, payload["name"], payload["material"],
                           payload["description"])
            self.manage_panel.refresh()
            self.projects_panel.refresh()
            return f"{len(payload['numbers'])} part(s) updated"
        # single
        final = svc.update_part(payload["old_number"], payload["new_number"],
                                payload["name"], payload["material"],
                                payload["description"], payload["part_type"])
        self.manage_panel.refresh()
        self.projects_panel.refresh()
        if final != payload["old_number"]:
            note = (f"The number {payload['new_number']} was already taken; "
                    f"this part was assigned {final} instead.")
            return f"Part {final} updated\n\n{note}"
        return f"Part {final} updated"

    def delete_part(self):
        if not self.is_logged_in():
            messagebox.showinfo("Login Required",
                                "Please log in to delete parts.",
                                parent=self.root)
            return
        if not self.connected or self.parts_service is None:
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
        if not self.is_logged_in():
            messagebox.showinfo("Login Required",
                                "Please log in to export parts.",
                                parent=self.root)
            return
        if not self.connected or self.current_project is None:
            messagebox.showinfo("No Project", "Please select a project first.",
                                parent=self.root)
            return
        path = filedialog.asksaveasfilename(
            parent=self.root, title="Export Parts to Excel",
            defaultextension=".xlsx",
            initialfile=f"{self.current_project.name}_parts.xlsx",
            filetypes=[("Excel Workbook", "*.xlsx")])
        if not path:
            return
        try:
            parts = self._require_parts().search("")
            if not parts:
                raise ValueError("No parts to export.")
            export_parts_to_excel(parts, path,
                                  project_name=self.current_project.name)
        except Exception as exc:  # pragma: no cover
            messagebox.showerror("Export Failed", f"Could not export:\n{exc}",
                                 parent=self.root)
            return
        messagebox.showinfo("Export Complete",
                            f"Exported {len(parts)} part(s) to:\n{path}",
                            parent=self.root)
