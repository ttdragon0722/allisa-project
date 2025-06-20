import cv2
import numpy as np
from typing import Tuple,List
from fitz import Pixmap
from PIL import Image, ImageTk,ImageDraw
from .debug import Debug


from .data.models import FoundResult,BoxInfo,ZoomScreen, BoundingBox

class DisplayEngine:
    def __init__(self):
        self.front = None
        self.back = None
        
    def set_result(self,
        pixmaps:Tuple[Pixmap, Pixmap],
        result:FoundResult,
        zoom: float,
        scale: float=1,
        thickness: int = 2
    ):
        front_pix, back_pix = pixmaps
        group_box = result.get_by_side()
        
        # set cv2 image processor
        self.front = CV2ImageProcessor(front_pix,group_box["front"],zoom,scale)
        self.back = CV2ImageProcessor(back_pix,group_box["back"],zoom,scale)
        
        self.front.draw_boxes(scale,thickness=thickness)
        self.back.draw_boxes(scale,thickness=thickness)
        
    def draw_bounding_box(self,bounding_boxes:Tuple[BoundingBox, BoundingBox],):
        front_bounding_box, back_bounding_box = bounding_boxes
        self.front.draw_bounding_box(front_bounding_box)
        self.back.draw_bounding_box(back_bounding_box)
    
        
    def valid_side(self,side):
        if side == "front":
            page = self.front
        elif side == "back":
            page = self.back
        else:
            raise ValueError(f"無效的 side 參數: {side}")
        return page
        
    def get_zoom(self,zoom_screen:ZoomScreen,output_size=(640, 480)) -> ImageTk.PhotoImage: 
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

        # OpenCV 用 BGR，Pillow 用 RGB，所以要轉換順序
        crop_rgb = cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)

        # 縮放成固定輸出大小
        image = Image.fromarray(crop_rgb).resize(output_size, Image.LANCZOS)

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

    def __init__(self, pix: Pixmap, src: List[BoxInfo], zoom, scale: float = 1):
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

    def draw_boxes(
        self,
        scale: float = 1.0,
        color: Tuple[int, int, int] = (0, 0, 255),
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
