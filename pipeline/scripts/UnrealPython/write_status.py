import sys
import json
import os
from datetime import datetime, timezone

def update_status(filepath: str, **kwargs) -> dict:
    """
    作為 Module 呼叫的主函數
    :param filepath: JSON 檔案路徑
    :param kwargs: 任意 key=value 鍵值對 (例如 state="rendering", frame=50)
    :return: 寫入的字典資料
    """
    # 1. 建立基礎資料 (預設 UTC 時間與 PID)
    data = {
        "started_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "pid": os.getpid()
    }

    # 2. 合併傳入的任意參數 (kwargs)
    data.update(kwargs)

    # 3. 寫入 JSON 檔案
    abs_path = os.path.abspath(filepath)
    os.makedirs(os.path.dirname(abs_path), exist_ok=True)
    
    with open(abs_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

    print(f"[OK] Written to {abs_path}")
    return data


# ---------------------------------------------------------
# CLI 入口：只有當此檔案被直接執行時才會跑這裡
# ---------------------------------------------------------
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python write_status.py <filepath> [key=value ...]")
        sys.exit(1)

    target_file = sys.argv[1]
    extra_args = {}

    # 解析命令列傳入的 key=value 參數
    for arg in sys.argv[2:]:
        if "=" in arg:
            k, v = arg.split("=", 1)
            # 自動將純數字轉為 int
            extra_args[k] = int(v) if v.isdigit() else v

    # 呼叫上面的主函數
    update_status(target_file, **extra_args)