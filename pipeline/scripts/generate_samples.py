from __future__ import annotations

import argparse, itertools, json, math, random, yaml
from datetime import datetime, timezone
from pathlib import Path
from scipy.stats import qmc

# ==============================================================================
# Global Configuration / Constants
# ==============================================================================
CONFIG = {
    "dir_samples": "samples",
    "file_marker": "generation_complete.json",
    "file_sample_prefix": "sample_",
    "sample_id_digits": 6,
    "encoding": "utf-8",
}


def _map_unit(v, u: float):
    u = min(max(float(u), 0.0), 0.9999999999999999)
    if v is bool:
        return u >= 0.5
    if isinstance(v, (list, tuple)) and len(v) == 2:
        lo, hi = v
        if isinstance(lo, int) and isinstance(hi, int) and not isinstance(lo, bool) and not isinstance(hi, bool):
            return lo + min(math.floor(u * (hi - lo + 1)), hi - lo)
        if isinstance(lo, (int, float)) and isinstance(hi, (int, float)):
            return lo + u * (hi - lo)
    vals = list(v)
    return vals[min(math.floor(u * len(vals)), len(vals) - 1)]


def _expand_grid(v):
    if v is bool:
        return [False, True]
    if (
        isinstance(v, (list, tuple))
        and len(v) == 2
        and isinstance(v[0], int)
        and isinstance(v[1], int)
        and not isinstance(v[0], bool)
        and not isinstance(v[1], bool)
    ):
        return list(range(v[0], v[1] + 1))
    return list(v)


def generate_from_yaml(job_yaml_path: str | Path):
    job_path = Path(job_yaml_path).resolve()
    if not job_path.exists():
        raise FileNotFoundError(f"Job YAML not found: {job_path}")

    job = yaml.safe_load(job_path.read_text(encoding=CONFIG["encoding"]))
    cfg = job["sampling"]
    method, params = cfg.get("method", "grid").lower(), cfg["parameters"]
    count, limit, seed = cfg.get("count"), cfg.get("limit"), cfg.get("seed", 0)
    fixed = job.get("fixed_parameters", {})

    # 1. 取得 HDA 路徑 (支援 hda_path 或 hda 欄位) 並做防呆檢查
    hda_raw = job.get("hda_path") or job.get("hda")
    hda_resolved_str = None
    if hda_raw:
        hda_p = Path(hda_raw)
        if not hda_p.is_absolute():
            hda_p = (job_path.parent / hda_p).resolve()
        if not hda_p.exists():
            raise FileNotFoundError(f"Specified HDA file not found: {hda_p}")
        hda_resolved_str = str(hda_p)

    # 2. 自動推導目錄：直接在 YAML 檔所在目錄下，以 YAML 檔名 (去除末尾空格) 建立資料夾
    dataset_name = job_path.stem.strip()
    out_dir = job_path.parent / dataset_name
    samples_dir = out_dir / CONFIG["dir_samples"]
    samples_dir.mkdir(parents=True, exist_ok=True)

    # 3. 清除舊 completion marker 與舊 samples
    marker = out_dir / CONFIG["file_marker"]
    if marker.exists():
        marker.unlink()

    sample_pattern = f"{CONFIG['file_sample_prefix']}*.json"
    for old_sample in samples_dir.glob(sample_pattern):
        old_sample.unlink()

    # 4. 構建 Sampler
    if method == "grid":
        names = [p["name"] for p in params]
        gen = (
            (i, dict(zip(names, c)))
            for i, c in enumerate(itertools.product(*[_expand_grid(p["range"]) for p in params]))
            if limit is None or i < limit
        )
    elif method in {"random", "lhs", "sobol"}:
        if count is None:
            raise ValueError(f"'{method}' requires 'count'")
        d = len(params)
        if method == "random":
            rng = random.Random(seed)
            mat = [[rng.random() for _ in range(d)] for _ in range(count)]
        elif method == "lhs":
            mat = qmc.LatinHypercube(d=d, seed=seed).random(n=count)
        else:
            mat = qmc.Sobol(d=d, scramble=True, seed=seed).random(n=count)

        gen = (
            (i, {p["name"]: _map_unit(p["range"], row[idx]) for idx, p in enumerate(params)})
            for i, row in enumerate(mat)
        )
    else:
        raise ValueError(f"Unsupported sampling method: {method}")

    # 5. 寫入 Samples
    digits = CONFIG["sample_id_digits"]
    prefix = CONFIG["file_sample_prefix"]
    written = 0

    for sid, sparam in gen:
        sample_filename = f"{prefix}{sid:0{digits}d}.json"
        (samples_dir / sample_filename).write_text(
            json.dumps({"sample_id": sid, "parameters": {**fixed, **sparam}}, indent=4),
            encoding=CONFIG["encoding"],
        )
        written += 1

    # 6. 寫入 Completion Marker (包含 metadata、HDA 路徑與時間戳記)
    marker_data = {
        "dataset_name": dataset_name,
        "status": "complete",
        "sample_count": written,
        "method": method,
        "hda_path": hda_resolved_str,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    
    marker.write_text(
        json.dumps(marker_data, indent=4),
        encoding=CONFIG["encoding"],
    )

    print(f"[Sampling] {method.upper()} generated {written} samples -> {out_dir}")
    return {
        "output_dir": str(out_dir),
        "samples_dir": str(samples_dir),
        "completion_file": str(marker),
        "sample_count": written,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate synthetic dataset sample JSON files.")
    parser.add_argument("job_file", help="Path to job.yaml")
    generate_from_yaml(parser.parse_args().job_file)