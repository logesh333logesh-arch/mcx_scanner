#!/bin/bash
set -e
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
echo "[OK] token.txt pushed to Scanner-2 repo."

echo ""
echo "========================================"
echo "[3.5/6] Updating Scanner-2's GitHub secret (UPSTOX_ACCESS_TOKEN)..."
echo "========================================"
gh secret set UPSTOX_ACCESS_TOKEN --repo logesh333logesh-arch/scanner-2-upstox < "$SCANNER4_DIR/token.txt"
echo "[OK] Scanner-2's UPSTOX_ACCESS_TOKEN secret updated."

echo ""
echo "========================================"
echo "[4/6] Pushing fresh token to MCX scanner's OWN repo..."
echo "========================================"
cd "$MCX_DIR"
git pull
git add token.txt
git commit -m "daily token update" || echo "[INFO] no change to commit"
git push
echo "[OK] token.txt pushed to mcx_scanner repo."

echo ""
echo "========================================"
echo "[5/6] Pushing fresh token to Scanner-5's repo + secret..."
echo "========================================"
if [ ! -d "$SCANNER5_DIR" ]; then
    echo "[INFO] $SCANNER5_DIR not found, cloning..."
    mkdir -p "$(dirname "$SCANNER5_DIR")"
    git clone "$SCANNER5_REPO" "$SCANNER5_DIR"
fi
cd "$SCANNER5_DIR"
git pull
cp "$SCANNER4_DIR/token.txt" "$SCANNER5_DIR/token.txt"
git add token.txt
git commit -m "daily token update" || echo "[INFO] no change to commit"
git push
gh secret set UPSTOX_TOKEN --repo logesh333logesh-arch/scanner5-opsan-strategy < "$SCANNER4_DIR/token.txt"
echo "[OK] token.txt pushed to Scanner-5 repo, UPSTOX_TOKEN secret updated."

echo ""
echo "========================================"
echo "[6/6] Refreshing instrument master + running local MCX scan..."
echo "========================================"
cd "$MCX_DIR"
mkdir -p instruments
curl -s -o instruments/mcx_instruments.csv.gz https://assets.upstox.com/market-quote/instruments/exchange/MCX.csv.gz
gunzip -f instruments/mcx_instruments.csv.gz
python mcx_scanner_main.py

echo ""
echo "========================================"
echo "Done. Check Telegram for MCX + Scanner-5 alerts."
echo "Scanner-2, MCX scanner, AND Scanner-5 will now run automatically all day."
echo "========================================"
