/* 用 DOM/Canvas 桩在 Node 中执行 index.html 的内联脚本，验证 drawDiagram 无运行时错误 */
const fs = require('fs');
const html = fs.readFileSync(__dirname + '/index.html', 'utf-8');
const js = html.match(/<script>([\s\S]*)<\/script>/)[1];

let polygonCount = 0;
let fillTextCount = 0;

function ctx2d() {
  return new Proxy({}, {
    get(t, p) {
      if (p === 'measureText') return () => ({ width: 60 });
      return (...a) => {
        if (p === 'fill' || p === 'stroke') polygonCount++;
        if (p === 'fillText') fillTextCount++;
      };
    },
    set() { return true; }
  });
}
function stubEl() {
  return {
    style: {}, children: [], value: '', checked: false, textContent: '', innerHTML: '',
    width: 1080, height: 400,
    classList: { toggle() {}, add() {}, remove() {} },
    appendChild(c) { this.children.push(c); return c; },
    setAttribute() {}, addEventListener() {},
    querySelector() { return stubEl(); },
    querySelectorAll() { return []; },
    getContext() { return ctx2d(); }
  };
}
global.document = {
  getElementById: () => stubEl(),
  createElement: () => stubEl(),
  createElementNS: () => stubEl(),
  createTextNode: t => ({ text: t }),
  querySelector: () => stubEl(),
  querySelectorAll: () => []
};
global.localStorage = { getItem: () => null, setItem() {}, removeItem() {} };
global.self = global;

const driver = `
;(function(){
  state = TsCodec.inputToState(EXAMPLE);
  const payload = TsCodec.stateToInput(state);
  drawDiagram(payload.planInfo, payload);
  // 再用一组“计算返回”的相位差（模拟输出）画一次
  const outPlan = { C1: 'A43B27,A0', C2: 'A21B32C17,A5', C3: 'A37B15C18,A34' };
  drawDiagram(outPlan, payload);
  // 冒烟：路口配置页新导航 + 运行页渲染
  gotoStep(2);
  gotoStep(3);
  console.log('DRAW OK');
})();`;

eval(js + driver);
console.log('canvas ops (fill/stroke):', polygonCount, ', fillText:', fillTextCount);
if (polygonCount < 10) { console.log('FAIL: too few draw ops'); process.exit(1); }
console.log('TEST PASSED');
