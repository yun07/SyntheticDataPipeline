#!/usr/bin/env python3
import sys
import time
import subprocess
import psutil

# ==============================================================================
# ⚙️ 系統檢查設定檔 (CONFIGURATIONS) - 請在此修改門檻
# ==============================================================================
# 1. 採樣設定
SAMPLE_COUNT = 3       # 採樣次數 (例如連續測 3 次)
SAMPLE_INTERVAL = 1    # 每次採樣間隔 (秒)

# 2. 門檻上限 (低於此數值才算 PASS)
MAX_CPU_USAGE_PCT = 30.0  # CPU 使用率上限 (%)
MAX_GPU_USAGE_PCT = 30.0  # GPU 使用率上限 (%)

# 3. 資源安全下限 (高於此數值才算 PASS)
MIN_RAM_AVAIL_GB = 4.0    # 最小可用系統記憶體 (GB)
MIN_DISK_FREE_GB = 10.0   # 最小硬碟剩餘空間 (GB)
DISK_CHECK_PATH = "/"     # 檢查的硬碟掛載點 (Windows 可改為 'C:\\')

# 4. Debug 輸出控制
VERBOSE = True            # 是否印出詳細檢測數值
# ==============================================================================


def get_gpu_usage():
    """使用 nvidia-smi 獲取 GPU 平均使用率 (%)"""
    try:
        result = subprocess.run(
            ['nvidia-smi', '--query-gpu=utilization.gpu', '--format=csv,noheader,nounits'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True
        )
        lines = result.stdout.strip().split('\n')
        gpu_usages = [float(line.strip()) for line in lines if line.strip()]
        if gpu_usages:
            return max(gpu_usages)  # 若有多張 GPU，取最高使用率的那張
    except (FileNotFoundError, subprocess.CalledProcessError, ValueError):
        pass
    return None  # 代表無 NVIDIA GPU 或無法取得數據


def check_system_resources():
    if VERBOSE:
        print(f"🔍 開始系統資源監測 (採樣 {SAMPLE_COUNT} 次，每秒 1 次)...")

    # 1. 靜態檢查：Disk 空間 (無需採樣)
    disk_info = psutil.disk_usage(DISK_CHECK_PATH)
    disk_free_gb = disk_info.free / (1024 ** 3)
    if disk_free_gb < MIN_DISK_FREE_GB:
        if VERBOSE:
            print(f"❌ FAIL: 硬碟空間不足! 剩餘: {disk_free_gb:.2f} GB (需求 >= {MIN_DISK_FREE_GB} GB)")
        return False

    # 2. 動態採樣：CPU, GPU, RAM
    cpu_samples = []
    gpu_samples = []
    ram_samples = []

    # 第一次調用 cpu_percent 會初始化，需稍等
    psutil.cpu_percent(interval=None)

    for i in range(SAMPLE_COUNT):
        time.sleep(SAMPLE_INTERVAL)
        
        # 採樣 CPU
        cpu_samples.append(psutil.cpu_percent(interval=None))
        
        # 採樣 Available RAM (GB)
        ram_avail_gb = psutil.virtual_memory().available / (1024 ** 3)
        ram_samples.append(ram_avail_gb)
        
        # 採樣 GPU
        gpu_val = get_gpu_usage()
        if gpu_val is not None:
            gpu_samples.append(gpu_val)

    # 計算採樣平均值
    avg_cpu = sum(cpu_samples) / len(cpu_samples)
    avg_ram_avail = sum(ram_samples) / len(ram_samples)
    avg_gpu = (sum(gpu_samples) / len(gpu_samples)) if gpu_samples else None

    if VERBOSE:
        print(f"📊 檢測結果 (平均值):")
        print(f"   • CPU Usage:     {avg_cpu:.1f}% (門檻: < {MAX_CPU_USAGE_PCT}%)")
        print(f"   • Available RAM: {avg_ram_avail:.2f} GB (門檻: > {MIN_RAM_AVAIL_GB} GB)")
        print(f"   • Disk Free:     {disk_free_gb:.2f} GB (門檻: > {MIN_DISK_FREE_GB} GB)")
        if avg_gpu is not None:
            print(f"   • GPU Usage:     {avg_gpu:.1f}% (門檻: < {MAX_GPU_USAGE_PCT}%)")
        else:
            print(f"   • GPU Usage:     未檢測到 N卡 或 nvidia-smi")

    # 3. 邏輯判斷
    if avg_cpu >= MAX_CPU_USAGE_PCT:
        if VERBOSE: print("❌ FAIL: CPU 使用率過高")
        return False

    if avg_ram_avail < MIN_RAM_AVAIL_GB:
        if VERBOSE: print("❌ FAIL: 可用 RAM 不足")
        return False

    if avg_gpu is not None and avg_gpu >= MAX_GPU_USAGE_PCT:
        if VERBOSE: print("❌ FAIL: GPU 使用率過高")
        return False

    if VERBOSE:
        print("✅ PASS: 系統資源充足，可以執行下游 Script！")
    return True


if __name__ == "__main__":
    is_safe = check_system_resources()
    
    # 遵從 Linux Return Code 慣例：
    # 0 = Success (可以執行下游 Script)
    # 1 = Error/Fail (資源不符合條件)
    if is_safe:
        sys.exit(0)
    else:
        sys.exit(1)