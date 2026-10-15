"""Launch the generated profile in an isolated Playwright browser."""
import json
import os
from .auto import _browser_profile
from .adapters.browser import BrowserAdapter
from .network import proxy_url
from .macos import data_dir


def launch_options(profile):
    plan = BrowserAdapter().plan({}, _browser_profile(profile['browser']))
    engine = plan['engine']
    options = {'headless': False}
    saved = profile.get('network', {}).get('egress', {}).get('proxy_url', proxy_url())
    proxy = os.environ.get('R0ENV_PROXY', saved)
    if proxy:
        options['proxy'] = {'server': proxy}
    if engine == 'firefox':
        prefs = dict(plan['firefox_prefs'])
        # Playwright sets the proxy. Never override it with network.proxy.type=0.
        if proxy:
            prefs.pop('network.proxy.type', None)
        else:
            prefs['network.proxy.type'] = 0
        dns = profile['network']['dns']
        if dns['mode'] == 'doh':
            prefs.update({'network.trr.mode': 3 if dns['fallback'] == 'deny' else 2,
                          'network.trr.uri': dns['servers'][0]})
        options['firefox_user_prefs'] = prefs
    else:
        options['args'] = list(plan['chromium_args'])
        if not proxy:
            options['args'].append('--no-proxy-server')
    return engine, options, plan['context_options']


def launch():
    path = data_dir() / 'profile.json'
    if not path.exists():
        raise RuntimeError('请先运行 r0env apply/ff/cr 生成 profile。')
    profile = json.loads(path.read_text(encoding='utf-8'))
    engine, options, context_options = launch_options(profile)
    from playwright.sync_api import sync_playwright
    with sync_playwright() as runtime:
        browser = getattr(runtime, engine).launch(**options)
        try:
            context = browser.new_context(**context_options)
            page = context.new_page()
            print('隔离浏览器已打开。关闭窗口结束会话；配置仅影响此浏览器。')
            if engine == 'chromium':
                print('Chromium DNS 由代理/系统管理；此命令不更改系统 DNS。')
            while browser.is_connected() and context.pages:
                try:
                    context.pages[0].wait_for_timeout(500)
                except Exception:
                    if browser.is_connected() and context.pages:
                        raise
        finally:
            browser.close()
