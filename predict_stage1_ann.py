import argparse
from pathlib import Path

import joblib
import pandas as pd


def main() -> None:
    parser = argparse.ArgumentParser(description="Predict PCOS risk using the trained Stage 1 ANN model.")
    parser.add_argument("--age", type=float, required=True, help="Age in years")
    parser.add_argument("--weight", type=float, required=True, help="Weight in Kg")
    parser.add_argument("--bmi", type=float, required=True, help="Body Mass Index")
    parser.add_argument("--cycle_ri", type=float, required=True, help="Cycle type: Regular=2, Irregular=4")
    parser.add_argument("--cycle_length", type=float, required=True, help="Cycle length in dataset encoding")
    parser.add_argument("--weight_gain", type=float, required=True, help="Weight gain: No=0, Yes=1")
    parser.add_argument("--hair_growth", type=float, required=True, help="Hair growth: No=0, Yes=1")
    parser.add_argument("--skin_darkening", type=float, required=True, help="Skin darkening: No=0, Yes=1")
    parser.add_argument("--hair_loss", type=float, required=True, help="Hair loss: No=0, Yes=1")
    parser.add_argument("--pimples", type=float, required=True, help="Pimples: No=0, Yes=1")
    parser.add_argument("--fast_food", type=float, required=True, help="Fast food: No=0, Yes=1")
    parser.add_argument("--reg_exercise", type=float, required=True, help="Regular exercise: No=0, Yes=1")
    parser.add_argument(
        "--model",
        default="artifacts/stage1_ann_model.joblib",
        help="Path to the trained model bundle.",
    )
    args = parser.parse_args()

    model_path = Path(args.model)
    bundle = joblib.load(model_path)
    model = bundle["model"]
    feature_columns = bundle["feature_columns"]
    threshold = float(bundle.get("threshold", 0.5))

    input_frame = pd.DataFrame(
        [
            {
                "Age (yrs)": args.age,
                "Weight (Kg)": args.weight,
                "BMI": args.bmi,
                "Cycle(R/I)": args.cycle_ri,
                "Cycle length(days)": args.cycle_length,
                "Weight gain(Y/N)": args.weight_gain,
                "hair growth(Y/N)": args.hair_growth,
                "Skin darkening (Y/N)": args.skin_darkening,
                "Hair loss(Y/N)": args.hair_loss,
                "Pimples(Y/N)": args.pimples,
                "Fast food (Y/N)": args.fast_food,
                "Reg.Exercise(Y/N)": args.reg_exercise,
            }
        ],
        columns=feature_columns,
    )

    probability = float(model.predict_proba(input_frame)[0][1])
    prediction = int(probability >= threshold)

    print(f"Predicted PCOS risk class: {prediction}")
    print(f"Predicted PCOS probability: {probability:.4f}")
    print(f"Decision threshold: {threshold:.2f}")
    if prediction == 1:
        print("Result: High PCOS risk")
    else:
        print("Result: Low PCOS risk")


if __name__ == "__main__":
    main()
