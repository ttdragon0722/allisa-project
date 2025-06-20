from sklearn.cluster import DBSCAN
from collections import defaultdict

from lib.data.models import FoundResult, ZoomScreen
from .debug import Debug

class ViewResult:
    def __init__(self):
        self.result: FoundResult = None
        self.cur_idx = 0
        self.screens = []
    
    def check_bounds(self, direction: str) -> bool:
        """索引邊界"""
        if direction == "prev" and self.cur_idx <= 0:
            print("⚠️ 已是第一筆")
            return False
        elif direction == "next" and self.cur_idx >= self.screens_length() - 1:
            print("⚠️ 已是最後一筆")
            return False
        return True
    
    def current_page(self) -> str:
        """return 當前索引的正反面"""
        return self.current_screen().side

    def current_screen(self) -> ZoomScreen:
        """return 當前索引搜尋結果視窗"""
        return self.screens[self.cur_idx] 

    def current_log(self):
        """DEBUG: 印出當前頁面"""
        print(self.current_screen())
    
    def screens_length(self) -> int:
        """return 頁面數"""
        return len(self.screens)
    
    def set_result(self,result:FoundResult):
        self.result = result
        self.side_group = self.result.get_by_side()
        if self.result.total > 0:
            self.cur_idx = 0
            
    
    @Debug.event("DBSCAN", color="blue")
    def group_DBSCAN(self, zoom_width=400, zoom_height=300, zoom=5) -> list[ZoomScreen]:
        """
        對 self.side_group 中的 BoxInfo 做 DBSCAN 分群，並依分群結果產生 ZoomScreen 區塊。
        如果沒有任何搜尋結果，或個別面為空，會直接跳過或回傳空陣列。
        """
        # 防呆：如果總體沒結果，直接返回
        if self.result.total == 0:
            print("❌ 搜尋結果為 0，跳過分群")
            return []
        
        eps = min(zoom_width, zoom_height) / zoom / 2  # 聚落半徑
        result_screens = []
        
        for side, box_list in self.side_group.items():
            if not box_list:
                print(f"⚠️ {side} 沒有任何 box，略過")
                continue

            print(f"🔍 處理 {side}，共 {len(box_list)} 個元件")
            points = [box.center for box in box_list]
            clustering = DBSCAN(eps=eps, min_samples=1).fit(points)

            clusters = defaultdict(list)
            for label, box in zip(clustering.labels_, box_list):
                clusters[label].append(box)

            print(clusters)

            for label, cluster_boxes in clusters.items():
                if len(cluster_boxes) == 1:
                    # 單點，置中顯示
                    cx, cy = cluster_boxes[0].center
                    x0 = int(cx - zoom_width / (2 * zoom))
                    y0 = int(cy - zoom_height / (2 * zoom))
                    x1 = int(cx + zoom_width / (2 * zoom))
                    y1 = int(cy + zoom_height / (2 * zoom))
                else:
                    # 多點，包住 + padding
                    x0 = min(b.x0 for b in cluster_boxes)
                    y0 = min(b.y0 for b in cluster_boxes)
                    x1 = max(b.x1 for b in cluster_boxes)
                    y1 = max(b.y1 for b in cluster_boxes)

                    pad_x = zoom_width / zoom / 2
                    pad_y = zoom_height / zoom / 2
                    x0 -= pad_x
                    y0 -= pad_y
                    x1 += pad_x
                    y1 += pad_y

                print(cluster_boxes)

                result_screens.append(ZoomScreen(
                    side=side,
                    x0=int(x0),
                    y0=int(y0),
                    x1=int(x1),
                    y1=int(y1),
                    zoom=zoom,
                    labels=cluster_boxes 
                ))
                
        self.screens = result_screens

        return result_screens
