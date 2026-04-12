import io
import os
import re
from datetime import date, datetime, timedelta
from pathlib import Path

import fitz
import joblib
import pandas as pd
import pytesseract
from flask import Flask, jsonify, request
from flask_cors import CORS
from PIL import Image, ImageOps, ImageFilter
from werkzeug.security import check_password_hash, generate_password_hash

try:
    from bson import ObjectId
    from pymongo import MongoClient
    from pymongo.errors import PyMongoError
except Exception:
    ObjectId = None
    MongoClient = None
    PyMongoError = Exception

BASE_DIR = Path(__file__).resolve().parent.parent
STAGE1_MODEL_PATH = BASE_DIR / "artifacts" / "stage1_ann_model.joblib"
STAGE2_MODEL_PATH = BASE_DIR / "artifacts" / "stage2_ann_model.joblib"
STAGE3_MODEL_PATH = BASE_DIR / "artifacts" / "stage3_ann_model.joblib"


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

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/pco")
mongo_client = MongoClient(MONGO_URI) if MongoClient is not None else None
tracker_db = mongo_client.get_default_database() if mongo_client is not None else None
users_collection = tracker_db["users"] if tracker_db is not None else None


def require_tracker_db() -> None:
    if users_collection is None or ObjectId is None:
        raise ValueError("MongoDB support is not available. Please install pymongo and bson dependencies.")


def parse_tracker_date(value: str) -> date:
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except Exception as error:
        raise ValueError("Dates must be in YYYY-MM-DD format.") from error


def calculate_cycle_dates(last_period_date: date, cycle_length: int) -> dict:
    next_period = last_period_date + timedelta(days=cycle_length)
    ovulation = next_period - timedelta(days=14)
    fertile_start = ovulation - timedelta(days=2)
    fertile_end = ovulation + timedelta(days=2)
    return {
        "last_period_date": last_period_date.isoformat(),
        "next_period_date": next_period.isoformat(),
        "ovulation_date": ovulation.isoformat(),
        "fertile_window": {
            "start": fertile_start.isoformat(),
            "end": fertile_end.isoformat(),
        },
        "cycle_length": cycle_length,
    }


def compute_cycle_consistency(profile: dict, cycle_history: list[dict]) -> dict:
    lengths = [entry.get("cycle_length") for entry in cycle_history if isinstance(entry.get("cycle_length"), int)]
    if lengths:
        average_length = round(sum(lengths) / len(lengths), 1)
        return {
            "average_cycle_length": average_length,
            "message": f"Your recent cycle average is around {average_length} days.",
        }

    cycle_length = profile.get("cycle_length")
    if not cycle_length:
        return {
            "average_cycle_length": None,
            "message": "Add your cycle details to see consistency insight.",
        }

    average_length = round(float(cycle_length), 1)
    return {
        "average_cycle_length": average_length,
        "message": f"Your cycle is currently tracked at around {average_length} days.",
    }


def generate_health_insight(flow: str, discharge: str) -> str:
    flow_key = (flow or "").strip().lower()
    discharge_key = (discharge or "").strip().lower()

    if flow_key == "heavy" and discharge_key in {"yellow", "brown", "pink"}:
        return "Heavy flow with colored discharge may indicate hormonal imbalance or infection. Monitor it closely and consult a doctor if it continues."
    if flow_key == "heavy" and discharge_key == "cottage cheese":
        return "Heavy flow with cottage-cheese-like discharge may suggest irritation or infection. A clinical review would be a good next step."
    if flow_key == "light" and discharge_key == "clear":
        return "A light flow with clear discharge can still be normal. Keep tracking your cycle pattern and any changes month to month."
    if discharge_key == "thick white":
        return "Thick white discharge can be normal for some women, but if it is accompanied by discomfort or odor, consider consulting a doctor."
    if discharge_key == "creamy":
        return "Creamy discharge is often seen around normal hormonal changes. Continue tracking to understand your regular pattern."
    return "Your current symptom pattern should be monitored. If the flow or discharge changes continue or feel unusual, seek medical advice."


def serialize_tracker_user(user_doc: dict) -> dict:
    profile = user_doc.get("profile") or {}
    cycle_history = user_doc.get("cycle_history") or []
    latest_insight = user_doc.get("latest_insight") or {}
    consistency = compute_cycle_consistency(profile, cycle_history)
    cycle_summary = calculate_cycle_dates(
        parse_tracker_date(profile["last_period_date"]),
        int(profile["cycle_length"]),
    ) if profile.get("last_period_date") and profile.get("cycle_length") else None

    calendar_dates = []
    if cycle_summary is not None:
        calendar_dates = [
            cycle_summary["last_period_date"],
            cycle_summary["next_period_date"],
            cycle_summary["ovulation_date"],
            cycle_summary["fertile_window"]["start"],
            cycle_summary["fertile_window"]["end"],
        ]

    return {
        "user_id": str(user_doc["_id"]),
        "name": user_doc.get("name", ""),
        "email": user_doc.get("email", ""),
        "profile": profile,
        "cycle_summary": cycle_summary,
        "cycle_history": cycle_history,
        "history_insight": consistency,
        "latest_insight": latest_insight,
        "calendar_dates": calendar_dates,
    }


def get_tracker_user(user_id: str) -> dict:
    require_tracker_db()
    try:
        object_id = ObjectId(user_id)
    except Exception as error:
        raise ValueError("Invalid user id.") from error

    user_doc = users_collection.find_one({"_id": object_id})
    if not user_doc:
        raise ValueError("User not found.")
    return user_doc

stage1_bundle = joblib.load(STAGE1_MODEL_PATH)
stage1_model = stage1_bundle["model"]
stage1_feature_columns = stage1_bundle["feature_columns"]
stage1_threshold = float(stage1_bundle.get("threshold", 0.5))

stage2_bundle = joblib.load(STAGE2_MODEL_PATH) if STAGE2_MODEL_PATH.exists() else None
stage2_model = stage2_bundle["model"] if stage2_bundle else None
stage2_feature_columns = stage2_bundle["feature_columns"] if stage2_bundle else ["LH(mIU/mL)", "FSH(mIU/mL)", "LH_FSH_Ratio"]
stage2_threshold = float(stage2_bundle.get("threshold", 0.5)) if stage2_bundle else 0.5

stage3_bundle = joblib.load(STAGE3_MODEL_PATH) if STAGE3_MODEL_PATH.exists() else None
stage3_model = stage3_bundle["model"] if stage3_bundle else None
stage3_feature_columns = stage3_bundle["feature_columns"] if stage3_bundle else ["Age", "Weight", "Height", "BMI", "FSH", "LH", "LH_FSH_Ratio", "TSH", "AMH", "Cycle_Length", "Cycle_Regular", "Weight_Gain", "Hair_Growth", "Skin_Darkening", "Hair_Loss", "Pimples", "Fast_Food", "Exercise", "Follicle_Left", "Follicle_Right"]
stage3_threshold = float(stage3_bundle.get("threshold", 0.5)) if stage3_bundle else 0.5

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

STAGE3_FIELD_LABELS = {
    "age": "Age",
    "weight": "Weight",
    "height": "Height",
    "bmi": "BMI",
    "fsh": "FSH",
    "lh": "LH",
    "lh_fsh_ratio": "LH_FSH_Ratio",
    "tsh": "TSH",
    "amh": "AMH",
    "cycle_length": "Cycle_Length",
    "cycle_regular": "Cycle_Regular",
    "weight_gain": "Weight_Gain",
    "hair_growth": "Hair_Growth",
    "skin_darkening": "Skin_Darkening",
    "hair_loss": "Hair_Loss",
    "pimples": "Pimples",
    "fast_food": "Fast_Food",
    "exercise": "Exercise",
    "follicle_left": "Follicle_Left",
    "follicle_right": "Follicle_Right",
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


def build_stage3_input_frame(payload: dict) -> pd.DataFrame:
    row = {}
    missing_fields = []

    lh_value = float(payload.get("lh", 0) or 0)
    fsh_value = float(payload.get("fsh", 0) or 0)
    computed_ratio = lh_value / fsh_value if fsh_value not in (0, 0.0) else 0.0

    for api_field, model_field in STAGE3_FIELD_LABELS.items():
        if api_field == "lh_fsh_ratio":
            row[model_field] = float(payload.get(api_field, computed_ratio) or computed_ratio)
            continue
        if api_field not in payload:
            missing_fields.append(api_field)
            continue
        row[model_field] = float(payload[api_field])

    if missing_fields:
        raise ValueError(f"Missing required fields: {', '.join(missing_fields)}")

    return pd.DataFrame([row], columns=stage3_feature_columns)


def run_stage3_prediction(payload: dict) -> dict:
    if stage3_model is None:
        raise ValueError("Stage 3 model is not trained yet. Run train_stage3_ann.py first.")

    input_frame = build_stage3_input_frame(payload)
    probability = float(stage3_model.predict_proba(input_frame)[0][1])
    prediction = int(probability >= stage3_threshold)
    return {
        "prediction": prediction,
        "probability": round(probability, 4),
        "threshold": round(stage3_threshold, 2),
        "risk_label": "High PCOS risk" if prediction == 1 else "Low PCOS risk",
    }


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


STAGE3_REPORT_PATTERNS = {
    "lh": [
        r"\bLH\b[^0-9]*([0-9]+(?:\.[0-9]+)?)",
    ],
    "fsh": [
        r"\bFSH\b[^0-9]*([0-9]+(?:\.[0-9]+)?)",
    ],
    "tsh": [
        r"\bTSH\b[^0-9]*([0-9]+(?:\.[0-9]+)?)",
    ],
    "amh": [
        r"\bAMH\b[^0-9]*([0-9]+(?:\.[0-9]+)?)",
    ],
    "follicle_left": [
        r"Follicle\s*No\.?\s*\(\s*Left\s*Ovary\s*\)[^0-9]*([0-9]+(?:\.[0-9]+)?)",
        r"Follicle\s*\(?L\)?[^0-9]*([0-9]+(?:\.[0-9]+)?)",
        r"Left\s*Ovary[^0-9]*([0-9]+(?:\.[0-9]+)?)",
    ],
    "follicle_right": [
        r"Follicle\s*No\.?\s*\(\s*Right\s*Ovary\s*\)[^0-9]*([0-9]+(?:\.[0-9]+)?)",
        r"Follicle\s*\(?R\)?[^0-9]*([0-9]+(?:\.[0-9]+)?)",
        r"Right\s*Ovary[^0-9]*([0-9]+(?:\.[0-9]+)?)",
    ],
}


def extract_stage3_values_from_text(report_text: str) -> dict:
    normalized_text = re.sub(r"\s+", " ", report_text)
    extracted = {}

    for field_name, patterns in STAGE3_REPORT_PATTERNS.items():
        for pattern in patterns:
            match = re.search(pattern, normalized_text, flags=re.IGNORECASE)
            if match:
                extracted[field_name] = float(match.group(1))
                break

    if "lh" in extracted and "fsh" in extracted and extracted["fsh"] not in (0, 0.0):
        extracted["lh_fsh_ratio"] = round(extracted["lh"] / extracted["fsh"], 4)

    if not extracted:
        raise ValueError(
            "Could not extract Stage 3 report values from the uploaded files. Please upload clearer reports or enter the values manually."
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


def collect_report_text(request_form, file_field_name: str, max_files: int = 1) -> str:
    report_text = (request_form.form.get("report_text") or "").strip()
    uploaded_files = [file for file in request_form.files.getlist(file_field_name) if file and (file.filename or "").strip()]

    if not report_text and not uploaded_files:
        raise ValueError("Please upload a report file or paste the report text.")

    if len(uploaded_files) > max_files:
        raise ValueError(f"Please upload at most {max_files} report files.")

    extracted_parts = []
    if report_text:
        extracted_parts.append(report_text)

    for uploaded_file in uploaded_files:
        extracted_parts.append(extract_report_text_from_upload(uploaded_file))

    return "\n".join(part for part in extracted_parts if part).strip()


@app.get("/health")
def health() -> tuple:
    return jsonify({
        "status": "ok",
        "stage1_model_loaded": STAGE1_MODEL_PATH.exists(),
        "stage2_model_loaded": STAGE2_MODEL_PATH.exists(),
        "stage3_model_loaded": STAGE3_MODEL_PATH.exists(),
        "tesseract_configured": TESSERACT_PATH is not None,
        "stage1_threshold": stage1_threshold,
        "stage2_threshold": stage2_threshold,
        "stage3_threshold": stage3_threshold,
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


@app.post("/predict-stage3")
def predict_stage3() -> tuple:
    try:
        payload = request.get_json(silent=True) or {}
        return jsonify(run_stage3_prediction(payload)), 200
    except ValueError as error:
        return jsonify({"error": str(error)}), 400
    except Exception as error:
        return jsonify({"error": f"Stage 3 prediction failed: {error}"}), 500


@app.post("/upload-stage2-report")
def upload_stage2_report() -> tuple:
    try:
        report_text = collect_report_text(request, "report_file", max_files=1)
        extracted = extract_lab_values_from_text(report_text)
        prediction_result = run_stage2_prediction(extracted["lh"], extracted["fsh"])
        prediction_result["report_excerpt"] = report_text[:500]
        return jsonify(prediction_result), 200
    except ValueError as error:
        return jsonify({"error": str(error)}), 400
    except Exception as error:
        return jsonify({"error": f"Stage 2 report analysis failed: {error}"}), 500


@app.post("/upload-stage3-report")
def upload_stage3_report() -> tuple:
    try:
        report_text = collect_report_text(request, "report_files", max_files=3)
        extracted = extract_stage3_values_from_text(report_text)
        return jsonify({
            "extracted_values": extracted,
            "report_excerpt": report_text[:1000],
        }), 200
    except ValueError as error:
        return jsonify({"error": str(error)}), 400
    except Exception as error:
        return jsonify({"error": f"Stage 3 report analysis failed: {error}"}), 500


@app.post("/tracker/signup")
def tracker_signup() -> tuple:
    try:
        require_tracker_db()
        payload = request.get_json(silent=True) or {}
        name = (payload.get("name") or "").strip()
        email = (payload.get("email") or "").strip().lower()
        password = payload.get("password") or ""

        if not name or not email or not password:
            raise ValueError("Name, email, and password are required.")
        if users_collection.find_one({"email": email}):
            raise ValueError("An account with this email already exists.")

        document = {
            "name": name,
            "email": email,
            "password_hash": generate_password_hash(password),
            "profile": {},
            "created_at": datetime.utcnow(),
        }
        inserted = users_collection.insert_one(document)
        user_doc = users_collection.find_one({"_id": inserted.inserted_id})
        return jsonify(serialize_tracker_user(user_doc)), 201
    except ValueError as error:
        return jsonify({"error": str(error)}), 400
    except PyMongoError as error:
        return jsonify({"error": f"MongoDB error: {error}"}), 500
    except Exception as error:
        return jsonify({"error": f"Tracker signup failed: {error}"}), 500


@app.post("/tracker/login")
def tracker_login() -> tuple:
    try:
        require_tracker_db()
        payload = request.get_json(silent=True) or {}
        email = (payload.get("email") or "").strip().lower()
        password = payload.get("password") or ""
        if not email or not password:
            raise ValueError("Email and password are required.")

        user_doc = users_collection.find_one({"email": email})
        if not user_doc or not check_password_hash(user_doc.get("password_hash", ""), password):
            raise ValueError("Invalid email or password.")

        return jsonify(serialize_tracker_user(user_doc)), 200
    except ValueError as error:
        return jsonify({"error": str(error)}), 400
    except PyMongoError as error:
        return jsonify({"error": f"MongoDB error: {error}"}), 500
    except Exception as error:
        return jsonify({"error": f"Tracker login failed: {error}"}), 500


@app.get("/tracker/dashboard/<user_id>")
def tracker_dashboard(user_id: str) -> tuple:
    try:
        user_doc = get_tracker_user(user_id)
        return jsonify(serialize_tracker_user(user_doc)), 200
    except ValueError as error:
        return jsonify({"error": str(error)}), 400
    except PyMongoError as error:
        return jsonify({"error": f"MongoDB error: {error}"}), 500
    except Exception as error:
        return jsonify({"error": f"Dashboard load failed: {error}"}), 500


@app.post("/tracker/profile/<user_id>")
def tracker_save_profile(user_id: str) -> tuple:
    try:
        payload = request.get_json(silent=True) or {}
        name = (payload.get("name") or "").strip()
        height = float(payload.get("height"))
        weight = float(payload.get("weight"))
        cycle_length = int(payload.get("cycle_length") or 28)
        last_period_date = parse_tracker_date(payload.get("last_period_date"))
        if cycle_length <= 0:
            raise ValueError("Cycle length must be greater than zero.")

        user_doc = get_tracker_user(user_id)
        flow_duration_days = int(payload.get("flow_duration_days") or 0)
        if flow_duration_days <= 0:
            raise ValueError("Menstrual flow duration must be greater than zero.")

        profile = {
            "name": name or user_doc.get("name", ""),
            "height": height,
            "weight": weight,
            "cycle_length": cycle_length,
            "flow_duration_days": flow_duration_days,
            "last_period_date": last_period_date.isoformat(),
        }
        existing_history = user_doc.get("cycle_history") or []
        initial_entry = {
            "period_start": last_period_date.isoformat(),
            "cycle_length": cycle_length,
            "flow_duration_days": flow_duration_days,
            "source": "profile_setup",
        }
        if not existing_history or existing_history[-1].get("period_start") != initial_entry["period_start"]:
            existing_history.append(initial_entry)

        users_collection.update_one(
            {"_id": user_doc["_id"]},
            {
                "$set": {
                    "name": profile["name"],
                    "profile": profile,
                    "cycle_history": existing_history,
                    "updated_at": datetime.utcnow(),
                },
                "$unset": {
                    "latest_insight": "",
                    "symptom_history": "",
                },
            },
        )
        updated = get_tracker_user(user_id)
        return jsonify(serialize_tracker_user(updated)), 200
    except ValueError as error:
        return jsonify({"error": str(error)}), 400
    except PyMongoError as error:
        return jsonify({"error": f"MongoDB error: {error}"}), 500
    except Exception as error:
        return jsonify({"error": f"Profile save failed: {error}"}), 500


@app.post("/tracker/period-started/<user_id>")
def tracker_period_started(user_id: str) -> tuple:
    try:
        payload = request.get_json(silent=True) or {}
        period_date = parse_tracker_date(payload.get("period_start_date"))
        user_doc = get_tracker_user(user_id)
        profile = user_doc.get("profile") or {}
        cycle_length = int(profile.get("cycle_length") or 28)

        last_stored = profile.get("last_period_date")
        if last_stored:
            previous_date = parse_tracker_date(last_stored)
            detected_cycle_length = (period_date - previous_date).days
            if detected_cycle_length > 0:
                cycle_length = detected_cycle_length

        existing_history = user_doc.get("cycle_history") or []
        new_entry = {
            "period_start": period_date.isoformat(),
            "cycle_length": cycle_length,
            "flow_duration_days": int(profile.get("flow_duration_days") or 0),
            "source": "period_started",
        }
        if not existing_history or existing_history[-1].get("period_start") != new_entry["period_start"]:
            existing_history.append(new_entry)

        users_collection.update_one(
            {"_id": user_doc["_id"]},
            {
                "$set": {
                    "profile.last_period_date": period_date.isoformat(),
                    "profile.cycle_length": cycle_length,
                    "profile.flow_duration_days": int(profile.get("flow_duration_days") or 0),
                    "cycle_history": existing_history,
                    "updated_at": datetime.utcnow(),
                },
            },
        )
        updated = get_tracker_user(user_id)
        return jsonify(serialize_tracker_user(updated)), 200
    except ValueError as error:
        return jsonify({"error": str(error)}), 400
    except PyMongoError as error:
        return jsonify({"error": f"MongoDB error: {error}"}), 500
    except Exception as error:
        return jsonify({"error": f"Period tracking failed: {error}"}), 500


@app.post("/tracker/symptoms/<user_id>")
def tracker_symptoms(user_id: str) -> tuple:
    try:
        payload = request.get_json(silent=True) or {}
        flow = (payload.get("flow") or "").strip()
        discharge = (payload.get("discharge") or "").strip()
        if not flow or not discharge:
            raise ValueError("Flow and discharge are required.")

        insight = {
            "flow": flow,
            "discharge": discharge,
            "message": generate_health_insight(flow, discharge),
            "recorded_at": datetime.utcnow().isoformat(),
        }
        user_doc = get_tracker_user(user_id)
        users_collection.update_one(
            {"_id": user_doc["_id"]},
            {
                "$set": {"updated_at": datetime.utcnow()},
                "$unset": {
                    "latest_insight": "",
                    "symptom_history": "",
                },
            },
        )
        data = serialize_tracker_user(user_doc)
        data["latest_insight"] = insight
        data["insight"] = insight
        return jsonify(data), 200
    except ValueError as error:
        return jsonify({"error": str(error)}), 400
    except PyMongoError as error:
        return jsonify({"error": f"MongoDB error: {error}"}), 500
    except Exception as error:
        return jsonify({"error": f"Symptom insight failed: {error}"}), 500


if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    debug = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    app.run(host="0.0.0.0", port=port, debug=debug)
