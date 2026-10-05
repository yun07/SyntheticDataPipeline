# Synthetic Data Pipeline — Project Status

## Current Status

**Status: Portfolio project — finalisation / repository cleanup**

The project is a controllable synthetic environment and dataset generation pipeline built around Houdini, Unreal Engine and Python.

The core pipeline is functional and the current focus is on:

* Repository organisation
* Reproducibility
* Documentation
* Dependency identification
* Final demo / portfolio presentation

No major new features are currently planned.

---

## Project Goal

The project explores a controllable synthetic environment workflow:

```text
Procedural Environment Generation
            ↓
       Unreal Engine
            ↓
      Automated Rendering
            ↓
    Semantic Dataset
            ↓
       COCO Export
            ↓
   Segmentation Training
            ↓
        Evaluation
```

The main objective is to demonstrate a complete, controllable synthetic-data workflow rather than a production-ready dataset platform.

---

## Main Components

### Houdini

Procedural environment generation using a Houdini Digital Asset (HDA).

The HDA exposes controllable parameters used to generate variations of the environment.

### Unreal Engine

Unreal Engine is used for:

* Scene assembly
* Procedural environment integration
* Rendering
* Semantic mask generation
* Scene capture
* Dataset image export

### Python

Python scripts provide orchestration and supporting pipeline functionality.

The main entry point is:

```text
pipeline/scripts/orchestra.py
```

Individual pipeline stages can also be executed independently.

---

## Dataset

The project generates synthetic scene data including RGB imagery and semantic information.

The dataset configuration is supplied through YAML configuration files.

Example:

```text
datasets/job_example_v001.yaml
```

Dataset/output locations are configurable rather than being tied to a single fixed location.

---

## Machine Learning

The generated semantic dataset has been used for semantic-segmentation experimentation with SegFormer.

Training and evaluation scripts are included in the repository.

The ML component is intended to demonstrate the complete synthetic-data loop and is not presented as a state-of-the-art segmentation benchmark.

---

## Current Limitations

* The pipeline depends on external software including Unreal Engine and Houdini.
* Some Unreal assets are external Marketplace assets and are not redistributed with this repository.
* Exact semantic output depends on the configured Unreal assets and materials.
* Dataset generation is currently controlled through explicit parameters/configuration.
* Closed-loop automatic optimisation of generation parameters based on model evaluation is not currently implemented.
* The repository is being prepared primarily as a portfolio / technical demonstration rather than a production deployment package.

---

## Finalisation Tasks

* [ ] Final repository cleanup
* [ ] Verify `.gitignore`
* [ ] Document external dependencies
* [ ] Document Unreal project setup
* [ ] Document Houdini/HDA setup
* [ ] Document Python dependencies
* [ ] Verify orchestration workflow
* [ ] Add final demo material
* [ ] Push final repository to GitHub

---

## Scope

The project is considered feature-complete for its intended portfolio purpose.

Future work should only be added if it materially improves reproducibility, technical clarity, or demonstration value.
