#!/usr/bin/env python3
"""
OCR結果をGUIで確認・編集するツール
"""
from __future__ import annotations

import json
import re
import tkinter as tk
from dataclasses import dataclass
from pathlib import Path
from tkinter import messagebox, ttk

from PIL import ExifTags, Image, ImageTk

from common import save_result
from config import RESULTS_JSON_DIR, RESULTS_SUMMARY_DIR, page_image_path
from json_to_csv_excel import convert_to_dataframe, save_to_csv_and_excel


RESULT_FIELD_NAMES = ("納品日", "会社名", "品名", "単価", "数量")
RESULT_FILE_PATTERN = re.compile(r"page_(?P<page>\d+)_result$")


@dataclass
class OCRResultRecord:
    source_file: str
    page_number: int
    entry_index: int
    container_type: str
    payload: dict[str, object]

    def get_value(self, field_name: str) -> str:
        value = self.payload.get(field_name, "")
        return "" if value is None else str(value)

    def set_value(self, field_name: str, value: str) -> None:
        self.payload[field_name] = value.strip()

    def to_export_row(self) -> dict[str, object]:
        row = dict(self.payload)
        row["ソースファイル"] = self.source_file
        return row


def _page_number_from_source_file(source_file: str) -> int:
    match = RESULT_FILE_PATTERN.fullmatch(source_file)
    if match is None:
        raise ValueError(f"結果ファイル名を解釈できません: {source_file}")
    return int(match.group("page"))


def load_result_records(results_dir: Path = RESULTS_JSON_DIR) -> list[OCRResultRecord]:
    records: list[OCRResultRecord] = []

    for json_file in sorted(results_dir.glob("page_*_result.json")):
        with json_file.open("r", encoding="utf-8") as file:
            data = json.load(file)

        source_file = json_file.stem
        page_number = _page_number_from_source_file(source_file)

        if isinstance(data, list):
            for index, item in enumerate(data):
                if not isinstance(item, dict):
                    raise ValueError(f"{json_file} にJSONオブジェクト以外の要素があります")
                payload = {key: value for key, value in item.items() if key != "ソースファイル"}
                for field_name in RESULT_FIELD_NAMES:
                    payload.setdefault(field_name, "")
                records.append(
                    OCRResultRecord(
                        source_file=source_file,
                        page_number=page_number,
                        entry_index=index,
                        container_type="list",
                        payload=payload,
                    )
                )
        elif isinstance(data, dict):
            payload = {key: value for key, value in data.items() if key != "ソースファイル"}
            for field_name in RESULT_FIELD_NAMES:
                payload.setdefault(field_name, "")
            records.append(
                OCRResultRecord(
                    source_file=source_file,
                    page_number=page_number,
                    entry_index=0,
                    container_type="dict",
                    payload=payload,
                )
            )
        else:
            raise ValueError(f"{json_file} のJSON形式が不正です")

    return records


def save_result_records(records: list[OCRResultRecord]) -> None:
    grouped_records: dict[str, list[OCRResultRecord]] = {}
    for record in records:
        grouped_records.setdefault(record.source_file, []).append(record)

    for source_file, source_records in grouped_records.items():
        sorted_records = sorted(source_records, key=lambda item: item.entry_index)
        container_type = sorted_records[0].container_type
        payloads = [record.payload for record in sorted_records]

        if container_type == "dict":
            if len(payloads) != 1:
                raise ValueError(f"{source_file} は単一オブジェクトのはずですが複数件あります")
            serialized = payloads[0]
        else:
            serialized = payloads

        save_result(serialized, f"{source_file}.json", RESULTS_JSON_DIR)

    export_rows = [record.to_export_row() for record in records]
    if export_rows:
        df = convert_to_dataframe(export_rows)
        save_to_csv_and_excel(df, RESULTS_SUMMARY_DIR)


class OCRResultViewerApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("OCR結果ビューア")
        self.root.geometry("1500x900")

        self.records: list[OCRResultRecord] = []
        self.selected_index: int | None = None
        self.status_var = tk.StringVar(value="待機中")
        self.record_info_var = tk.StringVar(value="レコード未選択")
        self.input_vars = {
            field_name: tk.StringVar()
            for field_name in RESULT_FIELD_NAMES
        }

        self.zoom_ratio = 1.0
        self.original_image: Image.Image | None = None
        self.current_image: Image.Image | None = None
        self.photo_image: ImageTk.PhotoImage | None = None

        self._build_ui()
        self.reload_records(initial_load=True)

    def _build_ui(self) -> None:
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(1, weight=1)

        header = ttk.Frame(self.root, padding=12)
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(0, weight=1)

        ttk.Label(
            header,
            text="results/json/page_*_result.json を確認・編集します",
        ).grid(row=0, column=0, sticky="w")

        buttons = ttk.Frame(header)
        buttons.grid(row=0, column=1, sticky="e")
        ttk.Button(buttons, text="再読込", command=self.reload_records).grid(
            row=0, column=0, padx=(0, 8)
        )
        ttk.Button(buttons, text="保存", command=self.save_records).grid(
            row=0, column=1, padx=(0, 8)
        )
        ttk.Button(buttons, text="閉じる", command=self.root.destroy).grid(
            row=0, column=2
        )

        content = ttk.Panedwindow(self.root, orient="vertical")
        content.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 12))

        upper = ttk.Frame(content, padding=4)
        upper.columnconfigure(0, weight=1)
        upper.rowconfigure(0, weight=1)
        content.add(upper, weight=2)

        columns = ("page", "entry", "source_file", *RESULT_FIELD_NAMES)
        self.tree = ttk.Treeview(
            upper,
            columns=columns,
            show="headings",
            selectmode="browse",
            height=10,
        )
        headings = {
            "page": "Page",
            "entry": "明細",
            "source_file": "ソースファイル",
            "納品日": "納品日",
            "会社名": "会社名",
            "品名": "品名",
            "単価": "単価",
            "数量": "数量",
        }
        widths = {
            "page": 80,
            "entry": 80,
            "source_file": 180,
            "納品日": 120,
            "会社名": 220,
            "品名": 260,
            "単価": 120,
            "数量": 100,
        }
        for column in columns:
            self.tree.heading(column, text=headings[column])
            self.tree.column(column, width=widths[column], anchor="w")

        self.tree.grid(row=0, column=0, sticky="nsew")
        self.tree.bind("<<TreeviewSelect>>", self.on_tree_select)

        tree_scrollbar = ttk.Scrollbar(upper, orient="vertical", command=self.tree.yview)
        tree_scrollbar.grid(row=0, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=tree_scrollbar.set)

        lower = ttk.Panedwindow(content, orient="horizontal")
        content.add(lower, weight=3)

        editor_frame = ttk.LabelFrame(lower, text="選択中レコードの編集", padding=12)
        editor_frame.columnconfigure(1, weight=1)
        lower.add(editor_frame, weight=1)

        ttk.Label(editor_frame, textvariable=self.record_info_var).grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 10)
        )

        for index, field_name in enumerate(RESULT_FIELD_NAMES, start=1):
            ttk.Label(editor_frame, text=field_name).grid(
                row=index,
                column=0,
                sticky="nw",
                padx=(0, 12),
                pady=4,
            )
            entry = ttk.Entry(editor_frame, textvariable=self.input_vars[field_name])
            entry.grid(row=index, column=1, sticky="ew", pady=4)

        editor_buttons = ttk.Frame(editor_frame)
        editor_buttons.grid(
            row=len(RESULT_FIELD_NAMES) + 1,
            column=0,
            columnspan=2,
            sticky="w",
            pady=(12, 0),
        )
        ttk.Button(editor_buttons, text="更新", command=self.update_selected_record).grid(
            row=0, column=0
        )

        image_frame = ttk.LabelFrame(lower, text="画像表示", padding=12)
        image_frame.columnconfigure(0, weight=1)
        image_frame.rowconfigure(1, weight=1)
        lower.add(image_frame, weight=1)

        controls = ttk.Frame(image_frame)
        controls.grid(row=0, column=0, sticky="w", pady=(0, 8))
        ttk.Button(controls, text="拡大", command=self.zoom_in).grid(row=0, column=0, padx=(0, 4))
        ttk.Button(controls, text="縮小", command=self.zoom_out).grid(row=0, column=1, padx=4)
        ttk.Button(controls, text="左回転", command=self.rotate_left).grid(row=0, column=2, padx=4)
        ttk.Button(controls, text="右回転", command=self.rotate_right).grid(row=0, column=3, padx=4)
        ttk.Button(controls, text="リセット", command=self.reset_view).grid(row=0, column=4, padx=4)

        canvas_container = ttk.Frame(image_frame)
        canvas_container.grid(row=1, column=0, sticky="nsew")
        canvas_container.columnconfigure(0, weight=1)
        canvas_container.rowconfigure(0, weight=1)

        self.image_canvas = tk.Canvas(canvas_container, bg="white", relief=tk.SUNKEN, bd=2)
        self.image_canvas.grid(row=0, column=0, sticky="nsew")
        self.image_canvas.bind("<Configure>", self.on_canvas_resize)

        x_scrollbar = ttk.Scrollbar(
            canvas_container,
            orient="horizontal",
            command=self.image_canvas.xview,
        )
        x_scrollbar.grid(row=1, column=0, sticky="ew")
        y_scrollbar = ttk.Scrollbar(
            canvas_container,
            orient="vertical",
            command=self.image_canvas.yview,
        )
        y_scrollbar.grid(row=0, column=1, sticky="ns")
        self.image_canvas.configure(
            xscrollcommand=x_scrollbar.set,
            yscrollcommand=y_scrollbar.set,
        )
        self.show_empty_image_message("行を選択すると画像が表示されます")

        status = ttk.Label(self.root, textvariable=self.status_var, padding=(12, 0, 12, 12))
        status.grid(row=2, column=0, sticky="ew")

    def reload_records(self, initial_load: bool = False) -> None:
        try:
            self.records = load_result_records()
        except Exception as exc:
            if not initial_load:
                messagebox.showerror("読込エラー", str(exc))
            self.status_var.set("OCR結果の読込に失敗しました")
            return

        self.refresh_tree()
        self.selected_index = None
        self.record_info_var.set("レコード未選択")
        self.clear_editor()
        self.show_empty_image_message("行を選択すると画像が表示されます")

        if not self.records:
            message = "OCR結果がありません。先にOCRを実行してください。"
            self.status_var.set(message)
            if not initial_load:
                messagebox.showinfo("結果なし", message)
            return

        first_item = self.tree.get_children()[0]
        self.tree.selection_set(first_item)
        self.tree.focus(first_item)
        self.tree.see(first_item)
        self.on_tree_select()
        self.status_var.set(f"{len(self.records)} 件のOCR結果を読み込みました")

    def refresh_tree(self) -> None:
        for item_id in self.tree.get_children():
            self.tree.delete(item_id)

        for index, record in enumerate(self.records):
            self.tree.insert(
                "",
                "end",
                iid=str(index),
                values=(
                    record.page_number,
                    record.entry_index + 1,
                    record.source_file,
                    *(record.get_value(field_name) for field_name in RESULT_FIELD_NAMES),
                ),
            )

    def on_tree_select(self, _event=None) -> None:
        selection = self.tree.selection()
        if not selection:
            self.selected_index = None
            self.record_info_var.set("レコード未選択")
            self.clear_editor()
            self.show_empty_image_message("行を選択すると画像が表示されます")
            return

        self.selected_index = int(selection[0])
        record = self.records[self.selected_index]
        self.record_info_var.set(
            f"{record.source_file} / page_{record.page_number} / 明細 {record.entry_index + 1}"
        )

        for field_name in RESULT_FIELD_NAMES:
            self.input_vars[field_name].set(record.get_value(field_name))

        self.show_record_image(record)
        self.status_var.set(f"page_{record.page_number} の結果を編集中")

    def update_selected_record(self) -> None:
        if self.selected_index is None:
            messagebox.showwarning("未選択", "更新する行を選択してください")
            return

        record = self.records[self.selected_index]
        for field_name in RESULT_FIELD_NAMES:
            record.set_value(field_name, self.input_vars[field_name].get())

        self.refresh_tree()
        item_id = str(self.selected_index)
        self.tree.selection_set(item_id)
        self.tree.focus(item_id)
        self.tree.see(item_id)
        self.status_var.set(f"{record.source_file} を更新しました")
        messagebox.showinfo("更新完了", "選択中レコードを更新しました")

    def save_records(self) -> None:
        if not self.records:
            messagebox.showwarning("保存不可", "保存するOCR結果がありません")
            return

        try:
            save_result_records(self.records)
        except Exception as exc:
            messagebox.showerror("保存エラー", str(exc))
            self.status_var.set("OCR結果の保存に失敗しました")
            return

        self.status_var.set("JSON / CSV / Excel を保存しました")
        messagebox.showinfo(
            "保存完了",
            "OCR結果を保存しました。\nresults/json と results/summary を更新しています。",
        )

    def clear_editor(self) -> None:
        for variable in self.input_vars.values():
            variable.set("")

    def show_record_image(self, record: OCRResultRecord) -> None:
        image_path = page_image_path(record.page_number)
        if not image_path.exists():
            self.original_image = None
            self.current_image = None
            self.photo_image = None
            self.show_empty_image_message(f"画像が見つかりません:\n{image_path}")
            return

        try:
            image = Image.open(image_path)
            self.original_image = self.auto_rotate_image(image)
            self.current_image = self.original_image.copy()
            self.zoom_ratio = 1.0
            self.display_image()
        except Exception as exc:
            self.original_image = None
            self.current_image = None
            self.photo_image = None
            self.show_empty_image_message(f"画像読み込みエラー:\n{exc}")

    def auto_rotate_image(self, image: Image.Image) -> Image.Image:
        try:
            orientation_tag = next(
                key for key, value in ExifTags.TAGS.items() if value == "Orientation"
            )
            exif = image.getexif()
            orientation = exif.get(orientation_tag)
            if orientation == 3:
                return image.rotate(180, expand=True)
            if orientation == 6:
                return image.rotate(270, expand=True)
            if orientation == 8:
                return image.rotate(90, expand=True)
        except StopIteration:
            pass
        return image

    def display_image(self) -> None:
        if self.current_image is None:
            return

        canvas_width = self.image_canvas.winfo_width()
        canvas_height = self.image_canvas.winfo_height()
        if canvas_width <= 1 or canvas_height <= 1:
            return

        image_width, image_height = self.current_image.size
        image_ratio = image_width / image_height
        canvas_ratio = canvas_width / canvas_height

        if image_ratio > canvas_ratio:
            fit_width = max(1, canvas_width - 20)
            fit_height = max(1, int(fit_width / image_ratio))
        else:
            fit_height = max(1, canvas_height - 20)
            fit_width = max(1, int(fit_height * image_ratio))

        display_width = max(1, int(fit_width * self.zoom_ratio))
        display_height = max(1, int(fit_height * self.zoom_ratio))

        resized_image = self.current_image.resize((display_width, display_height), Image.LANCZOS)
        self.photo_image = ImageTk.PhotoImage(resized_image)

        self.image_canvas.delete("all")
        x = max(0, (canvas_width - display_width) // 2)
        y = max(0, (canvas_height - display_height) // 2)
        self.image_canvas.create_image(x, y, anchor=tk.NW, image=self.photo_image)
        self.image_canvas.configure(scrollregion=(0, 0, display_width, display_height))

    def show_empty_image_message(self, message: str) -> None:
        self.image_canvas.delete("all")
        self.image_canvas.create_text(
            240,
            180,
            text=message,
            fill="gray",
            font=("Arial", 12),
        )
        self.image_canvas.configure(scrollregion=(0, 0, 0, 0))

    def on_canvas_resize(self, _event=None) -> None:
        if self.current_image is not None:
            self.display_image()

    def zoom_in(self) -> None:
        if self.current_image is None:
            return
        self.zoom_ratio += 0.2
        self.display_image()

    def zoom_out(self) -> None:
        if self.current_image is None:
            return
        self.zoom_ratio = max(0.2, self.zoom_ratio - 0.2)
        self.display_image()

    def rotate_left(self) -> None:
        if self.current_image is None:
            return
        self.current_image = self.current_image.rotate(90, expand=True)
        self.display_image()

    def rotate_right(self) -> None:
        if self.current_image is None:
            return
        self.current_image = self.current_image.rotate(-90, expand=True)
        self.display_image()

    def reset_view(self) -> None:
        if self.original_image is None:
            return
        self.zoom_ratio = 1.0
        self.current_image = self.original_image.copy()
        self.display_image()


def main() -> None:
    root = tk.Tk()
    OCRResultViewerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
