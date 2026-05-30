#!/usr/bin/env python3
"""
🚀 SERVIDOR WEB CON TRADING REAL Y IA
Dashboard completo con análisis de IA y control de trading
"""

from flask import Flask, render_template_string, jsonify, request, redirect, url_for, session
from datetime import datetime, timedelta
import hashlib
import secrets
import os
import sys
import numpy as np
import json

# Importar motor de trading
sys.path.insert(0, os.path.dirname(__file__))
from ai_trading import AIAnalyzer, TradingEngine

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)

# Datos globales
USERS = {}
SESSIONS = {}
TRADING_ENGINE = TradingEngine()
AI_ANALYZER = AIAnalyzer()

# Simulación de precios
PRICE_HISTORY = [1.0850 + np.random.randn() * 0.001 for _ in range(100)]

def hash_password(pwd):
    return hashlib.sha256(pwd.encode()).hexdigest()

def get_current_price():
    """Genera próximo precio"""
    last_price = PRICE_HISTORY[-1]
    change = np.random.randn() * 0.0005
    new_price = last_price + change
    PRICE_HISTORY.append(new_price)
    return new_price

# ============================================================================
# TEMPLATES HTML
# ============================================================================

LOGIN_TEMPLATE = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Trading System - Login</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
        }
        .container {
            background: white;
            padding: 40px;
            border-radius: 10px;
            box-shadow: 0 10px 25px rgba(0,0,0,0.2);
            width: 100%;
            max-width: 400px;
        }
        .header {
            text-align: center;
            margin-bottom: 30px;
        }
        .header h1 {
            color: #667eea;
            font-size: 28px;
            margin-bottom: 10px;
        }
        .form-group {
            margin-bottom: 20px;
        }
        label {
            display: block;
            color: #333;
            font-weight: 500;
            margin-bottom: 8px;
        }
        input {
            width: 100%;
            padding: 12px;
            border: 1px solid #ddd;
            border-radius: 5px;
            font-size: 14px;
        }
        input:focus {
            outline: none;
            border-color: #667eea;
        }
        .btn {
            width: 100%;
            padding: 12px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 5px;
            font-size: 16px;
            font-weight: bold;
            cursor: pointer;
        }
        .demo-users {
            margin-top: 30px;
            padding-top: 30px;
            border-top: 1px solid #eee;
            font-size: 12px;
            color: #666;
        }
        .demo-users h3 {
            color: #333;
            margin-bottom: 10px;
        }
        .demo-users p {
            margin: 5px 0;
            font-family: monospace;
            background: #f5f5f5;
            padding: 8px;
            border-radius: 3px;
        }
        .error { color: red; margin: 10px 0; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🤖 Trading + IA</h1>
            <p>Sistema Profesional con IA</p>
        </div>

        {% if error %}
        <div class="error">❌ {{ error }}</div>
        {% endif %}

        <form method="POST" action="/login">
            <div class="form-group">
                <label>👤 Usuario</label>
                <input type="text" name="username" required>
            </div>
            <div class="form-group">
                <label>🔑 Contraseña</label>
                <input type="password" name="password" required>
            </div>
            <button type="submit" class="btn">Iniciar Sesión</button>
        </form>

        <div class="demo-users">
            <h3>📌 Usuarios:</h3>
            <p><strong>Admin:</strong></p>
            <p>admin / RyzA_jjITjuPQtV66Wwf0A</p>
            <p style="margin-top: 10px;"><strong>Demo:</strong></p>
            <p>trader / SecurePass123</p>
        </div>
    </div>
</body>
</html>
"""

DASHBOARD_TEMPLATE = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Dashboard - Trading System + IA</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', sans-serif;
            background: #f5f5f5;
            color: #333;
        }
        .navbar {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px 40px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .navbar h1 { font-size: 24px; }
        .navbar a {
            color: white;
            text-decoration: none;
            padding: 8px 15px;
            border-radius: 5px;
            background: rgba(255,255,255,0.2);
            cursor: pointer;
        }
        .container {
            max-width: 1400px;
            margin: 30px auto;
            padding: 0 20px;
        }
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .card {
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        .card h3 {
            color: #667eea;
            margin-bottom: 15px;
            font-size: 16px;
        }
        .stat {
            font-size: 28px;
            font-weight: bold;
            color: #667eea;
            margin: 10px 0;
        }
        .stat-label {
            color: #666;
            font-size: 14px;
        }
        .signal-box {
            padding: 15px;
            border-radius: 8px;
            margin: 10px 0;
        }
        .signal-buy {
            background: #e8f5e9;
            border-left: 4px solid #4caf50;
            color: #2e7d32;
        }
        .signal-sell {
            background: #ffebee;
            border-left: 4px solid #f44336;
            color: #c62828;
        }
        .signal-hold {
            background: #fff3e0;
            border-left: 4px solid #ff9800;
            color: #e65100;
        }
        .trade-row {
            padding: 12px;
            border-bottom: 1px solid #eee;
            display: grid;
            grid-template-columns: 1fr 1fr 1fr 1fr;
            gap: 10px;
            font-size: 13px;
        }
        .trade-row:hover {
            background: #f5f5f5;
        }
        .profit {
            color: #4caf50;
            font-weight: bold;
        }
        .loss {
            color: #f44336;
            font-weight: bold;
        }
        .btn {
            padding: 10px 20px;
            background: #667eea;
            color: white;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-size: 14px;
            margin: 5px;
        }
        .btn:hover {
            background: #764ba2;
        }
        .btn-success {
            background: #4caf50;
        }
        .btn-danger {
            background: #f44336;
        }
        .chart-container {
            position: relative;
            height: 300px;
            margin-top: 20px;
        }
    </style>
</head>
<body>
    <div class="navbar">
        <h1>🤖 Trading System + IA</h1>
        <a href="/logout">🚪 Logout</a>
    </div>

    <div class="container">
        <h2 style="margin-bottom: 20px;">Bienvenido, {{ username }}! 👋</h2>

        <!-- ESTADÍSTICAS PRINCIPALES -->
        <div class="grid">
            <div class="card">
                <h3>💰 Balance</h3>
                <div class="stat" id="balance">$10,000.00</div>
                <div class="stat-label">Saldo disponible</div>
            </div>

            <div class="card">
                <h3>📊 Equity</h3>
                <div class="stat" id="equity">$10,000.00</div>
                <div class="stat-label">Valor total de cuenta</div>
            </div>

            <div class="card">
                <h3>📈 Precio EURUSD</h3>
                <div class="stat" id="current-price">1.0850</div>
                <div class="stat-label" id="price-change">↔️ Neutral</div>
            </div>

            <div class="card">
                <h3>🎯 Operaciones Abiertas</h3>
                <div class="stat" id="open-trades">0</div>
                <div class="stat-label">Trades en vivo</div>
            </div>
        </div>

        <!-- ANÁLISIS DE IA -->
        <div class="grid">
            <div class="card" style="grid-column: 1 / -1;">
                <h3>🤖 Análisis de IA</h3>
                <div id="ai-analysis">
                    <div style="text-align: center; color: #999;">Actualizando...</div>
                </div>
            </div>
        </div>

        <!-- GRÁFICO DE PRECIOS -->
        <div class="card">
            <h3>📊 Gráfico de Precios</h3>
            <div class="chart-container">
                <canvas id="priceChart"></canvas>
            </div>
        </div>

        <!-- OPERACIONES ABIERTAS -->
        <div class="card">
            <h3>📱 Operaciones Abiertas</h3>
            <div id="open-trades-list">
                <p style="color: #999; text-align: center;">No hay operaciones abiertas</p>
            </div>
        </div>

        <!-- HISTORIAL DE TRADES -->
        <div class="card">
            <h3>📋 Histórico de Trades</h3>
            <div id="closed-trades-list">
                <p style="color: #999; text-align: center;">Sin trades cerrados</p>
            </div>
        </div>

        <!-- CONTROLES DE TRADING -->
        <div class="card">
            <h3>⚙️ Controles de Trading</h3>
            <button class="btn btn-success" onclick="autoTrade()">🤖 Auto Trading Activado</button>
            <button class="btn btn-danger" onclick="stopAutoTrade()">🛑 Detener Auto Trading</button>
            <button class="btn" onclick="manualBuy()">📈 Comprar Manual</button>
            <button class="btn" onclick="manualSell()">📉 Vender Manual</button>
        </div>

        <!-- ESTADÍSTICAS -->
        <div class="grid">
            <div class="card">
                <h3>📊 Estadísticas</h3>
                <div id="statistics">
                    <p style="color: #999;">Total Trades: 0</p>
                    <p style="color: #999;">Win Rate: 0%</p>
                    <p style="color: #999;">P&L Total: $0</p>
                </div>
            </div>
        </div>
    </div>

    <script>
        let priceChart = null;
        let autoTradeActive = false;

        function updateDashboard() {
            // Obtener datos del servidor
            fetch('/api/trading-status')
                .then(r => r.json())
                .then(data => {
                    document.getElementById('balance').textContent = '$' + data.balance.toFixed(2);
                    document.getElementById('equity').textContent = '$' + data.equity.toFixed(2);
                    document.getElementById('current-price').textContent = data.current_price.toFixed(4);
                    document.getElementById('open-trades').textContent = data.open_trades_count;

                    // Actualizar análisis de IA
                    const analysis = data.analysis;
                    let html = '<div class="signal-' + analysis.signal.action.toLowerCase() + '">';
                    html += '<strong>' + analysis.signal.action + '</strong> - Confianza: ' + (analysis.signal.confidence * 100).toFixed(0) + '%<br>';
                    html += 'RSI: ' + analysis.indicators.rsi.toFixed(1) + ' | ';
                    html += 'Trend: ' + analysis.indicators.trend + '<br>';
                    html += 'Predicción 10 períodos: ' + analysis.prediction.next_10_periods.toFixed(4) + '<br>';
                    html += 'R-Múltiple: ' + analysis.prediction.expected_r_multiple.toFixed(2) + 'R';
                    html += '</div>';
                    document.getElementById('ai-analysis').innerHTML = html;

                    // Actualizar trades abiertos
                    updateTradesList(data.open_trades);

                    // Actualizar gráfico
                    updateChart(data.price_history);

                    // Actualizar estadísticas
                    updateStatistics(data.stats);
                });
        }

        function updateTradesList(trades) {
            let html = '';
            if (trades.length === 0) {
                html = '<p style="color: #999; text-align: center;">No hay operaciones abiertas</p>';
            } else {
                html += '<div style="overflow-x: auto;">';
                trades.forEach(trade => {
                    const color = trade.profit_loss >= 0 ? '#4caf50' : '#f44336';
                    html += '<div class="trade-row">';
                    html += '<span><strong>#' + trade.id + '</strong> ' + trade.action + '</span>';
                    html += '<span>' + trade.entry_price.toFixed(4) + '</span>';
                    html += '<span>' + (trade.current_price || trade.entry_price).toFixed(4) + '</span>';
                    html += '<span style="color:' + color + '; font-weight: bold;">' + (trade.profit_loss_pct || 0).toFixed(2) + '%</span>';
                    html += '</div>';
                });
                html += '</div>';
            }
            document.getElementById('open-trades-list').innerHTML = html;
        }

        function updateChart(prices) {
            const ctx = document.getElementById('priceChart').getContext('2d');
            
            if (priceChart) {
                priceChart.destroy();
            }

            priceChart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: prices.map((_, i) => i),
                    datasets: [{
                        label: 'EURUSD',
                        data: prices,
                        borderColor: '#667eea',
                        backgroundColor: 'rgba(102, 126, 234, 0.1)',
                        tension: 0.4,
                        fill: true
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { display: false }
                    },
                    scales: {
                        y: { beginAtZero: false }
                    }
                }
            });
        }

        function updateStatistics(stats) {
            let html = '<p>Total Trades: ' + stats.total_trades + '</p>';
            html += '<p>Win Rate: ' + stats.win_rate.toFixed(1) + '%</p>';
            html += '<p class="' + (stats.total_profit_loss >= 0 ? 'profit' : 'loss') + '">P&L Total: $' + stats.total_profit_loss.toFixed(2) + '</p>';
            document.getElementById('statistics').innerHTML = html;
        }

        function autoTrade() {
            autoTradeActive = true;
            alert('Auto Trading Activado 🤖');
        }

        function stopAutoTrade() {
            autoTradeActive = false;
            alert('Auto Trading Detenido');
        }

        function manualBuy() {
            fetch('/api/trade', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ action: 'BUY' })
            }).then(r => r.json()).then(data => {
                alert('Compra ejecutada: ' + data.message);
                updateDashboard();
            });
        }

        function manualSell() {
            fetch('/api/trade', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ action: 'SELL' })
            }).then(r => r.json()).then(data => {
                alert('Venta ejecutada: ' + data.message);
                updateDashboard();
            });
        }

        // Actualizar cada 2 segundos
        updateDashboard();
        setInterval(updateDashboard, 2000);
    </script>
</body>
</html>
"""

# ============================================================================
# RUTAS
# ============================================================================

@app.route('/')
def index():
    if 'user' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        
        USERS['admin'] = {
            'password_hash': hash_password('RyzA_jjITjuPQtV66Wwf0A'),
            'role': 'admin'
        }
        USERS['trader'] = {
            'password_hash': hash_password('SecurePass123'),
            'role': 'trader'
        }
        
        if not username or not password:
            error = "Usuario y contraseña requeridos"
        elif username not in USERS:
            error = "Usuario no encontrado"
        elif hash_password(password) != USERS[username]['password_hash']:
            error = "Contraseña incorrecta"
        else:
            session['user'] = username
            session['role'] = USERS[username]['role']
            session['login_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            return redirect(url_for('dashboard'))
    
    return render_template_string(LOGIN_TEMPLATE, error=error)

@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect(url_for('login'))
    
    return render_template_string(DASHBOARD_TEMPLATE,
                                 username=session.get('user', 'Usuario'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/api/trading-status')
def trading_status():
    """Retorna estado del trading"""
    
    # Actualizar precio
    current_price = get_current_price()
    
    # Análisis de IA
    analysis = AI_ANALYZER.analyze_prices(PRICE_HISTORY)
    
    # Evaluar entrada
    entry_eval = TRADING_ENGINE.evaluate_entry(analysis, current_price)
    
    # Auto trading
    if request.args.get('auto_trade') == 'true' and entry_eval['should_trade']:
        trade = TRADING_ENGINE.open_trade(
            action=entry_eval['action'],
            entry_price=entry_eval['entry_price'],
            stop_loss=entry_eval['stop_loss'],
            take_profit=entry_eval['take_profit'],
            position_size=entry_eval['position_size']
        )
    
    # Actualizar trades
    TRADING_ENGINE.update_trades(current_price)
    
    return jsonify({
        'balance': TRADING_ENGINE.balance,
        'equity': TRADING_ENGINE.equity,
        'current_price': current_price,
        'open_trades': list(TRADING_ENGINE.open_trades.values()),
        'open_trades_count': len(TRADING_ENGINE.open_trades),
        'analysis': analysis,
        'price_history': PRICE_HISTORY[-30:],
        'stats': TRADING_ENGINE.get_statistics()
    })

@app.route('/api/trade', methods=['POST'])
def trade():
    """Ejecutar trade manual"""
    
    data = request.json
    action = data.get('action', 'BUY')
    current_price = PRICE_HISTORY[-1]
    
    # Abrir trade
    trade = TRADING_ENGINE.open_trade(
        action=action,
        entry_price=current_price,
        stop_loss=current_price - 0.001,
        take_profit=current_price + 0.002,
        position_size=100
    )
    
    return jsonify({
        'success': True,
        'message': f'{action} ejecutado a {current_price:.4f}',
        'trade': trade
    })

# ============================================================================
# MAIN
# ============================================================================

if __name__ == '__main__':
    print("\n" + "=" * 80)
    print("🤖 PROFESSIONAL TRADING SYSTEM + IA")
    print("=" * 80)
    print()
    print("✅ Inicializando sistema con IA...")
    print()
    print("🌐 ACCESO:")
    print("   URL:      http://localhost:5000")
    print()
    print("🔐 CREDENCIALES:")
    print("   Admin:    admin / RyzA_jjITjuPQtV66Wwf0A")
    print("   Demo:     trader / SecurePass123")
    print()
    print("=" * 80)
    print("🚀 Sistema iniciado - Abre: http://localhost:5000")
    print("=" * 80)
    print()
    
    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)
