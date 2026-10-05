import argparse
import json
import os
from pathlib import Path
import shutil
import warnings
from PIL import Image
import torch
from torch.utils.data import Dataset
import transformers
from transformers import (
    SegformerForSemanticSegmentation,
    SegformerImageProcessor,
    Trainer,
    TrainingArguments,
)

# 徹底靜音所有 Warning 同 Log
warnings.filterwarnings("ignore")
os.environ["TRANSFORMERS_VERBOSITY"] = "error"
transformers.utils.logging.set_verbosity_error()
transformers.utils.logging.disable_progress_bar()


# ─────────────────────────────────────────
# 1. DATASET & METRIC (極速資料集與指標)
# ─────────────────────────────────────────


class SyntheticDataset(Dataset):
    def __init__(self, rgb_paths: list[Path], stencil_dir: Path, processor: SegformerImageProcessor):
        self.samples = []
        # 直接在 初始化階段 一次性讀入 RAM
        for rf in rgb_paths:
            sf = stencil_dir / f"{rf.stem.replace('rgb_', 'stencil_')}.png"
            enc = processor(
                images=Image.open(rf).convert("RGB"),
                segmentation_maps=Image.open(sf).convert("L"),
                return_tensors="pt",
            )
            self.samples.append({k: v.squeeze(0) for k, v in enc.items()})

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx: int):
        return self.samples[idx]  # 直接從記憶體傳回，0毫秒 I/O 延遲


def compute_metrics(eval_pred, num_classes: int) -> dict:
    logits, labels = eval_pred[0] if isinstance(eval_pred, tuple) else eval_pred
    preds = torch.nn.functional.interpolate(
        torch.from_numpy(logits),
        size=labels.shape[-2:],
        mode="bilinear",
        align_corners=False,
    ).argmax(1)

    labels_t, preds_t = torch.from_numpy(labels), preds
    mask = labels_t != 255
    bins = num_classes * labels_t[mask] + preds_t[mask]
    cm = torch.bincount(bins, minlength=num_classes**2).reshape(num_classes, num_classes)

    intersection = torch.diag(cm)
    union = cm.sum(0) + cm.sum(1) - intersection
    iou = torch.where(union > 0, intersection.float() / union.float(), torch.tensor(float("nan")))
    return {"miou": torch.nanmean(iou).item()}


# ─────────────────────────────────────────
# 2. CONFIG, FACTORIES & UTILS (模組化隔離)
# ─────────────────────────────────────────


def parse_cli_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Segformer Pipeline")
    parser.add_argument("dataset_dir", type=Path, help="資料集目錄")
    parser.add_argument("--epochs", type=int, default=20)
    parser.add_argument("--batch_size", type=int, default=16)
    parser.add_argument("--lr", type=float, default=6e-5)
    parser.add_argument("--img_size", type=int, default=512)
    return parser.parse_args()


def load_label_mapping(dataset_dir: Path) -> tuple[dict, dict]:
    class_json_path = dataset_dir / "Class.json"
    if not class_json_path.exists():
        raise FileNotFoundError(f"找不到類別定義檔: {class_json_path}")

    with open(class_json_path, "r", encoding="utf-8") as f:
        class_data = json.load(f)

    id2label = {0: "background", **{i["id"]: i["class"].lower() for i in class_data}}
    label2id = {v: k for k, v in id2label.items()}
    return id2label, label2id


def create_datasets(dataset_dir: Path, img_size: int):
    """資料集工廠：負責掃描檔案與 Train/Val 自動切割"""
    rgb_dir = dataset_dir / "rgb"
    stencil_dir = dataset_dir / "stencil"
    rgb_files = sorted([f for f in rgb_dir.iterdir() if f.suffix.lower() in (".jpg", ".jpeg", ".png")])

    val_size = 10 if len(rgb_files) > 10 else 1
    train_files = rgb_files[:-val_size]
    val_files = rgb_files[-val_size:]

    processor = SegformerImageProcessor(
        do_resize=True,
        size={"height": img_size, "width": img_size},
        do_normalize=True,
    )
    
    train_ds = SyntheticDataset(train_files, stencil_dir, processor)
    val_ds = SyntheticDataset(val_files, stencil_dir, processor)
    return train_ds, val_ds, processor


def build_model(num_classes: int, id2label: dict, label2id: dict) -> SegformerForSemanticSegmentation:
    return SegformerForSemanticSegmentation.from_pretrained(
        "nvidia/mit-b1",
        num_labels=num_classes,
        id2label=id2label,
        label2id=label2id,
        ignore_mismatched_sizes=True,
        use_safetensors=True,
    )


def build_training_args(output_dir: Path, args: argparse.Namespace) -> TrainingArguments:
    return TrainingArguments(
        output_dir=str(output_dir),
        learning_rate=args.lr,
        num_train_epochs=args.epochs,
        per_device_train_batch_size=args.batch_size,
        per_device_eval_batch_size=1,
        eval_strategy="epoch",
        save_strategy="epoch",
        save_total_limit=1,
        metric_for_best_model="miou",
        greater_is_better=True,
        load_best_model_at_end=True,
        logging_steps=5,
        remove_unused_columns=False,
        dataloader_num_workers=0,  # 小資料量務必設為 0，避免進程切換開銷
        fp16=False,                # 數據極小時關閉 FP16 避免 Scale 計算開銷
        disable_tqdm=True,
    )


def purge_intermediate_checkpoints(runs_dir: Path):
    """【動態清理】刪除 runs 旗下所有 checkpoint-* 資料夾，無視具體數字"""
    for ckpt in runs_dir.glob("checkpoint-*"):
        if ckpt.is_dir():
            shutil.rmtree(ckpt, ignore_errors=True)


def export_summary(
    runs_dir: Path,
    best_dir: Path,
    num_classes: int,
    id2label: dict,
    train_res,
    eval_res,
):
    summary = {
        "status": "success",
        "num_classes": num_classes,
        "id2label": id2label,
        "best_model_dir": str(best_dir),
        "metrics": {
            "best_eval_miou": round(eval_res.get("eval_miou", 0.0), 4),
            "eval_loss": round(eval_res.get("eval_loss", 0.0), 4),
            "train_loss": round(train_res.training_loss, 4),
            "train_runtime_sec": round(train_res.metrics.get("train_runtime", 0.0), 2),
        },
    }

    with open(runs_dir / "summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print(json.dumps(summary, indent=2))


# ─────────────────────────────────────────
# 3. MAIN PIPELINE (極簡高階流程)
# ─────────────────────────────────────────


def main():
    args = parse_cli_args()

    # 1. 配置與數據準備
    id2label, label2id = load_label_mapping(args.dataset_dir)
    runs_dir, best_dir = args.dataset_dir / "runs", args.dataset_dir / "runs" / "best_model"
    train_ds, val_ds, processor = create_datasets(args.dataset_dir, args.img_size)

    # 2. 模型與訓練器建構
    model = build_model(len(id2label), id2label, label2id)
    trainer = Trainer(
        model=model,
        args=build_training_args(runs_dir, args),
        train_dataset=train_ds,
        eval_dataset=val_ds,
        compute_metrics=lambda ep: compute_metrics(ep, len(id2label)),
    )

    # 3. 執行訓練與評估
    train_res = trainer.train()
    eval_res = trainer.evaluate()

    # 4. 匯出模型與清理中間資料夾
    trainer.save_model(str(best_dir))
    processor.save_pretrained(str(best_dir))
    purge_intermediate_checkpoints(runs_dir)

    # 5. 輸出報告
    export_summary(runs_dir, best_dir, len(id2label), id2label, train_res, eval_res)


if __name__ == "__main__":
    main()