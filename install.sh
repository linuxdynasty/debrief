#!/usr/bin/env bash
# install.sh — Universal installer for @linuxdynasty/debrief across all supported
# harnesses (claude, codex, opencode, agy, muse, cursor).
#
# Works both from a local checkout:
#   ./install.sh [--all | --harness claude,codex,...] [--with-hooks] [--uninstall]
# And via curl-pipe-bash:
#   curl -fsSL https://raw.githubusercontent.com/linuxdynasty/debrief/main/install.sh | bash
#   curl -fsSL https://raw.githubusercontent.com/linuxdynasty/debrief/main/install.sh | bash -s -- --with-hooks
set -euo pipefail

REPO_URL="${DEBRIEF_REPO_URL:-https://github.com/linuxdynasty/debrief.git}"
DATA_DIR="${DEBRIEF_DATA_DIR:-${XDG_DATA_HOME:-${HOME}/.local/share}/${DEBRIEF_APP_NAME:-debrief}}"

# Resolve checkout root; if piped via curl (no local bin/debrief.mjs), clone/update into $DATA_DIR/repo.
ROOT=""
if [ -n "${BASH_SOURCE[0]:-}" ] && [ -f "${BASH_SOURCE[0]}" ]; then
	CAND="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
	if [ -f "${CAND}/bin/debrief.mjs" ] && [ -f "${CAND}/scripts/debrief.sh" ]; then
		ROOT="${CAND}"
	fi
fi

if [ -z "${ROOT}" ]; then
	ROOT="${DATA_DIR}/repo"
	mkdir -p "${DATA_DIR}"
	if [ -d "${ROOT}/.git" ]; then
		git -C "${ROOT}" pull --ff-only --quiet origin main || true
	else
		git clone --depth 1 --quiet "${REPO_URL}" "${ROOT}"
	fi
fi

if command -v node >/dev/null 2>&1; then
	NODE_MAJOR="$(node -p 'process.versions.node.split(".")[0]' 2>/dev/null || echo 0)"
	if [ "${NODE_MAJOR}" -ge 18 ]; then
		exec node "${ROOT}/bin/debrief.mjs" install "$@"
	fi
fi

# Pure-bash fallback when Node < 18 or absent: install /debrief skill symlinks + ~/.local/bin/debrief.
HARNESSES=(claude codex opencode agy muse cursor)
selected=()
uninstall=0

skills_dir_for() {
	case "$1" in
	claude) printf '%s\n' "${HOME}/.claude/skills" ;;
	codex) printf '%s\n' "${HOME}/.codex/skills" ;;
	opencode) printf '%s\n' "${XDG_CONFIG_HOME:-${HOME}/.config}/opencode/skill" ;;
	agy) printf '%s\n' "${HOME}/.gemini/config/skills" ;;
	muse) printf '%s\n' "${HOME}/.agents/skills" ;;
	cursor) printf '%s\n' "${HOME}/.cursor/skills" ;;
	*)
		printf 'debrief: unknown harness: %s\n' "$1" >&2
		return 1
		;;
	esac
}

while [ $# -gt 0 ]; do
	case "$1" in
	--all) selected=("${HARNESSES[@]}") ;;
	--uninstall) uninstall=1 ;;
	--harness)
		shift
		IFS=',' read -r -a selected <<<"${1:-}"
		;;
	--harness=*)
		IFS=',' read -r -a selected <<<"${1#--harness=}"
		;;
	--with-hooks)
		echo "debrief: --with-hooks requires Node.js >= 18 (install Node or run via npx @linuxdynasty/debrief)" >&2
		exit 1
		;;
	-h | --help)
		echo "Usage: ./install.sh [--all | --harness claude,codex,opencode,agy,muse,cursor] [--with-hooks] [--uninstall]"
		exit 0
		;;
	*)
		echo "debrief: unknown option: $1" >&2
		exit 2
		;;
	esac
	shift
done

if [ ${#selected[@]} -eq 0 ]; then
	selected=("${HARNESSES[@]}")
fi

for h in "${selected[@]}"; do
	dir="$(skills_dir_for "${h}")"
	if [ "${uninstall}" -eq 1 ]; then
		rm -rf "${dir}/debrief"
		echo "removed skill (${h}): ${dir}/debrief"
	else
		mkdir -p "${dir}"
		ln -sfn "${ROOT}/skills/debrief" "${dir}/debrief"
		echo "installed skill (${h}): ${dir}/debrief -> ${ROOT}/skills/debrief"
	fi
done

if [ "${uninstall}" -eq 0 ]; then
	mkdir -p "${HOME}/.local/bin"
	ln -sfn "${ROOT}/scripts/debrief.sh" "${HOME}/.local/bin/debrief"
	echo "linked CLI: ${HOME}/.local/bin/debrief -> ${ROOT}/scripts/debrief.sh"
fi
