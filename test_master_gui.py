#!/usr/bin/env python3
"""
Test Master Trader GUI - Validation script
Tests all components without displaying window
"""
import sys
import logging
import tkinter as tk
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_imports():
    """Test all critical imports"""
    print("\n" + "="*70)
    print("[TEST] MASTER TRADER - GUI VALIDATION TEST")
    print("="*70)
    
    tests_passed = 0
    tests_failed = 0
    
    imports_to_test = [
        ('tkinter', 'tkinter'),
        ('matplotlib', 'matplotlib'),
        ('pandas', 'pandas'),
        ('numpy', 'numpy'),
        ('sklearn', 'scikit-learn'),
        ('binance', 'python-binance'),
        ('xgboost', 'xgboost'),
        ('requests', 'requests'),
        ('optuna', 'optuna'),
        ('config', 'config module'),
        ('market_analysis', 'market_analysis module'),
        ('crypto_engine', 'crypto_engine module'),
    ]
    
    print("\n[*] Testing imports...")
    for module_name, display_name in imports_to_test:
        try:
            __import__(module_name)
            print(f"  [OK] {display_name:30} PASS")
            tests_passed += 1
        except ImportError as e:
            print(f"  [FAIL] {display_name:30} FAIL - {e}")
            tests_failed += 1
    
    return tests_passed, tests_failed


def test_master_gui_components():
    """Test Master GUI component loading"""
    tests_passed = 0
    tests_failed = 0
    
    print("\n[*] Testing Master GUI components...")
    
    try:
        # Import master_gui
        from master_gui import (
            MasterThemeManager, MasterTraderGUI, 
            Card, StatCard, ModernButton,
            fetch_binance_symbols, theme_manager
        )
        print(f"  [OK] Master GUI imports           PASS")
        tests_passed += 1
        
        # Test theme manager
        tm = MasterThemeManager()
        colors = tm.get_colors()
        assert 'bg' in colors, "Missing 'bg' in colors"
        assert 'accent' in colors, "Missing 'accent' in colors"
        print(f"  [OK] Theme manager                 PASS")
        tests_passed += 1
        
        # Test theme switching
        tm.switch_theme()
        assert tm.current_theme == 'light', "Theme switch failed"
        tm.switch_theme()
        assert tm.current_theme == 'dark', "Theme switch back failed"
        print(f"  [OK] Theme switching              PASS")
        tests_passed += 1
        
        # Test color availability
        dark_colors = MasterThemeManager.THEMES['dark']
        light_colors = MasterThemeManager.THEMES['light']
        assert len(dark_colors) == len(light_colors), "Theme color mismatch"
        print(f"  [OK] Theme colors complete        PASS")
        tests_passed += 1
        
        # Test GUI creation (no display)
        root = tk.Tk()
        root.withdraw()  # Hide window
        
        app = MasterTraderGUI(root)
        assert app.current_symbol.get() is not None, "Symbol not initialized"
        print(f"  [OK] GUI initialization            PASS")
        tests_passed += 1
        
        # Test state variables
        assert hasattr(app, 'is_running'), "Missing is_running"
        assert hasattr(app, 'stats'), "Missing stats"
        assert hasattr(app, 'stat_cards'), "Missing stat_cards"
        print(f"  [OK] State management             PASS")
        tests_passed += 1
        
        # Test component creation
        components = ['start_btn', 'stop_btn', 'symbol_listbox', 'activity_text', 'status_label']
        for component in components:
            assert hasattr(app, component), f"Missing component: {component}"
        print(f"  [OK] UI components created        PASS")
        tests_passed += 1
        
        root.destroy()
        
    except Exception as e:
        print(f"  [FAIL] Master GUI test               FAIL - {e}")
        tests_failed += 1
        import traceback
        traceback.print_exc()
    
    return tests_passed, tests_failed


def test_binance_symbols():
    """Test Binance symbol fetching"""
    tests_passed = 0
    tests_failed = 0
    
    print("\n[*] Testing Binance integration...")
    
    try:
        from master_gui import fetch_binance_symbols
        
        print("  [*] Fetching Binance symbols...")
        symbols = fetch_binance_symbols()
        
        assert len(symbols) > 0, "No symbols fetched"
        assert 'BTCUSDT' in symbols, "BTC not in symbols"
        assert 'ETHUSDT' in symbols, "ETH not in symbols"
        
        print(f"  [OK] Binance API working          PASS")
        print(f"     Fetched {len(symbols)} trading pairs")
        tests_passed += 1
        
    except Exception as e:
        print(f"  [FAIL] Binance API test              FAIL - {e}")
        tests_failed += 1
    
    return tests_passed, tests_failed


def test_functionality():
    """Test core functionality"""
    tests_passed = 0
    tests_failed = 0
    
    print("\n[*] Testing functionality...")
    
    try:
        root = tk.Tk()
        root.withdraw()
        
        from master_gui import MasterTraderGUI
        app = MasterTraderGUI(root)
        
        # Test bot control methods
        app._log_activity("Test message")
        assert app.activity_text.get("1.0", "end-1c") != "", "Activity log failed"
        print(f"  [OK] Activity logging             PASS")
        tests_passed += 1
        
        # Test stats update
        app._update_stats()
        assert app.stats['balance'] != 0, "Stats not updating"
        print(f"  [OK] Stats system                 PASS")
        tests_passed += 1
        
        # Test symbol selection
        if app.symbol_listbox.size() > 0:
            app.symbol_listbox.selection_set(0)
            app._on_symbol_select(None)
            assert app.current_symbol.get() != '', "Symbol selection failed"
            print(f"  [OK] Symbol selection             PASS")
            tests_passed += 1
        
        root.destroy()
        
    except Exception as e:
        print(f"  [FAIL] Functionality test            FAIL - {e}")
        tests_failed += 1
        import traceback
        traceback.print_exc()
    
    return tests_passed, tests_failed


def main():
    """Run all tests"""
    print("\nStarting comprehensive test suite...\n")
    
    total_passed = 0
    total_failed = 0
    
    # Run tests
    p, f = test_imports()
    total_passed += p
    total_failed += f
    
    p, f = test_master_gui_components()
    total_passed += p
    total_failed += f
    
    p, f = test_binance_symbols()
    total_passed += p
    total_failed += f
    
    p, f = test_functionality()
    total_passed += p
    total_failed += f
    
    # Summary
    print("\n" + "="*70)
    print("[TEST] SUMMARY")
    print("="*70)
    print(f"[OK] Passed: {total_passed}")
    print(f"[FAIL] Failed: {total_failed}")
    print(f"[*] Total:  {total_passed + total_failed}")
    
    if total_failed == 0:
        print("\n[OK] ALL TESTS PASSED - APPLICATION IS READY!")
        print("\n[*] You can now:")
        print("  1. Run: python run_master.py")
        print("  2. Or build EXE: python build_exe.py")
        return 0
    else:
        print(f"\n[WARNING] {total_failed} test(s) failed - Please review errors above")
        return 1


if __name__ == "__main__":
    sys.exit(main())