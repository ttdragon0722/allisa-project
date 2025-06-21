import tkinter as tk
from tkinter import ttk
from lib.data.models import File

class FileBlock(tk.Frame):
    def __init__(self, parent, file: File, set_front_path_func, set_back_path_func, get_cur_front_func, get_cur_back_func):
        super().__init__(parent, bd=2, relief="groove", padx=10, pady=5)
        self.file = file
        self.set_front_path_func = set_front_path_func
        self.set_back_path_func = set_back_path_func
        self.get_cur_front_func = get_cur_front_func  # 用來取得目前正面 File
        self.get_cur_back_func = get_cur_back_func    # 用來取得目前背面 File

        # 檔案基本資訊
        lbl_name = ttk.Label(self, text=f"{file.name}", font=("Arial", 12, "bold"))
        lbl_time = ttk.Label(self, text=f"修改時間：{file.mod_time_str}（{file.ext}）")

        # 操作按鈕
        btn_front = ttk.Button(self, text="設為前景", command=self.set_front)
        btn_back = ttk.Button(self, text="設為背景", command=self.set_back)

        # 排版
        lbl_name.pack(anchor="w")
        lbl_time.pack(anchor="w")
        btn_frame = ttk.Frame(self)
        btn_frame.pack(anchor="e", pady=5)
        btn_front.pack(side="left", padx=5)
        btn_back.pack(side="left", padx=5)

        self.update_border_color()

    def set_front(self):
        self.set_front_path_func(self.file)

    def set_back(self):
        self.set_back_path_func(self.file)

    def update_border_color(self):
        # 判斷是否為目前選擇的前景或背景，改變邊框顏色
        border_color = "gray"  # 預設邊框色

        cur_front = self.get_cur_front_func()
        cur_back = self.get_cur_back_func()

        if cur_front and self.file.path == cur_front:
            border_color = "cyan"
        elif cur_back and self.file.path == cur_back:
            border_color = "blue"

        self.config(highlightthickness=2, highlightbackground=border_color)
