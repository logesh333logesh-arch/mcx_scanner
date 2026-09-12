#!/bin/bash
# run_mcx_scanner.sh (v3 — all 3 scanners run automatically all day from ONE morning command)
# ---------------------------------------------------------------
# Run this ONCE every trading morning. It:
#   1. Runs Scanner-4 (does the one-time browser/TOTP login, generates
#      today's baseline data -> token.txt) — this is a once-a-day job
#   2. Copies that token to mcx_scanner (this folder)
#   3. Pushes that same token to Scanner-2's GitHub repo -> its GitHub
#      Actions schedule runs all day automatically on this token
#   4. Pushes that same token to MCX scanner's OWN GitHub repo -> its
#      GitHub Actions schedule (mcx_scanner_workflow.yml) runs all day
#      automatically too — no need to manually run the scan intraday
#   5. Also runs one immediate local MCX scan right now, as a bonus/
#      sanity check (not required for the day's automation to work)
#
# After this script finishes, Scanner-2 AND MCX scanner both keep
# running on their own via GitHub Actions for the rest of the day.
# You do not need to touch Termux again until tomorrow morning.
#
# Save this file at: ~/mcx_scanner/run_mcx_scanner.sh
# Make it executable once: chmod +x run_mcx_scanner.sh
# Run it daily with: ./run_mcx_scanner.sh
#
# ONE-TIME SETUP before first use:
#   git clone https://github.com/logesh333logesh-arch/scanner-2-upstox.git ~/scanner-2-upstox
#   Confirm mcx_scanner_workflow.yml is committed at:
#     .github/workflows/mcx_scanner_workflow.yml   (inside the mcx_scanner repo)
#   Confirm Scanner-2's repo similarly has its own workflow file already.
# ---------------------------------------------------------------

set -e  # stop immediately if any step fails

SCANNER4_DIR=~/Scanner-4
MCX_DIR=~/mcx_scanner
SCANNER2_DIR=~/scanner-2-upstox
SCANNER2_REPO="https://github.com/logesh333logesh-arch/scanner-2-upstox.git"
SCANNER5_DIR=~/scanner5_project/scanner5
SCANNER5_REPO="https://github.com/logesh333logesh-arch/scanner5-opsan-strategy.git"

echo "========================================"
echo "[1/6] Running Scanner-4 (handles Upstox login + daily baseline)..."
echo "========================================"
cd "$SCANNER4_DIR"
./run_scanner4.sh

echo ""
echo "[INFO] Waiting 10s for the new token to fully activate on Upstox's side..."
sleep 10

echo ""
echo "========================================"
echo "[2/6] Copying fresh token to mcx_scanner..."
echo "========================================"
cp "$SCANNER4_DIR/token.txt" "$MCX_DIR/token.txt"
echo "[OK] token.txt copied to mcx_scanner."

echo ""
echo "========================================"
echo "[3/6] Pushing fresh token to Scanner-2's repo..."
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
echo "[3.5/6] Updating Scanner-2's GitHub secret (UPSTOX_ACCESS_TOKEN)..."
echo "========================================"
# Scanner-2's scanner.py reads the token from a GitHub Actions SECRET
# (not from token.txt), so pushing the file alone isn't enough — the
# secret itself must be refreshed daily too, or Scanner-2 keeps using
# yesterday's stale token and gets 401 Unauthorized.
gh secret set UPSTOX_ACCESS_TOKEN --repo logesh333logesh-arch/scanner-2-upstox < "$SCANNER4_DIR/token.txt"
echo "[OK] Scanner-2's UPSTOX_ACCESS_TOKEN secret updated with today's fresh token."

echo ""
echo "========================================"
echo "[4/5] Pushing fresh token to MCX scanner's OWN repo (for its GitHub Actions)..."
echo "========================================"
cd "$MCX_DIR"
git pull
git add token.txt
git commit -m "daily token update" || echo "[INFO] no change to commit"
git push
echo "[OK] token.txt pushed to mcx_scanner repo — its GitHub Actions runs will use this all day."

echo ""
echo "========================================"
echo "[5/5] Running one immediate local MCX scan (bonus sanity check)..."
echo "========================================"
python mcx_scanner_main.py

echo ""
echo "========================================"
echo "Done. Check Telegram for MCX alerts."
echo "Scanner-2 AND MCX scanner will now run automatically all day"
echo "via their own GitHub Actions schedules — no further action needed."
echo "========================================"
