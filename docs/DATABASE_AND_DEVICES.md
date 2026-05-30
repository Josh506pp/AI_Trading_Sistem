# 🗄️ Professional Trading System - Sistema de Base de Datos y Control de Dispositivos

## Descripción General

Este documento detalla el sistema completo de **base de datos** y **control de dispositivos** integrado en el Professional Trading System v2.0.0.

---

## 🏗️ Arquitectura del Sistema

```
┌─────────────────────────────────────────────────────────────────┐
│                    Professional Trading System                   │
│                                                                  │
│  ┌────────────────────┐         ┌────────────────────────────┐  │
│  │   DatabaseManager  │         │    DeviceManager           │  │
│  │                    │         │                            │  │
│  │ • Customers        │────────▶│ • Fingerprinting           │  │
│  │ • Devices          │         │ • Device Validation        │  │
│  │ • Sessions         │         │ • Single Device Enforcement│  │
│  │ • Payments         │         │ • Hardware Detection       │  │
│  │ • Audit Logs       │         │                            │  │
│  │ • Blocked Attempts │         │                            │  │
│  └────────────────────┘         └────────────────────────────┘  │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │         ProfessionalAuthenticator (Enhanced)            │    │
│  │  - Integración con DatabaseManager                      │    │
│  │  - Validación de dispositivos en login                  │    │
│  │  - Control de sesiones por dispositivo                  │    │
│  │  - Manejo de múltiples dispositivos                     │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │         SQLite Database (trading_system.db)             │    │
│  │                                                          │    │
│  │ Tables:                                                 │    │
│  │ • customers      - Información de clientes              │    │
│  │ • devices        - Dispositivos registrados             │    │
│  │ • sessions       - Sesiones activas                     │    │
│  │ • payments       - Historial de pagos                   │    │
│  │ • audit_log      - Registro de acciones                │    │
│  │ • blocked_attempts - Intentos denegados                 │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📦 Módulos Principales

### 1. DatabaseManager (`database_manager.py`)

**Propósito**: Gestión completa de la base de datos SQLite con tablas para clientes, dispositivos, sesiones y auditoría.

#### Tablas de la Base de Datos:

##### **Tabla: customers**
```sql
CREATE TABLE customers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    subscription_type TEXT DEFAULT 'free',
    payment_status TEXT DEFAULT 'pending',
    payment_amount REAL DEFAULT 0,
    payment_date TIMESTAMP,
    payment_method TEXT,
    stripe_customer_id TEXT UNIQUE,
    is_active BOOLEAN DEFAULT 1,
    last_login TIMESTAMP,
    role TEXT DEFAULT 'trader'
);
```

**Campos**:
- `id`: Identificador único del cliente
- `username`: Nombre de usuario único
- `email`: Correo electrónico único
- `password_hash`: Hash SHA-256 de la contraseña
- `subscription_type`: Tipo de suscripción (free, premium, enterprise)
- `payment_status`: Estado del pago (pending, completed, failed)
- `payment_amount`: Monto pagado
- `stripe_customer_id`: ID de cliente en Stripe

##### **Tabla: devices**
```sql
CREATE TABLE devices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER NOT NULL,
    device_fingerprint TEXT NOT NULL UNIQUE,
    device_name TEXT,
    device_type TEXT,
    ip_address TEXT NOT NULL,
    os TEXT,
    browser TEXT,
    registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_used TIMESTAMP,
    is_active BOOLEAN DEFAULT 1,
    is_primary BOOLEAN DEFAULT 0,
    FOREIGN KEY (customer_id) REFERENCES customers(id)
);
```

**Campos Importantes**:
- `device_fingerprint`: Hash único del dispositivo (hardware + SO + CPU)
- `ip_address`: Dirección IP del dispositivo
- `is_primary`: Si es el dispositivo principal
- `last_used`: Última vez que se usó

##### **Tabla: sessions**
```sql
CREATE TABLE sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER NOT NULL,
    device_id INTEGER NOT NULL,
    session_token TEXT UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL,
    last_activity TIMESTAMP,
    ip_address TEXT,
    is_active BOOLEAN DEFAULT 1,
    FOREIGN KEY (customer_id) REFERENCES customers(id),
    FOREIGN KEY (device_id) REFERENCES devices(id)
);
```

**Características**:
- Cada sesión vinculada a un dispositivo específico
- Token de sesión único e imposible de falsificar
- Expiración automática configurable

##### **Tabla: payments**
```sql
CREATE TABLE payments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER NOT NULL,
    amount REAL NOT NULL,
    currency TEXT DEFAULT 'USD',
    status TEXT DEFAULT 'pending',
    payment_method TEXT,
    stripe_payment_id TEXT UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    receipt_url TEXT,
    description TEXT,
    FOREIGN KEY (customer_id) REFERENCES customers(id)
);
```

##### **Tabla: audit_log**
```sql
CREATE TABLE audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER,
    action TEXT NOT NULL,
    details TEXT,
    ip_address TEXT,
    device_fingerprint TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status TEXT,
    FOREIGN KEY (customer_id) REFERENCES customers(id)
);
```

**Acciones registradas**:
- USER_REGISTERED
- DEVICE_REGISTERED
- SESSION_CREATED
- PAYMENT_RECEIVED
- DEVICE_ACCESS_DENIED
- ACCOUNT_DISABLED

##### **Tabla: blocked_attempts**
```sql
CREATE TABLE blocked_attempts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER,
    ip_address TEXT,
    device_fingerprint TEXT,
    reason TEXT,
    attempted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES customers(id)
);
```

#### Métodos Principales:

```python
# Registro y Autenticación
register_customer(username, email, password, subscription_type)
verify_customer_password(username, password) -> (is_valid, customer_id, message)

# Gestión de Dispositivos
register_device(customer_id, device_fingerprint, device_name, ...)
validate_device_access(customer_id, device_fingerprint, ip_address) -> (is_valid, message)

# Gestión de Sesiones
create_session(customer_id, device_id, session_token, ip_address)
verify_session_token(session_token) -> (is_valid, customer_id)
logout_customer(customer_id)

# Gestión de Pagos
record_payment(customer_id, amount, payment_method, stripe_payment_id)
get_customer_payments(customer_id, limit=10)

# Información
get_customer_info(customer_id) -> Dict
get_customer_devices(customer_id) -> List[Dict]
get_audit_log(customer_id, limit=100) -> List[Dict]
```

---

### 2. DeviceManager (`device_manager.py`)

**Propósito**: Gestión de identificación única de dispositivos con fingerprinting avanzado.

#### DeviceFingerprint

Genera un **fingerprint único e irrepetible** del dispositivo combinando:

1. **MAC Address** (hash SHA-256)
2. **Hostname** (nombre del computador)
3. **SO + Procesador** (Windows 11 Pro, Intel Core i7, etc.)
4. **UUID de Disco** (número de serie del disco duro)
5. **Información de CPU** (cantidad de núcleos, frecuencia)

```python
# Ejemplo de fingerprint generado:
# a3f8d2e1c9b6f4a7e2d5c1b8a9f3e6d4
```

**Ventajas**:
- ✅ Único por dispositivo (imposible duplicar)
- ✅ Persiste incluso si se reinicia Windows
- ✅ Combina múltiples componentes para mayor confiabilidad
- ✅ Imposible cambiar sin reformatear el disco

#### Métodos:

```python
# Generar fingerprint del dispositivo actual
generate_device_fingerprint() -> str

# Obtener info completa del dispositivo
get_device_info() -> Dict
{
    'hostname': 'DESKTOP-XYZ',
    'platform': 'Windows',
    'platform_release': '10',
    'platform_version': 'Windows-10-10.0.22621-SP0',
    'architecture': 'AMD64',
    'processor': 'Intel Core i7',
    'cpu_count': 8,
    'ram_gb': 16.0,
    'mac_address': '00:11:22:33:44:55'
}

# Registrar nuevo dispositivo
register_new_device(customer_id, ip_address, device_name, is_primary)

# Validar acceso desde dispositivo (SINGLE DEVICE ENFORCEMENT)
validate_device_session(customer_id, ip_address, device_fingerprint)
```

---

## 🔐 Sistema de Control de Dispositivos (SINGLE DEVICE ENFORCEMENT)

### Concepto Fundamental

**Un usuario = Un dispositivo activo a la vez**

```
Estado PERMITIDO:
Usuario A con Dispositivo X → ✅ SESIÓN ACTIVA

Estado DENEGADO:
Usuario A con Dispositivo X → ✅ Sesión Activa
Usuario A con Dispositivo Y → ❌ ACCESO DENEGADO

Mensaje: "Ya estás en sesión en otro dispositivo (Desktop). Cierra esa sesión primero."
```

### Flujo de Autenticación

```
1. Usuario intenta login con credenciales
   ↓
2. Sistema verifica username/password
   ↓
3. Si es válido, genera device_fingerprint del dispositivo actual
   ↓
4. Busca sesiones activas del usuario en OTROS dispositivos
   ↓
5. Si hay sesión activa en OTRO dispositivo:
   ├─ Registra intento bloqueado en blocked_attempts
   ├─ Retorna: "ACCESO DENEGADO - Ya estás en otro dispositivo"
   └─ NO se crea nueva sesión
   ↓
6. Si NO hay sesión activa o es MISMO dispositivo:
   ├─ Cierra sesiones previas (si las hay)
   ├─ Registra el dispositivo en tabla devices
   ├─ Crea nueva sesión en tabla sessions
   ├─ Retorna session_token
   └─ ✅ Login exitoso
```

### Ejemplo Práctico

**Escenario: Juan intenta usar dos computadoras**

```
10:00 AM - Juan en su laptop (Dispositivo A)
          Login exitoso → Sesión creada
          
10:05 AM - Juan en su celular (Dispositivo B)
          Intenta login
          Sistema detecta sesión activa en Dispositivo A
          ❌ ACCESO DENEGADO
          Mensaje: "Ya estás en sesión en tu laptop. Cierra esa sesión primero."

10:10 AM - Juan cierra sesión en laptop (logout)
          
10:12 AM - Juan en celular intenta login de nuevo
          No hay sesiones activas del usuario
          ✅ LOGIN EXITOSO
```

---

## 💳 Integración con Sistema de Pagos

### Flujo de Compra y Activación

```
1. Cliente hace clic en "Comprar - $497"
   ↓
2. Redirige a Stripe para pago
   ↓
3. Cliente completa pago
   ↓
4. Webhook de Stripe confirma pago
   ↓
5. Sistema registra en tabla payments
   ↓
6. Se actualiza subscription_type de 'free' a 'premium'
   ↓
7. Usuario recibe confirmación por email
   ↓
8. ✅ Cuenta totalmente activa en ese dispositivo
   ↓
9. Otros intentos de login desde otros dispositivos:
   ├─ Mantienen restriction de SINGLE DEVICE
   └─ Requieren nuevo pago (o transferencia de licencia)
```

### Base de Datos de Pagos

```python
# Ejemplo de registro de pago
{
    'id': 1,
    'customer_id': 5,
    'amount': 497.00,
    'currency': 'USD',
    'status': 'completed',
    'payment_method': 'stripe',
    'stripe_payment_id': 'pi_1234567890',
    'created_at': '2026-04-30 10:00:00',
    'completed_at': '2026-04-30 10:01:30',
    'receipt_url': 'https://receipts.stripe.com/...',
    'description': 'Professional Trading System - Single License'
}
```

---

## 🛡️ Sistema de Auditoría y Seguridad

### Registros de Auditoría

**Cada acción se registra con**:
- Quién: customer_id
- Qué: action (tipo de acción)
- Cuándo: timestamp
- Dónde: ip_address
- Qué dispositivo: device_fingerprint
- Resultado: status

### Ejemplo de Audit Log

```
┌─────────────────────────────────────────────────────────────┐
│ ID │ CUSTOMER │ ACTION          │ DETAILS             │ STATUS │
├─────────────────────────────────────────────────────────────┤
│ 1  │ 5        │ USER_REGISTERED │ nuevo cliente       │ success│
│ 2  │ 5        │ DEVICE_REG      │ Laptop - Windows 11 │ success│
│ 3  │ 5        │ SESSION_CREATED │ device_id: 1        │ success│
│ 4  │ 5        │ PAYMENT_RECEIVED│ $497 - Stripe       │ success│
│ 5  │ 5        │ DEVICE_ACCESS_D │ otro dispositivo    │ blocked│
│ 6  │ 5        │ SESSION_CLOSED  │ logout               │ success│
└─────────────────────────────────────────────────────────────┘
```

### Intentos Bloqueados

Se registran automáticamente intentos de acceso no autorizados:

```
Tabla: blocked_attempts
┌──────────────────────────────────────────────┐
│ ID │ CUSTOMER │ IP_ADDRESS │ REASON          │
├──────────────────────────────────────────────┤
│ 1  │ 5        │ 192.168.1.2│ Otro dispositivo│
│ 2  │ 5        │ 10.0.0.5   │ IP no autorizada│
└──────────────────────────────────────────────┘
```

---

## 📊 Panel de Control de Dispositivos

### Sección en Dashboard

```
📱 MIS DISPOSITIVOS
═════════════════════════════════════════════════════

✓ LAPTOP - Windows 11 Pro
  • IP: 192.168.1.100
  • Registrado: 30 abril 2026, 10:00 AM
  • Última actividad: Hace 2 minutos
  • Estado: ACTIVO (dispositivo actual)
  • Acciones: [Establecer como primario] [Eliminar]

✓ DESKTOP - Windows 10
  • IP: 192.168.1.50
  • Registrado: 28 abril 2026, 15:30
  • Última actividad: Ayer 22:15 PM
  • Estado: INACTIVO
  • Acciones: [Activar] [Eliminar]

✓ TELEFONO - Android 13
  • IP: 203.0.113.45
  • Registrado: 25 abril 2026, 09:00 AM
  • Última actividad: Hace 1 semana
  • Estado: INACTIVO
  • Acciones: [Activar] [Eliminar]

═════════════════════════════════════════════════════
Total dispositivos: 3 | Dispositivos activos: 1
```

---

## 🔒 Protecciones de Seguridad

### 1. Fingerprinting de Hardware
```
✅ Imposible falsificar el fingerprint
❌ No se puede cambiar sin reformatear el disco
```

### 2. Single Device Enforcement
```
✅ Solo un dispositivo activo por usuario
❌ Imposible usar la misma cuenta desde 2 dispositivos
```

### 3. Auditoría Completa
```
✅ Cada acción se registra con IP y dispositivo
❌ Se registran intentos bloqueados
```

### 4. Rate Limiting
```
✅ Máximo 5 intentos fallidos antes de bloquear
✅ Bloqueo de 15 minutos después de 5 intentos
```

### 5. Encriptación
```
✅ Contraseñas: SHA-256 + validación
✅ Sesiones: Tokens únicos e irrepetibles
✅ Comunicación: HTTPS/SSL-TLS
```

---

## 🚀 Cómo Usar el Sistema

### Para Administrador

```python
# Crear instancia del gestor
from database_manager import DatabaseManager

db = DatabaseManager('trading_system.db')

# Registrar nuevo cliente
success, msg = db.register_customer(
    username='juan',
    email='juan@example.com',
    password='SecurePass123!',
    subscription_type='free'
)

# Ver todos los clientes
customers = db.get_all_customers()
for customer in customers:
    print(f"Usuario: {customer['username']}, Email: {customer['email']}")

# Ver dispositivos de un cliente
devices = db.get_customer_devices(customer_id=1)
for device in devices:
    print(f"Dispositivo: {device['name']}, Última actividad: {device['last_used']}")

# Ver audit log
logs = db.get_audit_log(customer_id=1, limit=50)
for log in logs:
    print(f"[{log['timestamp']}] {log['action']} - {log['status']}")
```

### Para el Usuario (Automático)

El sistema funciona automáticamente cuando el usuario intenta login:

1. **Dashboard** solicita credenciales
2. **Backend** llama a `authenticate_user()` que:
   - Verifica password
   - Genera fingerprint del dispositivo actual
   - Valida que no haya sesión activa en otro dispositivo
   - Crea sesión si es válido
3. **Dashboard** redirige a página principal si login es exitoso

---

## 📈 Estadísticas y Reportes

El sistema proporciona datos para generar reportes:

```python
# Clientes por región (por IP)
# Dispositivos más usados
# Pagos por período
# Intentos bloqueados
# Actividad por hora del día
```

---

## 🔧 Mantenimiento

### Limpiar Sesiones Expiradas
```python
# Ejecutar periódicamente (ej: cada hora)
db.clean_expired_sessions()
```

### Hacer Backup
```bash
# Backup manual
cp trading_system.db trading_system.backup.db

# Backup automático recomendado
# Configurar en cron o Windows Task Scheduler
```

### Monitorear Intentos Bloqueados
```python
# Ver intentos bloqueados en última hora
blocked = db.get_blocked_attempts_last_hour()
print(f"Intentos bloqueados: {len(blocked)}")
```

---

## 📞 Soporte Técnico

### Problemas Comunes

**P: El usuario ve "ACCESO DENEGADO - Ya estás en otro dispositivo"**
- R: Es correcto. El usuario debe cerrar sesión en el otro dispositivo primero.

**P: ¿Cómo cambio de dispositivo?**
- R: Debe:
  1. Logout en dispositivo actual
  2. Esperar a que sesión expire (24h) O
  3. Administrador desactiva dispositivo antiguo

**P: ¿Se puede usar en 2 dispositivos al mismo tiempo?**
- R: No. Es característica de seguridad para prevenir copias ilegales.

**P: ¿Qué pasa si se reinicia Windows?**
- R: El fingerprint sigue siendo el mismo, puede loguearse normalmente.

---

## 📊 Conclusión

El sistema de **base de datos + control de dispositivos** proporciona:

✅ **Control total** sobre quién accede y desde dónde
✅ **Protección contra** copias ilegales del software
✅ **Auditoria completa** de todas las acciones
✅ **Seguridad de nivel bancario** en autenticación
✅ **Escalabilidad** para miles de usuarios

**¡Sistema completamente listo para producción y venta!** 🎯