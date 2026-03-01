import mss
import cv2
import numpy as np
import pytesseract
import pyperclip
from PIL import Image
import keyboard
import threading
import time

pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'


def run_ocr():
    with mss.mss() as sct:
        monitor = sct.monitors[1]
        screenshot = sct.grab(monitor)
        img = np.array(screenshot)
        img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)

        cv2.namedWindow("OCR Snip", cv2.WND_PROP_FULLSCREEN)
        cv2.setWindowProperty("OCR Snip", cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

        cv2.putText(img, "Drag to select - ENTER to OCR | ESC to cancel",
                    (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

        cv2.imshow("OCR Snip", img)
        cv2.waitKey(1)

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


def toggle():
    threading.Thread(target=run_ocr, daemon=True).start()

keyboard.add_hotkey('ctrl + shift + t', toggle)

keyboard.wait()
