import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
from tkinter import messagebox

import fitz  # PyMuPDF
import cv2
import numpy as np

pdf_path = 'C:/Users/Rex/Downloads/alisa project/source/ADN253_RA1-T.pdf'  # <-- 可改為你的 PDF 路徑
class PDFViewerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("PDF Zoom Viewer")
        self.window_width = 1440
        self.window_height = 810
        self.root.geometry(f"{self.window_width}x{self.window_height}")
        self.root.resizable(False, False)
        self.build_ui()

        # 初始化屬性
        self.doc = None
        self.target_boxes = []
        self.current_target_index = 0
        self.page_num = 0
        self.pdf_path = pdf_path  # 你預設的 PDF 路徑
        

        self.show_pdf_zoom_and_minimap(self.pdf_path, keyword="")

    def build_ui(self):
        container = tk.Frame(self.root)
        container.pack(fill='both', expand=True)

        # 左側 Zoom 顯示
        self.left_frame = tk.Frame(container, bg='lightblue', width=int(self.window_width * 0.7))
        self.left_frame.pack(side='left', fill='both')
        self.left_frame.pack_propagate(False)
        self.zoom_label = tk.Label(self.left_frame, text='Zoom Area', bg='lightblue')
        self.zoom_label.pack(expand=True)

        # 右側功能區
        right_frame = tk.Frame(container, width=int(self.window_width * 0.3), bg='gray')
        right_frame.pack(side='right', fill='y')
        right_frame.pack_propagate(False)

        # 右上 Function 區
        top_right = tk.Frame(right_frame, height=int(self.window_height * 0.3), bg='orange')
        top_right.pack(fill='x')
        top_right.pack_propagate(False)

        label_b = tk.Label(top_right, text='Function Area', bg='orange', font=('Arial', 20))
        label_b.pack(padx=10, pady=10)

        self.entry = ttk.Entry(top_right)
        self.entry.pack(pady=5, padx=10)

        search_btn = ttk.Button(top_right, text='Search', command=self.search_pdf)
        search_btn.pack(pady=5)

        # 右下 Minimap 區
        self.bottom_right = tk.Frame(right_frame, bg='lightgray')
        self.bottom_right.pack(fill='both', expand=True)
        self.bottom_right.pack_propagate(False)
        self.minimap_label = tk.Label(self.bottom_right, text='Minimap Area', bg='lightgray')
        self.minimap_label.pack(expand=True)

        # 翻頁按鈕
        self.prev_button = tk.Button(self.root, text="上一個", command=self.show_previous_result)
        self.next_button = tk.Button(self.root, text="下一個", command=self.show_next_result)
        self.prev_button.pack(side="left", padx=5)
        self.next_button.pack(side="left", padx=5)

        # 一開始禁用上一個/下一個
        self.prev_button.config(state='disabled')
        self.next_button.config(state='disabled')
        
        self.status_label = ttk.Label(top_right, text="尚未搜尋")
        self.status_label.pack(side='top', pady=2)

    def search_pdf(self):
        keyword = self.entry.get()
        if not keyword:
            return
        self.show_pdf_zoom_and_minimap(self.pdf_path, keyword)
        
        # 加這行：更新搜尋結果顯示文字
        total = len(self.target_boxes)
        if total:
            self.status_label.config(text=f"搜尋到 {total} 筆結果")
        else:
            self.status_label.config(text="找不到結果")

    def show_pdf_zoom_and_minimap(self, pdf_path, keyword, page_num=0):
        try:
            self.doc = fitz.open(pdf_path)
        except Exception as e:
            messagebox.showerror("錯誤", f"無法開啟 PDF：{e}")
            return

        if page_num >= len(self.doc):
            messagebox.showerror("錯誤", f"頁數 {page_num} 超出範圍，PDF 僅有 {len(self.doc)} 頁。")
            return

        self.page_num = page_num
        self.current_target_index = 0
        keyword = (keyword or "").strip().lower()
        page = self.doc.load_page(page_num)
        blocks = page.get_text('blocks')

        self.target_boxes = []
        if keyword:
            for b in blocks:
                x0, y0, x1, y1, text, *_ = b
                if keyword in text.lower():
                    self.target_boxes.append((int(x0), int(y0), int(x1), int(y1), text))

            if self.target_boxes:
                print(f"找到 {len(self.target_boxes)} 個符合關鍵字的區域")
            else:
                messagebox.showwarning("搜尋結果", f"找不到關鍵字：'{keyword}'")

        # 按鈕狀態更新
        self._update_navigation_buttons()

        # 顯示目前選中的結果
        self._render_current_target()

    def _render_current_target(self):
        if not self.doc:
            return
        page = self.doc.load_page(self.page_num)

        # 取得目標區域
        target_box = None
        if self.target_boxes:
            target_box = self.target_boxes[self.current_target_index]

        zoom = 5
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat)

        img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n).copy()
        if pix.n == 4:
            img = cv2.cvtColor(img, cv2.COLOR_RGBA2BGR)
        elif pix.n == 1:
            img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)

        output_x = 400
        output_y = 300

        if target_box:
            x0, y0, x1, y1, text = target_box

            cx = int((x0 + x1) // 2 * zoom)
            cy = int((y0 + y1) // 2 * zoom)

            left = max(cx - output_x // 2, 0)
            right = min(cx + output_x // 2, img.shape[1])
            top = max(cy - output_y // 2, 0)
            bottom = min(cy + output_y // 2, img.shape[0])

            zoomed = img[top:bottom, left:right]
            box_x0 = int(x0 * zoom) - left
            box_y0 = int(y0 * zoom) - top
            box_x1 = int(x1 * zoom) - left
            box_y1 = int(y1 * zoom) - top
            zoomed = cv2.resize(zoomed, (zoomed.shape[1] * 2, zoomed.shape[0] * 2), interpolation=cv2.INTER_CUBIC)

            box_x0 *= 2
            box_y0 *= 2
            box_x1 *= 2
            box_y1 *= 2

            cv2.rectangle(zoomed, (box_x0, box_y0), (box_x1, box_y1), (0, 0, 255), 2)

            max_label_len = 20
            label = text[:max_label_len].replace('\n', ' ').strip()
            if len(text) > max_label_len:
                label += "..."

            label_pos = (box_x1 + 10, box_y0 - 10)
            if label_pos[0] + 80 > zoomed.shape[1]:
                label_pos = (box_x0 - 90, label_pos[1])
            if label_pos[1] < 0:
                label_pos = (label_pos[0], 10)

            cv2.rectangle(zoomed, label_pos, (label_pos[0] + 80, label_pos[1] + 30), (0, 255, 255), -1)
            cv2.putText(zoomed, label, (label_pos[0] + 5, label_pos[1] + 22),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)
            cv2.arrowedLine(zoomed, (label_pos[0], label_pos[1] + 15), (box_x1, box_y0 + (box_y1 - box_y0) // 2),
                            (0, 255, 255), 2, tipLength=0.2)
        else:
            zoomed = img

        self.update_image(self.zoom_label, zoomed)

        # Minimap 繪製
        mat_minimap = fitz.Matrix(0.7, 0.7)
        pix_minimap = page.get_pixmap(matrix=mat_minimap)
        img_minimap = np.frombuffer(pix_minimap.samples, dtype=np.uint8).reshape(pix_minimap.height, pix_minimap.width,
                                                                              pix_minimap.n).copy()

        if pix_minimap.n == 4:
            img_minimap = cv2.cvtColor(img_minimap, cv2.COLOR_RGBA2BGR)
        elif pix_minimap.n == 1:
            img_minimap = cv2.cvtColor(img_minimap, cv2.COLOR_GRAY2BGR)

        scale = 0.5  # 縮放比例

        # 標示所有關鍵字區域 (紅框)
        for box in self.target_boxes:
            x0, y0, x1, y1 = box[0:4]
            cv2.rectangle(
                img_minimap,
                (int(x0 * scale), int(y0 * scale)),
                (int(x1 * scale), int(y1 * scale)),
                (0, 0, 255),
                2
            )

        # 標示放大區域 (綠框)
        if target_box:
            cx = int(((target_box[0] + target_box[2]) / 2) * zoom)
            cy = int(((target_box[1] + target_box[3]) / 2) * zoom)

            left = max(cx - output_x // 2, 0)
            right = min(cx + output_x // 2, img.shape[1])
            top = max(cy - output_y // 2, 0)
            bottom = min(cy + output_y // 2, img.shape[0])

            minimap_left = int(left / zoom * scale)
            minimap_right = int(right / zoom * scale)
            minimap_top = int(top / zoom * scale)
            minimap_bottom = int(bottom / zoom * scale)

            cv2.rectangle(
                img_minimap,
                (minimap_left, minimap_top),
                (minimap_right, minimap_bottom),
                (0, 255, 0),  # 綠色框
                2
            )

        self.update_image(self.minimap_label, img_minimap)

    def update_image(self, widget, cv_img):
        img_rgb = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
        img_pil = Image.fromarray(img_rgb)
        img_tk = ImageTk.PhotoImage(img_pil)
        widget.configure(image=img_tk)
        widget.image = img_tk  # 防止被回收

    def show_previous_result(self):
        if self.current_target_index > 0:
            self.current_target_index -= 1
            self._render_current_target()
            self._update_navigation_buttons()

    def show_next_result(self):
        if self.current_target_index < len(self.target_boxes) - 1:
            self.current_target_index += 1
            self._render_current_target()
            self._update_navigation_buttons()
            
    def _update_navigation_buttons(self):
        if len(self.target_boxes) < 2:
            self.prev_button.config(state='disabled')
            self.next_button.config(state='disabled')
            return

        if self.current_target_index <= 0:
            self.prev_button.config(state='disabled')
        else:
            self.prev_button.config(state='normal')

        if self.current_target_index >= len(self.target_boxes) - 1:
            self.next_button.config(state='disabled')
        else:
            self.next_button.config(state='normal')

        if self.target_boxes:
            self.status_label.config(text=f"目前第 {self.current_target_index + 1} 筆，共 {len(self.target_boxes)} 筆")
        else:
            self.status_label.config(text="沒有搜尋結果")



if __name__ == '__main__':
    root = tk.Tk()
    app = PDFViewerApp(root)
    root.mainloop()
