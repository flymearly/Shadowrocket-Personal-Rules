#!/usr/bin/env python3
"""Check additive AI proposals; never publish or infer domain ownership."""
import re
import subprocess
import sys
from ai_rules import LIST, parse
from check_ai_updates import classify, SOURCES
from review_memory import LEDGER, load


def check(base, candidate):
    old, new = parse(base), parse(candidate)
    if new[:len(old)] != old:
        raise ValueError('existing rules must remain in original order; append only')
    added = new[len(old):]
    for rule in added:
        if classify(rule, old) == 'BLOCKED_SHARED_ROOT':
            raise ValueError('blocked shared root: ' + rule[1])
    return added


def git(*args):
    return subprocess.check_output(['git', *args])


def main(base):
    if not re.fullmatch(r'[0-9a-f]{40}', base):
        raise ValueError('expected full base commit SHA')
    names = set(git('diff', '--name-only', '-z', base, 'HEAD').decode().split('\0')) - {''}
    allowed = {'rules/AI.list', 'rules/AI.review.json'}
    if not names & allowed or not names <= allowed | {'CHANGELOG.md'}:
        raise ValueError('proposal may change AI.list, AI.review.json and optionally CHANGELOG.md only')
    decisions = load(LEDGER.read_bytes(), SOURCES)
    print(f'PASS: {len(decisions)} review memory records; no automatic approval.')
    additions = check(git('show', base + ':rules/AI.list'), LIST.read_bytes())
    print(f'PASS: {len(additions)} additive conditions; existing conditions unchanged.')
    for typ, host in additions:
        print(f'REVIEW REQUIRED: {typ},{host}')
    print('Human evidence and routing review required before merge. No auto-publish.')


if __name__ == '__main__':
    try:
        main(sys.argv[1])
    except (ValueError, OSError, subprocess.CalledProcessError, IndexError) as exc:
        sys.exit(f'STOP: {exc}')
