# DTBench: run the LLM experiment on a Windows PC (CPU only, all cores) with llama.cpp.
#
# Run from PowerShell inside a clone of this repository:
#   powershell -ExecutionPolicy Bypass -File scripts\run_models_windows.ps1                    # all three models
#   powershell -ExecutionPolicy Bypass -File scripts\run_models_windows.ps1 -Models gemma3-4b  # one model
#
# llama.cpp (pinned release b11635) and the GGUF models (about 2-2.5 GB each) are downloaded to
# %LOCALAPPDATA%\dtbench_run. Every prompt and response is written to results\raw\<model>\; responses
# that already exist are reused, so delete results\raw\<model> first for a fresh run.
# Release builds produce the same constrained output as the paper's run because the runner sends the
# GBNF grammars in dtbench\grammars with every request.
param([string[]]$Models = @("qwen3-4b", "llama3.2-3b", "gemma3-4b"))

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

$repo = Split-Path $PSScriptRoot -Parent
$work = Join-Path $env:LOCALAPPDATA "dtbench_run"
$out  = Join-Path $repo "results\raw"
$port = 8765
New-Item -ItemType Directory -Force -Path $work, "$work\models", $out | Out-Null
$threads = [int]((Get-CimInstance Win32_Processor | Measure-Object -Property NumberOfCores -Sum).Sum)
Write-Host "Repository: $repo  |  downloads: $work  |  CPU threads: $threads"

function Find-Python {
    $c = @()
    foreach ($n in "python", "py", "python3") { $g = Get-Command $n -ErrorAction SilentlyContinue; if ($g) { $c += $g.Source } }
    $c += "$env:USERPROFILE\anaconda3\python.exe", "$env:USERPROFILE\miniconda3\python.exe",
          "$env:ProgramData\anaconda3\python.exe", "$env:LOCALAPPDATA\anaconda3\python.exe"
    $c += Get-ChildItem "$env:LOCALAPPDATA\Programs\Python" -Recurse -Filter python.exe -ErrorAction SilentlyContinue |
          ForEach-Object { $_.FullName }
    foreach ($p in $c) {
        if (-not $p -or -not (Test-Path $p) -or $p -like "*WindowsApps*") { continue }
        try { $v = & $p -c "import sys; print(sys.version_info >= (3, 9))" 2>$null; if ("$v".Trim() -eq "True") { return $p } } catch {}
    }
    throw "Python 3.9+ not found. Install Python from python.org (or run this from an Anaconda Prompt) and run again."
}
$py = Find-Python
Write-Host "Python: $py"
$env:PYTHONUTF8 = "1"; $env:PYTHONIOENCODING = "utf-8"

# 1. llama.cpp, pinned Windows CPU build
$server = Get-ChildItem "$work\llama" -Recurse -Filter llama-server.exe -ErrorAction SilentlyContinue | Select-Object -First 1
if (-not $server) {
    Write-Host "Downloading llama.cpp b11635 ..."
    curl.exe -L --retry 3 -s -o "$work\llama.zip" "https://github.com/ggml-org/llama.cpp/releases/download/b11635/llama-b11635-bin-win-cpu-x64.zip"
    Expand-Archive "$work\llama.zip" -DestinationPath "$work\llama" -Force
    $server = Get-ChildItem "$work\llama" -Recurse -Filter llama-server.exe | Select-Object -First 1
}
if (-not $server) { throw "llama-server.exe not found after download" }

# 2. models (4-bit Q4_K_M GGUF files from Hugging Face)
$urls = @{
    "qwen3-4b"    = "https://huggingface.co/unsloth/Qwen3-4B-Instruct-2507-GGUF/resolve/main/Qwen3-4B-Instruct-2507-Q4_K_M.gguf";
    "llama3.2-3b" = "https://huggingface.co/bartowski/Llama-3.2-3B-Instruct-GGUF/resolve/main/Llama-3.2-3B-Instruct-Q4_K_M.gguf";
    "gemma3-4b"   = "https://huggingface.co/bartowski/google_gemma-3-4b-it-GGUF/resolve/main/google_gemma-3-4b-it-Q4_K_M.gguf"
}
foreach ($key in $Models) {
    if (-not $urls.ContainsKey($key)) { throw "unknown model '$key' (use qwen3-4b, llama3.2-3b or gemma3-4b)" }
    $gguf = "$work\models\$key.gguf"
    if (-not (Test-Path "$gguf.done")) {
        Write-Host "Downloading model $key ..."
        curl.exe -L --retry 5 -C - -s -o $gguf $urls[$key]
        New-Item -ItemType File -Force -Path "$gguf.done" | Out-Null
    }

    # 3. one llama-server per model, same settings as the paper (context 6144, no prompt cache, 1 slot)
    Write-Host "Starting llama-server for $key ..."
    $srvArgs = @("-m", "`"$gguf`"", "-c", "6144", "--cache-ram", "0", "-t", "$threads", "-np", "1", "--jinja",
                 "--host", "127.0.0.1", "--port", "$port")
    $srv = Start-Process -FilePath $server.FullName -ArgumentList $srvArgs -PassThru -WindowStyle Hidden `
           -RedirectStandardOutput "$work\server_$key.out" -RedirectStandardError "$work\server_$key.log"
    $ok = $false
    for ($i = 0; $i -lt 240; $i++) {
        Start-Sleep -Seconds 2
        try { if ((Invoke-RestMethod "http://127.0.0.1:$port/health" -TimeoutSec 3).status -eq "ok") { $ok = $true; break } } catch {}
    }
    if (-not $ok) { Stop-Process -Id $srv.Id -Force -ErrorAction SilentlyContinue; throw "llama-server did not start; see $work\server_$key.log" }

    $t0 = Get-Date
    Push-Location $repo
    & $py -m dtbench.runner --model $key --base-url "http://127.0.0.1:$port/v1" --grammar-dir "dtbench\grammars" --out $out
    $rc = $LASTEXITCODE
    Pop-Location
    Stop-Process -Id $srv.Id -Force -ErrorAction SilentlyContinue
    Write-Host ("{0} finished in {1:N0} min (exit code {2})" -f $key, ((Get-Date) - $t0).TotalMinutes, $rc)
}
Write-Host "Done. Next: $py scripts\make_results.py"
