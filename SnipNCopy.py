import mss
import cv2
import numpy as np
import pytesseract
import pyperclip
from PIL import Image
import keyboard
import threading
import time
import tkinter as tk
from tkinter import ttk

pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

_snip_lock = threading.Lock()
_root = None
_status_var = None
_saved_geometry = None   # <-- added to store geometry before hiding

def show_countdown(delay):
    if delay <= 0:
        return
    count_root = tk.Tk()
    count_root.title("")
    count_root.overrideredirect(True)
    count_root.attributes('-topmost', True)
    count_root.configure(bg='black')
    count_root.attributes('-alpha', 0.7)
    screen_width = count_root.winfo_screenwidth()
    screen_height = count_root.winfo_screenheight()
    win_width, win_height = 200, 200
    x = (screen_width - win_width) // 2
    y = (screen_height - win_height) // 2
    count_root.geometry(f"{win_width}x{win_height}+{x}+{y}")
    label = tk.Label(count_root, text=str(delay), font=("Helvetica", 72),
                     fg="white", bg="black")
    label.pack(expand=True)

    def update_count(remaining):
        if remaining <= 0:
            count_root.destroy()
            return
        label.config(text=str(remaining))
        count_root.after(1000, update_count, remaining - 1)

    count_root.after(1000, update_count, delay - 1)
    count_root.mainloop()

def run_ocr(delay=0):
    global _root, _status_var
    if not _snip_lock.acquire(blocking=False):
        print("Snip already in progress.")
        return
    try:
        if _status_var:
            _root.after(0, lambda: _status_var.set("DELAY..."))

        if delay > 0:
            count_thread = threading.Thread(target=show_countdown, args=(delay,), daemon=True)
            count_thread.start()
            time.sleep(delay)
            time.sleep(0.2)

        if _status_var:
            _root.after(0, lambda: _status_var.set("SNIPPING..."))

        with mss.mss() as sct:
            monitor = sct.monitors[1]
            screenshot = sct.grab(monitor)
            img = np.array(screenshot)
            img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)

            cv2.namedWindow("OCR Snip", cv2.WND_PROP_FULLSCREEN)
            cv2.setWindowProperty("OCR Snip", cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
            cv2.setWindowProperty("OCR Snip", cv2.WND_PROP_TOPMOST, 1)
            cv2.imshow("OCR Snip", img)
            cv2.waitKey(1)
            time.sleep(0.1)

            rect = cv2.selectROI("OCR Snip", img, False)
            cv2.destroyAllWindows()

            x, y, w, h = rect
            if w > 0 and h > 0:
                region = {'left': x, 'top': y, 'width': w, 'height': h}
                selection = sct.grab(region)
                pil_img = Image.frombytes('RGB', selection.size, selection.rgb)
                gray = pil_img.convert('L')
                text = pytesseract.image_to_string(gray)
                lines = text.strip().split('\n')
                clean_text = ' '.join([line.strip() for line in lines if line.strip()])
                if clean_text:
                    pyperclip.copy(clean_text)
                    result = "SUCCESS"
                    print("Text copied to clipboard!")
                else:
                    result = "NO TEXT"
                    print("No text found.")
            else:
                result = "CANCELLED"
                print("Selection cancelled.")
    except Exception as e:
        print(f"Error: {e}")
        result = "ERROR"
    finally:
        _snip_lock.release()
        if _root:
            _root.after(0, lambda: restore_ui(_root, result))

def restore_ui(window, status):
    global _status_var, _saved_geometry
    window.deiconify()
    window.update_idletasks()   # let window manager process the deiconify

    if _saved_geometry:
        try:
            window.geometry(_saved_geometry)
        except Exception:
            # fallback: keep the default size if something goes wrong
            window.geometry("300x150")

    window.update_idletasks()
    window.lift()
    window.focus_force()
    if _status_var:
        _status_var.set(status)

def start_snip(delay):
    global _root, _status_var, _saved_geometry
    if _root:
        if _status_var:
            _status_var.set("STARTING...")
        # save geometry so it can be restored exactly later
        _saved_geometry = _root.winfo_geometry()
        _root.withdraw()
        _root.update()
        time.sleep(0.2)

    thread = threading.Thread(target=run_ocr, args=(delay,), daemon=True)
    thread.start()

def create_ui():
    global _root, _status_var
    _root = tk.Tk()
    _root.title("Text Snip")
    _root.geometry("300x150")
    _root.minsize(300, 150)
    _root.maxsize(300, 150)
    _root.resizable(False, False)
    _root.lift()
    _root.attributes('-topmost', True)
    _root.attributes('-topmost', False)

    ttk.Label(_root, text="Delay (seconds):").pack(pady=(10, 0))
    delay_var = tk.IntVar(value=0)
    delay_combo = ttk.Combobox(_root, textvariable=delay_var, values=[0, 1, 2, 3],
                               state="readonly", width=5)
    delay_combo.pack(pady=5)

    def on_snip_click():
        start_snip(delay_var.get())

    ttk.Button(_root, text="Take Snip", command=on_snip_click).pack(pady=10)

    _status_var = tk.StringVar(value="IDLE")
    status_label = ttk.Label(_root, textvariable=_status_var, foreground="blue")
    status_label.pack(pady=(0,5))

    ttk.Label(_root, text="Hotkey: Ctrl+Shift+T (delay 0)").pack(pady=(0,5))

    keyboard.add_hotkey('ctrl+shift+t', lambda: start_snip(0))
    _root.mainloop()

if __name__ == "__main__":
    create_ui()
