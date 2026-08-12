#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
SUMO路网仿真评估主程序
"""
import json
import os
import sys
import traceback

import numpy as np

from sumo.simulator import run_simulator_worker
from utils.logger import logger


class NpEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return super(NpEncoder, self).default(obj)


current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)


def main(input_json):
    try:
        input_data = json.loads(input_json)
        output = run_simulator_worker(input_data)
        return json.dumps(output, cls=NpEncoder, ensure_ascii=False)
    except Exception:
        trace = traceback.format_exc()
        logger.error('main failed\n%s', trace)
        return json.dumps({'error': 'internal_error', 'traceback': trace}, ensure_ascii=False)
