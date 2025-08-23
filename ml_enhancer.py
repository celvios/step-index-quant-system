import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, GradientBoostingRegressor
from sklearn.preprocessing import StandardScaler
import joblib

class StepIndexMLEnhancer:
    def __init__(self):
        self.regime_model = RandomForestClassifier(n_estimators=100)
        self.confluence_model = GradientBoostingRegressor(n_estimators=100)
        self.scaler = StandardScaler()
        self.is_trained = False
    
    def create_features(self, price_data, current_idx):
        """Create ML features from price data"""
        if current_idx < 20:
            return None
            
        prices = price_data['close'].iloc[current_idx-20:current_idx+1]
        
        # Technical features
        atr = prices.rolling(14).std().iloc[-1]
        momentum = (prices.iloc[-1] - prices.iloc[-5]) / prices.iloc[-5]
        volatility = prices.pct_change().rolling(10).std().iloc[-1]
        
        # Step-specific features
        step_count = sum(1 for i in range(len(prices)-1) 
                        if abs(prices.iloc[i+1] - prices.iloc[i]) >= 0.1)
        
        # Time features
        hour = price_data['timestamp'].iloc[current_idx].hour
        
        return np.array([atr, momentum, volatility, step_count, hour])
    
    def predict_market_regime(self, features):
        """Predict market regime: 0=ranging, 1=trending, 2=volatile"""
        if not self.is_trained:
            return 1  # Default to trending
        return self.regime_model.predict([features])[0]
    
    def predict_confluence_adjustment(self, features, base_score):
        """Predict confluence score adjustment"""
        if not self.is_trained:
            return base_score
        adjustment = self.confluence_model.predict([features])[0]
        return max(0, min(100, base_score + adjustment))
    
    def train_models(self, historical_data, trade_outcomes):
        """Train ML models on historical data"""
        features = []
        regimes = []
        adjustments = []
        
        for i in range(20, len(historical_data)):
            feature_vec = self.create_features(historical_data, i)
            if feature_vec is not None:
                features.append(feature_vec)
                
                # Simple regime classification based on volatility
                atr = feature_vec[0]
                if atr < 0.5:
                    regimes.append(0)  # ranging
                elif atr > 1.5:
                    regimes.append(2)  # volatile
                else:
                    regimes.append(1)  # trending
                
                # Mock adjustment based on success rate
                adjustments.append(np.random.normal(0, 5))
        
        if len(features) > 50:
            features = self.scaler.fit_transform(features)
            self.regime_model.fit(features, regimes)
            self.confluence_model.fit(features, adjustments)
            self.is_trained = True
    
    def get_adaptive_parameters(self, features):
        """Get adaptive strategy parameters"""
        regime = self.predict_market_regime(features)
        
        if regime == 0:  # ranging
            return {'min_confluence': 80, 'risk_multiplier': 0.8}
        elif regime == 2:  # volatile
            return {'min_confluence': 85, 'risk_multiplier': 0.6}
        else:  # trending
            return {'min_confluence': 75, 'risk_multiplier': 1.0}

# Enhanced Step Index System with ML
class MLEnhancedStepSystem:
    def __init__(self, base_system):
        self.base_system = base_system
        self.ml_enhancer = StepIndexMLEnhancer()
    
    def enhanced_confluence_score(self, price_data, current_idx, base_score):
        """Calculate ML-enhanced confluence score"""
        features = self.ml_enhancer.create_features(price_data, current_idx)
        if features is None:
            return base_score
        
        # Get adaptive parameters
        params = self.ml_enhancer.get_adaptive_parameters(features)
        
        # Adjust confluence score
        enhanced_score = self.ml_enhancer.predict_confluence_adjustment(features, base_score)
        
        return enhanced_score, params
    
    def should_enter_trade(self, enhanced_score, adaptive_params):
        """Determine if trade should be entered with ML enhancement"""
        min_confluence = adaptive_params.get('min_confluence', 75)
        return enhanced_score >= min_confluence