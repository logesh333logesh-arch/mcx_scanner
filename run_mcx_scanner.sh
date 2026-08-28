#!/bin/bash
# run_mcx_scanner.sh (v2 — handles all 3 scanners sharing one Upstox token)
# ---------------------------------------------------------------
# Run this ONCE every trading morning. It:
#   1. Runs Scanner-4 (does the one-time browser/TOTP login -> token.txt)
#   2. Copies that token to mcx_scanner (this folder)
#   3. Pushes that same token to Scanner-2's GitHub repo, so its
#      GitHub Actions runs use it all day (no separate login there)
#   4. Runs the MCX scan
#
# Save this file at: ~/mcx_scanner/run_mcx_scanner.sh
# Make it executable once: chmod +x run_mcx_scanner.sh
# Run it daily with: ./run_mcx_scanner.sh
#
# ONE-TIME SETUP before first use:
#   git clone https://github.com/logesh333logesh-arch/scanner-2-upstox.git ~/scanner-2-upstox
# (skip if you've already cloned it somewhere else — just update
#  SCANNER2_DIR below to match)
# ---------------------------------------------------------------

set -e  # stop immediately if any step fails

SCANNER4_DIR=~/Scanner-4
MCX_DIR=~/mcx_scanner
SCANNER2_DIR=~/scanner-2-upstox
SCANNER2_REPO="https://github.com/logesh333logesh-arch/scanner-2-upstox.git"

echo "========================================"
echo "[1/4] Running Scanner-4 (handles Upstox login)..."
echo "========================================"
cd "$SCANNER4_DIR"
./run_scanner4.sh

echo ""
echo "[INFO] Waiting 10s for the new token to fully activate on Upstox's side..."
sleep 10

echo ""
echo "========================================"
echo "[2/4] Copying fresh token to mcx_scanner..."
echo "========================================"
cp "$SCANNER4_DIR/token.txt" "$MCX_DIR/token.txt"
echo "[OK] token.txt copied to mcx_scanner."

echo ""
echo "========================================"
echo "[3/4] Pushing fresh token to Scanner-2's repo..."
echo "========================================"
if [ ! -d "$SCANNER2_DIR" ]; then
    echo "[INFO] $SCANNER2_DIR not found, cloning..."
    git clone "$SCANNER2_REPO" "$SCANNER2_DIR"
fi
cd "$SCANNER2_DIR"
git pull
cp "$SCANNER4_DIR/token.txt" "$SCANNER2_DIR/token.txt"
git add token.txt
git commit -m "daily token update" || echo "[INFO] no change to commit"
git push
echo "[OK] token.txt pushed to Scanner-2 repo — its GitHub Actions runs will use this all day."

echo ""
echo "========================================"
echo "[4/4] Running MCX scanner..."
echo "========================================"
cd "$MCX_DIR"
python mcx_scanner_main.py

echo ""
echo "========================================"
echo "Done. Check Telegram for MCX alerts."
echo "Scanner-2's GitHub Actions will keep running on today's token."
echo "========================================"
