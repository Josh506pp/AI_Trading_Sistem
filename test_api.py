#!/usr/bin/env python
"""
Script para verificar que el API devuelve datos correctos para el gráfico.
Ejecutar: python test_api.py
"""

import sys
import os
import json
from threading import Thread
import time
import requests

# Agregar src al path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def run_server():
    """Ejecutar servidor en thread separado."""
    try:
        from app import app, init_db
        with app.app_context():
            init_db(app)
        app.run(debug=False, host='127.0.0.1', port=5000, use_reloader=False, threaded=True)
    except Exception as e:
        print(f"❌ Error iniciando servidor: {e}")
        import traceback
        traceback.print_exc()

def test_api():
    """Probar endpoints del API."""
    print("🧪 Iniciando tests del API...")
    print("=" * 60)
    
    # Iniciar servidor en background
    server_thread = Thread(target=run_server, daemon=True)
    server_thread.start()
    
    # Esperar a que el servidor inicie
    print("\n⏳ Esperando que el servidor inicie...")
    time.sleep(3)
    
    base_url = "http://localhost:5000"
    
    try:
        # Test 1: GET /api/status
        print("\n📌 TEST 1: GET /api/status")
        print("-" * 60)
        response = requests.get(f"{base_url}/api/status")
        
        if response.status_code != 200:
            print(f"❌ Error: {response.status_code}")
            print(response.text)
            return False
        
        data = response.json()
        print(f"✅ Status: {response.status_code}")
        
        # Verificar campos necesarios
        required_fields = ['price', 'symbol', 'decimals', 'candles', 'balance']
        for field in required_fields:
            if field in data:
                print(f"  ✅ {field}: {type(data[field]).__name__}")
            else:
                print(f"  ❌ Falta: {field}")
                return False
        
        # Verificar candles
        candles = data.get('candles', [])
        print(f"\n📊 Datos del gráfico:")
        print(f"  - Candles: {len(candles)} puntos")
        
        if len(candles) > 0:
            print(f"  - Primer candle: {candles[0]}")
            print(f"  - Último candle: {candles[-1]}")
            
            # Verificar estructura de candles
            first = candles[0]
            if isinstance(first, dict):
                required_candle_fields = ['c', 'o', 'h', 'l']
                missing = [f for f in required_candle_fields if f not in first]
                if missing:
                    print(f"  ⚠️  Candles sin campos: {missing}")
                else:
                    print(f"  ✅ Estructura de candles correcta")
        else:
            print(f"  ⚠️  No hay candles disponibles")
        
        # Test 2: Verificar que los datos son numéricos
        print(f"\n🔢 Validación de datos:")
        for i, candle in enumerate(candles[:5]):  # Mostrar primeros 5
            try:
                if isinstance(candle, dict):
                    closing = float(candle.get('c', 0))
                else:
                    closing = float(candle)
                print(f"  ✅ Candle {i}: {closing}")
            except ValueError as e:
                print(f"  ❌ Candle {i}: no es numérico - {e}")
                return False
        
        # Test 3: Simular lo que hace JavaScript
        print(f"\n⚙️  Simulación del cliente (JavaScript):")
        
        chartDataArr = data.get('candles', data.get('prices', []))
        useCandles = (len(chartDataArr) > 0 and 
                     isinstance(chartDataArr[0], dict) and 
                     'c' in chartDataArr[0])
        
        print(f"  - Usa candles: {useCandles}")
        
        # Extraer datos como haría JavaScript
        chartData = []
        for item in chartDataArr:
            if useCandles:
                val = float(item.get('c', 0))
            else:
                val = float(item if isinstance(item, (int, float)) else item.get('y', 0))
            chartData.append(val)
        
        print(f"  - Datos extraídos: {len(chartData)} valores")
        
        if len(chartData) > 0:
            print(f"  - Rango de precios: {min(chartData):.5f} - {max(chartData):.5f}")
            print(f"  - Primer valor: {chartData[0]:.5f}")
            print(f"  - Último valor: {chartData[-1]:.5f}")
            
            if chartData[-1] > chartData[-2]:
                print(f"  🟢 Última actualización: SUBE")
            else:
                print(f"  🔴 Última actualización: BAJA")
        
        print("\n" + "=" * 60)
        print("✅ TODOS LOS TESTS PASARON")
        print("=" * 60)
        
        print("\n💡 Si el gráfico aún no se muestra:")
        print("   1. Abre http://localhost:5000/dashboard")
        print("   2. Presiona F12 para abrir Developer Tools")
        print("   3. Ve a la pestaña 'Console' para ver los logs de JavaScript")
        print("   4. Busca mensajes de error relacionados con 'Chart'")
        
        return True
        
    except requests.exceptions.ConnectionError:
        print("❌ Error: No se puede conectar al servidor")
        print("   El servidor puede estar tardando más en iniciar")
        return False
    except Exception as e:
        print(f"❌ Error inesperado: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    try:
        success = test_api()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n👋 Test interrumpido")
        sys.exit(0)
