#!/usr/bin/env bash
# Second Brain vault setup (macOS / Linux). Safe to run more than once.
#   bash setup.sh                    # full setup
#   bash setup.sh --remove-examples  # also delete the example notes
#   bash setup.sh --skip-install --no-obsidian
set -euo pipefail

SKIP_INSTALL=0; NO_OBSIDIAN=0; REMOVE_EXAMPLES=0
for a in "$@"; do
  case "$a" in
    --skip-install) SKIP_INSTALL=1 ;;
    --no-obsidian) NO_OBSIDIAN=1 ;;
    --remove-examples) REMOVE_EXAMPLES=1 ;;
    *) echo "unknown option: $a"; exit 1 ;;
  esac
done

VAULT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$VAULT"
TOOL="$VAULT/99 System/scripts/vault_tool.py"
OS="$(uname -s)"
step() { printf '\n\033[36m==> %s\033[0m\n' "$1"; }
ok()   { printf '    \033[32mOK\033[0m  %s\n' "$1"; }
warn() { printf '    \033[33m!!\033[0m  %s\n' "$1"; }
has()  { command -v "$1" >/dev/null 2>&1; }

# ------------------------------------------------------------------ 1. tools
step "Tools"
PY=""
for c in python3 python; do
  if has "$c" && "$c" -c 'import sys; sys.exit(0 if sys.version_info[0] == 3 else 1)' 2>/dev/null; then PY="$c"; break; fi
done
if [ -n "$PY" ]; then ok "Python 3 ($PY)"; else
  if [ "$SKIP_INSTALL" = 0 ] && [ "$OS" = "Darwin" ] && has brew; then brew install python3 && PY=python3 && ok "Python installed"
  else warn "Python 3 not found: the AI helper script needs it (macOS: brew install python3 · Debian/Ubuntu: sudo apt install python3)"; fi
fi

obsidian_installed() {
  if [ "$OS" = "Darwin" ]; then [ -d "/Applications/Obsidian.app" ] || [ -d "$HOME/Applications/Obsidian.app" ]
  else has obsidian || (has flatpak && flatpak info md.obsidian.Obsidian >/dev/null 2>&1) || [ -d "$HOME/snap/obsidian" ]; fi
}
if [ "$NO_OBSIDIAN" = 0 ]; then
  if obsidian_installed; then ok "Obsidian"; else
    if [ "$SKIP_INSTALL" = 0 ] && [ "$OS" = "Darwin" ] && has brew; then brew install --cask obsidian && ok "Obsidian installed"
    else warn "Obsidian not found: get it from https://obsidian.md"; fi
  fi
fi

# ------------------------------------------------------------------ 2. folders
step "Folders"
for d in "00 Inbox" "15 Tasks" "60 Resources/Attachments" "70 Analyses" "90 Archive"; do
  [ -d "$d" ] || { mkdir -p "$d"; ok "created: $d"; }
done
ok "Folder structure complete"

# ------------------------------------------------------------------ 3. git (optional)
if [ -d .git ] && has git; then
  step "Git"
  git config core.autocrlf false
  git config core.quotepath false
  ok "Line-ending conversion off for this repo"
fi

# ------------------------------------------------------------------ 4. examples / protected folders
if [ -n "$PY" ]; then
  if [ "$REMOVE_EXAMPLES" = 1 ]; then step "Example notes"; "$PY" "$TOOL" clean-examples --yes; fi
  if "$PY" -c 'import json,sys; sys.exit(0 if json.load(open("99 System/config.json")).get("protected") else 1)' 2>/dev/null; then
    step "Protected folders"; "$PY" "$TOOL" protected-baseline
  fi
fi

# ------------------------------------------------------------------ 5. Obsidian vault registration
if [ "$NO_OBSIDIAN" = 0 ] && [ -n "$PY" ]; then
  step "Obsidian"
  if [ "$OS" = "Darwin" ]; then CFG="$HOME/Library/Application Support/obsidian/obsidian.json"
  else
    CFG="$HOME/.config/obsidian/obsidian.json"
    [ -f "$HOME/.var/app/md.obsidian.Obsidian/config/obsidian/obsidian.json" ] && CFG="$HOME/.var/app/md.obsidian.Obsidian/config/obsidian/obsidian.json"
    [ -f "$HOME/snap/obsidian/current/.config/obsidian/obsidian.json" ] && CFG="$HOME/snap/obsidian/current/.config/obsidian/obsidian.json"
  fi
  if pgrep -xi obsidian >/dev/null 2>&1; then
    warn 'Obsidian is running, so registration was skipped. In Obsidian choose "Open folder as vault" and pick this folder.'
  else
    "$PY" - "$CFG" "$VAULT" <<'PY'
import json, os, sys, time, secrets, shutil
cfg, vault = sys.argv[1], sys.argv[2]
data = {}
if os.path.exists(cfg):
    with open(cfg, encoding="utf-8") as fh:
        data = json.load(fh)
vaults = data.setdefault("vaults", {})
if any(os.path.normpath(v.get("path", "")) == os.path.normpath(vault) for v in vaults.values()):
    print("    OK  Vault already registered in Obsidian")
else:
    if os.path.exists(cfg):
        shutil.copy(cfg, cfg + ".bak")
    os.makedirs(os.path.dirname(cfg), exist_ok=True)
    vaults[secrets.token_hex(8)] = {"path": vault, "ts": int(time.time() * 1000), "open": True}
    with open(cfg, "w", encoding="utf-8") as fh:
        json.dump(data, fh)
    print("    OK  Vault registered in Obsidian (previous settings saved as obsidian.json.bak)")
PY
  fi
  if obsidian_installed; then
    URI="obsidian://open?path=$("$PY" -c 'import sys, urllib.parse; print(urllib.parse.quote(sys.argv[1], safe=""))' "$VAULT")"
    if [ "$OS" = "Darwin" ]; then open "$URI"; elif has xdg-open; then xdg-open "$URI" >/dev/null 2>&1 || true; fi
    ok "Opening Obsidian. If it asks whether to trust this vault's plugins, choose trust (needed for the board)."
  fi
fi

# ------------------------------------------------------------------ 6. health
step "Health check"
if [ -n "$PY" ]; then "$PY" "$TOOL" lint | head -9; else warn "Python missing; health check skipped"; fi

step "Done"
cat <<EOF
    Vault: $VAULT
    - Start at Home.md, then read 99 System/Second Brain Guide.md
    - AI commands (/sb-*): open this folder in Claude Code (https://claude.com/claude-code) and type /sb-
    - Remove the example notes: bash setup.sh --remove-examples
EOF
