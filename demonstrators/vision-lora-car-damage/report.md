# Zero-shot baseline vs LoRA fine-tune (held-out test split)

| metric | zero-shot baseline | LoRA fine-tuned |
|---|---|---|
| accuracy | 0.6326 | 0.7739 |
| macro-F1 | 0.5161 | 0.7555 |
| selective accuracy @90% coverage | 0.6715 | 0.8140 |
| accuracy on abstained 10% | 0.2826 | 0.4130 |
| unrestricted answer is a letter | 1.0000 | 1.0000 |
| mean confidence | 0.7174 | 0.8130 |
| n | 460 | 460 |

**Delta macro-F1: +23.94 points** -> pre-registered acceptance (>= +10 points): **PASS**

## Per-class (baseline)

| class | precision | recall | F1 | support |
|---|---|---|---|---|
| F_Normal | 0.724 | 0.970 | 0.829 | 100 |
| F_Crushed | 0.545 | 0.075 | 0.132 | 80 |
| F_Breakage | 0.626 | 0.870 | 0.728 | 100 |
| R_Normal | 0.588 | 0.950 | 0.726 | 60 |
| R_Crushed | 0.143 | 0.017 | 0.030 | 60 |
| R_Breakage | 0.597 | 0.717 | 0.652 | 60 |

## Per-class (fine-tuned)

| class | precision | recall | F1 | support |
|---|---|---|---|---|
| F_Normal | 0.810 | 0.940 | 0.870 | 100 |
| F_Crushed | 0.700 | 0.700 | 0.700 | 80 |
| F_Breakage | 0.919 | 0.790 | 0.849 | 100 |
| R_Normal | 0.692 | 0.900 | 0.783 | 60 |
| R_Crushed | 0.615 | 0.533 | 0.571 | 60 |
| R_Breakage | 0.854 | 0.683 | 0.759 | 60 |

## Confusion (baseline)

| true \ pred | F_Normal | F_Crushed | F_Breakage | R_Normal | R_Crushed | R_Breakage |
|---|---|---|---|---|---|---|
| F_Normal | 97 | 0 | 3 | 0 | 0 | 0 |
| F_Crushed | 27 | 6 | 47 | 0 | 0 | 0 |
| F_Breakage | 9 | 4 | 87 | 0 | 0 | 0 |
| R_Normal | 1 | 1 | 0 | 57 | 0 | 1 |
| R_Crushed | 0 | 0 | 0 | 31 | 1 | 28 |
| R_Breakage | 0 | 0 | 2 | 9 | 6 | 43 |

## Confusion (fine-tuned)

| true \ pred | F_Normal | F_Crushed | F_Breakage | R_Normal | R_Crushed | R_Breakage |
|---|---|---|---|---|---|---|
| F_Normal | 94 | 6 | 0 | 0 | 0 | 0 |
| F_Crushed | 17 | 56 | 7 | 0 | 0 | 0 |
| F_Breakage | 4 | 17 | 79 | 0 | 0 | 0 |
| R_Normal | 1 | 1 | 0 | 54 | 4 | 0 |
| R_Crushed | 0 | 0 | 0 | 21 | 32 | 7 |
| R_Breakage | 0 | 0 | 0 | 3 | 16 | 41 |

## Repeat evaluation (fresh process)

- identical predictions: True
- max |confidence delta|: 0.00e+00
- byte-identical JSONL: True
