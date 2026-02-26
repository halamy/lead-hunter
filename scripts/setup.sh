#!/bin/bash
# ============================================================================
# Lead Hunter — VPS Setup Script
# Run via SSH: bash setup.sh
# ============================================================================
set -e

echo "============================================"
echo "  Lead Hunter — VPS Setup"
echo "============================================"
echo ""

# --------------------------------------------------------------------------
# Phase 1: System dependencies
# --------------------------------------------------------------------------
echo "[1/5] Installing system dependencies..."
sudo apt-get update -qq
sudo apt-get install -y python3 python3-pip python3-venv git -qq
echo "  Done."

# --------------------------------------------------------------------------
# Phase 2: Clone repo and setup venv
# --------------------------------------------------------------------------
INSTALL_DIR="$HOME/lead-hunter"

if [ -d "$INSTALL_DIR" ]; then
  echo "[2/5] Directory exists. Pulling latest..."
  cd "$INSTALL_DIR" && git pull
else
  echo "[2/5] Cloning repository..."
  git clone https://github.com/halamy/lead-hunter.git "$INSTALL_DIR"
fi

cd "$INSTALL_DIR/scripts"

echo "  Creating virtual environment..."
python3 -m venv "$INSTALL_DIR/venv"
source "$INSTALL_DIR/venv/bin/activate"

echo "  Installing Python dependencies..."
pip install -r requirements.txt -q
echo "  Done."

# --------------------------------------------------------------------------
# Phase 3: Configure .env (interactive — nothing in shell history)
# --------------------------------------------------------------------------
echo ""
echo "[3/5] Configuring environment variables..."
echo "  (credentials are NOT saved in shell history)"
echo ""

ENV_FILE="$INSTALL_DIR/scripts/.env"

read -p "  SUPABASE_URL (https://xxx.supabase.co): " SUPA_URL
read -sp "  SUPABASE_KEY (service_role key): " SUPA_KEY
echo ""
read -sp "  GOOGLE_MAPS_API_KEY: " GMAPS_KEY
echo ""
read -sp "  ANTHROPIC_API_KEY: " ANTHROPIC_KEY
echo ""
read -p "  EVOLUTION_API_URL (http://ip:port): " EVO_URL
read -sp "  EVOLUTION_API_KEY: " EVO_KEY
echo ""
read -p "  EVOLUTION_INSTANCE (default: lead-hunter): " EVO_INSTANCE
EVO_INSTANCE=${EVO_INSTANCE:-lead-hunter}

cat > "$ENV_FILE" << ENVEOF
# Lead Hunter — Environment Variables
# Generated: $(date -u +"%Y-%m-%dT%H:%M:%SZ")
# DO NOT COMMIT THIS FILE

# Supabase
SUPABASE_URL=$SUPA_URL
SUPABASE_KEY=$SUPA_KEY

# Google Maps
GOOGLE_MAPS_API_KEY=$GMAPS_KEY

# Anthropic / Claude
ANTHROPIC_API_KEY=$ANTHROPIC_KEY

# Evolution API (WhatsApp)
EVOLUTION_API_URL=$EVO_URL
EVOLUTION_API_KEY=$EVO_KEY
EVOLUTION_INSTANCE=$EVO_INSTANCE
ENVEOF

chmod 600 "$ENV_FILE"
echo "  .env created with restricted permissions (600)."

# --------------------------------------------------------------------------
# Phase 4: Dry run validation
# --------------------------------------------------------------------------
echo ""
echo "[4/5] Running dry-run validation..."
echo ""

set -a
source "$ENV_FILE"
set +a

python3 dry-run-test.py

echo ""

# --------------------------------------------------------------------------
# Phase 5: Setup cron jobs
# --------------------------------------------------------------------------
echo "[5/5] Setting up cron jobs..."

VENV_PYTHON="$INSTALL_DIR/venv/bin/python3"
SCRIPTS_PATH="$INSTALL_DIR/scripts"
LOG_DIR="/var/log/lead-hunter"

sudo mkdir -p "$LOG_DIR"
sudo chown "$USER:$USER" "$LOG_DIR"

# Build cron entries
CRON_DISPATCH="*/5 9-16 * * 1-6 cd $SCRIPTS_PATH && set -a && source .env && set +a && $VENV_PYTHON queue-processor.py >> $LOG_DIR/queue.log 2>&1"
CRON_CLEANUP="0 23 * * * cd $SCRIPTS_PATH && set -a && source .env && set +a && $VENV_PYTHON end-of-day-cleanup.py >> $LOG_DIR/cleanup.log 2>&1"

# Install cron (preserve existing entries)
(crontab -l 2>/dev/null | grep -v "lead-hunter"; echo "# Lead Hunter — Queue Processor (every 5 min, 9h-17h BRT, Mon-Sat)"; echo "$CRON_DISPATCH"; echo "# Lead Hunter — End-of-day Cleanup (23h daily)"; echo "$CRON_CLEANUP") | crontab -

echo "  Cron jobs installed:"
echo "    - Queue processor: every 5 min (9h-17h BRT, Mon-Sat)"
echo "    - Cleanup: daily at 23h"
echo ""

# --------------------------------------------------------------------------
# Done
# --------------------------------------------------------------------------
echo "============================================"
echo "  Lead Hunter — Setup Complete"
echo "============================================"
echo ""
echo "  Install dir:  $INSTALL_DIR"
echo "  Python venv:  $INSTALL_DIR/venv"
echo "  Env file:     $SCRIPTS_PATH/.env"
echo "  Logs:         $LOG_DIR/"
echo ""
echo "  Next steps:"
echo "    1. Run the Supabase schema (SQL Editor):"
echo "       $INSTALL_DIR/data/supabase-schema.sql"
echo "       $INSTALL_DIR/data/migrations/*.sql"
echo ""
echo "    2. Monitor logs:"
echo "       tail -f $LOG_DIR/queue.log"
echo ""
echo "    3. Manual dispatch test:"
echo "       cd $SCRIPTS_PATH && source .env"
echo "       $VENV_PYTHON whatsapp-api-client.py --status"
echo ""
echo "  To stop: crontab -e (remove lead-hunter lines)"
echo "============================================"
