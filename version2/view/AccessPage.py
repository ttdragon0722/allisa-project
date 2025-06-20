import tkinter as tk
from tkinter import ttk
from tkinter import filedialog
from tkinter import messagebox
from tkinter import Toplevel, Scrollbar, Canvas

from lib.PDFViewer import PDFViewer
from lib.ExcelReader import ExcelReader
from lib.data.models import FoundResult
from lib.CV2ImageProcessor import DisplayEngine

from lib.View import ViewResult
from lib.debug import Debug


class AccessPage(tk.Frame):
    def __init__(self, parent, controller):
        # 初始化
        super().__init__(parent)
        self.controller = controller
        self.window_width = 1440
        self.window_height = 810

        # 讀取PDF正反面的路徑
        self.pdf_viewer = PDFViewer(
            self.controller.shared_data.get("front_path", ""),
            self.controller.shared_data.get("back_path", "")
        )
        
        # Excel Read Engine
        self.excel_reader = ExcelReader()
        
        # View Result Engine
        self.view_result = ViewResult()
        
        # View Display Engine
        self.zoom_engine = DisplayEngine()
        self.minimap_engine = DisplayEngine()
        

        self.bind("<<PDFPATHS_UPDATED>>", self.on_pdf_update)

        self.build_ui()
    
    # Func: 讀取全域變數的路徑
    def get_shared_paths(self):
        """Func: 讀取全域變數的pdf路徑"""
        front = self.controller.shared_data.get("front_path", "")
        back = self.controller.shared_data.get("back_path", "")
        return front,back
    
    # Debug
    @Debug.event(color="magenta")
    def load_shared_data(self):
        """Debug: 輸出共享變數"""
        front, back = self.get_shared_paths()

        print("AccessPage 收到的正面 PDF 路徑：", front)
        print("AccessPage 收到的反面 PDF 路徑：", back)

    # Event: 路徑改變
    @Debug.event("Event")
    def on_pdf_update(self,event):
        """pdf 路徑更新事件"""
        print("set pdf paths")
        
        f,b = self.get_shared_paths()
        self.pdf_viewer.front.path = f
        self.pdf_viewer.back.path = b
        

    # View: Excel功能列
    def build_excel_section(self, parent_frame):
        """View: 建立 Excel 功能區塊"""
        style = ttk.Style()
        style.configure('Title.TLabel', font=('Arial', 16, 'bold'), foreground='white', background='#ff7f00')
        style.configure('Status.TLabel', relief='sunken', background='white', padding=5)
        style.configure('TButton', font=('Arial', 12))

        
        self.excel_frame = tk.Frame(parent_frame, bg='orange')
        self.excel_frame.pack(fill='x', pady=5)
        
        title = ttk.Label(
            self.excel_frame,
            text='輸入重工資料：',
            font=('Arial', 15),
            anchor='w',
            style='Title.TLabel',
        )
        title.pack(padx=10, pady=10, fill='x')

        self.excel_status_label = ttk.Label(
            self.excel_frame, 
            text="", width=30, anchor="w", 
            relief="sunken",
            style='Status.TLabel'
        )
        self.excel_status_label.pack(side="left", padx=(10, 5), pady=5)

        self.eye_button = tk.Button(self.excel_frame, text="👁", command=self.show_excel_preview)
        self.eye_button.pack(side="left", padx=5)
        self.eye_button.pack_forget()  # 一開始隱藏眼睛按鈕

        browse_button = tk.Button(self.excel_frame, text="輸入Excel", command=self.import_excel)
        browse_button.pack(side="left", padx=10, pady=5)
        
    # View: 搜尋結果
    def build_search_result_section(self, parent_frame):
        """View: 建立搜尋結果顯示區塊"""
        style = ttk.Style()
        style.configure('ResultTitle.TLabel', font=('Arial', 14, 'bold'), foreground='white', background='#1e90ff')
        style.configure('ResultText.TLabel', font=('Arial', 12), background='white', relief='sunken', padding=5)

        self.search_result_frame = tk.Frame(parent_frame, bg='#1e90ff')
        self.search_result_frame.pack(fill='x', pady=5)

        title = ttk.Label(
            self.search_result_frame,
            text="搜尋結果：",
            anchor='w',
            style='ResultTitle.TLabel'
        )
        title.pack(padx=10, pady=(10, 5), fill='x')

        self.search_result_label = ttk.Label(
            self.search_result_frame,
            text="尚未搜尋",
            anchor='w',
            style='ResultText.TLabel',
            justify='left'
        )
        self.search_result_label.pack(padx=10, pady=(0, 10), fill='x')
        
        self.prev_button = ttk.Button(self.search_result_frame, text='上一個', command=self.on_prev,state='disabled')
        self.next_button = ttk.Button(self.search_result_frame, text='下一個', command=self.on_next,state='disabled')
        self.prev_button.pack(side='left', padx=5)
        self.next_button.pack(side='left', padx=5)

        # 先隱藏整個搜尋結果區塊
        self.search_result_frame.pack_forget()

    # View: 更新搜尋結果
    def update_search_result(self, found_result: FoundResult):
        """View: 更新搜尋結果view"""
        # 更新文字
        self.search_result_label.config(
            text=f"搜尋結果，共找到 {found_result.total} 個對應零件。"
        )
        # 顯示搜尋結果區塊
        self.search_result_frame.pack(fill='x', pady=5)
        
        if self.view_result.screens_length() > 1:
            self.next_button.config(state='normal')


    # Func: 匯入 Excel 檔案
    @Debug.event(color="magenta")
    def import_excel(self):
        """Func: 匯入 Excel 檔案"""
        file_path = filedialog.askopenfilename(
            filetypes=[("Excel Files", "*.xlsx *.xls")],
            title="選擇 Excel 檔案"
        )
        if file_path:
            try:
                self.excel_reader.import_excel(file_path)
                file_name = self.excel_reader.get_fileName()
                self.excel_status_label.config(text=file_name)
                self.eye_button.pack(side="left", padx=5)  # 顯示眼睛按鈕
                print("匯入成功:", self.excel_reader.get_keywords())
            except Exception as e:
                self.excel_status_label.config(text="")
                self.eye_button.pack_forget()
                messagebox.showerror("匯入失敗", str(e))

    # View: Excel Modal
    def show_excel_preview(self):
        """彈出視窗顯示 Excel 表格資料（支援第一列為標題）"""
        preview_data = self.excel_reader.get_table()
        if not preview_data or len(preview_data) < 2:
            messagebox.showinfo("提示", "無可顯示的 Excel 資料")
            return

        # 拆出欄位名稱與資料列
        headers = preview_data[0]
        rows = preview_data[1:]

        preview_win = Toplevel(self)
        preview_win.title(f"Excel 預覽: {self.excel_reader.get_fileName()}")
        preview_win.geometry("700x400")

        # 建立表格容器
        tree_frame = ttk.Frame(preview_win)
        tree_frame.pack(fill="both", expand=True)

        # 垂直捲動條
        y_scrollbar = ttk.Scrollbar(tree_frame, orient="vertical")
        y_scrollbar.pack(side="right", fill="y")

        # Treeview
        tree = ttk.Treeview(
            tree_frame,
            columns=[f"col{i}" for i in range(len(headers))],
            show="headings",
            yscrollcommand=y_scrollbar.set
        )
        tree.pack(fill="both", expand=True)
        y_scrollbar.config(command=tree.yview)

        # 設定欄位標題
        for i, header in enumerate(headers):
            col_id = f"col{i}"
            tree.heading(col_id, text=str(header))
            tree.column(col_id, width=150, anchor="w")

        # 插入資料
        for row in rows[:100]:
            tree.insert("", "end", values=row)

    # View: UI Display 
    def build_ui(self):
        container = tk.Frame(self)
        container.pack(fill='both', expand=True)

        # 左側 Zoom 顯示
        self.left_frame = tk.Frame(container, bg='lightblue', width=int(self.window_width * 0.7))
        self.left_frame.pack(side='left', fill='both')
        self.left_frame.pack_propagate(False)
        self.zoom_label = tk.Label(self.left_frame, text='Zoom Area', bg='lightblue')
        self.zoom_label.pack(expand=True)
        
        
        

        self.front_label = ttk.Label(self.left_frame, text=f"正面開啟檔案：")
        self.front_label.pack(fill='x')

        self.back_label = ttk.Label(self.left_frame, text=f"背面開啟檔案：")
        self.back_label.pack(fill='x')

        # 右側功能區
        right_frame = tk.Frame(container, width=int(self.window_width * 0.3),height=self.window_height, bg='gray')
        right_frame.pack(side='right', fill='both')
        right_frame.pack_propagate(False)

        # 右上 Function 區
        top_right = tk.Frame(right_frame, height=int(self.window_height * 0.35), bg='orange')
        top_right.pack(fill='x')
        top_right.pack_propagate(False)

        # label_b = tk.Label(top_right, text='Function Area', bg='orange', font=('Arial', 15))
        # label_b.pack(padx=10, pady=10)

        # self.entry = ttk.Entry(top_right)
        # self.entry.pack(pady=5, padx=10)


        # self.status_label = ttk.Label(top_right, text="尚未搜尋")
        # self.status_label.pack(side='top', pady=2)
        
        self.build_excel_section(top_right)
        
        search_btn = ttk.Button(top_right, text='使用重工資料搜尋', command=self.search_pdf)
        search_btn.pack(pady=5)
        
        self.build_search_result_section(top_right)

        # 右下 Minimap 區
        self.bottom_right = tk.Frame(right_frame, bg='lightgray',height=self.window_height*0.65)
        self.bottom_right.pack(fill='both', expand=True)
        self.bottom_right.pack_propagate(True)
        self.minimap_label = tk.Label(self.bottom_right, text='Minimap Area', bg='lightgray')
        self.minimap_label.pack(expand=True,fill="both")

        # 翻頁按鈕
        # self.prev_button = tk.Button(self, text="上一個", command=self.show_previous_result)
        # self.next_button = tk.Button(self, text="下一個", command=self.show_next_result)
        # self.prev_button.pack(side="left", padx=5)
        # self.next_button.pack(side="left", padx=5)

        # self.prev_button.config(state='disabled')
        # self.next_button.config(state='disabled')

    # View: UI Tool Bar
    @property
    def menu(self):
        menu = tk.Menu(self.controller)

        # 建立檔案選單
        file_menu = tk.Menu(menu, tearoff=0)
        file_menu.add_command(label="除錯", command=self.load_shared_data)
        file_menu.add_separator()

        # 建立編輯選單
        edit_menu = tk.Menu(menu, tearoff=0)
        edit_menu.add_command(label="剪下", command=self.load_shared_data)
        edit_menu.add_command(label="複製", command=self.load_shared_data)
        edit_menu.add_command(label="貼上", command=self.load_shared_data)

        # 建立「編輯檔案路徑」子選單
        path_menu = tk.Menu(edit_menu, tearoff=0)
        path_menu.add_command(label="載入路徑 A", command=self.load_shared_data)
        path_menu.add_command(label="載入路徑 B", command=self.load_shared_data)

        # 加入「編輯檔案路徑」子選單到編輯選單
        edit_menu.add_cascade(label="編輯檔案路徑", menu=path_menu)

        # 建立「群組操作」子選單
        group_menu = tk.Menu(edit_menu, tearoff=0)
        group_menu.add_command(label="操作 1", command=self.load_shared_data)
        group_menu.add_command(label="操作 2", command=self.load_shared_data)

        # 加入「群組操作」子選單到編輯選單
        edit_menu.add_cascade(label="群組操作", menu=group_menu)

        # 將選單加入主選單列
        menu.add_cascade(label="檔案", menu=file_menu)
        menu.add_cascade(label="編輯", menu=edit_menu)

        return menu


    @Debug.event("CLUSTER DATA","green")
    def update_ui(self):
        self.prev_button.config(
            state="normal" if self.view_result.cur_idx > 0 else "disabled")
        self.next_button.config(
            state="normal" if self.view_result.cur_idx < self.view_result.screens_length() - 1 else "disabled")
        self.display_pdf()
        self.view_result.current_log()
        

    @Debug.event("BUTTON", "cyan")
    def on_prev(self):
        if not self.view_result.check_bounds("prev"):
            self.update_ui()
            return
        self.view_result.cur_idx -= 1
        print("👈 上一個")
        self.update_ui()

    @Debug.event("BUTTON", "cyan")
    def on_next(self):
        if not self.view_result.check_bounds("next"):
            self.update_ui()
            return
        self.view_result.cur_idx += 1
        print("👉 下一個")
        self.update_ui()

    # Func: 搜尋按鈕
    @Debug.event(color="yellow")
    def search_pdf(self):
        """搜尋function"""
        # excel 拿到關鍵字
        keywords = self.excel_reader.get_keywords()
        # 搜尋結果
        result = self.pdf_viewer.search_pdf_multiple(keywords)
        
        print("搜尋資料：",keywords)
        print(result)
        
        # 更新狀態
        self.view_result.set_result(result)
        self.set_pdf_zoom_and_minimap()
        
        # View: 更新搜尋結果
        self.update_search_result(result)
        
        # View 呈現 呈現兩張PDF Zoom區塊&Minimap
        self.display_pdf()
        
    def set_minimap(self):
        """minimap搜尋結果 設定資料""" 
        zoom = 0.8
        scale = 1
        self.minimap_engine.set_result(
            (
                self.pdf_viewer.front.get_pixmap(zoom),
                self.pdf_viewer.back.get_pixmap(zoom),
            ),
            self.view_result.result,
            zoom,
            scale
        )
        self.minimap_engine.draw_bounding_box(
            (
                self.pdf_viewer.front.bounding_box,
                self.pdf_viewer.back.bounding_box
            )
        )
    
    def set_pdf_zoom(self):
        """zoom搜尋結果 設定資料"""
        zoom = 5
        self.zoom_engine.set_result(
            (
                self.pdf_viewer.front.get_pixmap(zoom),
                self.pdf_viewer.back.get_pixmap(zoom),
            ),
            self.view_result.result,
            zoom,
            1,
            1
        )
        print(self.view_result.group_DBSCAN())

    def set_pdf_zoom_and_minimap(self):
        """Function: 設定結果資料"""
        self.set_minimap()
        self.set_pdf_zoom()
        
        
    def display_zoom(self,cur_page):
        """View: zoom 呈現"""
        img_tk = self.zoom_engine.get_zoom(self.view_result.screens[self.view_result.cur_idx])
        self.zoom_label.configure(image=img_tk)
        self.zoom_label.image = img_tk  # 防止被 GC 回收
    
    def display_minimap(self,cur_page):
        """View: mini map呈現"""
        img_tk = self.minimap_engine.get_image(
            cur_page,
            self.minimap_engine.draw_relative_position,
            self.view_result.current_screen()
            )
        self.minimap_label.configure(image=img_tk)
        self.minimap_label.image = img_tk  # 防止被 GC 回收
    
    def display_pdf(self):
        """View: 呈現pdf"""
        cur_page = self.view_result.current_page()
        self.display_zoom(cur_page)
        self.display_minimap(cur_page)