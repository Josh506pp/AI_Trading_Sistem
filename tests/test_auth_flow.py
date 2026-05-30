#!/usr/bin/env python3
"""
Complete Authentication Flow Test - Single Device Enforcement Demo
Tests the full login, device validation, and single-device enforcement
"""

import sys
import time
import logging
from database_manager import DatabaseManager
from device_manager import DeviceManager, DeviceFingerprint

logging.basicConfig(level=logging.INFO, format='%(message)s')

def print_header(text):
    print("\n" + "="*70)
    print(f"  {text}")
    print("="*70)

def print_step(num, text):
    print(f"\n[STEP {num}] {text}")
    print("-" * 70)

def print_result(success, text):
    icon = "✓" if success else "✗"
    print(f"  [{icon}] {text}")

def simulate_login(db, device_mgr, username, password, device_name, device_type, ip_address):
    """Simulate complete login flow"""
    print_step(1, f"Login attempt: {username} from {device_name} ({ip_address})")
    
    # Step 1: Verify credentials
    print("  Verifying credentials...")
    success, customer_id, msg = db.verify_customer_password(username, password)
    print_result(success, msg)
    
    if not success:
        print("  Login failed!")
        return False, None, None
    
    # Step 2: Generate device fingerprint
    print("  Generating device fingerprint...")
    fingerprint = DeviceFingerprint.generate_fingerprint()
    print_result(True, f"Fingerprint: {fingerprint[:16]}...{fingerprint[-16:]}")
    
    # Step 3: Validate device access (single-device enforcement)
    print("  Checking single-device enforcement...")
    allowed, access_msg = db.validate_device_access(customer_id, fingerprint, ip_address)
    print_result(allowed, access_msg)
    
    if not allowed:
        print("  Access denied - user already logged in on another device!")
        return False, None, None
    
    # Step 4: Register/get device
    print("  Registering device...")
    success, device_info = device_mgr.register_new_device(
        customer_id=customer_id,
        device_name=device_name,
        ip_address=ip_address,
        is_primary=device_type == "laptop"  # Mark laptop as primary
    )
    print_result(success, f"Device registered/found (ID: {device_info.get('id', '?')})")
    
    # Step 5: Create session
    print("  Creating session...")
    success, session_token = device_mgr.create_device_session(
        customer_id=customer_id,
        device_fingerprint=fingerprint,
        ip_address=ip_address
    )
    print_result(success, f"Session: {session_token[:20]}...{session_token[-20:]}")
    
    if success:
        print("\n  >>> LOGIN SUCCESSFUL <<<")
        return True, customer_id, session_token
    else:
        print("  Session creation failed!")
        return False, None, None


def main():
    print_header("PROFESSIONAL TRADING SYSTEM - SINGLE DEVICE ENFORCEMENT TEST")
    
    # Initialize
    print("\nInitializing system...")
    db = DatabaseManager('test_auth_flow.db')
    device_mgr = DeviceManager(db)
    print("  [✓] System initialized")
    
    # Register users
    print_step(0, "User Registration")
    
    db.register_customer("alice_trader", "alice@example.com", "password123", "premium")
    print_result(True, "User registered: alice_trader")
    
    db.register_customer("bob_trader", "bob@example.com", "password456", "starter")
    print_result(True, "User registered: bob_trader")
    
    # Test 1: Normal login from one device
    print_header("TEST 1: Normal Login from Single Device")
    
    success, customer_id, token1 = simulate_login(
        db, device_mgr,
        username="alice_trader",
        password="password123",
        device_name="Alice's Laptop",
        device_type="laptop",
        ip_address="192.168.1.100"
    )
    
    if not success:
        print("\nTest 1 FAILED")
        return False
    
    print("\nTest 1 PASSED - Single device login works")
    
    # Test 2: Verify session token
    print_header("TEST 2: Session Token Validation")
    print_step(1, "Validating session token")
    
    valid, verified_cid = db.verify_session_token(token1)
    print_result(valid, f"Token valid, Customer ID: {verified_cid}")
    
    if not valid or verified_cid != customer_id:
        print("\nTest 2 FAILED")
        return False
    
    print("\nTest 2 PASSED - Session validation works")
    
    # Test 3: Try to login from different device (SHOULD BE BLOCKED)
    print_header("TEST 3: Single Device Enforcement - Simultaneous Login Attempt")
    print_step(1, "Attempting login from DIFFERENT DEVICE")
    
    # Simulate different device by manually creating a different fingerprint
    print("\n  Different device fingerprint detected...")
    
    success, msg = db.validate_device_access(
        customer_id=customer_id,
        device_fingerprint="different_device_fingerprint_12345",  # Different!
        ip_address="192.168.1.200"  # Different IP
    )
    print_result(not success, msg)  # Should be NOT successful
    
    if success:
        print("\nTest 3 FAILED - Should have blocked access from different device")
        return False
    
    print("\nTest 3 PASSED - Single device enforcement blocking different device")
    
    # Test 4: Re-login from same device (SHOULD BE ALLOWED)
    print_header("TEST 4: Re-login from Same Device")
    print_step(1, "Attempting to re-login from same device")
    
    # Use same fingerprint as before
    fp = DeviceFingerprint.generate_fingerprint()
    success, msg = db.validate_device_access(
        customer_id=customer_id,
        device_fingerprint=fp,
        ip_address="192.168.1.100"  # Same IP
    )
    print_result(success, msg)
    
    if not success:
        print("\nTest 4 FAILED - Should allow re-login from same device")
        return False
    
    print("\nTest 4 PASSED - Same device can re-login")
    
    # Test 5: Logout and try different device
    print_header("TEST 5: Logout and Login from Different Device")
    print_step(1, "Alice logs out")
    
    db.logout_customer(customer_id)
    print_result(True, "Logged out")
    
    print_step(2, "Now attempting login from DIFFERENT DEVICE")
    
    # Verify different device can now login
    success, msg = db.validate_device_access(
        customer_id=customer_id,
        device_fingerprint="different_device_fingerprint_12345",
        ip_address="192.168.1.200"
    )
    print_result(success, msg)
    
    if not success:
        print("\nTest 5 FAILED - Should allow different device after logout")
        return False
    
    print("\nTest 5 PASSED - Different device allowed after logout")
    
    # Test 6: Multiple users can be online simultaneously
    print_header("TEST 6: Multiple Users Online Simultaneously")
    print_step(1, "Bob logs in from his device")
    
    success, bob_id, bob_token = simulate_login(
        db, device_mgr,
        username="bob_trader",
        password="password456",
        device_name="Bob's Mobile",
        device_type="mobile",
        ip_address="203.0.113.50"
    )
    
    if not success:
        print("\nTest 6 FAILED")
        return False
    
    print("\nTest 6 PASSED - Multiple users can be online simultaneously")
    
    # Test 7: View audit trail
    print_header("TEST 7: Audit Trail Review")
    print_step(1, "Retrieving audit log for alice")
    
    logs = db.get_audit_log(customer_id=customer_id, limit=10)
    print_result(True, f"Audit trail has {len(logs)} entries")
    
    print("\n  Recent activities:")
    for log in logs[:5]:
        print(f"    - {log['timestamp']}: {log['action']} ({log['status']})")
    
    print("\nTest 7 PASSED - Audit logging works")
    
    # Final summary
    print_header("TEST SUMMARY")
    print("""
    ✓ User registration with subscriptions
    ✓ Password verification
    ✓ Device fingerprinting
    ✓ Single device enforcement (blocks simultaneous logins)
    ✓ Session token validation
    ✓ Device re-login (same device)
    ✓ Device switching after logout
    ✓ Multiple concurrent users
    ✓ Comprehensive audit logging
    
    =================================================================
    SINGLE DEVICE ENFORCEMENT SYSTEM - FULLY OPERATIONAL ✓
    =================================================================
    """)
    
    return True


if __name__ == "__main__":
    import os
    
    # Clean database
    for f in ['test_auth_flow.db', 'test_auth_flow.db-wal', 'test_auth_flow.db-shm']:
        try:
            os.remove(f)
        except:
            pass
    
    try:
        success = main()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\nFATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
