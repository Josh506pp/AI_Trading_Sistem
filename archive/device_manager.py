#!/usr/bin/env python3
"""
PROFESSIONAL TRADING SYSTEM - Device Manager
Gestor de Dispositivos para Control de Acceso Único por Dispositivo
"""

import hashlib
import uuid
import platform
import socket
try:
    import psutil
except ImportError:
    psutil = None
from typing import Dict, Optional, Tuple
import logging
import json

class DeviceFingerprint:
    """Genera fingerprint único del dispositivo"""

    @staticmethod
    def generate_fingerprint() -> str:
        """Generar fingerprint único del dispositivo basado en hardware"""
        try:
            components = []

            # 1. MAC Address
            try:
                mac = hashlib.sha256(str(uuid.getnode()).encode()).hexdigest()[:16]
                components.append(mac)
            except:
                pass

            # 2. Hostname
            try:
                hostname = hashlib.sha256(socket.gethostname().encode()).hexdigest()[:16]
                components.append(hostname)
            except:
                pass

            # 3. Sistema Operativo + Procesador
            try:
                os_info = f"{platform.system()}{platform.release()}{platform.machine()}"
                os_hash = hashlib.sha256(os_info.encode()).hexdigest()[:16]
                components.append(os_hash)
            except:
                pass

            # 4. UUID de disco
            try:
                if platform.system() == "Windows":
                    import subprocess
                    result = subprocess.run(['wmic', 'logicaldisk', 'get', 'serialnumber'],
                                          capture_output=True, text=True)
                    disk_serial = result.stdout.strip()
                else:
                    disk_serial = "linux_disk"
                disk_hash = hashlib.sha256(disk_serial.encode()).hexdigest()[:16]
                components.append(disk_hash)
            except:
                pass

            # 5. CPU Info
            try:
                if psutil:
                    cpu_count = str(psutil.cpu_count() or 0)
                    cpu_freq = str(psutil.cpu_freq() or '')
                    cpu_info = hashlib.sha256(f"{cpu_count}{cpu_freq}".encode()).hexdigest()[:16]
                    components.append(cpu_info)
            except:
                pass

            # Combinar todos los componentes
            fingerprint = hashlib.sha256("".join(components).encode()).hexdigest()
            return fingerprint

        except Exception as e:
            logging.error(f"Error generando fingerprint: {e}")
            return hashlib.sha256(str(uuid.uuid4()).encode()).hexdigest()

    @staticmethod
    def get_device_info() -> Dict:
        """Obtener información del dispositivo actual"""
        try:
            cpu_count = None
            ram_gb = None
            
            if psutil:
                try:
                    cpu_count = psutil.cpu_count()
                    ram_bytes = psutil.virtual_memory().total
                    ram_gb = round(ram_bytes / (1024**3), 2)
                except:
                    pass
            
            info = {
                'hostname': socket.gethostname(),
                'platform': platform.system(),
                'platform_release': platform.release(),
                'platform_version': platform.version(),
                'architecture': platform.machine(),
                'processor': platform.processor(),
                'cpu_count': cpu_count,
                'ram_gb': ram_gb,
                'mac_address': ':'.join(['{:02x}'.format((uuid.getnode() >> ele) & 0xff)
                                        for ele in range(0, 48, 8)][::-1])
            }
            return info
        except Exception as e:
            logging.error(f"Error obteniendo info del dispositivo: {e}")
            return {
                'hostname': 'N/A',
                'platform': 'N/A',
                'platform_release': 'N/A',
                'platform_version': 'N/A',
                'architecture': 'N/A',
                'processor': 'N/A',
                'cpu_count': None,
                'ram_gb': None,
                'mac_address': 'N/A'
            }


class DeviceManager:
    """Gestor de dispositivos para control de acceso"""

    def __init__(self, db_manager):
        """Inicializar gestor de dispositivos"""
        self.db = db_manager
        self.logger = logging.getLogger("DeviceManager")
        self.fingerprint_generator = DeviceFingerprint()

    def generate_device_fingerprint(self) -> str:
        """Generar fingerprint del dispositivo actual"""
        return self.fingerprint_generator.generate_fingerprint()

    def get_current_device_info(self) -> Dict:
        """Obtener información del dispositivo actual"""
        return self.fingerprint_generator.get_device_info()

    def register_new_device(self, customer_id: int, ip_address: str,
                           device_name: str = None, is_primary: bool = False,
                           device_fingerprint: Optional[str] = None) -> Tuple[bool, Dict]:
        """Registrar nuevo dispositivo para el cliente"""
        try:
            # Generar fingerprint si no se proporciona uno explícitamente
            if not device_fingerprint:
                device_fingerprint = self.generate_device_fingerprint()
            device_info = self.get_current_device_info()

            # Generar nombre del dispositivo si no se proporciona
            if not device_name:
                device_name = f"{device_info.get('platform', 'Device')} - {device_info.get('hostname', 'Unknown')}"

            # Registrar en base de datos
            success, device_id = self.db.register_device(
                customer_id=customer_id,
                device_fingerprint=device_fingerprint,
                device_name=device_name,
                device_type=device_info.get('platform', ''),
                ip_address=ip_address,
                os=device_info.get('platform_version', ''),
                browser="Professional Trading System",
                is_primary=is_primary
            )

            if success:
                device_data = {
                    'id': device_id,
                    'fingerprint': device_fingerprint,
                    'name': device_name,
                    'info': device_info,
                    'registered': True
                }
                self.logger.info(f"✅ Dispositivo registrado: {device_name}")
                return True, device_data
            else:
                # El dispositivo ya estaba registrado, recuperar su fingerprint
                return True, {
                    'id': device_id,
                    'fingerprint': device_fingerprint,
                    'name': device_name,
                    'info': device_info,
                    'already_registered': True
                }

        except Exception as e:
            self.logger.error(f"❌ Error registrando dispositivo: {e}")
            return False, {'error': str(e)}

    def validate_device_session(self, customer_id: int, ip_address: str,
                               device_fingerprint: str) -> Tuple[bool, str]:
        """Validar que el dispositivo tiene derecho a acceder (SINGLE DEVICE ENFORCEMENT)"""
        try:
            # Llamar al validador de la base de datos
            return self.db.validate_device_access(customer_id, device_fingerprint, ip_address)

        except Exception as e:
            self.logger.error(f"❌ Error validando dispositivo: {e}")
            return False, str(e)

    def create_device_session(self, customer_id: int, device_fingerprint: str,
                             ip_address: str) -> Tuple[bool, str]:
        """Crear sesión de dispositivo"""
        try:
            # Obtener el ID del dispositivo
            import sqlite3
            db_conn = sqlite3.connect(self.db.db_path)
            cursor = db_conn.cursor()

            cursor.execute('''
                SELECT id FROM devices WHERE device_fingerprint = ?
            ''', (device_fingerprint,))

            result = cursor.fetchone()
            db_conn.close()

            if not result:
                return False, "Dispositivo no registrado"

            device_id = result[0]

            # Generar token de sesión
            session_token = hashlib.sha256(
                f"{customer_id}{device_fingerprint}{uuid.uuid4()}".encode()
            ).hexdigest()

            # Crear sesión
            success, token = self.db.create_session(
                customer_id=customer_id,
                device_id=device_id,
                session_token=session_token,
                ip_address=ip_address
            )

            if success:
                self.logger.info(f"✅ Sesión de dispositivo creada: Customer {customer_id}")
                return True, session_token
            else:
                return False, "Error creando sesión"

        except Exception as e:
            self.logger.error(f"❌ Error creando sesión de dispositivo: {e}")
            return False, str(e)

    def get_device_current_fingerprint(self) -> str:
        """Obtener fingerprint del dispositivo actual"""
        return self.generate_device_fingerprint()

    def check_multiple_devices(self, customer_id: int) -> Dict:
        """Verificar si cliente está usando múltiples dispositivos"""
        try:
            devices = self.db.get_customer_devices(customer_id)

            return {
                'total_devices': len(devices),
                'devices': devices,
                'active_devices': len([d for d in devices if d.get('is_active', False)])
            }

        except Exception as e:
            self.logger.error(f"❌ Error verificando dispositivos: {e}")
            return {'error': str(e)}

    def remove_device(self, customer_id: int, device_id: int) -> bool:
        """Remover dispositivo del cliente"""
        try:
            import sqlite3
            db_conn = sqlite3.connect(self.db.db_path if hasattr(self.db, 'db_path') else 'trading_system.db')
            cursor = db_conn.cursor()

            # Verificar que el dispositivo pertenece al cliente
            cursor.execute('''
                SELECT id FROM devices WHERE id = ? AND customer_id = ?
            ''', (device_id, customer_id))

            if not cursor.fetchone():
                db_conn.close()
                return False

            # Desactivar dispositivo
            cursor.execute('''
                UPDATE devices SET is_active = 0 WHERE id = ?
            ''', (device_id,))

            # Cerrar sesiones asociadas
            cursor.execute('''
                UPDATE sessions SET is_active = 0 WHERE device_id = ?
            ''', (device_id,))

            db_conn.commit()
            db_conn.close()

            self.logger.info(f"✅ Dispositivo removido: {device_id}")
            return True

        except Exception as e:
            self.logger.error(f"❌ Error removiendo dispositivo: {e}")
            return False

    def set_primary_device(self, customer_id: int, device_id: int) -> bool:
        """Establecer dispositivo como primario"""
        try:
            import sqlite3
            db_conn = sqlite3.connect(self.db.db_path if hasattr(self.db, 'db_path') else 'trading_system.db')
            cursor = db_conn.cursor()

            # Desmarcar todos como primarios
            cursor.execute('''
                UPDATE devices SET is_primary = 0 WHERE customer_id = ?
            ''', (customer_id,))

            # Marcar este como primario
            cursor.execute('''
                UPDATE devices SET is_primary = 1 WHERE id = ? AND customer_id = ?
            ''', (device_id, customer_id))

            db_conn.commit()
            db_conn.close()

            self.logger.info(f"✅ Dispositivo primario establecido: {device_id}")
            return True

        except Exception as e:
            self.logger.error(f"❌ Error estableciendo dispositivo primario: {e}")
            return False


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Test
    from database_manager import DatabaseManager
    
    db = DatabaseManager()
    device_mgr = DeviceManager(db)
    
    print("📱 Información del dispositivo actual:")
    device_info = device_mgr.get_current_device_info()
    print(json.dumps(device_info, indent=2))
    
    print("\n🔐 Fingerprint del dispositivo:")
    fp = device_mgr.generate_device_fingerprint()
    print(fp)