import tkinter as tk
from tkinter import ttk

class ImagePanel(ttk.Frame):
    def __init__(self, parent, title="圖像區塊", **kwargs):
        super().__init__(parent, **kwargs)

        # 上方標題
        ttk.Label(self, text=title, anchor="center").pack(pady=5)

        # 圖片顯示區
        self.image_label = ttk.Label(self, borderwidth=1, relief="solid", width=300, height=300)
        self.image_label.pack(expand=True, fill="both", padx=10, pady=5)

        # 操作按鈕區
        self.control_frame = ttk.Frame(self)
        self.control_frame.pack(pady=10)

        ttk.Button(self.control_frame, text="手動校正").pack(side="left", padx=5)

    def update_image(self, img_tk):
        """更新圖片內容"""
        self.image_label.configure(image=img_tk)
        self.image_label.image = img_tk  # 防止被 GC 回收
