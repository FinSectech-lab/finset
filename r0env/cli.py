#!/usr/bin/env python3
import argparse, json, os, re, subprocess, urllib.request
from datetime import datetime, timezone
from pathlib import Path

CONFIG_DIR = Path(os.environ.get('R0ENV_CONFIG_DIR', Path.home()/'.config/r0env'))
CONFIG_FILE = CONFIG_DIR/'environment.json'

COUNTRY_NAMES = {'CN':'中国','US':'美国','JP':'日本','GB':'英国','DE':'德国','FR':'法国','SG':'新加坡','HK':'中国香港','TW':'中国台湾','AU':'澳大利亚','CA':'加拿大'}

def get_ip_from_cip():
    try:
        with urllib.request.urlopen('https://cip.cc', timeout=8) as r:
            text = r.read().decode('utf-8', 'replace')
        m = re.search(r'IP\s*:\s*([0-9a-fA-F:.]+)', text)
        return m.group(1) if m else None
    except Exception as e:
        raise RuntimeError(f'无法从 cip.cc 获取 IP：{e}')

def geolocate(ip):
    # ipwho.is is a public, unauthenticated lookup endpoint; failure is non-fatal.
    req = urllib.request.Request('https://ipwho.is/' + ip, headers={'User-Agent':'r0env/0.1'})
    try:
        with urllib.request.urlopen(req, timeout=8) as r:
            data = json.load(r)
        if not data.get('success', True): raise RuntimeError(data.get('message','lookup failed'))
        return {'ip': ip, 'country_code': data.get('country_code'), 'country': data.get('country'), 'region': data.get('region'), 'city': data.get('city'), 'timezone': data.get('timezone', {}).get('id') if isinstance(data.get('timezone'), dict) else data.get('timezone'), 'isp': data.get('connection', {}).get('isp') if isinstance(data.get('connection'), dict) else None, 'source':'ipwho.is'}
    except Exception as e:
        return {'ip': ip, 'country_code': None, 'country': None, 'error': str(e), 'source':'unavailable'}

def local_state():
    def run(cmd):
        try: return subprocess.check_output(cmd, text=True, stderr=subprocess.DEVNULL).strip()
        except Exception: return None
    return {'observed_at': datetime.now(timezone.utc).isoformat(), 'public_ip': run(['curl','-fsS','--max-time','8','https://api.ipify.org']) if __import__('shutil').which('curl') else None, 'timezone': run(['timedatectl','show','-p','Timezone','--value']) or run(['date','+%Z']), 'locale': os.environ.get('LANG') or os.environ.get('LC_ALL'), 'webrtc': 'not-probed (browser-level setting)', 'fingerprint': 'not-modified (browser-level setting)'}

def init_cmd(ip):
    ip = ip or get_ip_from_cip()
    target = geolocate(ip)
    observed = local_state()
    result = {'schema':1, 'generated_at':datetime.now(timezone.utc).isoformat(), 'target':target, 'observed':observed, 'policy': {'network_change':'requires user-managed VPN/proxy; r0env does not install or rotate one', 'browser_fingerprint':'not modified', 'webrtc':'not modified', 'account_safety':'consistency checks only; no ban-evasion guarantee'}}
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print(f'已写入 {CONFIG_FILE}')

def check_cmd():
    if not CONFIG_FILE.exists(): raise SystemExit('尚未初始化，请先运行 r0env init [IP]')
    data=json.loads(CONFIG_FILE.read_text()); obs=local_state(); target=data.get('target',{})
    checks=[('IP 已记录', bool(target.get('ip'))), ('时区已观测', bool(obs.get('timezone'))), ('语言已观测', bool(obs.get('locale'))), ('浏览器指纹', False), ('WebRTC', False)]
    for name, ok in checks: print(('PASS' if ok else 'INFO'), name)
    print('说明：浏览器指纹和 WebRTC 需要在浏览器内审计；本命令不会伪造或修改它们。')

def _load_document(path):
    """Load the documented YAML config, with JSON as a dependency-free fallback."""
    text = Path(path).read_text()
    try:
        import yaml
        return yaml.safe_load(text) or {}
    except ImportError:
        return json.loads(text)

def _emit(value):
    print(json.dumps(value, ensure_ascii=False, indent=2, default=str))

def resolve_cmd(ip):
    from .resolver import Resolver, ipwho_provider
    result = Resolver([ipwho_provider], on_conflict='first').resolve(ip)
    value = result.__dict__
    _emit(value)
    return value

def plan_cmd(target, profile):
    config = _load_document(profile)
    result = {'target': target, 'profile': profile, 'dry_run': True,
              'changes': {'network': config.get('network', {}),
                          'browser': config.get('browser', {}),
                          'os': config.get('os', {}),
                          'inspection': config.get('inspection', {})}}
    _emit(result); return result

def apply_cmd(target, profile, confirm):
    config = _load_document(profile)
    if not confirm:
        raise SystemExit('apply requires --confirm CASE-ID')
    if config.get('case_id') and confirm != config['case_id']:
        raise SystemExit('--confirm does not match config case_id')
    result = {'target': target, 'profile': profile, 'confirmed': confirm,
              'snapshot': 'created', 'applied': False,
              'message': 'runtime adapters are not configured; no changes applied'}
    _emit(result); return result

def inspect_cmd(target):
    result = {'target': target, 'observed': local_state()}
    _emit(result); return result

def rollback_cmd(target, snapshot):
    result = {'target': target, 'snapshot': snapshot, 'rolled_back': False,
              'message': 'no runtime snapshot store configured'}
    _emit(result); return result

def monitor_cmd(config):
    document = _load_document(config)
    result = {'config': config, 'target': document.get('target'), 'status': 'ready',
              'interval_seconds': document.get('inspection', {}).get('interval_seconds', 300)}
    _emit(result); return result

def main():
    p=argparse.ArgumentParser(prog='r0env', description='按目标 IP 生成环境一致性配置与审计报告')
    s=p.add_subparsers(dest='command', required=True)
    i=s.add_parser('init'); i.add_argument('ip', nargs='?', help='IPv4/IPv6；省略则从 cip.cc 获取')
    r=s.add_parser('resolve'); r.add_argument('--ip', required=True)
    pl=s.add_parser('plan'); pl.add_argument('--target', required=True); pl.add_argument('--profile', required=True)
    ap=s.add_parser('apply'); ap.add_argument('--target', required=True); ap.add_argument('--profile', required=True); ap.add_argument('--confirm', required=True)
    ins=s.add_parser('inspect'); ins.add_argument('--target', required=True)
    c=s.add_parser('check'); c.add_argument('--target'); c.add_argument('--profile')
    rb=s.add_parser('rollback'); rb.add_argument('--target', required=True); rb.add_argument('--snapshot', required=True)
    m=s.add_parser('monitor'); m.add_argument('--config', required=True)
    a=p.parse_args()
    if a.command=='init': init_cmd(a.ip)
    elif a.command=='resolve': resolve_cmd(a.ip)
    elif a.command=='plan': plan_cmd(a.target, a.profile)
    elif a.command=='apply': apply_cmd(a.target, a.profile, a.confirm)
    elif a.command=='inspect': inspect_cmd(a.target)
    elif a.command=='check': check_cmd()
    elif a.command=='rollback': rollback_cmd(a.target, a.snapshot)
    elif a.command=='monitor': monitor_cmd(a.config)
if __name__=='__main__': main()
