#!/usr/bin/env bash
# Second Brain vault setup (macOS / Linux). Safe to run more than once.
#   bash setup.sh                    # full setup
#   bash setup.sh --remove-examples  # also delete the example notes
#   bash setup.sh --skip-install --no-obsidian
set -euo pipefail

#   bash setup.sh --remote https://github.com/<you>/<private-repo>.git   # back up to your own repo
SKIP_INSTALL=0; NO_OBSIDIAN=0; REMOVE_EXAMPLES=0; NO_GIT=0; REMOTE=""; GIT_NAME=""; GIT_EMAIL=""
while [ $# -gt 0 ]; do
  case "$1" in
    --skip-install) SKIP_INSTALL=1 ;;
    --no-obsidian) NO_OBSIDIAN=1 ;;
    --remove-examples) REMOVE_EXAMPLES=1 ;;
    --no-git) NO_GIT=1 ;;
    --remote) REMOTE="${2:?--remote needs a URL}"; shift ;;
    --git-name) GIT_NAME="${2:?--git-name needs a value}"; shift ;;
    --git-email) GIT_EMAIL="${2:?--git-email needs a value}"; shift ;;
    *) echo "unknown option: $1"; exit 1 ;;
  esac
  shift
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
for d in "Personal/00 Inbox" "Personal/15 Tasks" "Personal/60 Resources/Attachments" "Personal/70 Analyses" "Personal/90 Archive" \
         "Work/00 Inbox" "Work/10 Projects" "Work/20 Meetings" "Work/30 Organizations & People" "Work/40 Systems & APIs" \
         "Work/50 Tasks" "Work/60 Attachments" "Work/70 Analyses" "Work/90 Archive"; do
  [ -d "$d" ] || { mkdir -p "$d"; ok "created: $d"; }
done
ok "Folder structure complete"
# MCP server definition for Claude Code: point it at the Python found on this machine
if [ -n "$PY" ] && [ "$PY" != "python" ] && [ -f .mcp.json ] && grep -q '"command": "python"' .mcp.json; then
  sed -i.bak "s/\"command\": \"python\"/\"command\": \"$PY\"/" .mcp.json && rm -f .mcp.json.bak && ok "MCP server set to use $PY"
fi
if [ "$REMOVE_EXAMPLES" = 1 ] && [ -n "$PY" ]; then step "Example notes"; "$PY" "$TOOL" clean-examples --yes; fi

# ------------------------------------------------------------------ 3. git: version history for the Obsidian Git plugin
if [ "$NO_GIT" = 0 ]; then
  step "Git (version history)"
  if ! has git && [ "$SKIP_INSTALL" = 0 ] && [ "$OS" = "Darwin" ] && has brew; then brew install git; fi
  if ! has git; then
    warn "Git not found: version history is off. Install Git (https://git-scm.com) and run setup again, or disable the Git plugin in Obsidian."
  else
    if [ ! -d .git ]; then git init -b main -q; ok "Initialized a Git repository"; else ok "Git repository found"; fi
    git config core.autocrlf false
    git config core.quotepath false
    [ -n "$GIT_NAME" ] && git config user.name "$GIT_NAME"
    [ -n "$GIT_EMAIL" ] && git config user.email "$GIT_EMAIL"
    PLACEHOLDER=0
    git config user.name >/dev/null || { git config user.name "Second Brain"; PLACEHOLDER=1; }
    git config user.email >/dev/null || { git config user.email "second-brain@localhost"; PLACEHOLDER=1; }
    [ "$PLACEHOLDER" = 1 ] && warn 'No Git identity found; using "Second Brain <second-brain@localhost>" for this vault. Change it with --git-name/--git-email.'
    ORIGIN="$(git remote get-url origin 2>/dev/null || true)"
    if printf '%s' "$ORIGIN" | grep -Eq 'Doga0/obsidian-second-brain-template(\.git)?/?$'; then
      git remote remove origin; ORIGIN=""
      warn "This copy was cloned from the template repository; detached it. Use --remote <your-repo-url> to connect your own."
    fi
    if [ -n "$REMOTE" ]; then
      if [ -n "$ORIGIN" ]; then git remote set-url origin "$REMOTE"; else git remote add origin "$REMOTE"; fi
      ORIGIN="$REMOTE"; ok "Remote set: $REMOTE"
    fi
    if ! git rev-parse --verify HEAD >/dev/null 2>&1; then
      git add -A
      if git commit -q -m "Initial vault from obsidian-second-brain-template"; then ok "First commit created"; else warn 'First commit failed; run "git commit" manually'; fi
    fi
    PUSH_ON=false
    if [ -n "$ORIGIN" ]; then
      if git push -q -u origin "$(git rev-parse --abbrev-ref HEAD)" 2>/dev/null; then PUSH_ON=true; ok "Pushed to $ORIGIN; automatic sync enabled"
      else warn "Push to $ORIGIN failed (sign in or check the URL). Keeping local-only history; run setup again after fixing."; fi
    else ok "No remote: the Git plugin keeps local history only (auto-commit every 10 minutes)"; fi
    GCFG=".obsidian/plugins/obsidian-git/data.json"
    if [ -f "$GCFG" ] && [ -n "$PY" ]; then
      CHANGED="$("$PY" - "$GCFG" "$PUSH_ON" <<'PY'
import json, sys
p, on = sys.argv[1], sys.argv[2] == "true"
d = json.load(open(p, encoding="utf-8"))
if d.get("disablePush") != (not on) or d.get("autoPullOnBoot") != on:
    d["disablePush"] = not on
    d["autoPullOnBoot"] = on
    json.dump(d, open(p, "w", encoding="utf-8"), indent=2)
    print("yes")
PY
)"
      if [ "$CHANGED" = "yes" ]; then
        git add -- "$GCFG"
        if [ "$PUSH_ON" = true ]; then git commit -q -m "Git plugin: enable automatic sync" && git push -q 2>/dev/null || true
        else git commit -q -m "Git plugin: local history only" || true; fi
      fi
    fi
  fi
fi

# ------------------------------------------------------------------ 4. protected folders
if [ -n "$PY" ]; then
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
if [ -n "$PY" ]; then "$PY" "$TOOL" lint --no-write | head -9; else warn "Python missing; health check skipped"; fi

step "Done"
cat <<EOF
    Vault: $VAULT
    - Start at Home.md, then read 99 System/Second Brain Guide.md
    - AI commands (/sb-*): open this folder in Claude Code (https://claude.com/claude-code) and type /sb-
    - Remove the example notes: bash setup.sh --remove-examples
    - Back up to your own private repo: bash setup.sh --remote <repo-url>
EOF
