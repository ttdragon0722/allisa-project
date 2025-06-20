import fitz  # PyMuPDF

from tkinter import messagebox
from os import path
from os.path import isfile
import re

from .utils import function_runtime, handle_file_open_error
from .data import BoxInfo, FoundResult
from .SinglePDF import SinglePDF

from .debug import Debug

class PDFViewer:
    def __init__(self,front_path:str, back_path:str):
        self.front = SinglePDF(front_path,"front")
        self.back = SinglePDF(back_path,"back")
        
        # 預設解析度  方大區域& 小地圖
        self.zoom = 5
        self.zoom_mini = 0.7
        
    

    @staticmethod
    def is_valid_pdf(path: str) -> tuple[bool, str]:
        """驗證pdf是否可被開啟"""
        if not path:
            return False, "路徑為空"
        if not isfile(path):
            messagebox.showerror("錯誤", "檔案不存在。")
            return False, "檔案不存在"
        try:
            with fitz.open(path) as doc:
                if doc.page_count == 0:
                    messagebox.showerror("錯誤", "PDF 無頁面")
                    return False, "PDF 無頁面"
        except Exception as e:
            messagebox.showerror("錯誤", f"無法讀取 PDF：{e}")
            return False, f"無法讀取 PDF：{e}"
        return True, "OK"
    
    # 解析度設定
    @property
    def mat(self):
        return fitz.Matrix(self.zoom, self.zoom)

    @property
    def mat_mini(self):
        return fitz.Matrix(self.zoom_mini, self.zoom_mini)
    
    def is_valid_doc(self) -> bool:
        """檢查文檔是否合法"""
        if self.front_doc is None or self.back_doc is None:
            return False
        return True

    # 讀取路徑
    @property
    def paths(self):
        """輸出路徑""" 
        return [self.front.path, self.back.path]
    
    def _search_blocks(self, keywords: list[str], page_idx=0) -> tuple[list[BoxInfo], int, int]:
        """搜尋指定頁面中包含任一關鍵字的區塊（精確比對 & 只保留命中段）"""

        if not keywords:
            return [], 0, 0

        # 🔸 不再處理括號，保留原始關鍵字大小寫
        processed_keywords = [k.strip() for k in keywords if k.strip()]
        if not processed_keywords:
            return [], 0, 0

        # 建立完整單字匹配的 regex（不分大小寫）
        pattern = re.compile(r"\b(" + "|".join(re.escape(k) for k in processed_keywords) + r")\b")

        front_blocks = self.front.get_blocks(page_idx)
        back_blocks = self.back.get_blocks(page_idx)
        
        self.front.get_trimmed_bounding_box_v6()
        self.back.get_trimmed_bounding_box_v6()
        
        print(self.front.bounding_box)
        print(self.back.bounding_box)

        results = []
        seen = set()
        front_amount = 0
        back_amount = 0

        for side, blocks in [("front", front_blocks), ("back", back_blocks)]:
            for b in blocks:
                if len(b) < 6:
                    continue
                x0, y0, x1, y1, text, block_no = b[:6]
                if not isinstance(text, str):
                    continue

                # 找出所有命中關鍵字（保留原大小寫）
                matched = pattern.findall(text)
                if matched:
                    key = (side, block_no)
                    if key not in seen:
                        seen.add(key)

                        # ✅ 只保留命中的文字內容（逐行過濾）
                        lines = text.splitlines()
                        matched_lines = [line.strip() for line in lines if pattern.search(line)]

                        if matched_lines:
                            results.append(BoxInfo(
                                x0=round(x0),
                                y0=round(y0),
                                x1=round(x1),
                                y1=round(y1),
                                text="\n".join(matched_lines),
                                block_no=block_no,
                                side=side,
                                matched_keywords=list(set(matched))  # 若多行命中，也會有多個
                            ))

                            if side == "front":
                                front_amount += 1
                            else:
                                back_amount += 1

        return results, front_amount, back_amount

    @Debug.function_runtime
    def search_pdf_single(self, keyword: str, page_idx=0) -> FoundResult:
        if not keyword or not keyword.strip():
            return FoundResult(total=0, box=[])
        results,front_amount, back_amount = self._search_blocks([keyword], page_idx)
        return FoundResult(total=len(results),front_amount=front_amount,back_amount=back_amount, box=results)

    @Debug.function_runtime
    def search_pdf_multiple(self, keywords: list[str], page_idx=0) -> FoundResult:
        if not keywords:
            return FoundResult(total=0, box=[])
        results,front_amount, back_amount = self._search_blocks(keywords, page_idx)
        return FoundResult(total=len(results),front_amount=front_amount,back_amount=back_amount, box=results)




if __name__ == "__main__":
    # debug
    # 假設你手邊有測試用的 PDF 檔案
    path1 = "C:/Users/Rex/Downloads/alisa project/source/PR810_MB_RA-PDF-201123B.pdf"
    path2 = "C:/Users/Rex/Downloads/alisa project/source/PR810_MB_RA-PDF-201123T.pdf"

    viewer = PDFViewer(path1, path2)
    print(viewer.search_pdf_single("C924"))
    print(viewer.search_pdf_multiple(["LC8","SC13"]))