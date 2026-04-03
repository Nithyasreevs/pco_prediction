import io
import os
import re
from pathlib import Path

import fitz
import joblib
import pandas as pd
import pytesseract
from flask import Flask, jsonify, request
from flask_cors import CORS
from PIL import Image, ImageOps, ImageFilter

BASE_DIR = Path(__file__).resolve().parent.parent
STAGE1_MODEL_PATH = BASE_DIR / "artifacts" / "stage1_ann_model.joblib"
STAGE2_MODEL_PATH = BASE_DIR / "artifacts" / "stage2_ann_model.joblib"


def resolve_tesseract_path() -> Path | None:
    configured = os.getenv("TESSERACT_CMD")
    candidates = [
        configured,
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        "/usr/bin/tesseract",
        "/usr/local/bin/tesseract",
    ]
    for candidate in candidates:
        if not candidate:
            continue
        candidate_path = Path(candidate)
        if candidate_path.exists():
            return candidate_path
    return None


TESSERACT_PATH = resolve_tesseract_path()

if TESSERACT_PATH is not None:
    pytesseract.pytesseract.tesseract_cmd = str(TESSERACT_PATH)

app = Flask(__name__)
CORS(app)

stage1_bundle = joblib.load(STAGE1_MODEL_PATH)
stage1_model = stage1_bundle["model"]
stage1_feature_columns = stage1_bundle["feature_columns"]
stage1_threshold = float(stage1_bundle.get("threshold", 0.5))

stage2_bundle = joblib.load(STAGE2_MODEL_PATH) if STAGE2_MODEL_PATH.exists() else None
stage2_model = stage2_bundle["model"] if stage2_bundle else None
stage2_feature_columns = stage2_bundle["feature_columns"] if stage2_bundle else ["LH(mIU/mL)", "FSH(mIU/mL)", "LH_FSH_Ratio"]
stage2_threshold = float(stage2_bundle.get("threshold", 0.5)) if stage2_bundle else 0.5

STAGE1_FIELD_LABELS = {
    "age": "Age (yrs)",
    "weight": "Weight (Kg)",
    "bmi": "BMI",
    "cycle_ri": "Cycle(R/I)",
    "cycle_length": "Cycle length(days)",
    "weight_gain": "Weight gain(Y/N)",
    "hair_growth": "hair growth(Y/N)",
    "skin_darkening": "Skin darkening (Y/N)",
    "hair_loss": "Hair loss(Y/N)",
    "pimples": "Pimples(Y/N)",
    "fast_food": "Fast food (Y/N)",
    "reg_exercise": "Reg.Exercise(Y/N)",
}


def build_stage1_input_frame(payload: dict) -> pd.DataFrame:
    row = {}
    missing_fields = []

    for api_field, model_field in STAGE1_FIELD_LABELS.items():
        if api_field not in payload:
            missing_fields.append(api_field)
            continue
        row[model_field] = float(payload[api_field])

    if missing_fields:
        raise ValueError(f"Missing required fields: {', '.join(missing_fields)}")

    return pd.DataFrame([row], columns=stage1_feature_columns)


def build_stage2_input_frame(lh_value: float, fsh_value: float) -> pd.DataFrame:
    lh_value = float(lh_value)
    fsh_value = float(fsh_value)
    ratio = lh_value / fsh_value if fsh_value not in (0, 0.0) else 0.0
    return pd.DataFrame([
        {
            "LH(mIU/mL)": lh_value,
            "FSH(mIU/mL)": fsh_value,
            "LH_FSH_Ratio": ratio,
        }
    ], columns=stage2_feature_columns)


def run_stage2_prediction(lh_value: float, fsh_value: float) -> dict:
    if stage2_model is None:
        raise ValueError("Stage 2 model is not trained yet. Run train_stage2_ann.py first.")

    input_frame = build_stage2_input_frame(lh_value, fsh_value)
    probability = float(stage2_model.predict_proba(input_frame)[0][1])
    prediction = int(probability >= stage2_threshold)
    return {
        "lh": round(float(lh_value), 4),
        "fsh": round(float(fsh_value), 4),
        "prediction": prediction,
        "probability": round(probability, 4),
        "threshold": round(stage2_threshold, 2),
        "risk_label": "High PCOS risk" if prediction == 1 else "Low PCOS risk",
    }


def extract_first_value_after_marker(text: str, marker: str) -> float | None:
    pattern = rf"\b{marker}\b[^0-9]*([0-9]+(?:\.[0-9]+)?)"
    match = re.search(pattern, text, flags=re.IGNORECASE)
    if match:
        return float(match.group(1))
    return None


def extract_lab_values_from_text(report_text: str) -> dict:
    lines = [line.strip() for line in report_text.splitlines() if line.strip()]
    normalized_text = re.sub(r"\s+", " ", report_text)

    extracted = {}

    for line in lines:
        upper_line = line.upper()
        if "LH" in upper_line and "FSH" not in upper_line and "lh" not in extracted:
            value = extract_first_value_after_marker(line, "LH")
            if value is not None:
                extracted["lh"] = value
        if "FSH" in upper_line and "fsh" not in extracted:
            value = extract_first_value_after_marker(line, "FSH")
            if value is not None:
                extracted["fsh"] = value

    if "lh" not in extracted:
        value = extract_first_value_after_marker(normalized_text, "LH")
        if value is not None:
            extracted["lh"] = value

    if "fsh" not in extracted:
        value = extract_first_value_after_marker(normalized_text, "FSH")
        if value is not None:
            extracted["fsh"] = value

    if "lh" not in extracted or "fsh" not in extracted:
        raise ValueError(
            "Could not extract both LH and FSH from the uploaded report. Please upload a clearer report or paste the report text manually."
        )

    return extracted


def preprocess_image_for_ocr(image: Image.Image) -> Image.Image:
    image = image.convert("L")
    image = ImageOps.autocontrast(image)
    image = image.resize((image.width * 2, image.height * 2))
    image = image.filter(ImageFilter.SHARPEN)
    image = image.point(lambda px: 255 if px > 160 else 0)
    return image


def ocr_image_bytes(raw_bytes: bytes) -> str:
    if TESSERACT_PATH is None:
        raise ValueError("Tesseract OCR is not installed or not found at the configured path.")
    image = Image.open(io.BytesIO(raw_bytes))
    processed = preprocess_image_for_ocr(image)
    return pytesseract.image_to_string(processed, config="--oem 3 --psm 6")


def extract_text_from_pdf(raw_bytes: bytes) -> str:
    if TESSERACT_PATH is None:
        raise ValueError("Tesseract OCR is not installed or not found at the configured path.")

    document = fitz.open(stream=raw_bytes, filetype="pdf")
    pages = []

    for page in document:
        text = page.get_text("text").strip()
        if text:
            pages.append(text)
            continue

        pix = page.get_pixmap(dpi=300)
        image = Image.open(io.BytesIO(pix.tobytes("png")))
        processed = preprocess_image_for_ocr(image)
        pages.append(pytesseract.image_to_string(processed, config="--oem 3 --psm 6"))

    return "\n".join(pages)


def extract_report_text_from_upload(uploaded_file) -> str:
    filename = (uploaded_file.filename or "").lower()
    raw_bytes = uploaded_file.read()

    if filename.endswith((".txt", ".csv")):
        return raw_bytes.decode("utf-8", errors="ignore")

    if filename.endswith((".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff")):
        return ocr_image_bytes(raw_bytes)

    if filename.endswith(".pdf"):
        return extract_text_from_pdf(raw_bytes)

    raise ValueError("Unsupported file type. Please upload a .txt, .csv, image, or .pdf report.")


@app.get("/health")
def health() -> tuple:
    return jsonify({
        "status": "ok",
        "stage1_model_loaded": STAGE1_MODEL_PATH.exists(),
        "stage2_model_loaded": STAGE2_MODEL_PATH.exists(),
        "tesseract_configured": TESSERACT_PATH is not None,
        "stage1_threshold": stage1_threshold,
        "stage2_threshold": stage2_threshold,
    }), 200


@app.post("/predict")
def predict_stage1() -> tuple:
    try:
        payload = request.get_json(silent=True) or {}
        input_frame = build_stage1_input_frame(payload)
        probability = float(stage1_model.predict_proba(input_frame)[0][1])
        prediction = int(probability >= stage1_threshold)

        return jsonify({
            "prediction": prediction,
            "probability": round(probability, 4),
            "threshold": round(stage1_threshold, 2),
            "risk_label": "High PCOS risk" if prediction == 1 else "Low PCOS risk",
        }), 200
    except ValueError as error:
        return jsonify({"error": str(error)}), 400
    except Exception as error:
        return jsonify({"error": f"Prediction failed: {error}"}), 500


@app.post("/predict-stage2")
def predict_stage2() -> tuple:
    try:
        payload = request.get_json(silent=True) or {}
        lh_value = float(payload.get("lh"))
        fsh_value = float(payload.get("fsh"))
        return jsonify(run_stage2_prediction(lh_value, fsh_value)), 200
    except TypeError:
        return jsonify({"error": "LH and FSH values are required."}), 400
    except ValueError as error:
        return jsonify({"error": str(error)}), 400
    except Exception as error:
        return jsonify({"error": f"Stage 2 prediction failed: {error}"}), 500


@app.post("/upload-stage2-report")
def upload_stage2_report() -> tuple:
    try:
        report_text = (request.form.get("report_text") or "").strip()
        uploaded_file = request.files.get("report_file")

        if not report_text and uploaded_file is None:
            raise ValueError("Please upload a report file or paste the report text.")

        if not report_text and uploaded_file is not None:
            report_text = extract_report_text_from_upload(uploaded_file)

        extracted = extract_lab_values_from_text(report_text)
        prediction_result = run_stage2_prediction(extracted["lh"], extracted["fsh"])
        prediction_result["report_excerpt"] = report_text[:500]
        return jsonify(prediction_result), 200
    except ValueError as error:
        return jsonify({"error": str(error)}), 400
    except Exception as error:
        return jsonify({"error": f"Stage 2 report analysis failed: {error}"}), 500


if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    debug = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    app.run(host="0.0.0.0", port=port, debug=debug)
