from dataclasses import dataclass,field
from typing import List,Dict,Union
from ..debug import Debug

from datetime import datetime
@dataclass
class File:
    path: str
    name: str
    mod_time: float  # timestamp
    ext: str         # 副檔名（不含點）

    def __repr__(self):
        return f"<File name='{self.name}' ext='{self.ext}' modified='{self.mod_time_str}' full_path='{self.path}'>"

    @property
    def mod_time_str(self) -> str:
        return datetime.fromtimestamp(self.mod_time).strftime('%Y-%m-%d %H:%M:%S')



@dataclass
class BoundingBox:
    x0: int
    y0: int
    x1: int
    y1: int
    
    def __str__(self):
        return f"BoundingBox(x0={self.x0}, y0={self.y0}, x1={self.x1}, y1={self.y1})"

    @property
    def width(self) -> int:
        return self.x1 - self.x0

    @property
    def height(self) -> int:
        return self.y1 - self.y0

    def expand(self, margin: int | tuple[int, int, int, int]) -> "BoundingBox":
        """擴張邊界。支援單一 int 或 (left, top, right, bottom) tuple"""
        if isinstance(margin, int):
            l = t = r = b = margin
        else:
            l, t, r, b = margin
        return BoundingBox(
            x0=self.x0 - l,
            y0=self.y0 - t,
            x1=self.x1 + r,
            y1=self.y1 + b,
        )
    
    def expand_by_ratio(self, ratio: float | tuple[float, float]) -> "BoundingBox":
        """
        根據 width / height 的比例擴張邊界。
        ratio 可以是 float（兩邊各擴），或 tuple(w_ratio, h_ratio)
        例如 ratio=0.1 表示左右各加寬 10% 寬度，上下各加高 10% 高度
        """
        if isinstance(ratio, float) or isinstance(ratio, int):
            w_ratio = h_ratio = ratio
        else:
            w_ratio, h_ratio = ratio

        w_margin = int(self.width * w_ratio)
        h_margin = int(self.height * h_ratio)

        return BoundingBox(
            x0=self.x0 - w_margin,
            y0=self.y0 - h_margin,
            x1=self.x1 + w_margin,
            y1=self.y1 + h_margin,
        )

    def as_tuple(self) -> tuple[int, int, int, int]:
        return (self.x0, self.y0, self.x1, self.y1)

@dataclass
class BoxInfo:
    x0: int
    y0: int
    x1: int
    y1: int
    text: str
    block_no: int
    side: str  # 'front' or 'back'
    matched_keywords: List[str] = field(default_factory=list)

    def __str__(self):
        keywords = ', '.join(self.matched_keywords)
        return (
            f"[{self.side}] block {self.block_no}: "
            f"({self.x0},{self.y0})-({self.x1},{self.y1}) "
            f"text: {self.text.strip()} "
            f"{'(matched: ' + keywords + ')' if keywords else ''}"
        )
    
    @property
    def center(self):
        return ((self.x0+ self.x1)/2,(self.y0+self.y1)/2)

@dataclass
class FoundResult:
    total: int
    front_amount:int
    back_amount:int
    box: list[BoxInfo]
    
    def __str__(self):
        lines = [f"Found {self.total} results:"]
        lines += [str(b) for b in self.box]
        return "\n".join(lines)

    @Debug.event("分類資料", "green")
    def get_by_side(self) -> Dict[str, List[BoxInfo]]:
        """
        根據 BoxInfo.side 將 box 分類並回傳字典。
        
        Returns:
            Dict[str, List[BoxInfo]]: 例如 {"front": [...], "back": [...]}
        """
        result: Dict[str, List[BoxInfo]] = {}
        for b in self.box:
            result.setdefault(b.side, []).append(b)

        # 確保兩個 key 一定存在
        result.setdefault("front", [])
        result.setdefault("back", [])

        print(result)
        return result
    
    
@dataclass
class ZoomArea:
    side: str
    x0: int
    y0: int
    x1: int
    y1: int
    
@dataclass
class ZoomScreen:
    
    side: str
    x0: int
    y0: int
    x1: int
    y1: int
    zoom: int
    labels: List = field(default_factory=list)
    
    @property
    def display(self) -> ZoomArea:
        return ZoomArea(
            side=self.side,
            x0=int(self.x0 * self.zoom),
            y0=int(self.y0 * self.zoom),
            x1=int(self.x1 * self.zoom),
            y1=int(self.y1 * self.zoom),
        )
    
    def __str__(self):
        info = f"[{self.side}] Zoom: ({self.x0},{self.y0}) - ({self.x1},{self.y1})"
        if self.labels:
            label_infos = []
            for i, label in enumerate(self.labels, 1):
                try:
                    text = label.text.strip()
                    keywords = ', '.join(label.matched_keywords) if hasattr(label, 'matched_keywords') else ''
                    label_infos.append(f"  {i}. {text}" + (f" (matched: {keywords})" if keywords else ''))
                except Exception as e:
                    label_infos.append(f"  {i}. <error: {e}>")
            labels_str = "\n" + "\n".join(label_infos)
        else:
            labels_str = "\n  (no labels)"
        return info + labels_str
    