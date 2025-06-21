import tkinter as tk
from tkinter import ttk
from tkinter import messagebox

from lib.FilePicker import FilePicker
from lib.debug import Debug
from lib.data.models import File
from .components import *
from .AccessPage import AccessPage
class FilePickPage(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        
        # 初始化 FilePicker 物件，指定資料夾路徑，負責讀取該資料夾下所有檔案
        self.file_picker: FilePicker = FilePicker("C:/Users/Rex/Downloads/alisa project/source")
        
        # 用於存放畫面上所有 FileBlock 物件，方便管理和更新
        self.file_blocks = []
        
        # 建立 UI 元件
        self.build_ui()
    
    def build_ui(self):
        # 外層容器框架，用來包裹所有元件
        outer_frame = tk.Frame(self)
        outer_frame.pack(fill="both", expand=True)

        # 標題文字顯示 "輸入開啟檔案："
        title_label = ttk.Label(outer_frame, text="輸入開啟檔案：", font=("Arial", 12, "bold"))
        title_label.pack(anchor="w", padx=10, pady=(10, 0))

        # 正面與背面路徑變數，用 StringVar 方便綁定與更新
        self.front_path = tk.StringVar()
        self.back_path = tk.StringVar()

        # 清除正面檔案路徑的函式，會清空變數並更新畫面
        def clear_front():
            self.front_path.set("")
            self.update_file_blocks()

        # 清除背面檔案路徑的函式，會清空變數並更新畫面
        def clear_back():
            self.back_path.set("")
            self.update_file_blocks()

        # 正面與背面路徑顯示欄的框架
        path_row_frame = tk.Frame(outer_frame)
        path_row_frame.pack(fill="x", padx=10, pady=5)

        # 正面路徑輸入欄（只讀）+ 清除按鈕，顯示並操作正面檔案路徑
        PathInputRow(
            path_row_frame,
            "現在選取正面檔案：",
            self.front_path,
            clear_front,
            highlight_color="cyan"
        ).pack(side="left", padx=5)

        # 背面路徑輸入欄（只讀）+ 清除按鈕，顯示並操作背面檔案路徑
        PathInputRow(
            path_row_frame,
            "現在選取背面檔案：",
            self.back_path,
            clear_back,
            highlight_color="blue"
        ).pack(side="left", padx=5)

        # 「輸入」按鈕，按下後呼叫 handle_input 處理輸入動作
        ttk.Button(path_row_frame, text="輸入", command=self.handle_input).pack(side="left", padx=10)

        # 搜尋欄的框架，用來放搜尋相關元件
        search_frame = ttk.Frame(outer_frame)
        search_frame.pack(fill="x", padx=10, pady=5)

        # 搜尋圖示與文字標籤
        ttk.Label(search_frame, text="🔍 搜尋檔名：").pack(side="left")
        # 搜尋欄輸入框，綁定 self.search_var
        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(search_frame, textvariable=self.search_var)
        search_entry.pack(side="left", fill="x", expand=True)

        # 監聽搜尋欄文字改變事件，每次改變都呼叫 update_file_blocks 更新檔案顯示
        self.search_var.trace_add("write", lambda *args: self.update_file_blocks())

        # 放置檔案顯示區域的框架（包含可滾動區域）
        canvas_frame = ttk.Frame(outer_frame)
        canvas_frame.pack(fill="both", expand=True)

        # Canvas 用於製作滾動內容區塊
        self.canvas = tk.Canvas(canvas_frame)
        # 垂直滾動條，綁定 canvas 的 yview
        self.scrollbar = ttk.Scrollbar(canvas_frame, orient="vertical", command=self.canvas.yview)
        # 用於裝載檔案元件的內部 Frame，放在 Canvas 裡面
        self.scroll_frame = ttk.Frame(self.canvas)

        # 綁定內部 Frame 尺寸改變事件，更新 Canvas 的 scrollregion 以便滾動
        self.scroll_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        # 將 scroll_frame 放置到 canvas 中，設定置左上錨點
        self.canvas.create_window((0, 0), window=self.scroll_frame, anchor="nw")
        # 將 scrollbar 與 canvas 連動
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        # 佈局 canvas 和 scrollbar
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        # 顯示所有檔案的區塊
        self.update_file_blocks()

    def update_file_blocks(self):
        # 清除之前建立的 FileBlock 元件，避免重複
        for block in self.file_blocks:
            block.destroy()
        self.file_blocks.clear()

        # 取得搜尋關鍵字（小寫）
        keyword = self.search_var.get().strip().lower() if hasattr(self, 'search_var') else ""
        # 如果有輸入關鍵字，從 file_picker 做過濾搜尋
        if keyword:
            filtered_files = self.file_picker.search_files(keyword)
        else:
            filtered_files = self.file_picker.files

        # 設定每列最多放2個檔案區塊
        max_columns = 2
        row = col = 0

        # 逐一產生 FileBlock 元件
        for file in filtered_files:
            block = FileBlock(
                self.scroll_frame,
                file,
                self.set_front_path,
                self.set_back_path,
                self.get_cur_front,
                self.get_cur_back
            )
            # 用 grid 排版，設定邊距與填充
            block.grid(row=row, column=col, padx=10, pady=5, sticky="nsew")
            self.file_blocks.append(block)

            # 排列邏輯，超過 max_columns 換行
            col += 1
            if col >= max_columns:
                col = 0
                row += 1

        # 設定每欄平均寬度分配
        for c in range(max_columns):
            self.scroll_frame.grid_columnconfigure(c, weight=1)

    @Debug.event("set front_path", "blue")
    def set_front_path(self, file: File):
        try:
            # 防呆：如果已是目前正面檔案就跳過
            if self.front_path.get() == file.path:
                print("⚠️ 已經是目前前景檔案，略過。")
                return

            # 防呆：正面、背面不能是同一個檔案
            if self.back_path.get() == file.path:
                messagebox.showwarning("選取錯誤", "不能將相同檔案同時設為前景和背景！")
                return

            print(f"✅ 設定為前景：{file.name}")
            # 設定正面檔案路徑
            self.front_path.set(file.path)
            # 同步更新 controller 中的 shared_data
            self.controller.shared_data["front_path"] = self.get_cur_front()
        finally:
            # 不論是否有回傳都要更新畫面及通知 AccessPage
            self.update_file_blocks()
            self.controller.frames[AccessPage].event_generate("<<PDFPATHS_UPDATED>>")

    @Debug.event("set back_path", "blue")
    def set_back_path(self, file: File):
        try:
            # 防呆：如果已是目前背面檔案就跳過
            if self.back_path.get() == file.path:
                print("⚠️ 已經是目前背景檔案，略過。")
                return

            # 防呆：正面、背面不能是同一個檔案
            if self.front_path.get() == file.path:
                messagebox.showwarning("選取錯誤", "不能將相同檔案同時設為背景和前景！")
                return

            print(f"✅ 設定為背景：{file.name}")
            # 設定背面檔案路徑
            self.back_path.set(file.path)
            # 同步更新 controller 中的 shared_data
            self.controller.shared_data["back_path"] = self.get_cur_back()
        finally:
            # 不論是否有回傳都要更新畫面及通知 AccessPage
            self.update_file_blocks()
            self.controller.frames[AccessPage].event_generate("<<PDFPATHS_UPDATED>>")
        
    # 取得目前正面路徑字串
    def get_cur_front(self):
        return self.front_path.get()

    # 取得目前背面路徑字串
    def get_cur_back(self):
        return self.back_path.get()
    
    @Debug.event("entry", "yellow")
    def handle_input(self):
        front = self.get_cur_front()
        back = self.get_cur_back()
        print(f"- 正面：{front}\n- 背面：{back}")
        # 檢查兩邊路徑都有設定才繼續
        if not front or not back:
            messagebox.showwarning("缺少檔案", "請確認已設定正面與背面檔案。")
            print("⚠️ 尚未完成檔案設定，無法繼續。")
            return
        
        # 路徑都設定後，切換到下一個畫面 AccessPage
        self.controller.show_frame(AccessPage)
