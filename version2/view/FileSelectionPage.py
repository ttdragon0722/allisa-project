import tkinter as tk
from tkinter import filedialog, ttk

# 根據執行方式決定是否使用相對匯入
if __name__ == "__main__":
    from ..lib.PDFViewer import PDFViewer
    from AccessPage import AccessPage
else:
    from lib.PDFViewer import PDFViewer
    from .AccessPage import AccessPage
    from lib.debug import Debug


class FileSelectionPage(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller

        self.front_path = tk.StringVar()
        self.back_path = tk.StringVar()
        
        self.error_labels = {}

        self.build_ui()
        
    def build_ui(self):
        # 標題
        ttk.Label(self, text="請選擇 PDF 檔案", font=("Helvetica", 16)).pack(pady=20)

        # 整體容器：左右兩欄排版
        container = ttk.Frame(self)
        container.pack(pady=10, padx=50, fill="x")

        # 左側輸入區（第 0 欄）
        self.input_frame = ttk.Frame(container)
        self.input_frame.grid(row=0, column=0, sticky="w")

        # 右側按鈕區（第 1 欄）
        self.button_frame = ttk.Frame(container)
        self.button_frame.grid(row=0, column=1, padx=20, sticky="n")

        # 加入輸入欄位
        self.create_file_selector("正面 PDF 檔案", self.front_path, "front", row=0)
        self.create_file_selector("反面 PDF 檔案", self.back_path, "back", row=1)

        # 按鈕置頂對齊
        ttk.Button(self.button_frame, text="進入主頁面", command=self.go_to_main_page).pack()
        
        image_ui_container = ttk.Frame(self)
        image_ui_container.pack(pady=20, fill="both", expand=True)

        self.build_image_ui(image_ui_container)

        
    def build_image_ui(self, parent):
        parent.columnconfigure(0, weight=1)
        parent.columnconfigure(1, weight=1)
        parent.rowconfigure(1, weight=1)

        # 上方說明
        top_frame = ttk.Frame(parent)
        top_frame.grid(row=0, column=0, columnspan=2, pady=10, sticky="ew")
        ttk.Label(top_frame, text="正面 PDF 檔案").pack(side="left", expand=True)
        ttk.Label(top_frame, text="反面 PDF 檔案").pack(side="right", expand=True)

        # 圖像框
        left_frame = ttk.Frame(parent, borderwidth=1, relief="solid")
        right_frame = ttk.Frame(parent, borderwidth=1, relief="solid")
        left_frame.grid(row=1, column=0, padx=10, sticky="nsew")
        right_frame.grid(row=1, column=1, padx=10, sticky="nsew")

        self.left_image_label = ttk.Label(left_frame)
        self.left_image_label.pack(expand=True)
        self.right_image_label = ttk.Label(right_frame)
        self.right_image_label.pack(expand=True)

        # 底部操作按鈕
        bottom_left = ttk.Frame(parent)
        bottom_right = ttk.Frame(parent)
        bottom_left.grid(row=2, column=0, pady=10)
        bottom_right.grid(row=2, column=1, pady=10)

        ttk.Button(bottom_left, text="手動校正").pack(side="left", padx=5)
        ttk.Button(bottom_right, text="手動校正").pack(side="left", padx=5)


    def create_file_selector(self, label_text, path_var, id, row):
        """
        建立一列輸入排版，放入左側的 input_frame 中第 row 行。
        """
        label = ttk.Label(self.input_frame, text=label_text, width=15)
        entry = ttk.Entry(self.input_frame, textvariable=path_var, width=40)
        browse = ttk.Button(self.input_frame, text="瀏覽", command=lambda: self.select_file(path_var))
        error_label = ttk.Label(self.input_frame, text="", foreground="red")

        label.grid(row=row, column=0, padx=5, pady=5, sticky="w")
        entry.grid(row=row, column=1, padx=5, pady=5, sticky="we")
        browse.grid(row=row, column=2, padx=5, pady=5)
        error_label.grid(row=row, column=3, padx=5, pady=5, sticky="w")

        # 儲存錯誤提示 label
        self.error_labels[id] = error_label

    def update_correction(self):
        pass

    def select_file(self, path_var):
        """點擊選擇檔案的地方，選擇檔案"""
        file_path = filedialog.askopenfilename(filetypes=[("PDF Files", "*.pdf")])
        if file_path:
            path_var.set(file_path)

            # 同步更新到 App 的 shared_data
            if path_var == self.front_path:
                self.controller.shared_data["front_path"] = file_path
                self.input_is_valid("front")
                self.update_correction("front")
            elif path_var == self.back_path:
                self.controller.shared_data["back_path"] = file_path
                self.input_is_valid("back")
                self.update_correction("back")
                
            self.controller.frames[AccessPage].event_generate("<<PDFPATHS_UPDATED>>")
            
    def input_is_valid(self,id):
        if (id == "front"):
            cur = self.front_path.get()
        else:
            cur = self.back_path.get()
        valid, message = PDFViewer.is_valid_pdf(cur)
        if (valid):
            self.error_labels[id].config(text="")
        else:
            self.error_labels[id].config(text=f"正面 PDF 無效, {message}")
        return valid

    @Debug.event(color="magenta")
    def go_to_main_page(self):
        print("切換頁面前的 shared_data：", self.controller.shared_data)
        
        if not (self.input_is_valid("front") and self.input_is_valid("back")):
            return
        
        self.controller.show_frame(AccessPage)
