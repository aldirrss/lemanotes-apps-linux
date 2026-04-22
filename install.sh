#!/usr/bin/env bash
# LemaNotes installer for Ubuntu / Debian
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_DIR="$HOME/.local/lib/lemanotes"
VENV_DIR="$INSTALL_DIR/venv"
DESKTOP_FILE="$HOME/.local/share/applications/lemanotes.desktop"
BIN_DIR="$HOME/.local/bin"

# ── Shared server credentials (pre-configured by developer) ───────────────────
SHARED_SUPA_URL="https://yhtypmmnbjfbtqerxldk.supabase.co"
SHARED_SUPA_KEY="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InlodHlwbW1uYmpmYnRxZXJ4bGRrIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzY2ODc4MDcsImV4cCI6MjA5MjI2MzgwN30.cCVrBQCSqtRGMCj5IePpM6ZRe0rW_uDuenqWpkoOpF0"

# ── Colour helpers ─────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; DIM='\033[2m'; RESET='\033[0m'
WHITE='\033[1;37m'

info()    { echo -e "  ${CYAN}›${RESET}  $*"; }
success() { echo -e "  ${GREEN}✓${RESET}  $*"; }
warn()    { echo -e "  ${YELLOW}⚠${RESET}  $*"; }
die()     { echo -e "  ${RED}✗  $*${RESET}" >&2; exit 1; }

# ── Dialog helpers ─────────────────────────────────────────────────────────────
# All display inside ask_* functions goes to stderr so $() capture is clean.

HAS_ZENITY=false
command -v zenity &>/dev/null && HAS_ZENITY=true

_p()  { echo -e "$*" >&2; }

_dialog_box() {
    local title="$1"
    _p ""
    _p "${CYAN}${BOLD}  ╭──────────────────────────────────────────────────────────╮${RESET}"
    _p "${CYAN}${BOLD}  │${RESET}  ${WHITE}$(printf '%-56s' "$title")${CYAN}${BOLD}│${RESET}"
    _p "${CYAN}${BOLD}  ╰──────────────────────────────────────────────────────────╯${RESET}"
    _p ""
}

ask_choice() {
    local title="$1" question="$2" opt1="$3" opt2="$4"
    if $HAS_ZENITY; then
        # --question with custom button labels is much cleaner than --list radiolist
        if zenity --question \
               --title="$title" \
               --text="$(echo -e "$question")" \
               --ok-label="$opt1" \
               --cancel-label="$opt2" \
               --width=460 2>/dev/null; then
            echo "$opt1"
        else
            echo "$opt2"
        fi
        return
    fi
    _dialog_box "$title"
    echo -e "$question" | while IFS= read -r _ln; do _p "  ${DIM}$_ln${RESET}"; done
    _p ""
    _p "  ${CYAN}${BOLD}  ┌──────────────────────────────────────────────────────┐${RESET}"
    _p "  ${CYAN}${BOLD}  │${RESET}  ${GREEN}${BOLD}1)${RESET}  ${BOLD}${opt1}${RESET}  ${YELLOW}← default${RESET}"
    _p "  ${CYAN}${BOLD}  │${RESET}  ${DIM}2)  ${opt2}${RESET}"
    _p "  ${CYAN}${BOLD}  └──────────────────────────────────────────────────────┘${RESET}"
    _p ""
    local _c
    read -rp "$(echo -e "  ${BOLD}     Select [1/2]:${RESET} ")" _c
    _p ""
    [[ "$_c" == "2" ]] && echo "$opt2" || echo "$opt1"
}

ask_input() {
    local title="$1" label="$2" default="${3:-}"
    if $HAS_ZENITY; then
        zenity --entry --title="$title" --text="$label" \
               --entry-text="$default" 2>/dev/null || echo "$default"
        return
    fi
    _dialog_box "$title"
    _p "  ${BOLD}${label}${RESET}"
    [[ -n "$default" ]] && _p "  ${DIM}Leave blank to use: ${default}${RESET}"
    _p ""
    local _v
    read -rp "$(echo -e "  ${YELLOW}▶${RESET} ")" _v
    _p ""
    echo "${_v:-$default}"
}

show_info() {
    local title="$1" msg="$2"
    if $HAS_ZENITY; then
        zenity --info --title="$title" --text="$msg" --width=440 2>/dev/null || true
        return
    fi
    echo ""
    echo -e "${GREEN}${BOLD}  ╔══════════════════════════════════════════════════════════╗${RESET}"
    echo -e "${GREEN}${BOLD}  ║${RESET}  ${GREEN}${BOLD}✓  $(printf '%-54s' "$title")║${RESET}"
    echo -e "${GREEN}${BOLD}  ╚══════════════════════════════════════════════════════════╝${RESET}"
    echo ""
    echo -e "$msg" | while IFS= read -r _ln; do echo -e "  $_ln"; done
    echo ""
}

# ── Banner ─────────────────────────────────────────────────────────────────────
echo ""
echo -e "${CYAN}${BOLD}  ╔═══════════════════════════════════════╗${RESET}"
echo -e "${CYAN}${BOLD}  ║       LemaNotes  Installer            ║${RESET}"
echo -e "${CYAN}${BOLD}  ╚═══════════════════════════════════════╝${RESET}"
echo ""

# ── Step 1 — System dependencies ──────────────────────────────────────────────
info "Installing system dependencies…"
sudo apt-get install -y \
    libxcb-cursor0 libxcb-xinerama0 libxcb-icccm4 \
    libxcb-image0 libxcb-keysyms1 libxcb-render-util0 \
    python3 python3-pip python3-venv rsync \
    2>&1 | grep -E "^(Setting up|Get:|Err:)" || true

if ! dpkg -l python3-pyqt6.qtwebengine &>/dev/null 2>&1; then
    sudo apt-get install -y python3-pyqt6.qtwebengine 2>/dev/null || true
fi
success "System dependencies done"

# ── Step 2 — Detect or create Python environment ──────────────────────────────
info "Detecting Python environment with PyQt6…"
PYTHON_BIN=""
USING_VENV=false

# Priority 1: active conda env
if [[ -n "${CONDA_PREFIX:-}" ]]; then
    _py="$CONDA_PREFIX/bin/python"
    "$_py" -c "import PyQt6" 2>/dev/null && PYTHON_BIN="$_py" && \
        info "Using active conda env: ${CONDA_DEFAULT_ENV:-unknown}"
fi

# Priority 2: all conda envs
if [[ -z "$PYTHON_BIN" ]] && command -v conda &>/dev/null; then
    _base=$(conda info --base 2>/dev/null || echo "")
    if [[ -n "$_base" ]]; then
        while IFS= read -r _env; do
            _py="$_env/bin/python"
            [[ -x "$_py" ]] || continue
            if "$_py" -c "import PyQt6" 2>/dev/null; then
                PYTHON_BIN="$_py"
                info "Found PyQt6 in conda env: $_env"
                break
            fi
        done < <(find "$_base/envs" -maxdepth 1 -mindepth 1 -type d 2>/dev/null)
    fi
fi

# Priority 3: system python that already has PyQt6
if [[ -z "$PYTHON_BIN" ]]; then
    for _candidate in python3.12 python3.11 python3.10 python3; do
        _full=$(command -v "$_candidate" 2>/dev/null || true)
        if [[ -n "$_full" ]] && "$_full" -c "import PyQt6" 2>/dev/null; then
            PYTHON_BIN="$_full"
            info "Found PyQt6 in system Python: $PYTHON_BIN"
            break
        fi
    done
fi

# Priority 4: create a venv inside INSTALL_DIR and install everything there
if [[ -z "$PYTHON_BIN" ]]; then
    info "No existing Python with PyQt6 found — creating virtual environment…"

    # Find the best available python3
    BASE_PY=""
    for _candidate in python3.12 python3.11 python3.10 python3; do
        BASE_PY=$(command -v "$_candidate" 2>/dev/null || true)
        [[ -n "$BASE_PY" ]] && break
    done
    [[ -z "$BASE_PY" ]] && die "python3 not found. Install it with: sudo apt install python3"

    mkdir -p "$INSTALL_DIR"
    "$BASE_PY" -m venv "$VENV_DIR"
    PYTHON_BIN="$VENV_DIR/bin/python"
    USING_VENV=true
    info "Virtual environment created at $VENV_DIR"
fi

success "Python: $PYTHON_BIN"

# ── Step 3 — Install Python packages ──────────────────────────────────────────
info "Installing Python packages…"
if $USING_VENV; then
    # Fresh venv — install everything
    "$PYTHON_BIN" -m pip install --quiet --upgrade pip
    "$PYTHON_BIN" -m pip install --quiet -r "$SCRIPT_DIR/requirements.txt"
else
    # Existing env — only install what's missing
    "$PYTHON_BIN" -m pip install --quiet -r "$SCRIPT_DIR/requirements.txt"
fi
success "Python packages ready"

# ── Step 3 — Copy app to permanent install directory ──────────────────────────
info "Installing app to $INSTALL_DIR …"
mkdir -p "$INSTALL_DIR"

rsync -a --delete \
    "$SCRIPT_DIR/run.py" \
    "$SCRIPT_DIR/notes_app" \
    "$SCRIPT_DIR/assets" \
    "$INSTALL_DIR" \
    --exclude="__pycache__" \
    --exclude="*.pyc"

# Keep requirements.txt for reference
cp "$SCRIPT_DIR/requirements.txt" "$INSTALL_DIR/requirements.txt"

success "App files copied to $INSTALL_DIR"

# ── Step 4 — Server & sync configuration ──────────────────────────────────────
echo ""
SERVER_TYPE=$(ask_choice \
    "LemaNotes — Database Server" \
    "Which database server do you want to use?\n\n  Shared Server  — Connect to the developer's server.\n                   Just register / log in, no setup needed.\n\n  Self Hosted    — Use your own Supabase project." \
    "Shared Server (recommended)" \
    "Self Hosted (my own Supabase)")

ENV_FILE="$INSTALL_DIR/.env"
SYNC_MODE="Shared Server"

if [[ "$SERVER_TYPE" == "Shared Server (recommended)" ]]; then
    cat > "$ENV_FILE" <<EOF
# LemaNotes — generated by install.sh
LEMANOTES_SYNC_FROM_ENV=true
LEMANOTES_SUPABASE_URL=${SHARED_SUPA_URL}
LEMANOTES_SUPABASE_ANON_KEY=${SHARED_SUPA_KEY}
EOF
    success ".env written — Shared Server"

else
    # Self Hosted: ask Static or Dynamic
    SYNC_MODE=$(ask_choice \
        "LemaNotes — Self Hosted Sync" \
        "How should cloud sync be configured?\n\n  Static   — Enter Supabase credentials now.\n             Embedded in the app, users only need to log in.\n\n  Dynamic  — Users configure credentials inside the app\n             via Account → Setup Supabase…" \
        "Static (pre-configured)" \
        "Dynamic (in-app setup)")

    if [[ "$SYNC_MODE" == "Static (pre-configured)" ]]; then
        echo ""
        info "Enter your Supabase credentials."

        SUPA_URL=$(ask_input "Supabase URL" \
            "Supabase Project URL:" "https://xxxx.supabase.co")
        SUPA_KEY=$(ask_input "Supabase Anon Key" \
            "Supabase Anon Key (starts with eyJ…):" "")

        if [[ -z "$SUPA_URL" || "$SUPA_URL" == "https://xxxx.supabase.co" || -z "$SUPA_KEY" ]]; then
            warn "Invalid credentials — falling back to Dynamic mode."
            SYNC_MODE="Dynamic (in-app setup)"
        else
            cat > "$ENV_FILE" <<EOF
# LemaNotes — generated by install.sh
LEMANOTES_SYNC_FROM_ENV=true
LEMANOTES_SUPABASE_URL=${SUPA_URL}
LEMANOTES_SUPABASE_ANON_KEY=${SUPA_KEY}
EOF
            success ".env written with static credentials"
        fi
    fi

    if [[ "$SYNC_MODE" == "Dynamic (in-app setup)" ]]; then
        cat > "$ENV_FILE" <<EOF
# LemaNotes — generated by install.sh
LEMANOTES_SYNC_FROM_ENV=false
LEMANOTES_SUPABASE_URL=
LEMANOTES_SUPABASE_ANON_KEY=
EOF
        success ".env written — Dynamic mode"
    fi
fi

# ── Step 5 — Desktop shortcut ─────────────────────────────────────────────────
info "Creating desktop shortcut…"
ICON_PATH="$INSTALL_DIR/assets/images/icon.png"
mkdir -p "$(dirname "$DESKTOP_FILE")"

cat > "$DESKTOP_FILE" <<EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=LemaNotes
Comment=Hierarchical notes app with optional Supabase sync
Exec=${PYTHON_BIN} ${INSTALL_DIR}/run.py
Icon=${ICON_PATH}
Terminal=false
Categories=Office;TextEditor;
StartupWMClass=LemaNotes
EOF

chmod +x "$DESKTOP_FILE"

# Copy to Desktop as well
if [[ -d "$HOME/Desktop" ]]; then
    cp "$DESKTOP_FILE" "$HOME/Desktop/lemanotes.desktop"
    chmod +x "$HOME/Desktop/lemanotes.desktop"
    gio set "$HOME/Desktop/lemanotes.desktop" metadata::trusted true 2>/dev/null || true
fi

update-desktop-database "$HOME/.local/share/applications" 2>/dev/null || true
success "Desktop shortcut created"

# ── Step 6 — CLI launcher ─────────────────────────────────────────────────────
mkdir -p "$BIN_DIR"
cat > "$BIN_DIR/lemanotes" <<EOF
#!/usr/bin/env bash
exec ${PYTHON_BIN} ${INSTALL_DIR}/run.py "\$@"
EOF
chmod +x "$BIN_DIR/lemanotes"

if ! echo "$PATH" | grep -q "$BIN_DIR"; then
    warn "Add ~/.local/bin to PATH: export PATH=\"\$HOME/.local/bin:\$PATH\""
fi
success "CLI launcher: $BIN_DIR/lemanotes"

# ── Done ──────────────────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}${BOLD}  ╔════════════════════════════════════════════╗${RESET}"
echo -e "${GREEN}${BOLD}  ║   LemaNotes installed successfully!        ║${RESET}"
echo -e "${GREEN}${BOLD}  ╚════════════════════════════════════════════╝${RESET}"
echo ""
echo -e "  ${DIM}App directory  ${RESET}: ${BOLD}$INSTALL_DIR${RESET}"
echo -e "  ${DIM}Run in terminal${RESET}: ${CYAN}${BOLD}lemanotes${RESET}"
echo -e "  ${DIM}Sync mode      ${RESET}: ${YELLOW}${BOLD}$SYNC_MODE${RESET}"
echo ""
echo -e "  ${DIM}The installer folder can now be safely deleted.${RESET}"
echo ""

show_info "LemaNotes installed successfully!" \
"App installed at:
  $INSTALL_DIR

Run from terminal:  lemanotes
Sync mode:          $SYNC_MODE

You can now safely delete this installer folder."
