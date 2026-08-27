# Upstream dataset card (verbatim copy)

Source: https://huggingface.co/datasets/DrBimmer/comprehensive-car-damage
Revision: 355b0990ec008e15963055e6bb448045a65040a3 · License: MIT
Copied here unchanged for attribution and licence traceability.

---

---
annotations_creators:
- manual
language:
- en
license: mit
multilinguality: monolingual
pretty_name: Car Front and Rear Damage Detection
size_categories:
- 1K<n<10K
source_datasets: []
task_categories:
- image-classification
task_ids:
- multi-class-image-classification
---

# Car Front and Rear Damage Detection Dataset

## Dataset Summary

This dataset is designed for training and evaluating machine learning models for car damage detection, specifically focusing on front and rear vehicle damages.

It includes high-quality labeled images categorized into six distinct classes:
- **R_Normal**: Rear view of undamaged cars  
- **R_Crushed**: Rear view of cars with crushed damage  
- **R_Breakage**: Rear view of cars with visible breakage  
- **F_Normal**: Front view of undamaged cars  
- **F_Crushed**: Front view of cars with crushed damage  
- **F_Breakage**: Front view of cars with visible breakage  

## Use Cases

With this dataset, researchers and developers can build AI-powered solutions for:
- Automated vehicle inspection systems  
- Insurance claim assessment tools  
- Road safety and damage analytics  
- Training vision models for automotive applications  

The clear classification structure enables models to effectively distinguish between normal, crushed, and broken conditions in front and rear views.

## Dataset Structure

Each image is stored in a directory named after its class label. The dataset is balanced across the six categories and includes metadata for each image if needed (e.g., angle, lighting conditions).

### Example Labels

| Label       | Description                      |
|-------------|----------------------------------|
| R_Normal    | Rear view of undamaged car       |
| R_Crushed   | Rear view, visibly crushed       |
| R_Breakage  | Rear view, broken parts visible  |
| F_Normal    | Front view of undamaged car      |
| F_Crushed   | Front view, visibly crushed      |
| F_Breakage  | Front view, broken parts visible |
