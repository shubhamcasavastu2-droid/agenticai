#!/usr/bin/env python3
"""
Git Change Tracker - Record changes with commit IDs
Usage: python track_changes.py [commit-hash] [--type TYPE] [--desc DESCRIPTION]
"""

import subprocess
import sys
import argparse
from datetime import datetime
from pathlib import Path


def run_git(args):
    """Run git with an argument list (no shell), so a commit argument can't inject commands."""
    result = subprocess.run(["git", *args], capture_output=True, text=True, cwd=Path.cwd())
    return result.stdout.strip(), result.stderr.strip(), result.returncode


def _revision(commit_hash):
    rev = commit_hash or "HEAD"
    if rev.startswith("-"):
        raise SystemExit(f"Invalid commit reference: {rev}")
    return rev


def get_commit_info(commit_hash=None):
    stdout, stderr, code = run_git(["show", _revision(commit_hash), "--stat", "--format=%H|%an|%ad|%s", "--date=short"])
    if code != 0:
        return None
    lines = stdout.strip().split('\n')
    header = lines[0].split('|')
    return {
        'hash': header[0][:8],
        'author': header[1],
        'date': header[2],
        'subject': header[3],
        'files': [l.strip() for l in lines[1:] if l.strip() and not l.startswith(' ')],
    }


def get_changed_files(commit_hash=None):
    stdout, _, _ = run_git(["show", _revision(commit_hash), "--name-only", "--format="])
    return [f for f in stdout.strip().split('\n') if f]


def categorize_changes(files):
    categories = {
        'feat': [],
        'fix': [],
        'refactor': [],
        'docs': [],
        'test': [],
        'chore': [],
    }
    for f in files:
        if f.startswith('test') or f.endswith('_test.py') or 'test/' in f:
            categories['test'].append(f)
        elif f.endswith('.md') or f.endswith('.rst') or 'doc' in f.lower():
            categories['docs'].append(f)
        elif f.endswith('.py') and ('fix' in f or 'bug' in f):
            categories['fix'].append(f)
        elif f.endswith('.py') and ('refactor' in f or 'clean' in f):
            categories['refactor'].append(f)
        elif f.endswith('.py'):
            categories['feat'].append(f)
        else:
            categories['chore'].append(f)
    return {k: v for k, v in categories.items() if v}


def generate_entry(commit_hash=None, change_type=None, description=None):
    info = get_commit_info(commit_hash)
    if not info:
        return "Error: Could not get commit info"
    
    files = get_changed_files(commit_hash)
    categories = categorize_changes(files)
    
    # Determine primary type
    if change_type:
        primary_type = change_type
    elif 'fix' in categories:
        primary_type = 'fix'
    elif 'feat' in categories:
        primary_type = 'feat'
    elif 'refactor' in categories:
        primary_type = 'refactor'
    elif 'docs' in categories:
        primary_type = 'docs'
    elif 'test' in categories:
        primary_type = 'test'
    else:
        primary_type = 'chore'
    
    entry = f"## [{info['hash']}] - {info['date']}\n"
    entry += f"- **Type**: {primary_type}\n"
    entry += f"- **Author**: {info['author']}\n"
    if description:
        entry += f"- **Description**: {description}\n"
    else:
        entry += f"- **Description**: {info['subject']}\n"
    entry += f"- **Files** ({len(files)}):\n"
    for cat, cat_files in categories.items():
        if cat_files:
            entry += f"  - {cat}: {', '.join(cat_files[:5])}"
            if len(cat_files) > 5:
                entry += f" ... (+{len(cat_files)-5} more)"
            entry += "\n"
    entry += "\n"
    return entry


def main():
    parser = argparse.ArgumentParser(description="Track git changes with commit IDs")
    parser.add_argument('commit', nargs='?', help='Commit hash (default: HEAD)')
    parser.add_argument('--type', choices=['feat', 'fix', 'refactor', 'docs', 'test', 'chore'], help='Change type')
    parser.add_argument('--desc', help='Description of changes')
    parser.add_argument('--output', '-o', default='CHANGELOG.md', help='Output file')
    parser.add_argument('--append', '-a', action='store_true', help='Append to existing file')
    
    args = parser.parse_args()
    
    entry = generate_entry(args.commit, args.type, args.desc)
    
    output_path = Path(args.output)
    if args.append and output_path.exists():
        with open(output_path, 'a') as f:
            f.write(entry)
    else:
        with open(output_path, 'w') as f:
            f.write("# Changelog\n\n")
            f.write(entry)
    
    print(f"Recorded to {args.output}")
    print(entry)


if __name__ == '__main__':
    main()