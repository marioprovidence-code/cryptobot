#!/usr/bin/env python3
"""
Diagnostic script to verify all project components are working
Run with: python diagnose.py
"""

import sys
import importlib
from pathlib import Path

print("=" * 70)
print("🔍 CRYPTO BOT - DIAGNOSTIC REPORT")
print("=" * 70)
print()

# Track results
results = []

def check_module(name: str, module_path: str = None):
    """Check if a module can be imported"""
    try:
        if module_path:
            sys.path.insert(0, module_path)
        importlib.import_module(name)
        print(f"✅ {name:<30} - OK")
        results.append((name, True))
    except ImportError as e:
        print(f"❌ {name:<30} - FAILED: {e}")
        results.append((name, False))

def check_file(path: str):
    """Check if a file exists"""
    exists = Path(path).exists()
    status = "✅" if exists else "❌"
    print(f"{status} {path:<40} - {'EXISTS' if exists else 'MISSING'}")
    results.append((path, exists))

# 1. Check Python Version
print("📌 PYTHON ENVIRONMENT")
print("-" * 70)
print(f"Python Version: {sys.version}")
print(f"Python Executable: {sys.executable}")
print()

# 2. Check Core Files
print("📌 PROJECT FILES")
print("-" * 70)
base_path = Path(__file__).parent
files_to_check = [
    "main.py",
    "config.py",
    "crypto_engine.py",
    "gui.py",
    "market_analysis.py",
    "indicators.py",
    "advanced_backtest.py",
    "advanced_entry_exit.py",
    "logging_utils.py",
    "requirements.txt",
    ".env.txt"
]

for file in files_to_check:
    check_file(str(base_path / file))
print()

# 3. Check Dependencies
print("📌 PYTHON DEPENDENCIES")
print("-" * 70)
dependencies = [
    "pandas",
    "numpy",
    "xgboost",
    "optuna",
    "sklearn",
    "matplotlib",
    "requests",
    "dotenv",
    "binance"
]

for dep in dependencies:
    check_module(dep)
print()

# 4. Check Internal Modules
print("📌 INTERNAL MODULES")
print("-" * 70)
internal_modules = [
    "config",
    "logging_utils",
    "indicators",
    "market_analysis",
    "crypto_engine",
    "gui"
]

for module in internal_modules:
    check_module(module, str(base_path))
print()

# 5. Summary
print("=" * 70)
print("📊 SUMMARY")
print("=" * 70)

passed = sum(1 for _, result in results if result)
total = len(results)
percentage = (passed / total * 100) if total > 0 else 0

print(f"Passed: {passed}/{total} ({percentage:.1f}%)")

if passed == total:
    print("\n🎉 ALL CHECKS PASSED - Your project is ready to run!")
    print("\nRun the application with:")
    print("    python main.py")
elif passed > total * 0.8:
    print("\n⚠️  MOST CHECKS PASSED - Minor issues detected")
    print("\nTry running: pip install -r requirements.txt")
else:
    print("\n❌ CRITICAL ISSUES DETECTED - Please fix before running")
    print("\nFailed checks:")
    for name, result in results:
        if not result:
            print(f"  - {name}")

print()
print("=" * 70)