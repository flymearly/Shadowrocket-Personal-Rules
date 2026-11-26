#!/usr/bin/env python3
"""Read-only upstream review. Never writes stable rules or executes upstream content."""
import hashlib
import os
import re
import sys
import urllib.request
from collections import defaultdict
from datetime import datetime, timezone
from urllib.parse import urlparse
from ai_rules import LIST, LABEL, SHARED, parse
from review_memory import LEDGER, load, disposition

BASE = 'https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/master/rule/Shadowrocket/'
SOURCES = {
    'OpenAI community': (BASE + 'OpenAI/OpenAI.list', 'sr'),
    'Gemini community': (BASE + 'Gemini/Gemini.list', 'sr'),
    'Claude community': (BASE + 'Claude/Claude.list', 'sr'),
    'Gemini v2fly': ('https://raw.githubusercontent.com/v2fly/domain-list-community/master/data/google-deepmind', 'v2fly'),
    'OpenRouter official': ('https://openrouter.ai/developers', 'openrouter'),
}
MAX_BYTES = 2_000_000
MAX_RULES = 500
# A narrow classification aid, not a proof of service ownership.
DEDICATED = ('openai.com','chatgpt.com','oaistatic.com','oaiusercontent.com',
             'anthropic.com','claude.ai','claude.com','claudeusercontent.com','openrouter.ai',
             'gemini.google.com','gemini.google','aistudio.google.com','ai.google.dev')


def valid_host(host):
    return len(host) <= 253 and '.' in host and all(LABEL.fullmatch(x) for x in host.split('.'))


def under(host, suffix):
    return host == suffix or host.endswith('.' + suffix)


def covered(rule, stable):
    typ, host = rule
    return any((t == 'DOMAIN-SUFFIX' and under(host, h)) or (typ == 'DOMAIN' and t == 'DOMAIN' and host == h) for t,h in stable)


def classify(rule, stable):
    typ, host = rule
    if covered(rule, stable):
        return 'COVERED'
    if host in SHARED or (typ == 'DOMAIN-SUFFIX' and any(under(h, host) for h in SHARED)):
        return 'BLOCKED_SHARED_ROOT'
    if typ == 'DOMAIN-SUFFIX' and any(under(h, host) for _,h in stable):
        return 'REVIEW_SCOPE_EXPANSION'
    if any(under(host, h) for h in DEDICATED):
        return 'REVIEW_AI_NAMESPACE'
    return 'REVIEW_SHARED_OR_NEW_SERVICE'


def extract(data, fmt):
    text = data.decode('utf-8', errors='strict')
    rules, skipped = set(), 0
    if fmt == 'openrouter':
        # Only detect hosts inside the already known OpenRouter namespace.
        # No arbitrary domains from links or third-party dependencies.
        for h in re.findall(r'(?i)(?<![a-z0-9.-])(?:[a-z0-9-]+\.)*openrouter\.ai(?![a-z0-9.-])', text):
            h = h.lower()
            if valid_host(h):
                rules.add(('DOMAIN', h))
    else:
        for raw in text.splitlines():
            line = raw.split('#', 1)[0].strip()
            if not line:
                continue
            if fmt == 'sr':
                parts = [p.strip() for p in line.split(',')]
                if len(parts) != 2 or parts[0] not in ('DOMAIN','DOMAIN-SUFFIX'):
                    skipped += 1
                    continue
                typ, host = parts
            else:
                # v2fly bare domains are suffix matches; full: is exact.
                parts = line.split()
                if len(parts) != 1:
                    skipped += 1
                    continue
                if line.startswith('full:'):
                    typ, host = 'DOMAIN', line[5:]
                elif line.startswith('domain:'):
                    typ, host = 'DOMAIN-SUFFIX', line[7:]
                elif ':' not in line:
                    typ, host = 'DOMAIN-SUFFIX', line
                else:
                    skipped += 1
                    continue
            host = host.lower()
            if not valid_host(host):
                skipped += 1
                continue
            rules.add((typ,host))
    if not rules or len(rules) > MAX_RULES:
        raise ValueError('unexpected source rule count; review upstream format')
    return rules, skipped


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError('unexpected upstream redirect; review source URL')


def fetch(url):
    p = urlparse(url)
    if p.scheme != 'https' or p.hostname not in ('raw.githubusercontent.com','openrouter.ai'):
        raise ValueError('source not allowlisted')
    req = urllib.request.Request(url, headers={'User-Agent':'Personal-AI-Rule-Review/1.0', 'Accept-Encoding':'identity'})
    with urllib.request.build_opener(NoRedirect()).open(req, timeout=20) as response:
        data = response.read(MAX_BYTES+1)
    if len(data) > MAX_BYTES:
        raise ValueError('source exceeds size limit')
    return data


def review(fetcher=fetch, ledger_path=LEDGER, today=None):
    ledger_before = ledger_path.read_bytes()
    decisions = load(ledger_before, SOURCES)
    today = today or datetime.now(timezone.utc).date()
    before = LIST.read_bytes()
    stable = parse(before)
    found = defaultdict(set)
    stats, errors = [], []
    for name,(url,fmt) in SOURCES.items():
        try:
            raw = fetcher(url)
            rules, skipped = extract(raw,fmt)
            stats.append((name,url,len(rules),skipped,hashlib.sha256(raw).hexdigest()))
            for r in rules:
                found[r].add(name)
        except Exception as e:
            # Do not print untrusted response bodies or exception text into CI.
            errors.append((name,type(e).__name__))
    rows = [(classify(r,stable),r,sorted(names)) for r,names in sorted(found.items())]
    report = ['# AI rule review (not a release)', '',
              f'Stable: {len(stable)} rules; SHA-256 `{hashlib.sha256(before).hexdigest()}`.',
              'No rule was applied. No deletions inferred from upstream absence.',
              'Every uncovered entry requires human service-ownership and routing review.', '',
              '## Source status', '', '| Source | Parsed | Skipped | SHA-256 |', '|---|---:|---:|---|']
    for name,url,count,skipped,sha in stats:
        report.append(f'| [{name}]({url}) | {count} | {skipped} | `{sha}` |')
    for name,error in errors:
        report.append(f'| {name} FAILED ({error}) | - | - | - |')
    uncovered = [(c,r,n) for c,r,n in rows if c != 'COVERED']
    groups = {'action': [], 'remembered': [], 'blocked': []}
    for risk, rule, names in uncovered:
        state = disposition(rule, risk, names, decisions, today, bool(errors))
        group = ('blocked' if state == 'BLOCKED' else 'remembered'
                 if state in ('DEFERRED', 'REJECTED') else 'action')
        groups[group].append((state, risk, rule, names))
    report += ['', f'Covered upstream conditions: {len(rows)-len(uncovered)}. Uncovered conditions: {len(uncovered)}.',
               f'Actionable: {len(groups["action"])}; remembered: {len(groups["remembered"])}; blocked: {len(groups["blocked"])}.',
               f'Review ledger: {len(decisions)} records; SHA-256 `{hashlib.sha256(ledger_before).hexdigest()}`; UTC date {today}.']
    for group, heading in (('action', 'Candidates needing review'), ('remembered', 'Previously reviewed (still visible)'), ('blocked', 'Blocked shared roots (never auto-approved)')):
        report += ['', '## ' + heading, '', '| Decision state | Risk | Condition | Source | Review until |', '|---|---|---|---|---|']
        for state, risk, rule, names in groups[group]:
            typ, host = rule
            until = decisions.get(rule, {}).get('review_until', '-')
            report.append(f'| {state} | {risk} | `{typ},{host}` | {", ".join(names)} | {until} |')
        if not groups[group]:
            report.append('| - | - | None | - | - |')
    report += ['', 'UNREVIEWED means no recorded decision, not necessarily new upstream. A changed source set, risk, or expired date reopens a decision. Incomplete sources disable remembered filtering. Reasons remain in the ledger.']
    if errors:
        report += ['', '**INCOMPLETE: at least one source failed. Do not treat as a successful review.**']
    report += ['', 'OpenRouter monitoring is namespace-only; new unrelated dependency domains require manual discovery.',
               'Community sources are evidence leads, not official service inventories. Review official documentation and device logs before publishing.']
    if LIST.read_bytes() != before:
        raise RuntimeError('stable list changed during review')
    if ledger_path.read_bytes() != ledger_before:
        raise RuntimeError('review ledger changed during review')
    return '\n'.join(report)+'\n', bool(errors)


def main():
    report, failed = review()
    print(report, end='')
    if os.environ.get('GITHUB_STEP_SUMMARY'):
        with open(os.environ['GITHUB_STEP_SUMMARY'], 'a', encoding='utf-8') as f:
            f.write(report)
    return int(failed)


if __name__ == '__main__':
    sys.exit(main())
