import collections
import json
import os
import sys
import time
from contextlib import contextmanager

from utils.logger import log


def is_profiling_enabled(input_data=None):
    config = input_data.get('config', {}) if isinstance(input_data, dict) else {}
    config_value = config.get('enableProfiling') if isinstance(config, dict) else None
    if config_value is not None:
        return bool(config_value)
    return os.environ.get('ENABLE_GEN_PROFILING', '0') == '1'


def new_profile_store():
    return collections.OrderedDict()


def _emit_profile_line(message):
    log.info(message)
    try:
        sys.stderr.write(f'{message}\n')
        sys.stderr.flush()
    except Exception:
        pass


@contextmanager
def profile_stage(profile_store, stage_name, enabled=False, emit_log=True):
    start = time.perf_counter()
    try:
        yield
    finally:
        if not enabled:
            return
        elapsed_ms = round((time.perf_counter() - start) * 1000, 3)
        profile_store[stage_name] = elapsed_ms
        if emit_log:
            _emit_profile_line(f'profile stage={stage_name} elapsed_ms={elapsed_ms}')


def finalize_profile_summary(summary_name, profile_store, enabled=False, extra_fields=None):
    if not enabled:
        return
    summary = collections.OrderedDict(profile_store)
    if extra_fields:
        for key, value in extra_fields.items():
            summary[key] = value
    _emit_profile_line(f'profile summary name={summary_name} data={json.dumps(summary, ensure_ascii=False)}')
