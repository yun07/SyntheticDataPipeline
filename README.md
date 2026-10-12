# Synthetic Environment & Data Pipeline

**Independent Engineering Project | Houdini · Unreal Engine · Python · SegFormer**

A procedural synthetic-environment and data-generation pipeline designed to connect specialised scenario generation with automated rendering, semantic dataset export, and downstream model evaluation.

The project demonstrates an end-to-end workflow using a controllable procedural intersection generator as its reference implementation.

## Problem

Specialised edge cases often require purpose-built procedural generators. However, generating a scenario is only one part of the workflow: automated rendering, semantic annotation, dataset export, and downstream model evaluation must also be connected.

Building these components separately for each scenario can duplicate engineering effort and require expertise across procedural generation, real-time rendering, automation, and machine learning workflows.

## Approach

Designed a pipeline that separates **scenario generation from downstream data production**.

Developers can create specialised Houdini Digital Assets (HDAs) for configurable scenarios, while a shared workflow connects Houdini Engine with Unreal Engine for automated scene generation, rendering, and dataset export.

A procedural intersection generator serves as the reference implementation, demonstrating configurable road-junction geometry and parameter-driven scene variation.

## Technical Highlights

- **Procedural scenario generation:** Configurable intersection geometry and parameter sampling for generating varied road-junction layouts.
- **Automated rendering and export:** Integrated Houdini Engine and Unreal Engine to generate synthetic imagery and semantic outputs without an intermediate USD-file workflow.
- **Pipeline orchestration:** Coordinated independent Python scripts for sample generation, rendering, annotation export, and model evaluation.
- **Failure handling:** Implemented checkpoint-based recovery, lock-file coordination to help prevent duplicate file writes, and error handling for Houdini Engine failures during rendering.
- **Downstream ML validation:** Connected generated data to a SegFormer semantic-segmentation training and evaluation workflow.

## Results

A SegFormer model was fine-tuned on the generated synthetic dataset to validate its downstream use for semantic segmentation.

| Metric | Result |
|---|---|
| Best evaluation mIoU | **0.8745** |
| Semantic classes | 7 |
| Training images | Approximately 300 |
| Model | `nvidia/mit-b1` |

The result demonstrates an end-to-end workflow from procedural environment generation to semantic dataset creation, model training, and evaluation. It is a pipeline validation result, not a state-of-the-art benchmark or evidence of generalisation to real-world data.

## Pipeline Workflow

```text
Houdini Procedural Generation
              ↓
       Parameter Sampling
              ↓
         Houdini Engine
              ↓
         Unreal Engine
              ↓
        Automated Rendering
              ↓
       RGB + Semantic Masks
              ↓
        COCO Annotations
              ↓
       SegFormer Fine-tuning
              ↓
      Evaluation & Visualisation
```

The main orchestration entry point is `pipeline/scripts/orchestra.py`. Individual scripts can also be executed independently where appropriate.

## Repository Structure

```text
SyntheticDataPipeline/
├── HDA/
│   └── Houdini Digital Assets
├── pipeline/
│   └── scripts/
│       ├── UnrealPython/
│       ├── orchestra.py
│       ├── generate_samples.py
│       ├── ue_bridge.py
│       ├── rpm.py
│       ├── coco_generator.py
│       ├── segformer_finetune.py
│       ├── segformer_visualise.py
│       ├── json2jpg.py
│       ├── check_resources.py
│       └── status_check.py
├── UnrealProjects/
│   └── Unreal Engine project
├── datasets/
│   └── job_example_v001.yaml
├── PROJECT_STATUS.md
├── requirements.txt
└── README.md
```

## Sampling

`generate_samples.py` supports multiple sampling strategies:

- `grid`
- `random`
- `lhs` — Latin Hypercube Sampling
- `sobol` — Sobol sequence sampling

Sampling parameters are configured through YAML job files. An example configuration is provided at `datasets/job_example_v001.yaml`.

Generated datasets can be stored outside the repository. Their output locations are configured for the local environment rather than fixed to the repository directory.

## Python Pipeline

| Script | Responsibility |
|---|---|
| `orchestra.py` | Main pipeline orchestration |
| `generate_samples.py` | Parameter sampling and sample generation |
| `ue_bridge.py` | Unreal communication and pipeline integration |
| `rpm.py` | Unreal process and render-process management |
| `coco_generator.py` | Semantic mask conversion to COCO annotations |
| `segformer_finetune.py` | SegFormer training and evaluation |
| `segformer_visualise.py` | Prediction and ground-truth visualisation |
| `json2jpg.py` | Image format conversion |
| `check_resources.py` | Resource checks |
| `status_check.py` | Pipeline status handling |
| `UnrealPython/` | Unreal-side Python utilities |

The components are kept relatively independent so that individual stages can be tested or executed without always running the entire workflow.

## Houdini Setup

The repository includes the intersection generator HDA:

`HDA/sop_IntersectGenerator.1.3.hda`

The HDA generates controllable procedural road-junction environments consumed by Unreal Engine through Houdini Engine. Scene variation is driven by parameters such as road dimensions, intersection configuration, and random seeds.

A compatible Houdini installation and Houdini Engine for Unreal are required.

## Unreal Engine Setup

The Unreal project provides procedural scene assembly, automated rendering, and semantic-data generation.

The workflow uses:

- Houdini Engine integration
- Scene Capture
- Movie Render Queue / automated rendering
- Custom Stencil for semantic rendering
- Unreal Python automation

### Required plugins

Ensure the following plugins are enabled:

1. Blueprint File Utilities
2. Json Blueprint Utilities

### Editor preference

Under **Edit → Editor Preferences**, disable **Use Less CPU when in Background** for the intended automated pipeline workflow.

### External assets

Some example assets originate from external Unreal Marketplace downloads and are not redistributed in this repository.

The exact vehicle Static Mesh and Material configuration affects semantic stencil output. Reproducing the example dataset may therefore require an equivalent compatible asset and material setup.

Third-party assets remain subject to their original licences.

## Python Environment

Python 3.10+ is recommended.

Install the listed Python dependencies:

```bash
pip install -r requirements.txt
```

### PyTorch and CUDA

PyTorch is not pinned to a specific build in `requirements.txt`, because the appropriate installation depends on the target GPU and CUDA environment.

Install a compatible PyTorch build before running the machine-learning stage.

The complete workflow also requires the relevant Houdini and Unreal Engine installations, plugins, and compatible project assets.

### Local configuration

Machine-specific configuration is excluded from Git:

`pipeline/scripts/env.yaml`

An example configuration is provided:

`pipeline/scripts/env.example.yaml`

Configure local application paths and other environment-specific settings before running the pipeline.

## Machine Learning

The ML stage demonstrates the downstream use of the generated semantic dataset with SegFormer.

The current workflow includes:

- Loading RGB images and semantic masks
- Creating a training / validation split
- Fine-tuning `nvidia/mit-b1`
- Calculating mean Intersection over Union (mIoU)
- Saving the best model
- Exporting training and evaluation metrics
- Generating prediction visualisations

The ML stage is intended to validate the integration between synthetic data generation and downstream training and evaluation. The project does not claim state-of-the-art model performance or establish that the generated data generalises to real-world conditions.

## Reproducibility and Generated Data

The repository is intended to make the workflow understandable and reasonably reproducible, rather than provide a completely self-contained, one-click environment.

External dependencies include:

- Houdini
- Unreal Engine
- Houdini Engine for Unreal
- A compatible NVIDIA GPU / CUDA environment for model training
- External Unreal assets where applicable

Generated datasets, rendered images, checkpoints, and other large runtime outputs are intentionally excluded from Git.

Typical generated outputs include:

```text
rgb/
stencil/
depth/
coco_annotations.json
runs/
visualisations/
```

These outputs are generated locally according to the job configuration and pipeline settings.

## Scope and Limitations

This is a portfolio-scale engineering demonstration of a controllable synthetic-data workflow.

**Demonstrated scope:**

- Procedural intersection generation
- Parameterised scenario sampling
- Houdini-to-Unreal integration
- Automated rendering and semantic-data export
- COCO annotation generation
- Downstream segmentation training and evaluation
- Basic pipeline recovery and process-management mechanisms

**Outside the current scope:**

- Closed-loop optimisation that automatically changes future sampling distributions based on model evaluation
- General-purpose world generation
- Full vehicle, traffic-agent, or robotics physics simulation
- A validated benchmark of synthetic-to-real generalisation
- A self-contained environment that removes all external software and asset dependencies

The pipeline establishes a foundation for connecting specialised scenario generators to a shared data-production workflow. Its practical value for other scenario types would need to be validated by integrating additional generators and measuring the resulting development effort.

## Project Status

**Portfolio project — finalised.**

The repository contains the core procedural generation, Unreal rendering, dataset generation, COCO conversion, and SegFormer evaluation workflow.

See `PROJECT_STATUS.md` for additional implementation details and known limitations.

## Licence and Third-Party Assets

Code and project files are provided for portfolio and demonstration purposes unless otherwise stated.

Third-party assets remain subject to their respective licences and are not redistributed by this repository.