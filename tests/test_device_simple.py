#!/usr/bin/env python3
"""
Simple test for database and device manager
"""

import sys
import logging
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Import components
from database_manager import DatabaseManager
from device_manager import DeviceManager, DeviceFingerprint

def main():
    print("\n" + "="*70)
    print("TRADING SYSTEM - DATABASE & DEVICE CONTROL TEST")
    print("="*70 + "\n")

    # Test 1: Database initialization
    print("[TEST 1] Initializing database...")
    try:
        db = DatabaseManager('test_simple.db')
        print("OK - Database initialized\n")
    except Exception as e:
        print(f"FAILED: {e}\n")
        return False

    # Test 2: Register customers
    print("[TEST 2] Registering customers...")
    try:
        success, msg = db.register_customer("alice_trader", "alice@example.com", "pass123", "premium")
        print(f"  Alice: {msg}")
        
        success, msg = db.register_customer("bob_trader", "bob@example.com", "pass456", "free")
        print(f"  Bob: {msg}\n")
    except Exception as e:
        print(f"FAILED: {e}\n")
        return False

    # Test 3: Customer info
    print("[TEST 3] Retrieving customer info...")
    try:
        info = db.get_customer_info("alice_trader")
        print(f"  Customer: {info['username']} ({info['email']})")
        print(f"  Subscription: {info['subscription_type']}\n")
    except Exception as e:
        print(f"FAILED: {e}\n")
        return False

    # Test 4: Device fingerprinting
    print("[TEST 4] Generating device fingerprint...")
    try:
        fp = DeviceFingerprint.generate_fingerprint()
        print(f"  Fingerprint: {fp[:16]}...{fp[-16:]}")
        
        info = DeviceFingerprint.get_device_info()
        print(f"  Device: {info.get('hostname', 'N/A')}")
        print(f"  OS: {info.get('platform', 'N/A')} {info.get('platform_release', '')}\n")
    except Exception as e:
        print(f"FAILED: {e}\n")
        return False

    # Test 5: Register device for alice
    print("[TEST 5] Registering device for alice...")
    try:
        customer_id = db.get_customer_info("alice_trader")['id']
        
        success, device_id = db.register_device(
            customer_id=customer_id,
            device_fingerprint=fp,
            device_name="Alice's Laptop",
            device_type="laptop",
            ip_address="192.168.1.100",
            os="Windows 10",
            is_primary=True
        )
        
        if success:
            print(f"  Device registered (ID: {device_id})\n")
        else:
            print(f"  Device already exists (ID: {device_id})\n")
    except Exception as e:
        print(f"FAILED: {e}\n")
        return False

    # Test 6: Verify password
    print("[TEST 6] Verifying password...")
    try:
        success, cid, msg = db.verify_customer_password("alice_trader", "pass123")
        print(f"  Result: {msg}")
        print(f"  Customer ID: {cid}\n")
    except Exception as e:
        print(f"FAILED: {e}\n")
        return False

    # Test 7: Validate device access
    print("[TEST 7] Validating device access...")
    try:
        success, msg = db.validate_device_access(customer_id, fp, "192.168.1.100")
        print(f"  Access: {'ALLOWED' if success else 'DENIED'}")
        print(f"  Message: {msg}\n")
    except Exception as e:
        print(f"FAILED: {e}\n")
        return False

    # Test 8: Create session
    print("[TEST 8] Creating session...")
    try:
        token = "session_abc123_xyz789"
        success, result = db.create_session(
            customer_id=customer_id,
            device_id=device_id,
            session_token=token,
            ip_address="192.168.1.100",
            session_duration_hours=24
        )
        
        if success:
            print(f"  Session created")
            print(f"  Token: {token[:20]}...\n")
        else:
            print(f"  Failed to create session\n")
    except Exception as e:
        print(f"FAILED: {e}\n")
        return False

    # Test 9: Record payment
    print("[TEST 9] Recording payment...")
    try:
        success, payment_id = db.record_payment(
            customer_id=customer_id,
            amount=99.99,
            payment_method="stripe",
            stripe_payment_id="pi_test_123"
        )
        
        if success:
            print(f"  Payment recorded (ID: {payment_id})")
            
            # Check updated info
            info = db.get_customer_info("alice_trader")
            print(f"  New status: {info['subscription_type']} ({info['payment_status']})\n")
        else:
            print(f"  Payment recording failed\n")
    except Exception as e:
        print(f"FAILED: {e}\n")
        return False

    # Test 10: Get customer devices
    print("[TEST 10] Listing customer devices...")
    try:
        devices = db.get_customer_devices(customer_id)
        print(f"  Total devices: {len(devices)}")
        for dev in devices:
            print(f"    - {dev['name']} ({dev['type']}) - {dev['ip_address']}\n")
    except Exception as e:
        print(f"FAILED: {e}\n")
        return False

    # Test 11: Audit log
    print("[TEST 11] Checking audit log...")
    try:
        logs = db.get_audit_log(customer_id=customer_id, limit=5)
        print(f"  Logged events: {len(logs)}")
        for log in logs[:3]:
            print(f"    - {log['timestamp']}: {log['action']}\n")
    except Exception as e:
        print(f"FAILED: {e}\n")
        return False

    print("="*70)
    print("ALL TESTS COMPLETED SUCCESSFULLY")
    print("="*70 + "\n")
    
    return True


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"FATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
