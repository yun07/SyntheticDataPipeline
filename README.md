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

The project is designed as a technical demonstration of a controllable synthetic-data workflow.

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

## Main Entry Point

The pipeline is orchestrated through:

```text
pipeline/scripts/orchestra.py
```

The individual Python scripts can also be run independently where appropriate.

The dataset/input location is configurable, so the generated dataset does not need to live inside the repository.

---

## Configuration

Example configuration:

```text
datasets/job_example_v001.yaml
```

The configuration defines the parameters used for a dataset-generation job.

The repository contains an example configuration rather than a generated dataset.

---

## Environment

The project uses:

* Python
* Unreal Engine
* Houdini
* Houdini Engine for Unreal
* NVIDIA GPU hardware for the rendering / ML workflow

Exact software versions and setup requirements will be documented as the repository is finalised.

---

## Houdini

The project includes a Houdini Digital Asset used for procedural environment generation.

The HDA is intended to provide controllable scene variation which can then be consumed by Unreal Engine through Houdini Engine.

---

## Unreal Engine

The Unreal project provides the rendering and semantic-data generation stage.

The project uses Unreal functionality including:

* Scene Capture
* Movie Render Queue / automated rendering
* Custom Stencil / semantic rendering
* Procedural scene assembly
* Python automation

Some assets used by the project originate from external Unreal Marketplace downloads and are **not redistributed in this repository**.

When reproducing the semantic dataset, the required vehicle Static Mesh and Material configuration should be used because asset/material configuration affects the resulting semantic stencil output.

---

## Python Pipeline

The Python pipeline contains separate stages for tasks including:

* Pipeline orchestration
* Sample generation
* Unreal communication
* Dataset / COCO generation
* Image conversion
* SegFormer training
* Visualisation
* Resource checking
* Pipeline status handling

The scripts are intentionally kept as independently executable components where practical.

---

## Machine Learning

The generated dataset can be used for semantic-segmentation experiments with SegFormer.

The ML stage is included to demonstrate the downstream use of the generated synthetic data.

The project is not intended to claim state-of-the-art model performance.

---

## Reproducibility

The repository aims to make the pipeline understandable and reasonably reproducible.

However, the complete workflow depends on external software and assets that cannot be redistributed with the repository.

These include:

* Unreal Engine
* Houdini
* Houdini Engine for Unreal
* External Marketplace assets
* GPU / CUDA-dependent Python packages

The repository therefore separates project code and configuration from generated datasets and external assets.

---

## Status

This project is currently being finalised as a portfolio technical demonstration.

See:

```text
PROJECT_STATUS.md
```

for the current project status and known limitations.

---

## License / External Assets

Code and project files in this repository are provided for portfolio / demonstration purposes unless otherwise stated.

Third-party assets remain subject to their respective licences and are not redistributed by this repository.
