import argparse
import json
from pathlib import Path
import re
import shutil
import matplotlib.pyplot as plt
import numpy as np
import torch
import torch.nn.functional as F
from PIL import Image
from transformers import SegformerForSemanticSegmentation, SegformerImageProcessor

# ==================== 全域變數與參數設定 ====================
DEFAULT_BASE_DIR = "."             # 預設資料夾路徑
DEFAULT_INDEX = None              # 預設指定圖片 Index (若非 None 則優先處理單張)
LAST_N_IMAGES = 10                # 批次視覺化最後 N 張圖片的數量
DEFAULT_SUBDIR = "visualisations" # 批次圖片輸出的子資料夾名稱
IMAGE_DPI = 150                   # 儲存圖片解析度
DARK_BG_COLOR = "#121212"         # 畫布背景顏色 (深黑)
TEXT_COLOR = "#FFFFFF"            # 文字顏色 (純白)
# ==========================================================

def process_single_image(
    rgb_path, stencil_dir, model, processor, device, base_path, output_png, palette, overwrite=False
):
    """處理單張圖片推論與視覺化繪圖"""
    if output_png.exists() and not overwrite:
        print(f"⏩ {output_png.name} 已存在，跳過。")
        return True

    idx_match = re.search(r"\d+", rgb_path.stem)
    idx_str = idx_match.group(0) if idx_match else rgb_path.stem

    stencil_path = next((f for f in stencil_dir.glob("*.[jp][pn]g") if idx_str in f.stem), None)
    if not stencil_path:
        print(f"⚠️ 找不到對應 Stencil (Index: {idx_str}, RGB: {rgb_path.name})，跳過處理。")
        return False

    # 載入影像與模型推論
    rgb_img = Image.open(rgb_path).convert("RGB")
    sem_array = np.array(Image.open(stencil_path).convert("L"))
    h, w = sem_array.shape

    inputs = processor(images=rgb_img, return_tensors="pt").to(device)
    with torch.no_grad():
        logits = model(**inputs).logits

    upsampled = F.interpolate(logits, size=(h, w), mode="bilinear", align_corners=False)
    pred_array = upsampled.argmax(dim=1).squeeze().cpu().numpy()
    confidence = F.softmax(upsampled, dim=1).squeeze().max(dim=0).values.cpu().numpy()

    # 繪製 4-panel 圖表
    fig, axes = plt.subplots(1, 4, figsize=(18, 5), facecolor=DARK_BG_COLOR)
    titles = ["RGB Render", "Ground Truth", "Prediction", "Confidence"]
    images = [np.array(rgb_img), palette[sem_array], palette[pred_array], confidence]

    for ax, title, img in zip(axes, titles, images):
        ax.set_facecolor(DARK_BG_COLOR)
        ax.set_title(title, color=TEXT_COLOR, fontsize=12, fontweight="bold")
        ax.axis("off")
        
        if title == "Confidence":
            im = ax.imshow(img, cmap="RdYlGn", vmin=0.0, vmax=1.0)
            cbar = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
            cbar.ax.yaxis.set_tick_params(color=TEXT_COLOR)
            plt.setp(cbar.ax.get_yticklabels(), color=TEXT_COLOR)
        else:
            ax.imshow(img)

    plt.suptitle(
        f"{base_path.name} — SegFormer Visualisation ({rgb_path.name})",
        color=TEXT_COLOR,
        fontsize=14,
        fontweight="bold"
    )
    plt.tight_layout()
    
    plt.savefig(output_png, dpi=IMAGE_DPI, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    print(f"📊 成功儲存預測圖 → {output_png.name}")
    return True


def visualise(
    base_dir=DEFAULT_BASE_DIR,
    index=DEFAULT_INDEX,
    last_n=LAST_N_IMAGES,
    output_subdir=DEFAULT_SUBDIR,
    overwrite=False
):
    base_path = Path(base_dir).absolute()
    rgb_dir, stencil_dir = base_path / "rgb", base_path / "stencil"
    model_dir = base_path / "runs" / "best_model"

    rgb_files = sorted(list(rgb_dir.glob("*.[jp][pn]g")))
    if not rgb_files:
        raise FileNotFoundError(f"❌ {rgb_dir} 內找不到圖片")

    # 一次性解析 Class.json 並建立 Color Palette (LUT)
    with open(base_path / "Class.json", "r", encoding="utf-8") as f:
        classes_data = json.load(f)

    id2label = {int(item["id"]): item["class"] for item in classes_data}
    id2label.setdefault(0, "background")
    max_id = max(id2label.keys())
    cmap = plt.get_cmap("tab10", max_id + 1)
    palette = np.zeros((max_id + 1, 3), dtype=np.uint8)
    for cid in id2label:
        palette[cid] = [0, 0, 0] if cid == 0 else (np.array(cmap(cid)[:3]) * 255).astype(np.uint8)

    # 一次性載入模型
    device = "cuda" if torch.cuda.is_available() else "cpu"
    processor = SegformerImageProcessor.from_pretrained(model_dir)
    model = SegformerForSemanticSegmentation.from_pretrained(model_dir).to(device).eval()

    # 模式 1：指定 Index (產出單張至根目錄)
    if index is not None:
        rgb_path = next((f for f in rgb_files if str(index) in f.stem), None)
        if not rgb_path:
            raise FileNotFoundError(f"❌ 找不到 Index: {index}")
        
        output_png = base_path / f"visualisation_{rgb_path.stem}.png"
        process_single_image(
            rgb_path, stencil_dir, model, processor, device, base_path, output_png, palette, overwrite
        )
        return

    # 模式 2：批次處理最後 N 張圖片 (存入子資料夾) + 保留最新 1 張至根目錄
    target_files = rgb_files[-last_n:] if last_n and len(rgb_files) >= last_n else rgb_files
    out_dir = base_path / output_subdir
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"🔍 準備處理最後 {len(target_files)} 張圖片至 '{output_subdir}'...")
    for rgb_path in target_files:
        output_png = out_dir / f"visualisation_{rgb_path.stem}.png"
        process_single_image(
            rgb_path, stencil_dir, model, processor, device, base_path, output_png, palette, overwrite
        )

    # 將最新 1 張圖片複製至根目錄 (透過檔案複製，節省推論時間)
    latest_rgb = rgb_files[-1]
    sub_latest_png = out_dir / f"visualisation_{latest_rgb.stem}.png"
    root_latest_png = base_path / f"visualisation_{latest_rgb.stem}.png"
    
    if sub_latest_png.exists():
        shutil.copy2(sub_latest_png, root_latest_png)
        print(f"📌 最新預測圖已複製至根目錄 → {root_latest_png.name}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SegFormer 可視化繪圖腳本")
    parser.add_argument("dir", type=str, nargs="?", default=DEFAULT_BASE_DIR, help="根目錄路徑")
    parser.add_argument("--index", type=int, default=DEFAULT_INDEX, help="指定單張圖片 Index")
    parser.add_argument("--last-n", type=int, default=LAST_N_IMAGES, help="批次處理最後 N 張圖片")
    parser.add_argument("--subdir", type=str, default=DEFAULT_SUBDIR, help="批次圖片輸出子資料夾名稱")
    parser.add_argument("--overwrite", action="store_true", help="強制重新計算並覆蓋已有圖片")
    
    args = parser.parse_args()
    
    visualise(
        base_dir=args.dir,
        index=args.index,
        last_n=args.last_n,
        output_subdir=args.subdir,
        overwrite=args.overwrite
    )