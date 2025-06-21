import tkinter as tk
from tkinter import ttk
import os


class PathInputRow(tk.Frame):
    def __init__(self, parent, label_text, path_var, on_clear, highlight_color=None, **kwargs):
        super().__init__(parent, **kwargs)

        # 上排：label + 檔名 + 清除按鈕
        top_frame = tk.Frame(self)
        top_frame.pack(fill="x", pady=(0, 2))

        # Label（如：目前正面）
        ttk.Label(top_frame, text=label_text).pack(side="left")

        # 檔名：從 path 中取出 basename
        self.filename_var = tk.StringVar(value=self._get_filename(path_var.get()))
        filename_label = ttk.Label(top_frame, textvariable=self.filename_var, font=("Arial", 11, "bold"))
        filename_label.pack(side="left", padx=(5, 10))

        ttk.Button(top_frame, text="清除", command=on_clear).pack(side="right")

        # 下排：完整路徑欄
        entry_container = tk.Frame(self,
                                   highlightthickness=2 if highlight_color else 0,
                                   highlightbackground=highlight_color or "gray",
                                   bd=0)
        entry_container.pack(fill="x")

        self.path_entry = ttk.Entry(entry_container, textvariable=path_var, state="readonly")
        self.path_entry.pack(fill="x")

        # 綁定 path_var 的變化，自動更新 filename
        path_var.trace_add("write", lambda *args: self.filename_var.set(self._get_filename(path_var.get())))

    def _get_filename(self, path: str) -> str:
        return os.path.basename(path) if path else "（尚未選取）"