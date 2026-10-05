import os, json, argparse
from pathlib import Path
from datetime import datetime

def generate_coco(dataset_dir, min_area=50, num_workers=8):
    base_path = Path(dataset_dir.strip('\u202a\u202b\u202c\u202d\u202e\u200f ')).absolute()
    output_json = base_path / "coco_annotations.json"
    if output_json.exists(): return print(f"⏩ [SKIP] 檔案已存在: {output_json}")

    stencil_dir, class_json = base_path / "stencil", base_path / "Class.json"
    if not class_json.exists() or not stencil_dir.exists(): return print("❌ 找不到 Class.json 或 stencil 資料夾！")

    # Lazy Import
    import cv2, numpy as np
    from concurrent.futures import ThreadPoolExecutor

    with open(class_json, "r", encoding="utf-8") as f:
        categories = [{"id": c["id"], "name": c["class"]} for c in json.load(f)]
    png_files = sorted([f.name for f in stencil_dir.glob("*.png")])
    if not png_files: return print(f"❌ 搵唔到 PNG 檔案！")

    def process_single_image(args):
        img_id, file_name = args
        sem_array = cv2.imread(str(stencil_dir / file_name), cv2.IMREAD_GRAYSCALE)
        if sem_array is None: return None
        
        unique_ids, anns = np.unique(sem_array), []
        for cat in categories:
            if cat["id"] not in unique_ids: continue
            binary_mask = (sem_array == cat["id"]).astype(np.uint8)
            contours, _ = cv2.findContours(binary_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            polygons = [c.flatten().tolist() for c in contours if cv2.contourArea(c) >= min_area and len(c.flatten()) >= 6]
            if polygons:
                x, y, bw, bh = cv2.boundingRect(cv2.findNonZero(binary_mask))
                anns.append({"image_id": img_id, "category_id": cat["id"], "segmentation": polygons, "area": int(np.sum(binary_mask)), "bbox": [x, y, bw, bh], "iscrowd": 0})
        print(f"[{img_id}] Processed: {file_name}")
        return {"id": img_id, "file_name": file_name, "width": sem_array.shape[1], "height": sem_array.shape[0]}, anns

    with ThreadPoolExecutor(max_workers=num_workers) as executor:
        results = list(executor.map(process_single_image, [(i, f) for i, f in enumerate(png_files, start=1)]))

    images, all_anns, ann_id = [], [], 1
    for res in filter(None, results):
        img_info, anns = res
        images.append(img_info)
        for a in anns: a["id"] = ann_id; all_anns.append(a); ann_id += 1

    coco = {"info": {"description": "Synthetic Dataset", "date_created": datetime.now().strftime("%Y-%m-%d")}, "categories": categories, "images": images, "annotations": all_anns}
    with open(output_json, "w", encoding="utf-8") as f: json.dump(coco, f, indent=2, ensure_ascii=False)
    print(f"\n✅ 完成！生成 {ann_id - 1} 個標註 → {output_json}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("dataset_dir", type=str)
    parser.add_argument("--min-area", type=int, default=50)
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()
    generate_coco(args.dataset_dir, args.min_area, args.workers)