from .data.models import File
import os

from .debug import Debug

class FilePicker:
    def __init__(self, folder_path: str):
        """讀取資料夾下的所有資料"""
        if not os.path.exists(folder_path):
            raise ValueError(f"指定的路徑不存在: {folder_path}")
        if not os.path.isdir(folder_path):
            raise ValueError(f"指定的路徑不是資料夾: {folder_path}")
        self.folder_path = folder_path
        
        self.files:list[File] = self.get_files()
        
        # 篩選PDF
        self.files = self.get_pdf_files()
        

    def get_files(self) -> list[File]:
        file_list = []
        for filename in os.listdir(self.folder_path):
            full_path = os.path.join(self.folder_path, filename)
            if os.path.isfile(full_path):
                mod_time = os.path.getmtime(full_path)
                _, ext = os.path.splitext(filename)
                ext = ext[1:].lower() if ext else ''
                file_list.append(File(path=full_path, name=filename, mod_time=mod_time, ext=ext))
        # 按名字降序排序（T 會先出現）
        file_list.sort(key=lambda f: f.name.lower(), reverse=True)
        return file_list
    
    def get_pdf_files(self) -> list[File]:
        return [f for f in self.files if f.ext == 'pdf']

    def search_files(self, keyword: str) -> list[File]:
        """依關鍵字過濾檔案名稱，回傳符合的檔案清單"""
        keyword = keyword.lower()
        return [f for f in self.files if keyword in f.name.lower()]