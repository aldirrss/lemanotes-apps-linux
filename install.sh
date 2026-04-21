#!/usr/bin/env bash
# LemaNotes installer for Ubuntu / Debian
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_NAME="LemaNotes"
DESKTOP_FILE="$HOME/.local/share/applications/lemanotes.desktop"
INSTALL_DIR="$HOME/.local/lib/lemanotes"

# ── Colour helpers ─────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; RESET='\033[0m'

info()    { echo -e "${CYAN}[INFO]${RESET}  $*"; }
success() { echo -e "${GREEN}[OK]${RESET}    $*"; }
warn()    { echo -e "${YELLOW}[WARN]${RESET}  $*"; }
error()   { echo -e "${RED}[ERROR]${RESET} $*" >&2; }
die()     { error "$*"; exit 1; }

# ── Dialog helper (zenity → kdialog → whiptail → plain read) ──────────────────
HAS_ZENITY=false; HAS_KDIALOG=false; HAS_WHIPTAIL=false
command -v zenity   &>/dev/null && HAS_ZENITY=true
command -v kdialog  &>/dev/null && HAS_KDIALOG=true
command -v whiptail &>/dev/null && HAS_WHIPTAIL=true

ask_choice() {
    # Usage: ask_choice "Title" "Question" "Option1" "Option2"
    local title="$1" question="$2" opt1="$3" opt2="$4"
    if $HAS_ZENITY; then
        zenity --list --title="$title" --text="$question" \
               --radiolist --column="" --column="Mode" \
               TRUE "$opt1" FALSE "$opt2" \
               --width=420 --height=220 2>/dev/null || echo "$opt1"
    elif $HAS_KDIALOG; then
        kdialog --title "$title" --radiolist "$question" \
                1 "$opt1" on 2 "$opt2" off 2>/dev/null | \
            awk '{if($0=="1") print "'"$opt1"'"; else print "'"$opt2"'"}'
    elif $HAS_WHIPTAIL; then
        whiptail --title "$title" --radiolist "$question" 12 60 2 \
                 "$opt1" "" ON \
                 "$opt2" "" OFF \
                 3>&1 1>&2 2>&3 || echo "$opt1"
    else
        echo ""
        echo -e "${BOLD}$title${RESET}"
        echo "$question"
        echo "  1) $opt1 (default)"
        echo "  2) $opt2"
        read -rp "Choose [1/2]: " _choice
        [[ "$_choice" == "2" ]] && echo "$opt2" || echo "$opt1"
    fi
}

ask_input() {
    # Usage: ask_input "Title" "Label" "default_value"
    local title="$1" label="$2" default="${3:-}"
    if $HAS_ZENITY; then
        zenity --entry --title="$title" --text="$label" \
               --entry-text="$default" 2>/dev/null || echo "$default"
    elif $HAS_KDIALOG; then
        kdialog --title "$title" --inputbox "$label" "$default" 2>/dev/null || echo "$default"
    elif $HAS_WHIPTAIL; then
        whiptail --title "$title" --inputbox "$label" 10 70 "$default" \
                 3>&1 1>&2 2>&3 || echo "$default"
    else
        read -rp "$label [$default]: " _val
        echo "${_val:-$default}"
    fi
}

show_info() {
    local title="$1" msg="$2"
    if $HAS_ZENITY; then
        zenity --info --title="$title" --text="$msg" --width=380 2>/dev/null || true
    elif $HAS_KDIALOG; then
        kdialog --title "$title" --msgbox "$msg" 2>/dev/null || true
    elif $HAS_WHIPTAIL; then
        whiptail --title "$title" --msgbox "$msg" 12 60 || true
    else
        echo -e "\n${BOLD}$title${RESET}\n$msg\n"
    fi
}

# ── Banner ─────────────────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}${CYAN}╔══════════════════════════════════════╗${RESET}"
echo -e "${BOLD}${CYAN}║       LemaNotes — Installer          ║${RESET}"
echo -e "${BOLD}${CYAN}╚══════════════════════════════════════╝${RESET}"
echo ""

# ── Step 1 — System dependencies ──────────────────────────────────────────────
info "Installing system dependencies…"
sudo apt-get install -y \
    libxcb-cursor0 libxcb-xinerama0 libxcb-icccm4 \
    libxcb-image0 libxcb-keysyms1 libxcb-render-util0 \
    python3 python3-pip \
    2>&1 | grep -E "^(Setting up|Get:|Err:|Reading)" || true

# Try installing PyQt6-WebEngine via apt (system package — more reliable on Ubuntu)
if dpkg -l python3-pyqt6.qtwebengine &>/dev/null 2>&1; then
    success "python3-pyqt6.qtwebengine already installed"
else
    info "Trying to install PyQt6-WebEngine via apt…"
    sudo apt-get install -y python3-pyqt6.qtwebengine 2>/dev/null || \
        warn "apt install of WebEngine failed — will try pip later"
fi

success "System dependencies done"

# ── Step 2 — Python dependencies ──────────────────────────────────────────────
info "Installing Python dependencies…"
PYTHON_BIN="python3"

# Prefer conda env if active
if command -v conda &>/dev/null && [[ -n "${CONDA_DEFAULT_ENV:-}" ]]; then
    info "Conda environment detected: $CONDA_DEFAULT_ENV"
    PYTHON_BIN="python"
fi

"$PYTHON_BIN" -m pip install --quiet --upgrade pip
"$PYTHON_BIN" -m pip install --quiet -r "$SCRIPT_DIR/requirements.txt"
success "Python dependencies installed"

# ── Step 3 — Sync mode choice ─────────────────────────────────────────────────
echo ""
SYNC_MODE=$(ask_choice \
    "LemaNotes — Sync Configuration" \
    "How should cloud sync be configured?\n\n  Static   — Supabase URL and Anon Key are embedded during install.\n             Users only need to log in (no setup dialog in app).\n\n  Dynamic  — Users configure Supabase credentials inside the app\n             (Account → Setup Supabase…)." \
    "Static (pre-configured)" \
    "Dynamic (in-app setup)")

ENV_FILE="$SCRIPT_DIR/.env"

if [[ "$SYNC_MODE" == "Static (pre-configured)" ]]; then
    echo ""
    info "Static mode selected — enter your Supabase credentials."
    echo ""

    SUPA_URL=$(ask_input \
        "Supabase URL" \
        "Enter your Supabase Project URL:" \
        "https://xxxx.supabase.co")

    SUPA_KEY=$(ask_input \
        "Supabase Anon Key" \
        "Enter your Supabase Anon Key (starts with eyJ…):" \
        "")

    if [[ -z "$SUPA_URL" || "$SUPA_URL" == "https://xxxx.supabase.co" || -z "$SUPA_KEY" ]]; then
        warn "Invalid or empty credentials — falling back to Dynamic mode."
        SYNC_MODE="Dynamic (in-app setup)"
    else
        cat > "$ENV_FILE" <<EOF
# LemaNotes — auto-generated by install.sh
LEMANOTES_SYNC_FROM_ENV=true
LEMANOTES_SUPABASE_URL=${SUPA_URL}
LEMANOTES_ANON_KEY=${SUPA_KEY}
EOF
        success ".env written with static Supabase credentials"
    fi
fi

if [[ "$SYNC_MODE" == "Dynamic (in-app setup)" ]]; then
    cat > "$ENV_FILE" <<EOF
# LemaNotes — auto-generated by install.sh
LEMANOTES_SYNC_FROM_ENV=false
LEMANOTES_SUPABASE_URL=
LEMANOTES_ANON_KEY=
EOF
    success ".env written — Dynamic mode (configure via app)"
fi

# ── Step 4 — Desktop shortcut ─────────────────────────────────────────────────
info "Creating desktop shortcut…"
ICON_PATH="$SCRIPT_DIR/assets/images/icon.png"
mkdir -p "$(dirname "$DESKTOP_FILE")"

cat > "$DESKTOP_FILE" <<EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=LemaNotes
Comment=Hierarchical notes app with optional Supabase sync
Exec=$PYTHON_BIN $SCRIPT_DIR/run.py
Icon=$ICON_PATH
Terminal=false
Categories=Office;TextEditor;
StartupWMClass=LemaNotes
EOF

chmod +x "$DESKTOP_FILE"

# Register with desktop (best-effort)
if command -v update-desktop-database &>/dev/null; then
    update-desktop-database "$HOME/.local/share/applications" 2>/dev/null || true
fi
if command -v xdg-desktop-menu &>/dev/null; then
    xdg-desktop-menu forceupdate 2>/dev/null || true
fi

success "Desktop shortcut created: $DESKTOP_FILE"

# ── Step 5 — Launcher script in ~/.local/bin ──────────────────────────────────
BIN_DIR="$HOME/.local/bin"
mkdir -p "$BIN_DIR"
cat > "$BIN_DIR/lemanotes" <<EOF
#!/usr/bin/env bash
exec $PYTHON_BIN $SCRIPT_DIR/run.py "\$@"
EOF
chmod +x "$BIN_DIR/lemanotes"

# Ensure ~/.local/bin is in PATH for this shell
if ! echo "$PATH" | grep -q "$BIN_DIR"; then
    warn "~/.local/bin is not in your PATH."
    warn "Add this line to your ~/.bashrc or ~/.zshrc:"
    warn "  export PATH=\"\$HOME/.local/bin:\$PATH\""
fi

success "Launcher installed: $BIN_DIR/lemanotes"

# ── Done ──────────────────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}${GREEN}Installation complete!${RESET}"
echo ""
echo -e "  Run from terminal : ${BOLD}lemanotes${RESET}"
echo -e "  Run directly      : ${BOLD}$PYTHON_BIN $SCRIPT_DIR/run.py${RESET}"
echo -e "  Desktop shortcut  : search for ${BOLD}LemaNotes${RESET} in your app launcher"
echo ""

show_info "LemaNotes installed" \
"Installation complete!\n\nSync mode: $SYNC_MODE\n\nYou can now launch LemaNotes from your app launcher\nor by running: lemanotes"
