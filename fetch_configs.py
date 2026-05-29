#!/usr/bin/env python3
import requests
import base64
import os
import time
import json
import socket
import random
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Set, Tuple, Optional
from urllib.parse import urlparse
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# ============================================================
# لیست لینک‌های جمع‌کننده کانفیگ
# ============================================================
urls = [
    'https://raw.githubusercontent.com/ALIILAPRO/v2rayNG-Config/refs/heads/main/server.txt',
    'https://raw.githubusercontent.com/Epodonios/v2ray-configs/refs/heads/main/Sub1.txt',
    'https://raw.githubusercontent.com/Epodonios/v2ray-configs/refs/heads/main/Sub2.txt',
    'https://raw.githubusercontent.com/Epodonios/v2ray-configs/refs/heads/main/Splitted-By-Protocol/trojan.txt',
    'https://raw.githubusercontent.com/mahdibland/ShadowsocksAggregator/master/Eternity',
    'https://raw.githubusercontent.com/roosterkid/openproxylist/refs/heads/main/V2RAY_RAW.txt',
    'https://raw.githubusercontent.com/roosterkid/openproxylist/refs/heads/main/V2RAY_BASE64.txt',
    'https://www.v2nodes.com/subscriptions/country/all/?key=3890BB040E05763',
# ============================================================
# لیست لینک‌های جمع‌کننده کانفیگ
# ============================================================
    'https://raw.githubusercontent.com/mahsanet/MahsaFreeConfig/refs/heads/main/mtn/sub_1.txt',
    'https://raw.githubusercontent.com/mahsanet/MahsaFreeConfig/refs/heads/main/mtn/sub_2.txt',
    'https://raw.githubusercontent.com/mahsanet/MahsaFreeConfig/refs/heads/main/mtn/sub_3.txt',
    'https://raw.githubusercontent.com/mahsanet/MahsaFreeConfig/refs/heads/main/mtn/sub_4.txt',
    'https://raw.githubusercontent.com/mahsanet/MahsaFreeConfig/refs/heads/main/mci/sub_1.txt',
    'https://raw.githubusercontent.com/mahsanet/MahsaFreeConfig/refs/heads/main/mci/sub_2.txt',
    'https://raw.githubusercontent.com/mahsanet/MahsaFreeConfig/refs/heads/main/mci/sub_3.txt',
    'https://raw.githubusercontent.com/mahsanet/MahsaFreeConfig/refs/heads/main/mci/sub_4.txt',
    'https://raw.githubusercontent.com/10ium/V2RayAggregator/refs/heads/master/Eternity',
    'https://raw.githubusercontent.com/10ium/base64-encoder/main/encoded/10ium_ss_iran.txt',
    'https://raw.githubusercontent.com/10ium/base64-encoder/main/encoded/10ium-V2rayCollector-ss.txt',
    'https://raw.githubusercontent.com/10ium/base64-encoder/main/encoded/10ium_trojan_iran.txt',
    'https://raw.githubusercontent.com/10ium/V2ray-Config/main/Splitted-By-Protocol/ss.txt',
    'https://raw.githubusercontent.com/10ium/VpnClashFaCollector/refs/heads/main/sub/all/ss_base64.txt',
# ============================================================
# لیست لینک‌های جمع‌کننده کانفیگ
# ============================================================
    'https://raw.githubusercontent.com/Epodonios/v2ray-configs/refs/heads/main/All_Configs_base64_Sub.txt',
    'https://raw.githubusercontent.com/SoliSpirit/v2ray-configs/refs/heads/main/all_configs.txt',
    'https://raw.githubusercontent.com/Epodonios/v2ray-configs/refs/heads/main/All_Configs_Sub.txt',
    'https://raw.githubusercontent.com/barry-far/V2ray-config/main/All_Configs_base64_Sub.txt'
]

OUTPUT_FILES = {
    'vless': 'vless.txt',
    'reality': 'reality.txt',
    'vmess': 'vmess.txt',
    'trojan': 'trojan.txt',
    'hysteria2': 'hysteria2.txt',
    'shadowsocks': 'ss.txt',
    'socks': 'socks.txt',
    'wireguard': 'wireguard.txt'
}

MAX_CONFIGS_PER_FILE = 20000  # حداکثر تعداد کانفیگ در هر فایل

# ------------------------------------------------------------
# توابع (بدون تغییر)
# ------------------------------------------------------------
def decode_if_base64(content: str) -> str:
    try:
        return base64.b64decode(content).decode('utf-8', errors='ignore')
    except:
        return content

def extract_configs_from_line(line: str) -> Tuple[Optional[str], Optional[str]]:
    line = line.strip()
    if not line:
        return None, None
    if line.startswith('vless://'):
        if 'security=reality' in line:
            return 'reality', line
        return 'vless', line
    elif line.startswith('vmess://'):
        return 'vmess', line
    elif line.startswith('trojan://'):
        return 'trojan', line
    elif line.startswith('hysteria2://') or line.startswith('hy2://'):
        return 'hysteria2', line
    elif line.startswith('ss://'):
        return 'shadowsocks', line
    elif line.startswith('socks4://') or line.startswith('socks5://'):
        return 'socks', line
    elif line.startswith('wireguard://') or '[interface]' in line.lower():
        return 'wireguard', line
    return None, None

def get_host_port_from_config(protocol: str, config: str) -> Tuple[Optional[str], Optional[int]]:
    try:
        if protocol in ('vless', 'reality', 'trojan'):
            parsed = urlparse(config)
            return parsed.hostname, parsed.port
        elif protocol == 'vmess':
            import json
            encoded = config[8:]
            decoded = base64.b64decode(encoded).decode('utf-8', errors='ignore')
            data = json.loads(decoded)
            return data.get('add'), data.get('port')
        elif protocol == 'socks':
            parsed = urlparse(config)
            return parsed.hostname, parsed.port
        elif protocol == 'shadowsocks':
            if '@' in config:
                after_at = config.split('@')[1].split('#')[0]
                host, port = after_at.split(':')
                return host, int(port)
            else:
                encoded = config[5:].split('#')[0]
                decoded = base64.b64decode(encoded).decode('utf-8', errors='ignore')
                if '@' in decoded:
                    host_port = decoded.split('@')[1]
                    host, port = host_port.split(':')
                    return host, int(port)
        else:
            return None, None
    except:
        return None, None
    return None, None

def tcp_ping(host: str, port: int, timeout: float = 1.0) -> bool:
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        sock.connect((host, port))
        sock.close()
        return True
    except:
        return False

def fetch_url_with_retry(url: str, max_retries: int = 2, timeout: Tuple[int, int] = (10, 25)) -> Tuple[str, List[str]]:
    session = requests.Session()
    retries = Retry(
        total=max_retries,
        backoff_factor=0.5,
        status_forcelist=[500, 502, 503, 504],
        allowed_methods=["GET"]
    )
    adapter = HTTPAdapter(max_retries=retries)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    try:
        resp = session.get(url, timeout=timeout)
        if resp.status_code == 200:
            decoded = decode_if_base64(resp.text.strip())
            lines = [line.strip() for line in decoded.splitlines() if line.strip()]
            return url, lines
        else:
            print(f"   ⚠️ {url} returned {resp.status_code}")
            return url, []
    except Exception as e:
        print(f"   ❌ Failed after retries: {url} - {e}")
        return url, []

def fetch_all_parallel(urls: List[str], max_workers: int = 8) -> Dict[str, List[str]]:
    results = {}
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_url = {executor.submit(fetch_url_with_retry, url): url for url in urls}
        for future in as_completed(future_to_url):
            url, lines = future.result()
            results[url] = lines
            print(f"   ✅ {url} -> {len(lines)} lines")
    return results

def sample_health_check(configs: Set[str], protocol: str, sample_size: int = 300) -> dict:
    if protocol in ('hysteria2', 'wireguard'):
        return {'sampled': 0, 'alive': 0, 'percent': 0}
    config_list = list(configs)
    if len(config_list) <= sample_size:
        sample = config_list
    else:
        sample = random.sample(config_list, sample_size)
    alive = 0
    for cfg in sample:
        host, port = get_host_port_from_config(protocol, cfg)
        if host and port and tcp_ping(host, port, timeout=1.0):
            alive += 1
    return {'sampled': len(sample), 'alive': alive, 'percent': (alive/len(sample))*100 if sample else 0}

def main():
    print("🚀 Starting fetch with retry, parallel, health stats...")
    start_total = time.perf_counter()
    
    print("📡 Fetching from all sources concurrently (with retry)...")
    url_to_lines = fetch_all_parallel(urls, max_workers=8)
    
    configs_by_protocol: Dict[str, Set[str]] = {key: set() for key in OUTPUT_FILES.keys()}
    for url, lines in url_to_lines.items():
        for line in lines:
            proto, cfg = extract_configs_from_line(line)
            if proto and cfg:
                configs_by_protocol[proto].add(cfg)
    
    stats = {}
    print("\n🩺 Running health check sampling...")
    for proto, cfg_set in configs_by_protocol.items():
        raw_count = len(cfg_set)
        health = sample_health_check(cfg_set, proto, sample_size=300)
        stats[proto] = {
            'raw_count': raw_count,
            'final_count': raw_count,
            'health_sample': health
        }
        print(f"   {proto}: total={raw_count:,}, sample={health['sampled']}, alive={health['alive']} ({health['percent']:.1f}%)")
    
    # ============================================================
    # ذخیره فایل‌ها با قابلیت تقسیم خودکار (۲۰,۰۰۰ کانفیگ در هر فایل)
    # ============================================================
    for protocol, cfg_set in configs_by_protocol.items():
        if not cfg_set:
            print(f"⚠️ {OUTPUT_FILES[protocol]}: no configs found.")
            continue
        
        all_configs = sorted(cfg_set)
        total = len(all_configs)
        
        if total <= MAX_CONFIGS_PER_FILE:
            # یک فایل واحد
            text = "\n".join(all_configs)
            encoded = base64.b64encode(text.encode('utf-8')).decode('utf-8')
            with open(OUTPUT_FILES[protocol], 'w', encoding='utf-8') as f:
                f.write(encoded)
            print(f"✅ {OUTPUT_FILES[protocol]}: {total} configs saved.")
        else:
            # تقسیم به چند فایل
            num_files = (total + MAX_CONFIGS_PER_FILE - 1) // MAX_CONFIGS_PER_FILE
            base_name = OUTPUT_FILES[protocol].replace('.txt', '')
            for i in range(num_files):
                start = i * MAX_CONFIGS_PER_FILE
                end = min((i+1) * MAX_CONFIGS_PER_FILE, total)
                part_configs = all_configs[start:end]
                text = "\n".join(part_configs)
                encoded = base64.b64encode(text.encode('utf-8')).decode('utf-8')
                filename = f"{base_name}_{i+1}.txt"
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(encoded)
                print(f"✅ {filename}: {len(part_configs)} configs (part {i+1}/{num_files}) saved.")
    
    # ذخیره آمار
    total_configs = sum(stats[p]['final_count'] for p in stats)
    summary = {
        'total_configs': total_configs,
        'total_sources': len(urls),
        'execution_time_sec': time.perf_counter() - start_total,
        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime()),
        'successful_sources': len([u for u, lines in url_to_lines.items() if lines]),
        'failed_sources': len([u for u, lines in url_to_lines.items() if not lines])
    }
    stats['summary'] = summary
    with open('stats.json', 'w', encoding='utf-8') as f:
        json.dump(stats, f, indent=2)
    print(f"\n📊 Stats saved to stats.json")
    print(f"   Total configs: {total_configs:,}")
    print(f"   Execution time: {summary['execution_time_sec']:.2f}s")
    print(f"   Successful sources: {summary['successful_sources']} / {summary['total_sources']}")

if __name__ == "__main__":
    main()
