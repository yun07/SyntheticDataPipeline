import os
import argparse
import imageio.v2 as imageio


def png_r_to_grayscale(png_path):
    if not os.path.exists(png_path):
        raise ValueError(f"無效路徑: {png_path}")

    tmp_path = png_path + ".tmp"

    try:
        # 1. 讀取並直接提取 R 通道 (8-bit uint8)
        img = imageio.imread(png_path)
        img_r = img[:, :, 0] if img.ndim == 3 else img

        # 2. 寫入臨時檔
        imageio.imwrite(tmp_path, img_r, format="png")

        # 3. 驗證
        if not os.path.exists(tmp_path) or os.path.getsize(tmp_path) == 0:
            raise RuntimeError("PNG 寫入失敗或檔案大小為 0")

        # 4. Atomic 覆蓋原檔
        os.replace(tmp_path, png_path)
        print(f"[SUCCESS] {png_path} -> Updated with R channel")

    except Exception as e:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        raise e


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract R channel from 8-bit PNG.")
    parser.add_argument("png_path", type=str, help="PNG 檔案路徑")
    args = parser.parse_args()

    try:
        png_r_to_grayscale(args.png_path)
    except Exception as e:
        print(f"[ERROR] {e}")