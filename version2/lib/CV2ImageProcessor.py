import cv2
import numpy as np
from typing import Tuple,List
from fitz import Pixmap
from PIL import Image, ImageTk,ImageDraw,ImageFont
import math

from .SinglePDF import SinglePDF
from .debug import Debug
from .data.models import FoundResult,BoxInfo,ZoomScreen, BoundingBox

class DisplayEngine:
    def __init__(self):
        self.front: CV2ImageProcessor = None
        self.back: CV2ImageProcessor = None
        
    def set_valid(self,
        pdf_data: Tuple[SinglePDF, SinglePDF],
        zoom: float = 0.8,
        scale:float = 1
    ):
        front, back = pdf_data
        front_pixmap = front.get_pixmap(zoom)
        back_pixmap = back.get_pixmap(zoom)
        
        self.front = CV2ImageProcessor(
            front_pixmap,[],zoom,scale
        )
        self.back = CV2ImageProcessor(
            back_pixmap,[],zoom,scale
        )
        
        # 畫文字除錯框
        self.front.draw_block_highlight(
            front.get_blocks()
        )
        self.back.draw_block_highlight(
            back.get_blocks()
        )
        
        # 畫邊界
        self.front.draw_bounding_box(
            front.bounding_box
        )
        self.back.draw_bounding_box(
            back.bounding_box
        )
        
    def set_result(self,
        pixmaps:Tuple[Pixmap, Pixmap],
        result:FoundResult,
        zoom: float,
        scale: float=1,
        thickness: int = 2,
        color: Tuple[int, int, int] = (255, 0, 0),
    ):
        front_pix, back_pix = pixmaps
        group_box = result.get_by_side()
        
        # set cv2 image processor
        self.front = CV2ImageProcessor(front_pix,group_box["front"],zoom,scale)
        self.back = CV2ImageProcessor(back_pix,group_box["back"],zoom,scale)
        
        self.front.draw_boxes(scale,thickness=thickness,color=color)
        self.back.draw_boxes(scale,thickness=thickness,color=color)
    
    @Debug.event("mini map debug","magenta")
    def draw_bounding_box(self,bounding_boxes:Tuple[BoundingBox, BoundingBox],):
        front_bounding_box, back_bounding_box = bounding_boxes
        fi = self.front.draw_bounding_box(front_bounding_box)
        bi = self.back.draw_bounding_box(back_bounding_box)
        
        print(fi.mode)
        
        x, y = int(front_bounding_box.x0 * self.front.factor), int(front_bounding_box.y0 * self.front.factor)
        self.draw_label_box_with_side(fi, side="front", position=(x, y))
        self.front.update_image_with_pil_image(fi)
        
        x, y = int(back_bounding_box.x0 * self.back.factor), int(back_bounding_box.y0 * self.back.factor)
        self.draw_label_box_with_side(bi, side="back", position=(x, y))
        self.back.update_image_with_pil_image(bi)
    
        
    def valid_side(self,side):
        if side == "front":
            page = self.front
        elif side == "back":
            page = self.back
        else:
            raise ValueError(f"無效的 side 參數: {side}")
        return page
        
    
    def draw_label_box_with_side(
        self,
        image: Image.Image,
        side: str,
        size: Tuple[int, int] = (60, 30),
        position: Tuple[int, int] = (0, 0),
        box_color: Tuple[int, int, int] = (255, 192, 0),
        text_color: Tuple[int, int, int] = (0, 0, 0),
    ) -> Image.Image:
        """
        在指定位置畫出「TOP」或「BOT」標籤。
        
        :param image: PIL.Image 圖片物件
        :param side: "front" → TOP，其它 → BOT
        :param size: 標籤區塊的大小 (width, height)
        :param position: 要畫在的位置 (x, y)，預設左上角
        :param box_color: 背景顏色
        :param text_color: 字體顏色
        :return: 修改後的 image
        """
        
        label = "TOP" if side.lower() == "front" else "BOT"

        draw = ImageDraw.Draw(image)
        box_width, box_height = size
        x, y = position

        # 畫底色矩形
        draw.rectangle([x, y, x + box_width, y + box_height], fill=box_color)

        # 字型
        try:
            font = ImageFont.truetype("arial.ttf", 18)
        except:
            font = ImageFont.load_default()

        # 計算文字置中位置
        bbox = draw.textbbox((0, 0), label, font=font)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]
        text_x = x + (box_width - text_w) // 2
        text_y = y + (box_height - text_h) // 2

        draw.text((text_x, text_y), label, fill=text_color, font=font)

        return image
    
    def force_label_spread(self, labels_info, component_boxes, output_size, padding=4, spacing=2, max_radius=100):
        placed = []

        def rect(x, y, w, h):
            return (x - w / 2 - padding, y - h / 2 - padding, x + w / 2 + padding, y + h / 2 + padding)

        def is_conflict(r, others):
            for other in others:
                if not (r[2] <= other[0] or r[0] >= other[2] or r[3] <= other[1] or r[1] >= other[3]):
                    return True
            return False

        for label in labels_info:
            cx, cy = label['orig_x'], label['orig_y']
            w, h = label['w'], label['h']

            # 嘗試用發射角度進行避讓
            placed_rect = None
            for r in range(0, max_radius, spacing):
                for angle_deg in range(0, 360, 30):  # 每 30 度試一次
                    angle_rad = math.radians(angle_deg)
                    x = cx + r * math.cos(angle_rad)
                    y = cy + r * math.sin(angle_rad)

                    # 不超出畫布
                    if not (0 < x < output_size[0] and 0 < y < output_size[1]):
                        continue

                    box = rect(x, y, w, h)
                    if not is_conflict(box, component_boxes + placed):
                        label['x'], label['y'] = x, y
                        placed.append(box)
                        placed_rect = box
                        break
                if placed_rect:
                    break

            # 如果找不到合適點，保留原地
            if not placed_rect:
                label['x'], label['y'] = cx, cy
                placed.append(rect(cx, cy, w, h))

        return labels_info

    
    def draw_labels_on_image(self, image: Image.Image, zoom_screen: ZoomScreen):
        draw = ImageDraw.Draw(image)
        try:
            font = ImageFont.truetype("arial.ttf", 14)
        except:
            font = ImageFont.load_default()

        # 1️⃣ 準備元件框 & 初始標籤資料
        component_boxes = [(label.x0, label.y0, label.x1, label.y1) for label in zoom_screen.labels]
        padding = 4

        # 2️⃣ 建立標籤清單，包含估算文字尺寸與初始位置
        labels_info = []
        for label in zoom_screen.labels:
            x0, y0, x1, y1 = label.x0, label.y0, label.x1, label.y1
            text = label.text.replace('\n', ' ')

            # 估算文字框尺寸
            bbox = draw.textbbox((0, 0), text, font=font)
            text_w = bbox[2] - bbox[0]
            text_h = bbox[3] - bbox[1]

            # 以元件上方為初始放置點，若不足改為下方
            center_x = (x0 + x1) / 2
            prefer_y = y0 - text_h - padding * 2
            if prefer_y < 0:
                prefer_y = y1 + padding

            labels_info.append({
                'x': center_x,
                'y': prefer_y,
                'w': text_w,
                'h': text_h,
                'text': text,
                'orig_x': center_x,
                'orig_y': prefer_y
            })

        # 3️⃣ 使用力導向演算法調整標籤座標
        adjusted_labels = self.force_label_spread(labels_info, component_boxes, image.size)

        # 4️⃣ 繪製元件框與標籤
        for i, label in enumerate(zoom_screen.labels):
            # 畫元件框
            draw.rectangle([label.x0, label.y0, label.x1, label.y1], outline=(255, 192, 0), width=2)

            # 取得標籤資訊
            adj = adjusted_labels[i]
            text = adj['text']
            text_w = adj['text_w']
            text_h = adj['text_h']
            margin_x = adj['margin_x']
            margin_y = adj['margin_y']

            # ➕ 計算文字繪製位置
            bg_x0 = adj['x'] - text_w / 2
            bg_y0 = adj['y'] - text_h / 2
            text_x = bg_x0
            text_y = bg_y0

            # ✏️ 繪製文字（無背景）
            draw.text((text_x, text_y), text, fill=(255, 255, 255), font=font)

            # ➕ 計算元件中心點
            comp_cx = (label.x0 + label.x1) / 2
            comp_cy = (label.y0 + label.y1) / 2

            # ➕ 計算文字中心點（含 margin 中心）
            label_cx = adj['x']
            label_cy = adj['y']

            # ➖ 畫一條線連接 label 與元件中心
            draw.line([(label_cx, label_cy), (comp_cx, comp_cy)], fill=(255, 192, 0), width=1)

        return image

    def draw_labels_on_image_v2(self, image: Image.Image, zoom_screen: ZoomScreen):
        draw = ImageDraw.Draw(image)
        try:
            font = ImageFont.truetype("arial.ttf", 14)
        except:
            font = ImageFont.load_default()

        spacing = 15  # 控制標籤間距（layout計算）
        component_boxes = [(label.x0, label.y0, label.x1, label.y1) for label in zoom_screen.labels]

        labels_info = []
        margin_x = 6  # 相當於 mx-3
        margin_y = 4  # 相當於 my-2

        for label in zoom_screen.labels:
            text = label.text.replace('\n', ' ')
            bbox = draw.textbbox((0, 0), text, font=font)
            text_w = bbox[2] - bbox[0]
            text_h = bbox[3] - bbox[1]

            total_w = text_w + margin_x * 2
            total_h = text_h + margin_y * 2

            labels_info.append({
                'label': label,
                'text': text,
                'w': total_w,         # layout用：含margin
                'h': total_h,
                'text_w': text_w,     # 真正文字寬高（畫字用）
                'text_h': text_h,
                'margin_x': margin_x,
                'margin_y': margin_y,
                'orig_x': (label.x0 + label.x1) / 2,
                'orig_y': label.y0
            })

        adjusted_labels = self.smart_label_layout(labels_info, component_boxes, image.size, spacing)

        for info in adjusted_labels:
            label = info['label']
            x0, y0, x1, y1 = label.x0, label.y0, label.x1, label.y1
            draw.rectangle([x0, y0, x1, y1], outline=(255, 192, 0), width=2)

            # 這裡畫背景用 margin 決定大小
            bg_x0 = info['x'] - info['w'] / 2
            bg_y0 = info['y'] - info['h'] / 2
            bg_x1 = info['x'] + info['w'] / 2
            bg_y1 = info['y'] + info['h'] / 2
            draw.rectangle([bg_x0, bg_y0, bg_x1, bg_y1], fill=(255, 192, 0))

            # 內部文字靠 margin 定位
            text_x = bg_x0 + info['margin_x']
            text_y = bg_y0 + info['margin_y']
            draw.text((text_x, text_y), info['text'], fill=(255, 255, 255), font=font)

        return image

    def smart_label_layout(self, labels_info, component_boxes, canvas_size, spacing=2):
        placed = []

        def rect(x, y, w, h):
            return (x - w / 2, y - h / 2, x + w / 2, y + h / 2)

        def is_conflict(r, others):
            for other in others:
                if not (r[2] <= other[0] or r[0] >= other[2] or r[3] <= other[1] or r[1] >= other[3]):
                    return True
            return False

        for label in labels_info:
            cx, cy = label['orig_x'], label['orig_y']
            w, h = label['w'], label['h']
            best_score = float('inf')
            best_pos = None

            for r in range(0, 100, spacing):
                for deg in range(0, 360, 15):
                    angle = math.radians(deg)
                    x = cx + r * math.cos(angle)
                    y = cy + r * math.sin(angle)

                    if not (0 <= x <= canvas_size[0] and 0 <= y <= canvas_size[1]):
                        continue

                    candidate_box = rect(x, y, w, h)
                    if is_conflict(candidate_box, component_boxes + placed):
                        continue

                    dist_score = r
                    align_score = abs(x - cx) + abs(y - cy)
                    total_score = dist_score + 0.5 * align_score

                    if total_score < best_score:
                        best_score = total_score
                        best_pos = (x, y, candidate_box)

                if best_pos:
                    break

            if best_pos:
                x, y, box = best_pos
            else:
                x, y = cx, cy
                box = rect(cx, cy, w, h)

            label['x'] = x
            label['y'] = y
            placed.append(box)

        return labels_info

    
    def get_zoom(self, zoom_screen: ZoomScreen, output_size=(640, 480)) -> ImageTk.PhotoImage:
        page = self.valid_side(zoom_screen.side)  # 取得已繪製好元件的 np.ndarray 圖片
        display = zoom_screen.display
        img = page.image

        x0, y0, x1, y1 = display.x0, display.y0, display.x1, display.y1

        # 邊界保護，避免裁切出界
        h, w, _ = img.shape
        x0 = max(0, min(x0, w - 1))
        x1 = max(0, min(x1, w))
        y0 = max(0, min(y0, h - 1))
        y1 = max(0, min(y1, h))


        # 裁切出該區域
        crop = img[y0:y1, x0:x1]

        # OpenCV BGR → Pillow RGB
        crop_rgb = cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)

        # 縮放成固定輸出大小
        image = Image.fromarray(crop_rgb).resize(output_size, Image.LANCZOS)


        # 左上畫東西
        self.draw_label_box_with_side(image,zoom_screen.side)

        normalized_screen = zoom_screen.normalized(output_size)
        print("normalized_screen",normalized_screen)
        # 標出元件
        self.draw_labels_on_image_v2(image,normalized_screen)

        return ImageTk.PhotoImage(image)
    
    @Debug.event("draw relative position","magenta")
    def draw_relative_position(self, page ,screen: ZoomScreen):
        img = page.image.copy()
        factor = page.zoom * page.scale
        x0 = int(screen.x0*factor)
        y0 = int(screen.y0*factor)
        x1 = int(screen.x1*factor)
        y1 = int(screen.y1*factor)
        print(screen)

        # 畫紅框
        cv2.rectangle(img, (x0, y0), (x1, y1), (0, 0, 255), 2)

        return img
        

    def get_image(self, side: str, draw_func=None,screen=None) -> ImageTk.PhotoImage:
        """
        取得 Tkinter 用影像，支援傳入 draw_func(img) 回傳畫好後的 img
        """
        page = self.valid_side(side)
        img = page.image
        img = img.copy()  # 保護原圖

        if draw_func:
            img = draw_func(page,screen)

        # OpenCV → PIL → Tk
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        img_pil = Image.fromarray(img_rgb)
        return ImageTk.PhotoImage(img_pil)
    
class CV2ImageProcessor:
    """
    OpenCV 圖像處理工具類
    支援：自動通道處理 + BoundingBox遮罩 + 框線繪製
    """

    def __init__(self, 
        pix: Pixmap, 
        src: List[BoxInfo], 
        zoom, 
        scale: float = 1
    ):
        self.height = pix.height
        self.width = pix.width
        self.channels = pix.n
        self.samples = pix.samples

        self.zoom = zoom
        self.scale = scale
        self.source = src

        # 轉為 numpy 陣列
        self.image = np.frombuffer(self.samples, dtype=np.uint8).reshape(
            (self.height, self.width, self.channels)
        )

        # 若通道不是 4，轉成 RGBA 以便後續處理透明遮罩
        if self.channels == 3:
            self.image = cv2.cvtColor(self.image, cv2.COLOR_RGB2RGBA)
        elif self.channels == 1:
            self.image = cv2.cvtColor(self.image, cv2.COLOR_GRAY2RGBA)

    @property
    def factor(self):
        return self.zoom * self.scale

    def draw_block_highlight(self, blocks: list):
        """將 fitz.get_text("blocks") 的結果畫出半透明黃色區塊"""
        overlay = Image.new("RGBA", (self.width, self.height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        factor = self.factor

        for block in blocks:
            x0, y0, x1, y1 = block[:4]
            draw.rectangle(
                [
                    int(x0 * factor),
                    int(y0 * factor),
                    int(x1 * factor),
                    int(y1 * factor)
                ],
                fill=(255, 255, 0, 128)  # 正常黃色
            )

        # 修正這裡：先轉 RGB，再轉 RGBA，避免通道混亂
        base_image = Image.fromarray(self.image).convert("RGB").convert("RGBA")
        result = Image.alpha_composite(base_image, overlay)

        self.image = np.array(result).astype("uint8")  # 回存為 numpy 格式

    def draw_bounding_box(self, bounding_box: BoundingBox):
        """將 bounding box 外部區域覆蓋半透明黑色遮罩"""
        overlay = Image.new("RGBA", (self.width, self.height), (0, 0, 0, 128))

        factor = self.factor
        mask_draw = ImageDraw.Draw(overlay)
        mask_draw.rectangle(
            [
                int(bounding_box.x0 * factor),
                int(bounding_box.y0 * factor),
                int(bounding_box.x1 * factor),
                int(bounding_box.y1 * factor),
            ],
            fill=(0, 0, 0, 0)  # 挖洞
        )

        base_image = Image.fromarray(self.image).convert("RGBA")
        result = Image.alpha_composite(base_image, overlay)
        self.image = np.array(result)
        return result 
    
    def update_image_with_pil_image(self,pil_image: Image.Image):
        rgb_image = pil_image.convert("RGB")
        np_img = np.array(rgb_image)
        # 轉 BGR 給 OpenCV 顯示用（若你是用OpenCV）
        bgr_img = cv2.cvtColor(np_img, cv2.COLOR_RGB2BGR)
        self.image = bgr_img

    def draw_boxes(
        self,
        scale: float = 1.0,
        color: Tuple[int, int, int] = (255, 0, 0),
        thickness: int = 2
    ) -> np.ndarray:
        """
        繪製來源框框（來源為 BoxInfo）至圖片上
        """
        img = self.image.copy()

        # RGBA 轉 BGR（for cv2.rectangle）
        if img.shape[2] == 4:
            img = cv2.cvtColor(img, cv2.COLOR_RGBA2BGR)

        factor = self.zoom * scale
        for box in self.source:
            cv2.rectangle(
                img,
                (int(box.x0 * factor), int(box.y0 * factor)),
                (int(box.x1 * factor), int(box.y1 * factor)),
                color,
                thickness
            )

        self.image = img  # 更新當前影像
        return img
