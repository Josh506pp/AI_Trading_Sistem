#!/usr/bin/env python3
"""
QUICK START - Sistema de Trading Inteligente
Guía de inicio rápido (5 minutos)
"""

# =============================================================================
# PASO 1: INSTALAR DEPENDENCIAS
# =============================================================================
"""
Ejecuta en terminal:

    pip install -r requirements.txt

Tiempo: ~2 minutos
"""

# =============================================================================
# PASO 2: IMPORTAR Y CREAR SISTEMA
# =============================================================================

from integrated_trading_system import IntegratedTradingSystem
import numpy as np

# Crear sistema con configuración por defecto
system = IntegratedTradingSystem()

print("✅ Sistema creado exitosamente\n")

# =============================================================================
# PASO 3: DEMOSTRACIÓN RÁPIDA
# =============================================================================

# 3A: Ver estado actual
print("=" * 60)
print("📊 ESTADO DEL SISTEMA")
print("=" * 60)

status = system.get_system_status()
print(f"Balance:            ${status['balance']:.2f}")
print(f"Posiciones Abiertas: {status['open_positions']}")
print(f"Total R-Multiple:   {status['total_r']:.2f}R")
print(f"Salud del Sistema:   {status['scorecard']['health_status']}")
print()

# 3B: Simular análisis de mercado
print("=" * 60)
print("📈 ANÁLISIS DE MERCADO SIMULADO")
print("=" * 60)

# Generar precios de ejemplo
prices = np.random.randn(200).cumsum() * 0.0001 + 1.0850

# Analizar
market_analysis = system.analyze_market(prices)

print(f"Tendencia:         {market_analysis['price_analysis'].trend_direction}")
print(f"Volatilidad:       {market_analysis['price_analysis'].volatility_status}")
print(f"RSI:               {market_analysis['features'].rsi:.1f}")
print(f"Momentum:          {market_analysis['features'].momentum:.6f}")
print(f"IA Predicción:     {market_analysis['ai_prediction']['expected_r_multiple']:.2f}R")
print(f"Salud del Sistema: {market_analysis['scorecard']['health_status']}")
print()

# 3C: Evaluar oportunidad de entrada
print("=" * 60)
print("💼 EVALUACIÓN DE ENTRADA")
print("=" * 60)

entry_opp = system.evaluate_entry_opportunity(prices)

if entry_opp['should_trade']:
    signal = entry_opp['signal']
    params = entry_opp['parameters']
    
    print(f"✅ SEÑAL VÁLIDA")
    print(f"Dirección:         {signal.direction.value}")
    print(f"Confianza:         {signal.confidence*100:.1f}%")
    print(f"Entrada:           {params['entry_price']:.5f}")
    print(f"Stop Loss:         {params['stop_loss']:.5f}")
    print(f"Take Profit:       {params['take_profit']:.5f}")
    print(f"Tamaño:            {params['lot_size']:.2f} lotes")
    print(f"R/R Ratio:         1:{params['risk_reward_ratio']:.2f}")
    print()
    
    # 3D: Simular apertura de trade
    print("=" * 60)
    print("📍 ABRIENDO TRADE")
    print("=" * 60)
    
    result = system.open_trade(
        direction=signal.direction.value,
        entry_price=params['entry_price'],
        stop_loss=params['stop_loss'],
        take_profit=params['take_profit'],
        lot_size=params['lot_size']
    )
    
    trade_id = result['trade_id']
    print(f"✅ Trade #{trade_id} abierto exitosamente")
    print()
    
    # 3E: Simular cierre
    print("=" * 60)
    print("🎯 CERRANDO TRADE")
    print("=" * 60)
    
    # Simular cierre en take profit
    exit_price = params['take_profit']
    
    close_result = system.close_trade(
        trade_id=trade_id,
        exit_price=exit_price,
        exit_reason='TAKE_PROFIT'
    )
    
    print(f"✅ Trade cerrado: {close_result['result']}")
    print()

else:
    print(f"❌ NO HAY SEÑAL VÁLIDA")
    print(f"Razón: {entry_opp['reason']}")
    print(f"Confianza: {entry_opp['confidence']*100:.1f}%")
    print()

# =============================================================================
# PASO 4: MODO INTERACTIVO
# =============================================================================

print("=" * 60)
print("💬 MODO INTERACTIVO")
print("=" * 60)
print()
print("Escribe el siguiente comando para iniciar modo chat interactivo:")
print()
print("    system.chat_interface.start_interactive_mode()")
print()
print("Comandos disponibles:")
print("  abre 5              - Abre 5 operaciones")
print("  status              - Estado del bot")
print("  historial 10        - Últimas 10 operaciones")
print("  riesgo 2%           - Configura riesgo a 2%")
print("  pausa               - Pausa el bot")
print("  resume              - Reanuda el bot")
print("  ayuda               - Ver todos los comandos")
print("  salir               - Cerrar el bot")
print()

# =============================================================================
# PASO 5: PRÓXIMOS PASOS
# =============================================================================

print("=" * 60)
print("🚀 PRÓXIMOS PASOS")
print("=" * 60)
print()
print("1. Leer RESUMEN_EJECUTIVO.md para entender el sistema")
print("2. Leer TRADING_SYSTEM_REDESIGN.md para conceptos")
print("3. Leer IMPLEMENTATION_GUIDE.md para uso avanzado")
print()
print("4. Ejecutar modo interactivo:")
print("   system.chat_interface.start_interactive_mode()")
print()
print("5. Validar con datos reales de MT5")
print()

# =============================================================================
# PASO 6: SCRIPTS DE UTILIDAD
# =============================================================================

print("=" * 60)
print("📝 SCRIPTS DE UTILIDAD")
print("=" * 60)
print()

def print_scorecard():
    """Imprime scorecard del sistema"""
    print(system.scorecard.get_scorecard_report())

def get_statistics():
    """Obtiene estadísticas"""
    return system.reward_calc.calculate_statistics()

def run_backtest(num_simulations=100):
    """Ejecuta backtest simple"""
    results = []
    for i in range(num_simulations):
        prices = np.random.randn(200).cumsum() * 0.0001 + 1.0850
        analysis = system.analyze_market(prices)
        results.append(analysis['ai_prediction']['expected_r_multiple'])
    
    import numpy as np
    return {
        'mean_r': np.mean(results),
        'std_r': np.std(results),
        'min_r': np.min(results),
        'max_r': np.max(results)
    }

print("Funciones útiles disponibles:")
print()
print("  print_scorecard()      - Muestra scorecard de salud")
print("  get_statistics()       - Obtiene estadísticas del sistema")
print("  run_backtest(100)      - Corre backtest de 100 simulaciones")
print()

# =============================================================================
# EJEMPLO DE USO
# =============================================================================

print("=" * 60)
print("💡 EJEMPLO: USO RÁPIDO")
print("=" * 60)
print()

print("""
# Opción 1: Modo Interactivo (Más fácil)
system.chat_interface.start_interactive_mode()

# En la consola:
# TradingBot > abre 5
# TradingBot > status
# TradingBot > historial
# TradingBot > puntos
# TradingBot > salir


# Opción 2: Programático (Más control)
import numpy as np

prices = np.random.randn(200).cumsum() * 0.0001 + 1.0850
entry = system.evaluate_entry_opportunity(prices)

if entry['should_trade']:
    result = system.open_trade(...)
    system.close_trade(...)


# Opción 3: Loop de Trading Completo
for i in range(100):
    prices = get_prices_from_mt5()  # Tu función de MT5
    
    # Analizar
    analysis = system.analyze_market(prices)
    
    # Evaluar entrada
    entry = system.evaluate_entry_opportunity(prices)
    if entry['should_trade']:
        system.open_trade(...)
    
    # Monitorear posiciones abiertas
    for trade_id in system.active_trades:
        trade = system.active_trades[trade_id]
        current_price = get_current_price()
        
        exit_eval = system.evaluate_exit_opportunity(
            trade_id, current_price, features
        )
        if exit_eval['should_exit']:
            system.close_trade(...)
    
    # Dormir
    import time
    time.sleep(5)  # Check cada 5 segundos
"""
)

print()
print("=" * 60)
print("✅ LISTO PARA USAR")
print("=" * 60)
print()
print("Tu sistema está completamente configurado y funcionando.")
print("Elige entre modo interactivo o programático y ¡comienza a tradear!")
print()
