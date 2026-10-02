#!/usr/bin/env python3
"""Read-only HTTP phase diagnostics. Does not update Upptime state or issues."""
import concurrent.futures
import datetime
import json
import subprocess
import tempfile
from pathlib import Path

ENDPOINTS = (
    ('apex_redirect', 'https://yunle.fun/', False, 301),
    ('www_home', 'https://www.yunle.fun/', False, 200),
    ('home_chain', 'https://yunle.fun/', True, 200),
    ('app', 'https://app.yunle.fun/', False, 200),
)
SAFE_HEADERS = {'location', 'server', 'content-type', 'content-length',
                'cache-control', 'age', 'eo-cache-status', 'eo-log-uuid', 'date'}
METRICS = ('url_effective', 'http_code', 'remote_ip', 'remote_port', 'http_version',
           'num_redirects', 'time_namelookup', 'time_connect', 'time_appconnect',
           'time_starttransfer', 'time_total', 'size_download', 'ssl_verify_result')


def summarize_headers(raw):
    # Do not log cookies, authorization headers, or response bodies.
    return [line for line in raw.splitlines()
            if line.startswith('HTTP/') or line.partition(':')[0].lower() in SAFE_HEADERS]


def failure_phase(exit_code, metrics):
    if exit_code == 0:
        return None
    if exit_code in (5, 6):
        return 'dns'
    if exit_code == 7:
        return 'tcp_connect'
    if exit_code in (35, 51, 58, 60, 77):
        return 'tls'
    if exit_code != 28:
        return 'other_transport_error'
    # Milestones indicate the last completed phase, not the historical root cause.
    if metrics.get('num_redirects', 0):
        return 'timeout_during_redirect_chain_phase_unknown'
    if metrics.get('time_connect', 0) == 0:
        return 'dns_or_tcp_connect_timeout'
    if metrics.get('time_appconnect', 0) == 0:
        return 'tls_handshake_timeout'
    if metrics.get('time_starttransfer', 0) == 0:
        return 'http_first_byte_timeout'
    return 'response_body_timeout'


def evaluate(spec, exit_code, metrics, headers):
    name, url, follow, expected_status = spec
    phase = failure_phase(exit_code, metrics)
    if exit_code:
        return False, phase
    if metrics.get('http_code') != expected_status:
        return False, 'unexpected_http_status'
    if name == 'apex_redirect':
        locations = [line.partition(':')[2].strip()
                     for line in headers if line.lower().startswith('location:')]
        if locations != ['https://www.yunle.fun/']:
            return False, 'unexpected_redirect_target'
    if name == 'home_chain':
        if metrics.get('url_effective') != 'https://www.yunle.fun/' or metrics.get('num_redirects') != 1:
            return False, 'unexpected_redirect_chain'
    return True, None


def probe(spec):
    name, url, follow, expected_status = spec
    with tempfile.TemporaryDirectory(prefix='yunle-endpoint-') as directory:
        header_path = Path(directory) / 'headers'
        command = ['curl', '--disable', '--silent', '--show-error', '--user-agent', 'upptime.js.org',
                   '--connect-timeout', '30', '--max-time', '60', '--max-redirs', '3',
                   '--dump-header', str(header_path), '--output', '/dev/null',
                   '--write-out', '%{json}', url]
        if follow:
            command.append('--location')
        try:
            process = subprocess.run(command, capture_output=True, text=True, timeout=65)
            metrics = json.loads(process.stdout)
        except (subprocess.TimeoutExpired, OSError, json.JSONDecodeError) as error:
            # Exception messages may contain subprocess output; log only the type.
            return {'name': name, 'url': url, 'ok': False,
                    'failure': 'diagnostic_tool_error', 'error_type': type(error).__name__}
        headers = summarize_headers(header_path.read_text(errors='replace') if header_path.exists() else '')
        ok, failure = evaluate(spec, process.returncode, metrics, headers)
        return {'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                'name': name, 'url': url, 'follow_redirects': follow,
                'expected_status': expected_status, 'curl_exit': process.returncode,
                'ok': ok, 'failure': failure, 'headers': headers,
                **{key: metrics.get(key) for key in METRICS}}


def main():
    # Independent probes run together so the hops can be compared in one time window.
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(ENDPOINTS)) as executor:
        results = list(executor.map(probe, ENDPOINTS))
    for result in results:
        print(json.dumps(result, ensure_ascii=False), flush=True)
    return 0 if all(result['ok'] for result in results) else 1


if __name__ == '__main__':
    raise SystemExit(main())
