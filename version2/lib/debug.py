from colorama import init, Fore, Style

init(autoreset=True)

class Debug:
    COLOR_MAP = {
        "black": Fore.BLACK,
        "red": Fore.RED,
        "green": Fore.GREEN,
        "yellow": Fore.YELLOW,
        "blue": Fore.BLUE,
        "magenta": Fore.MAGENTA,
        "cyan": Fore.CYAN,
        "white": Fore.WHITE,
        "reset": Fore.RESET,
    }

    @staticmethod
    def function_runtime(func):
        from time import time
        def wrapper(*args,**kwargs):
            a = time()
            res = func(*args,**kwargs)
            b = time()
            print(Fore.YELLOW+"程式耗時: ",b-a)
            return res
        return wrapper


    @staticmethod
    def event(event_name="DEBUG", color="red"):
        """可帶事件名稱與顏色（可為 Fore 或 字串）的裝飾器
        * black
        * red
        * green
        * yellow
        * blue
        * magenta
        * cyan
        * white
        """
        # 如果 color 是字串，就轉換為 Fore 顏色
        if isinstance(color, str):
            color = Debug.COLOR_MAP.get(color.lower(), Fore.RED)  # 預設為紅色

        def decorator(func):
            def wrapper(*args, **kwargs):
                print(color + "[" + Style.BRIGHT + event_name + Style.NORMAL + color + "] ----")
                res = func(*args, **kwargs)
                print("")
                return res
            return wrapper
        return decorator
