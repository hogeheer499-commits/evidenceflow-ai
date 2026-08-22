# Abstention analysis (selective prediction on the held-out test split)

Confidence = softmax over the six answer-letter logits (a proxy). Coverage = fraction of images on which the model answers; the rest is abstained / escalated.

| coverage | zero-shot: acc on answered | zero-shot: acc on abstained | zero-shot: threshold | fine-tuned: acc on answered | fine-tuned: acc on abstained | fine-tuned: threshold |
|---|---|---|---|---|---|---|
| 100% | 0.633 | - | 0.284 | 0.774 | - | 0.279 |
| 95% | 0.652 | 0.261 | 0.430 | 0.794 | 0.391 | 0.513 |
| 90% | 0.671 | 0.283 | 0.479 | 0.814 | 0.413 | 0.551 |
| 80% | 0.707 | 0.337 | 0.576 | 0.848 | 0.478 | 0.643 |
| 70% | 0.730 | 0.406 | 0.637 | 0.873 | 0.543 | 0.719 |
| 50% | 0.791 | 0.474 | 0.748 | 0.930 | 0.617 | 0.854 |

| calibration metric | zero-shot | fine-tuned |
|---|---|---|
| expected calibration error (10 bins) | 0.095 | 0.049 |
| Brier score (max-prob vs correct) | 0.206 | 0.142 |
| overall accuracy (100% coverage) | 0.633 | 0.774 |
