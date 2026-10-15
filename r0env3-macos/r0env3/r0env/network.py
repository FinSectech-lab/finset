"""Consistent proxy selection, including explicit direct connections."""
import json
import os
import urllib.request


def proxy_url():
    return os.environ.get('R0ENV_PROXY', 'http://127.0.0.1:7890')


def opener(proxy=None):
    proxy = proxy_url() if proxy is None else proxy
    if proxy and not proxy.startswith(('http://', 'https://')):
        raise ValueError('IP 查询需要 HTTP/HTTPS 代理，请使用 Clash/mihomo 的 HTTP 或 mixed 端口。')
    return urllib.request.build_opener(urllib.request.ProxyHandler({'http': proxy, 'https': proxy} if proxy else {}))


def fetch_json(url, proxy=None):
    with opener(proxy).open(urllib.request.Request(url, headers={'User-Agent': 'r0env3/0.1'}), timeout=10) as response:
        data = json.load(response)
    if data.get('success') is False:
        raise ValueError(data.get('message', 'IP lookup failed'))
    return data


def exit_ip(proxy=None):
    from .resolver import validate_public_ip
    return validate_public_ip(fetch_json('https://ipwho.is/', proxy)['ip'])
