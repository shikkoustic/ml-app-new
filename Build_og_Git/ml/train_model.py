import os
import pickle
import numpy as np
from xgboost import XGBRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from ml.preprocess import get_training_data
from xgboost.callback import EarlyStopping

MODEL_PATH = "/Users/shikkoustic/Desktop/ML Project/Build-og/saved_models/pm25_model.pkl"
FEATURE_PATH = "/Users/shikkoustic/Desktop/ML Project/Build-og/saved_models/feature_columns.pkl"
METRICS_PATH = "/Users/shikkoustic/Desktop/ML Project/Build-og/saved_models/model_metrics.pkl"


def train():

    print("Loading training data...")
    X, y, feature_columns = get_training_data()
    split_index = int(len(X) * 0.8)

    X_train = X.iloc[:split_index]
    y_train = y.iloc[:split_index]

    X_test = X.iloc[split_index:]
    y_test = y.iloc[split_index:]

    print(f"Training samples: {len(X_train)}")
    print(f"Testing samples : {len(X_test)}")

    print("\nTraining XGBoost model...")

    model = XGBRegressor(
        n_estimators=1500,
        learning_rate=0.02,
        max_depth=5,
        min_child_weight=5,
        subsample=0.8,
        colsample_bytree=0.8,
        gamma=0.2,
        reg_alpha=0.2,
        reg_lambda=1.2,
        random_state=42,
        objective="reg:squarederror"
    )

    model.fit(
        X_train,
        y_train)

    preds = model.predict(X_test)

    # reverse log transform
    preds = np.expm1(preds)
    y_test_actual = np.expm1(y_test)

    mae = mean_absolute_error(y_test_actual, preds)
    rmse = np.sqrt(mean_squared_error(y_test_actual, preds))
    r2 = r2_score(y_test_actual, preds)

    print("\nModel Evaluation:")
    print("MAE :", round(mae, 2))
    print("RMSE:", round(rmse, 2))
    print("R2  :", round(r2, 4))

    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)

    with open(MODEL_PATH, "wb") as f:
        pickle.dump(model, f)

    with open(FEATURE_PATH, "wb") as f:
        pickle.dump(feature_columns, f)

    # Save metrics for prediction range
    metrics = {
        "mae": mae,
        "rmse": rmse,
        "r2": r2
    }

    with open(METRICS_PATH, "wb") as f:
        pickle.dump(metrics, f)

    print("\nModel saved successfully.")
    print("Metrics saved successfully.")


if __name__ == "__main__":
    train()