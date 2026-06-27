#!/usr/bin/env python3
"""
PDFごとのページ設定CSVをGUIで編集するツール
"""
from __future__ import annotations

import tkinter as tk
from pathlib import Path
from threading import Thread
from tkinter import filedialog, messagebox, ttk

from config import DATA_DIR
from main import process_pdf
from page_config import PageConfig, default_pages_config, load_pages_config, save_pages_config


class PageConfigEditor:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("納品書OCR ページ設定")
        self.root.geometry("1080x700")
        self.root.minsize(980, 640)

        self.current_pdf_path: Path | None = None
        self.pages_config: list[PageConfig] = []
        self.selected_index: int | None = None
        self.is_running = False

        self.pdf_path_var = tk.StringVar(value="PDFを選択すると設定がここに表示されます")
        self.status_var = tk.StringVar(value="待機中")
        self.selected_pdf_var = tk.StringVar(value="未選択")
        self.page_count_var = tk.StringVar(value="0")
        self.multiple_count_var = tk.StringVar(value="0")
        self.rotate_count_var = tk.StringVar(value="0")
        self.selection_var = tk.StringVar(value="未選択")

        self.page_var = tk.StringVar()
        self.is_multiple_var = tk.BooleanVar(value=False)
        self.rotate_clockwise_var = tk.BooleanVar(value=False)

        self._configure_style()
        self._build_ui()
        self._bind_shortcuts()
        self._update_summary()
        self._update_action_state()

    def _configure_style(self) -> None:
        self.root.configure(bg="#f3f4f6")

        style = ttk.Style()
        if "clam" in style.theme_names():
            style.theme_use("clam")

        style.configure("App.TFrame", background="#f3f4f6")
        style.configure("Surface.TFrame", background="#ffffff")
        style.configure(
            "Title.TLabel",
            background="#f3f4f6",
            foreground="#111827",
            font=("Yu Gothic UI", 19, "bold"),
        )
        style.configure(
            "Subtitle.TLabel",
            background="#f3f4f6",
            foreground="#4b5563",
            font=("Yu Gothic UI", 10),
        )
        style.configure(
            "Section.TLabel",
            background="#ffffff",
            foreground="#111827",
            font=("Yu Gothic UI", 11, "bold"),
        )
        style.configure(
            "Muted.TLabel",
            background="#ffffff",
            foreground="#6b7280",
            font=("Yu Gothic UI", 9),
        )
        style.configure(
            "Value.TLabel",
            background="#ffffff",
            foreground="#111827",
            font=("Yu Gothic UI", 16, "bold"),
        )
        style.configure(
            "Path.TLabel",
            background="#ffffff",
            foreground="#1f2937",
            font=("Yu Gothic UI", 10),
        )
        style.configure(
            "Primary.TButton",
            font=("Yu Gothic UI", 10, "bold"),
            padding=(14, 8),
        )
        style.configure("Secondary.TButton", font=("Yu Gothic UI", 10), padding=(14, 8))
        style.configure(
            "Card.TLabelframe",
            background="#ffffff",
            borderwidth=1,
            relief="solid",
        )
        style.configure(
            "Card.TLabelframe.Label",
            background="#ffffff",
            foreground="#111827",
            font=("Yu Gothic UI", 10, "bold"),
        )
        style.configure(
            "Treeview",
            rowheight=30,
            font=("Yu Gothic UI", 10),
            fieldbackground="#ffffff",
        )
        style.configure(
            "Treeview.Heading",
            font=("Yu Gothic UI", 10, "bold"),
            padding=(8, 6),
        )
        style.map(
            "Treeview",
            background=[("selected", "#dbeafe")],
            foreground=[("selected", "#111827")],
        )
        style.configure("TProgressbar", thickness=10)

    def _build_ui(self) -> None:
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        shell = ttk.Frame(self.root, padding=18, style="App.TFrame")
        shell.grid(row=0, column=0, sticky="nsew")
        shell.columnconfigure(0, weight=1)
        shell.rowconfigure(3, weight=1)

        hero = ttk.Frame(shell, style="App.TFrame")
        hero.grid(row=0, column=0, sticky="ew")
        hero.columnconfigure(0, weight=1)
        ttk.Label(hero, text="納品書OCR ページ設定", style="Title.TLabel").grid(
            row=0, column=0, sticky="w"
        )
        ttk.Label(
            hero,
            text="PDFごとのページ設定を整理して、そのままOCR実行まで進められます。",
            style="Subtitle.TLabel",
        ).grid(row=1, column=0, sticky="w", pady=(6, 0))

        toolbar = ttk.Frame(shell, padding=16, style="Surface.TFrame")
        toolbar.grid(row=1, column=0, sticky="ew", pady=(16, 12))
        toolbar.columnconfigure(1, weight=1)

        ttk.Label(toolbar, text="対象PDF", style="Section.TLabel").grid(
            row=0, column=0, sticky="w"
        )
        ttk.Label(toolbar, textvariable=self.selected_pdf_var, style="Section.TLabel").grid(
            row=0, column=1, sticky="w"
        )
        ttk.Label(toolbar, textvariable=self.pdf_path_var, style="Path.TLabel").grid(
            row=1, column=0, columnspan=2, sticky="ew", pady=(6, 0)
        )

        actions = ttk.Frame(toolbar, style="Surface.TFrame")
        actions.grid(row=0, column=2, rowspan=2, sticky="e", padx=(18, 0))
        self.open_button = ttk.Button(
            actions,
            text="PDFを選択",
            command=self.select_pdf,
            style="Secondary.TButton",
        )
        self.open_button.grid(row=0, column=0, sticky="ew")
        self.save_button = ttk.Button(
            actions,
            text="CSVを保存",
            command=self.save_current_config,
            style="Secondary.TButton",
        )
        self.save_button.grid(row=0, column=1, sticky="ew", padx=(8, 0))
        self.run_button = ttk.Button(
            actions,
            text="OCRを実行",
            command=self.run_ocr,
            style="Primary.TButton",
        )
        self.run_button.grid(row=0, column=2, sticky="ew", padx=(8, 0))

        summary = ttk.Frame(shell, style="App.TFrame")
        summary.grid(row=2, column=0, sticky="ew", pady=(0, 12))
        for column in range(4):
            summary.columnconfigure(column, weight=1)

        self._create_stat_card(summary, 0, "設定件数", self.page_count_var)
        self._create_stat_card(summary, 1, "複数納品書", self.multiple_count_var)
        self._create_stat_card(summary, 2, "回転対象", self.rotate_count_var)
        self._create_stat_card(summary, 3, "選択中", self.selection_var)

        content = ttk.Panedwindow(shell, orient="horizontal")
        content.grid(row=3, column=0, sticky="nsew")

        list_panel = ttk.Frame(content, padding=14, style="Surface.TFrame")
        list_panel.columnconfigure(0, weight=1)
        list_panel.rowconfigure(1, weight=1)
        content.add(list_panel, weight=5)

        ttk.Label(list_panel, text="ページ一覧", style="Section.TLabel").grid(
            row=0, column=0, sticky="w"
        )
        ttk.Label(
            list_panel,
            text="複数納品書と回転の列はクリックでその場で切り替えできます。",
            style="Muted.TLabel",
        ).grid(row=0, column=1, sticky="e")

        columns = ("page", "is_multiple", "rotate_clockwise")
        self.tree = ttk.Treeview(
            list_panel,
            columns=columns,
            show="headings",
            selectmode="browse",
            height=16,
        )
        self.tree.heading("page", text="ページ")
        self.tree.heading("is_multiple", text="複数納品書")
        self.tree.heading("rotate_clockwise", text="90度回転")
        self.tree.column("page", width=110, anchor="center")
        self.tree.column("is_multiple", width=150, anchor="center")
        self.tree.column("rotate_clockwise", width=150, anchor="center")
        self.tree.grid(row=1, column=0, sticky="nsew", pady=(10, 0))
        self.tree.bind("<<TreeviewSelect>>", self.on_tree_select)
        self.tree.bind("<Button-1>", self.on_tree_click, add="+")
        self.tree.tag_configure("even", background="#ffffff")
        self.tree.tag_configure("odd", background="#f9fafb")

        scrollbar = ttk.Scrollbar(list_panel, orient="vertical", command=self.tree.yview)
        scrollbar.grid(row=1, column=1, sticky="ns", pady=(10, 0))
        self.tree.configure(yscrollcommand=scrollbar.set)

        editor = ttk.LabelFrame(content, text="編集", padding=16, style="Card.TLabelframe")
        editor.columnconfigure(1, weight=1)
        content.add(editor, weight=4)

        ttk.Label(
            editor,
            text="ページ番号を入力し、必要なフラグを設定して保存してください。",
            style="Muted.TLabel",
        ).grid(row=0, column=0, columnspan=2, sticky="w")

        ttk.Label(editor, text="ページ番号", style="Section.TLabel").grid(
            row=1, column=0, sticky="w", pady=(16, 0)
        )
        self.page_entry = ttk.Entry(editor, textvariable=self.page_var, width=12)
        self.page_entry.grid(row=1, column=1, sticky="w", pady=(16, 0))

        self.multiple_check = ttk.Checkbutton(
            editor,
            text="このページには複数の納品書が含まれる",
            variable=self.is_multiple_var,
        )
        self.multiple_check.grid(row=2, column=0, columnspan=2, sticky="w", pady=(14, 0))
        self.rotate_check = ttk.Checkbutton(
            editor,
            text="画像を時計回りに90度回転する",
            variable=self.rotate_clockwise_var,
        )
        self.rotate_check.grid(row=3, column=0, columnspan=2, sticky="w", pady=(8, 0))

        buttons = ttk.Frame(editor, style="Surface.TFrame")
        buttons.grid(row=4, column=0, columnspan=2, sticky="w", pady=(20, 0))
        self.update_button = ttk.Button(
            buttons,
            text="選択行を更新",
            command=self.update_selected_row,
            style="Primary.TButton",
        )
        self.update_button.grid(row=0, column=0, sticky="w")
        self.add_button = ttk.Button(
            buttons,
            text="新規行を追加",
            command=self.add_row,
            style="Secondary.TButton",
        )
        self.add_button.grid(row=0, column=1, sticky="w", padx=(8, 0))
        self.delete_button = ttk.Button(
            buttons,
            text="選択行を削除",
            command=self.delete_selected_row,
            style="Secondary.TButton",
        )
        self.delete_button.grid(row=0, column=2, sticky="w", padx=(8, 0))

        shortcuts = ttk.LabelFrame(
            editor,
            text="ショートカット",
            padding=14,
            style="Card.TLabelframe",
        )
        shortcuts.grid(row=5, column=0, columnspan=2, sticky="ew", pady=(24, 0))
        shortcuts.columnconfigure(0, weight=1)
        ttk.Label(
            shortcuts,
            text="Ctrl+O: PDF選択    Ctrl+S: 保存    F5: OCR実行    Delete: 行削除",
            style="Muted.TLabel",
        ).grid(row=0, column=0, sticky="w")

        footer = ttk.Frame(shell, padding=(16, 12), style="Surface.TFrame")
        footer.grid(row=4, column=0, sticky="ew", pady=(12, 0))
        footer.columnconfigure(0, weight=1)
        ttk.Label(footer, textvariable=self.status_var, style="Path.TLabel").grid(
            row=0, column=0, sticky="w"
        )
        self.progress = ttk.Progressbar(footer, mode="indeterminate")
        self.progress.grid(row=0, column=1, sticky="e", padx=(16, 0))

    def _create_stat_card(
        self,
        parent: ttk.Frame,
        column: int,
        label: str,
        value_var: tk.StringVar,
    ) -> None:
        card = ttk.Frame(parent, padding=14, style="Surface.TFrame")
        card.grid(row=0, column=column, sticky="ew", padx=(0 if column == 0 else 10, 0))
        ttk.Label(card, text=label, style="Muted.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(card, textvariable=value_var, style="Value.TLabel").grid(
            row=1, column=0, sticky="w", pady=(8, 0)
        )

    def _bind_shortcuts(self) -> None:
        self.root.bind("<Control-o>", lambda _event: self.select_pdf())
        self.root.bind("<Control-s>", lambda _event: self.save_current_config())
        self.root.bind("<F5>", lambda _event: self.run_ocr())
        self.root.bind("<Delete>", lambda _event: self.delete_selected_row())

    def _update_summary(self) -> None:
        self.selected_pdf_var.set(self.current_pdf_path.name if self.current_pdf_path else "未選択")
        self.page_count_var.set(str(len(self.pages_config)))
        self.multiple_count_var.set(
            str(sum(1 for item in self.pages_config if item.is_multiple))
        )
        self.rotate_count_var.set(
            str(sum(1 for item in self.pages_config if item.rotate_clockwise))
        )
        if self.selected_index is None or self.selected_index >= len(self.pages_config):
            self.selection_var.set("未選択")
            return
        self.selection_var.set(f"page_{self.pages_config[self.selected_index].page}")

    def _update_action_state(self) -> None:
        has_pdf = self.current_pdf_path is not None
        has_rows = bool(self.pages_config)
        has_selection = self.selected_index is not None and self.selected_index < len(self.pages_config)
        running_state = "disabled" if self.is_running else "normal"

        self.open_button.configure(state=running_state)
        self.save_button.configure(
            state="disabled" if self.is_running or not (has_pdf and has_rows) else "normal"
        )
        self.run_button.configure(
            state="disabled" if self.is_running or not (has_pdf and has_rows) else "normal"
        )
        self.add_button.configure(state=running_state)
        self.update_button.configure(
            state="disabled" if self.is_running or not has_selection else "normal"
        )
        self.delete_button.configure(
            state="disabled" if self.is_running or not has_selection else "normal"
        )
        self.page_entry.configure(state=running_state)
        self.multiple_check.configure(state=running_state)
        self.rotate_check.configure(state=running_state)

    def select_pdf(self) -> None:
        file_path = filedialog.askopenfilename(
            title="PDFを選択",
            initialdir=DATA_DIR,
            filetypes=[("PDF files", "*.pdf")],
        )
        if not file_path:
            return

        pdf_path = Path(file_path)
        self.current_pdf_path = pdf_path
        self.pdf_path_var.set(str(pdf_path))

        try:
            self.pages_config = load_pages_config(pdf_path)
            self.status_var.set(f"CSVを読み込みました: {pdf_path.stem}.csv")
        except FileNotFoundError:
            self.pages_config = default_pages_config(pdf_path)
            self.status_var.set(
                f"CSVがないためデフォルト設定を生成しました: {pdf_path.stem}.csv"
            )
        except Exception as exc:
            messagebox.showerror("読込エラー", str(exc))
            self.status_var.set("読込に失敗しました")
            return

        self.selected_index = None
        self.refresh_tree()
        self.clear_editor()
        if self.pages_config:
            first_item = self.tree.get_children()[0]
            self.tree.selection_set(first_item)
            self.tree.focus(first_item)
            self.on_tree_select()
        else:
            self._update_summary()
            self._update_action_state()

    def refresh_tree(self) -> None:
        for item_id in self.tree.get_children():
            self.tree.delete(item_id)

        for index, page_config in enumerate(self.pages_config):
            self.tree.insert(
                "",
                "end",
                iid=str(index),
                values=(
                    page_config.page,
                    self._bool_label(page_config.is_multiple),
                    self._bool_label(page_config.rotate_clockwise),
                ),
                tags=(("even" if index % 2 == 0 else "odd"),),
            )

        self._update_summary()
        self._update_action_state()

    def on_tree_select(self, _event=None) -> None:
        selection = self.tree.selection()
        if not selection:
            self.selected_index = None
            self.clear_editor()
            self._update_summary()
            self._update_action_state()
            return

        self.selected_index = int(selection[0])
        page_config = self.pages_config[self.selected_index]
        self.page_var.set(str(page_config.page))
        self.is_multiple_var.set(page_config.is_multiple)
        self.rotate_clockwise_var.set(page_config.rotate_clockwise)
        self.status_var.set(f"page_{page_config.page} を編集中")
        self._update_summary()
        self._update_action_state()

    def on_tree_click(self, event) -> None:
        if self.is_running:
            return

        row_id = self.tree.identify_row(event.y)
        column_id = self.tree.identify_column(event.x)

        if not row_id or column_id not in {"#2", "#3"}:
            return

        index = int(row_id)
        current = self.pages_config[index]
        updated = PageConfig(
            page=current.page,
            is_multiple=(
                not current.is_multiple if column_id == "#2" else current.is_multiple
            ),
            rotate_clockwise=(
                not current.rotate_clockwise
                if column_id == "#3"
                else current.rotate_clockwise
            ),
        )
        self.pages_config[index] = updated
        self.refresh_tree()
        self._select_page(updated.page)
        self.status_var.set(f"page_{updated.page} を更新しました")

    def clear_editor(self) -> None:
        self.page_var.set("")
        self.is_multiple_var.set(False)
        self.rotate_clockwise_var.set(False)

    def update_selected_row(self) -> None:
        if self.selected_index is None:
            messagebox.showwarning("未選択", "更新する行を選択してください")
            return

        updated = self._read_editor_values()
        if updated is None:
            return

        self.pages_config[self.selected_index] = updated
        self._sort_pages_config()
        self.refresh_tree()
        self._select_page(updated.page)
        self.status_var.set(f"page_{updated.page} を更新しました")

    def add_row(self) -> None:
        new_page_config = self._read_editor_values()
        if new_page_config is None:
            return

        if any(item.page == new_page_config.page for item in self.pages_config):
            messagebox.showwarning("重複", f"page {new_page_config.page} は既に存在します")
            return

        self.pages_config.append(new_page_config)
        self._sort_pages_config()
        self.refresh_tree()
        self._select_page(new_page_config.page)
        self.status_var.set(f"page_{new_page_config.page} を追加しました")

    def delete_selected_row(self) -> None:
        if self.selected_index is None:
            messagebox.showwarning("未選択", "削除する行を選択してください")
            return

        page = self.pages_config[self.selected_index].page
        del self.pages_config[self.selected_index]
        self.refresh_tree()
        self.clear_editor()
        self.selected_index = None
        self._update_summary()
        self._update_action_state()
        self.status_var.set(f"page_{page} を削除しました")

    def save_current_config(self) -> None:
        if self.current_pdf_path is None:
            messagebox.showwarning("未選択", "先にPDFを選択してください")
            return
        if not self.pages_config:
            messagebox.showwarning("空データ", "保存する設定がありません")
            return

        try:
            config_path = save_pages_config(self.current_pdf_path, self.pages_config)
        except Exception as exc:
            messagebox.showerror("保存エラー", str(exc))
            self.status_var.set("保存に失敗しました")
            return

        self.status_var.set(f"保存しました: {config_path}")
        messagebox.showinfo("保存完了", f"保存しました\n{config_path}")

    def run_ocr(self) -> None:
        if self.current_pdf_path is None:
            messagebox.showwarning("未選択", "先にPDFを選択してください")
            return
        if self.is_running:
            messagebox.showinfo("実行中", "OCR処理は既に実行中です")
            return

        try:
            self.save_current_config_silent()
        except Exception as exc:
            messagebox.showerror("保存エラー", str(exc))
            self.status_var.set("実行前の保存に失敗しました")
            return

        self.is_running = True
        self._update_action_state()
        self.progress.start(10)
        self.status_var.set(f"OCR実行中: {self.current_pdf_path.name}")
        worker = Thread(target=self._run_ocr_worker, daemon=True)
        worker.start()

    def save_current_config_silent(self) -> Path:
        if self.current_pdf_path is None:
            raise ValueError("PDF is not selected")
        if not self.pages_config:
            raise ValueError("保存する設定がありません")

        return save_pages_config(self.current_pdf_path, self.pages_config)

    def _run_ocr_worker(self) -> None:
        assert self.current_pdf_path is not None
        exit_code = process_pdf(self.current_pdf_path)
        self.root.after(0, lambda: self._finish_run(exit_code))

    def _finish_run(self, exit_code: int) -> None:
        self.is_running = False
        self.progress.stop()
        self._update_action_state()
        if exit_code == 0:
            self.status_var.set("OCR処理が完了しました")
            messagebox.showinfo("完了", "OCR処理が完了しました")
        else:
            self.status_var.set("OCR処理に失敗しました。results/logs を確認してください")
            messagebox.showwarning(
                "失敗",
                "OCR処理に失敗しました。\nresults/logs/app.log と results/logs/pages/*.log を確認してください。",
            )

    def _read_editor_values(self) -> PageConfig | None:
        page_text = self.page_var.get().strip()
        if not page_text:
            messagebox.showwarning("入力不足", "ページ番号を入力してください")
            return None

        try:
            page = int(page_text)
        except ValueError:
            messagebox.showwarning("入力エラー", "ページ番号は整数で入力してください")
            return None

        if page < 1:
            messagebox.showwarning("入力エラー", "ページ番号は1以上で入力してください")
            return None

        return PageConfig(
            page=page,
            is_multiple=self.is_multiple_var.get(),
            rotate_clockwise=self.rotate_clockwise_var.get(),
        )

    def _sort_pages_config(self) -> None:
        self.pages_config.sort(key=lambda item: item.page)

    def _select_page(self, page: int) -> None:
        for index, page_config in enumerate(self.pages_config):
            if page_config.page == page:
                item_id = str(index)
                self.tree.selection_set(item_id)
                self.tree.focus(item_id)
                self.tree.see(item_id)
                self.on_tree_select()
                return

    @staticmethod
    def _bool_label(value: bool) -> str:
        return "☑" if value else "☐"


def main() -> None:
    root = tk.Tk()
    PageConfigEditor(root)
    root.mainloop()


if __name__ == "__main__":
    main()
