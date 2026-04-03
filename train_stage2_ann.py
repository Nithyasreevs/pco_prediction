import argparse
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.inspection import permutation_importance
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.model_selection import train_test_split
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from train_stage1_ann import parse_xlsx_sheet

BASE_FEATURE_COLUMNS = ["LH(mIU/mL)", "FSH(mIU/mL)"]
FEATURE_COLUMNS = ["LH(mIU/mL)", "FSH(mIU/mL)", "LH_FSH_Ratio"]
TARGET_COLUMN = "PCOS (Y/N)"


def build_stage2_dataset(excel_path: Path) -> pd.DataFrame:
    dataframe = parse_xlsx_sheet(excel_path, sheet_name="Full_new")
    selected_columns = [TARGET_COLUMN, *BASE_FEATURE_COLUMNS]
    missing_columns = [column for column in selected_columns if column not in dataframe.columns]
    if missing_columns:
        raise ValueError(f"Missing expected columns: {missing_columns}")

    dataset = dataframe[selected_columns].copy()
    for column in dataset.columns:
        dataset[column] = pd.to_numeric(dataset[column], errors="coerce")
    dataset = dataset.dropna(subset=selected_columns).reset_index(drop=True)
    dataset["LH_FSH_Ratio"] = dataset["LH(mIU/mL)"] / dataset["FSH(mIU/mL)"].replace(0, pd.NA)
    dataset["LH_FSH_Ratio"] = dataset["LH_FSH_Ratio"].fillna(0)
    return dataset[[TARGET_COLUMN, *FEATURE_COLUMNS]]


def build_pipeline(random_state: int) -> Pipeline:
    classifier = MLPClassifier(
        hidden_layer_sizes=(32, 16),
        activation="relu",
        solver="adam",
        alpha=0.0005,
        batch_size=16,
        learning_rate_init=0.001,
        max_iter=1500,
        early_stopping=True,
        n_iter_no_change=30,
        random_state=random_state,
    )
    return Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
            ("classifier", classifier),
        ]
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Train Stage 2 PCOS ANN using LH and FSH values.")
    parser.add_argument("--data", default="dataset/pcos.xlsx", help="Path to the Excel dataset.")
    parser.add_argument("--model-out", default="artifacts/stage2_ann_model.joblib", help="Path to save the trained model.")
    parser.add_argument("--metrics-out", default="artifacts/stage2_metrics.json", help="Path to save training metrics.")
    parser.add_argument("--test-size", type=float, default=0.2, help="Fraction of data used for testing.")
    parser.add_argument("--random-state", type=int, default=42, help="Random seed for reproducibility.")
    args = parser.parse_args()

    data_path = Path(args.data)
    model_out = Path(args.model_out)
    metrics_out = Path(args.metrics_out)
    model_out.parent.mkdir(parents=True, exist_ok=True)
    metrics_out.parent.mkdir(parents=True, exist_ok=True)

    dataset = build_stage2_dataset(data_path)
    x = dataset[FEATURE_COLUMNS]
    y = dataset[TARGET_COLUMN].astype(int)

    x_train, x_test, y_train, y_test = train_test_split(
        x,
        y,
        test_size=args.test_size,
        stratify=y,
        random_state=args.random_state,
    )

    train_frame = x_train.copy()
    train_frame["_target"] = y_train.values
    max_count = int(train_frame["_target"].value_counts().max())
    balanced_parts = []
    for _, group in train_frame.groupby("_target"):
        repeats = max_count // len(group)
        remainder = max_count % len(group)
        additions = [group] * repeats
        if remainder:
            additions.append(group.sample(remainder, replace=True, random_state=args.random_state))
        balanced_parts.append(pd.concat(additions, ignore_index=True))
    balanced_frame = pd.concat(balanced_parts, ignore_index=True).sample(frac=1, random_state=args.random_state).reset_index(drop=True)
    x_train_balanced = balanced_frame.drop(columns="_target")
    y_train_balanced = balanced_frame["_target"].astype(int)

    pipeline = build_pipeline(args.random_state)
    pipeline.fit(x_train_balanced, y_train_balanced)

    y_pred = pipeline.predict(x_test)
    y_prob = pipeline.predict_proba(x_test)[:, 1]

    accuracy = accuracy_score(y_test, y_pred)
    report = classification_report(y_test, y_pred, output_dict=True)
    matrix = confusion_matrix(y_test, y_pred)
    importance = permutation_importance(
        pipeline,
        x_test,
        y_test,
        n_repeats=20,
        random_state=args.random_state,
        scoring="f1",
    )
    feature_importance = {
        feature: float(score)
        for feature, score in sorted(
            zip(FEATURE_COLUMNS, importance.importances_mean),
            key=lambda item: item[1],
            reverse=True,
        )
    }

    model_bundle = {
        "model": pipeline,
        "feature_columns": FEATURE_COLUMNS,
        "target_column": TARGET_COLUMN,
        "threshold": 0.5,
    }
    joblib.dump(model_bundle, model_out)

    metrics = {
        "samples": int(len(dataset)),
        "train_samples": int(len(x_train)),
        "balanced_train_samples": int(len(x_train_balanced)),
        "test_samples": int(len(x_test)),
        "features": FEATURE_COLUMNS,
        "threshold": 0.5,
        "accuracy": float(accuracy),
        "confusion_matrix": matrix.tolist(),
        "classification_report": report,
        "feature_importance_f1_permutation": feature_importance,
        "positive_rate_test": float(np.mean(y_test)),
        "average_predicted_probability": float(np.mean(y_prob)),
    }
    metrics_out.write_text(json.dumps(metrics, indent=2), encoding="utf-8")

    print("Stage 2 ANN trained successfully.")
    print(f"Dataset samples: {len(dataset)}")
    print(f"Train samples: {len(x_train)} | Balanced train samples: {len(x_train_balanced)} | Test samples: {len(x_test)}")
    print("Decision threshold: 0.50")
    print(f"Accuracy: {accuracy:.4f}")
    print("Confusion matrix:")
    print(matrix)
    print("\nClassification report:")
    print(classification_report(y_test, y_pred))
    print("\nFeature importance (permutation F1):")
    for feature, score in feature_importance.items():
        print(f"{feature}: {score:.4f}")
    print(f"Model saved to: {model_out}")
    print(f"Metrics saved to: {metrics_out}")


if __name__ == "__main__":
    main()
