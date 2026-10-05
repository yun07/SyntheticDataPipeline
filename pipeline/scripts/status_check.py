import json
from pathlib import Path

def batch_state(dir_path: str) -> int:
    base_dir = Path(dir_path).absolute()
    status_dir = base_dir / "status"
    samples_dir = status_dir / "samples"
    
    render_complete_file = base_dir / "render_complete.json"
    gen_complete_file = base_dir / "generation_complete.json"

    # Feature: Early Exit - 如果已完成，直接返回 -1 並退出
    if render_complete_file.exists():
        return -1

    # 1. 讀取 generation_complete.json 取得 sample_count
    if not gen_complete_file.exists():
        raise FileNotFoundError(f"Missing config: {gen_complete_file}")
        
    with open(gen_complete_file, "r", encoding="utf-8") as f:
        gen_data = json.load(f)
        sample_count = gen_data.get("sample_count", 0)

    # 2. 尋找最大的 Batch_XXXXXX.done 取得起始 cursor
    cursor = 0
    if status_dir.exists():
        batch_files = list(status_dir.glob("Batch_*.done"))
        for bf in batch_files:
            # 提取 Batch_XXXXXX.done 中的數字部分
            num_str = bf.stem.split("_")[-1]
            if num_str.isdigit():
                val = int(num_str)
                if val > cursor:
                    cursor = val

    # 3. 檢查並推進批次
    while cursor < sample_count:
        target_end = min(cursor + 100, sample_count)
        all_samples_ready = True

        for i in range(cursor, target_end):
            pattern = f"*_{i:06d}.done"
            # 檢查是否有符合 *_{i:06d}.done 的檔案
            if not any(samples_dir.glob(pattern)):
                all_samples_ready = False
                break

        if all_samples_ready:
            # 建立下一個 Batch 完成標記
            next_cursor = cursor + 100
            batch_done_file = status_dir / f"Batch_{next_cursor:06d}.done"
            status_dir.mkdir(parents=True, exist_ok=True)
            batch_done_file.touch(exist_ok=True)
            
            cursor = next_cursor
        else:
            # 當前批次未齊全，跳出迴圈
            break

    # 4. 最終狀態判定與 Return
    if cursor >= sample_count:
        # 建立渲染完成標記
        with open(render_complete_file, "w", encoding="utf-8") as f:
            json.dump({"status": "completed", "total_samples": sample_count}, f, indent=2)
        return -1

    return cursor

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        target_dir = sys.argv[1]
        result = batch_state(target_dir)
        print(result)