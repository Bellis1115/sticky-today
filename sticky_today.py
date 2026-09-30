#!/usr/bin/env python3
"""A tiny Linux desktop sticky note for today's tasks."""

from __future__ import annotations

import json
import calendar
import re
import tkinter as tk
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

APP_NAME = "sticky-today"
DATA_DIR = Path.home() / ".local" / "share" / APP_NAME
DATA_FILE = DATA_DIR / "today.json"
ICON_FILE = Path(__file__).with_name("sticky_today.png")
BG = "#fff7b2"
PANEL = "#fff2a3"
SURFACE = "#f5df7a"
INPUT = "#fffbe0"
TEXT = "#2f2a1d"
MUTED = "#776f52"
ACCENT = "#d28b00"
ACCENT_WARM = "#f5df7a"
BORDER = "#ead67a"
SELECTED = "#f3df79"
FONT = ("Noto Sans CJK SC", 11)
TITLE_FONT = ("Noto Sans CJK SC", 14, "bold")
SMALL_FONT = ("Noto Sans CJK SC", 10)


@dataclass
class Task:
    text: str
    done: bool = False
    date: str = ""


class StickyToday(tk.Tk):
    def __init__(self) -> None:
        super().__init__(className="StickyToday")
        self.title("今日便利贴")
        self.geometry("360x520")
        self.minsize(300, 360)
        self.configure(bg=BG)
        try:
            self._icon_image = tk.PhotoImage(file=str(ICON_FILE))
            self.iconphoto(True, self._icon_image)
        except tk.TclError:
            self._icon_image = None

        self.tasks: list[Task] = []
        self.task_rows: list[tuple[tk.BooleanVar, tk.Frame]] = []
        self.selected_task: Task | None = None
        self.action_buttons: list[tk.Button] = []

        self._build_ui()
        self._load()
        self._render_tasks()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.bind("<Control-s>", lambda _event: self._save(show_status=True))
        self.bind("<Control-n>", lambda _event: self._focus_new_task())

    def _build_ui(self) -> None:
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure(
            "TCombobox",
            fieldbackground=INPUT,
            background=SURFACE,
            foreground=TEXT,
            arrowcolor=ACCENT,
            bordercolor=BORDER,
        )
        header = tk.Frame(self, bg=BG)
        header.pack(fill="x", padx=14, pady=(12, 6))

        tk.Label(header, text="今天要做什么", bg=BG, fg=TEXT, font=TITLE_FONT).pack(side="left")
        entry_row = tk.Frame(self, bg=BG)
        entry_row.pack(fill="x", padx=14, pady=(2, 8))

        self.task_entry = tk.Entry(entry_row, font=FONT, relief="flat", bg=INPUT, fg=TEXT, insertbackground=TEXT)
        self.task_entry.pack(side="left", fill="x", expand=True, ipady=7)
        self.task_entry.bind("<Return>", lambda _event: self._add_task())

        tk.Label(entry_row, text="日期", bg=BG, fg=MUTED, font=SMALL_FONT).pack(side="left", padx=(8, 3))
        self.date_entry = tk.Entry(entry_row, width=11, font=SMALL_FONT, relief="flat", bg=INPUT, fg=TEXT, insertbackground=TEXT)
        self.date_entry.pack(side="left", ipady=6)
        self.date_entry.bind("<Button-1>", lambda _event: self._choose_date(self.date_entry))

        add_button = tk.Button(
            entry_row,
            text="添加",
            command=self._add_task,
            bg=ACCENT,
            fg="white",
            activebackground="#b87500",
            activeforeground="white",
            relief="flat",
            font=SMALL_FONT,
            padx=12,
            pady=5,
        )
        add_button.pack(side="left", padx=(8, 0))

        content_pane = tk.PanedWindow(
            self,
            orient="vertical",
            bg=BG,
            bd=0,
            sashwidth=6,
            sashrelief="raised",
            showhandle=False,
            cursor="sb_v_double_arrow",
        )
        content_pane.pack(fill="both", expand=True, padx=14, pady=(0, 10))

        list_panel = tk.Frame(self, bg=BG)
        content_pane.add(list_panel, minsize=150, stretch="always")
        list_shell = tk.Frame(list_panel, bg=PANEL, highlightthickness=1, highlightbackground=BORDER)
        list_shell.pack(fill="both", expand=True)

        self.tasks_canvas = tk.Canvas(list_shell, bg=PANEL, highlightthickness=0, bd=0)
        self.tasks_canvas.pack(side="left", fill="both", expand=True, padx=(8, 0), pady=8)

        self.tasks_scrollbar = tk.Scrollbar(
            list_shell,
            orient="vertical",
            command=self.tasks_canvas.yview,
            relief="flat",
            bg=PANEL,
            troughcolor=INPUT,
            activebackground=MUTED,
        )
        self.tasks_scrollbar.pack(side="right", fill="y", padx=(0, 4), pady=8)
        self.tasks_canvas.configure(yscrollcommand=self.tasks_scrollbar.set)

        self.tasks_frame = tk.Frame(self.tasks_canvas, bg=PANEL)
        self.tasks_window = self.tasks_canvas.create_window(
            (0, 0),
            window=self.tasks_frame,
            anchor="nw",
        )
        self.tasks_frame.bind("<Configure>", self._update_scroll_region)
        self.tasks_canvas.bind("<Configure>", self._resize_tasks_window)
        self.tasks_canvas.bind("<Enter>", self._bind_mousewheel)
        self.tasks_canvas.bind("<Leave>", self._unbind_mousewheel)

        action_bar = tk.Frame(list_panel, bg=BG)
        action_bar.pack(fill="x", pady=(5, 0))
        for text, command in (
            ("↑ 上移", lambda: self._move_selected(-1)),
            ("↓ 下移", lambda: self._move_selected(1)),
            ("编辑", self._edit_selected),
            ("删除", self._remove_selected),
            ("清除已完成", self._clear_done),
        ):
            button = tk.Button(
                action_bar,
                text=text,
                command=command,
                state="disabled",
                relief="flat",
                bg=SURFACE,
                fg=TEXT,
                activebackground="#edd060",
                font=SMALL_FONT,
                padx=7,
                pady=3,
            )
            button.pack(side="left", padx=(0, 5))
            self.action_buttons.append(button)

        notes_panel = tk.Frame(self, bg=BG)
        content_pane.add(notes_panel, minsize=100, stretch="always")
        notes_header = tk.Frame(notes_panel, bg=BG)
        notes_header.pack(fill="x", pady=(0, 3))
        tk.Label(notes_header, text="随手记", bg=BG, fg=MUTED, font=SMALL_FONT).pack(side="left")
        tk.Button(
            notes_header,
            text="另存为",
            command=self._save_notes_as,
            relief="flat",
            bg=SURFACE,
            fg=TEXT,
            activebackground="#edd060",
            font=SMALL_FONT,
            padx=7,
            pady=2,
        ).pack(side="right")
        notes_shell = tk.Frame(notes_panel, bg=BG)
        notes_shell.pack(fill="both", expand=True)
        self.notes = tk.Text(
            notes_shell,
            height=5,
            wrap="word",
            relief="flat",
            bg=INPUT,
            fg=TEXT,
            insertbackground=TEXT,
            font=FONT,
            padx=8,
            pady=8,
        )
        self.notes.pack(side="left", fill="both", expand=True)
        notes_scrollbar = tk.Scrollbar(
            notes_shell,
            orient="vertical",
            command=self.notes.yview,
            relief="flat",
            bg=PANEL,
            troughcolor=INPUT,
            activebackground=MUTED,
        )
        notes_scrollbar.pack(side="right", fill="y")
        self.notes.configure(yscrollcommand=notes_scrollbar.set)
        self.notes.bind("<KeyRelease>", lambda _event: self._save_debounced())

        footer = tk.Frame(self, bg=BG)
        footer.pack(fill="x", padx=14, pady=(0, 12))

        self.status = tk.Label(footer, text="已自动保存", bg=BG, fg=MUTED, font=SMALL_FONT)
        self.status.pack(side="right")

    def _focus_new_task(self) -> None:
        self.task_entry.focus_set()
        self.task_entry.select_range(0, tk.END)

    def _update_scroll_region(self, _event: tk.Event) -> None:
        self.tasks_canvas.configure(scrollregion=self.tasks_canvas.bbox("all"))

    def _resize_tasks_window(self, event: tk.Event) -> None:
        self.tasks_canvas.itemconfigure(self.tasks_window, width=event.width)
        wraplength = max(120, event.width - 150)
        for _var, row in self.task_rows:
            for child in row.winfo_children():
                if isinstance(child, tk.Label):
                    child.configure(wraplength=wraplength)

    def _bind_mousewheel(self, _event: tk.Event) -> None:
        self.bind_all("<MouseWheel>", self._on_mousewheel)
        self.bind_all("<Button-4>", self._on_mousewheel)
        self.bind_all("<Button-5>", self._on_mousewheel)

    def _unbind_mousewheel(self, _event: tk.Event) -> None:
        self.unbind_all("<MouseWheel>")
        self.unbind_all("<Button-4>")
        self.unbind_all("<Button-5>")

    def _on_mousewheel(self, event: tk.Event) -> None:
        if getattr(event, "num", None) == 4:
            delta = -1
        elif getattr(event, "num", None) == 5:
            delta = 1
        else:
            delta = -1 * int(event.delta / 120)
        self.tasks_canvas.yview_scroll(delta, "units")

    def _add_task(self) -> None:
        text = self.task_entry.get().strip()
        if not text:
            return
        raw_date = self.date_entry.get()
        task_date = self._normalize_date(raw_date)
        if raw_date.strip() and not task_date:
            messagebox.showwarning("日期格式", "请输入 YYYY-MM-DD 格式，例如 2026-09-30。", parent=self)
            return
        self.tasks.append(Task(text=text, date=task_date))
        self.task_entry.delete(0, tk.END)
        self.date_entry.delete(0, tk.END)
        self._render_tasks()
        self._save(show_status=True)

    @staticmethod
    def _normalize_date(value: str) -> str:
        value = value.strip()
        if not value:
            return ""
        value = value.replace("/", "-")
        if not re.fullmatch(r"\d{4}-\d{1,2}-\d{1,2}", value):
            return ""
        try:
            return datetime.strptime(value, "%Y-%m-%d").strftime("%Y-%m-%d")
        except ValueError:
            return ""

    def _choose_date(self, target: tk.Entry) -> None:
        current = self._normalize_date(target.get()) or datetime.now().strftime("%Y-%m-%d")
        year, month, day = map(int, current.split("-"))
        dialog = tk.Toplevel(self)
        dialog.title("选择日期")
        dialog.transient(self)
        dialog.resizable(False, False)
        dialog.configure(bg=BG)

        form = tk.Frame(dialog, bg=BG)
        form.pack(padx=14, pady=14)
        year_var, month_var, day_var = (tk.StringVar(value=str(value)) for value in (year, month, day))
        years = [str(value) for value in range(max(2000, year - 10), year + 11)]
        year_box = ttk.Combobox(form, textvariable=year_var, values=years, state="readonly", width=6)
        month_box = ttk.Combobox(form, textvariable=month_var, values=[str(value) for value in range(1, 13)], state="readonly", width=3)
        day_box = ttk.Combobox(form, textvariable=day_var, state="readonly", width=3)
        year_box.grid(row=0, column=0, padx=2)
        month_box.grid(row=0, column=1, padx=2)
        day_box.grid(row=0, column=2, padx=2)
        tk.Label(form, text="年", bg=BG, fg=MUTED, font=SMALL_FONT).grid(row=1, column=0)
        tk.Label(form, text="月", bg=BG, fg=MUTED, font=SMALL_FONT).grid(row=1, column=1)
        tk.Label(form, text="日", bg=BG, fg=MUTED, font=SMALL_FONT).grid(row=1, column=2)

        def update_days(*_args: object) -> None:
            count = calendar.monthrange(int(year_var.get()), int(month_var.get()))[1]
            days = [str(value) for value in range(1, count + 1)]
            day_box.configure(values=days)
            if int(day_var.get()) > count:
                day_var.set(str(count))

        year_box.bind("<<ComboboxSelected>>", update_days)
        month_box.bind("<<ComboboxSelected>>", update_days)
        update_days()

        def confirm() -> None:
            target.delete(0, tk.END)
            target.insert(0, f"{int(year_var.get()):04d}-{int(month_var.get()):02d}-{int(day_var.get()):02d}")
            dialog.destroy()

        buttons = tk.Frame(form, bg=BG)
        buttons.grid(row=2, column=0, columnspan=3, pady=(12, 0))
        tk.Button(buttons, text="取消", command=dialog.destroy, relief="flat", bg=SURFACE, fg=TEXT).pack(side="right")
        tk.Button(buttons, text="确定", command=confirm, relief="flat", bg=ACCENT, fg="white").pack(side="right", padx=(0, 8))
        dialog.grab_set()

    def _save_notes_as(self) -> None:
        path = filedialog.asksaveasfilename(
            parent=self,
            title="随手记另存为",
            defaultextension=".txt",
            filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")],
        )
        if not path:
            return
        try:
            Path(path).write_text(self.notes.get("1.0", "end-1c"), encoding="utf-8")
        except OSError as exc:
            messagebox.showerror("保存失败", f"无法保存随手记：{exc}")
            return
        self.status.configure(text="随手记已另存")
        self.after(1200, lambda: self.status.configure(text="已自动保存"))

    def _select_task(self, task: Task) -> None:
        if any(item is task for item in self.tasks):
            self.selected_task = task
            self._render_tasks()

    def _selected_index(self) -> int | None:
        if self.selected_task is None:
            return None
        for index, task in enumerate(self.tasks):
            if task is self.selected_task:
                return index
        self.selected_task = None
        return None

    def _update_action_buttons(self) -> None:
        state = "normal" if self._selected_index() is not None else "disabled"
        for button in self.action_buttons:
            button.configure(state=state)

    def _remove_selected(self) -> None:
        index = self._selected_index()
        if index is not None:
            self._remove_task(index)

    def _edit_selected(self) -> None:
        index = self._selected_index()
        if index is not None:
            self._edit_task(index)

    def _move_selected(self, direction: int) -> None:
        index = self._selected_index()
        if index is not None:
            self._move_task(index, direction)

    def _remove_task(self, index: int) -> None:
        if 0 <= index < len(self.tasks):
            if self.tasks[index] is self.selected_task:
                self.selected_task = None
            del self.tasks[index]
            self._render_tasks()
            self._save(show_status=True)

    def _edit_task(self, index: int) -> None:
        if not 0 <= index < len(self.tasks):
            return
        task = self.tasks[index]
        dialog = tk.Toplevel(self)
        dialog.title("编辑任务")
        dialog.transient(self)
        dialog.resizable(True, False)
        dialog.minsize(460, 135)
        dialog.geometry("560x135")
        dialog.configure(bg=BG)

        form = tk.Frame(dialog, bg=BG)
        form.pack(fill="both", expand=True, padx=16, pady=14)
        tk.Label(form, text="内容", bg=BG, fg=MUTED, font=SMALL_FONT).grid(row=0, column=0, sticky="w")
        text_entry = tk.Entry(form, font=FONT, relief="flat", bg=INPUT, fg=TEXT, insertbackground=TEXT)
        text_entry.insert(0, task.text)
        text_entry.grid(row=0, column=1, sticky="ew", padx=(8, 0), ipady=6)
        tk.Label(form, text="日期", bg=BG, fg=MUTED, font=SMALL_FONT).grid(row=1, column=0, sticky="w", pady=(10, 0))
        date_controls = tk.Frame(form, bg=BG)
        date_controls.grid(row=1, column=1, sticky="w", padx=(8, 0), pady=(10, 0))
        date_entry = tk.Entry(date_controls, width=12, font=SMALL_FONT, relief="flat", bg=INPUT, fg=TEXT, insertbackground=TEXT)
        date_entry.insert(0, task.date)
        date_entry.pack(side="left", ipady=4)
        date_entry.bind("<Button-1>", lambda _event: self._choose_date(date_entry))
        form.columnconfigure(1, weight=1)

        def save_edit() -> None:
            text = text_entry.get().strip()
            if not text:
                return
            raw_date = date_entry.get()
            task_date = self._normalize_date(raw_date)
            if raw_date.strip() and not task_date:
                messagebox.showwarning("日期格式", "请输入 YYYY-MM-DD 格式，例如 2026-09-30。", parent=dialog)
                return
            task.text = text
            task.date = task_date
            dialog.destroy()
            self._render_tasks()
            self._save(show_status=True)

        buttons = tk.Frame(form, bg=BG)
        buttons.grid(row=2, column=1, sticky="e", pady=(12, 0))
        tk.Button(buttons, text="取消", command=dialog.destroy, relief="flat", bg=SURFACE, fg=TEXT).pack(side="right")
        tk.Button(buttons, text="保存", command=save_edit, relief="flat", bg=ACCENT, fg="white").pack(side="right", padx=(0, 8))
        text_entry.bind("<Return>", lambda _event: save_edit())
        dialog.protocol("WM_DELETE_WINDOW", dialog.destroy)
        dialog.grab_set()
        text_entry.focus_set()
        text_entry.select_range(0, tk.END)

    def _move_task(self, index: int, direction: int) -> None:
        target = index + direction
        if not (0 <= index < len(self.tasks) and 0 <= target < len(self.tasks)):
            return
        self.tasks[index], self.tasks[target] = self.tasks[target], self.tasks[index]
        self._render_tasks()
        self._save(show_status=True)

    def _clear_done(self) -> None:
        before = len(self.tasks)
        self.tasks = [task for task in self.tasks if not task.done]
        if not any(task is self.selected_task for task in self.tasks):
            self.selected_task = None
        if len(self.tasks) != before:
            self._render_tasks()
            self._save(show_status=True)

    def _toggle_task(self, index: int, var: tk.BooleanVar) -> None:
        if 0 <= index < len(self.tasks):
            task = self.tasks[index]
            self.selected_task = task
            task.done = bool(var.get())
            self.tasks.pop(index)
            if task.done:
                self.tasks.append(task)
            else:
                first_done = next((i for i, item in enumerate(self.tasks) if item.done), len(self.tasks))
                self.tasks.insert(first_done, task)
            self._render_tasks()
            self._save(show_status=True)

    def _render_tasks(self) -> None:
        if not any(task is self.selected_task for task in self.tasks):
            self.selected_task = None
        for child in self.tasks_frame.winfo_children():
            child.destroy()
        self.task_rows.clear()

        if not self.tasks:
            tk.Label(
                self.tasks_frame,
                text="还没有任务，输入后按 Enter 添加。",
                bg=PANEL,
                fg=MUTED,
                font=SMALL_FONT,
            ).pack(anchor="w", pady=8)
            self._update_action_buttons()
            return

        display_tasks = sorted(
            enumerate(self.tasks),
            key=lambda pair: (pair[1].done, pair[1].date == "", pair[1].date or "9999-99-99", pair[0]),
        )
        last_group = None
        last_status = None
        for index, task in display_tasks:
            if task.done != last_status:
                tk.Label(
                    self.tasks_frame,
                    text="已完成" if task.done else "待完成",
                    bg=PANEL,
                    fg=MUTED,
                    font=(FONT[0], FONT[1], "bold"),
                ).pack(anchor="w", pady=(8 if last_status is not None else 2, 2))
                last_status = task.done
                last_group = None
            group = task.date or "未设置日期"
            if group != last_group:
                tk.Label(
                    self.tasks_frame,
                    text=f"日期：{group}",
                    bg=PANEL,
                    fg=MUTED,
                    font=SMALL_FONT,
                ).pack(anchor="w", pady=(6 if last_group is not None else 2, 1))
                last_group = group
            row_bg = SELECTED if task is self.selected_task else PANEL
            row = tk.Frame(self.tasks_frame, bg=row_bg)
            row.pack(fill="x", pady=3)
            row.bind("<Button-1>", lambda _event, t=task: self._select_task(t))

            var = tk.BooleanVar(value=task.done)
            check = tk.Checkbutton(
                row,
                variable=var,
                command=lambda i=index, v=var: self._toggle_task(i, v),
                text="☑" if task.done else "☐",
                indicatoron=0,
                width=2,
                relief="flat",
                font=(FONT[0], 17, "bold"),
                fg=ACCENT if task.done else MUTED,
                bg=row_bg,
                activebackground=row_bg,
                selectcolor=row_bg,
            )
            check.pack(side="left")

            label_font = (FONT[0], FONT[1], "overstrike") if task.done else FONT
            label = tk.Label(
                row,
                text=task.text,
                bg=row_bg,
                fg=MUTED if task.done else TEXT,
                font=label_font,
                anchor="w",
                justify="left",
                wraplength=max(120, self.tasks_canvas.winfo_width() - 150),
            )
            label.pack(side="left", fill="x", expand=True)
            label.bind("<Button-1>", lambda _event, t=task: self._select_task(t))
            self.task_rows.append((var, row))
        self._update_action_buttons()

    def _load(self) -> None:
        if not DATA_FILE.exists():
            return
        try:
            payload = json.loads(DATA_FILE.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            messagebox.showwarning("读取失败", f"无法读取已保存内容：{exc}")
            return

        self.tasks = [
            Task(
                text=str(item.get("text", "")).strip(),
                done=bool(item.get("done", False)),
                date=self._normalize_date(str(item.get("date", item.get("time", "")))),
            )
            for item in payload.get("tasks", [])
            if str(item.get("text", "")).strip()
        ]
        self.notes.delete("1.0", tk.END)
        self.notes.insert("1.0", str(payload.get("notes", "")))

    def _save_debounced(self) -> None:
        if hasattr(self, "_save_job"):
            self.after_cancel(self._save_job)
        self._save_job = self.after(400, self._save)

    def _save(self, show_status: bool = False) -> None:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        payload = {
            "tasks": [{"text": task.text, "done": task.done, "date": task.date} for task in self.tasks],
            "notes": self.notes.get("1.0", "end-1c"),
        }
        DATA_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        if show_status:
            self.status.configure(text="已保存")
            self.after(1200, lambda: self.status.configure(text="已自动保存"))

    def _on_close(self) -> None:
        self._save()
        self.destroy()


if __name__ == "__main__":
    StickyToday().mainloop()
