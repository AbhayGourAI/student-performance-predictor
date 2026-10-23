from pathlib import Path
import numpy as np
import joblib
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, r2_score

FEATURES = ["study_hours", "attendance", "previous_score", "sleep_hours"]

def main():
    rng = np.random.default_rng(42)
    n = 1200
    study_hours = rng.uniform(0, 12, n)
    attendance = rng.uniform(40, 100, n)
    previous_score = rng.uniform(25, 100, n)
    sleep_hours = rng.uniform(4, 10, n)

    # Synthetic teaching data only; this is not a validated educational model.
    noise = rng.normal(0, 5, n)
    score = (
        0.48 * previous_score
        + 2.15 * study_hours
        + 0.20 * attendance
        + 1.15 * sleep_hours
        - 12
        + noise
    )
    score = np.clip(score, 0, 100)

    X = np.column_stack([study_hours, attendance, previous_score, sleep_hours])
    X_train, X_test, y_train, y_test = train_test_split(
        X, score, test_size=0.2, random_state=42
    )

    model = RandomForestRegressor(n_estimators=180, random_state=42, min_samples_leaf=3)
    model.fit(X_train, y_train)
    predictions = model.predict(X_test)

    out = Path(__file__).resolve().parent / "model.joblib"
    joblib.dump({"model": model, "features": FEATURES}, out)
    print(f"Saved model to: {out}")
    print(f"Demo holdout MAE: {mean_absolute_error(y_test, predictions):.2f} points")
    print(f"Demo holdout R²: {r2_score(y_test, predictions):.3f}")
    print("Reminder: metrics are only for synthetic demonstration data.")

if __name__ == "__main__":
    main()
