#!/usr/bin/env python3
import sys
import time
import glob
import os
import subprocess
from pathlib import Path
import psutil

# ==============================================================================
# ⚙️ CONFIGURATIONS
# ==============================================================================
POLL_INTERVAL = 10  # Polling interval (seconds)
VERBOSE = True      # Enable detailed logging
PYTHON_EXE = sys.executable  # Current Python executable

# 🎯 Get the absolute path of the directory containing orchestra.py
BASE_SCRIPT_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = BASE_SCRIPT_DIR  

# 🔒 Define heavy tasks (scripts that require a process lock)
HEAVY_SCRIPTS = ["rpm.py", "segformer_run.py", "segformer_finetune.py"]
# ==============================================================================


def log(message: str):
    """Format and print log messages"""
    if VERBOSE:
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] [Orchestrator] {message}")


def get_script_path(script_name: str) -> str:
    """Get the absolute path of a target script"""
    return str(SCRIPTS_DIR / script_name)


def is_locked() -> bool:
    """
    Dynamic lock check:
    Scans system processes. Returns True if rpm.py or segformer scripts are running.
    """
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            cmdline = proc.info.get('cmdline')
            if cmdline and len(cmdline) > 1:
                for script in HEAVY_SCRIPTS:
                    if any(script in arg for arg in cmdline):
                        return True
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
    return False


def run_cmd_sync(cmd: list) -> tuple[int, str]:
    """[Blocking] Execute command synchronously, wait for completion, and return output"""
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"

    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=env
        )
        if result.returncode != 0 and VERBOSE:
            log(f"⚠️ Command error (Code {result.returncode}): {' '.join(cmd)}")
            if result.stderr:
                log(f"   [Error Detail]: {result.stderr.strip()}")

        return result.returncode, result.stdout.strip()
    except Exception as e:
        log(f"❌ [Sync execution failed] {' '.join(cmd)}: {e}")
        return -1, ""


def run_cmd_async(cmd: list):
    """[Non-blocking] Launch command directly attached to current terminal output"""
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUNBUFFERED"] = "1"  # 🔥 Force unbuffered output

    try:
        subprocess.Popen(
            cmd,
            stdout=None,  # Inherit console output directly
            stderr=None,  # Progress bars (e.g., tqdm) go to stderr, print directly
            env=env
        )
        log(f"🚀 [Async process started]: {' '.join(cmd)}")
    except Exception as e:
        log(f"❌ [Async launch failed] {' '.join(cmd)}: {e}")


def get_cursor(job_dir: str) -> int:
    """[Blocking] Invoke status_check.py to retrieve cursor position"""
    code, output = run_cmd_sync([PYTHON_EXE, "-u", get_script_path("status_check.py"), job_dir])
    if code == 0:
        try:
            return int(output)
        except ValueError:
            return -1
    return -1


def process_job(yaml_path: str, root_dir: str):
    """Process a single .yaml Job pipeline"""
    yaml_file = Path(yaml_path)
    job_name = yaml_file.stem
    job_dir = os.path.join(root_dir, job_name)

    # --------------------------------------------------------------------------
    # Step 1: Check generation_complete.json
    # --------------------------------------------------------------------------
    gen_complete_flag = os.path.join(job_dir, "generation_complete.json")
    if not os.path.exists(gen_complete_flag):
        log(f"▶️ [Blocking] Running generate_samples.py ({job_name})")
        run_cmd_sync([PYTHON_EXE, "-u", get_script_path("generate_samples.py"), yaml_path])
    #else:
        #log(f"⏩ [SKIP] generation_complete.json already exists for {job_name}")

    # --------------------------------------------------------------------------
    # Step 2: Check render_complete.json
    # --------------------------------------------------------------------------
    render_complete_flag = os.path.join(job_dir, "render_complete.json")
    if not os.path.exists(render_complete_flag):
        cursor = get_cursor(job_dir)
        #log(f"📌 {job_name} current cursor: {cursor}")

        if cursor != -1:
            if not is_locked():
                sample_file = os.path.join(job_dir, "samples", f"sample_{cursor:06d}.json")
                log(f"⚡ [Async] No lock found, launching rpm.py ({sample_file})")
                run_cmd_async([PYTHON_EXE, "-u", get_script_path("rpm.py"), sample_file])
            #else:
                #log(f"🔒 [Locked] Heavy task running, skipping rpm.py ({job_name})")
            
            # Continue polling until rendering is finished
            return

    # --------------------------------------------------------------------------
    # Step 3: Check coco_annotations.json
    # --------------------------------------------------------------------------
    coco_flag = os.path.join(job_dir, "coco_annotations.json")
    if not os.path.exists(coco_flag):
        log(f"▶️ [Blocking] Running coco_generator.py ({job_name})")
        run_cmd_sync([PYTHON_EXE, "-u", get_script_path("coco_generator.py"), job_dir])
    #else:
        #log(f"⏩ [SKIP] coco_annotations.json already exists for {job_name}")

    # --------------------------------------------------------------------------
    # Step 4: Check summary.json & launch segformer_run.py (Async)
    # --------------------------------------------------------------------------
    summary_flag = os.path.join(job_dir, "runs", "summary.json")
    if not os.path.exists(summary_flag):
        segformer_script = "segformer_finetune.py" if os.path.exists(get_script_path("segformer_finetune.py")) else "segformer_run.py"
        
        if not is_locked():
            log(f"⚡ [Async] No lock and missing summary.json, launching {segformer_script} ({job_name})")
            run_cmd_async([PYTHON_EXE, "-u", get_script_path(segformer_script), job_dir])
        #else:
            #log(f"🔒 [Locked] Heavy task running, skipping {segformer_script} ({job_name})")
        
        # Return after launching (or skipping due to lock) to start next polling loop
        return

    # --------------------------------------------------------------------------
    # Step 5: Check visualisation_*.png & run segformer_visualise.py (Blocking)
    # --------------------------------------------------------------------------
    # Check for any visualisation_*.png files using wildcard globbing
    visual_images = glob.glob(os.path.join(job_dir, "visualisation_*.png"))
    
    if not visual_images:
        log(f"▶️ [Blocking] No visualization images found, running segformer_visualise.py ({job_name})")
        run_cmd_sync([PYTHON_EXE, "-u", get_script_path("segformer_visualise.py"), job_dir])
    #else:
        #log(f"⏩ [SKIP] Visualization images already exist for {job_name} ({len(visual_images)} files)")

    #log(f"✅ Job processing complete: {job_name}\n")


def main():
    if len(sys.argv) < 2:
        print("Usage: python orchestra.py <DIR>")
        sys.exit(1)

    target_dir = sys.argv[1]
    log(f"🎧 Orchestrator started, monitoring directory: {target_dir}")

    try:
        while True:
            yaml_files = sorted(glob.glob(os.path.join(target_dir, "*.yaml")))

            if yaml_files:
                for job_yaml in yaml_files:
                    process_job(job_yaml, target_dir)

            time.sleep(POLL_INTERVAL)

    except KeyboardInterrupt:
        log("🛑 Termination signal received. Orchestrator stopped.")
        sys.exit(0)


if __name__ == "__main__":
    main()