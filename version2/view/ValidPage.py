import tkinter as tk
from tkinter import ttk

from lib.debug import Debug
from lib.PDFViewer import PDFViewer
from lib.CV2ImageProcessor import DisplayEngine

from .AccessPage import AccessPage

import threading


class ValidPage(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        
        self.build_ui()
        
        self.display_engine = DisplayEngine()
        
        self.bind("<<PDFPATHS_UPDATED>>", self.on_pdf_update)
        
    def get_shared_paths(self):
        """Func: 讀取全域變數的pdf路徑"""
        front = self.controller.shared_data.get("front_path", "")
        back = self.controller.shared_data.get("back_path", "")
        return front,back
        
    @Debug.event("Event: ValidPage")
    def on_pdf_update(self, event):
        print("set pdf paths")

        # 開始進度條動畫
        self.progress.start()

        # 用 thread 執行長時間任務，避免卡 UI
        threading.Thread(target=self.run_pdf_processing).start()
        
    def run_pdf_processing(self):
        f, b = self.get_shared_paths()
        self.pdf_viewer = PDFViewer(f, b)
        
        self.front_label.config(text=f"正面檔案路徑：{f}")
        self.back_label.config(text=f"背面檔案路徑：{b}")

        # === 前面處理 ===
        self.pdf_viewer.front.get_trimmed_bounding_box_v6(0)
        self.after(0, lambda: self.progress.config(value=50))  # 更新為 50%

        # === 背面處理 ===
        self.pdf_viewer.back.get_trimmed_bounding_box_v6(0)
        self.after(0, lambda: self.progress.config(value=100))  # 更新為 100%

        # === 回主線程更新畫面 ===
        self.after(0, self.update_ui_after_processing)

    @Debug.event("Process Finish","red")
    def update_ui_after_processing(self):
        self.progress.stop()  # 停止進度條
        self.progress.pack_forget()  # 移除元件

        print(self.pdf_viewer.front.bounding_box)
        print(self.pdf_viewer.back.bounding_box)
        
        self.build_image_ui(self.image_ui_container)
        
        self.display_engine.set_valid(
            [self.pdf_viewer.front,self.pdf_viewer.back]
        )
        
        left = self.display_engine.get_image("front")
        right = self.display_engine.get_image("back")
        
        self.left_image_label.configure(image=left)
        self.left_image_label.image = left  # 防止被 GC 回收
        
        self.right_image_label.configure(image=right)
        self.right_image_label.image = right  # 防止被 GC 回收


    def enter_search_page(self):
        self.controller.show_frame(AccessPage)
        # 可在此加入頁面跳轉邏輯
        self.controller.shared_data["pdf_engine"] = self.pdf_viewer
        self.controller.frames[AccessPage].event_generate("<<PDF_ENGINE_UPDATE>>")
        
        
    def build_ui(self):
        # 外層容器框架，用來包裹所有元件
        outer_frame = tk.Frame(self)
        outer_frame.pack(fill="both", expand=True)
        
        title_frame = ttk.Frame(outer_frame)
        title_frame.pack(anchor="w", padx=10, pady=(10, 0))

        # 左側標題
        title_label = ttk.Label(title_frame, text="確認輸入檔案：", font=("Arial", 12, "bold"))
        title_label.pack(side="left")

        # 右側按鈕
        search_button = ttk.Button(title_frame, text="進入搜尋頁面", command=self.enter_search_page)
        search_button.pack(side="right")
        
        self.front_label = ttk.Label(outer_frame, text="正面檔案路徑：", font=("Arial", 10, "bold"))
        self.front_label.pack(anchor="w", padx=5, pady=(10, 0))
    
        self.back_label = ttk.Label(outer_frame, text="背面檔案路徑：", font=("Arial", 10, "bold"))
        self.back_label.pack(anchor="w", padx=5, pady=(10, 0))
        
        note_label = tk.Label(
            outer_frame,
            text="* note: 如果檔案沒有畫出黃色的區塊代表pdf檔案有出問題。請再注意",
            font=("Arial", 12, "bold"),
            fg="red",
            wraplength=1000,
            justify="left"
        )
        note_label.pack(anchor="w", padx=10, pady=(15, 0))
        
        # === 進度條 ===
        self.progress = ttk.Progressbar(outer_frame, mode='determinate', length=200)
        self.progress.pack(pady=10)
        self.progress.stop()
        # === 建立可捲動容器 ===
        scroll_frame = ttk.Frame(outer_frame)
        scroll_frame.pack(fill="both", expand=True, pady=20)

        # Canvas 是捲動的基礎
        canvas = tk.Canvas(scroll_frame)
        canvas.pack(side="left", fill="both", expand=True)

        # Scrollbar 放右邊
        scrollbar = ttk.Scrollbar(scroll_frame, orient="vertical", command=canvas.yview)
        scrollbar.pack(side="right", fill="y")

        # 讓 canvas 跟 scrollbar 綁在一起
        canvas.configure(yscrollcommand=scrollbar.set)

        # === Frame 放進 Canvas 裡 ===
        self.image_ui_container = ttk.Frame(canvas)

        # 將 image_ui_container 放入 Canvas 的視圖內
        canvas.create_window((0, 0), window=self.image_ui_container, anchor="nw")

        # 當 image_ui_container 大小變動時，自動調整 scroll 區域
        def on_frame_configure(event):
            canvas.configure(scrollregion=canvas.bbox("all"))
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")

        canvas.bind_all("<MouseWheel>", _on_mousewheel)  # Windows

        self.image_ui_container.bind("<Configure>", on_frame_configure)
        
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