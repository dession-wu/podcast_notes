"""Bounded HTTP fetches with public-IP pinning and redirect revalidation."""
import http.client
import ipaddress
import socket
import ssl
import time
from urllib.parse import urljoin, urlsplit


def destination(url):
    parsed = urlsplit(url)
    if (parsed.scheme not in ('http', 'https') or not parsed.hostname
            or parsed.username or parsed.password or parsed.fragment
            or parsed.port not in (None, 80, 443)):
        raise ValueError('不支持的内容地址')
    port = parsed.port or (443 if parsed.scheme == 'https' else 80)
    addresses = socket.getaddrinfo(parsed.hostname, port, type=socket.SOCK_STREAM)
    ips = [item[4][0] for item in addresses]
    if not ips or any(not ipaddress.ip_address(ip).is_global or ipaddress.ip_address(ip).is_multicast for ip in ips):
        raise ValueError('内容地址必须指向公网')
    return parsed, port, ips[0]


def fetch(url, limit, target=None):
    """Never re-resolve DNS on connect, never honor proxy environment variables."""
    started = time.monotonic()
    for _ in range(6):
        parsed, port, ip = destination(url)
        conn = http.client.HTTPConnection(parsed.hostname, port, timeout=20)
        sock = socket.create_connection((ip, port), timeout=20)
        try:
            if parsed.scheme == 'https':
                sock = ssl.create_default_context().wrap_socket(sock, server_hostname=parsed.hostname)
            conn.sock = sock
            path = parsed.path or '/'
            if parsed.query:
                path += '?' + parsed.query
            conn.request('GET', path, headers={'User-Agent': 'PodcastNotes/mini', 'Accept-Encoding': 'identity'})
            response = conn.getresponse()
            if response.status in (301, 302, 303, 307, 308):
                location = response.getheader('Location')
                if not location:
                    raise ValueError('来源跳转无效')
                url = urljoin(url, location)
                continue
            if response.status != 200:
                raise ValueError('来源暂时无法访问')
            length = response.getheader('Content-Length')
            if length and int(length) > limit:
                raise ValueError('来源文件超过大小限制')
            data = bytearray()
            size = 0
            output = target.open('wb') if target else None
            try:
                while True:
                    if time.monotonic() - started > 180:
                        raise ValueError('来源下载超时')
                    chunk = response.read(65536)
                    if not chunk:
                        break
                    size += len(chunk)
                    if size > limit:
                        raise ValueError('来源文件超过大小限制')
                    if output:
                        output.write(chunk)
                    else:
                        data.extend(chunk)
            finally:
                if output:
                    output.close()
            return bytes(data)
        finally:
            conn.close()
            sock.close()
    raise ValueError('来源跳转次数过多')
