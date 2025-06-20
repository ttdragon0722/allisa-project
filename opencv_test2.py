import fitz  # PyMuPDF
import cv2
import numpy as np

def search_and_zoom_with_minimap(pdf_path, keyword, page_num=0, output_img='zoomed.png', minimap_img='minimap.png'):
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
        return

    zoom = 8
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat)
    img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n).copy()
    if pix.n == 4:
        img = cv2.cvtColor(img, cv2.COLOR_RGBA2BGR)
    elif pix.n == 1:
        img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)

    # 輸出局部放大圖尺寸
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

    # 在局部放大圖上標紅框（元件區域）
    # 元件區域相對局部區塊座標
    box_x0 = int((x0 * zoom) - left)
    box_y0 = int((y0 * zoom) - top)
    box_x1 = int((x1 * zoom) - left)
    box_y1 = int((y1 * zoom) - top)
    # 先畫紅框（元件位置）
    cv2.rectangle(zoomed, (box_x0, box_y0), (box_x1, box_y1), (0, 0, 255), 2)

    # 標籤文字
    label = keyword.upper()

    # 黃框大小 & 位置（靠紅框右邊，並稍微往上）
    box_w, box_h = 80, 30
    label_pos = (box_x1 + 10, box_y0 - 10)

    # 確保黃框不會超出圖片範圍，往左上修正
    if label_pos[0] + box_w > zoomed.shape[1]:
        label_pos = (box_x0 - box_w - 10, label_pos[1])
    if label_pos[1] < 0:
        label_pos = (label_pos[0], 10)

    # 畫黃底方塊
    cv2.rectangle(zoomed, label_pos, (label_pos[0] + box_w, label_pos[1] + box_h), (0, 255, 255), -1)
    # 加文字（黑字）
    cv2.putText(zoomed, label, (label_pos[0] + 5, label_pos[1] + 22), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)

    # 畫箭頭連結標籤與紅框中點
    arrow_start = (label_pos[0], label_pos[1] + box_h // 2)
    arrow_end = (box_x1, box_y0 + (box_y1 - box_y0) // 2)
    cv2.arrowedLine(zoomed, arrow_start, arrow_end, (0, 255, 255), 2, tipLength=0.2)

    cv2.imshow(f'Zoomed view: {keyword}', zoomed)
    cv2.imwrite(output_img, zoomed)

    # 生成縮小版小地圖
    minimap_scale = 0.1  # 縮小比例
    minimap = cv2.resize(img, (int(img.shape[1]*minimap_scale), int(img.shape[0]*minimap_scale)), interpolation=cv2.INTER_AREA)

    # 在小地圖上標示放大區域位置（紅框）
    mm_box_x0 = int(left * minimap_scale)
    mm_box_y0 = int(top * minimap_scale)
    mm_box_x1 = int(right * minimap_scale)
    mm_box_y1 = int(bottom * minimap_scale)
    cv2.rectangle(minimap, (mm_box_x0, mm_box_y0), (mm_box_x1, mm_box_y1), (0, 0, 255), 1)

    cv2.imshow('Minimap', minimap)
    cv2.imwrite(minimap_img, minimap)

    cv2.waitKey(0)
    cv2.destroyAllWindows()

if __name__ == '__main__':
    pdf_path = 'sample.pdf'
    keyword = input("請輸入要搜尋的文字：")
    search_and_zoom_with_minimap(pdf_path, keyword, page_num=0)
