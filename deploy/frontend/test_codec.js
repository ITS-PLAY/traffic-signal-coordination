/* Node 往返测试：benchmark JSON -> state -> 协议字符串，应与原始一致 */
const fs = require('fs');
const path = require('path');
const codec = require('./codec.js');

const bench = JSON.parse(fs.readFileSync(
  path.join(__dirname, '..', '..', 'traffic-signal-generator', 'test', 'benchmark', 'shuzhilu_shengtangba-ali.json'),
  'utf-8'));

const state = codec.inputToState(bench);
const out = codec.stateToInput(state);

let fail = 0;
function eq(name, a, b) {
  const sa = JSON.stringify(a), sb = JSON.stringify(b);
  if (sa === sb) { console.log('PASS', name); }
  else { fail++; console.log('FAIL', name, '\n  expect:', sb, '\n  actual:', sa); }
}

eq('crossList', out.crossList, bench.crossList);
eq('roadLength', out.roadLength, bench.roadLength);
eq('roadSpeed', out.roadSpeed, bench.roadSpeed);
eq('crossInfo', out.crossInfo, bench.crossInfo);
eq('planInfo', out.planInfo, bench.planInfo);
eq('crossFlow', out.crossFlow, bench.crossFlow);

// 时距图数据结构检查
const gw = codec.greenWindows(out.crossList, out.planInfo);
console.log('greenWindows:', JSON.stringify(gw, null, 1));
if (gw.length !== out.crossList.length || gw[0].cycle !== 70) { fail++; console.log('FAIL greenWindows basic'); }

// 绝对相位差验证：gs[k]=gs[k-1]+rel[k]（累加绿窗起点），offset[k]=gs[k]-phaseStart[k]
let _gs = 0;
for (let _i = 0; _i < gw.length; _i++) {
  const _c = gw[_i].cycle || 1;
  if (_i === 0) { _gs = gw[_i].relOffset + gw[_i].phaseStart; }
  else { _gs = _gs + gw[_i].relOffset; }
  _gs = ((_gs % _c) + _c) % _c;
  const expected = ((_gs - gw[_i].phaseStart) % _c + _c) % _c;
  if (gw[_i].offset !== expected) {
    fail++; console.log('FAIL greenWindows abs offset at', _i, 'expect', expected, 'actual', gw[_i].offset);
  }
}

// 不同协调相位场景：C1协调A(phaseStart=0)，C2协调B(phaseStart=21)，C3协调A(phaseStart=0)
// rel offsets: C1=0, C2=5, C3=10
// 预期绿窗起点: gs=0, 5, 15；绝对offset: 0, (5-21+70)%70=54, 15
const mixed = codec.greenWindows(['C1','C2','C3'], {
  C1: 'A43B27,A0', C2: 'A21B32C17,B5', C3: 'A37B15C18,A10'
});
console.log('mixed coordPhase test:', mixed.map(g => g.cross + ': rel=' + g.relOffset + ' abs=' + g.offset + ' phaseStart=' + g.phaseStart + ' gs=' + ((g.offset + g.phaseStart) % 70)));
if (mixed[0].offset !== 0) { fail++; console.log('FAIL mixed C1 abs, expect 0, got', mixed[0].offset); }
if (mixed[1].offset !== 54) { fail++; console.log('FAIL mixed C2 abs, expect 54, got', mixed[1].offset); }
if (mixed[2].offset !== 15) { fail++; console.log('FAIL mixed C3 abs, expect 15, got', mixed[2].offset); }
// 验证绿窗起点确实连续累加
if ((mixed[0].offset + mixed[0].phaseStart) % 70 !== 0) { fail++; console.log('FAIL mixed C1 gs'); }
if ((mixed[1].offset + mixed[1].phaseStart) % 70 !== 5) { fail++; console.log('FAIL mixed C2 gs'); }
if ((mixed[2].offset + mixed[2].phaseStart) % 70 !== 15) { fail++; console.log('FAIL mixed C3 gs'); }

// 绿波带宽检查：C1->C2 正向 52km/h 下 117m 行程约 8.1s
const tau = 117 / (52 / 3.6);
const band = codec.computeBand(gw[0], gw[1], tau);
console.log('band C1->C2:', JSON.stringify(band));
if (!band || band.len <= 0 || band.len > Math.min(gw[0].greenDur, gw[1].greenDur) + 0.5) {
  fail++; console.log('FAIL computeBand range');
}
const bandBack = codec.computeBand(gw[1], gw[0], tau);
console.log('band C2->C1:', JSON.stringify(bandBack));
// 带宽数值应落在绿窗内：验证采样时刻确实可通过
if (band && band.len > 0) {
  const t = band.start + band.len / 2;
  if (!(codec.isGreenAt(t, gw[0]) && codec.isGreenAt(t + tau, gw[1]))) {
    fail++; console.log('FAIL band midpoint not passable');
  }
}

console.log(fail === 0 ? '\nALL TESTS PASSED' : `\n${fail} TEST(S) FAILED`);
process.exit(fail === 0 ? 0 : 1);
