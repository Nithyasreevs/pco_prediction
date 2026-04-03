# PCOS Stage 1 Full Stack Flow

This project now follows:

`React Frontend -> Flask Backend API -> ANN Model -> Prediction -> React UI`

## Backend

Backend path: `backend/app.py`

Install backend dependencies:

```powershell
python -m pip install -r backend/requirements.txt
```

Run backend:

```powershell
python backend/app.py
```

Backend endpoints:

- `GET /health`
- `POST /predict`

## Frontend

Frontend path: `frontend`

Install frontend dependencies:

```powershell
npm.cmd install
```

Run frontend:

```powershell
npm.cmd run dev
```

Open the local Vite URL shown in the terminal, usually `http://localhost:5173`.

## Request Payload

```json
{
  "age": 28,
  "weight": 65,
  "bmi": 26,
  "cycle_ri": 4,
  "cycle_length": 45,
  "weight_gain": 1,
  "hair_growth": 1,
  "skin_darkening": 1,
  "hair_loss": 1,
  "pimples": 1,
  "fast_food": 1,
  "reg_exercise": 0
}
```

## Output

```json
{
  "prediction": 1,
  "probability": 0.8421,
  "risk_label": "High PCOS risk"
}
```
