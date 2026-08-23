import os
import shutil
import subprocess
import time
from datetime import datetime, timezone

_CACHE_TTL_S = 15.0
_cache = {'at': 0.0, 'payload': None}

QUERY_FIELDS = (
    'index',
    'name',
    'uuid',
    'utilization.gpu',
    'utilization.memory',
    'memory.used',
    'memory.total',
    'temperature.gpu',
    'power.draw',
    'power.limit',
    'fan.speed',
    'clocks.current.graphics',
    'clocks.current.memory',
    'pstate',
    'pcie.link.gen.current',
    'pcie.link.width.current',
)


def _parse_number(value):
    if value is None:
        return None
    text = str(value).strip()
    if not text or text in {'[N/A]', 'N/A', '-', 'Not Specified'}:
        return None
    text = text.replace('W', '').replace('MHz', '').replace('%', '').replace('MiB', '').replace('C', '')
    try:
        if '.' in text:
            return float(text)
        return int(text)
    except ValueError:
        try:
            return float(text)
        except ValueError:
            return None


def _chungus_devices():
    """Physical GPU indices/UUIDs Chungus may use (CUDA_VISIBLE_DEVICES)."""
    raw = (os.environ.get('CUDA_VISIBLE_DEVICES') or '').strip()
    if not raw:
        return None, raw
    claimed = set()
    for part in raw.split(','):
        token = part.strip()
        if not token:
            continue
        claimed.add(token)
        if token.isdigit():
            claimed.add(int(token))
    return claimed, raw


def _is_chungus(gpu, claimed):
    if not claimed:
        return True
    index = gpu.get('index')
    uuid = gpu.get('uuid')
    return index in claimed or str(index) in claimed or uuid in claimed


def _collect_gpus():
    smi = shutil.which('nvidia-smi')
    if not smi:
        return {
            'available': False,
            'error': 'nvidia-smi not found',
            'gpus': [],
            'collected_at': datetime.now(timezone.utc).isoformat(),
        }

    query = ','.join(QUERY_FIELDS)
    try:
        raw = subprocess.check_output(
            [smi, f'--query-gpu={query}', '--format=csv,noheader,nounits'],
            text=True,
            timeout=3,
            stderr=subprocess.DEVNULL,
        )
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError) as exc:
        return {
            'available': False,
            'error': str(exc).strip() or 'nvidia-smi failed',
            'gpus': [],
            'collected_at': datetime.now(timezone.utc).isoformat(),
        }

    claimed, cuda_visible = _chungus_devices()
    gpus = []
    for line in raw.splitlines():
        if not line.strip():
            continue
        parts = [part.strip() for part in line.split(',')]
        if len(parts) < 13:
            continue
        index = _parse_number(parts[0])
        used = _parse_number(parts[5])
        total = _parse_number(parts[6])
        mem_pct = None
        if used is not None and total:
            mem_pct = round((float(used) / float(total)) * 100, 1)
        gpus.append({
            'index': index,
            'name': parts[1],
            'uuid': parts[2],
            'utilization_gpu': _parse_number(parts[3]),
            'utilization_memory': _parse_number(parts[4]),
            'memory_used_mb': used,
            'memory_total_mb': total,
            'memory_pct': mem_pct,
            'temperature_c': _parse_number(parts[7]),
            'power_draw_w': _parse_number(parts[8]),
            'power_limit_w': _parse_number(parts[9]),
            'fan_speed_pct': _parse_number(parts[10]),
            'clock_graphics_mhz': _parse_number(parts[11]),
            'clock_memory_mhz': _parse_number(parts[12]),
            'pstate': parts[13] if len(parts) > 13 else None,
            'pcie_gen': _parse_number(parts[14]) if len(parts) > 14 else None,
            'pcie_width': _parse_number(parts[15]) if len(parts) > 15 else None,
            'voltage_mv': None,
        })
        gpus[-1]['in_use'] = _is_chungus(gpus[-1], claimed)

    return {
        'available': bool(gpus),
        'error': None if gpus else 'no GPUs reported',
        'gpus': gpus,
        'cuda_visible_devices': cuda_visible or None,
        'collected_at': datetime.now(timezone.utc).isoformat(),
    }


def gpu_status():
    now = time.monotonic()
    if _cache['payload'] is not None and (now - _cache['at']) < _CACHE_TTL_S:
        return _cache['payload']
    payload = _collect_gpus()
    _cache['at'] = now
    _cache['payload'] = payload
    return payload
