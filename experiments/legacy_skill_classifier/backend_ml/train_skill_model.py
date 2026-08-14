import pandas as pd
import joblib

from pathlib import Path
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report

BASE = Path(__file__).resolve().parents[2]
DATA = BASE / "data"
MODEL_DIR = BASE / "backend" / "ml" / "models"

MODEL_DIR.mkdir(parents=True, exist_ok=True)

# Load training data
df = pd.read_csv(DATA / "training_dataset.csv")

features = [
    "course_count",
    "avg_marks",
    "project_count",
    "project_stars",
    "avg_complexity"
]

X = df[features]

# Training target based on existing evidence.
# Assessment is NOT used to detect the skill.
y = (
    (
        (df["course_count"] > 0) |
        (df["project_count"] > 0)
    )
    &
    (
        (df["avg_marks"] >= 60) |
        (df["project_count"] >= 1)
    )
).astype(int)

# Split data
X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.2,
    random_state=42,
    stratify=y
)

# Train model
model = RandomForestClassifier(
    n_estimators=200,
    max_depth=10,
    random_state=42,
    class_weight="balanced"
)

model.fit(X_train, y_train)

# Evaluate
predictions = model.predict(X_test)

accuracy = accuracy_score(y_test, predictions)

print("\n==============================")
print("Skill Detection Model")
print("==============================")
print(f"Accuracy: {accuracy:.2%}")
print("==============================")

print(
    classification_report(
        y_test,
        predictions,
        zero_division=0
    )
)

# Feature importance
print("\nFeature Importance:")

for feature, importance in zip(
    features,
    model.feature_importances_
):
    print(
        f"{feature:25} "
        f"{importance:.3f}"
    )

# Save model
model_path = MODEL_DIR / "skill_detection_model.joblib"

joblib.dump(
    {
        "model": model,
        "features": features
    },
    model_path
)

print(f"\nModel saved to:")
print(model_path)