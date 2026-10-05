import os
import sys
import time
import ctypes
import threading
import subprocess
from pathlib import Path
from ctypes import wintypes
import yaml

# ============================================================
# CONFIG & PATHS (Global Unified Configuration)
# ============================================================
SCRIPT_DIR = Path(__file__).resolve().parent
ENV_YAML_PATH = SCRIPT_DIR / "env.yaml"
EXAMPLE_YAML_PATH = SCRIPT_DIR / "env.example.yaml"

def load_yaml(path: Path) -> dict:
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            print(f"[RPM] Warning: Failed to parse {path.name}: {e}")
    return {}

yaml_config = load_yaml(ENV_YAML_PATH)
example_config = load_yaml(EXAMPLE_YAML_PATH)

def get_config_val(key: str, default=None):
    return os.getenv(key, yaml_config.get(key, example_config.get(key, default)))

raw_engine = get_config_val("UE_ENGINE_PATH")
raw_project = get_config_val("UE_PROJECT_PATH")

if not raw_engine or not raw_project:
    print("[RPM] Critical Error: UE_ENGINE_PATH or UE_PROJECT_PATH is not configured in env.yaml or env.example.yaml!")
    sys.exit(1)

ENGINE_EXECUTABLE = str(Path(raw_engine).resolve())
PROJECT_PATH = str(Path(raw_project).resolve())

UE_BRIDGE_SCRIPT = str((SCRIPT_DIR / "UE_BRIDGE.PY").resolve())
LOG_FREEZE_TIMEOUT = int(get_config_val("LOG_FREEZE_TIMEOUT", 180))

# ============================================================
# Windows API / Job Object Declarations
# ============================================================
kernel32 = ctypes.windll.kernel32
user32 = ctypes.windll.user32

JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x2000
JobObjectExtendedLimitInformation = 9
SEM_FAILCRITICALERRORS = 0x0001
SEM_NOGPFAULTERRORBOX = 0x0002

class JOBOBJECT_BASIC_LIMIT_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("PerProcessUserTimeLimit", wintypes.LARGE_INTEGER),
        ("PerJobUserTimeLimit", wintypes.LARGE_INTEGER),
        ("LimitFlags", wintypes.DWORD),
        ("MinimumWorkingSetSize", ctypes.c_size_t),
        ("MaximumWorkingSetSize", ctypes.c_size_t),
        ("ActiveProcessLimit", wintypes.DWORD),
        ("Affinity", ctypes.c_size_t),
        ("PriorityClass", wintypes.DWORD),
        ("SchedulingClass", wintypes.DWORD),
    ]

class IO_COUNTERS(ctypes.Structure):
    _fields_ = [
        ("ReadOperationCount", wintypes.ULARGE_INTEGER),
        ("WriteOperationCount", wintypes.ULARGE_INTEGER),
        ("OtherOperationCount", wintypes.ULARGE_INTEGER),
        ("ReadTransferCount", wintypes.ULARGE_INTEGER),
        ("WriteTransferCount", wintypes.ULARGE_INTEGER),
        ("OtherTransferCount", wintypes.ULARGE_INTEGER),
    ]

class JOBOBJECT_EXTENDED_LIMIT_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("BasicLimitInformation", JOBOBJECT_BASIC_LIMIT_INFORMATION),
        ("IoInfo", IO_COUNTERS),
        ("ProcessMemoryLimit", ctypes.c_size_t),
        ("JobMemoryLimit", ctypes.c_size_t),
        ("PeakProcessMemoryUsed", ctypes.c_size_t),
        ("PeakJobMemoryUsed", ctypes.c_size_t),
    ]

def setup_job_object():
    """ Create a Windows Job Object to auto-kill child processes (HARS, UE, etc.) when rpm.py exits """
    h_job = kernel32.CreateJobObjectW(None, None)
    if h_job:
        info = JOBOBJECT_EXTENDED_LIMIT_INFORMATION()
        info.BasicLimitInformation.LimitFlags = JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        kernel32.SetInformationJobObject(
            h_job,
            JobObjectExtendedLimitInformation,
            ctypes.byref(info),
            ctypes.sizeof(info)
        )
    return h_job

def assign_process_to_job(h_job, process_handle):
    if h_job and process_handle:
        kernel32.AssignProcessToJobObject(h_job, process_handle)

# ============================================================
# HEALTH CHECK 1: Prevent Duplicate Instances
# ============================================================
def check_already_running(project_path_str):
    """ Check if an UnrealEditor-Cmd.exe process is already running for this project """
    try:
        cmd = 'powershell "Get-CimInstance Win32_Process -Filter \\"name=\'UnrealEditor-Cmd.exe\'\\" | Select-Object -ExpandProperty CommandLine"'
        output = subprocess.check_output(cmd, shell=True, text=True, stderr=subprocess.DEVNULL)
        
        proj_name = Path(project_path_str).name.lower()
        for line in output.splitlines():
            if proj_name in line.lower():
                return True
    except Exception:
        pass
    return False

# ============================================================
# OPTIMIZATION: Background Pop-up Killer Thread
# ============================================================
def window_killer_worker():
    WM_CLOSE = 0x0010
    WM_KEYDOWN = 0x0100
    VK_RETURN = 0x0D

    while True:
        hwnd = user32.FindWindowW(None, "Houdini Error")
        if hwnd:
            user32.PostMessageW(hwnd, WM_KEYDOWN, VK_RETURN, 0)
            user32.PostMessageW(hwnd, WM_CLOSE, 0, 0)
            print("[RPM] Successfully intercepted and closed HARS crash pop-up!")
        time.sleep(0.5)

# ============================================================
# MAIN EXECUTION
# ============================================================
def main():
    # 0. Parse CLI JSON argument and write to environment variables
    env = os.environ.copy()
    if len(sys.argv) > 1:
        json_path = str(Path(sys.argv[1]).resolve())
        env["RENDER_JSON_PATH"] = json_path
        print(f"[RPM] Wrote JSON config path to environment variable: {json_path}")
    else:
        print("[RPM] Info: No JSON argument passed.")

    # 1. Health Check: Prevent duplicate processes
    print("[RPM] Running Health Check: Checking for existing project processes...")
    if check_already_running(PROJECT_PATH):
        print(f"[RPM] Error: UnrealEditor-Cmd is already running for project [{Path(PROJECT_PATH).name}]! Aborting to prevent resource conflicts.")
        sys.exit(1)

    # 2. Setup Job Object and system-level Error Mode
    h_job = setup_job_object()
    kernel32.SetErrorMode(SEM_FAILCRITICALERRORS | SEM_NOGPFAULTERRORBOX)

    # 3. Start background Window Killer Thread
    killer_thread = threading.Thread(target=window_killer_worker, daemon=True)
    killer_thread.start()

    # 4. Configure environment variables (Silent Mode)
    env["HOUDINI_ERROR_MODE"] = "0"
    env["HARS_SILENT_CRASH"] = "1"
    env["HOUDINI_SETERRORMODE"] = "1"
    env["HOUDINI_DISABLE_CRASH_RPT"] = "1"
    env["HENGINE_SILENT_MODE"] = "1"
    env["HAPI_ENABLE_CRASH_HANDLER"] = "0"
    env["UE_LOG_STDOUT"] = "1"

    # 5. Assemble command line string
    cmd_str = f'"{ENGINE_EXECUTABLE}" "{PROJECT_PATH}" -Unattended -NoSplash -NoSound -ExecutePythonScript="{UE_BRIDGE_SCRIPT}"'

    print(f"[RPM] Executing Command: {cmd_str}")
    print("[RPM] Launching automated render task (Headless / Silent Mode)...")
    
    # Launch subprocess
    process = subprocess.Popen(cmd_str, env=env, shell=True)
    
    if h_job:
        PROCESS_ALL_ACCESS = 0x1F0FFF
        p_handle = kernel32.OpenProcess(PROCESS_ALL_ACCESS, False, process.pid)
        if p_handle:
            assign_process_to_job(h_job, p_handle)
            kernel32.CloseHandle(p_handle)

    # 6. Compute UE Project Log path (for Freeze monitoring)
    project_dir = Path(PROJECT_PATH).parent
    project_name = Path(PROJECT_PATH).stem
    log_file_path = project_dir / "Saved" / "Logs" / f"{project_name}.log"

    # 7. HEALTH CHECK 2: Background Log Monitor (Detect Freeze / Deadlocks)
    last_log_mtime = None
    stalled_start_time = None

    try:
        while process.poll() is None:
            time.sleep(5)
            
            if log_file_path.exists():
                current_mtime = os.path.getmtime(log_file_path)
                
                if last_log_mtime is None or current_mtime > last_log_mtime:
                    last_log_mtime = current_mtime
                    stalled_start_time = None
                else:
                    if stalled_start_time is None:
                        stalled_start_time = time.time()
                    else:
                        stuck_duration = time.time() - stalled_start_time
                        if stuck_duration > LOG_FREEZE_TIMEOUT:
                            print(f"\n[RPM] Warning: UE Log has been inactive for over {LOG_FREEZE_TIMEOUT} seconds! Freeze/Deadlock detected.")
                            print("[RPM] Force terminating UE and all child processes...")
                            process.kill()
                            break

        return_code = process.poll()
        if return_code == 0:
            print("[RPM] Render task completed successfully!")
        else:
            print(f"[RPM] Render process finished or interrupted with Exit Code: {return_code}")

    except KeyboardInterrupt:
        print("\n[RPM] User interrupt received. Cleaning up and terminating all child processes...")
        process.kill()

if __name__ == "__main__":
    main()