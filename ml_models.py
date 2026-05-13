import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
import shap
import joblib

class FillLevelPredictor:
    """
    Predicts bin fill levels using machine learning [citation:8]
    """
    
    def __init__(self):
        self.model = RandomForestRegressor(
            n_estimators=100,
            max_depth=10,
            random_state=42
        )
        self.feature_names = None
        self.shap_explainer = None
    
    def prepare_features(self, historical_data: pd.DataFrame) -> tuple:
        """
        Prepare features from historical bin data
        Features: time of day, day of week, zone, bin type, previous fills
        """
        df = historical_data.copy()
        
        # Time features
        df['hour'] = pd.to_datetime(df['timestamp']).dt.hour
        df['day_of_week'] = pd.to_datetime(df['timestamp']).dt.dayofweek
        df['is_weekend'] = df['day_of_week'].isin([5, 6]).astype(int)
        
        # Zone encoding
        zone_dummies = pd.get_dummies(df['zone'], prefix='zone')
        
        # Bin type encoding
        type_dummies = pd.get_dummies(df['bin_type'], prefix='type')
        
        # Previous fill levels (lag features)
        df['fill_lag_1'] = df.groupby('bin_id')['fill_percentage'].shift(1)
        df['fill_lag_2'] = df.groupby('bin_id')['fill_percentage'].shift(2)
        df['fill_lag_3'] = df.groupby('bin_id')['fill_percentage'].shift(3)
        
        # Fill rate
        df['fill_rate'] = df['fill_lag_1'] - df['fill_lag_2']
        
        # Combine features
        features = pd.concat([
            df[['hour', 'day_of_week', 'is_weekend', 'fill_lag_1', 
                'fill_lag_2', 'fill_lag_3', 'fill_rate']],
            zone_dummies,
            type_dummies
        ], axis=1)
        
        # Drop rows with NaN (from lag features)
        features = features.dropna()
        targets = df.loc[features.index, 'fill_percentage']
        
        return features, targets
    
    def train(self, historical_data: pd.DataFrame):
        """
        Train the prediction model
        """
        X, y = self.prepare_features(historical_data)
        self.feature_names = X.columns.tolist()
        
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )
        
        self.model.fit(X_train, y_train)
        
        # Calculate SHAP values for explainability [citation:8]
        self.shap_explainer = shap.TreeExplainer(self.model)
        
        train_score = self.model.score(X_train, y_train)
        test_score = self.model.score(X_test, y_test)
        
        print(f"Train R²: {train_score:.3f}")
        print(f"Test R²: {test_score:.3f}")
        
        return {
            'train_score': train_score,
            'test_score': test_score,
            'feature_importance': dict(zip(
                self.feature_names,
                self.model.feature_importances_
            ))
        }
    
    def predict(self, current_data: pd.DataFrame) -> np.ndarray:
        """
        Predict future fill levels
        """
        X, _ = self.prepare_features(current_data)
        return self.model.predict(X)
    
    def explain_prediction(self, data_point: pd.DataFrame):
        """
        Explain a single prediction using SHAP [citation:8]
        """
        if self.shap_explainer is None:
            return None
        
        X, _ = self.prepare_features(data_point)
        shap_values = self.shap_explainer.shap_values(X)
        
        return {
            'shap_values': shap_values,
            'base_value': self.shap_explainer.expected_value,
            'features': X
        }
    
    def save_model(self, path: str):
        """Save trained model"""
        joblib.dump({
            'model': self.model,
            'feature_names': self.feature_names,
            'explainer': self.shap_explainer
        }, path)
    
    def load_model(self, path: str):
        """Load trained model"""
        data = joblib.load(path)
        self.model = data['model']
        self.feature_names = data['feature_names']
        self.shap_explainer = data['explainer']