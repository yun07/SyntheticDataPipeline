import os
import argparse
import numpy as np
import imageio.v2 as imageio


def exr_depth_to_png16(exr_path):
    if not os.path.exists(exr_path):
        raise ValueError(f"無效路徑: {exr_path}")

    base_path = os.path.splitext(exr_path)[0]
    tmp_path = base_path + ".png.tmp"
    final_path = base_path + ".png"

    try:
        # 1. 讀取與通道處理
        img_raw = imageio.imread(exr_path)
        img_val = img_raw[:, :, 0] if img_raw.ndim == 3 else img_raw

        # 2. 轉碼 16-bit
        valid_mask = np.isfinite(img_val) & (img_val >= 0.0) & (img_val <= 1.0)
        img16 = np.where(
            valid_mask,
            np.round(img_val * 65534.0),
            65535
        ).astype(np.uint16)

        # 3. 寫入臨時檔 .tmp (指定 format="png" 避免 UE Python 環境識別失敗)
        imageio.imwrite(tmp_path, img16, format="png")

        # 4. 極簡 Validation
        if not os.path.exists(tmp_path) or os.path.getsize(tmp_path) == 0:
            raise RuntimeError("PNG 寫入失敗或檔案大小為 0")

        # 5. 檢查並移除已存在的舊 .png 檔
        if os.path.exists(final_path):
            os.remove(final_path)

        # 6. Atomic 重命名 & 刪除原 EXR
        os.replace(tmp_path, final_path)
        os.remove(exr_path)

        print(f"[SUCCESS] {exr_path} -> {final_path} (EXR deleted)")

    except Exception as e:
        # 中途失敗時清理 .tmp 殘留檔
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        raise e


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Atomic convert normalized EXR depth to 16-bit PNG.")
    parser.add_argument("exr_path", type=str, help="EXR 檔案路徑")
    args = parser.parse_args()

    try:
        exr_depth_to_png16(args.exr_path)
    except Exception as e:
        print(f"[ERROR] {e}")