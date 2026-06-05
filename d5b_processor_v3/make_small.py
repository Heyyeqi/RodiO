# make_small.py
import sys
from PIL import Image
Image.MAX_IMAGE_PIXELS = None

def make_small(src, dst, width=2048, height=1024):
    print(f"读取: {src}")
    img = Image.open(src).convert("RGB")
    print(f"原始分辨率: {img.size}")
    img = img.resize((width, height), Image.LANCZOS)
    img.save(dst, "JPEG", quality=95)
    print(f"小图已保存: {dst} ({width}×{height})")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("用法: python make_small.py <输入图> <输出图>")
        sys.exit(1)
    make_small(sys.argv[1], sys.argv[2])
