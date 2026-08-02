#!/usr/bin/env bash
# s3d/run_eval.sh — ewaluacja zamknietej petli 3d (PRE_3D0 §6): wszystkie ramiona x 3 nogi.
# Kazde wywolanie 'measure <arm> all [seed]' = 3 nogi (clean/p50/L5) x N=100.
# Weryfikacja artefaktow po kazdym biegu; 1 retry przy padzie (WSL/GPU exit 144 / dxg -22).
set -u
cd "$(dirname "$0")/.."
PY=.venv/bin/python
OUT=results/s3d
SEEDS="45040 45041 45042 45043 45044"
LEGS="clean p50 L5"

run_one () {  # $1=arm  $2=seed(opt)
  local arm="$1" seed="${2:-}"
  local tagbase="${arm}${seed:+_s${seed}}"
  local ok=1
  for leg in $LEGS; do [ -f "$OUT/eval_${tagbase}_${leg}.json" ] || ok=0; done
  if [ "$ok" = 1 ]; then echo "SKIP $tagbase (artefakty juz sa)"; return 0; fi
  for attempt in 1 2; do
    echo ">>> measure $arm all $seed (proba $attempt)"
    $PY -m s3d.measure "$arm" all $seed > "$OUT/log_${tagbase}.log" 2>&1
    local rc=$?
    ok=1; for leg in $LEGS; do [ -f "$OUT/eval_${tagbase}_${leg}.json" ] || ok=0; done
    if [ "$rc" = 0 ] && [ "$ok" = 1 ]; then
      grep -E "^\[" "$OUT/log_${tagbase}.log" | tail -3
      return 0
    fi
    echo "!! pad ($tagbase) rc=$rc ok=$ok — retry" ; sleep 3
  done
  echo "!! TRWALY PAD $tagbase — STOP driver"; return 1
}

run_one A0        || exit 1
run_one A1        || exit 1
for s in $SEEDS; do run_one A2 "$s" || exit 1; done
for s in $SEEDS; do run_one A3 "$s" || exit 1; done
echo "=== EVAL KOMPLET ==="
