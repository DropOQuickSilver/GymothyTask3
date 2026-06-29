import os
import joblib
import pandas as pd

from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, PolynomialFeatures, StandardScaler


class StrengthPredictor:
        """
        Gymothy's OOP machine learning model.

        This class trains, evaluates, saves, loads and uses a supervised
        regression model to predict a user's next estimated 1RM.
        """

        REQUIRED_COLUMNS = [
            "lift_name",
            "session_number",
            "estimated_1rm",
            "volume",
            "avg_rpe",
            "days_since_last_session",
            "next_estimated_1rm"
        ]

        FEATURE_COLUMNS = [
            "lift_name",
            "session_number",
            "estimated_1rm",
            "volume",
            "avg_rpe",
            "days_since_last_session"
        ]

        NUMERIC_FEATURES = [
            "session_number",
            "estimated_1rm",
            "volume",
            "avg_rpe",
            "days_since_last_session"
        ]

        CATEGORICAL_FEATURES = ["lift_name"]

        def __init__(self, model_path="ml/saved_models/strength_predictor.joblib"):
            self.model_path = model_path
            self.model = None
            self.metrics = {}

        def load_training_data(self, csv_path):
            data = pd.read_csv(csv_path)

            missing_columns = [
                column for column in self.REQUIRED_COLUMNS
                if column not in data.columns
            ]

            if missing_columns:
                raise ValueError(f"Training data is missing columns: {missing_columns}")

            data = data.dropna()

            data = data[data["estimated_1rm"] > 0]
            data = data[data["next_estimated_1rm"] > 0]
            data = data[data["volume"] >= 0]
            data = data[(data["avg_rpe"] >= 1) & (data["avg_rpe"] <= 10)]
            data = data[data["days_since_last_session"] >= 0]

            return data

        def create_model(self, degree):
            numeric_pipeline = Pipeline([
                ("scaler", StandardScaler()),
                ("polynomial", PolynomialFeatures(degree=degree, include_bias=False))
            ])

            preprocessor = ColumnTransformer([
                ("numeric", numeric_pipeline, self.NUMERIC_FEATURES),
                ("lift", OneHotEncoder(handle_unknown="ignore"), self.CATEGORICAL_FEATURES)
            ])

            model = Pipeline([
                ("preprocessor", preprocessor),
                ("regressor", LinearRegression())
            ])

            return model

        def train(self, csv_path):
            data = self.load_training_data(csv_path)

            if len(data) < 12:
                raise ValueError("Not enough training records. At least 12 valid records are required.")

            X = data[self.FEATURE_COLUMNS]
            y = data["next_estimated_1rm"]

            X_train, X_test, y_train, y_test = train_test_split(
                X,
                y,
                test_size=0.25,
                random_state=42
            )

            candidate_models = {
                "Linear Regression": self.create_model(degree=1),
                "Polynomial Regression": self.create_model(degree=2)
            }

            results = {}

            for model_name, model in candidate_models.items():
                model.fit(X_train, y_train)
                predictions = model.predict(X_test)

                results[model_name] = {
                    "model": model,
                    "mae": round(float(mean_absolute_error(y_test, predictions)), 2),
                    "r2": round(float(r2_score(y_test, predictions)), 3)
                }

            best_model_name = min(results, key=lambda name: results[name]["mae"])
            best_result = results[best_model_name]

            self.model = best_result["model"]
            self.metrics = {
                "model_type": best_model_name,
                "records_used": int(len(data)),
                "mae": best_result["mae"],
                "r2": best_result["r2"],
                "linear_mae": results["Linear Regression"]["mae"],
                "polynomial_mae": results["Polynomial Regression"]["mae"]
            }

            return self.metrics

        def save_model(self):
            if self.model is None:
                raise ValueError("No trained model exists. Train the model before saving.")

            os.makedirs(os.path.dirname(self.model_path), exist_ok=True)

            payload = {
                "model": self.model,
                "metrics": self.metrics,
                "feature_columns": self.FEATURE_COLUMNS
            }

            joblib.dump(payload, self.model_path)

        def load_model(self):
            if not os.path.exists(self.model_path):
                raise FileNotFoundError("Saved model file was not found. Train the model first.")

            payload = joblib.load(self.model_path)
            self.model = payload["model"]
            self.metrics = payload.get("metrics", {})
            return self.model

        def predict_next_1rm(self, features):
            if self.model is None:
                self.load_model()

            clean_features = {
                "lift_name": str(features["lift_name"]),
                "session_number": int(features["session_number"]),
                "estimated_1rm": float(features["estimated_1rm"]),
                "volume": float(features["volume"]),
                "avg_rpe": float(features["avg_rpe"]),
                "days_since_last_session": int(features["days_since_last_session"])
            }

            input_data = pd.DataFrame([clean_features], columns=self.FEATURE_COLUMNS)

            model = self.model

            if model is None:
                raise RuntimeError("Strength prediction model could not be loaded.")

            prediction = model.predict(input_data)[0]

            return round(float(prediction), 2)

        def interpret_prediction(self, current_1rm, predicted_1rm):
            change = predicted_1rm - current_1rm
            percent_change = (change / current_1rm) * 100 if current_1rm > 0 else 0

            if percent_change >= 2.5:
                trend = "Improving"
            elif percent_change <= -2.5:
                trend = "Declining"
            else:
                trend = "Stable"

            return {
                "change": round(change, 2),
                "percent_change": round(percent_change, 2),
                "trend": trend
            }