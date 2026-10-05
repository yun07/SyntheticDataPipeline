import glob
import json
import os
import sys
import yaml  # 需安裝 pyyaml (pip install pyyaml)
from PIL import Image, ImageDraw, ImageFont

# ==========================================
# 頂部變數設定 (GLOBAL / CONFIG VARIABLES)
# ==========================================
# 傳入的第一個參數（可以是資料夾或單一檔案）
INPUT_ARG = sys.argv[1] if len(sys.argv) > 1 else "."

# 判斷輸入是檔案還是資料夾
IS_SINGLE_FILE = os.path.isfile(INPUT_ARG)

if IS_SINGLE_FILE:
    # 如果是單一檔案，預設輸出資料夾為該檔案所在的資料夾
    DEFAULT_OUTPUT_DIR = os.path.dirname(INPUT_ARG) or "."
    INPUT_DIR = os.path.dirname(INPUT_ARG) or "."
else:
    DEFAULT_OUTPUT_DIR = INPUT_ARG
    INPUT_DIR = INPUT_ARG

# 若有傳第二個參數，則覆蓋預設輸出資料夾
OUTPUT_DIR = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_OUTPUT_DIR

IMAGE_WIDTH = 600               # 圖片寬度 (像素)
IMAGE_HEIGHT = 600              # 圖片高度 (像素)
BACKGROUND_COLOR = (30, 30, 30)  # 背景顏色 (RGB)
HEADER_TEXT_COLOR = (255, 255, 0)# 標題文字顏色 (黃色)
KEY_TEXT_COLOR = (0, 255, 255)   # Key / 區塊標題顏色 (青色)
BODY_TEXT_COLOR = (255, 255, 255)  # 屬性文字顏色 (白色)

# ------------------------------------------
# 🔤 文字大小與行距設定
# ------------------------------------------
FONT_SIZE = 22                   # 全局文字大小
HEADER_FONT_SIZE = 26            # 標題文字大小

LINE_HEIGHT = FONT_SIZE + 10     # 單行行高
PARENT_SPACING = 18              # 主屬性區塊之間的隔行距離

START_X = 40                     # 文字起始 X 座標
START_Y = 40                     # 文字起始 Y 座標
INDENT_X = 35                    # 第一層縮排距離 (像素)
HEADER_PADDING = 40              # 標題與內文之間的間距
WORD_SEPARATOR = "   :   "       # Key 與 Value 之間的加寬間距

IMAGE_FORMAT = "JPEG"            # 輸出圖片格式
IMAGE_EXT = ".jpg"               # 輸出副檔名

# ==========================================
# 載入系統預設字型
# ==========================================
try:
    font = ImageFont.truetype("arial.ttf", FONT_SIZE)
    header_font = ImageFont.truetype("arial.ttf", HEADER_FONT_SIZE)
except OSError:
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", FONT_SIZE)
        header_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", HEADER_FONT_SIZE)
    except OSError:
        font = ImageFont.load_default()
        header_font = font

# ==========================================
# 輔助函式：清理字串
# ==========================================
def clean_text(val):
    if isinstance(val, (dict, list)):
        val_str = json.dumps(val, ensure_ascii=False)
    else:
        val_str = str(val)
    return val_str.replace("'", "").replace('"', "")

# ==========================================
# 輔助函式：遞迴繪製結構化資料 (Dict & List)
# ==========================================
def draw_data(draw, data, x, y, is_root=False):
    current_y = y

    if isinstance(data, dict):
        for k, v in data.items():
            clean_k = clean_text(k)

            if isinstance(v, (dict, list)):
                draw.text((x, current_y), f"{clean_k}{WORD_SEPARATOR}", fill=KEY_TEXT_COLOR, font=font)
                current_y += LINE_HEIGHT
                current_y = draw_data(draw, v, x + INDENT_X, current_y)
                if is_root:
                    current_y += PARENT_SPACING
            else:
                clean_v = clean_text(v)
                text_line = f"{clean_k}{WORD_SEPARATOR}{clean_v}"
                draw.text((x, current_y), text_line, fill=BODY_TEXT_COLOR, font=font)
                current_y += LINE_HEIGHT
                if is_root:
                    current_y += PARENT_SPACING

    elif isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                first = True
                for k, v in item.items():
                    clean_k = clean_text(k)
                    clean_v = clean_text(v)
                    prefix = "- " if first else "  "
                    text_line = f"{prefix}{clean_k}{WORD_SEPARATOR}{clean_v}"
                    draw.text((x, current_y), text_line, fill=BODY_TEXT_COLOR, font=font)
                    current_y += LINE_HEIGHT
                    first = False
                current_y += 8
            else:
                clean_item = clean_text(item)
                draw.text((x, current_y), f"- {clean_item}", fill=BODY_TEXT_COLOR, font=font)
                current_y += LINE_HEIGHT

    return current_y

# ==========================================
# 主程式邏輯
# ==========================================
os.makedirs(OUTPUT_DIR, exist_ok=True)

# 準備待處理檔案列表
if IS_SINGLE_FILE:
    input_files = [INPUT_ARG]
else:
    input_files = []
    for ext in ("*.json", "*.yaml", "*.yml"):
        input_files.extend(glob.glob(os.path.join(INPUT_DIR, ext)))

if not input_files:
    print(f"No valid JSON/YAML files found at '{INPUT_ARG}'")
    sys.exit(0)

print(f"Processing {len(input_files)} file(s) -> '{OUTPUT_DIR}'...\n")

for file_path in sorted(input_files):
    filename = os.path.basename(file_path)
    base_name, file_ext = os.path.splitext(filename)
    jpg_path = os.path.join(OUTPUT_DIR, f"{base_name}{IMAGE_EXT}")

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            if file_ext.lower() in [".yaml", ".yml"]:
                data = yaml.safe_load(f)
            else:
                data = json.load(f)

        img = Image.new("RGB", (IMAGE_WIDTH, IMAGE_HEIGHT), color=BACKGROUND_COLOR)
        draw = ImageDraw.Draw(img)

        current_y = START_Y
        clean_filename = clean_text(filename)
        draw.text((START_X, current_y), f"FILE   {clean_filename}", fill=HEADER_TEXT_COLOR, font=header_font)
        current_y += HEADER_PADDING

        draw_data(draw, data, START_X, current_y, is_root=True)

        img.save(jpg_path, IMAGE_FORMAT)

        if os.path.exists(jpg_path):
            print(f"Successfully generated: {jpg_path}")

    except Exception as e:
        print(f"Error processing {file_path}: {e}")