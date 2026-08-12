/* -*- coding: utf-8 -*-
 * sketch.js — 路口示意图渲染（SVG）
 *
 *  1. drawChannel  渠化图：沥青路面、分道线、绿色中心线、停止线、斑马线、路面转向箭头、出口道数
 *  2. drawPhase    相位图：每相位一个小路口图（浅绿底+深灰路面+白色控制转向箭头）+ 相位时间轴
 *  3. drawFlow     流量图：各转向彩色粗箭头（路端到路端，粗细∝流量）+ 箭身流量标签 + 出口端总量标签
 *
 * 约定：右行规则。方向 1=北(上) 2=东(右) 3=南(下) 4=西(左)，进口在行进方向右侧。
 * 几何由"北进口"模板绕中心顺时针旋转 90°*(dir-1) 生成；路面按 进口/出口车道数 非对称计算半宽。
 */
(function (root, factory) {
  if (typeof module === 'object' && module.exports) module.exports = factory();
  else root.TsSketch = factory();
})(typeof self !== 'undefined' ? self : this, function () {
  'use strict';

  var SVGNS = 'http://www.w3.org/2000/svg';
  var LEG_NAME = { 1: '方向1·北', 2: '方向2·东', 3: '方向3·南', 4: '方向4·西' };
  var BIT2CODE = { 8: 't', 4: 'l', 2: 's', 1: 'r' };
  var PHASE_COLORS = ['#16a34a', '#ea580c', '#7c3aed', '#2563eb', '#db2777', '#0891b2', '#65a30d', '#b45309'];
  var FLOW_COLORS = ['#7c3aed', '#dc2626', '#ea580c', '#16a34a', '#2563eb', '#0891b2', '#db2777',
                     '#65a30d', '#b45309', '#4f46e5', '#0d9488', '#c026d3', '#ca8a04', '#475569'];
  /* 进口车道横向偏移（北进口模板；负=靠外侧路缘，数值越小越靠外）。
     内侧→外侧：掉头 -6，左转 -14，直行 -24，右转 -33（右行规则：右转车道最外侧）。 */
  var ENTRY_OFF = { t: -6, l: -14, s: -24, r: -33 };

  function el(name, attrs) {
    var e = document.createElementNS(SVGNS, name);
    for (var k in attrs) e.setAttribute(k, attrs[k]);
    return e;
  }
  function txt(svg, x, y, str, opt) {
    opt = opt || {};
    var t = el('text', {
      x: x, y: y, 'font-size': opt.size || 12, fill: opt.fill || '#475569',
      'text-anchor': opt.anchor || 'middle', 'font-weight': opt.bold ? 700 : 400
    });
    t.textContent = str;
    svg.appendChild(t);
    return t;
  }
  /* 文本宽度粗估：CJK≈size，其余≈0.58size */
  function textW(str, size) {
    var w = 0;
    String(str).split('').forEach(function (ch) { w += /[\u2e80-\u9fff]/.test(ch) ? size : size * 0.58; });
    return w;
  }
  /* 胶囊标签（默认白底彩边，可指定深色底） */
  function pill(svg, x, y, str, opt) {
    opt = opt || {};
    var size = opt.size || 12;
    var w = textW(str, size) + 12, h = size + 8;
    var attrs = { x: x - w / 2, y: y - h / 2, width: w, height: h, rx: 4,
                  fill: opt.bg || '#ffffff', 'fill-opacity': opt.bgOpacity == null ? 0.94 : opt.bgOpacity };
    if (opt.noStroke) attrs.stroke = 'none';
    else { attrs.stroke = opt.color || '#64748b'; attrs['stroke-width'] = 1.4; }
    svg.appendChild(el('rect', attrs));
    txt(svg, x, y + size * 0.34, str, { size: size, fill: opt.textColor || opt.color || '#1e293b', bold: true });
    return [w, h];
  }
  function rot(cx, cy, p, k) {
    var x = p[0], y = p[1];
    for (var i = 0; i < k; i++) { var dx = x - cx, dy = y - cy; x = cx - dy; y = cy + dx; }
    return [x, y];
  }
  function poly(svg, pts, attrs) {
    attrs.points = pts.map(function (p) { return p[0].toFixed(1) + ',' + p[1].toFixed(1); }).join(' ');
    svg.appendChild(el('polygon', attrs));
  }

  /* ============ 通用运动轨迹几何（支持路端延伸与圆弧） ============
   * 返回 { d, tip, prev, mid, start }：tip/prev 定箭头方向，mid 为标签锚点 */
  function moveGeom(box, dir, bit, extIn, extOut) {
    var cx = box.cx, cy = box.cy, hx = box.hx, hy = box.hy;
    var c = Math.min(hx, hy);
    var sc = c / 64;
    var code = BIT2CODE[bit];
    var ein = ENTRY_OFF[code] * sc;
    if (extIn == null) extIn = hy;
    if (extOut == null) extOut = hy;
    var tpl, tipT, prevT, midT;
    if (code === 's') {
      tpl = [{ op: 'M', pts: [[cx + ein, cy - extIn]] },
             { op: 'L', pts: [[cx + ein, cy + extOut]] }];
      tipT = [cx + ein, cy + extOut]; prevT = [cx + ein, cy + extOut - 10]; midT = [cx + ein, cy];
    } else if (code === 'l') {
      /* 左转：绕"入口侧远角"的四分之一圆弧（弧心在北进口模板的路口东北角），
         不同进口的左转弧位于不同象限，避免多股左转在中心打结 */
      var rA = hx - ein; // ein<0 → hx+|ein|
      tpl = [{ op: 'M', pts: [[cx + ein, cy - extIn]] },
             { op: 'L', pts: [[cx + ein, cy - hy]] },
             { op: 'A', r: rA, sweep: 0, pts: [[cx + hx, cy - ein]] },
             { op: 'L', pts: [[cx + extOut, cy - ein]] }];
      tipT = [cx + extOut, cy - ein]; prevT = [cx + extOut - 10, cy - ein];
      midT = [cx + hx - rA * 0.7071, cy - hy + rA * 0.7071];
    } else if (code === 'r') {
      tpl = [{ op: 'M', pts: [[cx + ein, cy - extIn]] },
             { op: 'L', pts: [[cx + ein, cy - hy]] },
             { op: 'Q', pts: [[cx - hx + c * 0.32, cy - hy + c * 0.32], [cx - hx, cy + ein]] },
             { op: 'L', pts: [[cx - extOut, cy + ein]] }];
      tipT = [cx - extOut, cy + ein]; prevT = [cx - extOut + 10, cy + ein];
      midT = [0.25 * (cx + ein) + 0.5 * (cx - hx + c * 0.32) + 0.25 * (cx - hx),
              0.25 * (cy - hy) + 0.5 * (cy - hy + c * 0.32) + 0.25 * (cy + ein)];
    } else { /* t 掉头 */
      tpl = [{ op: 'M', pts: [[cx + ein, cy - extIn]] },
             { op: 'L', pts: [[cx + ein, cy - c * 0.1]] },
             { op: 'C', pts: [[cx + ein, cy + c * 0.5], [cx - ein, cy + c * 0.5], [cx - ein, cy - c * 0.1]] },
             { op: 'L', pts: [[cx - ein, cy - extOut]] }];
      tipT = [cx - ein, cy - extOut]; prevT = [cx - ein, cy - extOut + 10]; midT = [cx, cy + c * 0.45];
    }
    var k = dir - 1, R = function (p) { return rot(cx, cy, p, k); };
    var d = '', start = null;
    tpl.forEach(function (seg, si) {
      var rp = seg.pts.map(R);
      if (seg.op === 'A') {
        d += ' A' + seg.r.toFixed(1) + ' ' + seg.r.toFixed(1) + ' 0 0 ' + seg.sweep + ' ' +
             rp[0][0].toFixed(1) + ',' + rp[0][1].toFixed(1);
      } else {
        d += (si === 0 ? '' : ' ') + seg.op +
             rp.map(function (p) { return p[0].toFixed(1) + ',' + p[1].toFixed(1); }).join(' ');
      }
      if (si === 0) start = rp[0];
    });
    return { d: d, tip: R(tipT), prev: R(prevT), mid: R(midT), start: start };
  }

  function arrowHead(svg, tip, prev, color, size, opacity) {
    var vx = tip[0] - prev[0], vy = tip[1] - prev[1];
    var vl = Math.hypot(vx, vy) || 1; vx /= vl; vy /= vl;
    var s = size || 11;
    var bx = tip[0] - vx * s, by = tip[1] - vy * s;
    poly(svg, [tip, [bx - vy * s * 0.42, by + vx * s * 0.42], [bx + vy * s * 0.42, by - vx * s * 0.42]],
         { fill: color, 'fill-opacity': opacity == null ? 1 : opacity });
  }

  function exitDirOf(dir, bit) {
    var code = BIT2CODE[bit];
    if (code === 't') return dir;
    if (code === 's') return { 1: 3, 2: 4, 3: 1, 4: 2 }[dir];
    if (code === 'l') return { 1: 2, 2: 3, 3: 4, 4: 1 }[dir];
    return { 1: 4, 2: 1, 3: 2, 4: 3 }[dir];
  }

  /* ================= 1. 渠化图 ================= */
  function drawChannel(svg, c) {
    svg.innerHTML = '';
    svg.setAttribute('viewBox', '0 0 560 560');
    var cx = 280, cy = 280, W = 24, EDGE = 185;
    var ASPH = '#8f8f8f';

    var info = {};
    (c.channel || []).forEach(function (row) {
      var lanes = String(row.lanes || '');
      info[row.dir] = { lanes: lanes === '0' ? '' : lanes, out: Number(row.out) || 0 };
    });
    var dirs = [1, 2, 3, 4].filter(function (d) { return !!info[d]; });
    if (!dirs.length) { txt(svg, cx, cy, '暂无渠化数据', { size: 14, fill: '#94a3b8' }); return; }
    function entryN(d) { return info[d] ? info[d].lanes.length : 0; }
    function exitN(d) { return info[d] ? info[d].out : 0; }

    /* 非对称半宽：竖路西/东侧 = 北进口/南出口、北出口/南进口；
       横路北/南侧 = 东进口/西出口、东出口/西进口 */
    var westX = Math.max(entryN(1), exitN(3)) * W;
    var eastX = Math.max(exitN(1), entryN(3)) * W;
    var northY = Math.max(entryN(2), exitN(4)) * W;
    var southY = Math.max(exitN(2), entryN(4)) * W;
    westX = Math.max(westX, W); eastX = Math.max(eastX, W);
    northY = Math.max(northY, W); southY = Math.max(southY, W);
    var edgeOf = { 1: northY, 3: southY, 2: eastX, 4: westX }; // 各方向盒边距中心距离

    // 中心盒
    svg.appendChild(el('rect', { x: cx - westX, y: cy - northY, width: westX + eastX, height: northY + southY, fill: ASPH }));
    // 路腿（只画存在的方向）
    dirs.forEach(function (d) {
      var r;
      if (d === 1) r = { x: cx - entryN(1) * W, y: cy - EDGE, width: (entryN(1) + exitN(1)) * W, height: EDGE - northY };
      if (d === 3) r = { x: cx - exitN(3) * W, y: cy + southY, width: (exitN(3) + entryN(3)) * W, height: EDGE - southY };
      if (d === 2) r = { x: cx + eastX, y: cy - entryN(2) * W, width: EDGE - eastX, height: (entryN(2) + exitN(2)) * W };
      if (d === 4) r = { x: cx - EDGE, y: cy - exitN(4) * W, width: EDGE - westX, height: (exitN(4) + entryN(4)) * W };
      r.fill = ASPH;
      svg.appendChild(el('rect', r));
    });
    // 绿色中心线
    dirs.forEach(function (d) {
      var k = d - 1;
      var p1 = rot(cx, cy, [cx, cy - EDGE], k), p2 = rot(cx, cy, [cx, cy - edgeOf[d]], k);
      svg.appendChild(el('line', { x1: p1[0], y1: p1[1], x2: p2[0], y2: p2[1], stroke: '#22c55e', 'stroke-width': 3 }));
    });

    // 每条腿的细节
    dirs.forEach(function (d) {
      var k = d - 1;
      var R = function (p) { return rot(cx, cy, p, k); };
      var nE = entryN(d), nX = exitN(d), j;
      var eD = edgeOf[d];

      // 进口分道虚线
      for (j = 1; j < nE; j++) {
        var a1 = R([cx - j * W, cy - EDGE]), a2 = R([cx - j * W, cy - eD - 22]);
        svg.appendChild(el('line', { x1: a1[0], y1: a1[1], x2: a2[0], y2: a2[1], stroke: '#fff', 'stroke-width': 2, 'stroke-dasharray': '10 8' }));
      }
      // 进口外边缘实线
      if (nE > 0) {
        var e1 = R([cx - nE * W, cy - EDGE]), e2 = R([cx - nE * W, cy - eD]);
        svg.appendChild(el('line', { x1: e1[0], y1: e1[1], x2: e2[0], y2: e2[1], stroke: '#fff', 'stroke-width': 2.5 }));
      }
      // 停止线（仅进口侧）
      if (nE > 0) {
        var s1 = R([cx - nE * W, cy - eD]), s2 = R([cx, cy - eD]);
        svg.appendChild(el('line', { x1: s1[0], y1: s1[1], x2: s2[0], y2: s2[1], stroke: '#fff', 'stroke-width': 4 }));
      }
      // 斑马线（整腿宽，盒边外侧）
      var span = (nE + nX) * W;
      var stripes = Math.max(2, Math.floor((span - 8) / 10));
      for (var s = 0; s < stripes; s++) {
        var sx = cx - nE * W + 4 + s * 10;
        if (sx + 4 > cx + nX * W - 2) break;
        poly(svg, [R([sx, cy - eD - 17]), R([sx, cy - eD - 4]), R([sx + 4, cy - eD - 4]), R([sx + 4, cy - eD - 17])], { fill: '#f8fafc' });
      }
      // 出口分道虚线 + 外边缘
      for (j = 1; j < nX; j++) {
        var x1 = R([cx + j * W, cy - EDGE]), x2 = R([cx + j * W, cy - eD - 22]);
        svg.appendChild(el('line', { x1: x1[0], y1: x1[1], x2: x2[0], y2: x2[1], stroke: '#fff', 'stroke-width': 2, 'stroke-dasharray': '10 8' }));
      }
      if (nX > 0) {
        var o1 = R([cx + nX * W, cy - EDGE]), o2 = R([cx + nX * W, cy - eD]);
        svg.appendChild(el('line', { x1: o1[0], y1: o1[1], x2: o2[0], y2: o2[1], stroke: '#fff', 'stroke-width': 2.5 }));
      }
      // 路面转向箭头
      for (j = 0; j < nE; j++) {
        var bits = TsCodec.hexCharToBits(info[d].lanes[j]);
        if (bits.length) drawLaneGlyph(svg, R([cx - j * W - W / 2, cy - eD - 60]), bits, HEADING_DEG[d]);
      }
      // 出口道数标注（深色胶囊，避免压线难读）
      if (nX > 0) {
        var lp;
        if (d === 1) lp = [cx + nX * W / 2, cy - (EDGE + eD) / 2];
        if (d === 3) lp = [cx - nX * W / 2, cy + (EDGE + eD) / 2];
        if (d === 2) lp = [cx + (EDGE + eD) / 2, cy + nX * W / 2];
        if (d === 4) lp = [cx - (EDGE + eD) / 2, cy - nX * W / 2];
        pill(svg, lp[0], lp[1], '出口×' + nX, { size: 12, bg: '#334155', bgOpacity: 0.82, noStroke: true, textColor: '#ffffff' });
      }
      // 方向标签（路端外侧）
      var np = R([cx, cy - EDGE - 20]);
      txt(svg, np[0], np[1], LEG_NAME[d], { size: 15, fill: '#334155', bold: true });
    });
  }

  var HEADING_DEG = { 1: 180, 2: 270, 3: 0, 4: 90 };
  var GLYPH = {
    s: 'M0,15 L0,-11 M-5,-5 L0,-12 L5,-5',
    l: 'M1,15 L1,-2 Q1,-9 -6,-9 L-11,-9 M-6,-14 L-12,-9 L-6,-4',
    r: 'M-1,15 L-1,-2 Q-1,-9 6,-9 L11,-9 M6,-14 L12,-9 L6,-4',
    t: 'M-4,15 L-4,-3 Q-4,-10 3,-10 Q10,-10 10,-3 L10,6 M5,1 L10,7 L15,1'
  };
  function drawLaneGlyph(svg, center, bits, deg) {
    var n = bits.length;
    bits.forEach(function (bit, bi) {
      var off = (bi - (n - 1) / 2) * 12;
      var g = el('g', { transform: 'translate(' + center[0] + ',' + center[1] + ') rotate(' + deg + ') translate(' + off + ',0)' + (n > 1 ? ' scale(0.78)' : ' scale(1)') });
      g.appendChild(el('path', { d: GLYPH[BIT2CODE[bit]], fill: 'none', stroke: '#ffffff',
                                 'stroke-width': 3.6, 'stroke-linecap': 'round', 'stroke-linejoin': 'round' }));
      svg.appendChild(g);
    });
  }

  /* ================= 2. 相位图 ================= */
  function drawPhase(svg, c, soloId) {
    svg.innerHTML = '';
    var order = (c.phaseOrder || []).filter(function (id) { return c.phases.some(function (p) { return p.id === id; }); });
    var P = order.length;
    if (!P) return;
    var TW = 132, TH = 132, GAP = 14, TOP = 8, LABELH = 26, BARH = 56;
    var W = P * (TW + GAP) - GAP + 16;
    var H = TOP + TH + LABELH + BARH + 12;
    svg.setAttribute('viewBox', '0 0 ' + W + ' ' + H);

    /* 只画实际存在的进口臂（支持 T 型/十字/路段中间口） */
    var used = { 1: false, 2: false, 3: false, 4: false };
    (c.channel || []).forEach(function (r) { if (String(r.lanes || '').length > 0 || Number(r.out) > 0) used[r.dir] = true; });
    c.phases.forEach(function (p) { (p.moves || []).forEach(function (m) { if (m.bits && m.bits.length) used[m.dir] = true; }); });

    var cycle = order.reduce(function (s, id) { return s + (Number(c.durations[id]) || 0); }, 0);

    order.forEach(function (pid, pi) {
      var ph = c.phases.find(function (p) { return p.id === pid; });
      var color = PHASE_COLORS[pi % PHASE_COLORS.length];
      var x0 = 8 + pi * (TW + GAP), y0 = TOP;
      var dim = soloId && soloId !== pid;
      var g = el('g', { opacity: dim ? 0.25 : 1 });
      g.appendChild(el('rect', { x: x0, y: y0, width: TW, height: TH, rx: 6,
                                 fill: '#e9f7d9', stroke: pid === c.coordPhase ? '#ea580c' : '#cbd5e1',
                                 'stroke-width': pid === c.coordPhase ? 3 : 1 }));
      var mcx = x0 + TW / 2, mcy = y0 + TH / 2, rw = 21;
      var arms = {
        1: { x: mcx - rw, y: y0 + 4, width: rw * 2, height: mcy - y0 - 4 },
        3: { x: mcx - rw, y: mcy, width: rw * 2, height: y0 + TH - 4 - mcy },
        4: { x: x0 + 4, y: mcy - rw, width: mcx - x0 - 4, height: rw * 2 },
        2: { x: mcx, y: mcy - rw, width: x0 + TW - 4 - mcx, height: rw * 2 }
      };
      [1, 2, 3, 4].forEach(function (d) { if (used[d]) { var r = arms[d]; r.fill = '#666666'; g.appendChild(el('rect', r)); } });
      [[mcx - rw, mcy - rw], [mcx + rw, mcy - rw], [mcx - rw, mcy + rw], [mcx + rw, mcy + rw]].forEach(function (cn) {
        g.appendChild(el('circle', { cx: cn[0], cy: cn[1], r: 9, fill: '#e9f7d9' }));
      });
      var box = { cx: mcx, cy: mcy, hx: rw, hy: rw };
      (ph.moves || []).forEach(function (mv) {
        mv.bits.forEach(function (bit) {
          var geo = moveGeom(box, mv.dir, bit);
          g.appendChild(el('path', { d: geo.d, fill: 'none', stroke: '#ffffff', 'stroke-width': 3.4,
                                     'stroke-linecap': 'round', 'stroke-opacity': 0.95 }));
          arrowHead(g, geo.tip, geo.prev, '#ffffff', 9, 0.95);
        });
      });
      var dur = Number(c.durations[pid]) || 0;
      var capT = el('text', { x: mcx, y: y0 + TH + 17, 'font-size': 13, 'text-anchor': 'middle',
                              fill: pid === c.coordPhase ? '#ea580c' : '#334155',
                              'font-weight': pid === c.coordPhase ? 700 : 400 });
      capT.textContent = '第' + pid + '相位：' + dur + '秒' + (pid === c.coordPhase ? '（协调）' : '');
      g.appendChild(capT);
      svg.appendChild(g);
    });

    // 相位时间轴
    var barX = 8, barW = W - 16, barY = TOP + TH + LABELH + 12, barH = 16;
    var total = cycle + 3 * P;
    var scale = barW / total;
    svg.appendChild(el('rect', { x: barX, y: barY, width: barW, height: barH, fill: '#dc2626', rx: 3 }));
    var acc = 0;
    order.forEach(function (pid, pi) {
      var dur = Number(c.durations[pid]) || 0;
      svg.appendChild(el('rect', { x: barX + acc * scale, y: barY, width: dur * scale, height: barH,
                                   fill: PHASE_COLORS[pi % PHASE_COLORS.length] }));
      txt(svg, barX + (acc + dur / 2) * scale, barY + 12, pid + ' ' + dur + 's', { size: 11, fill: '#fff', bold: true });
      acc += dur;
      svg.appendChild(el('rect', { x: barX + acc * scale, y: barY, width: 3 * scale, height: barH, fill: '#eab308' }));
      acc += 3;
    });
    txt(svg, barX, barY + barH + 15, '公共周期 ' + cycle + ' 秒（每相位后含 3s 黄灯清空）', { size: 11, fill: '#64748b', anchor: 'start' });
  }

  /* ================= 3. 流量图 ================= */
  function drawFlow(svg, c) {
    svg.innerHTML = '';
    svg.setAttribute('viewBox', '0 0 640 640');
    var cx = 320, cy = 320, hx = 80, hy = 80, EDGE = 190;

    var agg = {}, order = [];
    (c.flows || []).forEach(function (f) {
      if (!f.dir || !f.bit) return;
      var key = f.dir + '|' + f.bit;
      if (!(key in agg)) order.push(key);
      agg[key] = (agg[key] || 0) + (Number(f.flow) || 0);
    });

    /* 路网底：只画有渠化或有流量进出的腿（支持 T 型/直线路口） */
    var legs = { 1: false, 2: false, 3: false, 4: false };
    (c.channel || []).forEach(function (r) { if (String(r.lanes || '').length > 0 || Number(r.out) > 0) legs[r.dir] = true; });
    order.forEach(function (key) {
      var p = key.split('|'), dir = Number(p[0]), bit = Number(p[1]);
      legs[dir] = true; legs[exitDirOf(dir, bit)] = true;
    });
    var ROAD = '#eef2f7', RBORDER = '#d7e0ea';
    if (legs[1] || legs[3]) {
      var yTop = legs[1] ? cy - EDGE : cy, yBot = legs[3] ? cy + EDGE : cy;
      svg.appendChild(el('rect', { x: cx - hx, y: yTop, width: 2 * hx, height: yBot - yTop, fill: ROAD, stroke: RBORDER }));
    }
    if (legs[4] || legs[2]) {
      var xL = legs[4] ? cx - EDGE : cx, xR = legs[2] ? cx + EDGE : cx;
      svg.appendChild(el('rect', { x: xL, y: cy - hy, width: xR - xL, height: 2 * hy, fill: ROAD, stroke: RBORDER }));
    }
    if (!order.length) { txt(svg, cx, cy, '暂无流量数据', { size: 14, fill: '#94a3b8' }); return; }

    var maxFlow = Math.max.apply(null, order.map(function (k) { return agg[k]; }).concat([1]));
    var box = { cx: cx, cy: cy, hx: hx, hy: hy };
    var exitTotals = { 1: 0, 2: 0, 3: 0, 4: 0 };
    var pillsTodo = [];

    /* 第一遍：箭头 */
    order.forEach(function (key, i) {
      var parts = key.split('|'), dir = Number(parts[0]), bit = Number(parts[1]);
      var flow = agg[key];
      var color = FLOW_COLORS[i % FLOW_COLORS.length];
      var w = 5 + 13 * (flow / maxFlow);
      var geo = moveGeom(box, dir, bit, EDGE, EDGE);
      svg.appendChild(el('path', { d: geo.d, fill: 'none', stroke: color, 'stroke-width': w.toFixed(1),
                                   'stroke-opacity': 0.78, 'stroke-linecap': 'round' }));
      arrowHead(svg, geo.tip, geo.prev, color, 8 + w * 0.55, 0.9);
      exitTotals[exitDirOf(dir, bit)] += flow;
      pillsTodo.push({ mid: geo.mid, flow: flow, color: color });
    });

    /* 第二遍：箭身流量标签（白底彩边胶囊，重叠时自动错位） */
    var placed = [];
    pillsTodo.forEach(function (it) {
      var x = it.mid[0], y = it.mid[1];
      for (var t = 0; t < 5; t++) {
        var clash = placed.some(function (p) { return Math.abs(p[0] - x) < 42 && Math.abs(p[1] - y) < 21; });
        if (!clash) break;
        y += (t % 2 === 0 ? 23 : -23);
        if (t >= 2) x += 20;
      }
      placed.push([x, y]);
      pill(svg, x, y, String(it.flow), { size: 12, color: it.color, textColor: it.color });
    });

    /* 出口端总量标签（灰色胶囊，贴近出口道） */
    [1, 2, 3, 4].forEach(function (d) {
      if (!exitTotals[d]) return;
      var p;
      if (d === 1) p = [cx + 54, cy - EDGE + 26];
      if (d === 3) p = [cx - 54, cy + EDGE - 26];
      if (d === 4) p = [cx - EDGE + 32, cy - 46];
      if (d === 2) p = [cx + EDGE - 46, cy + 52];
      pill(svg, p[0], p[1], 'Σ' + exitTotals[d], { size: 12, color: '#64748b', textColor: '#1e293b' });
    });

    /* 方向标签（路端外侧） */
    [1, 2, 3, 4].forEach(function (d) {
      if (!legs[d]) return;
      var lp;
      if (d === 1) lp = [cx, cy - EDGE - 16];
      if (d === 3) lp = [cx, cy + EDGE + 26];
      if (d === 4) lp = [cx - EDGE - 26, cy + 5];
      if (d === 2) lp = [cx + EDGE + 30, cy + 5];
      txt(svg, lp[0], lp[1], LEG_NAME[d], { size: 15, fill: '#334155', bold: true });
    });
  }

  return { drawChannel: drawChannel, drawPhase: drawPhase, drawFlow: drawFlow, exitDirOf: exitDirOf };
});
