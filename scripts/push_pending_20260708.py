#!/usr/bin/env python3
"""Push pending-2026-07-08 branch via GitHub REST API.

W28 #5 聊斋 · Retelling — 小翠 (卷七)
rotation_pointer: 5 → 6
"""
import json
import os
import re
import subprocess
import urllib.request
import urllib.error
import sys

REPO = "Hammerboy2016/cathaytales"
BRANCH = "pending-2026-07-08"
API = "https://api.github.com"

# 从 git remote 抽 PAT（避免硬编码到脚本）
remote = subprocess.check_output(
    ["git", "config", "--get", "remote.origin.url"], text=True
).strip()
m = re.match(r"https://Hammerboy2016:([^@]+)@github\.com/.+", remote)
if not m:
    sys.exit("无法从 remote.origin.url 中提取 PAT")
PAT = m.group(1)

POSTS = [
    {
        "path": "posts/066-the-fox-wife-whose-pranks-cured-a-fool.md",
        "msg": "Add Liaozhai: The Fox Wife Whose Pranks Cured a Fool [scheduled:12:38]",
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
    print(f"tree: {tree_sha}")

    commit = call("POST", f"/repos/{REPO}/git/commits", {
        "message": post["msg"],
        "tree": tree_sha,
        "parents": [current_parent],
        "author": AUTHOR,
        "committer": AUTHOR,
    })
    commit_sha = commit["sha"]
    print(f"commit: {commit_sha}  {post['msg']}")
    current_parent = commit_sha
    current_tree = tree_sha

# Create or update the pending branch ref
try:
    call("GET", f"/repos/{REPO}/git/ref/heads/{BRANCH}")
    print(f"branch {BRANCH} exists, updating (force)")
    call("PATCH", f"/repos/{REPO}/git/refs/heads/{BRANCH}", {
        "sha": current_parent, "force": True,
    })
except urllib.error.HTTPError as e:
    if e.code == 404:
        print(f"branch {BRANCH} not exists, creating")
        call("POST", f"/repos/{REPO}/git/refs", {
            "ref": f"refs/heads/{BRANCH}",
            "sha": current_parent,
        })
    else:
        raise

print(f"DONE: {BRANCH} -> {current_parent}")
