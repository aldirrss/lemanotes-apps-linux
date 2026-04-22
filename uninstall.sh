#!/usr/bin/env bash
# LemaNotes uninstaller
set -euo pipefail

INSTALL_DIR="$HOME/.local/lib/lemanotes"
DESKTOP_FILE="$HOME/.local/share/applications/lemanotes.desktop"
DESKTOP_ICON="$HOME/Desktop/lemanotes.desktop"
BIN_FILE="$HOME/.local/bin/lemanotes"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; RESET='\033[0m'

info()    { echo -e "${CYAN}[INFO]${RESET}  $*"; }
success() { echo -e "${GREEN}[OK]${RESET}    $*"; }
warn()    { echo -e "${YELLOW}[WARN]${RESET}  $*"; }

echo ""
echo -e "${BOLD}${RED}╔══════════════════════════════════════╗${RESET}"
echo -e "${BOLD}${RED}║      LemaNotes — Uninstaller         ║${RESET}"
echo -e "${BOLD}${RED}╚══════════════════════════════════════╝${RESET}"
echo ""

# ── Confirm ────────────────────────────────────────────────────────────────────
echo -e "${YELLOW}This will remove:${RESET}"
echo "  • App files     : $INSTALL_DIR"
echo "  • Launcher      : $BIN_FILE"
echo "  • Desktop entry : $DESKTOP_FILE"
[[ -f "$DESKTOP_ICON" ]] && echo "  • Desktop icon  : $DESKTOP_ICON"
echo ""
echo -e "${YELLOW}Your notes in ~/LemaNotes/ will NOT be deleted.${RESET}"
echo -e "${YELLOW}Your settings in ~/.config/lemanotes/ will NOT be deleted.${RESET}"
echo ""
read -rp "Continue uninstall? [y/N]: " _confirm
[[ "$_confirm" =~ ^[Yy]$ ]] || { echo "Aborted."; exit 0; }
echo ""

# ── Remove app files ───────────────────────────────────────────────────────────
if [[ -d "$INSTALL_DIR" ]]; then
    rm -rf "$INSTALL_DIR"
    success "Removed $INSTALL_DIR"
else
    warn "App directory not found: $INSTALL_DIR"
fi

# ── Remove desktop entries ─────────────────────────────────────────────────────
if [[ -f "$DESKTOP_FILE" ]]; then
    rm -f "$DESKTOP_FILE"
    success "Removed $DESKTOP_FILE"
fi

if [[ -f "$DESKTOP_ICON" ]]; then
    rm -f "$DESKTOP_ICON"
    success "Removed $DESKTOP_ICON"
fi

update-desktop-database "$HOME/.local/share/applications" 2>/dev/null || true

# ── Remove CLI launcher ────────────────────────────────────────────────────────
if [[ -f "$BIN_FILE" ]]; then
    rm -f "$BIN_FILE"
    success "Removed $BIN_FILE"
fi

# ── Done ───────────────────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}${GREEN}LemaNotes has been uninstalled.${RESET}"
echo ""
echo "  Your notes     : ${BOLD}~/LemaNotes/${RESET}  (kept)"
echo "  Your settings  : ${BOLD}~/.config/lemanotes/${RESET}  (kept)"
echo ""
echo "  To also remove notes and settings:"
echo "    rm -rf ~/LemaNotes ~/.config/lemanotes"
echo ""
