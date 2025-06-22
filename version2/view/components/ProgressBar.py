import tkinter as tk
from tkinter import ttk
import threading

class ProgressBar(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        
        self.progress = ttk.Progressbar(self, mode='determinate', length=300)
        self.progress.pack(side='left', padx=5, pady=5, fill='x', expand=True)

        self.label = tk.Label(self, text="進度: 0%")
        self.label.pack(side='left', padx=5)

        self.disable()  # 預設隱藏

    def set_progress(self, percent: int, text: str = None):
        """設定進度條百分比和顯示文字"""
        if percent < 0:
            percent = 0
        elif percent > 100:
            percent = 100
        self.progress['value'] = percent
        display_text = text if text is not None else f"進度: {percent}%"
        self.label.config(text=display_text)
        self.update_idletasks()

    def enable(self):
        """顯示進度條和文字"""
        self.pack(fill='x', padx=5, pady=5)  # 顯示整個 Frame
        self.progress.pack(side='left', padx=5, pady=5, fill='x', expand=True)
        self.label.pack(side='left', padx=5)
        self.progress['value'] = 0
        self.label.config(text="進度: 0%")

    def disable(self):
        """隱藏進度條和文字"""
        self.progress.pack_forget()
        self.label.pack_forget()
        self.pack_forget()

    def change_progress(self, func, on_complete=None):
        """
        以線程執行 func(func參數應包含 set_progress 方法以更新進度)
        func 格式: func(set_progress_callback)
        on_complete: 完成後執行的 callback (無參數)
        """

        def worker():
            try:
                func(self.set_progress)
            finally:
                if on_complete:
                    self.after(0, on_complete)
        
        self.enable()
        thread = threading.Thread(target=worker, daemon=True)
        thread.start()
