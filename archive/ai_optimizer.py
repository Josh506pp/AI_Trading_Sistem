#!/usr/bin/env python3
"""
Optimización de IA para Sistema de Trading
Reentrenamiento con R-múltiplos para maximizar rentabilidad ajustada al riesgo
"""

import logging
import numpy as np
import pandas as pd
from typing import List, Tuple, Dict, Optional
from datetime import datetime
from sklearn.preprocessing import StandardScaler
from sklearn.neural_network import MLPRegressor, MLPClassifier
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import cross_val_score, train_test_split
import pickle
import os

logger = logging.getLogger(__name__)

# =============================================================================
# CONFIGURACIÓN
# =============================================================================
MODEL_SAVE_DIR = "./models"
if not os.path.exists(MODEL_SAVE_DIR):
    os.makedirs(MODEL_SAVE_DIR)


# =============================================================================
# AI OPTIMIZER
# =============================================================================
class AIOptimizer:
    """
    Reentrenamiento de modelos IA basado en nuevo sistema de puntos
    Optimiza para maximizar R-múltiplos (no solo win rate)
    """
    
    def __init__(self, model_type: str = 'neural_network'):
        """
        model_type: 'neural_network' o 'random_forest'
        """
        self.model_type = model_type
        self.model = None
        self.scaler = StandardScaler()
        self.training_history = []
        self.performance_metrics = {}
    
    def prepare_training_data(
        self,
        trade_history: List[Dict],
        price_data: pd.DataFrame,
        feature_extractor
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Prepara datos de entrenamiento donde:
        - X = Features técnicos en momento de entrada
        - Y = R-múltiples realizados (no 0/1 ganancia/pérdida)
        
        Esto hace que el modelo aprenda a MAXIMIZAR BENEFICIO AJUSTADO AL RIESGO
        no solo a ganar trades
        """
        
        X_list = []
        Y_list = []
        
        logger.info(f"Preparing training data from {len(trade_history)} trades")
        
        for trade in trade_history:
            try:
                # Obtener tiempo de entrada
                entry_time = trade.get('entry_time')
                if entry_time is None:
                    continue
                
                # Buscar en price_data cerca de entry_time
                entry_row = None
                if isinstance(entry_time, datetime):
                    # Buscar por timestamp
                    for idx, row in price_data.iterrows():
                        if abs((row['time'] - entry_time).total_seconds()) < 60:
                            entry_row = row
                            break
                
                if entry_row is None:
                    # Intentar usar índice si es numérico
                    entry_idx = trade.get('entry_index', 0)
                    if entry_idx < len(price_data):
                        entry_row = price_data.iloc[entry_idx]
                    else:
                        continue
                
                # Extraer features técnicos en el momento de entrada
                if 'prices' in price_data.columns:
                    prices = price_data['prices'].values
                    entry_price_idx = price_data.index.get_loc(entry_row.name) if entry_row.name in price_data.index else len(price_data)-1
                    prices_at_entry = prices[:max(entry_price_idx, 50)]
                else:
                    continue
                
                features = feature_extractor.extract_features(prices_at_entry)
                
                # Convertir features a array
                features_array = np.array([
                    features.trend_strength,
                    float(features.sma_crossover),
                    features.rsi / 100,  # Normalizar 0-1
                    features.momentum,
                    features.volatility_ratio,
                    features.bb_position,
                    features.volume_ratio if features.volume_ratio else 0.5,
                ])
                
                # Target = R-múltiple realizado
                r_multiple = trade.get('r_multiple', 0.0)
                
                X_list.append(features_array)
                Y_list.append(r_multiple)
            
            except Exception as e:
                logger.debug(f"Error processing trade: {e}")
                continue
        
        if len(X_list) == 0:
            logger.warning("No training data available")
            return np.array([]), np.array([])
        
        X = np.array(X_list)
        Y = np.array(Y_list)
        
        logger.info(f"Training data prepared: {len(X)} samples, {X.shape[1]} features")
        logger.info(f"Target (R-multiple) stats: mean={Y.mean():.2f}, std={Y.std():.2f}")
        
        # Normalizar features
        X_scaled = self.scaler.fit_transform(X)
        
        return X_scaled, Y
    
    def retrain_model(
        self,
        X_train: np.ndarray,
        Y_train: np.ndarray,
        validation_split: float = 0.2,
        epochs: int = 500
    ) -> Dict:
        """
        Reentrenamiento con nuevo sistema
        
        Cambio importante: Usar REGRESIÓN no CLASIFICACIÓN
        - Antes: Predecir si trade gana/pierde (0/1)
        - Ahora: Predecir cuánto gana/pierde (R-múltiplos continuos)
        """
        
        if len(X_train) == 0:
            logger.warning("No training data available")
            return {'success': False, 'error': 'No training data'}
        
        try:
            logger.info(f"Starting model retraining ({self.model_type})...")
            
            if self.model_type == 'neural_network':
                self.model = MLPRegressor(
                    hidden_layer_sizes=(64, 32, 16),  # Arquitectura
                    activation='relu',
                    learning_rate_init=0.001,
                    learning_rate='adaptive',
                    max_iter=epochs,
                    early_stopping=True,
                    validation_fraction=validation_split,
                    n_iter_no_change=20,  # Stop si no mejora en 20 iteraciones
                    tol=1e-4,
                    random_state=42,
                    verbose=1
                )
            
            elif self.model_type == 'random_forest':
                self.model = RandomForestRegressor(
                    n_estimators=100,
                    max_depth=15,
                    min_samples_split=10,
                    min_samples_leaf=5,
                    random_state=42,
                    n_jobs=-1
                )
            
            else:
                raise ValueError(f"Unknown model type: {self.model_type}")
            
            # Entrenar
            self.model.fit(X_train, Y_train)
            
            # Evaluar en datos de entrenamiento
            train_score = self.model.score(X_train, Y_train)
            
            # Cross-validation
            cv_scores = self._perform_cross_validation(X_train, Y_train)
            
            metrics = {
                'success': True,
                'train_score': train_score,
                'cv_mean_score': cv_scores['mean'],
                'cv_std_score': cv_scores['std'],
                'cv_scores': cv_scores['scores'].tolist(),
                'training_samples': len(X_train)
            }
            
            self.performance_metrics = metrics
            
            logger.info(
                f"Model training completed: R² = {train_score:.4f}, "
                f"CV = {cv_scores['mean']:.4f} ± {cv_scores['std']:.4f}"
            )
            
            # Guardar modelo
            self._save_model()
            
            return metrics
        
        except Exception as e:
            logger.error(f"Model training failed: {e}")
            return {'success': False, 'error': str(e)}
    
    def predict_trade_quality(
        self,
        features: np.ndarray
    ) -> Dict:
        """
        Predice calidad del trade próximo (en R-múltiplos esperados)
        """
        
        if self.model is None:
            logger.warning("Model not trained yet")
            return {
                'expected_r_multiple': 0.0,
                'expected_confidence': 0.0,
                'trade_quality': 'UNKNOWN'
            }
        
        try:
            # Normalizar features
            features_scaled = self.scaler.transform([features])
            
            # Predecir
            expected_r_multiple = float(self.model.predict(features_scaled)[0])
            
            # Confianza = valor absoluto del R predicho (max 1.0)
            expected_confidence = min(abs(expected_r_multiple), 1.0)
            
            # Clasificar calidad
            if expected_r_multiple > 1.0:
                trade_quality = 'EXCELLENT'
            elif expected_r_multiple > 0.5:
                trade_quality = 'GOOD'
            elif expected_r_multiple > 0:
                trade_quality = 'MODERATE'
            elif expected_r_multiple > -0.5:
                trade_quality = 'POOR'
            else:
                trade_quality = 'RISKY'
            
            return {
                'expected_r_multiple': expected_r_multiple,
                'expected_confidence': expected_confidence,
                'trade_quality': trade_quality
            }
        
        except Exception as e:
            logger.error(f"Prediction failed: {e}")
            return {
                'expected_r_multiple': 0.0,
                'expected_confidence': 0.0,
                'trade_quality': 'ERROR'
            }
    
    def _perform_cross_validation(
        self,
        X: np.ndarray,
        Y: np.ndarray,
        k_folds: int = 5
    ) -> Dict:
        """
        K-Fold Cross Validation
        """
        
        if len(X) < k_folds:
            logger.warning(f"Not enough samples for {k_folds}-fold CV")
            return {'mean': 0.0, 'std': 0.0, 'scores': np.array([])}
        
        try:
            scores = cross_val_score(
                self.model,
                X, Y,
                cv=k_folds,
                scoring='r2'
            )
            
            return {
                'mean': float(scores.mean()),
                'std': float(scores.std()),
                'scores': scores
            }
        
        except Exception as e:
            logger.error(f"Cross-validation failed: {e}")
            return {'mean': 0.0, 'std': 0.0, 'scores': np.array([])}
    
    def _save_model(self, filename: str = None):
        """Guarda modelo entrenado"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = os.path.join(MODEL_SAVE_DIR, f"model_{timestamp}.pkl")
        
        try:
            with open(filename, 'wb') as f:
                pickle.dump({
                    'model': self.model,
                    'scaler': self.scaler,
                    'type': self.model_type,
                    'metrics': self.performance_metrics
                }, f)
            logger.info(f"Model saved to {filename}")
        except Exception as e:
            logger.error(f"Failed to save model: {e}")
    
    def load_model(self, filename: str):
        """Carga modelo previamente entrenado"""
        try:
            with open(filename, 'rb') as f:
                data = pickle.load(f)
                self.model = data['model']
                self.scaler = data['scaler']
                self.model_type = data['type']
                self.performance_metrics = data['metrics']
            logger.info(f"Model loaded from {filename}")
            return True
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            return False


# =============================================================================
# OVERFITTING PREVENTION
# =============================================================================
class OverfittingPrevention:
    """
    Previene que modelo se ajuste demasiado al historial pasado
    """
    
    def __init__(self, model: MLPRegressor = None):
        self.model = model
        self.regularization_history = []
    
    def apply_regularization(self, lambda_l2: float = 0.01):
        """
        L2 Regularization = penaliza pesos muy grandes
        Previene sobreajuste a datos históricos
        """
        if self.model is not None:
            self.model.alpha = lambda_l2
            logger.info(f"L2 regularization applied: lambda={lambda_l2}")
    
    def detect_overfitting(
        self,
        train_score: float,
        cv_mean_score: float,
        cv_std_score: float
    ) -> bool:
        """
        Detecta si hay sobreajuste
        
        Overfitting = diferencia entre train y CV score > umbral
        """
        
        score_gap = train_score - cv_mean_score
        
        # Si diferencia > 0.1 (10%), probablemente hay overfitting
        if score_gap > 0.1:
            logger.warning(
                f"Possible overfitting detected: train_score={train_score:.4f}, "
                f"cv_score={cv_mean_score:.4f}, gap={score_gap:.4f}"
            )
            return True
        
        return False
    
    def adapt_to_market_changes(
        self,
        recent_trades: List[Dict],
        historical_win_rate: float = 0.55,
        window_size: int = 100
    ) -> bool:
        """
        Si últimas N trades muestran patrón diferente:
        - Mercado cambió
        - Reentrenar modelo recomendado
        """
        
        if len(recent_trades) < window_size:
            return False
        
        recent_window = recent_trades[-window_size:]
        
        # Calcular métrica de "novedad"
        recent_winners = sum(1 for t in recent_window if t.get('r_multiple', 0) > 0)
        recent_win_rate = recent_winners / len(recent_window)
        
        # Si diferencia > 15%, mercado cambió
        win_rate_change = abs(recent_win_rate - historical_win_rate)
        
        if win_rate_change > 0.15:
            logger.info(
                f"Market change detected: recent_wr={recent_win_rate:.1%}, "
                f"historical_wr={historical_win_rate:.1%}, change={win_rate_change:.1%}"
            )
            return True  # Reentrenar
        
        return False
    
    def evaluate_model_stability(
        self,
        recent_predictions: List[Dict]
    ) -> Dict:
        """
        Evalúa estabilidad de predicciones recientes
        """
        
        if not recent_predictions:
            return {'stability': 'UNKNOWN', 'variance': 0.0}
        
        predictions = [p.get('expected_r_multiple', 0) for p in recent_predictions]
        variance = np.var(predictions) if len(predictions) > 1 else 0.0
        
        # Baja varianza = predicciones estables
        if variance < 0.1:
            stability = 'HIGH'
        elif variance < 0.3:
            stability = 'MEDIUM'
        else:
            stability = 'LOW'
        
        return {
            'stability': stability,
            'variance': float(variance),
            'mean_prediction': float(np.mean(predictions))
        }


# =============================================================================
# MARKET ADAPTATION
# =============================================================================
class MarketAdaptationEngine:
    """
    Detecta y adapta a cambios de mercado
    """
    
    def __init__(self, lookback_window: int = 100, change_threshold: float = 0.20):
        self.lookback_window = lookback_window
        self.change_threshold = change_threshold
        self.market_regimes = []
    
    def detect_regime_change(
        self,
        recent_trades: List[Dict]
    ) -> Dict:
        """
        Detecta cambio de régimen de mercado
        """
        
        if len(recent_trades) < self.lookback_window:
            return {'regime_change': False, 'reason': 'Insufficient data'}
        
        window = recent_trades[-self.lookback_window:]
        
        # Calcular métricas
        metrics = self._calculate_window_metrics(window)
        
        # Comparar con régimen anterior
        if len(self.market_regimes) > 0:
            previous_metrics = self.market_regimes[-1]
            
            # Detectar cambios
            changes = self._detect_metric_changes(previous_metrics, metrics)
            
            if changes['detected']:
                logger.info(f"Market regime change detected: {changes['changed_metrics']}")
                return {
                    'regime_change': True,
                    'reason': ', '.join(changes['changed_metrics']),
                    'previous_metrics': previous_metrics,
                    'current_metrics': metrics
                }
        
        self.market_regimes.append(metrics)
        
        return {'regime_change': False, 'reason': 'No significant changes'}
    
    def _calculate_window_metrics(self, trades: List[Dict]) -> Dict:
        """Calcula métricas de ventana de trades"""
        
        winners = [t.get('r_multiple', 0) for t in trades if t.get('r_multiple', 0) > 0]
        losers = [t.get('r_multiple', 0) for t in trades if t.get('r_multiple', 0) < 0]
        
        total_r = sum(t.get('r_multiple', 0) for t in trades)
        win_rate = len(winners) / len(trades) if trades else 0
        
        return {
            'timestamp': datetime.now(),
            'win_rate': win_rate,
            'total_r': total_r,
            'avg_winner_r': np.mean(winners) if winners else 0,
            'avg_loser_r': np.mean(losers) if losers else 0,
            'profit_factor': abs(sum(winners) / sum(losers)) if losers and sum(losers) != 0 else 0
        }
    
    def _detect_metric_changes(self, previous: Dict, current: Dict) -> Dict:
        """Detecta cambios en métricas"""
        
        changes = []
        
        if abs(current['win_rate'] - previous['win_rate']) > self.change_threshold:
            changes.append(f"win_rate: {previous['win_rate']:.1%} → {current['win_rate']:.1%}")
        
        if abs(current['profit_factor'] - previous['profit_factor']) > 0.5:
            changes.append(f"profit_factor: {previous['profit_factor']:.2f} → {current['profit_factor']:.2f}")
        
        return {
            'detected': len(changes) > 0,
            'changed_metrics': changes
        }
