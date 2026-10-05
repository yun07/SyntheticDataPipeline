import json
import sys
from pathlib import Path


def generate_class_json(output_path: str, classes_str: str):
    # 1. 解析並清理逗號分隔字串
    raw_classes = [c.strip() for c in classes_str.split(",") if c.strip()]
    if not raw_classes:
        sys.exit("錯誤：請提供有效的類別名稱。")

    # 3. 檢查重複類別
    if len(raw_classes) != len(set(raw_classes)):
        duplicates = set(c for c in raw_classes if raw_classes.count(c) > 1)
        sys.exit(f"錯誤：發現重複的類別名稱 {list(duplicates)}")

    # 2. 生成資料 (從 1 開始遞增)
    data = [{"class": cls, "id": i} for i, cls in enumerate(raw_classes, start=1)]

    # 4. 修改後的路徑邏輯：判斷是資料夾還是檔案
    path = Path(output_path)
    if path.suffix.lower() == ".json":
        target_file = path
    elif path.suffix == "":  # 沒有副檔名 -> 視為資料夾，自動補 /class.json
        target_file = path / "class.json"
    else:  # 有其他副檔名 (如 .txt) -> 強制改成 .json
        target_file = path.with_suffix(".json")

    # 自動建立目錄
    target_file.parent.mkdir(parents=True, exist_ok=True)

    # 寫入 JSON
    with open(target_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

    print(f"成功生成 JSON 檔案：{target_file}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit("用法：python class_json.py <output_path> <classes_string>")

    generate_class_json(sys.argv[1], sys.argv[2])