# Stage 1 PCOS Risk Prediction

This stage predicts PCOS risk using only symptom-based inputs and an Artificial Neural Network (ANN).

## Features Used

- Age
- Weight
- BMI
- Cycle(R/I)
- Cycle length(days)
- Weight gain(Y/N)
- hair growth(Y/N)
- Skin darkening (Y/N)
- Hair loss(Y/N)
- Pimples(Y/N)
- Fast food (Y/N)
- Reg.Exercise(Y/N)

## Files

- `train_stage1_ann.py`: trains the ANN and saves model artifacts
- `predict_stage1_ann.py`: predicts PCOS risk for one new case
- `artifacts/stage1_ann_model.joblib`: saved trained model
- `artifacts/stage1_metrics.json`: saved evaluation metrics

## Train

```powershell
python train_stage1_ann.py
```

## Predict

```powershell
python predict_stage1_ann.py `
  --age 28 `
  --weight 65 `
  --bmi 26 `
  --cycle_ri 4 `
  --cycle_length 45 `
  --weight_gain 1 `
  --hair_growth 1 `
  --skin_darkening 1 `
  --hair_loss 1 `
  --pimples 1 `
  --fast_food 1 `
  --reg_exercise 0
```

## Notes

- The script reads the Excel file directly, so `openpyxl` is not required.
- The ANN is implemented with `scikit-learn` `MLPClassifier`.
- Target column: `PCOS (Y/N)`
