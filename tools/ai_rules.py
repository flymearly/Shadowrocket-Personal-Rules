#!/usr/bin/env python3
"""Validate syntax, and build the initial V1.5 additive candidate."""
import argparse
import hashlib
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LIST = ROOT / 'rules' / 'AI.list'
BASE_SHA = '24ba1cf1f057fac76687e9afdea9609bffd19cb2220ac665be5de78f959936e3'
LABEL = re.compile(r'[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\Z')
SHARED = {'google.com','googleapis.com','gstatic.com','googleusercontent.com','cloudflare.com','workos.com','workoscdn.com','imgix.net','auth0.com','amazonaws.com','cloudfront.net','stripe.com','github.com','azurewebsites.net','akamaihd.net','accounts.google.com','oauth2.googleapis.com'}

def require(ok, message):
    if not ok:
        raise ValueError(message)

def parse(raw):
    result = []
    for i, line in enumerate(raw.decode('utf-8').splitlines(), 1):
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        parts = line.split(',')
        require(len(parts)==2 and parts[0] in ('DOMAIN','DOMAIN-SUFFIX'), f'line {i}: expected DOMAIN or DOMAIN-SUFFIX,host')
        typ, host = parts
        require(len(host)<=253 and '.' in host and all(LABEL.fullmatch(x) for x in host.split('.')), f'line {i}: invalid host')
        require(host not in SHARED, f'line {i}: shared root/service requires separate review: {host}')
        require((typ,host) not in result, f'line {i}: duplicate rule')
        result.append((typ,host))
    require(bool(result), 'empty rule list')
    for t,h in result:
        require(not any(t2=='DOMAIN-SUFFIX' and (t2,h2)!=(t,h) and (h==h2 or h.endswith('.'+h2)) for t2,h2 in result), f'redundant domain: {t},{h}')
    return result

def build(base, remote, owner, output):
    require(re.fullmatch(r'[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?', owner) is not None, 'invalid GitHub owner')
    data = base.read_bytes()
    require(hashlib.sha256(data).hexdigest()==BASE_SHA, 'baseline hash mismatch; stop and review, no output written')
    local = LIST.read_bytes()
    require(remote.read_bytes()==local, 'downloaded remote file does not match local AI.list')
    actual = parse(local)
    text = data.decode('utf-8')
    a = text.index('# ===== AI =====\n')
    b = text.index('# YouTube\n',a)
    original = [tuple(x.split(',')[:2]) for x in text[a:b].splitlines() if x.startswith(('DOMAIN,','DOMAIN-SUFFIX,')) and x.endswith(',AI')]
    require(len(original)==42 and actual==original, 'initial remote list must exactly match all 42 original AI rules in order')
    url = f'https://raw.githubusercontent.com/{owner}/Shadowrocket-Personal-Rules/main/rules/AI.list'
    line = f'RULE-SET,{url},AI\n'
    addition = '# V1.5: remote additions after local AI baseline; keep V1.4 for rollback.\n'+line+'\n'
    candidate = text[:b]+addition+text[b:]
    require(candidate.replace(addition,'',1)==text, 'unexpected config mutation')
    with output.open('xb') as f:
        f.write(candidate.encode('utf-8'))
    print(f'PASS: 42 initial rules match exactly; only one RULE-SET added; {output}')
    print('SHA256:', hashlib.sha256(output.read_bytes()).hexdigest())
    print('RULE-SET:',url)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    subs=p.add_subparsers(dest='command',required=True)
    subs.add_parser('validate')
    b=subs.add_parser('build')
    b.add_argument('--base',type=Path,required=True)
    b.add_argument('--remote-list',type=Path,required=True)
    b.add_argument('--owner',required=True)
    b.add_argument('--output',type=Path,required=True)
    args=p.parse_args()
    try:
        if args.command=='validate':
            print(f'PASS: {len(parse(LIST.read_bytes()))} rules; syntax, duplicates, known shared roots, suffix redundancy checked. Human semantic review still required.')
        else:
            build(args.base,args.remote_list,args.owner,args.output)
    except (ValueError,OSError) as e:
        p.exit(1,f'STOP: {e}\n')
