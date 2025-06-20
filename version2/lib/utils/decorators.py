from tkinter import messagebox

def function_runtime(func):
    from time import time
    def wrapper(*args,**kwargs):
        a = time()
        res = func(*args,**kwargs)
        b = time()
        print("程式耗時: ",b-a)
        return res
    return wrapper

def handle_file_open_error(func):
    """處理開啟PDF的錯誤"""
    def wrapper(*args, **kwargs):
        try:
            doc = func(*args,**kwargs)
        except Exception as e:
            messagebox.showerror("錯誤", f"無法開啟 PDF：{e}")
            print("無法開啟PDF")
            return None
        return doc
    return wrapper
