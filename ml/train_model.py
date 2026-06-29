from ml.strength_predictor import StrengthPredictor


def main():
    predictor = StrengthPredictor()

    metrics = predictor.train("ml/training_data.csv")
    predictor.save_model()

    print("Gymothy Strength Predictor trained successfully.")
    print(f"Selected model: {metrics['model_type']}")
    print(f"Records used: {metrics['records_used']}")
    print(f"Linear Regression MAE: {metrics['linear_mae']} kg")
    print(f"Polynomial Regression MAE: {metrics['polynomial_mae']} kg")
    print(f"Selected model MAE: {metrics['mae']} kg")
    print(f"Selected model R² Score: {metrics['r2']}")


if __name__ == "__main__":
    main()