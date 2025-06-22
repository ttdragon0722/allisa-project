import tkinter as tk
from tkinter import filedialog, ttk

from view import AccessPage, FilePickPage, ValidPage

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("PDF 選擇器")
        
        # 視窗大小
        self.window_width = 1440
        self.window_height = 810
        self.geometry(f"{self.window_width}x{self.window_height}")
        self.resizable(False, False)
        
        
        # 註冊全域變數
        self.shared_data = {
            "front_path": None,
            "back_path": None
        }
        
        # 容器（Frame 切換用）
        container = tk.Frame(self)
        container.pack(fill="both", expand=True)

        # 註冊頁面
        self.frames = {}
        for F in (FilePickPage,ValidPage,AccessPage):
            frame = F(parent=container, controller=self)
            self.frames[F] = frame
            frame.grid(row=0, column=0, sticky="nsew")

        self.show_frame(FilePickPage)

    def show_frame(self, page):
        frame = self.frames[page]
        frame.tkraise()
        
        # 生成選單
        menu = getattr(frame, "menu", None)
        if menu:
            self.config(menu=menu)
        else:
            self.config(menu=tk.Menu(self))  # 預設空選單



if __name__ == "__main__":
    app = App()
    app.mainloop()