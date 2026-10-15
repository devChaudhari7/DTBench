#!/bin/bash
# Usage: scripts/run_model.sh <model-key>   (runs all 12 specs with a local llama.cpp server)
set -u
KEY=$1
ROOT=$(cd "$(dirname "$0")/.." && pwd)
LLAMA=${LLAMA_SERVER:-/home/claude/work/llama.cpp/build/bin/llama-server}
MODELS=${MODELS_DIR:-/home/claude/work/models}
case $KEY in
  qwen3-4b)    GGUF=$MODELS/Qwen3-4B-Instruct-2507-Q4_K_M.gguf ;;
  llama3.2-3b) GGUF=$MODELS/Llama-3.2-3B-Instruct-Q4_K_M.gguf ;;
  gemma3-4b)   GGUF=$MODELS/google_gemma-3-4b-it-Q4_K_M.gguf ;;
  *) echo "unknown model $KEY"; exit 1 ;;
esac
mkdir -p "$ROOT/results/raw" "$ROOT/results/logs"
"$LLAMA" -m "$GGUF" -c 8192 -t 2 -np 1 --jinja --host 127.0.0.1 --port 8080 > "$ROOT/results/logs/server_$KEY.log" 2>&1 &
SERVER=$!
for i in $(seq 1 120); do sleep 2; curl -s 127.0.0.1:8080/health | grep -q ok && break; done
cd "$ROOT" && python3 -m dtbench.runner --model "$KEY" --specs "${SPECS:-all}"
kill $SERVER; wait $SERVER 2>/dev/null
echo "finished $KEY"
