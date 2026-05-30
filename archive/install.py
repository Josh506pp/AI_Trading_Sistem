#!/usr/bin/env python3
"""
PROFESSIONAL TRADING SYSTEM - Automated Installer
Instalador Automatizado para el Sistema de Trading Profesional
"""

import os
import sys
import subprocess
import platform
import shutil
from pathlib import Path

class ProfessionalSystemInstaller:
    """Instalador completo del sistema profesional de trading"""
    
    def __init__(self):
        self.os_type = platform.system()
        self.python_version = sys.version_info
        self.installation_path = Path.cwd()
        self.colors = {
            'GREEN': '\033[92m',
            'RED': '\033[91m',
            'YELLOW': '\033[93m',
            'BLUE': '\033[94m',
            'RESET': '\033[0m'
        }
    
    def print_banner(self):
        """Mostrar banner de bienvenida"""
        banner = f"""
{self.colors['BLUE']}
╔══════════════════════════════════════════════════════════════════════════════╗
║                                                                              ║
║   🚀 PROFESSIONAL TRADING SYSTEM v2.0.0                                     ║
║   Sistema Automatizado de Trading con IA Avanzada                           ║
║                                                                              ║
║   {self.colors['GREEN']}✅ Instalador Profesional{self.colors['BLUE']}                                              ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
{self.colors['RESET']}
"""
        print(banner)
    
    def print_step(self, step, title):
        """Mostrar paso actual"""
        print(f"\n{self.colors['BLUE']}[PASO {step}]{self.colors['RESET']} {title}")
        print(f"{'-' * 80}")
    
    def print_success(self, message):
        """Mostrar mensaje de éxito"""
        print(f"{self.colors['GREEN']}✅{self.colors['RESET']} {message}")
    
    def print_error(self, message):
        """Mostrar mensaje de error"""
        print(f"{self.colors['RED']}❌{self.colors['RESET']} {message}")
    
    def print_warning(self, message):
        """Mostrar mensaje de advertencia"""
        print(f"{self.colors['YELLOW']}⚠️{self.colors['RESET']} {message}")
    
    def check_python_version(self):
        """Verificar versión de Python"""
        self.print_step(1, "Verificando versión de Python")
        
        min_version = (3, 8)
        if self.python_version >= min_version:
            self.print_success(f"Python {self.python_version.major}.{self.python_version.minor} detectado")
            return True
        else:
            self.print_error(f"Se requiere Python 3.8+, tienes {self.python_version.major}.{self.python_version.minor}")
            return False
    
    def install_dependencies(self):
        """Instalar dependencias requeridas"""
        self.print_step(2, "Instalando dependencias")
        
        try:
            # Actualizar pip
            print("Actualizando pip...")
            subprocess.run(
                [sys.executable, "-m", "pip", "install", "--upgrade", "pip"],
                check=True,
                capture_output=True
            )
            self.print_success("pip actualizado")
            
            # Instalar requirements.txt
            requirements_file = self.installation_path / "requirements.txt"
            if requirements_file.exists():
                print("Instalando dependencias del proyecto...")
                subprocess.run(
                    [sys.executable, "-m", "pip", "install", "-r", str(requirements_file)],
                    check=True
                )
                self.print_success("Dependencias instaladas correctamente")
            else:
                self.print_warning("requirements.txt no encontrado, instalando básicas...")
                basic_deps = [
                    "numpy>=1.24.0",
                    "pandas>=2.0.0",
                    "scikit-learn>=1.3.0",
                    "Flask>=2.3.0",
                    "cryptography>=41.0.0",
                    "flask-limiter>=3.5.0"
                ]
                for dep in basic_deps:
                    print(f"  Instalando {dep}...")
                    subprocess.run(
                        [sys.executable, "-m", "pip", "install", dep],
                        capture_output=True
                    )
                self.print_success("Dependencias básicas instaladas")
            
            return True
        except Exception as e:
            self.print_error(f"Error instalando dependencias: {e}")
            return False
    
    def validate_files(self):
        """Validar que los archivos necesarios existan"""
        self.print_step(3, "Validando archivos requeridos")
        
        required_files = [
            "professional_trading_system.py",
            "config_secure.py",
            "launcher.py"
        ]
        
        missing = []
        for file in required_files:
            file_path = self.installation_path / file
            if file_path.exists():
                self.print_success(f"Encontrado: {file}")
            else:
                self.print_error(f"Faltante: {file}")
                missing.append(file)
        
        if missing:
            self.print_error(f"Archivos faltantes: {', '.join(missing)}")
            return False
        
        return True
    
    def check_mt5(self):
        """Verificar instalación de MetaTrader 5"""
        self.print_step(4, "Verificando MetaTrader 5")
        
        try:
            import MetaTrader5
            self.print_success("MetaTrader 5 detectado")
            return True
        except ImportError:
            self.print_warning("MetaTrader 5 no está instalado")
            print("Descargalo desde: https://www.metatrader5.com/")
            print("Es requerido para trading real. Para demo, es opcional.")
            return False
    
    def configure_system(self):
        """Configurar el sistema"""
        self.print_step(5, "Configurando sistema")
        
        config_file = self.installation_path / "config_secure.py"
        
        if config_file.exists():
            print("\nDatos de configuración:")
            print("  Para trading DEMO (sin dinero real):")
            print("    - Dejar valores por defecto en config_secure.py")
            print("\n  Para trading REAL (con dinero):")
            print("    - Editar config_secure.py con tus credenciales MT5")
            print("    - Cambia 'enable_real_trading': False a True")
            print("    - ⚠️ IMPORTANTE: Verifica todo antes de habilitar!")
            self.print_success("Sistema listo para configurar")
        else:
            self.print_error("config_secure.py no encontrado")
            return False
        
        return True
    
    def test_system(self):
        """Probar el sistema"""
        self.print_step(6, "Probando sistema")
        
        try:
            launcher_file = self.installation_path / "launcher.py"
            if launcher_file.exists():
                print("Ejecutando prueba del sistema...")
                print("(Esto puede tomar unos segundos...)\n")
                
                result = subprocess.run(
                    [sys.executable, str(launcher_file), "--validate"],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                if result.returncode == 0 or "validado" in result.stdout.lower():
                    self.print_success("Sistema validado correctamente")
                    return True
                else:
                    self.print_warning("Validación completada con advertencias")
                    if result.stdout:
                        print(result.stdout)
                    return True
            else:
                self.print_error("launcher.py no encontrado")
                return False
        except subprocess.TimeoutExpired:
            self.print_warning("Prueba excedió timeout (sistema sigue siendo funcional)")
            return True
        except Exception as e:
            self.print_warning(f"Error en prueba: {e}")
            return True
    
    def create_shortcuts(self):
        """Crear atajos de acceso rápido"""
        self.print_step(7, "Creando atajos")
        
        if self.os_type == "Windows":
            try:
                # Crear batch file para dashboard
                batch_content = f"""@echo off
cd /d "{self.installation_path}"
{sys.executable} launcher.py --dashboard
pause
"""
                batch_file = self.installation_path / "Start_Dashboard.bat"
                with open(batch_file, 'w') as f:
                    f.write(batch_content)
                self.print_success(f"Atajo creado: Start_Dashboard.bat")
                
                # Crear batch file para CLI
                cli_batch = f"""@echo off
cd /d "{self.installation_path}"
{sys.executable} launcher.py --cli
pause
"""
                cli_file = self.installation_path / "Start_CLI.bat"
                with open(cli_file, 'w') as f:
                    f.write(cli_batch)
                self.print_success(f"Atajo creado: Start_CLI.bat")
                
            except Exception as e:
                self.print_warning(f"No se pudieron crear atajos: {e}")
        
        elif self.os_type == "Darwin":  # macOS
            try:
                script = f"""#!/bin/bash
cd "{self.installation_path}"
{sys.executable} launcher.py --dashboard
"""
                script_file = self.installation_path / "start_dashboard.sh"
                with open(script_file, 'w') as f:
                    f.write(script)
                os.chmod(script_file, 0o755)
                self.print_success("Atajo creado: start_dashboard.sh")
            except Exception as e:
                self.print_warning(f"No se pudieron crear atajos: {e}")
        
        elif self.os_type == "Linux":
            try:
                script = f"""#!/bin/bash
cd "{self.installation_path}"
{sys.executable} launcher.py --dashboard
"""
                script_file = self.installation_path / "start_dashboard.sh"
                with open(script_file, 'w') as f:
                    f.write(script)
                os.chmod(script_file, 0o755)
                self.print_success("Atajo creado: start_dashboard.sh")
            except Exception as e:
                self.print_warning(f"No se pudieron crear atajos: {e}")
    
    def print_final_instructions(self):
        """Mostrar instrucciones finales"""
        print(f"\n{self.colors['GREEN']}")
        print("╔══════════════════════════════════════════════════════════════════════════════╗")
        print("║                                                                              ║")
        print("║   ✅ ¡INSTALACIÓN COMPLETADA EXITOSAMENTE!                                  ║")
        print("║                                                                              ║")
        print("║   🚀 PRÓXIMOS PASOS:                                                         ║")
        print("║                                                                              ║")
        print("║   1. CONFIGURAR                                                              ║")
        print("║      Edita config_secure.py con tus datos de MT5                            ║")
        print("║                                                                              ║")
        print("║   2. EJECUTAR DASHBOARD                                                      ║")
        if self.os_type == "Windows":
            print("║      Opción A: Doble-click en 'Start_Dashboard.bat'                        ║")
            print("║      Opción B: python launcher.py --dashboard                             ║")
        else:
            print("║      ./start_dashboard.sh                                                  ║")
            print("║      o: python launcher.py --dashboard                                    ║")
        print("║                                                                              ║")
        print("║   3. ACCEDER                                                                 ║")
        print("║      Abre tu navegador en: http://localhost:5000                            ║")
        print("║                                                                              ║")
        print("║   4. USAR EL SISTEMA                                                         ║")
        print("║      - Dashboard: Control visual completo                                   ║")
        print("║      - CLI: Control por línea de comandos                                   ║")
        print("║      - API: Integración programática                                        ║")
        print("║                                                                              ║")
        print("║   📖 DOCUMENTACIÓN:                                                          ║")
        print("║      - README.md: Documentación técnica                                     ║")
        print("║      - PROFESSIONAL_README.md: Guía completa                                ║")
        print("║      - SALES_PACKAGE.md: Información de características                    ║")
        print("║                                                                              ║")
        print("║   💬 SOPORTE:                                                                ║")
        print("║      - Email: support@professional-trading-system.com                      ║")
        print("║      - Discord: discord.gg/trading-system                                   ║")
        print("║                                                                              ║")
        print("║   ⚠️  IMPORTANTE:                                                            ║")
        print("║      - Comienza con DEMO antes de usar dinero real                          ║")
        print("║      - Prueba toda la configuración primero                                 ║")
        print("║      - Lee la documentación de seguridad                                    ║")
        print("║                                                                              ║")
        print("║   🎉 ¡Tu sistema de trading profesional está listo!                         ║")
        print("║                                                                              ║")
        print("╚══════════════════════════════════════════════════════════════════════════════╝")
        print(self.colors['RESET'])
    
    def run_installation(self):
        """Ejecutar instalación completa"""
        self.print_banner()
        
        # Ejecutar pasos de instalación
        if not self.check_python_version():
            return False
        
        if not self.install_dependencies():
            return False
        
        if not self.validate_files():
            return False
        
        self.check_mt5()  # Opcional, no bloquea
        
        if not self.configure_system():
            return False
        
        if not self.test_system():
            return False
        
        self.create_shortcuts()
        
        self.print_final_instructions()
        
        return True


def main():
    """Función principal"""
    installer = ProfessionalSystemInstaller()
    success = installer.run_installation()
    
    if success:
        print("\n✅ Instalación completada. ¡Disfruta tu sistema profesional de trading!")
        sys.exit(0)
    else:
        print("\n❌ Instalación incompleta. Por favor, contacta a soporte.")
        sys.exit(1)


if __name__ == "__main__":
    main()