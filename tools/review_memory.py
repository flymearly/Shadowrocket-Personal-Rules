"""Validated, exact-condition review decisions; never modifies routing rules."""
import json
from datetime import date
from ai_rules import ROOT, LABEL

LEDGER = ROOT / 'rules' / 'AI.review.json'
RISKS = {'REVIEW_AI_NAMESPACE', 'REVIEW_SCOPE_EXPANSION', 'REVIEW_SHARED_OR_NEW_SERVICE'}
FIELDS = {'condition', 'decision', 'risk', 'sources', 'review_until', 'reason'}


def load(raw, source_names):
    def unique_object(pairs):
        obj = {}
        for k, v in pairs:
            if k in obj:
                raise ValueError('duplicate JSON field')
            obj[k] = v
        return obj
    data = json.loads(raw, object_pairs_hook=unique_object)
    if not isinstance(data, list) or len(data) > 5000:
        raise ValueError('expected decision array, at most 5000 entries')
    out = {}
    for row in data:
        if not isinstance(row, dict) or set(row) != FIELDS:
            raise ValueError('invalid review decision fields')
        if not all(isinstance(row[k], str) for k in FIELDS - {'sources'}):
            raise ValueError('invalid decision value type')
        parts = row['condition'].split(',')
        if (len(parts) != 2 or parts[0] not in ('DOMAIN', 'DOMAIN-SUFFIX')
                or len(parts[1]) > 253 or '.' not in parts[1]
                or not all(LABEL.fullmatch(x) for x in parts[1].split('.'))):
            raise ValueError('invalid review condition')
        rule = tuple(parts)
        if rule in out:
            raise ValueError('duplicate review condition')
        if row['decision'] not in ('deferred', 'rejected') or row['risk'] not in RISKS:
            raise ValueError('unsupported review decision or risk')
        names = row['sources']
        if (not isinstance(names, list) or not names or not all(isinstance(s, str) for s in names)
                or len(set(names)) != len(names) or not set(names) <= set(source_names)):
            raise ValueError('invalid review sources')
        expiry = date.fromisoformat(row['review_until'])
        if expiry.isoformat() != row['review_until']:
            raise ValueError('expected ISO review date')
        if not row['reason'].strip() or len(row['reason']) > 500:
            raise ValueError('reason required (1-500 characters)')
        out[rule] = row
    return out


def disposition(rule, risk, names, decisions, today, incomplete=False):
    if risk == 'BLOCKED_SHARED_ROOT':
        return 'BLOCKED'
    row = decisions.get(rule)
    if row is None:
        return 'UNREVIEWED'
    if incomplete:
        return 'REOPENED_INCOMPLETE'
    if risk != row['risk'] or set(names) != set(row['sources']):
        return 'REOPENED_CHANGED'
    if today >= date.fromisoformat(row['review_until']):
        return 'REOPENED_EXPIRED'
    return row['decision'].upper()
