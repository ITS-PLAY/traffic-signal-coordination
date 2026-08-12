/* -*- coding: utf-8 -*-
 * codec.js — ts-generator 协议编解码层（纯函数，无 DOM 依赖，可被浏览器和 Node 复用）
 *
 * 协议要点（与后端 config/parser.py 对齐）：
 * - crossInfo[路口] = "渠化;相位组合"
 *     渠化: "方向,车道串,出口道数|..."  方向 1=北 2=东 3=南 4=西
 *           车道串每个字符=一条车道(从左到右书写)，十六进制位掩码: 8掉头 4左转 2直行 1右转
 *     相位组合: "A1636|B47|..."  相位字母 + 每2字符一组(方向,转向掩码)
 * - planInfo[路口] = "A43B27,A0"  相位时长串 + "," + 协调相位字母 + 相位差(可负)
 * - crossFlow[路口] = { "方位转向": 小时流量 }  键2位: 方位(1-4) + 转向(8/4/2/1单比特)
 * - roadSpeed = [[正向每段速度...],[反向每段速度...]]  km/h
 */
(function (root, factory) {
  if (typeof module === 'object' && module.exports) module.exports = factory();
  else root.TsCodec = factory();
})(typeof self !== 'undefined' ? self : this, function () {
  'use strict';

  var DIRS = [
    { id: 1, name: '北' },
    { id: 2, name: '东' },
    { id: 3, name: '南' },
    { id: 4, name: '西' }
  ];
  var TURN_BITS = [
    { bit: 8, code: 't', name: '掉头' },
    { bit: 4, code: 'l', name: '左转' },
    { bit: 2, code: 's', name: '直行' },
    { bit: 1, code: 'r', name: '右转' }
  ];

  function dirName(id) {
    var d = DIRS.find(function (x) { return x.id === Number(id); });
    return d ? d.name : String(id);
  }

  /* ---------- 车道/转向 ---------- */

  // 转向比特数组 -> 十六进制字符，如 [8,4] -> 'C'
  function bitsToHexChar(bits) {
    var v = 0;
    bits.forEach(function (b) { v |= Number(b); });
    return v.toString(16).toUpperCase();
  }

  // 十六进制字符 -> 转向比特数组，如 '6' -> [4,2]
  function hexCharToBits(ch) {
    var v = parseInt(ch, 16);
    if (isNaN(v)) return [];
    return TURN_BITS.filter(function (t) { return v & t.bit; }).map(function (t) { return t.bit; });
  }

  function turnNames(bits) {
    return TURN_BITS.filter(function (t) { return bits.indexOf(t.bit) >= 0; })
      .map(function (t) { return t.name; }).join('+') || '无';
  }

  /* ---------- crossInfo ---------- */

  // 结构化 -> 协议字符串
  // channel: [{dir:1, lanes:'221', out:4}], phases: [{id:'A', moves:[{dir:1,bits:[4,2]},...]}]
  function encodeCrossInfo(channel, phases) {
    var chanStr = channel.map(function (c) {
      return c.dir + ',' + (c.lanes || '') + ',' + (c.out === '' || c.out == null ? 1 : c.out);
    }).join('|');
    var phaseStr = phases.map(function (p) {
      var moves = (p.moves || []).map(function (m) {
        return String(m.dir) + bitsToHexChar(m.bits);
      }).join('');
      return p.id + moves;
    }).join('|');
    return chanStr + ';' + phaseStr;
  }

  // 协议字符串 -> 结构化
  function decodeCrossInfo(str) {
    var parts = String(str || '').split(';');
    var channel = [], phases = [];
    (parts[0] || '').split('|').forEach(function (seg) {
      if (!seg) return;
      var f = seg.split(',');
      if (f.length < 3) return;
      channel.push({ dir: Number(f[0]), lanes: f[1], out: Number(f[2]) || 0 });
    });
    (parts[1] || '').split('|').forEach(function (seg) {
      if (!seg) return;
      var id = seg[0];
      var moves = [];
      var rest = seg.slice(1);
      for (var i = 0; i + 1 < rest.length; i += 2) {
        moves.push({ dir: Number(rest[i]), bits: hexCharToBits(rest[i + 1]) });
      }
      phases.push({ id: id, moves: moves });
    });
    return { channel: channel, phases: phases };
  }

  /* ---------- planInfo ---------- */

  // 结构化 -> 协议字符串
  // durations: 按相位顺序 [{id:'A', duration:43}], coordPhase:'A', offset:0
  function encodePlanInfo(timing, coordPhase, offset) {
    var t = timing.map(function (x) { return x.id + String(x.duration); }).join('');
    var off = Number(offset) || 0;
    return t + ',' + (coordPhase || '') + String(off);
  }

  // 协议字符串 -> 结构化（同时用于输入与输出 planInfo）
  function decodePlanInfo(str) {
    var parts = String(str || '').split(',');
    var timing = [];
    var re = /([A-Za-z])(\d+)/g, m;
    while ((m = re.exec(parts[0] || '')) !== null) {
      timing.push({ id: m[1], duration: Number(m[2]) });
    }
    var coord = parts[1] || '';
    var coordPhase = coord ? coord[0] : '';
    var offset = 0;
    if (coord.length > 1) {
      var v = parseInt(coord.slice(1), 10);
      if (!isNaN(v)) offset = v;
    }
    return {
      timing: timing,
      coordPhase: coordPhase,
      offset: offset,
      cycle: timing.reduce(function (s, x) { return s + x.duration; }, 0)
    };
  }

  /* ---------- 整体负载 ---------- */

  // 后端期望的 roadSpeed 二维列表: [[正向...],[反向...]]
  function encodeRoadSpeed(forward, backward) {
    return [forward.map(Number), backward.map(Number)];
  }

  function decodeRoadSpeed(rs) {
    // 兼容两种理解: [[fwd每段],[bwd每段]]（协议约定）
    var forward = Array.isArray(rs[0]) ? rs[0].map(Number) : [];
    var backward = Array.isArray(rs[1]) ? rs[1].map(Number) : [];
    return { forward: forward, backward: backward };
  }

  // 完整输入 JSON -> 编辑状态
  function inputToState(input) {
    var state = {
      crossList: (input.crossList || []).slice(),
      roadLength: (input.roadLength || []).map(Number),
      roadSpeed: decodeRoadSpeed(input.roadSpeed || []),
      crosses: {},
      config: Object.assign({
        outbound: true, inbound: true, onlyEvaluation: false,
        mode: 'best', iterationNum: 20
      }, input.config || {})
    };
    state.crossList.forEach(function (cid) {
      var ci = decodeCrossInfo((input.crossInfo || {})[cid]);
      var pi = decodePlanInfo((input.planInfo || {})[cid]);
      // 相位时长以 planInfo 为准；相位结构以 crossInfo 为准，做并集
      var durations = {};
      pi.timing.forEach(function (t) { durations[t.id] = t.duration; });
      var flowObj = (input.crossFlow || {})[cid] || {};
      var flows = Object.keys(flowObj).map(function (k) {
        return { dir: Number(k[0]), bit: Number(k.slice(1)), flow: Number(flowObj[k]) };
      });
      state.crosses[cid] = {
        channel: ci.channel,
        phases: ci.phases,
        // 相位执行顺序以 planInfo 为准（crossInfo 中相位组合的书写顺序不代表执行顺序）
        phaseOrder: pi.timing.map(function (t) { return t.id; }),
        durations: durations,
        coordPhase: pi.coordPhase,
        offset: pi.offset,
        flows: flows
      };
    });
    return state;
  }

  // 编辑状态 -> 完整请求负载的 in 字段
  function stateToInput(state) {
    var crossInfo = {}, planInfo = {}, crossFlow = {};
    state.crossList.forEach(function (cid) {
      var c = state.crosses[cid];
      crossInfo[cid] = encodeCrossInfo(c.channel, c.phases);
      var phaseIds = c.phases.map(function (p) { return p.id; });
      // 相位执行顺序：优先 planInfo 原顺序，新增的相位排在末尾
      var order = (c.phaseOrder || []).filter(function (id) { return phaseIds.indexOf(id) >= 0; });
      phaseIds.forEach(function (id) { if (order.indexOf(id) < 0) order.push(id); });
      var timing = order.map(function (id) {
        return { id: id, duration: Number(c.durations[id]) || 0 };
      });
      planInfo[cid] = encodePlanInfo(timing, c.coordPhase, c.offset);
      var f = {};
      (c.flows || []).forEach(function (row) {
        if (!row.dir || !row.bit) return;
        f[String(row.dir) + String(row.bit)] = Number(row.flow) || 0;
      });
      crossFlow[cid] = f;
    });
    return {
      crossList: state.crossList.slice(),
      roadLength: state.roadLength.map(Number),
      crossInfo: crossInfo,
      planInfo: planInfo,
      roadSpeed: encodeRoadSpeed(state.roadSpeed.forward, state.roadSpeed.backward),
      crossFlow: crossFlow,
      config: state.config
    };
  }

  /* ---------- 时距图数据 ---------- */

  // 由输出 planInfo 计算每个路口的协调相位绿信窗口
  // 返回 [{cross, cycle, coordPhase, offset, phaseStart, greenDur, relOffset}]
  //
  // 重要：planInfo 中存储的是**相对相位差**——相邻两个路口**协调相位绿窗起点**之间的时间差。
  // 时距图需要**绝对相位差**——每个路口的 offset 使得 offset + phaseStart = 绿窗绝对起点。
  //
  // 当相邻路口的协调相位不同（如 C1 协调 A 相位、C2 协调 B 相位）时，
  // 各路口的 phaseStart 不同，直接累加 rel 值会导致绿窗起点错位。
  // 正确做法：先累加绿窗绝对起点，再减去各自的 phaseStart。
  //
  // 转换公式：
  //   gs[0] = rel[0] + phaseStart[0]           （第一个路口的绿窗起点）
  //   gs[k] = gs[k-1] + rel[k]                  （累加绿窗起点）
  //   abs_offset[k] = gs[k] - phaseStart[k]     （减去自身协调相位起始，得绝对 offset）
  //   绿信绝对窗口: [abs_offset + phaseStart + m*cycle, +greenDur]
  function greenWindows(crossList, outPlanInfo) {
    var decoded = crossList.map(function (cid) {
      var pi = decodePlanInfo(outPlanInfo[cid]);
      var phaseStart = 0;
      for (var i = 0; i < pi.timing.length; i++) {
        if (pi.timing[i].id === pi.coordPhase) break;
        phaseStart += pi.timing[i].duration;
      }
      var coord = pi.timing.find(function (t) { return t.id === pi.coordPhase; });
      return {
        cross: cid,
        cycle: pi.cycle,
        coordPhase: pi.coordPhase,
        offset: pi.offset,   // 原始值（相对相位差）
        phaseStart: phaseStart,
        greenDur: coord ? coord.duration : 0,
        timing: pi.timing
      };
    });
    // 相对相位差 → 绝对相位差（先累加绿窗起点，再减去各自 phaseStart）
    var gs = 0;  // 绿窗绝对起点（green window absolute start）
    decoded.forEach(function (g, i) {
      var c = g.cycle || 1;
      if (i === 0) {
        gs = g.offset + g.phaseStart;    // 第一个路口：绿窗起点 = offset + phaseStart
      } else {
        gs = gs + g.offset;              // 累加相对相位差到绿窗起点
      }
      gs = ((gs % c) + c) % c;          // 归一化到 [0, cycle)
      g.relOffset = g.offset;            // 保留原始相对相位差
      g.offset = ((gs - g.phaseStart) % c + c) % c;  // 绝对 offset = 绿窗起点 - phaseStart
    });
    return decoded;
  }

  /* ---------- 绿波带宽 ---------- */

  // 某时刻 t 是否处于该路口协调相位绿灯内（绿窗起点 = offset + phaseStart，周期回绕）
  function isGreenAt(t, g) {
    if (!g.greenDur || !g.cycle) return false;
    var rel = (((t - (g.offset + g.phaseStart)) % g.cycle) + g.cycle) % g.cycle;
    return rel < g.greenDur;
  }

  // 计算从路口 gi 到 gj、行程时间 tau 秒时的最大绿波带：
  // 出发时刻 t 需满足 t 在 gi 绿灯内 且 t+tau 在 gj 绿灯内，
  // 在一个公共周期内找最长连续可通过区间（环形处理）。
  // 返回 { start, len, cycle }（start/len 单位秒），无绿窗时返回 null。
  function computeBand(gi, gj, tau) {
    var C = Math.max(gi.cycle, gj.cycle);
    if (!gi.greenDur || !gj.greenDur || !C) return null;
    var step = 0.2;
    var N = Math.max(1, Math.round(C / step));
    var arr = [];
    for (var k = 0; k < N; k++) {
      arr.push(isGreenAt(k * step, gi) && isGreenAt(k * step + tau, gj));
    }
    var falseIdx = arr.indexOf(false);
    if (falseIdx === -1) return { start: 0, len: C, cycle: C }; // 全周期可通过
    var bestLen = 0, bestStart = 0, curLen = 0, curStart = 0;
    for (var k2 = 1; k2 <= N; k2++) {
      var idx = (falseIdx + k2) % N;
      if (arr[idx]) {
        if (curLen === 0) curStart = idx;
        curLen++;
        if (curLen > bestLen) { bestLen = curLen; bestStart = curStart; }
      } else {
        curLen = 0;
      }
    }
    if (bestLen === 0) return { start: 0, len: 0, cycle: C };
    return { start: bestStart * step, len: bestLen * step, cycle: C };
  }

  return {
    DIRS: DIRS,
    TURN_BITS: TURN_BITS,
    dirName: dirName,
    bitsToHexChar: bitsToHexChar,
    hexCharToBits: hexCharToBits,
    turnNames: turnNames,
    encodeCrossInfo: encodeCrossInfo,
    decodeCrossInfo: decodeCrossInfo,
    encodePlanInfo: encodePlanInfo,
    decodePlanInfo: decodePlanInfo,
    encodeRoadSpeed: encodeRoadSpeed,
    decodeRoadSpeed: decodeRoadSpeed,
    inputToState: inputToState,
    stateToInput: stateToInput,
    greenWindows: greenWindows,
    isGreenAt: isGreenAt,
    computeBand: computeBand
  };
});
