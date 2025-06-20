import tkinter as tk
from PIL import Image, ImageTk
import cv2
import numpy as np
import fitz  # PyMuPDF

def search_and_zoom_with_minimap(pdf_path, keyword, page_num=0):
    keyword = keyword.lower()
    doc = fitz.open(pdf_path)
    page = doc.load_page(page_num)

    blocks = page.get_text('blocks')
    target_box = None
    for b in blocks:
        x0, y0, x1, y1, text, *_ = b
        if keyword in text.lower():
            target_box = (int(x0), int(y0), int(x1), int(y1))
            break
    if target_box is None:
        print(f"找不到關鍵字「{keyword}」")
        return None, None

    zoom = 8
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat)
    img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n).copy()
    if pix.n == 4:
        img = cv2.cvtColor(img, cv2.COLOR_RGBA2BGR)
    elif pix.n == 1:
        img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)

    output_x, output_y = 400, 300
    x0, y0, x1, y1 = target_box
    cx = int((x0 + x1) / 2 * zoom)
    cy = int((y0 + y1) / 2 * zoom)

    left = max(cx - output_x // 2, 0)
    right = min(cx + output_x // 2, img.shape[1])
    top = max(cy - output_y // 2, 0)
    bottom = min(cy + output_y // 2, img.shape[0])

    zoomed = img[top:bottom, left:right]
    zoomed = cv2.resize(zoomed, (output_x, output_y), interpolation=cv2.INTER_CUBIC)

    box_x0 = int((x0 * zoom) - left)
    box_y0 = int((y0 * zoom) - top)
    box_x1 = int((x1 * zoom) - left)
    box_y1 = int((y1 * zoom) - top)
    cv2.rectangle(zoomed, (box_x0, box_y0), (box_x1, box_y1), (0, 0, 255), 2)

    label = keyword.upper()
    box_w, box_h = 80, 30
    label_pos = (box_x1 + 10, box_y0 - 10)
    if label_pos[0] + box_w > zoomed.shape[1]:
        label_pos = (box_x0 - box_w - 10, label_pos[1])
    if label_pos[1] < 0:
        label_pos = (label_pos[0], 10)
    cv2.rectangle(zoomed, label_pos, (label_pos[0] + box_w, label_pos[1] + box_h), (0, 255, 255), -1)
    cv2.putText(zoomed, label, (label_pos[0] + 5, label_pos[1] + 22),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)
    arrow_start = (label_pos[0], label_pos[1] + box_h // 2)
    arrow_end = (box_x1, box_y0 + (box_y1 - box_y0) // 2)
    cv2.arrowedLine(zoomed, arrow_start, arrow_end, (0, 255, 255), 2, tipLength=0.2)

    minimap_scale = 0.1
    minimap = cv2.resize(img, (int(img.shape[1]*minimap_scale), int(img.shape[0]*minimap_scale)), interpolation=cv2.INTER_AREA)
    mm_box_x0 = int(left * minimap_scale)
    mm_box_y0 = int(top * minimap_scale)
    mm_box_x1 = int(right * minimap_scale)
    mm_box_y1 = int(bottom * minimap_scale)
    cv2.rectangle(minimap, (mm_box_x0, mm_box_y0), (mm_box_x1, mm_box_y1), (0, 0, 255), 1)

    return zoomed, minimap

def cv_img_to_tk_img(cv_img):
    cv_img = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
    pil_img = Image.fromarray(cv_img)
    return ImageTk.PhotoImage(pil_img)

def create_app(pdf_path):
    root = tk.Tk()
    root.title("PDF 搜尋放大器")

    container = tk.Frame(root)
    container.pack(fill='both', expand=True)

    # 左邊放放大圖和小地圖
    left_frame = tk.Frame(container)
    left_frame.pack(side='left', padx=10, pady=10)

    zoom_label = tk.Label(left_frame)
    zoom_label.pack(pady=5)

    minimap_label = tk.Label(left_frame)
    minimap_label.pack(pady=5)

    # 右邊放輸入框跟按鈕
    right_frame = tk.Frame(container)
    right_frame.pack(side='left', padx=10, pady=10)

    tk.Label(right_frame, text="輸入關鍵字搜尋：").pack(pady=5)
    entry = tk.Entry(right_frame, width=20, font=('Arial', 16))
    entry.pack(pady=5)

    def on_search():
        keyword = entry.get()
        if not keyword:
            print("請輸入關鍵字")
            return

        zoomed_img, minimap_img = search_and_zoom_with_minimap(pdf_path, keyword)
        if zoomed_img is None:
            zoom_label.config(text=f"找不到關鍵字「{keyword}」")
            minimap_label.config(image='')
            zoom_label.image = None
            minimap_label.image = None
            return

        zoom_tk = cv_img_to_tk_img(zoomed_img)
        minimap_tk = cv_img_to_tk_img(minimap_img)

        zoom_label.config(image=zoom_tk, text='')
        zoom_label.image = zoom_tk
        minimap_label.config(image=minimap_tk)
        minimap_label.image = minimap_tk

    btn = tk.Button(right_frame, text="搜尋", command=on_search)
    btn.pack(pady=10)

    root.mainloop()

if __name__ == "__main__":
    pdf_path = "sample.pdf"  # 你的 PDF 路徑
    create_app(pdf_path)
