# --------------------------------------------------------------
# check_and_fix_bot_environment.ps1
# Environment diagnostic + auto-repair for crypto_bot.py
# --------------------------------------------------------------

$ErrorActionPreference = "SilentlyContinue"
$report = "bot_check_report.txt"
if (Test-Path $report) { Remove-Item $report }

Write-Host "`n🤖 Starting Crypto Bot Environment Check & Repair...`n" -ForegroundColor Cyan
Add-Content $report "=== CRYPTO BOT ENVIRONMENT CHECK REPORT ==="
Add-Content $report "Generated on: $(Get-Date)"
Add-Content $report "`n--------------------------------------------`n"

# 1️⃣ Check Python
if (!(Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "❌ Python not found in PATH!" -ForegroundColor Red
    Add-Content $report "❌ Python not found. Install from https://python.org and add to PATH."
    exit
} else {
    $pythonVersion = python --version
    Write-Host "✅ Python detected: $pythonVersion"
    Add-Content $report "✅ Python detected: $pythonVersion"
}

# 2️⃣ Syntax check
if (Test-Path ".\crypto_bot.py") {
    Write-Host "`n🧠 Checking for syntax errors..."
    python -m py_compile crypto_bot.py 2>&1 | Tee-Object -Variable syntaxErrors
    if ($syntaxErrors) {
        Write-Host "❌ Syntax errors found. See log." -ForegroundColor Red
        Add-Content $report "`n--- Syntax Errors ---`n$syntaxErrors"
    } else {
        Write-Host "✅ No syntax errors found." -ForegroundColor Green
        Add-Content $report "`n✅ No syntax errors found."
    }
} else {
    Write-Host "⚠️ crypto_bot.py not found in current folder." -ForegroundColor Yellow
    Add-Content $report "⚠️ crypto_bot.py not found in current folder."
}

# 3️⃣ Missing imports (executed as separate Python process)
Write-Host "`n📦 Checking for missing imports..."
$missingImports = python - <<'PYCODE'
import importlib, sys, os
try:
    f = 'crypto_bot.py'
    if os.path.exists(f):
        with open(f) as fh:
            code = fh.read()
        mods = []
        for line in code.splitlines():
            if line.startswith('import ') or line.startswith('from '):
                parts = line.split()
                if len(parts) > 1:
                    mods.append(parts[1].split('.')[0])
        for m in sorted(set(mods)):
            if not importlib.util.find_spec(m):
                print(m)
except Exception as e:
    pass
PYCODE

if ($missingImports) {
    Write-Host "❌ Missing Python modules detected:" -ForegroundColor Red
    $missingImports | ForEach-Object { Write-Host "   - $_" }
    Add-Content $report "`n--- Missing Imports ---`n$missingImports"

    Write-Host "`n🛠 Installing missing modules..." -ForegroundColor Yellow
    foreach ($mod in $missingImports) {
        Write-Host "Installing $mod..."
        pip install $mod -q
    }
} else {
    Write-Host "✅ All imports found." -ForegroundColor Green
    Add-Content $report "`n✅ All imports found."
}

# 4️⃣ API keys
Write-Host "`n🔑 Checking API keys..."
$apiKeys = @("BINANCE_API_KEY", "BINANCE_API_SECRET", "OPENAI_API_KEY")
foreach ($key in $apiKeys) {
    $value = [Environment]::GetEnvironmentVariable($key, "User")
    if ($value) {
        Write-Host "✅ $key is set."
        Add-Content $report "✅ $key is set."
    } else {
        Write-Host "❌ $key is missing!" -ForegroundColor Red
        Add-Content $report "❌ $key is missing!"
        $newVal = Read-Host "Enter value for $key"
        if ($newVal -ne "") {
            [Environment]::SetEnvironmentVariable($key, $newVal, "User")
            Write-Host "✅ Saved $key successfully."
            Add-Content $report "✅ $key added by user."
        }
    }
}

# 5️⃣ Required libraries
Write-Host "`n🧩 Checking required Python libraries..."
$libs = @("pandas","numpy","scikit-learn","xgboost","optuna","python-telegram-bot","ta","matplotlib","requests")
foreach ($lib in $libs) {
    python -c "import $lib" 2>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Missing: $lib" -ForegroundColor Red
        Add-Content $report "❌ Missing: $lib"
        Write-Host "Installing $lib..."
        pip install $lib -q
    } else {
        Add-Content $report "✅ $lib installed."
    }
}

# 6️⃣ Final check
Write-Host "`n🔁 Final validation..." -ForegroundColor Cyan
python - <<'PYCODE'
import importlib, os
modules = ['pandas','numpy','scikit-learn','xgboost','optuna','python-telegram-bot','ta','matplotlib','requests']
print("\n🧩 Dependency check:")
for m in modules:
    try:
        importlib.import_module(m)
        print(f"✅ {m}")
    except ImportError:
        print(f"❌ {m} still missing!")
print("\n🔑 API key status:")
for key in ["BINANCE_API_KEY", "BINANCE_API_SECRET", "OPENAI_API_KEY"]:
    print(f"{key}: {'✅ Set' if os.getenv(key) else '❌ Missing'}")
PYCODE

# 7️⃣ Auto-launch the bot
if (Test-Path ".\crypto_bot.py") {
    Write-Host "`n🚀 Launching crypto_bot.py..." -ForegroundColor Cyan
    python .\crypto_bot.py
} else {
    Write-Host "⚠️ crypto_bot.py not found — skipping launch." -ForegroundColor Yellow
}

Write-Host "`n✅ Check & repair complete! See 'bot_check_report.txt' for details.`n" -ForegroundColor Green
Add-Content $report "`n--------------------------------------------`n"
Add-Content $report "✅ Environment check and repair complete."
