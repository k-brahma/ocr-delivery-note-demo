#!/usr/bin/env python3
"""
PDFごとのページ設定CSVをGUIで編集するツール
"""
from __future__ import annotations

import tkinter as tk
from threading import Thread
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from config import DATA_DIR
from main import process_pdf
from page_config import PageConfig, default_pages_config, load_pages_config, save_pages_config


class PageConfigEditor:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("OCR Page Config Editor")
        self.root.geometry("860x560")

        self.current_pdf_path: Path | None = None
        self.pages_config: list[PageConfig] = []
        self.selected_index: int | None = None
        self.is_running = False

        self.pdf_path_var = tk.StringVar(value="PDFを選択してください")
        self.status_var = tk.StringVar(value="待機中")

        self.page_var = tk.StringVar()
        self.is_multiple_var = tk.BooleanVar(value=False)
        self.rotate_clockwise_var = tk.BooleanVar(value=False)

        self._build_ui()

    def _build_ui(self) -> None:
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(1, weight=1)

        header = ttk.Frame(self.root, padding=12)
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(1, weight=1)

        ttk.Button(header, text="PDFを選択", command=self.select_pdf).grid(
            row=0, column=0, sticky="w"
        )
        ttk.Label(header, textvariable=self.pdf_path_var).grid(
            row=0, column=1, sticky="ew", padx=(12, 0)
        )
        ttk.Button(header, text="CSVを保存", command=self.save_current_config).grid(
            row=0, column=2, sticky="e", padx=(12, 0)
        )
        self.run_button = ttk.Button(header, text="実行", command=self.run_ocr)
        self.run_button.grid(row=0, column=3, sticky="e", padx=(12, 0))

        content = ttk.Panedwindow(self.root, orient="vertical")
        content.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 12))

        upper = ttk.Frame(content, padding=8)
        upper.columnconfigure(0, weight=1)
        upper.rowconfigure(0, weight=1)
        content.add(upper, weight=3)

        columns = ("page", "is_multiple", "rotate_clockwise")
        self.tree = ttk.Treeview(
            upper,
            columns=columns,
            show="headings",
            selectmode="browse",
            height=12,
        )
        self.tree.heading("page", text="Page")
        self.tree.heading("is_multiple", text="Multiple")
        self.tree.heading("rotate_clockwise", text="Rotate CW")
        self.tree.column("page", width=120, anchor="center")
        self.tree.column("is_multiple", width=160, anchor="center")
        self.tree.column("rotate_clockwise", width=160, anchor="center")
        self.tree.grid(row=0, column=0, sticky="nsew")
        self.tree.bind("<<TreeviewSelect>>", self.on_tree_select)
        self.tree.bind("<Button-1>", self.on_tree_click, add="+")

        scrollbar = ttk.Scrollbar(upper, orient="vertical", command=self.tree.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=scrollbar.set)

        lower = ttk.LabelFrame(content, text="編集", padding=12)
        lower.columnconfigure(1, weight=1)
        content.add(lower, weight=2)

        ttk.Label(lower, text="Page").grid(row=0, column=0, sticky="w")
        self.page_entry = ttk.Entry(lower, textvariable=self.page_var, width=12)
        self.page_entry.grid(row=0, column=1, sticky="w")

        ttk.Checkbutton(lower, text="複数納品書", variable=self.is_multiple_var).grid(
            row=1, column=0, columnspan=2, sticky="w", pady=(12, 0)
        )
        ttk.Checkbutton(
            lower,
            text="時計回りに90度回転",
            variable=self.rotate_clockwise_var,
        ).grid(row=2, column=0, columnspan=2, sticky="w", pady=(8, 0))

        buttons = ttk.Frame(lower)
        buttons.grid(row=3, column=0, columnspan=2, sticky="w", pady=(16, 0))
        ttk.Button(buttons, text="更新", command=self.update_selected_row).grid(
            row=0, column=0, sticky="w"
        )
        ttk.Button(buttons, text="新規行を追加", command=self.add_row).grid(
            row=0, column=1, sticky="w", padx=(8, 0)
        )
        ttk.Button(buttons, text="選択行を削除", command=self.delete_selected_row).grid(
            row=0, column=2, sticky="w", padx=(8, 0)
        )

        status = ttk.Label(self.root, textvariable=self.status_var, padding=(12, 0, 12, 12))
        status.grid(row=2, column=0, sticky="ew")

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
            )

    def on_tree_select(self, _event=None) -> None:
        selection = self.tree.selection()
        if not selection:
            self.selected_index = None
            self.clear_editor()
            return

        self.selected_index = int(selection[0])
        page_config = self.pages_config[self.selected_index]
        self.page_var.set(str(page_config.page))
        self.is_multiple_var.set(page_config.is_multiple)
        self.rotate_clockwise_var.set(page_config.rotate_clockwise)
        self.status_var.set(f"page_{page_config.page} を編集中")

    def on_tree_click(self, event) -> None:
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
        self.run_button.configure(state="disabled")
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
        self.run_button.configure(state="normal")
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
            messagebox.showwarning("入力不足", "Page を入力してください")
            return None

        try:
            page = int(page_text)
        except ValueError:
            messagebox.showwarning("入力エラー", "Page は整数で入力してください")
            return None

        if page < 1:
            messagebox.showwarning("入力エラー", "Page は1以上で入力してください")
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
