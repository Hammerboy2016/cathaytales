#!/usr/bin/env python3
"""
Push AdSense P0+P1 fixes to pending-2026-07-23 branch.
Does NOT push to main — owner reviews and merges manually.

Run: python3 scripts/push_ads_fix_20260723.py
"""
import subprocess, os, sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BRANCH = "pending-2026-07-23"

def run(cmd, cwd=REPO):
    print(f"  $ {cmd}")
    result = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True)
    if result.stdout.strip():
        print(f"    {result.stdout.strip()}")
    if result.returncode != 0:
        print(f"    ERROR: {result.stderr.strip()}")
        sys.exit(1)
    return result.stdout.strip()

def main():
    os.chdir(REPO)
    print("=" * 50)
    print(f"Push to branch: {BRANCH}")
    print("=" * 50)

    # Stage all changes
    run("git add -A")
    
    # Check what changed
    status = run("git status --short")
    if not status:
        print("  No changes to commit.")
        return

    # Create/checkout branch
    # Check if branch exists
    result = subprocess.run(f"git rev-parse --verify {BRANCH}", shell=True, cwd=REPO, capture_output=True)
    if result.returncode == 0:
        run(f"git checkout {BRANCH}")
    else:
        run(f"git checkout -b {BRANCH}")

    # Commit
    commit_msg = """fix: AdSense resubmission — P0+P1 fixes

P0-1: ads.txt (already in static/, verified in dist/)
P0-2: About page rewritten with editorial stance, Wang Cai translator credit, 8 series, methodology
P1-1: 71 posts get 3-5 internal links each (Related Tales section, rotated by hub/series)
P1-2: 71 posts get Translator's Note (50-80 words, series-specific, three-part structure)

- No frontmatter fields modified
- No existing content deleted
- Build verified: dist/ads.txt, dist/about.html, all 71 post HTMLs include new sections"""

    run(f'git commit -m "{commit_msg}"')
    
    # Push
    run(f"git push origin {BRANCH} --force-with-lease")
    
    # Get commit hash
    commit_hash = run("git rev-parse --short HEAD")
    print(f"\n✓ Done! Commit: {commit_hash}")
    print(f"  Branch: {BRANCH}")
    print(f"  Review at: https://github.com/Hammerboy2016/cathaytales/tree/{BRANCH}")
    print(f"\n  Owner: review and merge to main when ready to resubmit AdSense.")

if __name__ == '__main__':
    main()
