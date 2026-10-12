# Synthetic Data Pipeline

A controllable synthetic-environment and dataset-generation pipeline combining **Houdini, Unreal Engine and Python**.

The project generates procedural environments, renders synthetic imagery and semantic masks, exports dataset annotations, and supports downstream semantic-segmentation training and evaluation.

---

## Overview

```text
Houdini Procedural Generation
            ↓
       Houdini Engine
            ↓
       Unreal Engine
            ↓
      Automated Render
            ↓
    RGB + Semantic Mask
            ↓
        COCO Dataset
            ↓
     SegFormer Training
            ↓
        Evaluation
```

### Problem

Specialised edge cases often require purpose-built procedural generators. However, generating a scenario is only one part of the workflow: automated rendering, semantic annotation, dataset export, and downstream model evaluation also need to be connected. Rebuilding these components for each new generator can duplicate engineering effort and require expertise across multiple disciplines.

### Approach

Designed an automated synthetic data pipeline that separates scenario generation from downstream data production. Developers can build specialised Houdini Digital Assets (HDAs) for configurable scenarios, while a shared pipeline connects Houdini Engine with Unreal Engine for automated rendering and dataset export.
A procedural intersection generator serves as the reference implementation, demonstrating controllable road-junction geometry and variation for targeted scenario generation.

### Technical Highlights

Procedural scenario generation: Configurable intersection geometry and parameters for generating varied road-junction layouts.

Automated data production: Integrated Houdini Engine and Unreal Engine for batch rendering and semantic dataset export, without an intermediate USD-file workflow.

Pipeline reliability: Implemented checkpoint-based recovery, lock-file coordination, and error handling for Houdini Engine failures during rendering.

Downstream ML validation: Connected generated data to a SegFormer semantic-segmentation training and evaluation workflow.

### Results

Best evaluation mIoU: 0.8745
Semantic classes: 8
Training images: ~300
Model: SegFormer nvidia/mit-b1

Demonstration task: Semantic segmentation

The results demonstrate an end-to-end workflow from procedural environment generation to downstream model training and evaluation. The project focuses on controllable scenario generation and data-pipeline integration, rather than claiming state-of-the-art model performance.

### Intended Value

The architecture is designed to make specialised scenario generators easier to connect to a shared data-production workflow, reducing the need to rebuild rendering and export infrastructure for every new scenario type.

---

## Repository Structure

```text
SyntheticDataPipeline/
│
├── HDA/
│   └── Houdini Digital Assets
│
├── pipeline/
│   └── scripts/
│       ├── orchestra.py
│       ├── generate_samples.py
│       ├── coco_generator.py
│       ├── segformer_finetune.py
│       ├── segformer_visualise.py
│       ├── json2jpg.py
│       ├── rpm.py
│       ├── ue_bridge.py
│       ├── check_resources.py
│       ├── status_check.py
│       └── UnrealPython/
│
├── UnrealProjects/
│   └── Unreal Engine project
│
├── datasets/
│   └── job_example_v001.yaml
│
├── PROJECT_STATUS.md
├── README.md
├── requirements.txt
└── .gitignore
```

---

## Pipeline

The main workflow is:

1. Define a dataset-generation job in YAML.
2. Generate parameterised samples from the configured ranges.
3. Feed the generated parameters into Unreal / Houdini Engine.
4. Generate procedural scenes.
5. Render RGB and semantic outputs.
6. Convert semantic masks into COCO-style annotations.
7. Train a SegFormer semantic-segmentation model.
8. Evaluate the model using mean Intersection over Union (mIoU).
9. Generate visual comparisons between RGB, ground truth and predictions.

The main orchestration entry point is:

```text
pipeline/scripts/orchestra.py
```

Individual scripts can also be executed independently where appropriate.

---

## Sampling

`generate_samples.py` supports several sampling strategies:

```text
grid
random
lhs
sobol
```

The sampling configuration is provided through YAML.

Example:

```text
datasets/job_example_v001.yaml
```

The generated dataset does **not** need to live inside the repository. The dataset/output location is derived from the supplied job configuration and can be provided from outside the repository.

---

## Unreal Engine Setup

Open the Unreal project and make sure the following plugins are enabled:

1. **Blueprint File Utilities**
2. **Json Blueprint Utilities**

### Editor Preferences

Go to:

**Edit → Editor Preferences**

Disable:

**Use Less CPU when in Background**

This setting is required for the intended automated pipeline workflow.

---

## Unreal Project

The Unreal project provides the rendering and semantic-data generation stage.

It uses:

* Scene Capture
* Movie Render Queue / automated rendering
* Custom Stencil / semantic rendering
* Procedural scene assembly
* Unreal Python automation

The project also contains the Unreal assets required by the example scene and capture workflow.

### External Assets

Some assets used by the project originate from external Unreal Marketplace downloads and are **not redistributed in this repository**.

The exact vehicle Static Mesh and Material configuration affects the semantic stencil output. When reproducing the example dataset, an equivalent compatible asset/material setup may therefore be required.

Third-party assets remain subject to their original licences.

---

## Houdini

The repository includes a Houdini Digital Asset:

```text
HDA/sop_IntersectGenerator.1.3.hda
```

The HDA generates controllable procedural intersection environments which are consumed by Unreal Engine through Houdini Engine.

The scene variation is driven by parameters such as road dimensions, intersection configuration and random seeds.

---

## Python Pipeline

The Python pipeline is divided into independently executable components:

| Script                   | Purpose                                      |
| ------------------------ | -------------------------------------------- |
| `orchestra.py`           | Main pipeline orchestration                  |
| `generate_samples.py`    | Parameter sampling and sample generation     |
| `ue_bridge.py`           | Unreal communication / pipeline bridge       |
| `rpm.py`                 | Unreal process and render-process management |
| `coco_generator.py`      | Semantic mask → COCO annotations             |
| `segformer_finetune.py`  | SegFormer training and evaluation            |
| `segformer_visualise.py` | Prediction / ground-truth visualisation      |
| `check_resources.py`     | Resource checks                              |
| `status_check.py`        | Pipeline status handling                     |
| `UnrealPython/`          | Unreal-side Python utilities                 |

The components are intentionally kept relatively independent so that individual stages can be tested or executed without requiring the entire pipeline.

---

## Python Environment

Python **3.10+** is recommended.

Install the direct Python dependencies with:

```powershell
pip install -r requirements.txt
```

### PyTorch / CUDA

PyTorch is intentionally not pinned to a specific version in `requirements.txt`.

Install the PyTorch build appropriate for the target NVIDIA / CUDA environment before running the ML stage.

The Unreal and Houdini stages also depend on their respective application installations and plugins.

---

## Machine Learning

The generated semantic dataset can be used for semantic-segmentation experiments with **SegFormer**.

The current implementation:

* loads RGB images and semantic masks
* creates a train / validation split
* fine-tunes `nvidia/mit-b1`
* calculates mean IoU
* saves the best model
* exports training / evaluation metrics
* generates prediction visualisations

The ML stage exists primarily to demonstrate the downstream use of the generated synthetic data.

This project does **not** claim state-of-the-art model performance.

---
## Reproducibility

The repository is intended to make the complete workflow **understandable and reasonably reproducible**, rather than provide a completely self-contained one-click environment.

The following external dependencies are required:

* Unreal Engine
* Houdini
* Houdini Engine for Unreal
* NVIDIA GPU / compatible CUDA environment
* External Unreal Marketplace assets where applicable

Generated datasets, renders, checkpoints and other large runtime outputs are intentionally excluded from the repository.

Local environment configuration is also excluded:

```text
pipeline/scripts/env.yaml
```

An example configuration is provided as:

```text
pipeline/scripts/env.example.yaml
```

This allows machine-specific paths and settings to remain local.

---

## Generated Data

Generated datasets are intentionally **not committed** to Git.

Typical generated content includes:

```text
rgb/
stencil/
depth/
coco_annotations.json
runs/
visualisations/
```

These outputs can be generated locally from the pipeline configuration.

---

## Current Scope

This repository is a portfolio-scale technical demonstration of a controllable synthetic-data workflow.

It demonstrates:

```text
Procedural Generation
        ↓
Parameter Sampling
        ↓
Automated Scene Assembly
        ↓
Automated Rendering
        ↓
Semantic Dataset Generation
        ↓
COCO Annotation
        ↓
Model Training
        ↓
Evaluation
```

The project does **not** currently implement closed-loop optimisation in which model evaluation automatically modifies the next sampling distribution.

That is intentionally outside the current project scope.

---

## Known Limitations

* Unreal Engine and Houdini are external application dependencies.
* Some example assets are external Marketplace assets and cannot be redistributed.
* Exact semantic output depends on the configured Unreal assets and materials.
* GPU / CUDA compatibility affects the ML environment.
* The ML stage is intended as downstream validation of the synthetic dataset rather than a research benchmark.
* Generated datasets and training outputs are excluded from Git.

---

## Status

**Portfolio project — finalised / repository cleanup complete.**

The repository contains the core procedural generation, Unreal rendering, dataset generation, COCO conversion and SegFormer evaluation workflow.

See:

```text
PROJECT_STATUS.md
```

for the detailed project status and known limitations.

---

## License / External Assets

Code and project files in this repository are provided for portfolio / demonstration purposes unless otherwise stated.

Third-party assets remain subject to their respective licences and are not redistributed by this repository.
