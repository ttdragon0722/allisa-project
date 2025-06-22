import fitz
from os.path import isfile
from tkinter import messagebox
import numpy as np
import cv2
from .data import BoundingBox,Union
from .utils import handle_file_open_error
from .debug import Debug

class SinglePDF:
    def __init__(self, path: str = None, side: str = None):
        self._path: str = None
        self.doc = None
        self.side = side  # 新增 side 屬性
        if path:
            self.path: str = path

    def get_sobel_bounding_box(self,idx:int = 0 ,debug: bool = False) -> BoundingBox:
        """根據 pixmap 圖像，使用 Sobel 邊緣檢測找出最大內容區域的邊界"""
        page = self.get_page(idx)
        pixmap = page.get_pixmap()
        img = np.frombuffer(pixmap.samples, dtype=np.uint8).reshape((pixmap.height, pixmap.width, pixmap.n))
        if img.shape[2] == 4:
            img = img[:, :, :3]
        height, width = img.shape[:2]

        # 轉灰階並做 Sobel 邊緣偵測
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        sobelx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
        sobely = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
        sobel = cv2.magnitude(sobelx, sobely)
        sobel = np.uint8(np.clip(sobel, 0, 255))

        # 二值化 + 膨脹以連結斷裂邊界
        _, edge_bin = cv2.threshold(sobel, 30, 255, cv2.THRESH_BINARY)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 15))
        dilated_edge = cv2.dilate(edge_bin, kernel, iterations=1)

        # 找最大連通區域
        num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(dilated_edge)
        if num_labels <= 1:
            return BoundingBox(0, 0, width, height)

        stats = stats[1:]  # 去掉背景
        max_stat = max(stats, key=lambda s: s[cv2.CC_STAT_AREA])
        x, y, w, h = max_stat[:4]
        
        bbox = BoundingBox(x, y, x + w, y + h)
        
        if debug:
            import matplotlib.pyplot as plt
            vis = img.copy()
            cv2.rectangle(vis, (bbox.x0, bbox.y0), (bbox.x1, bbox.y1), (0, 0, 255), 3)

            plt.figure(figsize=(16, 6))
            plt.subplot(1, 3, 1)
            plt.imshow(cv2.cvtColor(vis, cv2.COLOR_BGR2RGB))
            plt.title("原圖 + BoundingBox")
            plt.axis("off")

            plt.subplot(1, 3, 2)
            plt.imshow(sobel, cmap='gray')
            plt.title("Sobel 邊緣")
            plt.axis("off")

            plt.subplot(1, 3, 3)
            plt.imshow(dilated_edge, cmap='gray')
            plt.title("膨脹後邊緣區")
            plt.axis("off")

            plt.tight_layout()
            plt.show()
        
        return bbox

    @Debug.event("get density", "blue")
    def get_density_bounding_box_from_sobel(
        self,
        sobel_bbox: BoundingBox,
        idx: int = 0,
        debug: bool = False,
        small_win: int = 50,
        small_stride: int = 25,
        large_win: int = 200,
        large_stride: int = 100,
        top_k: int = 10,
        padding: int = 5
    ) -> BoundingBox:
        """使用滑動視窗密度分析，於 sobel 框內尋找文字最密集的區域"""
        page = self.get_page(idx)
        words = self.get_words(idx)

        height, width = map(int, (page.rect.height, page.rect.width))
        heatmap = np.zeros((height, width), dtype=np.uint8)

        # Step 1: 篩選在 sobel 框內的文字並繪製 heatmap（有 padding）
        for word in words:
            x0, y0, x1, y1 = map(int, word[:4])
            if (
                sobel_bbox.x0 <= x0 <= sobel_bbox.x1 and
                sobel_bbox.y0 <= y0 <= sobel_bbox.y1
            ):
                px0 = max(x0 - padding, 0)
                py0 = max(y0 - padding, 0)
                px1 = min(x1 + padding, width)
                py1 = min(y1 + padding, height)
                cv2.rectangle(heatmap, (px0, py0), (px1, py1), 255, -1)

        # Step 2: 小視窗滑動尋找高密度 seed
        small_seeds = []
        for y in range(sobel_bbox.y0 - small_win, sobel_bbox.y1 + small_stride, small_stride):
            for x in range(sobel_bbox.x0 - small_win, sobel_bbox.x1 + small_stride, small_stride):
                sx0 = max(x, 0)
                sy0 = max(y, 0)
                sx1 = min(x + small_win, width)
                sy1 = min(y + small_win, height)
                if sx1 <= sx0 or sy1 <= sy0:
                    continue  # 避免錯誤視窗
                score = np.sum(heatmap[sy0:sy1, sx0:sx1] == 255)
                if score > 0:
                    small_seeds.append((score, sx0, sy0, sx1, sy1))


        if not small_seeds:
            return sobel_bbox  # fallback：找不到任何內容就回傳原 sobel 框

        top_small = sorted(small_seeds, key=lambda s: s[0], reverse=True)[:top_k]

        # Step 3: 大視窗掃描涵蓋小 seed 的視窗
        large_windows = []
        for y in range(sobel_bbox.y0 - large_win, sobel_bbox.y1 + large_stride, large_stride):
            for x in range(sobel_bbox.x0 - large_win, sobel_bbox.x1 + large_stride, large_stride):
                lx0 = max(x, 0)
                ly0 = max(y, 0)
                lx1 = min(x + large_win, width)
                ly1 = min(y + large_win, height)
                if lx1 <= lx0 or ly1 <= ly0:
                    continue
                overlaps = [
                    1 for _, sx0, sy0, sx1, sy1 in top_small
                    if lx0 <= sx0 <= lx1 and ly0 <= sy0 <= ly1
                ]
                if overlaps:
                    large_windows.append((len(overlaps), lx0, ly0, lx1, ly1))

        # Step 4: 根據結果合併邊界
        if large_windows:
            x0 = min(w[1] for w in large_windows)
            y0 = min(w[2] for w in large_windows)
            x1 = max(w[3] for w in large_windows)
            y1 = max(w[4] for w in large_windows)
        else:
            x0 = min(w[1] for w in top_small)
            y0 = min(w[2] for w in top_small)
            x1 = max(w[3] for w in top_small)
            y1 = max(w[4] for w in top_small)

        # Step 5: 保護不超出原 sobel 框
        x0 = max(x0, sobel_bbox.x0)
        y0 = max(y0, sobel_bbox.y0)
        x1 = min(x1, sobel_bbox.x1)
        y1 = min(y1, sobel_bbox.y1)

        if debug:
            import matplotlib.pyplot as plt

            # 原圖 + 紅框：結果圖
            pix = page.get_pixmap()
            img = np.frombuffer(pix.samples, dtype=np.uint8).reshape((pix.height, pix.width, pix.n))
            img_result = img.copy()
            cv2.rectangle(img_result, (x0, y0), (x1, y1), (0, 0, 255), 3)  # 結果框
            cv2.rectangle(img_result, (sobel_bbox.x0, sobel_bbox.y0), (sobel_bbox.x1, sobel_bbox.y1), (255, 0, 0), 2)  # Sobel框

            # heatmap + 過程視覺化
            vis = cv2.cvtColor(heatmap, cv2.COLOR_GRAY2BGR)
            for _, sx0, sy0, sx1, sy1 in top_small:
                cv2.rectangle(vis, (sx0, sy0), (sx1, sy1), (0, 255, 0), 1)  # 小框
            for _, lx0, ly0, lx1, ly1 in large_windows:
                cv2.rectangle(vis, (lx0, ly0), (lx1, ly1), (255, 255, 0), 1)  # 大框
            cv2.rectangle(vis, (x0, y0), (x1, y1), (0, 0, 255), 3)  # 最終框
            cv2.rectangle(vis, (sobel_bbox.x0, sobel_bbox.y0), (sobel_bbox.x1, sobel_bbox.y1), (255, 0, 0), 2)  # Sobel框

            # 顯示兩張圖
            plt.figure(figsize=(16, 8))

            plt.subplot(1, 2, 1)
            plt.imshow(vis)
            plt.title("1. Sobel 與視窗演算過程")
            plt.axis("off")

            plt.subplot(1, 2, 2)
            plt.imshow(cv2.cvtColor(img_result, cv2.COLOR_BGR2RGB))
            plt.title("2. 最終輸出框")
            plt.axis("off")

            plt.tight_layout()
            plt.show()


        return BoundingBox(x0, y0, x1, y1)

    @Debug.event("get density v2 with debug", "blue")
    def get_density_bounding_box_from_sobel_v2(
        self,
        sobel_bbox: BoundingBox,
        idx: int = 0,
        debug: bool = False,
        small_win: int = 50,
        small_stride: int = 25,
        large_win: int = 200,
        large_stride: int = 100,
        top_k: int = 10,
        padding: int = 2,
        min_score: int = 5
    ) -> BoundingBox:
        """
        根據 Sobel 預測的邊界框，在範圍內進行密度分析，
        找出文字最密集的區域作為更精準的裁切框。

        參數說明：
        ----------
        sobel_bbox : BoundingBox
            Sobel 邊緣偵測結果，用來限定密度分析的初步範圍。
        
        idx : int, 預設 0
            要處理的頁面索引，用來取得對應 PDF 頁面與文字。

        debug : bool, 預設 False
            是否啟用除錯模式。啟用後會顯示滑動視窗與邊界可視化圖。

        small_win : int, 預設 50
            小視窗的邊長，用來偵測局部高密度的文字種子點。  
            - 數值越小可捕捉較細緻的密度區塊，但容易產生雜訊。

        small_stride : int, 預設 25
            小視窗的滑動步距，控制小視窗掃描的精細程度。  
            - 步距越小，精準度提升但處理速度會變慢。

        large_win : int, 預設 200
            大視窗的邊長，用來聚合多個高密度 seed 區域，找出整體密集區。  
            - 數值越大，整合範圍越寬，但可能包含無關區域。

        large_stride : int, 預設 100
            大視窗滑動步距，影響大視窗聚合密集區的掃描範圍與速度。

        top_k : int, 預設 10
            只取前 k 個密度最高的小視窗作為有效種子點。  
            - 數值越大，可能合併更多密集區域，但風險是引入噪訊。

        padding : int, 預設 2
            在文字框外圍擴張的像素範圍，確保文字熱區完整。  
            - 避免文字框太小無法形成有效密度。

        min_score : int, 預設 5
            小視窗中至少要有多少像素值為 255（代表文字）才算是有效密度視窗。  
            - 可以過濾掉空白或雜訊區域。
        
        傳回：
        -------
        BoundingBox
            依照密度計算後的最終邊界框（限制在 sobel_bbox 內部）。
        """
        page = self.get_page(idx)
        words = self.get_words(idx)

        height, width = map(int, (page.rect.height, page.rect.width))
        heatmap = np.zeros((height, width), dtype=np.uint8)

        # Step 1: 篩選與 sobel 框有交集的文字並繪製 heatmap（有 padding）
        for word in words:
            x0, y0, x1, y1 = map(int, word[:4])
            if not (x1 < sobel_bbox.x0 or x0 > sobel_bbox.x1 or y1 < sobel_bbox.y0 or y0 > sobel_bbox.y1):
                px0 = max(x0 - padding, 0)
                py0 = max(y0 - padding, 0)
                px1 = min(x1 + padding, width)
                py1 = min(y1 + padding, height)
                cv2.rectangle(heatmap, (px0, py0), (px1, py1), 255, -1)

        # Step 1.5: morphology 過濾雜訊
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        heatmap = cv2.morphologyEx(heatmap, cv2.MORPH_OPEN, kernel)

        # Step 2: 小視窗滑動尋找高密度 seed
        small_seeds = []
        for y in range(sobel_bbox.y0 - small_win, sobel_bbox.y1 + small_stride, small_stride):
            for x in range(sobel_bbox.x0 - small_win, sobel_bbox.x1 + small_stride, small_stride):
                sx0 = max(x, 0)
                sy0 = max(y, 0)
                sx1 = min(x + small_win, width)
                sy1 = min(y + small_win, height)
                if sx1 <= sx0 or sy1 <= sy0:
                    continue
                score = np.sum(heatmap[sy0:sy1, sx0:sx1] == 255)
                if score >= min_score:
                    small_seeds.append((score, sx0, sy0, sx1, sy1))

        if not small_seeds:
            return sobel_bbox

        top_small = sorted(small_seeds, key=lambda s: s[0], reverse=True)[:top_k]

        # Step 3: 大視窗掃描涵蓋小 seed 的視窗
        large_windows = []
        for y in range(sobel_bbox.y0 - large_win, sobel_bbox.y1 + large_stride, large_stride):
            for x in range(sobel_bbox.x0 - large_win, sobel_bbox.x1 + large_stride, large_stride):
                lx0 = max(x, 0)
                ly0 = max(y, 0)
                lx1 = min(x + large_win, width)
                ly1 = min(y + large_win, height)
                if lx1 <= lx0 or ly1 <= ly0:
                    continue
                overlaps = [
                    1 for _, sx0, sy0, sx1, sy1 in top_small
                    if min(sx1, lx1) - max(sx0, lx0) > 0 and min(sy1, ly1) - max(sy0, ly0) > 0
                ]
                if overlaps:
                    large_windows.append((len(overlaps), lx0, ly0, lx1, ly1))

        # Step 4: 根據結果合併邊界
        if large_windows:
            x0 = min(w[1] for w in large_windows)
            y0 = min(w[2] for w in large_windows)
            x1 = max(w[3] for w in large_windows)
            y1 = max(w[4] for w in large_windows)
        else:
            x0 = min(w[1] for w in top_small)
            y0 = min(w[2] for w in top_small)
            x1 = max(w[3] for w in top_small)
            y1 = max(w[4] for w in top_small)

        # Step 5: 不超出 sobel 範圍
        x0 = max(x0, sobel_bbox.x0)
        y0 = max(y0, sobel_bbox.y0)
        x1 = min(x1, sobel_bbox.x1)
        y1 = min(y1, sobel_bbox.y1)


        if debug:
            import os
            import matplotlib.pyplot as plt

            # 視覺化熱度圖（Sobel框+滑窗框）
            vis = cv2.cvtColor(heatmap, cv2.COLOR_GRAY2BGR)
            for _, sx0, sy0, sx1, sy1 in top_small:
                cv2.rectangle(vis, (sx0, sy0), (sx1, sy1), (0, 255, 0), 1)
            for _, lx0, ly0, lx1, ly1 in large_windows:
                cv2.rectangle(vis, (lx0, ly0), (lx1, ly1), (255, 255, 0), 1)
            cv2.rectangle(vis, (x0, y0), (x1, y1), (0, 0, 255), 3)
            cv2.rectangle(vis, (sobel_bbox.x0, sobel_bbox.y0), (sobel_bbox.x1, sobel_bbox.y1), (255, 0, 0), 2)

            # 原圖
            pix = page.get_pixmap()
            img = np.frombuffer(pix.samples, dtype=np.uint8).reshape((pix.height, pix.width, pix.n))
            img_result = img.copy()
            if pix.n == 4:
                img_result = img_result[:, :, :3]
            img_result = cv2.cvtColor(img_result, cv2.COLOR_BGR2RGB)
            cv2.rectangle(img_result, (x0, y0), (x1, y1), (255, 0, 0), 3)

            # 準備存檔資料夾路徑
            base_dir = "v2"
            sub_dir = self.get_file_name()
            save_dir = os.path.join(base_dir, sub_dir)
            os.makedirs(save_dir, exist_ok=True)

            # 存檔路徑
            sobel_vis_path = os.path.join(save_dir, f"sobel_density_idx{idx}.png")
            output_vis_path = os.path.join(save_dir, f"density_output_idx{idx}.png")

            # 儲存圖檔 (用 matplotlib)
            plt.imsave(sobel_vis_path, cv2.cvtColor(vis, cv2.COLOR_BGR2RGB))
            plt.imsave(output_vis_path, img_result)
        return BoundingBox(x0, y0, x1, y1)



    @Debug.event("get bounding v2", "blue")
    def get_trimmed_bounding_box(self, idx: int = 0) -> Union[BoundingBox, None]:
        import matplotlib.pyplot as plt
        import cv2
        import numpy as np

        # === 1. 準備圖像與尺寸 ===
        page = self.get_page(idx)
        pix = page.get_pixmap()
        img = np.frombuffer(pix.samples, dtype=np.uint8).reshape((pix.height, pix.width, pix.n))
        if img.shape[2] == 4:  # 有 alpha
            img = img[:, :, :3]
        height, width = img.shape[:2]

        # === 2. 文字 heatmap ===
        blocks = self.get_blocks(idx)
        heatmap = np.zeros((height, width), dtype=np.uint8)
        for b in blocks:
            x0, y0, x1, y1 = map(int, b[:4])
            cv2.rectangle(heatmap, (x0, y0), (x1, y1), 255, -1)

        # === 3. Sobel 邊緣偵測 ===
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        sobelx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
        sobely = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
        sobel = cv2.magnitude(sobelx, sobely)
        sobel = np.uint8(np.clip(sobel, 0, 255))

        # === 4. 二值化 + 擴張邊緣 ===
        _, edge_bin = cv2.threshold(sobel, 30, 255, cv2.THRESH_BINARY)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 15))
        dilated_edge = cv2.dilate(edge_bin, kernel, iterations=1)

        # === 5. 合併文字 + 邊緣圖像 ===
        # 強化文字權重，使它佔主導
        weighted_heatmap = cv2.multiply(heatmap, 2)       # 文字重要度加倍
        weighted_combined = cv2.bitwise_or(weighted_heatmap, dilated_edge)
        combined = np.clip(weighted_combined, 0, 255).astype(np.uint8)

        # === 6. 找最大連通區 ===
        num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(combined)
        if num_labels <= 1:
            print("找不到任何有意義的內容")
            return BoundingBox(0, 0, width, height)

        # 排除背景，找最大區塊
        stats = stats[1:]  # 排除背景
        max_stat = max(stats, key=lambda s: s[cv2.CC_STAT_AREA])
        x, y, w, h, _ = max_stat
        self.bounding_box = BoundingBox(x, y, x + w, y + h)

        # === 7. 除錯可視化 ===
        vis_text = img.copy()
        for b in blocks:
            x0, y0, x1, y1 = map(int, b[:4])
            cv2.rectangle(combined, (x0, y0), (x1, y1), (255, 0, 0), 1)  # 藍色文字區

        cv2.rectangle(vis_text, (x, y), (x + w, y + h), (0, 0, 255), 3)  # 紅色總 bounding box
        
        vis = img.copy()
        vis_comb = cv2.cvtColor(combined, cv2.COLOR_GRAY2BGR)
        cv2.rectangle(vis_comb, (x, y), (x + w, y + h), (0, 0, 255), 3)
        cv2.rectangle(vis, (x, y), (x + w, y + h), (0, 255, 0), 3)

        plt.figure(figsize=(18, 6))
        plt.subplot(1, 3, 1)
        plt.imshow(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
        plt.title("原圖")
        plt.axis("off")

        plt.subplot(1, 3, 2)
        plt.imshow(combined, cmap="gray")
        plt.title("文字 + 邊緣合併圖")
        plt.axis("off")

        plt.subplot(1, 3, 3)
        plt.imshow(cv2.cvtColor(vis_text, cv2.COLOR_BGR2RGB))
        plt.title("最終裁切 + 文字框")
        plt.axis("off")

        plt.show()

        return self.bounding_box

    @Debug.event("get bounding v3", "blue")
    def get_trimmed_bounding_box_v3(self, idx: int = 0) -> Union[BoundingBox, None]:
        import matplotlib.pyplot as plt
        import cv2
        import numpy as np

        # === 1. 準備圖像與尺寸 ===
        page = self.get_page(idx)
        pix = page.get_pixmap()
        img = np.frombuffer(pix.samples, dtype=np.uint8).reshape((pix.height, pix.width, pix.n))
        if img.shape[2] == 4:
            img = img[:, :, :3]
        height, width = img.shape[:2]

        # === 2. Sobel 邊緣偵測找粗略區域 ===
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        sobelx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
        sobely = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
        sobel = cv2.magnitude(sobelx, sobely)
        sobel = np.uint8(np.clip(sobel, 0, 255))
        _, edge_bin = cv2.threshold(sobel, 30, 255, cv2.THRESH_BINARY)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 15))
        dilated_edge = cv2.dilate(edge_bin, kernel, iterations=1)

        # === 3. 找最大 Sobel 區域 ===
        num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(dilated_edge)
        if num_labels <= 1:
            return BoundingBox(0, 0, width, height)
        stats = stats[1:]
        max_stat = max(stats, key=lambda s: s[cv2.CC_STAT_AREA])
        ex, ey, ew, eh, _ = max_stat

        # === 4. 擷取區域內的文字框，並做擴散處理 ===
        blocks = self.get_blocks(idx)
        heatmap = np.zeros((height, width), dtype=np.uint8)
        inflate_percent = 0.1

        for b in blocks:
            x0, y0, x1, y1 = map(int, b[:4])
            w, h = x1 - x0, y1 - y0
            dx, dy = int(w * inflate_percent / 2), int(h * inflate_percent / 2)
            x0_, y0_ = max(x0 - dx, 0), max(y0 - dy, 0)
            x1_, y1_ = min(x1 + dx, width), min(y1 + dy, height)

            if ex <= x0_ <= x1_ <= ex + ew and ey <= y0_ <= y1_ <= ey + eh:
                cv2.rectangle(heatmap, (x0_, y0_), (x1_, y1_), 255, -1)

        expand_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 15))
        dilated_heatmap = cv2.dilate(heatmap, expand_kernel, iterations=1)

        # === 5. 使用密度滑窗 top-k 合併法 找密度最高區域 ===
        
        # 這裡使用新方法
        
        final_box = BoundingBox(x0, y0, x1, y1)
        self.bounding_box = final_box

        # === 6. 可視化 ===
        vis1 = cv2.cvtColor(dilated_heatmap, cv2.COLOR_GRAY2BGR)
        vis2 = cv2.cvtColor(dilated_edge, cv2.COLOR_GRAY2BGR)
        vis3 = img.copy()

        # 在 vis1 上標出處理過的元件（粉紅框）
        for b in blocks:
            x0, y0, x1, y1 = map(int, b[:4])
            w, h = x1 - x0, y1 - y0
            dx, dy = int(w * inflate_percent / 2), int(h * inflate_percent / 2)
            x0_, y0_ = max(x0 - dx, 0), max(y0 - dy, 0)
            x1_, y1_ = min(x1 + dx, width), min(y1 + dy, height)

            if ex <= x0_ <= x1_ <= ex + ew and ey <= y0_ <= y1_ <= ey + eh:
                cv2.rectangle(vis1, (x0_, y0_), (x1_, y1_), (255, 0, 255), 1)  # 粉紅框

        # vis2 畫上文字元件與 Sobel 區（藍、綠）
        for b in blocks:
            bx0, by0, bx1, by1 = map(int, b[:4])
            if ex <= bx0 <= bx1 <= ex + ew and ey <= by0 <= by1 <= ey + eh:
                cv2.rectangle(vis2, (bx0, by0), (bx1, by1), (255, 0, 0), 1)

        cv2.rectangle(vis2, (ex, ey), (ex + ew, ey + eh), (0, 255, 0), 2)  # Sobel 區（綠框）
        cv2.rectangle(vis3, (final_box.x0, final_box.y0), (final_box.x1, final_box.y1), (0, 0, 255), 3)  # 最終框（紅）

        import os
        filename = self.get_file_name()  # 假設這個回傳不含副檔名
        output_dir = os.path.join("output", filename)
        os.makedirs(output_dir, exist_ok=True)

        # 圖1：原圖（Sobel內元件）
        plt.figure(figsize=(6, 6))
        plt.imshow(cv2.cvtColor(vis1, cv2.COLOR_BGR2RGB))
        plt.title("原圖（Sobel內元件）")
        plt.axis("off")
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, f"{filename}_original_with_sobel_components.png"), dpi=300)
        plt.close()

        # 圖2：Sobel + 文字區
        plt.figure(figsize=(6, 6))
        plt.imshow(cv2.cvtColor(vis2, cv2.COLOR_BGR2RGB))
        plt.title("Sobel + 文字區")
        plt.axis("off")
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, f"{filename}_sobel_and_text_area.png"), dpi=300)
        plt.close()

        # 圖3：最終裁切框
        plt.figure(figsize=(6, 6))
        plt.imshow(cv2.cvtColor(vis3, cv2.COLOR_BGR2RGB))
        plt.title("最終裁切框")
        plt.axis("off")
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, f"{filename}_final_cropping_box.png"), dpi=300)
        plt.close()

        # 圖4：所有 word 的標註圖
        vis_words = img.copy()
        words = self.get_words(idx)
        for word in words:
            x0, y0, x1, y1 = map(int, word[:4])
            cv2.rectangle(vis_words, (x0, y0), (x1, y1), (0, 255, 255), 1)  # 黃框
            cv2.putText(vis_words, word[4], (x0, y0 - 2), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 255), 1)

        plt.figure(figsize=(8, 8))
        plt.imshow(cv2.cvtColor(vis_words, cv2.COLOR_BGR2RGB))
        plt.title("Word 標註圖")
        plt.axis("off")
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, f"{filename}_words_annotated.png"), dpi=300)
        plt.close()

        return self.bounding_box

    @Debug.event("get bounding v5", "blue")
    def get_trimmed_bounding_box_v5(self, idx:int = 0,
                                    small_win=50, small_stride=25,
                                    large_win=200, large_stride=100,
                                    top_k=10) -> BoundingBox:
        
        import matplotlib.pyplot as plt
        import cv2
        import numpy as np
        
        page = self.get_page(idx)
        pix = page.get_pixmap()
        img = np.frombuffer(pix.samples, dtype=np.uint8).reshape((pix.height, pix.width, pix.n))
        if img.shape[2] == 4:
            img = img[:, :, :3]
        height, width = img.shape[:2]
        
        heatmap = np.zeros((height, width), dtype=np.uint8)

        # Step 1: 建立 heatmap（將 blocks 畫入）
        for b in self.get_blocks(idx):
            x0, y0, x1, y1 = map(int, b[:4])
            cv2.rectangle(heatmap, (x0, y0), (x1, y1), 255, -1)

        # Step 2: Sobel 邊緣檢測 → 找到粗略外框
        sobel = cv2.Sobel(heatmap, cv2.CV_64F, 1, 1, ksize=3)
        abs_sobel = np.abs(sobel).astype(np.uint8)
        _, binary = cv2.threshold(abs_sobel, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        if not contours:
            return BoundingBox(0, 0, width, height)

        # 找出最大輪廓框起來
        contour = max(contours, key=cv2.contourArea)
        x_sob, y_sob, w_sob, h_sob = cv2.boundingRect(contour)
        sobel_bbox = BoundingBox(x_sob, y_sob, x_sob + w_sob, y_sob + h_sob)

        # Step 3: 限定於 sobel_bbox 範圍內執行雙階段密度分析
        density_map_small = []
        for y in range(y_sob - small_win, y_sob + h_sob, small_stride):
            for x in range(x_sob - small_win, x_sob + w_sob, small_stride):
                sx0, sy0 = max(x, 0), max(y, 0)
                sx1, sy1 = min(x + small_win, width), min(y + small_win, height)
                score = np.sum(heatmap[sy0:sy1, sx0:sx1] == 255)
                if score > 0:
                    density_map_small.append((score, sx0, sy0, sx1, sy1))

        if not density_map_small:
            return sobel_bbox

        # Step 4: 取前 K 高密度小視窗
        top_small = sorted(density_map_small, key=lambda s: s[0], reverse=True)[:top_k]

        # 再使用大視窗包含 top_small 區域
        large_windows = []
        for y in range(y_sob - large_win, y_sob + h_sob, large_stride):
            for x in range(x_sob - large_win, x_sob + w_sob, large_stride):
                lx0, ly0 = max(x, 0), max(y, 0)
                lx1, ly1 = min(x + large_win, width), min(y + large_win, height)
                overlaps = [1 for _, sx0, sy0, sx1, sy1 in top_small
                            if lx0 <= sx0 <= lx1 and ly0 <= sy0 <= ly1]
                if overlaps:
                    large_windows.append((len(overlaps), lx0, ly0, lx1, ly1))

        # Step 5: 生成精準紅框
        if not large_windows:
            x0 = min(w[1] for w in top_small)
            y0 = min(w[2] for w in top_small)
            x1 = max(w[3] for w in top_small)
            y1 = max(w[4] for w in top_small)
        else:
            x0 = min(w[1] for w in large_windows)
            y0 = min(w[2] for w in large_windows)
            x1 = max(w[3] for w in large_windows)
            y1 = max(w[4] for w in large_windows)

        final_bbox = BoundingBox(x0, y0, x1, y1)

        # Step 6: 可視化
        vis = cv2.cvtColor(heatmap, cv2.COLOR_GRAY2BGR)
        cv2.rectangle(vis, (sobel_bbox.x0, sobel_bbox.y0), (sobel_bbox.x1, sobel_bbox.y1), (255, 0, 255), 2)  # Sobel框
        for _, sx0, sy0, sx1, sy1 in top_small:
            cv2.rectangle(vis, (sx0, sy0), (sx1, sy1), (0, 255, 0), 1)
        for _, lx0, ly0, lx1, ly1 in large_windows:
            cv2.rectangle(vis, (lx0, ly0), (lx1, ly1), (255, 255, 0), 1)
        cv2.rectangle(vis, (x0, y0), (x1, y1), (0, 0, 255), 3)  # 最終紅框

        plt.figure(figsize=(12, 12))
        plt.imshow(vis)
        plt.title("v5：Sobel + 雙階段密度分析")
        plt.axis("off")
        plt.show()

        return final_bbox


    @Debug.event("get bounding box v6","blue")
    def get_trimmed_bounding_box_v6(self, idx:int = 0):
        # step.1 準備資料
        page = self.get_page(idx)
        pix = page.get_pixmap()
        img = np.frombuffer(pix.samples, dtype=np.uint8).reshape((pix.height, pix.width, pix.n))
        if img.shape[2] == 4:
            img = img[:, :, :3]
        height, width = img.shape[:2]
        
        # step.2 sobel
        sobel = self.get_sobel_bounding_box(idx)
        final = self.get_density_bounding_box_from_sobel_v2(
            sobel,idx,debug=True,
        )
        
        self.bounding_box = final
        
        return final
    
    def visualize_and_group_words(self, idx: int = 0, threshold: int = 10):
        import cv2
        import numpy as np
        import os
        import matplotlib.pyplot as plt

        page = self.get_page(idx)
        pix = page.get_pixmap()
        img = np.frombuffer(pix.samples, dtype=np.uint8).reshape((pix.height, pix.width, pix.n))
        if img.shape[2] == 4:
            img = img[:, :, :3]

        words = self.get_words(idx)
        horizontal, vertical = [], []

        # === 1. 分方向 ===
        for w in words:
            x0, y0, x1, y1, text = w[:5]
            if abs(x1 - x0) >= abs(y1 - y0):
                horizontal.append([x0, y0, x1, y1, text])
            else:
                vertical.append([x0, y0, x1, y1, text])

        # === 2. 分組聚合函式 ===
        def group_words(word_list, is_vertical=False):
            groups = []
            used = [False] * len(word_list)
            for i, w1 in enumerate(word_list):
                if used[i]:
                    continue
                x0_1, y0_1, x1_1, y1_1, text1 = w1
                group = [w1]
                used[i] = True
                for j in range(i+1, len(word_list)):
                    if used[j]:
                        continue
                    x0_2, y0_2, x1_2, y1_2, text2 = word_list[j]

                    if is_vertical:
                        close_x = abs(x0_1 - x0_2) < threshold
                        near_y = abs(y0_2 - y1_1) < threshold or abs(y1_2 - y0_1) < threshold
                        if close_x and near_y:
                            group.append(word_list[j])
                            used[j] = True
                    else:
                        close_y = abs(y0_1 - y0_2) < threshold
                        near_x = abs(x0_2 - x1_1) < threshold or abs(x1_2 - x0_1) < threshold
                        if close_y and near_x:
                            group.append(word_list[j])
                            used[j] = True
                groups.append(group)
            return groups

        # === 3. 執行分組聚合 ===
        h_groups = group_words(sorted(horizontal, key=lambda w: (w[1], w[0])), is_vertical=False)
        v_groups = group_words(sorted(vertical, key=lambda w: (w[0], w[1])), is_vertical=True)

        # === 4. 視覺化 ===
        vis = img.copy()
        color_h = (0, 255, 0)  # 綠色 for 水平
        color_v = (0, 0, 255)  # 紅色 for 垂直
        font = cv2.FONT_HERSHEY_SIMPLEX

        def draw_groups(groups, color, is_vertical=False):
            for group in groups:
                x0 = min(int(w[0]) for w in group)
                y0 = min(int(w[1]) for w in group)
                x1 = max(int(w[2]) for w in group)
                y1 = max(int(w[3]) for w in group)
                content = "".join(w[4] for w in sorted(group, key=lambda w: (w[1], w[0]) if not is_vertical else (w[0], w[1])))
                cv2.rectangle(vis, (x0, y0), (x1, y1), color, 1)
                cv2.putText(vis, content, (x0, max(0, y0 - 5)), font, 0.5, color, 1)
                print(f"詞內容：{content}，座標：({x0},{y0}) - ({x1},{y1})")

        draw_groups(h_groups, color_h, is_vertical=False)
        draw_groups(v_groups, color_v, is_vertical=True)

        # === 5. 輸出 ===
        file_name = self.get_file_name()
        out_dir = os.path.join("output", file_name)
        os.makedirs(out_dir, exist_ok=True)
        out_path = os.path.join(out_dir, f"{file_name}_聚合詞視覺化.png")
        cv2.imwrite(out_path, vis)

        plt.figure(figsize=(12, 12))
        plt.imshow(cv2.cvtColor(vis, cv2.COLOR_BGR2RGB))
        plt.title("詞聚合結果")
        plt.axis("off")
        plt.show()
    
    def get_file_name(self) -> str:
        """
        回傳PDF的檔名
        """
        return self.path.split("/")[-1]
            
    def get_page(self,idx:int=0):
        """get: pdf page"""
        return self.doc.load_page(idx)

    def get_pixmap(self,zoom,idx:int=0):
        # 解析度
        mat = fitz.Matrix(zoom,zoom)
        
        return self.get_page(idx).get_pixmap(matrix=mat)
    
    def get_blocks(self,idx:int=0):
        """建立搜尋頁面source"""
        return self.get_page(idx).get_text("blocks")
    
    def get_words(self,idx:int=0):
        """建立搜尋頁面source"""
        return self.get_page(idx).get_text("words")

    @property
    def path(self):
        """get path"""
        return self._path

    @path.setter
    def path(self, value):
        if value is None:
            print("path 設定為 None，忽略這次設定")
            return
        if value == self._path:
            print("path 與原本相同，忽略設定")
            return

        # 在設定前先驗證 PDF 是否有效
        valid, msg = self.is_valid_pdf(value)
        if not valid:
            print(f"設定路徑失敗：{msg}")
            return

        print(f"PDF path changed to: {value}")
        self._path = value
        self.doc = self.open_pdf_file(value)

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

    @staticmethod
    @handle_file_open_error
    def open_pdf_file(path: str) -> fitz.Document:
        """fitz開檔"""
        return fitz.open(path)

