#!/usr/bin/env bash
# One-line installer for the Vicarius vRx MCP servers (vicarius-v2-mcp and vicarius-mcp).
#
#   curl -fsSL https://raw.githubusercontent.com/OrenTheRed/vicarius-mcp/main/install.sh | bash
#
# It asks its questions first (type b to go back one question), shows a review, and changes
# nothing until you submit. Then it installs git, curl and uv if they are missing, installs the
# servers with uv, writes the v2 tenants file, and connects the AI clients you picked.
# Works with bash 3.2 (the macOS default) and newer, on macOS and Linux (WSL included).

set -euo pipefail

REPO_URL="https://github.com/OrenTheRed/vicarius-mcp"
TENANTS_FILE="${VICARIUS_V2_TENANTS_FILE:-$HOME/.config/vicarius-v2-mcp/tenants.json}"
DRY_RUN=0

# Answers come from the terminal even when the script itself arrives on stdin (curl | bash).
# VICARIUS_INSTALL_INPUT replaces the terminal with a file, for tests.
INPUT="${VICARIUS_INSTALL_INPUT:-/dev/tty}"

usage() {
  cat <<'USAGE'
Vicarius vRx MCP installer

  curl -fsSL https://raw.githubusercontent.com/OrenTheRed/vicarius-mcp/main/install.sh | bash
  bash install.sh [--dry-run]

It asks its questions first (type b to go back one question), shows a review, and changes
nothing until you submit.

  --dry-run   ask the questions and print what would run, without changing anything
  --help      show this help
USAGE
}

# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

if [ -t 1 ] && [ -z "${NO_COLOR:-}" ]; then
  BOLD=$'\033[1m'; DIM=$'\033[2m'; RED=$'\033[31m'; GREEN=$'\033[32m'; YELLOW=$'\033[33m'; RESET=$'\033[0m'
else
  BOLD=""; DIM=""; RED=""; GREEN=""; YELLOW=""; RESET=""
fi

say()  { printf '%s\n' "$*"; }
info() { printf '%s==>%s %s\n' "$BOLD" "$RESET" "$*"; }
ok()   { printf '%s ok%s %s\n' "$GREEN" "$RESET" "$*"; }
warn() { printf '%swarn%s %s\n' "$YELLOW" "$RESET" "$*" >&2; }
die()  { printf '%serror%s %s\n' "$RED" "$RESET" "$*" >&2; exit 1; }
has()  { command -v "$1" >/dev/null 2>&1; }

# Run a command, or print it in a dry run. An API key in an argument is masked.
run() {
  if [ "$DRY_RUN" = 1 ]; then
    local shown="" arg
    for arg in "$@"; do
      case "$arg" in VICARIUS_API_KEY=*) arg="VICARIUS_API_KEY=***" ;; esac
      shown="$shown $(printf '%q' "$arg")"
    done
    printf '%s[dry-run]%s%s\n' "$DIM" "$RESET" "$shown"
  else
    "$@"
  fi
}

# Secrets reach Python in a private temporary file, never on a command line.
TMP_FILES=()
cleanup() { if [ ${#TMP_FILES[@]} -gt 0 ]; then rm -f "${TMP_FILES[@]}"; fi; }
trap cleanup EXIT
# private_tmp: make a file only you can read, named in TMP and removed when the script exits.
private_tmp() { TMP="$(umask 077; mktemp "${TMPDIR:-/tmp}/vicarius-install.XXXXXX")"; TMP_FILES+=("$TMP"); }

# ---------------------------------------------------------------------------
# Questions. Each ask helper sets ANSWER and returns 0, or returns 2 when the user typed b.
# ---------------------------------------------------------------------------

BACK=2
SKIP=3

read_line() {  # read_line [-s]: one line from the terminal into LINE; -s hides what is typed
  LINE=""
  if [ "${1:-}" = "-s" ] && [ "$INPUT" = "/dev/tty" ]; then
    IFS= read -r -s LINE <&3 || die "No answer: the installer needs a terminal."
    printf '\n'
  else
    IFS= read -r LINE <&3 || die "No answer: the installer needs a terminal."
  fi
}

# ask "Question" "default" [-s]
ask() {
  local question="$1" default="${2:-}" hidden="${3:-}"
  while :; do
    if [ -n "$default" ]; then
      printf '%s %s[%s]%s: ' "$question" "$DIM" "$default" "$RESET"
    else
      printf '%s: ' "$question"
    fi
    if [ -n "$hidden" ]; then read_line -s; else read_line; fi
    case "$LINE" in
      b|B|back) return $BACK ;;
      q|Q|quit) say "Cancelled. Nothing was changed."; exit 0 ;;
    esac
    ANSWER="${LINE:-$default}"
    [ -z "$ANSWER" ] || return 0
    say "  Please type an answer, b to go back, or q to quit."
  done
}

# choose "Question" "default number" "option 1" "option 2" ...; ANSWER is the chosen number
choose() {
  local question="$1" default="$2" i=1 opt
  shift 2
  say ""
  say "$BOLD$question$RESET"
  for opt in "$@"; do say "  $i) $opt"; i=$((i + 1)); done
  while :; do
    ask "Choose 1-$#" "$default" || return $BACK
    case "$ANSWER" in
      *[!0-9]*) ;;
      *) if [ "$ANSWER" -ge 1 ] && [ "$ANSWER" -le $# ]; then return 0; fi ;;
    esac
    say "  Type a number from 1 to $#, b to go back, or q to quit."
  done
}

# yes_no "Question" "y|n"; ANSWER is y or n
yes_no() {
  while :; do
    ask "$1 (y/n)" "$2" || return $BACK
    case "$ANSWER" in
      y|Y|yes) ANSWER=y; return 0 ;;
      n|N|no) ANSWER=n; return 0 ;;
    esac
    say "  Type y or n, b to go back, or q to quit."
  done
}

# ---------------------------------------------------------------------------
# What the user chose
# ---------------------------------------------------------------------------

WANT_V2=1
WANT_V1=0
T_NAMES=()   # v2 tenants as parallel arrays: bash 3.2 has no associative arrays
T_KEYS=()
T_HOSTS=()
TENANTS_MODE="new"        # new | merge | replace | keep
V1_DASHBOARD=""
V1_KEY=""
READ_ONLY=n
TOOLSETS="all"
CLIENT_CLAUDE_CODE=""    # y | n, empty until asked: the first default is whether it is installed
CLIENT_CODEX=""
CLIENT_CLAUDE_DESKTOP=""
VERSION_CHOICE="release"  # release | main

# ---------------------------------------------------------------------------
# System detection
# ---------------------------------------------------------------------------

OS=""; DISTRO=""; PKG=""

detect_system() {
  case "$(uname -s)" in
    Darwin) OS=macos; DISTRO="macOS $(sw_vers -productVersion 2>/dev/null || true)" ;;
    Linux)
      OS=linux
      local id="" like="" name=""
      if [ -r /etc/os-release ]; then
        # shellcheck disable=SC1091
        id="$(. /etc/os-release && printf '%s' "${ID:-}")"
        # shellcheck disable=SC1091
        like="$(. /etc/os-release && printf '%s' "${ID_LIKE:-}")"
        # shellcheck disable=SC1091
        name="$(. /etc/os-release && printf '%s' "${PRETTY_NAME:-}")"
      fi
      DISTRO="${name:-Linux}"
      case " $id $like " in
        *" debian "*|*" ubuntu "*) PKG=apt ;;
        *" fedora "*|*" rhel "*|*" centos "*) if has dnf; then PKG=dnf; else PKG=yum; fi ;;
        *" arch "*) PKG=pacman ;;
        *" alpine "*) PKG=apk ;;
        *" suse "*|*" opensuse "*) PKG=zypper ;;
        *) PKG="" ;;
      esac
      if grep -qi microsoft /proc/version 2>/dev/null; then DISTRO="$DISTRO (WSL)"; fi
      ;;
    MINGW*|MSYS*|CYGWIN*)
      die "Native Windows is not supported by this script. Run it inside WSL, or follow the Windows steps in the README." ;;
    *) die "Unsupported system: $(uname -s)." ;;
  esac
}

claude_desktop_config() {
  case "$OS" in
    macos) printf '%s' "$HOME/Library/Application Support/Claude/claude_desktop_config.json" ;;
    linux) printf '%s' "${XDG_CONFIG_HOME:-$HOME/.config}/Claude/claude_desktop_config.json" ;;
  esac
}

# ---------------------------------------------------------------------------
# Steps. Each returns 0 (next), 2 (back) or 3 (does not apply, skip it).
# ---------------------------------------------------------------------------

step_servers() {
  local def=1
  if [ "$WANT_V2" = 1 ] && [ "$WANT_V1" = 1 ]; then def=3; elif [ "$WANT_V1" = 1 ]; then def=2; fi
  choose "Which servers do you want?" "$def" \
    "v2: vRx v2 Customer API (vicarius.cloud), one or many tenants. Most people want this." \
    "v1: vRx External Data API (a <name>.vicarius.cloud dashboard)" \
    "Both" || return $BACK
  case "$ANSWER" in
    1) WANT_V2=1; WANT_V1=0 ;;
    2) WANT_V2=0; WANT_V1=1 ;;
    3) WANT_V2=1; WANT_V1=1 ;;
  esac
}

step_existing_tenants() {
  if [ "$WANT_V2" != 1 ] || [ ! -f "$TENANTS_FILE" ]; then TENANTS_MODE=new; return $SKIP; fi
  local count
  count="$(grep -c '"api_key"' "$TENANTS_FILE" || true)"
  choose "You already have a tenants file ($TENANTS_FILE, $count tenant(s)). What should happen to it?" 1 \
    "Keep it and add new tenants to it" \
    "Keep it as it is (add no tenants)" \
    "Replace it with the tenants you enter now" || return $BACK
  case "$ANSWER" in
    1) TENANTS_MODE=merge ;;
    2) TENANTS_MODE=keep ;;
    3) TENANTS_MODE=replace ;;
  esac
}

# Check a v2 API key with one read-only call. Returns 0 when the API accepts it.
# The key goes to curl in a private header file, so it never shows in the process list.
check_v2_key() {
  local code header
  private_tmp; header="$TMP"
  printf 'X-Api-Key: %s\n' "$2" >"$header"
  code="$(curl -s -o /dev/null -w '%{http_code}' --max-time 15 -H "@$header" "https://$1/api/me")" || code=""
  rm -f "$header"
  [ "$code" = 200 ]
}

# Ask for one tenant, field by field. b goes back one field, or out of the tenant at the first.
add_tenant() {
  local field=1 name="" key="" host="vicarius.cloud"
  while :; do
    case $field in
      0) return $BACK ;;
      1) say ""; say "${BOLD}New tenant${RESET} ${DIM}(b goes back one field)${RESET}"
         if ask "Tenant name, any short label such as acme" "$name"; then
           case "$ANSWER" in
             *[!A-Za-z0-9_.-]*) say "  Use letters, digits, dot, dash or underscore only."; continue ;;
           esac
           name="$ANSWER"; field=2
         else field=0; fi ;;
      2) if ask "API key for $name (input is hidden)" "" -s; then key="$ANSWER"; field=3; else field=1; fi ;;
      3) if ask "API host" "$host"; then host="${ANSWER#https://}"; host="${host%%/*}"; field=4; else field=2; fi ;;
      4) if [ "$DRY_RUN" = 0 ] && has curl; then
           printf 'Checking the key... '
           if check_v2_key "$host" "$key"; then
             say "${GREEN}it works${RESET}"
           else
             say "${YELLOW}the API did not accept it${RESET}"
             if ! yes_no "Keep this key anyway?" n || [ "$ANSWER" != y ]; then field=2; continue; fi
           fi
         fi
         T_NAMES+=("$name"); T_KEYS+=("$key"); T_HOSTS+=("$host")
         return 0 ;;
    esac
  done
}

remove_last_tenant() {
  local n=$((${#T_NAMES[@]} - 1)) i=0 names=() keys=() hosts=()
  while [ $i -lt $n ]; do names+=("${T_NAMES[$i]}"); keys+=("${T_KEYS[$i]}"); hosts+=("${T_HOSTS[$i]}"); i=$((i + 1)); done
  T_NAMES=("${names[@]+"${names[@]}"}"); T_KEYS=("${keys[@]+"${keys[@]}"}"); T_HOSTS=("${hosts[@]+"${hosts[@]}"}")
}

step_v2_tenants() {
  if [ "$WANT_V2" != 1 ] || [ "$TENANTS_MODE" = keep ]; then return $SKIP; fi
  while :; do
    say ""
    say "${BOLD}v2 tenants${RESET}: each is a name you choose plus one Vicarius API key (vRx: Account Settings > API Tokens)."
    if [ ${#T_NAMES[@]} -eq 0 ]; then
      say "  No tenants yet."
      add_tenant || return $BACK
      continue
    fi
    local i=0
    while [ $i -lt ${#T_NAMES[@]} ]; do say "  - ${T_NAMES[$i]} (${T_HOSTS[$i]})"; i=$((i + 1)); done
    choose "Tenants" 3 "Add another tenant" "Remove the last tenant" "Continue" || return $BACK
    case "$ANSWER" in
      1) add_tenant || true ;;   # b inside the new tenant returns to this list
      2) remove_last_tenant ;;
      3) return 0 ;;
    esac
  done
}

step_v1() {
  [ "$WANT_V1" = 1 ] || return $SKIP
  local field=1
  while :; do
    case $field in
      0) return $BACK ;;
      1) say ""; say "${BOLD}v1 dashboard${RESET} ${DIM}(b goes back one field)${RESET}"
         if ask "Dashboard name, the part before .vicarius.cloud" "$V1_DASHBOARD"; then
           V1_DASHBOARD="${ANSWER#https://}"; V1_DASHBOARD="${V1_DASHBOARD%%.*}"; field=2
         else field=0; fi ;;
      2) if ask "API key for $V1_DASHBOARD (dashboard: Settings > API > Create Integration; input is hidden)" "" -s; then
           V1_KEY="$ANSWER"; return 0
         else field=1; fi ;;
    esac
  done
}

step_read_only() {
  say ""
  say "${BOLD}Read-only mode${RESET} gives the AI the read tools only: it can look, but not change anything."
  yes_no "Use read-only mode?" "$READ_ONLY" || return $BACK
  READ_ONLY="$ANSWER"
}

step_toolsets() {
  [ "$WANT_V2" = 1 ] || return $SKIP
  local def=1
  [ "$TOOLSETS" != core ] || def=2
  choose "How many v2 tools should the AI see?" "$def" \
    "All tools (best for Claude, GPT and other large hosted models)" \
    "core: a small set for the usual questions (best for local models with a small context)" || return $BACK
  if [ "$ANSWER" = 2 ]; then TOOLSETS=core; else TOOLSETS=all; fi
}

step_clients() {
  local def
  found=""
  if has claude; then found="$found Claude-Code"; fi
  if has codex; then found="$found Codex"; fi
  if [ -d "$(dirname "$(claude_desktop_config)")" ]; then found="$found Claude-Desktop"; fi
  say ""
  say "${BOLD}AI clients${RESET} to connect ${DIM}(found on this computer:${found:- none})${RESET}"
  def="${CLIENT_CLAUDE_CODE:-$(found_default Claude-Code)}"
  yes_no "Connect Claude Code?" "$def" || return $BACK
  CLIENT_CLAUDE_CODE="$ANSWER"
  def="${CLIENT_CODEX:-$(found_default Codex)}"
  yes_no "Connect Codex?" "$def" || return $BACK
  CLIENT_CODEX="$ANSWER"
  def="${CLIENT_CLAUDE_DESKTOP:-$(found_default Claude-Desktop)}"
  yes_no "Connect Claude Desktop?" "$def" || return $BACK
  CLIENT_CLAUDE_DESKTOP="$ANSWER"
}

found_default() { case "$found" in *"$1"*) echo y ;; *) echo n ;; esac; }

step_version() {
  local def=1
  [ "$VERSION_CHOICE" != main ] || def=2
  choose "Which version?" "$def" "The latest release (recommended)" "The newest code on main" || return $BACK
  if [ "$ANSWER" = 2 ]; then VERSION_CHOICE=main; else VERSION_CHOICE=release; fi
}

step_review() {
  local servers="" tenant_list="" clients=""
  [ "$WANT_V2" != 1 ] || servers="v2"
  [ "$WANT_V1" != 1 ] || servers="${servers:+$servers and }v1"
  [ ${#T_NAMES[@]} -eq 0 ] || tenant_list="${T_NAMES[*]}"
  [ "$CLIENT_CLAUDE_CODE" != y ] || clients="${clients:+$clients, }Claude Code"
  [ "$CLIENT_CODEX" != y ] || clients="${clients:+$clients, }Codex"
  [ "$CLIENT_CLAUDE_DESKTOP" != y ] || clients="${clients:+$clients, }Claude Desktop"
  say ""
  say "${BOLD}Review${RESET}"
  say "  System:       $DISTRO"
  say "  Servers:      $servers"
  if [ "$WANT_V2" = 1 ]; then
    case "$TENANTS_MODE" in
      keep) say "  v2 tenants:   keep $TENANTS_FILE as it is" ;;
      merge) say "  v2 tenants:   add ${tenant_list:-none} to $TENANTS_FILE" ;;
      *) say "  v2 tenants:   ${tenant_list:-none}, written to $TENANTS_FILE" ;;
    esac
    say "  v2 tools:     $TOOLSETS"
  fi
  [ "$WANT_V1" != 1 ] || say "  v1 dashboard: $V1_DASHBOARD.vicarius.cloud (API key hidden)"
  say "  Read-only:    $READ_ONLY"
  say "  Connect:      ${clients:-nothing}"
  say "  Version:      $VERSION_CHOICE"
  choose "Ready?" 1 "Submit and install" "Go back and change something" "Quit without changes" || return $BACK
  case "$ANSWER" in
    1) return 0 ;;
    2) return $BACK ;;
    3) say "Cancelled. Nothing was changed."; exit 0 ;;
  esac
}

STEPS=(step_servers step_existing_tenants step_v2_tenants step_v1 step_read_only step_toolsets step_clients step_version step_review)

run_wizard() {
  local i=0 dir=1 rc
  while [ $i -lt ${#STEPS[@]} ]; do
    if [ $i -lt 0 ]; then say "  This is the first question."; i=0; dir=1; fi
    rc=0; "${STEPS[$i]}" || rc=$?
    case $rc in
      0) dir=1; i=$((i + 1)) ;;
      2) dir=-1; i=$((i - 1)) ;;
      3) i=$((i + dir)) ;;
      *) die "Unexpected step result $rc." ;;
    esac
  done
}

# ---------------------------------------------------------------------------
# Install
# ---------------------------------------------------------------------------

install_system_packages() {
  local need=""
  has git || need="$need git"
  has curl || need="$need curl"
  has tar || need="$need tar"      # the uv installer unpacks a .tar.gz
  has gzip || need="$need gzip"
  if [ -z "$need" ]; then ok "git, curl, tar and gzip are already installed"; return 0; fi
  info "Installing:$need"
  if [ "$OS" = macos ]; then
    if has brew; then
      # shellcheck disable=SC2086
      run brew install $need
    else
      run xcode-select --install
      [ "$DRY_RUN" = 1 ] || die "macOS is installing its command line tools, which include git. When that finishes, run the installer again."
    fi
    return 0
  fi
  local sudo=""
  if [ "$(id -u)" != 0 ]; then
    has sudo || die "Installing$need needs root, and sudo is not available. Install$need yourself, then run the installer again."
    sudo="sudo"
  fi
  # shellcheck disable=SC2086
  case "$PKG" in
    apt) run $sudo apt-get update -qq
         run $sudo env DEBIAN_FRONTEND=noninteractive apt-get install -y -qq $need ca-certificates ;;
    dnf) run $sudo dnf install -y -q $need ;;
    yum) run $sudo yum install -y -q $need ;;
    pacman) run $sudo pacman -Sy --noconfirm --needed $need ;;
    apk) run $sudo apk add --no-cache $need ca-certificates ;;
    zypper) run $sudo zypper --non-interactive install $need ;;
    *) die "Unknown Linux package manager. Install$need yourself, then run the installer again." ;;
  esac
}

UV="uv"
install_uv() {
  if has uv; then ok "uv is already installed ($(uv --version))"; return 0; fi
  info "Installing uv"
  if [ "$DRY_RUN" = 1 ]; then
    run sh -c "curl -LsSf https://astral.sh/uv/install.sh | sh"
    return 0
  fi
  curl -LsSf https://astral.sh/uv/install.sh | sh
  local bin
  for bin in "$HOME/.local/bin/uv" "$HOME/.cargo/bin/uv"; do
    if [ -x "$bin" ]; then UV="$bin"; PATH="$(dirname "$bin"):$PATH"; export PATH; return 0; fi
  done
  die "uv was installed but cannot be found. Open a new terminal and run the installer again."
}

GIT_REF=""
resolve_version() {
  GIT_REF=""
  [ "$VERSION_CHOICE" = release ] || return 0
  if [ "$DRY_RUN" = 1 ] && ! has git; then GIT_REF="@<latest-release>"; return 0; fi
  local tag
  tag="$(git ls-remote --tags --refs --sort=-v:refname "$REPO_URL" 'v*' | sed -n '1s#.*refs/tags/##p')" || tag=""
  if [ -n "$tag" ]; then GIT_REF="@$tag"; else warn "Could not find a release tag. Installing from main."; fi
}

BIN_DIR=""
install_servers() {
  local s
  for s in $(servers_chosen); do
    info "Installing the $s server${GIT_REF:+ (${GIT_REF#@})}"
    run "$UV" tool install --force "git+$REPO_URL$GIT_REF#subdirectory=$s"
  done
  if [ "$DRY_RUN" = 1 ]; then BIN_DIR="<uv tool bin dir>"; return 0; fi
  BIN_DIR="$("$UV" tool dir --bin)"
  case ":$PATH:" in
    *":$BIN_DIR:"*) ;;
    *) PATH="$BIN_DIR:$PATH"; export PATH
       "$UV" tool update-shell || warn "Could not add $BIN_DIR to your shell's PATH. Run: uv tool update-shell" ;;
  esac
}

# Python from uv, for JSON edits that keep the rest of an existing file.
py() { "$UV" run --no-project --quiet python - "$@"; }

# Copy a file before changing it. Prints where the copy went, or nothing for a new file.
backup() { if [ -f "$1" ]; then cp -p "$1" "$1.bak"; printf '%s' "$1.bak"; fi; }

write_tenants() {
  if [ "$WANT_V2" != 1 ] || [ "$TENANTS_MODE" = keep ] || [ ${#T_NAMES[@]} -eq 0 ]; then return 0; fi
  info "Writing $TENANTS_FILE"
  if [ "$DRY_RUN" = 1 ]; then
    say "${DIM}[dry-run]${RESET} write ${T_NAMES[*]} to $TENANTS_FILE ($TENANTS_MODE, readable by you only)"
    return 0
  fi
  mkdir -p "$(dirname "$TENANTS_FILE")"
  local saved rows i=0
  saved="$(backup "$TENANTS_FILE")"
  private_tmp; rows="$TMP"
  while [ $i -lt ${#T_NAMES[@]} ]; do
    printf '%s\t%s\t%s\n' "${T_NAMES[$i]}" "${T_HOSTS[$i]}" "${T_KEYS[$i]}" >>"$rows"
    i=$((i + 1))
  done
  py "$TENANTS_FILE" "$TENANTS_MODE" "$rows" <<'PY'
import json, os, sys
path, mode, rows_path = sys.argv[1:4]
data = {}
if mode == "merge" and os.path.exists(path):
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
with open(rows_path, encoding="utf-8") as rows:
    for line in rows:
        name, host, key = line.rstrip("\n").split("\t", 2)
        entry = {"api_key": key}
        if host != "vicarius.cloud":
            entry["host"] = host
        data[name] = entry
tmp = path + ".tmp"
fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
with os.fdopen(fd, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2)
    f.write("\n")
os.chmod(tmp, 0o600)
os.replace(tmp, path)
PY
  ok "Tenants file written, readable by you only${saved:+. The old one is $saved}"
}

# The environment of each server, as NAME=value lines.
server_env() {
  if [ "$1" = v2 ]; then
    [ "$READ_ONLY" != y ] || echo "VICARIUS_READ_ONLY=true"
    [ "$TOOLSETS" != core ] || echo "VICARIUS_V2_TOOLSETS=core"
  else
    echo "VICARIUS_DASHBOARD=$V1_DASHBOARD"
    echo "VICARIUS_API_KEY=$V1_KEY"
    [ "$READ_ONLY" != y ] || echo "VICARIUS_READ_ONLY=true"
  fi
}

servers_chosen() { [ "$WANT_V2" != 1 ] || echo v2; [ "$WANT_V1" != 1 ] || echo v1; }
server_name() { if [ "$1" = v2 ]; then echo vicarius-v2; else echo vicarius; fi; }
server_cmd() { if [ "$1" = v2 ]; then echo vicarius-v2-mcp; else echo vicarius-mcp; fi; }

# connect_cli <client command> <env flag> <remove args...>: one entry per server, replacing an old one
connect_cli() {
  local client="$1" flag="$2" s name line args
  for s in $(servers_chosen); do
    name="$(server_name "$s")"
    if [ "$client" = claude ]; then info "Connecting $name to Claude Code"; else info "Connecting $name to Codex"; fi
    args=()
    while IFS= read -r line; do [ -z "$line" ] || args+=("$flag" "$line"); done <<ENV
$(server_env "$s")
ENV
    if [ "$client" = claude ]; then
      if claude mcp get "$name" >/dev/null 2>&1; then run claude mcp remove --scope user "$name"; fi
      run claude mcp add --scope user "$name" "${args[@]+"${args[@]}"}" -- "$(server_cmd "$s")"
    else
      if codex mcp get "$name" >/dev/null 2>&1; then run codex mcp remove "$name"; fi
      run codex mcp add "$name" "${args[@]+"${args[@]}"}" -- "$(server_cmd "$s")"
    fi
  done
}

connect_clients() {
  if [ "$CLIENT_CLAUDE_CODE" = y ]; then
    if has claude || [ "$DRY_RUN" = 1 ]; then connect_cli claude -e; else warn "Claude Code (claude) is not installed. Skipped it."; fi
  fi
  if [ "$CLIENT_CODEX" = y ]; then
    if has codex || [ "$DRY_RUN" = 1 ]; then connect_cli codex --env; else warn "Codex (codex) is not installed. Skipped it."; fi
  fi
  [ "$CLIENT_CLAUDE_DESKTOP" != y ] || connect_claude_desktop
}

connect_claude_desktop() {
  local cfg saved rows s line
  cfg="$(claude_desktop_config)"
  info "Connecting to Claude Desktop ($cfg)"
  if [ "$DRY_RUN" = 1 ]; then
    say "${DIM}[dry-run]${RESET} add $(servers_chosen | tr '\n' ' ')to $cfg, with the full path to each server"
    return 0
  fi
  mkdir -p "$(dirname "$cfg")"
  saved="$(backup "$cfg")"
  private_tmp; rows="$TMP"
  # Claude Desktop does not read your shell's PATH, so each server gets its full path.
  for s in $(servers_chosen); do
    printf 'server\t%s\t%s\n' "$(server_name "$s")" "$BIN_DIR/$(server_cmd "$s")" >>"$rows"
    while IFS= read -r line; do
      [ -z "$line" ] || printf 'env\t%s\t%s\n' "${line%%=*}" "${line#*=}" >>"$rows"
    done <<ENV
$(server_env "$s")
ENV
  done
  py "$cfg" "$rows" <<'PY'
import json, os, sys
path, rows_path = sys.argv[1:3]
data = {}
if os.path.exists(path) and os.path.getsize(path):
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
servers = data.setdefault("mcpServers", {})
current = None
with open(rows_path, encoding="utf-8") as rows:
    for line in rows:
        kind, a, b = line.rstrip("\n").split("\t", 2)
        if kind == "server":
            current = servers[a] = {"command": b}
        else:
            current.setdefault("env", {})[a] = b
tmp = path + ".tmp"
fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
with os.fdopen(fd, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2)
    f.write("\n")
os.chmod(tmp, 0o600)
os.replace(tmp, path)
PY
  ok "Claude Desktop config updated${saved:+ (the old one is $saved)}. Restart Claude Desktop to load the servers."
}

verify() {
  [ "$DRY_RUN" = 0 ] || return 0
  local s cmd
  for s in $(servers_chosen); do
    cmd="$BIN_DIR/$(server_cmd "$s")"
    if "$cmd" --version >/dev/null 2>&1; then
      ok "$("$cmd" --version | head -n 1) is installed"
    else
      warn "$(server_cmd "$s") did not start. To see why, run: $cmd --version"
    fi
  done
}

install_all() {
  say ""
  info "Installing on $DISTRO"
  install_system_packages
  install_uv
  resolve_version
  install_servers
  write_tenants
  connect_clients
  verify
  say ""
  if [ "$DRY_RUN" = 1 ]; then
    ok "Dry run finished. Nothing was changed."
  else
    ok "Done. Open a new terminal, then ask your AI: \"List my Vicarius tenants.\""
  fi
}

main() {
  while [ $# -gt 0 ]; do
    case "$1" in
      --dry-run) DRY_RUN=1 ;;
      -h|--help) usage; exit 0 ;;
      *) die "Unknown option: $1 (try --help)" ;;
    esac
    shift
  done
  ( exec 3<"$INPUT" ) 2>/dev/null || die "The installer needs a terminal to ask its questions. Run it from a terminal window."
  exec 3<"$INPUT"
  detect_system
  say ""
  say "${BOLD}Vicarius vRx MCP installer${RESET}"
  say "System: $DISTRO. Type ${BOLD}b${RESET} to go back one question, ${BOLD}q${RESET} to quit. Nothing changes until you submit."
  [ "$DRY_RUN" = 0 ] || say "${YELLOW}Dry run: nothing will be changed.${RESET}"
  run_wizard
  install_all
}

main "$@"
