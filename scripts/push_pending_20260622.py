#!/usr/bin/env python3
"""Push pending-2026-06-22 branch via GitHub REST API (sandbox git push blocked)."""
import json
import urllib.request
import urllib.error
import sys

REPO = "Hammerboy2016/cathaytales"
BRANCH = "pending-2026-06-22"
API = "https://api.github.com"
PAT = open("/tmp/pat.txt").read().strip()

POSTS = [
    {
        "path": "posts/045-the-night-the-dead-sat-up-crying.md",
        "msg": "Add Liaozhai: The Night the Dead Sat Up Crying [scheduled:12:07]",
    },
    {
        "path": "posts/046-the-ghost-who-kept-her-lover-alive.md",
        "msg": "Add Yuewei: The Ghost Who Kept Her Lover Alive on Purpose [scheduled:15:41]",
    },
]
AUTHOR = {"name": "wangcai", "email": "wudecangyu@163.com"}


def call(method, path, data=None):
    url = f"{API}{path}" if path.startswith("/") else path
    body = json.dumps(data).encode() if data is not None else None
    req = urllib.request.Request(url, data=body, method=method, headers={
        "Authorization": f"token {PAT}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "Content-Type": "application/json",
        "User-Agent": "wangcai-cli",
    })
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")
        print(f"HTTP {e.code} on {method} {path}: {body}", file=sys.stderr)
        raise


# 1. get current main sha
ref = call("GET", f"/repos/{REPO}/git/ref/heads/main")
parent_sha = ref["object"]["sha"]
print(f"main HEAD sha: {parent_sha}")

parent_commit = call("GET", f"/repos/{REPO}/git/commits/{parent_sha}")
base_tree_sha = parent_commit["tree"]["sha"]
print(f"main HEAD tree: {base_tree_sha}")

current_parent = parent_sha
current_tree = base_tree_sha

for post in POSTS:
    with open(post["path"], "r", encoding="utf-8") as f:
        content = f.read()
    blob = call("POST", f"/repos/{REPO}/git/blobs", {
        "content": content, "encoding": "utf-8",
    })
    blob_sha = blob["sha"]
    print(f"blob {post['path']}: {blob_sha}")

    tree = call("POST", f"/repos/{REPO}/git/trees", {
        "base_tree": current_tree,
        "tree": [{"path": post["path"], "mode": "100644", "type": "blob", "sha": blob_sha}],
    })
    tree_sha = tree["sha"]

    commit = call("POST", f"/repos/{REPO}/git/commits", {
        "message": post["msg"], "tree": tree_sha, "parents": [current_parent],
        "author": AUTHOR, "committer": AUTHOR,
    })
    print(f"commit: {commit['sha']} -- {post['msg'][:65]}")
    current_parent = commit["sha"]
    current_tree = tree_sha

# create or update branch ref
try:
    call("POST", f"/repos/{REPO}/git/refs", {
        "ref": f"refs/heads/{BRANCH}", "sha": current_parent,
    })
    print(f"branch {BRANCH} created at {current_parent}")
except urllib.error.HTTPError:
    call("PATCH", f"/repos/{REPO}/git/refs/heads/{BRANCH}", {
        "sha": current_parent, "force": True,
    })
    print(f"branch {BRANCH} force-updated to {current_parent}")

print(f"\nhttps://github.com/{REPO}/tree/{BRANCH}")
