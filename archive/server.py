#!/usr/bin/env python3

"""
SERVER TRADING + IA - FUNCTIONAL VERSION
Dashboard with AI analysis and trading control.
"""

from flask import Flask, render_template_string, jsonify, request, redirect, session
import hashlib
import secrets
import os
import sys
import random
import threading
import time

sys.path.insert(0, os.path.dirname(__file__))
from ai_simple import AIAnalyzer, TradingEngine, mt5, MT5_AVAILABLE

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_HTTPONLY'] = True

PRICE_LOCK = threading.Lock()
MARKET_RUNNING = True
AUTO_THRESHOLD = 0.7
GLOBAL_PRICE_HISTORY = [1.0850 + random.uniform(-0.01, 0.01) for _ in range(50)]
AI_ANALYZER = AIAnalyzer()
MT5_READY = False
MT5_ACCOUNT_INFO = None


def hash_password(pwd):
    return hashlib.sha256(pwd.encode()).hexdigest()


USERS = {
    'admin': {
        'password': hash_password('RyzA_jjITjuPQtV66Wwf0A'),
        'role': 'admin',
        'email': 'admin@local',
        'auto_enabled': False
    },
    'trader': {
        'password': hash_password('SecurePass123'),
        'role': 'trader',
        'email': 'trader@local',
        'auto_enabled': True
    }
}

USER_PROFILES = {}


class UserProfile:
    def __init__(self, username: str, role: str, email: str, auto_enabled: bool):
        self.username = username
        self.role = role
        self.email = email
        self.engine = TradingEngine()
        self.auto_enabled = auto_enabled
        self.signal = {'action': 'HOLD', 'confidence': 0.0}
        self.indicators = {'rsi': 50.0, 'trend': 'SIDE'}
        self.price_history = GLOBAL_PRICE_HISTORY.copy()
        self.last_price = self.price_history[-1]
        self.analysis = {}
        self.chat_history = [
            {'sender': 'IA', 'text': 'Bienvenido. Escribe un comando: buy, sell, estado, analizar, auto on, auto off, cuenta mt5.'}
        ]

    def summary(self):
        return {
            'username': self.username,
            'role': self.role,
            'email': self.email,
            'balance': self.engine.balance,
            'equity': self.engine.equity,
            'trades_open': len(self.engine.trades),
            'auto_enabled': self.auto_enabled,
            'signal': self.signal,
            'rsi': self.indicators.get('rsi', 50),
            'trend': self.indicators.get('trend', 'SIDE'),
            'last_price': self.last_price,
            'stats': self.engine.stats()
        }


HTML_LOGIN = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Trading + IA</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            background: linear-gradient(135deg, #667eea, #764ba2);
            height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            margin: 0;
        }
        .login-box {
            background: white;
            padding: 40px;
            border-radius: 10px;
            box-shadow: 0 10px 25px rgba(0,0,0,0.2);
            width: 100%;
            max-width: 400px;
        }
        .login-box h1 {
            color: #667eea;
            text-align: center;
            margin-bottom: 30px;
        }
        .form-group {
            margin-bottom: 20px;
        }
        label {
            display: block;
            color: #333;
            font-weight: bold;
            margin-bottom: 8px;
        }
        input {
            width: 100%;
            padding: 12px;
            border: 1px solid #ddd;
            border-radius: 5px;
            font-size: 14px;
            box-sizing: border-box;
        }
        input:focus {
            outline: none;
            border-color: #667eea;
        }
        button {
            width: 100%;
            padding: 12px;
            background: linear-gradient(135deg, #667eea, #764ba2);
            color: white;
            border: none;
            border-radius: 5px;
            font-size: 16px;
            font-weight: bold;
            cursor: pointer;
        }
        button:hover {
            opacity: 0.9;
        }
        .error {
            color: red;
            margin-bottom: 20px;
        }
        .creds {
            margin-top: 30px;
            padding-top: 30px;
            border-top: 1px solid #eee;
            font-size: 12px;
            color: #666;
        }
        .creds code {
            background: #f5f5f5;
            padding: 4px;
            border-radius: 3px;
        }
    </style>
</head>
<body>
    <div class="login-box">
        <h1>Trading + IA</h1>
        {% if error %}<div class="error">{{ error }}</div>{% endif %}
        <form method="POST">
            <div class="form-group">
                <label>Usuario</label>
                <input type="text" name="user" required>
            </div>
            <div class="form-group">
                <label>Contrasena</label>
                <input type="password" name="pass" required>
            </div>
            <button type="submit">Entrar</button>
        </form>
        <div class="creds">
            <strong>Admin:</strong> <code>admin</code> / <code>RyzA_jjITjuPQtV66Wwf0A</code><br>
            <strong>Demo:</strong> <code>trader</code> / <code>SecurePass123</code>
        </div>
    </div>
</body>
</html>
"""

HTML_DASHBOARD = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Dashboard Trading</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@3.9.1/dist/chart.min.js"></script>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        html, body {
            min-height: 100%;
            overflow-x: hidden;
            overflow-y: auto;
        }
        body {
            font-family: Arial, sans-serif;
            background: #f5f5f5;
            position: relative;
        }
        .navbar {
            background: linear-gradient(135deg, #667eea, #764ba2);
            color: white;
            padding: 20px 40px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            position: relative;
            z-index: 1;
        }
        .navbar a {
            color: white;
            text-decoration: none;
            background: rgba(255,255,255,0.2);
            padding: 8px 15px;
            border-radius: 5px;
            cursor: pointer;
        }
        .container {
            max-width: 1400px;
            margin: 20px auto;
            padding: 20px;
        }
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }
        .card {
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        .card h3 {
            color: #667eea;
            margin-bottom: 10px;
            font-size: 14px;
        }
        .stat {
            font-size: 28px;
            font-weight: bold;
            color: #667eea;
            margin: 10px 0;
        }
        .signal {
            padding: 15px;
            border-radius: 8px;
            margin: 10px 0;
            border-left: 4px solid;
        }
        .buy { background: #e8f5e9; border-color: #4caf50; color: #2e7d32; }
        .sell { background: #ffebee; border-color: #f44336; color: #c62828; }
        .hold { background: #fff3e0; border-color: #ff9800; color: #e65100; }
        .btn {
            padding: 10px 20px;
            margin: 5px;
            background: #667eea;
            color: white;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-size: 14px;
        }
        .btn:hover { background: #764ba2; }
        .btn-green { background: #4caf50; }
        .btn-red { background: #f44336; }
        .chart-container { overflow: hidden; border-radius: 10px; }
        .chart { min-height: 320px; height: 320px; margin-top: 20px; display: block; width: 100%; }
        table {
            width: 100%;
            border-collapse: collapse;
        }
        th, td {
            padding: 10px;
            text-align: left;
            border-bottom: 1px solid #eee;
        }
        th { background: #f5f5f5; font-weight: bold; }
        tr:hover { background: #fafafa; }
        .green { color: #4caf50; }
        .red { color: #f44336; }
    </style>
</head>
<body>
    <div class="navbar">
        <h1>Trading System + IA</h1>
        <a href="/logout">Logout</a>
    </div>
    <div class="container">
        <h2>Welcome {{ user }}!</h2>
        <div class="grid">
            <div class="card">
                <h3>Balance</h3>
                <div class="stat" id="bal">$10,000</div>
            </div>
            <div class="card">
                <h3>Equity</h3>
                <div class="stat" id="eq">$10,000</div>
            </div>
            <div class="card">
                <h3>Price</h3>
                <div class="stat" id="price">1.0850</div>
            </div>
            <div class="card">
                <h3>Trades</h3>
                <div class="stat" id="trades">0</div>
            </div>
        </div>
        <div class="grid">
            <div class="card" style="grid-column: 1/-1;">
                <h3>AI Analysis</h3>
                <div id="signal" class="signal hold"><strong>Loading...</strong></div>
            </div>
        </div>
        <div class="card">
            <h3>Price Chart</h3>
            <div class="chart-container">
                <canvas id="chart" class="chart"></canvas>
            </div>
        </div>
        <div class="card">
            <h3>Controls</h3>
            <div style="margin-bottom: 10px;">
                <strong>Auto IA:</strong> <span id="auto-status">OFF</span>
            </div>
            <button class="btn btn-green" onclick="buy()">BUY</button>
            <button class="btn btn-red" onclick="sell()">SELL</button>
            <button class="btn" onclick="toggleAuto()">Toggle Auto IA</button>
            <button class="btn btn-red" onclick="closeAllTrades()">Cerrar todos los trades</button>
        </div>
        <div class="card">
            <h3>Open Trades</h3>
            <table>
                <thead>
                    <tr>
                        <th>ID</th>
                        <th>Action</th>
                        <th>Entry</th>
                        <th>P&L</th>
                    </tr>
                </thead>
                <tbody id="trades-list">
                    <tr><td colspan="4" style="text-align:center">-</td></tr>
                </tbody>
            </table>
        </div>
        <div class="card">
            <h3>Statistics</h3>
            <table>
                <tr><td>Total Trades:</td><td id="stat-total">0</td></tr>
                <tr><td>Win Rate:</td><td id="stat-wr">0%</td></tr>
                <tr><td>Total P&L:</td><td id="stat-pl">$0</td></tr>
            </table>
        </div>
        <div class="card">
            <h3>MT5 Account</h3>
            <div class="stat" id="mt5-status">Desconocido</div>
            <div style="margin-top:10px; color:#333; font-size:14px;" id="mt5-account">Conecta MetaTrader 5 para ver el estado de la cuenta.</div>
        </div>
        <div class="card">
            <h3>Chat IA</h3>
            <div id="chat-window" style="height:240px; overflow-y:auto; background:#fafafa; border:1px solid #ddd; padding:12px; border-radius:10px; margin-bottom:12px;">Bienvenido. Escribe un comando: buy, sell, estado, analizar, auto on, auto off, cuenta mt5.</div>
            <input id="chat-input" type="text" placeholder="Escribe tu comando aquí..." style="width:100%; padding:12px; border:1px solid #ddd; border-radius:8px; margin-bottom:10px;">
            <button class="btn btn-green" onclick="sendChat()">Enviar Chat IA</button>
        </div>
    </div>
    <script>
        let chart = null;
        function update() {
            fetch('/api/status').then(r => r.json()).then(d => {
                if (d.error) {
                    return;
                }
                document.getElementById('bal').innerText = '$' + d.balance.toFixed(2);
                document.getElementById('eq').innerText = '$' + d.equity.toFixed(2);
                document.getElementById('price').innerText = d.price.toFixed(4);
                document.getElementById('trades').innerText = d.trades_open;
                document.getElementById('auto-status').innerText = d.auto_enabled ? 'ON' : 'OFF';
                const s = d.signal;
                let html = '<strong>' + s.action + '</strong> - ' + (s.confidence * 100).toFixed(0) + '%<br>';
                html += 'RSI: ' + d.rsi.toFixed(1) + ' | Trend: ' + d.trend;
                document.getElementById('signal').className = 'signal ' + s.action.toLowerCase();
                document.getElementById('signal').innerHTML = html;
                let tlist = '';
                if (d.trades_list.length > 0) {
                    d.trades_list.forEach(t => {
                        const color = t.pl >= 0 ? 'green' : 'red';
                        tlist += '<tr><td>#' + t.id + '</td><td>' + t.action + '</td><td>' + t.entry.toFixed(4) + '</td><td class="' + color + '">' + t.pct.toFixed(2) + '%</td></tr>';
                    });
                } else {
                    tlist = '<tr><td colspan="4" style="text-align:center">-</td></tr>';
                }
                document.getElementById('trades-list').innerHTML = tlist;
                document.getElementById('stat-total').innerText = d.stats.total;
                document.getElementById('stat-wr').innerText = d.stats.wr.toFixed(1) + '%';
                document.getElementById('stat-pl').innerText = '$' + d.stats.pl.toFixed(2);
                document.getElementById('mt5-status').innerText = d.mt5_connected ? 'Conectado' : 'Desconectado';
                if (d.mt5_connected && d.mt5_info) {
                    document.getElementById('mt5-account').innerText =
                        'Login ' + d.mt5_info.login + ' | Balance $' + parseFloat(d.mt5_info.balance).toFixed(2) + ' ' + d.mt5_info.currency +
                        ' | Leverage ' + d.mt5_info.leverage;
                } else {
                    document.getElementById('mt5-account').innerText = d.mt5_message || 'No hay datos de MT5 disponibles.';
                }
                if (d.chat_history) {
                    renderChatHistory(d.chat_history);
                }
                drawChart(d.prices);
            });
        }
        function renderChatHistory(history) {
            const windowEl = document.getElementById('chat-window');
            windowEl.innerHTML = '';
            history.forEach(item => {
                const bubble = document.createElement('div');
                bubble.style.marginBottom = '10px';
                bubble.style.padding = '10px';
                bubble.style.borderRadius = '10px';
                bubble.style.background = item.sender === 'IA' ? '#eef4ff' : '#f3f3f3';
                bubble.innerHTML = '<strong>' + item.sender + ':</strong> ' + item.text;
                windowEl.appendChild(bubble);
            });
            windowEl.scrollTop = windowEl.scrollHeight;
        }
        function drawChart(prices) {
            const ctx = document.getElementById('chart').getContext('2d');
            if (chart) chart.destroy();
            chart = new Chart(ctx, {
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
                    plugins: { legend: { display: false } },
                    scales: { 
                        y: { beginAtZero: false },
                        x: { display: false }
                    },
                    interaction: {
                        intersect: false,
                        mode: 'index'
                    }
                }
            });
        }
        function buy() {
            fetch('/api/buy', { method: 'POST' }).then(r => r.json()).then(d => { alert('BUY executed at ' + d.price.toFixed(4)); update(); });
        }
        function sell() {
            fetch('/api/sell', { method: 'POST' }).then(r => r.json()).then(d => { alert('SELL executed at ' + d.price.toFixed(4)); update(); });
        }
        function toggleAuto() {
            fetch('/api/toggle-auto', { method: 'POST' }).then(r => r.json()).then(d => {
                document.getElementById('auto-status').innerText = d.auto_enabled ? 'ON' : 'OFF';
                alert('Auto IA ' + (d.auto_enabled ? 'ENABLED' : 'DISABLED'));
                update();
            });
        }
        function addChatLine(sender, text) {
            const windowEl = document.getElementById('chat-window');
            const bubble = document.createElement('div');
            bubble.style.marginBottom = '10px';
            bubble.style.padding = '10px';
            bubble.style.borderRadius = '10px';
            bubble.style.background = sender === 'IA' ? '#eef4ff' : '#f3f3f3';
            bubble.innerHTML = '<strong>' + sender + ':</strong> ' + text;
            windowEl.appendChild(bubble);
            windowEl.scrollTop = windowEl.scrollHeight;
        }
        function sendChat() {
            const input = document.getElementById('chat-input');
            const message = input.value.trim();
            if (!message) return;
            input.value = '';
            fetch('/api/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message })
            }).then(r => r.json()).then(d => {
                if (d.response) {
                    update();
                }
            });
        }
        function closeAllTrades() {
            fetch('/api/close-all', { method: 'POST' })
                .then(r => r.json())
                .then(d => {
                    if (d.success) {
                        alert('Se cerraron ' + d.closed + ' trades.');
                    } else {
                        alert('No se pudieron cerrar los trades.');
                    }
                    update();
                });
        }
        update();
        setInterval(update, 1000);
    </script>
</body>
</html>
"""

HTML_ADMIN_DASHBOARD = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Admin Dashboard - Trading IA</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        html, body { min-height: 100%; overflow-x: hidden; overflow-y: auto; }
        body { font-family: Arial, sans-serif; background: #f4f7fb; }
        .navbar { background: linear-gradient(135deg, #1f3c88, #4b6cb7); color: white; padding: 20px 40px; display: flex; justify-content: space-between; align-items: center; position: relative; z-index: 1; }
        .navbar a { color: white; text-decoration: none; background: rgba(255,255,255,0.2); padding: 10px 15px; border-radius: 6px; }
        .container { max-width: 1400px; margin: 20px auto; padding: 20px; }
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 20px; margin-bottom: 20px; }
        .card { background: white; border-radius: 14px; padding: 20px; box-shadow: 0 12px 30px rgba(0,0,0,0.08); }
        .card h3 { margin-bottom: 16px; color: #1f3c88; }
        .search-box input { width: 100%; padding: 14px 16px; border: 1px solid #d9e2ef; border-radius: 12px; }
        table { width: 100%; border-collapse: collapse; }
        th, td { padding: 14px 12px; border-bottom: 1px solid #eef2f7; text-align: left; }
        th { background: #f6f8fb; color: #334e68; }
        tr:hover { background: #f0f4f9; }
        .btn { padding: 10px 16px; border: none; border-radius: 10px; cursor: pointer; color: white; font-weight: bold; }
        .btn-success { background: #38a169; }
        .btn-danger { background: #e53e3e; }
        .badge { display: inline-block; padding: 6px 10px; border-radius: 999px; font-size: 12px; color: white; }
        .badge-on { background: #38a169; }
        .badge-off { background: #a0aec0; }
        .info-list { list-style: none; margin-top: 10px; }
        .info-list li { margin-bottom: 10px; color: #475569; }
        @media (max-width: 768px) { .navbar { flex-direction: column; gap: 10px; } }
    </style>
</head>
<body>
    <div class="navbar">
        <h1>Admin - Control IA y Usuarios</h1>
        <a href="/logout">Logout</a>
    </div>
    <div class="container">
        <div class="grid">
            <div class="card search-box">
                <h3>Buscar Usuarios</h3>
                <input id="userSearch" type="text" placeholder="Buscar por usuario, correo o rol..." oninput="renderUsers()">
            </div>
            <div class="card">
                <h3>Resumen Global</h3>
                <ul class="info-list">
                    <li id="summary-count">Usuarios cargados: 0</li>
                    <li id="summary-auto">IA automatica activa: 0</li>
                    <li id="summary-open">Trades abiertos totales: 0</li>
                    <li id="summary-balance">Balance total combinado: $0</li>
                </ul>
            </div>
        </div>
        <div class="card">
            <h3>Usuarios del Sistema</h3>
            <table>
                <thead>
                    <tr>
                        <th>Usuario</th>
                        <th>Rol</th>
                        <th>Email</th>
                        <th>Balance</th>
                        <th>Equity</th>
                        <th>Trades</th>
                        <th>Auto IA</th>
                        <th>Acciones</th>
                    </tr>
                </thead>
                <tbody id="usersTableBody"></tbody>
            </table>
        </div>
    </div>
    <script>
        let allUsers = [];
        async function loadUsers() {
            const response = await fetch('/api/admin/users');
            if (!response.ok) return;
            allUsers = await response.json();
            renderUsers();
            renderSummary();
        }
        function renderUsers() {
            const filter = document.getElementById('userSearch').value.toLowerCase();
            const filtered = allUsers.filter(u => {
                return u.username.toLowerCase().includes(filter)
                    || u.email.toLowerCase().includes(filter)
                    || u.role.toLowerCase().includes(filter);
            });
            const rows = filtered.map(u => {
                return `<tr>
                    <td>${u.username}</td>
                    <td>${u.role}</td>
                    <td>${u.email}</td>
                    <td>$${u.balance.toFixed(2)}</td>
                    <td>$${u.equity.toFixed(2)}</td>
                    <td>${u.trades_open}</td>
                    <td><span class="badge ${u.auto_enabled ? 'badge-on' : 'badge-off'}">${u.auto_enabled ? 'ON' : 'OFF'}</span></td>
                    <td>
                        <button class="btn btn-success" onclick="toggleUserAuto('${u.username}')">Auto</button>
                        <button class="btn btn-danger" onclick="closeUserTrades('${u.username}')">Cerrar Trades</button>
                    </td>
                </tr>`;
            }).join('');
            document.getElementById('usersTableBody').innerHTML = rows || '<tr><td colspan="8" style="text-align:center">No hay usuarios</td></tr>';
        }
        function renderSummary() {
            const activeAuto = allUsers.filter(u => u.auto_enabled).length;
            const openTrades = allUsers.reduce((sum, u) => sum + u.trades_open, 0);
            const balanceTotal = allUsers.reduce((sum, u) => sum + u.balance, 0);
            document.getElementById('summary-count').innerText = `Usuarios cargados: ${allUsers.length}`;
            document.getElementById('summary-auto').innerText = `IA automatica activa: ${activeAuto}`;
            document.getElementById('summary-open').innerText = `Trades abiertos totales: ${openTrades}`;
            document.getElementById('summary-balance').innerText = `Balance total combinado: $${balanceTotal.toFixed(2)}`;
        }
        async function toggleUserAuto(username) {
            await fetch(`/api/admin/user/${username}/toggle-auto`, { method: 'POST' });
            loadUsers();
        }
        async function closeUserTrades(username) {
            await fetch(`/api/admin/user/${username}/close-trades`, { method: 'POST' });
            loadUsers();
        }
        loadUsers();
        setInterval(loadUsers, 3000);
    </script>
</body>
</html>
"""


def create_user_profile(username):
    user = USERS.get(username)
    if not user:
        return None
    if username not in USER_PROFILES:
        USER_PROFILES[username] = UserProfile(
            username=username,
            role=user['role'],
            email=user.get('email', ''),
            auto_enabled=user.get('auto_enabled', False)
        )
    return USER_PROFILES[username]


def get_user_profile(username):
    profile = USER_PROFILES.get(username)
    if not profile:
        profile = create_user_profile(username)
    return profile


def advance_price():
    with PRICE_LOCK:
        last = GLOBAL_PRICE_HISTORY[-1]
        change = random.uniform(-0.0005, 0.0005)
        new_price = max(0.9, last + change)
        GLOBAL_PRICE_HISTORY.append(new_price)
        if len(GLOBAL_PRICE_HISTORY) > 200:
            GLOBAL_PRICE_HISTORY.pop(0)
        return new_price


def init_mt5_connection():
    global MT5_READY, MT5_ACCOUNT_INFO
    if not MT5_AVAILABLE or mt5 is None:
        MT5_READY = False
        MT5_ACCOUNT_INFO = None
        return False
    try:
        MT5_READY = mt5.initialize()
        if MT5_READY:
            account_info = mt5.account_info()
            MT5_ACCOUNT_INFO = account_info._asdict() if account_info else None
        return MT5_READY
    except Exception as e:
        print(f"MT5 init error: {e}")
        MT5_READY = False
        MT5_ACCOUNT_INFO = None
        return False


def get_mt5_price():
    if not MT5_AVAILABLE or not MT5_READY or mt5 is None:
        return None
    try:
        tick = mt5.symbol_info_tick("EURUSD")
        if tick:
            return tick.ask
    except Exception as e:
        print(f"MT5 price error: {e}")
    return None


def get_mt5_account_info():
    if not MT5_AVAILABLE or not MT5_READY or mt5 is None:
        return {'connected': False, 'message': 'MT5 not available or not initialized'}
    try:
        account_info = mt5.account_info()
        if account_info is None:
            return {'connected': False, 'message': 'MT5 terminal disconnected'}
        return {'connected': True, 'account': account_info._asdict()}
    except Exception as e:
        return {'connected': False, 'message': str(e)}


def run_local_market():
    while MARKET_RUNNING:
        price = get_mt5_price() or advance_price()
        for profile in list(USER_PROFILES.values()):
            profile.price_history.append(price)
            if len(profile.price_history) > 200:
                profile.price_history.pop(0)
            profile.last_price = price
            profile.engine.update(price)

            if len(profile.price_history) >= 20:
                analysis = AI_ANALYZER.analyze_prices(profile.price_history[-20:])
            else:
                analysis = {
                    'signal': {'action': 'HOLD', 'confidence': 0.0},
                    'indicators': {'rsi': 50.0, 'trend': 'SIDE'}
                }
            profile.signal = analysis.get('signal', {'action': 'HOLD', 'confidence': 0.0})
            profile.indicators = analysis.get('indicators', {'rsi': 50.0, 'trend': 'SIDE'})
            profile.analysis = analysis
            if profile.auto_enabled and profile.signal['action'] != 'HOLD' and profile.signal['confidence'] > AUTO_THRESHOLD:
                if len(profile.engine.trades) < 3:
                    profile.engine.open_trade(profile.signal['action'], price)
        time.sleep(1)


def get_profile_response(profile):
    mt5_info = get_mt5_account_info()
    account_info = mt5_info.get('account') if mt5_info.get('connected') else None
    return {
        'price': profile.last_price,
        'balance': profile.engine.balance,
        'equity': profile.engine.equity,
        'trades_open': len(profile.engine.trades),
        'trades_list': list(profile.engine.trades.values()),
        'signal': profile.signal,
        'rsi': profile.indicators.get('rsi', 50),
        'trend': profile.indicators.get('trend', 'SIDE'),
        'prices': profile.price_history[-30:],
        'stats': profile.engine.stats(),
        'auto_enabled': profile.auto_enabled,
        'mt5_connected': bool(mt5_info.get('connected')),
        'mt5_info': account_info,
        'mt5_message': mt5_info.get('message', ''),
        'chat_history': profile.chat_history
    }


for username in USERS:
    create_user_profile(username)


@app.route('/')
def index():
    if 'user' in session:
        return redirect('/dashboard')
    return redirect('/login')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = request.form.get('user', '').strip()
        pwd = request.form.get('pass', '').strip()
        stored = USERS.get(user)
        if stored and hash_password(pwd) == stored['password']:
            session.permanent = True
            session['user'] = user
            create_user_profile(user)
            return redirect('/dashboard')
        return render_template_string(HTML_LOGIN, error='Invalid credentials')
    return render_template_string(HTML_LOGIN)


@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect('/login')
    username = session['user']
    user = USERS.get(username, {})
    if user.get('role') == 'admin':
        return render_template_string(HTML_ADMIN_DASHBOARD)
    return render_template_string(HTML_DASHBOARD, user=username)


@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')


@app.route('/api/status')
def status():
    if 'user' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    username = session['user']
    profile = get_user_profile(username)
    if not profile:
        return jsonify({'error': 'Profile not found'}), 404
    return jsonify(get_profile_response(profile))


def process_chat_message(profile, message):
    if not message:
        response = 'Por favor ingresa un comando de chat.'
        profile.chat_history.append({'sender': 'IA', 'text': response})
        return response
    profile.chat_history.append({'sender': 'Yo', 'text': message})
    text = message.strip().lower()

    if 'buy' in text or 'comprar' in text:
        trade = profile.engine.open_trade('BUY', profile.last_price)
        response = f'✅ Orden de compra ejecutada localmente a {profile.last_price:.5f}. Trade ID {trade["id"]}.'
        profile.chat_history.append({'sender': 'IA', 'text': response})
        return response
    if 'sell' in text or 'vender' in text:
        trade = profile.engine.open_trade('SELL', profile.last_price)
        return f'✅ Orden de venta ejecutada localmente a {profile.last_price:.5f}. Trade ID {trade["id"]}.'
    if 'cerrar' in text and 'trade' in text or 'cerrar' in text and 'todos' in text:
        closed = profile.engine.close_all(profile.last_price)
        return f'🚪 Trades cerrados: {len(closed)}. Precio actual {profile.last_price:.5f}.'
    if 'auto' in text or 'autónomo' in text or 'autonomo' in text:
        if 'desactivar' in text or 'detener' in text or 'off' in text:
            profile.auto_enabled = False
            response = '⚙️ Modo automático de IA DESACTIVADO. El bot controla menos operaciones.'
            profile.chat_history.append({'sender': 'IA', 'text': response})
            return response
        profile.auto_enabled = True
        response = '⚙️ Modo automático de IA ACTIVADO. El bot abrirá trades según la señal.'
        profile.chat_history.append({'sender': 'IA', 'text': response})
        return response
    if 'estado' in text or 'status' in text or 'balance' in text:
        stats = profile.engine.stats()
        return (f'📊 Balance ${profile.engine.balance:.2f}, Equity ${profile.engine.equity:.2f}, ' 
                f'Trades abiertos {len(profile.engine.trades)}, WR {stats["wr"]:.1f}%')
    if 'mt5' in text or 'cuenta' in text:
        mt5_info = get_mt5_account_info()
        if mt5_info.get('connected'):
            acct = mt5_info['account']
            return (f'📈 MT5 conectado: Login {acct.get("login")} - Balance ${acct.get("balance",0):.2f} ' 
                    f'{acct.get("currency","")} - Leverage {acct.get("leverage",0)}')
        return f'⚠️ MT5 desconectado: {mt5_info.get("message", "Sin datos")}.'
    if 'analizar' in text or 'analyze' in text or 'señal' in text:
        analysis = profile.analysis or AI_ANALYZER.analyze_prices(profile.price_history[-20:])
        signal = analysis.get('signal', {'action': 'HOLD', 'confidence': 0.0})
        response = (f'🔎 Señal {signal["action"]} con confianza {signal["confidence"]*100:.1f}% - '
                f'RSI {profile.indicators.get("rsi", 50):.1f}, Trend {profile.indicators.get("trend", "SIDE")}')
        profile.chat_history.append({'sender': 'IA', 'text': response})
        return response
    response = '💬 Comando no reconocido. Prueba: buy, sell, estado, analizar, auto on, auto off, mt5'
    profile.chat_history.append({'sender': 'IA', 'text': response})
    return response


@app.route('/api/chat', methods=['POST'])
def chat():
    if 'user' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    username = session['user']
    profile = get_user_profile(username)
    if not profile:
        return jsonify({'error': 'Profile not found'}), 404
    data = request.get_json(silent=True) or {}
    message = data.get('message', '')
    response = process_chat_message(profile, message)
    return jsonify({'response': response})


@app.route('/api/close-all', methods=['POST'])
def close_all():
    if 'user' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    username = session['user']
    profile = get_user_profile(username)
    closed = profile.engine.close_all(profile.last_price)
    return jsonify({'success': True, 'closed': len(closed), 'current_price': profile.last_price})


@app.route('/api/toggle-auto', methods=['POST'])
def toggle_auto():
    if 'user' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    username = session['user']
    user = USERS.get(username, {})
    if user.get('role') == 'admin':
        return jsonify({'error': 'Admin cannot toggle auto IA here'}), 403
    profile = get_user_profile(username)
    profile.auto_enabled = not profile.auto_enabled
    return jsonify({'success': True, 'auto_enabled': profile.auto_enabled})


@app.route('/api/buy', methods=['POST'])
def buy():
    if 'user' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    username = session['user']
    profile = get_user_profile(username)
    price = advance_price()
    profile.price_history.append(price)
    profile.engine.update(price)
    trade = profile.engine.open_trade('BUY', price)
    return jsonify({'success': True, 'price': price, 'trade': trade})


@app.route('/api/sell', methods=['POST'])
def sell():
    if 'user' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    username = session['user']
    profile = get_user_profile(username)
    price = advance_price()
    profile.price_history.append(price)
    profile.engine.update(price)
    trade = profile.engine.open_trade('SELL', price)
    return jsonify({'success': True, 'price': price, 'trade': trade})


@app.route('/api/admin/users')
def admin_users():
    if 'user' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    username = session['user']
    if USERS.get(username, {}).get('role') != 'admin':
        return jsonify({'error': 'Access denied'}), 403
    users = [get_user_profile(user).summary() for user in USERS]
    return jsonify(users)


@app.route('/api/admin/user/<target>/toggle-auto', methods=['POST'])
def admin_toggle_auto(target):
    if 'user' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    username = session['user']
    if USERS.get(username, {}).get('role') != 'admin':
        return jsonify({'error': 'Access denied'}), 403
    profile = get_user_profile(target)
    if not profile:
        return jsonify({'error': 'User not found'}), 404
    profile.auto_enabled = not profile.auto_enabled
    return jsonify({'success': True, 'username': target, 'auto_enabled': profile.auto_enabled})


@app.route('/api/admin/user/<target>/close-trades', methods=['POST'])
def admin_close_trades(target):
    if 'user' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    username = session['user']
    if USERS.get(username, {}).get('role') != 'admin':
        return jsonify({'error': 'Access denied'}), 403
    profile = get_user_profile(target)
    if not profile:
        return jsonify({'error': 'User not found'}), 404
    current_price = profile.last_price
    closed = [profile.engine.close_trade(tid, current_price) for tid in list(profile.engine.trades.keys())]
    return jsonify({'success': True, 'closed_trades': closed, 'current_price': current_price})


if __name__ == '__main__':
    init_mt5_connection()
    market_thread = threading.Thread(target=run_local_market, daemon=True)
    market_thread.start()
    print('\n' + '='*80)
    print('PROFESSIONAL TRADING SYSTEM + IA')
    print('='*80)
    print('Starting server...')
    print('Access: http://localhost:5000')
    print('Admin: admin / RyzA_jjITjuPQtV66Wwf0A')
    print('Demo: trader / SecurePass123')
    print('MT5 Connected:', MT5_READY)
    if MT5_READY:
        print('MT5 Account:', MT5_ACCOUNT_INFO.get('login') if MT5_ACCOUNT_INFO else 'Unknown')
    print('='*80)
    app.run(host='0.0.0.0', port=5000, debug=False)
