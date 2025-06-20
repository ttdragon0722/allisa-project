import tkinter as tk
from PIL import Image, ImageTk
import cv2
import numpy as np

def create_app():
    root = tk.Tk()
    root.title("自訂版面")

    # 取得螢幕寬高，設定視窗為全螢幕
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    root.geometry(f"{screen_width}x{screen_height}")

    # 主容器：橫向分兩區塊（左 Zoom / 右 Function + MiniMap）
    container = tk.Frame(root)
    container.pack(fill='both', expand=True)

    # 左邊：Zoom 區域（flex: 1）
    zoom_frame = tk.Frame(container, bg='lightblue', width=int(screen_width * 0.7))
    zoom_frame.pack(side='left', fill='both', expand=True)
    zoom_label = tk.Label(zoom_frame, text="Zoom 區域", bg='lightblue')
    zoom_label.pack(expand=True)

    # 右邊：功能 + Minimap
    right_frame = tk.Frame(container, bg='lightgray', width=int(screen_width * 0.3))
    right_frame.pack(side='left', fill='both')

    # 上：功能區（高度 30%）
    function_frame = tk.Frame(right_frame, bg='white', height=int(screen_height * 0.3))
    function_frame.pack(fill='x')
    function_frame.pack_propagate(False)  # 禁止內容撐開

    tk.Label(function_frame, text="🔍 關鍵字查詢").pack(pady=10)
    entry = tk.Entry(function_frame, font=('Arial', 16))
    entry.pack(pady=10)
    btn = tk.Button(function_frame, text="搜尋", font=('Arial', 14))
    btn.pack(pady=10)

    # 下：Minimap 區域（其餘高度）
    minimap_frame = tk.Frame(right_frame, bg='gray')
    minimap_frame.pack(fill='both', expand=True)
    minimap_label = tk.Label(minimap_frame, text="MiniMap 區域", bg='gray')
    minimap_label.pack(expand=True)

    root.mainloop()

create_app()
