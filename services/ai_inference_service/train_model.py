from pathlib import Path

import joblib
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder


# Locate the project folder and Excel dataset.
current_file = Path(__file__).resolve()
project_root = current_file.parents[2]
dataset_path = project_root / "test_data.xlsx"

# Load data from the correct Excel sheet.
data = pd.read_excel(
    dataset_path,
    sheet_name="Telemetry Data"
)

print("Dataset loaded successfully.")
print(f"Number of rows: {len(data)}")
print(f"Number of columns: {len(data.columns)}")
print()

print("Columns found:")
print(data.columns.tolist())
print()

# Car plate is only an identifier and should not be used for prediction.
data = data.drop(columns=["Car_Plate"])

# Remove rows containing missing values.
data = data.dropna()

# The value that the AI model must predict.
target_column = "Maintenance_Decision"

# Separate inputs from the target output.
X = data.drop(columns=[target_column])
y = data[target_column]

# Car model is text, while the remaining inputs are numbers.
categorical_features = ["Car_Model"]

numerical_features = [
    "Vehicle_Age_Years",
    "Total_Mileage_KM",
    "Tire_Pressure_PSI",
    "Engine_RPM",
    "Battery_Voltage_V",
    "Fuel_Level_Percent",
    "Coolant_Temperature_C",
    "Brake_Pad_Thickness_mm",
    "O2_Sensor_Voltage_V",
]

# Convert the text-based car model into numerical data.
preprocessor = ColumnTransformer(
    transformers=[
        (
            "car_model_encoder",
            OneHotEncoder(handle_unknown="ignore"),
            categorical_features,
        ),
        (
            "numerical_data",
            "passthrough",
            numerical_features,
        ),
    ]
)

# Create the Random Forest classification model.
classifier = RandomForestClassifier(
    n_estimators=200,
    random_state=42,
    class_weight="balanced",
)

# Combine data processing and model training into one pipeline.
model_pipeline = Pipeline(
    steps=[
        ("preprocessor", preprocessor),
        ("classifier", classifier),
    ]
)

# Split the data: 80% for training and 20% for testing.
X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.20,
    random_state=42,
    stratify=y,
)

# Train the AI model.
model_pipeline.fit(X_train, y_train)

# Test the trained model.
predictions = model_pipeline.predict(X_test)

accuracy = accuracy_score(y_test, predictions)

print(f"Training records: {len(X_train)}")
print(f"Testing records: {len(X_test)}")
print()
print(f"Model accuracy: {accuracy:.2%}")
print()
print("Classification report:")
print(classification_report(y_test, predictions))

# Save the full pipeline.
model_output_path = current_file.parent / "vehicle_maintenance_model.pkl"

joblib.dump(model_pipeline, model_output_path)

print()
print("Model training completed successfully.")
print(f"Model saved to: {model_output_path}")