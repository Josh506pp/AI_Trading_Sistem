# Sistema de Trading Inteligente - Redesign Completo
## Arquitectura Basada en R-Múltiplos y Optimización de IA

---

## 1. SISTEMA DE RECOMPENSAS (PUNTOS) BASADO EN R

### 1.1 Concepto Fundamental de "R"

**R = Riesgo por Operación**
- R = Distancia del precio de entrada al stop loss (en puntos/pips)
- Ejemplo: Entrada 1.0850, Stop Loss 1.0800 → R = 50 pips

**Sistema de Puntos = Múltiplos de R**

| Resultado | Fórmula | Puntos | Descripción |
|-----------|---------|--------|-------------|
| **Win** | (Ganancia en pips) / R | +1.5R a +5R | Ganancia relativa al riesgo |
| **Loss** | -(Pérdida en pips) / R | -1.0R a -2R | Pérdida relativa al riesgo |

**Ejemplos Prácticos:**
```
Escenario 1: Trade Conservador
- Entrada: 1.0850, SL: 1.0800, TP: 1.0900
- R = 50 pips, Recompensa potencial = 50 pips (+1R)
- Resultado: Cierre en 1.0900 = +1R = +100 puntos ✓

Escenario 2: Trade Agresivo (MALO)
- Entrada: 1.0850, SL: 1.0800, TP: 1.0810
- R = 50 pips, Recompensa potencial = 20 pips (+0.4R)
- Resultado: Cierre en 1.0790 = -1.2R = -120 puntos ✗
```

### 1.2 Cálculo de Puntos Detallado

```python
class RewardCalculator:
    """
    Calcula puntos basados en múltiplos de R
    """
    
    def calculate_reward(
        self,
        entry_price: float,
        stop_loss: float,
        exit_price: float,
        is_buy: bool
    ) -> dict:
        """
        Calcula recompensa en R-múltiplos
        
        Returns:
            {
                'r_value': float,        # Múltiplos de R (ej: 1.5, -1.0)
                'points': int,          # Puntos base (r_value * 100)
                'adjusted_points': int, # Puntos después de penalizaciones
                'pnl_percent': float    # PnL como porcentaje
            }
        """
        
        # Calcular R (riesgo por operación)
        if is_buy:
            R = (entry_price - stop_loss) / point_size
        else:
            R = (stop_loss - entry_price) / point_size
        
        # Calcular ganancia/pérdida
        if is_buy:
            pnl_pips = (exit_price - entry_price) / point_size
        else:
            pnl_pips = (entry_price - exit_price) / point_size
        
        # Convertir a R-múltiplos
        r_value = pnl_pips / R if R != 0 else 0
        
        # Puntos base (escala 1R = 100 puntos)
        base_points = int(r_value * 100)
        
        return {
            'r_value': r_value,
            'points': base_points,
            'pnl_pips': pnl_pips
        }
```

---

## 2. CONTROL DE RIESGO AVANZADO

### 2.1 Penalizaciones por Comportamiento de Riesgo

```python
class RiskPenaltySystem:
    """
    Penaliza comportamientos de riesgo peligroso
    """
    
    def __init__(self, window_size: int = 20):
        self.trade_history = []  # Últimas N operaciones
        self.window_size = window_size
    
    # =========== PENALIZACIÓN 1: DRAWDOWN ===========
    def calculate_drawdown_penalty(self, current_balance: float, peak_balance: float) -> int:
        """
        Penaliza si drawdown supera umbrales
        
        Drawdown = (Peak - Current) / Peak
        """
        drawdown_pct = (peak_balance - current_balance) / peak_balance * 100
        
        if drawdown_pct > 30:  # Crítico
            return -500  # Penalización severa
        elif drawdown_pct > 20:  # Alto riesgo
            return -250
        elif drawdown_pct > 10:  # Moderado
            return -100
        else:
            return 0
    
    # =========== PENALIZACIÓN 2: RACHAS DE PÉRDIDAS ===========
    def calculate_losing_streak_penalty(self) -> int:
        """
        Penaliza rachas de pérdidas consecutivas
        """
        if not self.trade_history:
            return 0
        
        # Contar pérdidas consecutivas desde el final
        losing_streak = 0
        for trade in reversed(self.trade_history[-10:]):  # Últimos 10 trades
            if trade['r_value'] < 0:
                losing_streak += 1
            else:
                break
        
        penalties = {
            3: -50,   # 3 pérdidas seguidas
            4: -100,
            5: -200,  # 5+ pérdidas = penalización severa
        }
        
        return penalties.get(min(losing_streak, 5), 0)
    
    # =========== PENALIZACIÓN 3: RIESGO POR OPERACIÓN ALTO ===========
    def calculate_excessive_risk_penalty(self, r_value: float, risk_percent: float) -> int:
        """
        Penaliza si riesgo por operación es muy alto
        """
        if risk_percent > 5:  # Más del 5% de riesgo
            return -150
        elif risk_percent > 3:
            return -75
        else:
            return 0
    
    # =========== PENALIZACIÓN 4: REVENGE TRADING ===========
    def calculate_revenge_trading_penalty(self, current_r: float) -> int:
        """
        Detecta y penaliza revenge trading (aumentar lotaje tras pérdidas)
        """
        if len(self.trade_history) < 2:
            return 0
        
        last_trade = self.trade_history[-1]
        prev_trade = self.trade_history[-2]
        
        # Si pérdida anterior y ahora lotaje más alto = revenge trading
        if (prev_trade['r_value'] < 0 and 
            last_trade['lot_size'] > prev_trade['lot_size'] * 1.5):
            return -200  # Penalización severa
        
        return 0
```

### 2.2 Sistema de Bonificación por Consistencia

```python
class ConsistencyBonusSystem:
    """
    Bonifica comportamientos consistentes y rentables
    """
    
    def calculate_consistency_bonus(self, trade_history: List[dict], window: int = 20) -> int:
        """
        Premia consistencia en ganancias
        """
        if len(trade_history) < window:
            return 0
        
        recent_trades = trade_history[-window:]
        
        # Calcular métricas
        win_rate = sum(1 for t in recent_trades if t['r_value'] > 0) / window
        profit_factor = sum(t['r_value'] for t in recent_trades if t['r_value'] > 0) / \
                        abs(sum(t['r_value'] for t in recent_trades if t['r_value'] < 0) or 1)
        
        # Bonificaciones
        bonus = 0
        
        # Bonus por alta tasa de ganancia (>55%)
        if win_rate > 0.60:
            bonus += int(win_rate * 100)  # Hasta +60 puntos
        
        # Bonus por profit factor (ganancias/pérdidas)
        if profit_factor > 2:  # Por cada 2 ganadas, 1 perdida
            bonus += min(profit_factor * 50, 200)  # Máx +200
        
        # Bonus por racha de ganancias (sin penalizaciones)
        if recent_trades[-3:]:  # Últimas 3 operaciones
            if all(t['r_value'] > 0 for t in recent_trades[-3:]):
                bonus += 75
            elif all(t['r_value'] > 0 for t in recent_trades[-5:]):
                bonus += 150
        
        return bonus
```

### 2.3 Puntaje Total (Scoring System)

```python
class TradingScoreCard:
    """
    Calcula puntuación total de salud del sistema
    """
    
    def calculate_total_score(
        self,
        base_points: int,           # De reward calculator
        drawdown_penalty: int,      # De risk penalty
        streak_penalty: int,
        excessive_risk_penalty: int,
        revenge_trading_penalty: int,
        consistency_bonus: int
    ) -> dict:
        """
        Scoring = BasePoints + Bonuses - Penalizaciones
        """
        
        penalties = (
            drawdown_penalty + 
            streak_penalty + 
            excessive_risk_penalty + 
            revenge_trading_penalty
        )
        
        total_score = base_points + consistency_bonus + penalties
        
        # Clasificación de salud
        health = "CRITICAL"  # Por defecto
        if total_score < -500:
            health = "CRITICAL"  # Riesgo muy alto
        elif total_score < -200:
            health = "HIGH_RISK"
        elif total_score < 0:
            health = "AT_RISK"
        elif total_score < 200:
            health = "CAUTION"
        elif total_score < 500:
            health = "HEALTHY"
        else:
            health = "EXCELLENT"
        
        return {
            'total_score': total_score,
            'base_points': base_points,
            'consistency_bonus': consistency_bonus,
            'total_penalties': penalties,
            'health_status': health
        }
```

---

## 3. ANÁLISIS INTELIGENTE DE PRECIOS

### 3.1 Selección de Precios Relevantes

**Problema:** Analizar 100-200 precios sin filtro = ruido y sobreajuste

**Solución:** Análisis jerárquico en múltiples timeframes

```python
class SmartPriceAnalyzer:
    """
    Selecciona precios relevantes en lugar de todos los disponibles
    """
    
    def select_relevant_prices(
        self,
        all_prices: np.ndarray,
        price_time: np.ndarray
    ) -> dict:
        """
        Selecciona prices según relevancia (no todos)
        
        Estrategia:
        1. Identificar puntos de quiebre (breakpoints): cambios de dirección
        2. Detectar niveles de soporte/resistencia
        3. Medir volatilidad local
        4. Priorizar últimos N candles + puntos importantes
        
        Returns:
            {
                'most_recent': np.ndarray,     # Últimos 20 precios
                'support_resistance': dict,    # Niveles importantes
                'volatility_zones': dict,      # Zonas de alta volatilidad
                'trend_points': list,          # Puntos clave de tendencia
                'selected_total': int          # Num total de precios relevantes
            }
        """
        
        analysis = {}
        
        # 1. PRECIOS MÁS RECIENTES (Siempre relevantes)
        analysis['most_recent'] = all_prices[-20:]  # Últimos 20
        
        # 2. DETECTAR SOPORTE/RESISTENCIA (Máximos/Mínimos locales)
        support_resistance = self._find_support_resistance(all_prices, window=20)
        analysis['support_resistance'] = support_resistance
        
        # 3. DETECTAR VOLATILIDAD
        volatility = self._analyze_volatility(all_prices, window=30)
        analysis['volatility_zones'] = volatility
        
        # 4. PUNTOS CLAVE DE TENDENCIA (Breakpoints)
        trend_points = self._identify_trend_changes(all_prices)
        analysis['trend_points'] = trend_points
        
        # TOTAL: 20 recientes + 5 soporte/resistencia + 5 volat + 10 tendencia = 40 precios relevantes
        analysis['selected_total'] = 40  # Mejor que 200
        
        return analysis
    
    def _find_support_resistance(self, prices: np.ndarray, window: int = 20) -> dict:
        """Encuentra máximos y mínimos locales"""
        highs = []
        lows = []
        
        for i in range(window, len(prices) - window):
            if prices[i] == np.max(prices[i-window:i+window]):
                highs.append((i, prices[i]))
            if prices[i] == np.min(prices[i-window:i+window]):
                lows.append((i, prices[i]))
        
        return {'highs': highs[-5:], 'lows': lows[-5:]}  # Últimos 5 de cada
    
    def _analyze_volatility(self, prices: np.ndarray, window: int = 30) -> dict:
        """Detecta zonas de alta volatilidad"""
        returns = np.diff(prices) / prices[:-1]  # Retornos porcentuales
        volatility = pd.Series(returns).rolling(window).std()
        
        # Períodos de alta volatilidad
        high_vol_threshold = volatility.mean() + volatility.std()
        high_vol_zones = np.where(volatility > high_vol_threshold)[0]
        
        return {
            'current_volatility': volatility.iloc[-1],
            'avg_volatility': volatility.mean(),
            'high_vol_zones': high_vol_zones[-10:] if len(high_vol_zones) > 0 else []
        }
    
    def _identify_trend_changes(self, prices: np.ndarray) -> list:
        """Identifica cambios de tendencia (puntos críticos)"""
        # Calcular cambio de dirección (derivatives)
        price_change = np.diff(prices)
        direction_change = np.diff(np.sign(price_change))  # Cambios de signo = picos/valles
        
        # Puntos donde cambia la dirección
        breakpoints = np.where(direction_change != 0)[0]
        
        return breakpoints[-10:].tolist() if len(breakpoints) > 0 else []
```

### 3.2 Features Técnicos Relevantes

```python
class TechnicalFeatureExtractor:
    """
    Extrae features técnicos relevantes (no todos posibles)
    """
    
    def extract_key_features(self, prices: np.ndarray, volume: np.ndarray = None) -> dict:
        """
        Extrae SOLO los features más predictivos
        """
        
        features = {}
        
        # 1. TENDENCIA (2 features)
        sma_20 = self._sma(prices, 20)
        sma_50 = self._sma(prices, 50)
        features['trend_strength'] = (prices[-1] - sma_50[-1]) / prices[-1]  # Cuán fuerte es tendencia
        features['sma_crossover'] = 1 if sma_20[-1] > sma_50[-1] else -1
        
        # 2. MOMENTUM (2 features)
        rsi = self._rsi(prices, 14)
        features['rsi'] = rsi[-1]  # 0-100
        features['momentum'] = prices[-1] - prices[-20]  # Cambio últimos 20 precios
        
        # 3. VOLATILIDAD (1 feature)
        atr = self._atr(prices, 14)
        features['volatility_ratio'] = atr[-1] / prices[-1]  # ATR como % del precio
        
        # 4. BANDAS DE BOLLINGER (1 feature)
        bb_upper, bb_middle, bb_lower = self._bollinger_bands(prices, 20)
        bb_position = (prices[-1] - bb_lower[-1]) / (bb_upper[-1] - bb_lower[-1])
        features['bb_position'] = bb_position  # 0-1, dónde está el precio en las bandas
        
        # 5. VOLUMEN (si disponible)
        if volume is not None:
            features['volume_trend'] = np.mean(volume[-5:]) / np.mean(volume[-20:])
        
        return features  # Total: 7 features relevantes, no 50
```

---

## 4. LÓGICA DE DECISIONES MEJORADA

### 4.1 Entrada (Entry Decision Logic)

```python
class EntryDecisionLogic:
    """
    Decide entradas COMPRADAS/VENDIDAS basadas en ventaja estadística
    """
    
    def should_open_trade(
        self,
        price_analysis: dict,
        technical_features: dict,
        score_card: dict,
        max_positions: int,
        current_positions: int
    ) -> dict:
        """
        Abre operación si hay ventaja estadística
        
        NO asume certeza, sino PROBABILIDAD
        """
        
        decision = {
            'should_trade': False,
            'direction': None,  # 'BUY' o 'SELL'
            'confidence': 0.0,
            'reason': '',
            'entry_price': None
        }
        
        # ===== PARADA 1: CHEQUES DE SALUD =====
        if current_positions >= max_positions:
            decision['reason'] = "Max positions reached"
            return decision
        
        if score_card['health_status'] in ['CRITICAL', 'HIGH_RISK']:
            decision['reason'] = f"System in {score_card['health_status']} state"
            return decision
        
        # ===== PARADA 2: VOLATILIDAD EXTREMA =====
        if technical_features['volatility_ratio'] > 0.05:  # > 5% volatilidad
            decision['reason'] = "Volatility too high, waiting"
            return decision
        
        # ===== LÓGICA DE DECISIÓN =====
        # Compilar señales (cada señal = peso)
        buy_signals = 0
        sell_signals = 0
        
        # SEÑAL 1: CRUCE SMA (Peso: 2)
        if technical_features['sma_crossover'] == 1:  # SMA 20 > SMA 50
            buy_signals += 2
        else:
            sell_signals += 2
        
        # SEÑAL 2: RSI (Peso: 1.5)
        if technical_features['rsi'] < 30:  # Sobvendido = comprar
            buy_signals += 1.5
        elif technical_features['rsi'] > 70:  # Sobrecomprado = vender
            sell_signals += 1.5
        
        # SEÑAL 3: MOMENTUM (Peso: 1)
        if technical_features['momentum'] > 0:
            buy_signals += 1
        else:
            sell_signals += 1
        
        # SEÑAL 4: POSICIÓN EN BANDAS BOLLINGER (Peso: 1.5)
        if technical_features['bb_position'] < 0.2:  # Cerca del límite inferior
            buy_signals += 1.5
        elif technical_features['bb_position'] > 0.8:  # Cerca del límite superior
            sell_signals += 1.5
        
        # SEÑAL 5: TENDENCIA GENERAL (Peso: 2)
        if technical_features['trend_strength'] > 0.02:  # Tendencia alcista fuerte
            buy_signals += 2
        elif technical_features['trend_strength'] < -0.02:  # Tendencia bajista fuerte
            sell_signals += 2
        
        # ===== CALCULAR CONFIANZA =====
        total_signals = buy_signals + sell_signals
        
        if buy_signals > sell_signals:
            confidence = buy_signals / total_signals if total_signals > 0 else 0
            direction = 'BUY'
        else:
            confidence = sell_signals / total_signals if total_signals > 0 else 0
            direction = 'SELL'
        
        # MÍNIMO DE CONFIANZA: 55% (para permitir múltiples posiciones)
        if confidence >= 0.55:
            decision['should_trade'] = True
            decision['direction'] = direction
            decision['confidence'] = confidence
            decision['reason'] = f"{direction} signal with {confidence*100:.1f}% confidence"
        else:
            decision['reason'] = f"Confidence {confidence*100:.1f}% < 55% threshold"
        
        return decision
```

### 4.2 Gestión de Salida (Exit Decision Logic)

```python
class ExitDecisionLogic:
    """
    Decide salidas de posiciones
    """
    
    def should_exit_trade(
        self,
        trade: dict,
        current_price: float,
        technical_features: dict,
        trailing_stop_enabled: bool = True
    ) -> dict:
        """
        Decide si salir de una posición
        
        Criterios:
        1. Take profit alcanzado
        2. Stop loss tocado
        3. Trail stop activado
        4. Cambio de tendencia (salida táctica)
        """
        
        exit_decision = {
            'should_exit': False,
            'exit_reason': None,
            'exit_price': None,
            'expected_r_multiple': 0
        }
        
        is_buy = trade['direction'] == 'BUY'
        entry = trade['entry_price']
        sl = trade['stop_loss']
        tp = trade['take_profit']
        R = abs(entry - sl)
        
        # ===== PARADA 1: STOP LOSS =====
        if is_buy and current_price <= sl:
            exit_decision['should_exit'] = True
            exit_decision['exit_reason'] = 'STOP_LOSS'
            exit_decision['exit_price'] = sl
            exit_decision['expected_r_multiple'] = -1.0
            return exit_decision
        
        if not is_buy and current_price >= sl:
            exit_decision['should_exit'] = True
            exit_decision['exit_reason'] = 'STOP_LOSS'
            exit_decision['exit_price'] = sl
            exit_decision['expected_r_multiple'] = -1.0
            return exit_decision
        
        # ===== PARADA 2: TAKE PROFIT =====
        if is_buy and current_price >= tp:
            exit_decision['should_exit'] = True
            exit_decision['exit_reason'] = 'TAKE_PROFIT'
            exit_decision['exit_price'] = tp
            pnl_pips = (tp - entry) / 0.00001  # Para EURUSD
            expected_r = pnl_pips / R
            exit_decision['expected_r_multiple'] = expected_r
            return exit_decision
        
        if not is_buy and current_price <= tp:
            exit_decision['should_exit'] = True
            exit_decision['exit_reason'] = 'TAKE_PROFIT'
            exit_decision['exit_price'] = tp
            pnl_pips = (entry - tp) / 0.00001
            expected_r = pnl_pips / R
            exit_decision['expected_r_multiple'] = expected_r
            return exit_decision
        
        # ===== PARADA 3: TRAIL STOP (si enabled) =====
        if trailing_stop_enabled:
            highest_since_entry = trade.get('highest_price', entry)
            trail_distance = R * 0.5  # Trail a 0.5R
            
            if is_buy:
                if current_price > highest_since_entry:
                    trade['highest_price'] = current_price
                
                if current_price < trade['highest_price'] - trail_distance:
                    exit_decision['should_exit'] = True
                    exit_decision['exit_reason'] = 'TRAILING_STOP'
                    exit_decision['exit_price'] = current_price
                    # Calcular R múltiple
                    pnl_pips = (current_price - entry) / 0.00001
                    expected_r = pnl_pips / R
                    exit_decision['expected_r_multiple'] = expected_r
                    return exit_decision
        
        # ===== PARADA 4: REVERSIÓN DE TENDENCIA (Salida táctica) =====
        # Si la tendencia cambia significativamente, salir antes del TP
        if technical_features['sma_crossover'] * (1 if is_buy else -1) < 0:
            # Tendencia se revirtió
            profit_so_far = abs(current_price - entry) / 0.00001
            if profit_so_far > R * 0.3:  # Ganancia de al menos 0.3R
                exit_decision['should_exit'] = True
                exit_decision['exit_reason'] = 'TREND_REVERSAL'
                exit_decision['exit_price'] = current_price
                expected_r = profit_so_far / R
                exit_decision['expected_r_multiple'] = expected_r
                return exit_decision
        
        return exit_decision
```

---

## 5. OPTIMIZACIÓN DE IA

### 5.1 Reentrenamiento con Sistema de R-Múltiplos

```python
class AIOptimizer:
    """
    Reentrenamiento de modelos IA basado en nuevo sistema de puntos
    """
    
    def prepare_training_data(
        self,
        trade_history: List[dict],
        price_data: pd.DataFrame
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Prepara datos de entrenamiento donde:
        - X = Features técnicos
        - Y = Resultado en R-múltiplos (no solo 0/1 ganancia/pérdida)
        
        Esto hace que el modelo aprenda a MAXIMIZAR BENEFICIO AJUSTADO AL RIESGO
        no solo a ganar trades
        """
        
        X_list = []
        Y_list = []  # En lugar de 0/1, usamos R-múltiplos
        
        for trade in trade_history:
            # Extraer features del momento de entrada
            entry_time = trade['entry_time']
            features = self._extract_features_at_time(price_data, entry_time)
            
            # Target = R-múltiple alcanzado
            r_multiple = trade['r_multiple']
            
            X_list.append(features)
            Y_list.append(r_multiple)
        
        X = np.array(X_list)
        Y = np.array(Y_list)
        
        # Normalizar
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)
        
        return X_scaled, Y
    
    def retrain_model(
        self,
        X_train: np.ndarray,
        Y_train: np.ndarray,
        model_type: str = 'neural_network'
    ):
        """
        Reentrenamiento con nuevo sistema
        
        Importante: Usar REGRESIÓN no CLASIFICACIÓN
        - Antes: Predecir si trade gana/pierde (0/1)
        - Ahora: Predecir cuánto gana/pierde (R-múltiplos continuos)
        """
        
        if model_type == 'neural_network':
            # Neurona salida = regresión (R-múltiplo continuo)
            model = MLPRegressor(
                hidden_layer_sizes=(64, 32, 16),  # Arquitectura
                activation='relu',
                learning_rate_init=0.001,
                max_iter=500,
                early_stopping=True,
                validation_fraction=0.1,
                n_iter_no_change=20,  # Stop si no mejora en 20 iteraciones
                random_state=42
            )
        
        # Entrenar
        model.fit(X_train, Y_train)
        
        return model
    
    def predict_trade_quality(
        self,
        features: np.ndarray,
        trained_model
    ) -> dict:
        """
        Predice calidad del trade próximo (en R-múltiplos esperados)
        """
        
        expected_r_multiple = trained_model.predict([features])[0]
        
        return {
            'expected_r_multiple': expected_r_multiple,
            'expected_confidence': min(abs(expected_r_multiple), 1.0),
            'trade_quality': 'GOOD' if expected_r_multiple > 0.5 else 'RISKY' if expected_r_multiple > 0 else 'POOR'
        }
```

### 5.2 Prevención de Overfitting

```python
class OverfittingPrevention:
    """
    Previene que modelo se ajuste demasiado al historial pasado
    """
    
    def apply_regularization(
        self,
        model,
        lambda_l2: float = 0.01
    ):
        """
        L2 Regularization = penaliza pesos muy grandes
        Previene sobreajuste a datos históricos
        """
        # En sklearn, se configura con `alpha`
        model.alpha = lambda_l2
    
    def use_cross_validation(
        self,
        X_train: np.ndarray,
        Y_train: np.ndarray,
        k_folds: int = 5
    ) -> dict:
        """
        K-Fold Cross Validation
        Evalúa modelo en múltiples splits del data
        """
        from sklearn.model_selection import cross_val_score
        
        scores = cross_val_score(
            self.model,
            X_train, Y_train,
            cv=k_folds,
            scoring='r2'  # Coeficiente de determinación
        )
        
        return {
            'mean_score': scores.mean(),
            'std_score': scores.std(),
            'individual_scores': scores.tolist()
        }
    
    def implement_dropout_strategy(self, model):
        """
        En cada predicción, desactivar randomly 10-20% de neuronas
        (Técnica simular de dropout sin modificar arquitectura)
        """
        pass
    
    def adapt_to_market_changes(
        self,
        recent_trades: List[dict],
        sliding_window: int = 100
    ) -> bool:
        """
        Si últimas N trades muestran patrón diferente:
        - Reentrenar modelo
        - Ajustar parámetros
        - Devolver True si reentrenamiento necesario
        """
        
        if len(recent_trades) < sliding_window:
            return False
        
        recent_window = recent_trades[-sliding_window:]
        
        # Calcular métrica de "novedad"
        recent_win_rate = sum(1 for t in recent_window if t['r_multiple'] > 0) / sliding_window
        historical_win_rate = 0.55  # Asumido
        
        # Si diferencia > 10%, mercado cambió
        if abs(recent_win_rate - historical_win_rate) > 0.10:
            return True  # Reentrenar
        
        return False
```

---

## 6. INTERFAZ INTERACTIVA (CHAT PARA COMANDOS)

### 6.1 Comandos Soportados

```
USUARIO                          →  BOT REALIZA
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"abre 5 operaciones"             → Abre hasta 5 trades
"cierra todas"                   → Cierra todas las posiciones
"pausa"                          → Pausa el bot (sin cerrar)
"resume"                         → Reanuda operaciones
"tradea 30 minutos"              → Tradea próximos 30 min, luego pausa
"status"                         → Muestra estado actual
"historial"                      → Últimas 10 operaciones
"puntos totales"                 → Puntuación total del sistema
"riesgo 2%"                      → Cambia riesgo a 2% por operación
"sube lotaje 1.2x"               → Multiplica lotaje por 1.2
"stop loss 100"                  → Cambia stop loss a 100 pips
"take profit 200"                → Cambia take profit a 200 pips
"análisis"                       → Análisis técnico actual del par
"reentrenar ia"                  → Reentrenamiento con datos recientes
"backtest 100"                   → Backtest últimas 100 operaciones
```

### 6.2 Estructura de Interfaz

```python
class TradingBotChatInterface:
    """
    Interfaz CLI/Chat para controlar bot de trading
    """
    
    def __init__(self, trading_bot):
        self.bot = trading_bot
        self.running = False
    
    def start_interactive_mode(self):
        """Inicia modo interactivo"""
        print("🤖 Trading Bot IA - Modo Interactivo")
        print("Escribe 'ayuda' para ver comandos disponibles\n")
        
        while True:
            try:
                command = input("TradingBot > ").strip().lower()
                
                if not command:
                    continue
                
                response = self.process_command(command)
                print(f"\n{response}\n")
            
            except KeyboardInterrupt:
                print("\n\n⚠️  Bot pausado. Escribe 'resume' para continuar o 'salir'")
                continue
            except Exception as e:
                print(f"❌ Error: {e}")
    
    def process_command(self, command: str) -> str:
        """Procesa comando de usuario"""
        
        # ===== COMANDOS DE OPERACIÓN =====
        if command.startswith('abre'):
            num = int(command.split()[-1]) if len(command.split()) > 1 else 1
            return self.bot.open_trades(num)
        
        elif command == 'cierra todas':
            return self.bot.close_all_positions()
        
        elif command == 'pausa':
            self.bot.pause()
            return "⏸️  Bot pausado"
        
        elif command == 'resume':
            self.bot.resume()
            return "▶️  Bot reanudado"
        
        elif command.startswith('tradea'):
            minutes = int(command.split()[-1]) if len(command.split()) > 1 else 30
            return self.bot.trade_for_duration(minutes)
        
        elif command == 'status':
            return self.get_status_report()
        
        elif command == 'historial':
            return self.get_trade_history()
        
        elif command == 'puntos totales':
            return self.get_total_score()
        
        elif command.startswith('riesgo'):
            risk = float(command.split()[-1]) if '%' in command else 2.0
            self.bot.set_risk_percent(risk)
            return f"✅ Riesgo configurado a {risk}%"
        
        # ... más comandos
        
        elif command == 'ayuda':
            return self.print_help()
        
        elif command == 'salir':
            self.bot.close_all_positions()
            return "👋 Bot cerrado. ¡Hasta luego!"
        
        else:
            return f"❌ Comando desconocido: '{command}'. Escribe 'ayuda' para ver opciones"
```

---

## 7. PARÁMETROS RECOMENDADOS

```
┌─────────────────────────────────────────────────────────────┐
│ CONFIGURACIÓN RECOMENDADA INICIAL                           │
├─────────────────────────────────────────────────────────────┤
│ Riesgo por operación:        1.5% - 2.5%                  │
│ Stop loss:                    50 - 100 pips                │
│ Take profit:                  150 - 250 pips (1.5:1 a 2:1) │
│ Trailing stop:                30 - 50 pips                 │
│ Max posiciones simultáneas:   5 - 10                       │
│ Min confianza IA:             55% - 60%                    │
│                                                            │
│ UMBRALES DE RIESGO                                         │
├─────────────────────────────────────────────────────────────┤
│ Drawdown máximo aceptable:    10% - 15%                   │
│ Drawdown crítico:             > 20%                        │
│ Rachas pérdidas consecutivas  > 5 = pausa automática      │
│ Pérdidas diarias máximas:     3% - 5% (pausa)            │
│                                                            │
│ PARÁMETROS IA                                             │
├─────────────────────────────────────────────────────────────┤
│ Ventana de análisis:          100 - 150 precios            │
│ Período SMA rápido:           10 - 15 candles             │
│ Período SMA lento:            20 - 30 candles             │
│ Período RSI:                  14 candles                  │
│ Reentrenamiento:              Cada 50 - 100 operaciones   │
│ Regularización L2:            0.001 - 0.01               │
│                                                            │
│ HORARIOS (Forex - EURUSD)                                │
├─────────────────────────────────────────────────────────────┤
│ Horario óptimo:               08:00 - 17:00 GMT (Londres) │
│ Pausar en:                    20:00 - 08:00 GMT           │
│ Evitar horarios:              Noticias económicas          │
└─────────────────────────────────────────────────────────────┘
```

---

## 8. ARQUITECTURA DEL SISTEMA COMPLETO

```
┌────────────────────────────────────────────────────────────┐
│                  TRADING BOT ARCHITECTURE                  │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  ┌──────────────────────────────────────────────────────┐ │
│  │ INTERFAZ INTERACTIVA (Chat/CLI)                     │ │
│  └──────────────────────────────────────────────────────┘ │
│           ↓ Comandos del usuario                        │
│  ┌──────────────────────────────────────────────────────┐ │
│  │ ORQUESTADOR PRINCIPAL (Main Bot)                    │ │
│  │  - Gestión de posiciones                            │ │
│  │  - Loop de trading                                  │ │
│  │  - Manejo de eventos MT5                            │ │
│  └──────────────────────────────────────────────────────┘ │
│           ↓ Eventos                                      │
│  ┌─────────────────────┬─────────────────────────────────┐ │
│  │ MOTOR DE DECISIÓN   │ SISTEMA DE SCORING             │ │
│  │                     │                                 │ │
│  │ Entry Logic    ─────→ Reward Calculator              │ │
│  │ Exit Logic           Risk Penalty System             │ │
│  │ Risk Management ─────→ Consistency Bonus             │ │
│  │                      Score Card                      │ │
│  └─────────────────────┴─────────────────────────────────┘ │
│           ↓                                              │
│  ┌──────────────────────────────────────────────────────┐ │
│  │ ANALIZADOR DE PRECIOS INTELIGENTE                   │ │
│  │  - Selección de precios relevantes                  │ │
│  │  - Extracción de features técnicos                  │ │
│  │  - Detección soporte/resistencia                    │ │
│  │  - Análisis volatilidad                             │ │
│  └──────────────────────────────────────────────────────┘ │
│           ↓                                              │
│  ┌──────────────────────────────────────────────────────┐ │
│  │ MOTOR DE IA / REENTRENAMIENTO                       │ │
│  │  - Modelo Neuronal (Regresión)                      │ │
│  │  - Random Forest                                    │ │
│  │  - Detección de overfitting                         │ │
│  │  - Adaptación a cambios de mercado                  │ │
│  └──────────────────────────────────────────────────────┘ │
│           ↓                                              │
│  ┌──────────────────────────────────────────────────────┐ │
│  │ MT5 INTERFACE / EXECUTION                           │ │
│  │  - Conexión con servidor                            │ │
│  │  - Envío de órdenes                                 │ │
│  │  - Recuperación de datos                            │ │
│  └──────────────────────────────────────────────────────┘ │
│           ↓                                              │
│  ┌──────────────────────────────────────────────────────┐ │
│  │ PERSISTENCIA / LOGGING                              │ │
│  │  - Historial de trades                              │ │
│  │  - Métricas de performance                          │ │
│  │  - Logs de decisiones IA                            │ │
│  └──────────────────────────────────────────────────────┘ │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

---

## 9. ROADMAP DE IMPLEMENTACIÓN

```
FASE 1: FUNDAMENTOS (Semana 1)
├─ Crear módulo RewardCalculator
├─ Crear módulo RiskPenaltySystem
├─ Crear módulo ConsistencyBonusSystem
├─ Crear TradingScoreCard
└─ ✓ Completar: Sistema de puntos basado en R

FASE 2: ANÁLISIS INTELIGENTE (Semana 2)
├─ Crear SmartPriceAnalyzer
├─ Crear TechnicalFeatureExtractor
├─ Integrar análisis en decisiones
└─ ✓ Completar: Selección inteligente de precios

FASE 3: LÓGICA DE DECISIONES (Semana 2-3)
├─ Crear EntryDecisionLogic
├─ Crear ExitDecisionLogic
├─ Integrar con sistema de scoring
└─ ✓ Completar: Decisiones basadas en ventaja estadística

FASE 4: IA Y REENTRENAMIENTO (Semana 3-4)
├─ Crear AIOptimizer
├─ Implementar regresión (R-múltiplos)
├─ Crear OverfittingPrevention
├─ Reentrenar con historial
└─ ✓ Completar: IA optimizada al nuevo sistema

FASE 5: INTERFAZ INTERACTIVA (Semana 4)
├─ Crear TradingBotChatInterface
├─ Implementar comandos
├─ Integrar con bot principal
└─ ✓ Completar: Control tipo chat

FASE 6: INTEGRACIÓN Y TESTING (Semana 5)
├─ Integrar todos módulos
├─ Backtest completo
├─ Testing en demo MT5
└─ ✓ LANZAMIENTO

```

---

## 10. SUMARIO DE MEJORAS

| Aspecto | Antes | Después |
|---------|-------|---------|
| **Sistema Puntos** | Fijo (1 ganancia, -1 pérdida) | Dinámico basado en R-múltiplos |
| **Control Riesgo** | Mínimo | Penalizaciones múltiples + bonificaciones |
| **Análisis Precios** | 200 precios sin filtro | 40 precios relevantes seleccionados |
| **Features Técnicos** | ~50 sin prioritización | 7 features clave priorizados |
| **Modelo IA** | Clasificación (0/1) | Regresión (R-múltiplos continuos) |
| **Overfitting** | No contemplado | Cross-validation + regularización |
| **Adaptabilidad** | Estática | Reentrenamiento automático |
| **Control Usuario** | Solo start/stop | Chat interactivo con 15+ comandos |
| **Objetivo** | Maximizar ganancias | Maximizar Sharpe Ratio (rentabilidad/riesgo) |

