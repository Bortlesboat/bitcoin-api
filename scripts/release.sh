#!/usr/bin/env bash
# release.sh — Version tagging & safe rollback for Satoshi API
#
# Usage:
#   bash scripts/release.sh tag              # tag current HEAD as vX.Y.Z (reads pyproject.toml)
#   bash scripts/release.sh tag v0.3.4       # tag with explicit version
#   bash scripts/release.sh list             # list all tagged releases with dates
#   bash scripts/release.sh diff v0.3.2      # show what changed since v0.3.2
#   bash scripts/release.sh revert v0.3.2    # revert to v0.3.2 (creates backup branch first)
#   bash scripts/release.sh status           # show current version vs latest tag
set -uo pipefail

API_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$API_DIR"

GREEN='\033[0;32m'; RED='\033[0;31m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'

get_version() {
    grep -m1 'version' pyproject.toml | sed 's/.*"\(.*\)".*/\1/'
}

cmd_tag() {
    local version="${1:-v$(get_version)}"
    # Ensure v prefix
    [[ "$version" != v* ]] && version="v$version"

    # Check for uncommitted changes
    if [[ $(git status --porcelain | wc -l | tr -d ' ') -gt 0 ]]; then
        echo -e "${RED}ERROR: Uncommitted changes. Commit first.${NC}"
        git status --short
        exit 1
    fi

    # Check if tag already exists
    if git rev-parse "$version" >/dev/null 2>&1; then
        echo -e "${YELLOW}Tag $version already exists.${NC}"
        echo "  Commit: $(git rev-parse --short "$version")"
        echo "  Date:   $(git log -1 --format='%ci' "$version")"
        exit 0
    fi

    # Run tests before tagging
    echo -e "${CYAN}Running tests before tagging...${NC}"
    if ! PYTHONPATH=src python -m pytest tests/ -q --tb=short \
        --ignore=tests/test_e2e.py --ignore=tests/locustfile.py; then
        echo -e "${RED}Tests failed — refusing to tag.${NC}"
        exit 1
    fi

    # Create annotated tag
    local msg="Release $version — $(date '+%Y-%m-%d')"
    # Pull release notes from CHANGELOG if available
    local changelog_entry
    changelog_entry=$(sed -n "/^## $version\|^## \[${version#v}\]/,/^## /p" CHANGELOG.md 2>/dev/null | sed '1d;$d' | head -10)
    if [[ -n "$changelog_entry" ]]; then
        msg="$msg

$changelog_entry"
    fi

    git tag -a "$version" -m "$msg"
    echo ""
    echo -e "${GREEN}${BOLD}Tagged $version${NC}"
    echo "  Commit: $(git rev-parse --short HEAD)"
    echo "  Date:   $(date '+%Y-%m-%d %H:%M:%S')"
    echo ""
    echo "  To push tag:  git push origin $version"
    echo "  To push all:  git push origin --tags"
}

cmd_list() {
    echo -e "${BOLD}=== Tagged Releases ===${NC}"
    echo ""

    local tags
    tags=$(git tag -l 'v*' --sort=-version:refname 2>/dev/null)

    if [[ -z "$tags" ]]; then
        echo -e "${YELLOW}No tags found. Create one: bash scripts/release.sh tag${NC}"
        exit 0
    fi

    local current_version="v$(get_version)"
    local head_sha
    head_sha=$(git rev-parse --short HEAD)

    printf "  %-12s %-10s %-20s %s\n" "VERSION" "COMMIT" "DATE" "STATUS"
    printf "  %-12s %-10s %-20s %s\n" "-------" "------" "----" "------"

    while read -r tag; do
        local sha date status=""
        sha=$(git rev-parse --short "$tag" 2>/dev/null)
        date=$(git log -1 --format='%ci' "$tag" 2>/dev/null | cut -d' ' -f1)

        if [[ "$sha" == "$head_sha" ]]; then
            status="<-- HEAD"
        fi
        if [[ "$tag" == "$current_version" ]]; then
            status="${status:+$status, }pyproject.toml"
        fi

        printf "  %-12s %-10s %-20s %s\n" "$tag" "$sha" "$date" "$status"
    done <<< "$tags"

    echo ""
    local commits_ahead
    local latest_tag
    latest_tag=$(echo "$tags" | head -1)
    commits_ahead=$(git rev-list "$latest_tag"..HEAD --count 2>/dev/null || echo "0")
    if [[ "$commits_ahead" -gt 0 ]]; then
        echo -e "  ${YELLOW}HEAD is $commits_ahead commit(s) ahead of $latest_tag${NC}"
    fi
}

cmd_diff() {
    local version="$1"
    [[ "$version" != v* ]] && version="v$version"

    if ! git rev-parse "$version" >/dev/null 2>&1; then
        echo -e "${RED}Tag $version not found.${NC}"
        cmd_list
        exit 1
    fi

    echo -e "${BOLD}=== Changes since $version ===${NC}"
    echo ""

    # Commit log
    echo -e "${CYAN}Commits:${NC}"
    git log --oneline "$version"..HEAD 2>/dev/null || echo "  (none)"
    echo ""

    # File-level summary
    echo -e "${CYAN}Files changed:${NC}"
    git diff --stat "$version"..HEAD 2>/dev/null || echo "  (none)"
}

cmd_revert() {
    local version="$1"
    [[ "$version" != v* ]] && version="v$version"

    if ! git rev-parse "$version" >/dev/null 2>&1; then
        echo -e "${RED}Tag $version not found.${NC}"
        cmd_list
        exit 1
    fi

    # Safety: check for uncommitted changes
    if [[ $(git status --porcelain | wc -l | tr -d ' ') -gt 0 ]]; then
        echo -e "${RED}ERROR: Uncommitted changes. Commit or stash first.${NC}"
        git status --short
        exit 1
    fi

    local current_branch
    current_branch=$(git branch --show-current 2>/dev/null || echo "detached")
    local backup_branch="backup/pre-revert-$(date '+%Y%m%d-%H%M%S')"
    local head_sha
    head_sha=$(git rev-parse --short HEAD)

    echo -e "${BOLD}=== Revert Plan ===${NC}"
    echo ""
    echo "  Current HEAD:    $head_sha ($current_branch)"
    echo "  Target version:  $version ($(git rev-parse --short "$version"))"
    echo "  Backup branch:   $backup_branch"
    echo ""

    # Show what will change
    echo -e "${CYAN}Files that will change:${NC}"
    git diff --stat "$version"..HEAD 2>/dev/null
    echo ""

    # Confirm
    echo -e "${YELLOW}${BOLD}This will:${NC}"
    echo "  1. Create backup branch '$backup_branch' at current HEAD"
    echo "  2. Create a new revert commit on '$current_branch'"
    echo "  3. Restart the API with the reverted code"
    echo ""
    read -rp "Proceed? [y/N] " confirm
    if [[ "$confirm" != "y" && "$confirm" != "Y" ]]; then
        echo "Aborted."
        exit 0
    fi

    # Create backup branch
    git branch "$backup_branch" HEAD
    echo -e "${GREEN}Backup branch created: $backup_branch${NC}"

    # Revert via a new commit (safe, preserves history)
    # Use git revert for each commit between version and HEAD, or use diff-apply
    # Simplest safe approach: checkout the old version's tree onto current branch
    git checkout "$version" -- . 2>/dev/null
    git commit -m "revert: roll back to $version

Reverted all files to match $version.
Backup branch: $backup_branch
Triggered by: bash scripts/release.sh revert $version"

    echo ""
    echo -e "${GREEN}${BOLD}Reverted to $version${NC}"
    echo ""
    echo "  To restore:  git merge $backup_branch"
    echo "  To restart:  bash scripts/deploy-api.sh"
    echo "  To verify:   bash scripts/diagnose.sh"
    echo ""

    # Ask about restart
    read -rp "Restart API now? [Y/n] " restart
    if [[ "$restart" != "n" && "$restart" != "N" ]]; then
        echo ""
        bash "$API_DIR/scripts/deploy-api.sh"
    fi
}

cmd_status() {
    local version
    version="v$(get_version)"
    local head_sha
    head_sha=$(git rev-parse --short HEAD)
    local latest_tag
    latest_tag=$(git tag -l 'v*' --sort=-version:refname 2>/dev/null | head -1)

    echo -e "${BOLD}=== Version Status ===${NC}"
    echo ""
    echo "  pyproject.toml:  $version"
    echo "  HEAD:            $head_sha"
    echo "  Latest tag:      ${latest_tag:-none}"

    if [[ -n "$latest_tag" ]]; then
        local behind ahead
        behind=$(git rev-list HEAD.."$latest_tag" --count 2>/dev/null || echo "0")
        ahead=$(git rev-list "$latest_tag"..HEAD --count 2>/dev/null || echo "0")
        echo "  HEAD vs tag:     $ahead ahead, $behind behind"
    fi

    local dirty
    dirty=$(git status --porcelain 2>/dev/null | wc -l | tr -d ' ')
    if [[ "$dirty" -gt 0 ]]; then
        echo -e "  Working tree:    ${YELLOW}$dirty uncommitted change(s)${NC}"
    else
        echo -e "  Working tree:    ${GREEN}clean${NC}"
    fi
}

# =====================================================================
# Main dispatch
# =====================================================================
case "${1:-help}" in
    tag)    cmd_tag "${2:-}" ;;
    list)   cmd_list ;;
    diff)
        if [[ -z "${2:-}" ]]; then echo "Usage: release.sh diff <version>"; exit 1; fi
        cmd_diff "$2" ;;
    revert)
        if [[ -z "${2:-}" ]]; then echo "Usage: release.sh revert <version>"; exit 1; fi
        cmd_revert "$2" ;;
    status) cmd_status ;;
    help|*)
        echo "release.sh — Version tagging & safe rollback"
        echo ""
        echo "Commands:"
        echo "  tag [version]     Tag current HEAD (default: reads pyproject.toml)"
        echo "  list              List all tagged releases"
        echo "  diff <version>    Show changes since a version"
        echo "  revert <version>  Safely revert to a tagged version"
        echo "  status            Show current version state"
        ;;
esac
