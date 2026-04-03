import argparse
import json
import zipfile
import xml.etree.ElementTree as ET
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


EXCEL_NS = {"a": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
WORKBOOK_REL_NS = {
    "a": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
}
PACKAGE_REL_NS = {"pr": "http://schemas.openxmlformats.org/package/2006/relationships"}

FEATURE_COLUMNS = [
    "Age (yrs)",
    "Weight (Kg)",
    "BMI",
    "Cycle(R/I)",
    "Cycle length(days)",
    "Weight gain(Y/N)",
    "hair growth(Y/N)",
    "Skin darkening (Y/N)",
    "Hair loss(Y/N)",
    "Pimples(Y/N)",
    "Fast food (Y/N)",
    "Reg.Exercise(Y/N)",
]
TARGET_COLUMN = "PCOS (Y/N)"


def cell_column(cell_ref: str) -> str:
    letters = []
    for char in cell_ref:
        if char.isalpha():
            letters.append(char)
        else:
            break
    return "".join(letters)


def load_shared_strings(archive: zipfile.ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in archive.namelist():
        return []

    root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
    strings = []
    for item in root.findall("a:si", EXCEL_NS):
        text_parts = [node.text or "" for node in item.iter("{%s}t" % EXCEL_NS["a"])]
        strings.append("".join(text_parts))
    return strings


def sheet_path_by_name(archive: zipfile.ZipFile, sheet_name: str) -> str:
    workbook = ET.fromstring(archive.read("xl/workbook.xml"))
    workbook_rels = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
    relationship_map = {
        rel.attrib["Id"]: rel.attrib["Target"]
        for rel in workbook_rels.findall("pr:Relationship", PACKAGE_REL_NS)
    }

    for sheet in workbook.find("a:sheets", WORKBOOK_REL_NS):
        if sheet.attrib.get("name") == sheet_name:
            rel_id = sheet.attrib["{%s}id" % WORKBOOK_REL_NS["r"]]
            target = relationship_map[rel_id]
            return f"xl/{target}"
    raise ValueError(f"Sheet '{sheet_name}' not found in workbook.")


def parse_xlsx_sheet(path: Path, sheet_name: str) -> pd.DataFrame:
    with zipfile.ZipFile(path) as archive:
        shared_strings = load_shared_strings(archive)
        sheet_xml_path = sheet_path_by_name(archive, sheet_name)
        sheet_root = ET.fromstring(archive.read(sheet_xml_path))

    rows = []
    for row in sheet_root.find("a:sheetData", EXCEL_NS).findall("a:row", EXCEL_NS):
        current_row = {}
        for cell in row.findall("a:c", EXCEL_NS):
            ref = cell.attrib.get("r", "")
            value_node = cell.find("a:v", EXCEL_NS)
            if value_node is None:
                value = ""
            else:
                raw_value = value_node.text or ""
                if cell.attrib.get("t") == "s":
                    value = shared_strings[int(raw_value)]
                else:
                    value = raw_value
            current_row[cell_column(ref)] = value
        rows.append(current_row)

    if not rows:
        raise ValueError(f"Sheet '{sheet_name}' is empty.")

    header_row = rows[0]
    ordered_columns = list(header_row.keys())
    headers = [header_row.get(column, "").strip() for column in ordered_columns]

    data_rows = []
    for row in rows[1:]:
        values = [row.get(column, "") for column in ordered_columns]
        if any(str(value).strip() != "" for value in values):
            data_rows.append(values)

    dataframe = pd.DataFrame(data_rows, columns=headers)
    dataframe = dataframe.loc[:, dataframe.columns != ""]
    return dataframe


def build_dataset(excel_path: Path) -> pd.DataFrame:
    dataframe = parse_xlsx_sheet(excel_path, sheet_name="Full_new")
    selected_columns = [TARGET_COLUMN, *FEATURE_COLUMNS]
    missing_columns = [column for column in selected_columns if column not in dataframe.columns]
    if missing_columns:
        raise ValueError(f"Missing expected columns: {missing_columns}")

    dataset = dataframe[selected_columns].copy()
    for column in selected_columns:
        dataset[column] = pd.to_numeric(dataset[column], errors="coerce")
    dataset = dataset.dropna(subset=[TARGET_COLUMN]).reset_index(drop=True)
    return dataset


def build_pipeline(random_state: int) -> Pipeline:
    classifier = MLPClassifier(
        hidden_layer_sizes=(32, 16),
        activation="relu",
        solver="adam",
        alpha=0.0005,
        batch_size=32,
        learning_rate_init=0.001,
        max_iter=1200,
        early_stopping=True,
        n_iter_no_change=25,
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
    parser = argparse.ArgumentParser(description="Train Stage 1 PCOS ANN using symptom-only inputs.")
    parser.add_argument("--data", default="dataset/pcos.xlsx", help="Path to the Excel dataset.")
    parser.add_argument("--model-out", default="artifacts/stage1_ann_model.joblib", help="Path to save the trained model.")
    parser.add_argument("--metrics-out", default="artifacts/stage1_metrics.json", help="Path to save training metrics.")
    parser.add_argument("--test-size", type=float, default=0.2, help="Fraction of data used for testing.")
    parser.add_argument("--random-state", type=int, default=42, help="Random seed for reproducibility.")
    args = parser.parse_args()

    data_path = Path(args.data)
    model_out = Path(args.model_out)
    metrics_out = Path(args.metrics_out)
    model_out.parent.mkdir(parents=True, exist_ok=True)
    metrics_out.parent.mkdir(parents=True, exist_ok=True)

    dataset = build_dataset(data_path)
    x = dataset[FEATURE_COLUMNS]
    y = dataset[TARGET_COLUMN].astype(int)

    x_train, x_test, y_train, y_test = train_test_split(
        x,
        y,
        test_size=args.test_size,
        stratify=y,
        random_state=args.random_state,
    )

    pipeline = build_pipeline(args.random_state)
    pipeline.fit(x_train, y_train)

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

    print("Stage 1 ANN trained successfully.")
    print(f"Dataset samples: {len(dataset)}")
    print(f"Train samples: {len(x_train)} | Test samples: {len(x_test)}")
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
