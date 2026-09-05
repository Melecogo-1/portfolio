/* ============================================================
   凌煜圣 · 沉浸式全栈作品集（纯静态 / 零后端 / 零外部 API）
   3D 采集员 + 环绕档案 + 深度项目卡 + 本地创意终端
   ============================================================ */

const state = {
  three: null,
  fallback: null,
  portrait: null,
  mixers: [],
  activeProject: -1,
  pointer: { x: 0, y: 0 },
  focus: 0,            // 0 静止，1 聚焦某项目
  reduced: window.matchMedia('(prefers-reduced-motion: reduce)').matches,
};
window.portfolioState = state;

/* ---------------- 项目数据（权威时间 / 硬数据） ---------------- */
const projects = [
  {
    title: 'AI-DataPilot',
    type: '电商经营数据分析平台',
    time: '2026.06 – 08',
    glyph: '01', tone: 'tone-0', lamp: 0x7fd6dd,
    outcome: '电商经营分析平台：从多 sheet 原始 Excel，做到指标看板、分级业务发现、分岗日报与自然语言查数。',
    how: '分三层：pandas 读管报与订单、统一金额并对姓名手机号脱敏，落标准化 CSV 后多维聚合；服务层内存现算，Flask 出看板、指标、日报、问答四类接口、不设独立数据库；ECharts 画月度双轴、品牌占比、平台对比、品类成交率四张图。自然语言查数不走 NL2SQL：先聚合指标摘要注入，模型只在给定范围内作答并回传来源与置信度，无 Key 回退关键词规则。',
    metrics: [['20.15亿', '营收'], ['28.4万', '台'], ['4.9万', '报价单'], ['15.6万', '账单'], ['CR3', '88%']],
    proof: [
      ['口径甄别', '成交价 44.2% 为空，按撤销、报价中、新建采购、待发布拆开，判定是报价未成交而非缺数，统一改用报价到成交转化率'],
      ['受限生成', '不做 NL2SQL，模型只在预聚合摘要内给结论、标来源与置信度、不直接查库，调用异常同样回退规则应答'],
      ['小样本过滤', '成交率排名设样本阈值，品牌大于 100、来源大于 200，剔除小样本算出的极端比率'],
      ['逐级下钻', '快手渠道毛利 -1.70%（26 万 / 96 台 / 客单 2741），沿品牌、平台、机型逐级定位到亏损点'],
    ],
    tags: ['Python', 'Flask', 'pandas', 'ECharts', 'DeepSeek', '数据脱敏'],
    cover: null, useAbstract: true,
    launchUrl: null,
  },
  {
    title: 'Dream Weaver',
    type: '互动叙事引擎后端',
    time: '2026.04 – 06',
    glyph: '02', tone: 'tone-1', lamp: 0x9f8eff,
    outcome: '互动叙事后端：把玩家输入的判定与叙述生成解耦，硬状态只由规则写，模型只理解意图、在有界区间影响软数值。',
    how: '世界、NPC、事件规则与结局全外置 JSON，程序是读数据的通用引擎、运行状态在内存。输入先由本地关键词规则解析成动作基线，再交 DeepSeek 判可行性与意图；返回先过白名单与存在性校验，物品、NPC 生死、结局、移动一律由规则写入，最后才让模型把既定结果写成叙述。模型不可用时回退本地规则与确定性模板。',
    metrics: [['1435', '行后端'], ['17', '因果卡'], ['27', '事件卡'], ['5', '结局']],
    proof: [
      ['模型输出护栏', '7 类动作、4 档可行性、4 档风险全走白名单；模型单步态度增量夹在 [-8,8]，目标不存在回退基线'],
      ['声明式条件', '9 种谓词配 AND/OR 递归嵌套；多张卡同时命中先按特异度、再按 priority 排序，并按态度冷暖与成败选版本'],
      ['降级与清洗', '判定回规则、叙述回模板，两路独立；玩家文本先在提示词禁机制词、输出再复检 D20/JSON/API 并按句截断'],
      ['锁粒度取舍', '结算与提交放锁内，最慢的叙述生成移出临界区；判定因耦合暂留锁内，下一步拆成快照、判定、提交'],
    ],
    tags: ['Flask', '规则引擎', 'DeepSeek', 'JSON 数据驱动', '并发控制'],
    cover: './assets/projects/dream-weaver-cover.png', useAbstract: false,
    launchUrl: null,
  },
  {
    title: '一源树多服务部署',
    type: '云部署 / 运维实践',
    time: '2026.02 – 05',
    glyph: '03', tone: 'tone-2', lamp: 0xecc478,
    outcome: '一份 Render Blueprint 把同一代码树编排成 4 个独立 Web 服务，本地云端同一套代码、不改一行。',
    how: '一份 YAML 声明主站、互动叙事、文字游戏与图像溯源四个服务。进程模型按依赖最小化选型：主站与溯源用标准库 ThreadingHTTPServer（主站零第三方依赖），两个 Flask 服务用 gunicorn 绑平台端口。地址走环境变量、主站用配置接口下发前端做服务发现。免费实例重启清空磁盘，服务启动幂等自举：缺表建表、PRAGMA 查列、缺列才 ALTER、缺种子就程序化重建；公共领域参考图单独标来源与许可。',
    metrics: [['4', '个服务'], ['1', '份 Blueprint'], ['8×8=64位', '感知哈希'], ['零', '主站依赖']],
    proof: [
      ['配置代码分离', '下游地址、模型 Key、会话密钥全走环境变量，Key 面板手填不入库、会话密钥平台生成，代码不分本地云端'],
      ['幂等自举', 'CREATE IF NOT EXISTS 后用 PRAGMA 比对、只对缺列 ALTER；种子谱系仅在为空时用 Pillow 程序化生成并串好'],
      ['资产溯源', 'SHA-256 内容哈希做文件名与去重，8×8 感知哈希配汉明距离算相似度；parent_id 谱系校验父存在、禁自环、删父先解子'],
    ],
    tags: ['Render Blueprint', 'YAML IaC', '服务发现', 'gunicorn', '标准库 HTTP', 'Pillow', 'SQLite'],
    cover: null, useAbstract: true,
    launchUrl: null,
  },
  {
    title: 'Creative Engine Lab',
    type: 'AIGC 创意工具',
    time: '2026.02',
    glyph: '04', tone: 'tone-3', lamp: 0xc9793b,
    outcome: 'AIGC 创意生成工具：一句主题产出配色、材质、构图、灯光、镜头与多版 Prompt 的完整视觉方案，并保存历史。',
    how: '后端不引框架，用 Python 标准库手写 HTTP、路由与静态托管，SQLite 存生成历史。用输入文本派生随机种子，同一主题每次得到同一套方案；一次把调色板、结构原型、材质、灯光、镜头和多版 Prompt 打包成一条 JSON 入库。右下角创意终端是同一确定性逻辑的纯前端复刻（自写 PRNG），断网可跑。',
    metrics: [['零', 'Web 框架'], ['24 条', '最近历史'], ['10 选 4', '材质'], ['3', '版 Prompt']],
    proof: [
      ['可复现', '输入字符和作随机种子驱动全部选择，同一输入结果一致，这也是能整段搬到前端离线运行的前提'],
      ['零框架', '标准库手写 HTTP、JSON 接口、MIME 与 CORS 预检，静态文件服务额外做目录穿越校验'],
      ['一条记录', '配色、材质、构图、灯光、镜头与多版 Prompt 作为整体，以 JSON 文本列存进关系库，复现不缺项'],
    ],
    tags: ['Python 标准库', 'SQLite', '确定性生成', '数据驱动', 'Prompt'],
    cover: null, useAbstract: true,
    launchUrl: null,
  },
  {
    title: 'Silent Asylum',
    type: '文字互动游戏',
    time: '2026.01',
    glyph: '05', tone: 'tone-4', lamp: 0xe08286,
    outcome: '文字恐怖游戏：以 0-100 精神侵蚀度为核心数值，配合碎片收集与行为标志驱动分支和结局。',
    how: '71KB JSON 描述 5 场景、52 规则、22 事件、66 选项，程序只做状态流转、内容与逻辑分离。选项携带侵蚀增减、碎片或行为标志，侵蚀每次选择后钳在 0-100；前端按五档换 body 类，用 CSS 变量与滤镜随档位压低选项可读性。状态存 Session，五个存档槽过场自动写，死亡可原地重试或回最近存档。',
    metrics: [['71KB', 'JSON 数据'], ['66', '选项'], ['18', '碎片'], ['13', '即死结局']],
    proof: [
      ['数值驱动界面', '五档区间、配色、状态类全由数据给出，前端只换 body 类，叠加 CSS 变量与滤镜连续劣化，不在分支硬写界面'],
      ['状态一致性', '选择当下、进入页面、读档三处都校验侵蚀，满值统一结算同化结局，异常状态绕不过结局判定'],
      ['存档与回环', '五槽随过场自动写、死亡原地重试或向前找最近档；被送回首间病房只重置场景，侵蚀、碎片、标志全保留'],
    ],
    tags: ['Flask', 'JSON 数据驱动', '数值驱动分支', 'Session', '原生 JS'],
    cover: './assets/projects/silent-asylum-cover.png', useAbstract: false,
    launchUrl: null,
  },
];

const quickPrompts = [
  '为一个关于深海遗迹的独立游戏设计第一幕',
  '把城市夜跑做成一支反乌托邦短片的视觉概念',
  '设计一个会记录玩家记忆的奇幻旅店',
];

const $ = (id) => document.getElementById(id);
const escapeHtml = (v) => String(v).replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;').replaceAll("'",'&#039;');
const isNarrow = () => window.matchMedia('(max-width: 760px)').matches;

/* ============================================================
   加载层
   ============================================================ */
const preloader = { el: null, fill: null, pct: null, label: null, done: false };
function initPreloader() {
  preloader.el = $('preloader'); preloader.fill = $('preFill');
  preloader.pct = $('prePct'); preloader.label = $('preLabel');
}
function setPreload(p, label) {
  const v = Math.max(0, Math.min(100, Math.round(p)));
  if (preloader.fill) preloader.fill.style.width = v + '%';
  if (preloader.pct) preloader.pct.textContent = String(v).padStart(2, '0');
  if (label && preloader.label) preloader.label.textContent = label;
}
function finishPreload() {
  if (preloader.done) return; preloader.done = true;
  setPreload(100, '加载完成');
  setTimeout(() => {
    preloader.el?.classList.add('is-done');
    document.body.classList.add('is-ready');
    // 保险：过渡结束后直接移出渲染树，避免个别环境 transition 不推进导致残影
    setTimeout(() => { if (preloader.el) preloader.el.style.display = 'none'; }, 900);
  }, 350);
}

/* ============================================================
   自定义光标（仅桌面精细指针）
   ============================================================ */
function initCursor() {
  const fine = window.matchMedia('(pointer: fine)').matches;
  if (!fine) return;
  document.body.classList.add('has-fine-pointer');
  const ring = $('cursorRing'), dot = $('cursorDot');
  const target = { x: innerWidth / 2, y: innerHeight / 2 };
  const pos = { ...target };
  addEventListener('pointermove', (e) => { target.x = e.clientX; target.y = e.clientY;
    dot.style.transform = `translate(${target.x}px,${target.y}px)`; });
  const hotSel = 'button, a, .project-node, input, textarea, [data-hot]';
  addEventListener('pointerover', (e) => document.body.classList.toggle('cursor-hot', !!e.target.closest?.(hotSel)));
  (function loop() {
    pos.x += (target.x - pos.x) * 0.18; pos.y += (target.y - pos.y) * 0.18;
    ring.style.transform = `translate(${pos.x}px,${pos.y}px)`;
    requestAnimationFrame(loop);
  })();
}

/* ============================================================
   面板开关
   ============================================================ */
function setPanel(panel, open) {
  if (!panel) return;
  panel.classList.toggle('is-open', open);
  panel.setAttribute('aria-hidden', String(!open));
}
function setProjectAtmosphere(index = null) {
  const stage = $('stage'), signal = $('projectSignal');
  if (!stage || !signal) return;
  if (index === null || !projects[index]) { delete stage.dataset.project; signal.classList.remove('is-active'); return; }
  stage.dataset.project = String(index);
  signal.querySelector('small').textContent = `${projects[index].title.toUpperCase()} / LINKED`;
  signal.classList.add('is-active');
}
function closeProjectFile() {
  state.activeProject = -1;
  setPanel($('projectFile'), false);
  document.querySelectorAll('.project-node').forEach(n => n.classList.remove('is-selected'));
  setProjectAtmosphere(); state.focus = 0;
  if (location.hash.startsWith('#p')) history.replaceState(null, '', location.pathname + location.search);
}
function setEngineOpen(open) { setPanel($('engine'), open); $('engineToggle')?.classList.toggle('is-active', open); if (open) { closeProjectFile(); setResultOpen(false); } }
function setResultOpen(open) { setPanel($('resultPanel'), open); }
function setResumeOpen(open) {
  setPanel($('resumeDossier'), open);
  $('resumeToggle')?.setAttribute('aria-expanded', String(open));
  if (open) { closeProjectFile(); setEngineOpen(false); setResultOpen(false); }
}

/* ============================================================
   项目轨道（桌面椭圆环绕 / 窄屏静态列）
   ============================================================ */
let orbitState = null;
function renderOrbit() {
  const orbit = $('projectOrbit');
  orbit.innerHTML = projects.map((p, i) => {
    const visual = p.useAbstract || !p.cover
      ? `<span class="node-abstract abs ${p.tone}" data-glyph="${p.glyph}"></span>`
      : `<span class="node-thumb" style="background-image:url('${p.cover}')"></span>`;
    return `
      <button class="project-node" type="button" data-project="${i}" aria-label="查看 ${escapeHtml(p.title)}">
        ${visual}
        <span class="node-index mono">${p.glyph}</span>
        <span class="node-time mono">${p.time}</span>
        <span class="node-label"><strong>${escapeHtml(p.title)}</strong><small>${escapeHtml(p.type)}</small><em>${escapeHtml(p.metrics[0][0])} ${escapeHtml(p.metrics[0][1])} · ${escapeHtml(p.tags.slice(0,2).join(' / '))}</em></span>
      </button>`;
  }).join('');
  orbit.querySelectorAll('.project-node').forEach(node => {
    const i = Number(node.dataset.project);
    node.addEventListener('click', () => showProjectFile(i));
    node.addEventListener('pointerenter', () => { orbitState && (orbitState.paused = true); setProjectAtmosphere(i); lampTo(i); });
    node.addEventListener('pointerleave', () => { if (orbitState && state.activeProject < 0) { orbitState.paused = false; setProjectAtmosphere(); lampTo(null); } });
    node.addEventListener('focus', () => { orbitState && (orbitState.paused = true); });
    node.addEventListener('blur', () => { orbitState && (orbitState.paused = false); });
  });
  setupOrbitMode();
}
function setupOrbitMode() {
  const orbit = $('projectOrbit');
  const nodes = [...orbit.querySelectorAll('.project-node')];
  if (isNarrow()) { orbit.classList.add('static-orbit'); orbitState = null; return; }
  orbit.classList.remove('static-orbit');
  orbitState = { nodes, phase: -0.18, last: performance.now(), paused: false };
  (function frame(now) {
    if (!orbitState) return;
    const dt = Math.min((now - orbitState.last) / 1000, 0.05); orbitState.last = now;
    if (!orbitState.paused && !state.reduced) orbitState.phase += dt * 0.2;
    const w = innerWidth, h = innerHeight, n = orbitState.nodes.length;
    const rx = Math.min(w * 0.285, 482), ry = Math.min(h * 0.118, 122), cy = h * 0.54;
    orbitState.nodes.forEach((node, i) => {
      const a = orbitState.phase + (Math.PI * 2 * i) / n;
      const depth = (Math.sin(a) + 1) / 2;
      const x = Math.cos(a) * rx, y = (depth - .5) * ry;
      node.style.setProperty('--orbit-x', x.toFixed(1) + 'px');
      node.style.setProperty('--orbit-y', (cy + y - h / 2).toFixed(1) + 'px');
      node.style.setProperty('--orbit-scale', (0.7 + depth * 0.32).toFixed(3));
      node.style.setProperty('--orbit-opacity', (0.46 + depth * 0.54).toFixed(3));
      node.style.zIndex = depth > 0.48 ? String(15 + Math.round(depth * 4)) : '2';
      node.classList.toggle('is-behind', depth <= 0.48);
    });
    requestAnimationFrame(frame);
  })(performance.now());
}

/* ============================================================
   深度项目档案
   ============================================================ */
function showProjectFile(index) {
  const p = projects[index]; if (!p) return;
  state.activeProject = index; state.focus = 1;
  setProjectAtmosphere(index); lampTo(index);
  $('fileType').textContent = `项目 ${p.glyph} / ${p.type} · ${p.time}`;
  $('fileTitle').textContent = p.title;
  $('fileOutcome').textContent = p.outcome;
  $('fileHow').textContent = p.how;
  $('fileMetrics').innerHTML = p.metrics.map(([v, k]) => `<span><b class="mono">${escapeHtml(v)}</b>${escapeHtml(k)}</span>`).join('');
  $('fileProof').innerHTML = p.proof.map(([tag, txt], i) =>
    `<span><b class="mono">${String(i + 1).padStart(2, '0')} · ${escapeHtml(tag)}</b>${escapeHtml(txt)}</span>`).join('');
  $('fileTags').innerHTML = p.tags.map(t => `<span>${escapeHtml(t)}</span>`).join('');

  const frame = $('fileCoverFrame'), img = $('fileCover');
  frame.classList.toggle('abs', p.useAbstract || !p.cover);
  frame.className = `file-cover ${p.tone}${(p.useAbstract || !p.cover) ? ' abs' : ''}`;
  if (p.useAbstract || !p.cover) { img.removeAttribute('src'); img.alt = ''; frame.setAttribute('data-glyph', p.glyph); }
  else { img.src = p.cover; img.alt = `${p.title} 封面`; frame.removeAttribute('data-glyph'); }

  const launch = $('launchProject');
  if (p.launchUrl) { launch.innerHTML = '进入在线体验 <span>↗</span>'; launch.disabled = false; }
  else { launch.innerHTML = '本地可运行 · 欢迎现场演示 <span>●</span>'; launch.disabled = false; }
  launch.dataset.project = String(index);

  setEngineOpen(false); setPanel($('projectFile'), true);
  document.querySelectorAll('.project-node').forEach(n => n.classList.toggle('is-selected', Number(n.dataset.project) === index));
  if (location.hash !== `#p${index}`) history.replaceState(null, '', `#p${index}`);
}
function applyHash() {
  const h = location.hash;
  if (/^#p\d+$/.test(h)) { const i = Number(h.slice(2)); if (projects[i]) showProjectFile(i); }
  else if (h === '#cv') setResumeOpen(true);
  else if (h === '#engine') setEngineOpen(true);
}
function launchActiveProject() {
  const i = Number($('launchProject').dataset.project), p = projects[i]; if (!p) return;
  if (p.launchUrl) { window.open(p.launchUrl, '_blank', 'noopener'); return; }
  const btn = $('launchProject'); const old = btn.innerHTML;
  btn.innerHTML = '已记录 · 可约面现场演示 <span>✓</span>';
  setTimeout(() => { btn.innerHTML = old; }, 1400);
}

/* ============================================================
   3D 舞台
   ============================================================ */
function initFallback() {
  const canvas = $('fallbackStage'), ctx = canvas.getContext('2d');
  state.fallback = { canvas, ctx, tick: 0 };
  const resize = () => { const r = canvas.getBoundingClientRect();
    canvas.width = Math.max(1, Math.floor(r.width * devicePixelRatio));
    canvas.height = Math.max(1, Math.floor(r.height * devicePixelRatio));
    ctx.setTransform(devicePixelRatio, 0, 0, devicePixelRatio, 0, 0); };
  resize(); addEventListener('resize', resize);
  (function paint() {
    const { width: w, height: h } = canvas.getBoundingClientRect();
    state.fallback.tick += 0.012; ctx.clearRect(0, 0, w, h);
    const g = ctx.createRadialGradient(w * .5, h * .62, 12, w * .5, h * .62, Math.min(w, h) * .48);
    g.addColorStop(0, 'rgba(225,146,72,.26)'); g.addColorStop(.52, 'rgba(44,28,14,.13)'); g.addColorStop(1, 'rgba(0,0,0,0)');
    ctx.fillStyle = g; ctx.fillRect(0, 0, w, h);
    ctx.strokeStyle = 'rgba(236,196,120,.22)'; ctx.lineWidth = 1; ctx.beginPath();
    ctx.ellipse(w * .5, h * .77, w * .16, h * .035, 0, 0, Math.PI * 2); ctx.stroke();
    requestAnimationFrame(paint);
  })();
}

let lampTarget = null;
function lampTo(i) { lampTarget = (i == null) ? null : projects[i].lamp; }

function initThree(manager) {
  const host = $('threeStage'), fallback = $('fallbackStage');
  if (!window.THREE || !window.THREE.GLTFLoader) { return false; }
  const THREE = window.THREE;
  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(30, 1, .1, 100);
  const baseCam = { z: 6.9, y: 0.15 };
  camera.position.set(0, baseCam.y, baseCam.z);
  const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
  renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.18;
  renderer.domElement.className = 'three-canvas';
  host.appendChild(renderer.domElement);

  const world = new THREE.Group(); scene.add(world);
  const key = new THREE.DirectionalLight(0xffc77c, 2.4); key.position.set(3.2, 4.2, 5.2); scene.add(key);
  const fill = new THREE.DirectionalLight(0x88cbd1, 1.15); fill.position.set(-4, 1.6, 2.4); scene.add(fill);
  const rim = new THREE.PointLight(0xff7f38, 8.5, 13); rim.position.set(-2.7, 1.3, 2.4); scene.add(rim);
  scene.add(new THREE.AmbientLight(0x17212b, 1.18));
  const rimBase = new THREE.Color(0xff7f38);

  const loader = new THREE.GLTFLoader(manager);
  loader.loadAsync('./assets/models/autumn-explorer.glb').then(gltf => {
    const m = gltf.scene; m.scale.setScalar(0.94); m.position.set(0, -.14, 0); m.rotation.y = -.05;
    m.traverse(c => { if (c.isMesh) { c.castShadow = false; c.frustumCulled = true; } });
    world.add(m); state.portrait = m;
    if (gltf.animations?.length) { const mixer = new THREE.AnimationMixer(m); gltf.animations.forEach(c => mixer.clipAction(c).play()); state.mixers.push(mixer); }
    fallback.classList.add('is-hidden');
  }).catch(() => fallback.classList.remove('is-hidden'));

  const resize = () => { const r = host.getBoundingClientRect();
    camera.aspect = r.width / Math.max(r.height, 1); camera.updateProjectionMatrix();
    renderer.setSize(r.width, r.height, true); };
  resize(); addEventListener('resize', resize);
  addEventListener('pointermove', (e) => { state.pointer.x = (e.clientX / innerWidth - .5) * 2; state.pointer.y = (e.clientY / innerHeight - .5) * 2; });

  const clock = new THREE.Clock();
  let curRim = rimBase.clone();
  (function render() {
    const t = clock.getElapsedTime(), dt = clock.getDelta();
    state.mixers.forEach(m => m.update(dt));
    if (state.portrait) {
      state.portrait.position.y = -.14 + Math.sin(t * 1.15) * .025;
      state.portrait.rotation.y = -.05 + Math.sin(t * .46) * .028 + state.pointer.x * .06;
      const breathe = 1 + Math.sin(t * 1.2) * .007;
      state.portrait.scale.setScalar(0.94 * breathe);
    }
    // 相机视差 + 聚焦推近
    const targetZ = baseCam.z - state.focus * 0.85;
    camera.position.z += (targetZ - camera.position.z) * 0.06;
    camera.position.x += (state.pointer.x * 0.32 - camera.position.x) * 0.05;
    camera.position.y += ((baseCam.y - state.pointer.y * 0.2) - camera.position.y) * 0.05;
    camera.lookAt(0, 0, 0);
    // 灯光随项目切换
    const goal = lampTarget ? new THREE.Color(lampTarget) : rimBase;
    curRim.lerp(goal, 0.08); rim.color.copy(curRim);
    rim.intensity = 7.7 + Math.sin(t * .78) * .7 + state.focus * 1.4;
    renderer.render(scene, camera);
    requestAnimationFrame(render);
  })();

  state.three = { scene, camera, renderer, key, fill, rim };
  return true;
}

/* ============================================================
   本地创意终端（把后端规则生成搬到前端，零请求）
   ============================================================ */
const PALETTES = [
  { name: 'Ion Glass', colors: ['#E8FAFF', '#62D8FF', '#FFCF66', '#17212B', '#F46A6A'], mood: '清透锋利、高能实验室冷光' },
  { name: 'Nocturne Signal', colors: ['#101318', '#36F5B2', '#EAF0FF', '#E3487A', '#F6B95E'], mood: '夜间信号、潮湿金属与霓虹边缘' },
  { name: 'Solar Archive', colors: ['#FFF4D7', '#FF8A3D', '#3547E8', '#111827', '#7BE0AD'], mood: '档案室、太阳尘埃与工业暖扫描光' },
  { name: 'Bio Circuit', colors: ['#F2FFE8', '#00C27A', '#1C2A32', '#B963FF', '#FFD166'], mood: '电路走线和生物纹理叠在一起的界面感' },
];
const ARCHETYPES = [
  { label: '沉浸式空间', structure: '入口区 → 观察廊 → 核心装置 → 资料层' },
  { label: '品牌概念片', structure: '黑场标题 → 材质微距 → 主体显形 → 标语定格' },
  { label: '游戏关卡提案', structure: '出生点 → 视觉地标 → 风险路径 → 奖励区域' },
  { label: '展览策展方案', structure: '主题墙 → 分区叙事 → 交互台 → 纪念出口' },
];
const AUDIENCES = ['AIGC 概念艺术作品集', '品牌视觉提案', '游戏 / 影视前期设定', '交互展览策划'];
const MATERIALS = ['半透明树脂','阳极氧化铝','雾面陶瓷','湿润沥青','发光纤维','磨砂玻璃','碳纤维织纹','液态金属','投影薄雾','再生塑料'];
const LIGHTING = ['顶部一束窄冷光，靠地面反射补第二层亮','侧后方打强轮廓光压出剪影，暗部用暖色扫描线破开','低饱和环境光铺底，只给关键物体一点脉冲高光','柔和天光打底，再用硬边投影勾出形体'];
const FORMATS = ['一页式视觉提案板', '15 秒概念短片分镜', '可交互网页首屏', '三张系列概念图'];
function seedRng(seed) { let s = seed % 2147483647; if (s <= 0) s += 2147483646; return () => (s = s * 16807 % 2147483647) / 2147483647; }
function pick(r, a) { return a[Math.floor(r() * a.length)]; }
function sample(r, a, n) { const c = [...a]; for (let i = c.length - 1; i > 0; i--) { const j = Math.floor(r() * (i + 1)); [c[i], c[j]] = [c[j], c[i]]; } return c.slice(0, n); }
function generateLocal(brief) {
  let seed = 0; const s = brief || 'x'; for (let i = 0; i < s.length; i++) seed = (seed + s.charCodeAt(i) * (i + 1)) % 1000003;
  const r = seedRng(seed || 7);
  const palette = pick(r, PALETTES), arch = pick(r, ARCHETYPES), mats = sample(r, MATERIALS, 4);
  const words = (brief.toLowerCase().match(/[\w\u4e00-\u9fff]+/g) || ['unknown','signal']).slice(0, 3);
  return {
    title: words.map(w => w.toUpperCase()).join(' / ') || 'UNKNOWN SIGNAL',
    audience: pick(r, AUDIENCES), output_format: pick(r, FORMATS),
    creative_thesis: `先定方向：「${brief}」不急着堆元素，基调走「${palette.mood}」，把主体、空间和材质立住，其余围绕它展开。`,
    worldview: `结构按「${arch.structure}」推进，整体走${palette.mood}，往后能扩成系列图、短片分镜或交互首屏。材质选 ${mats.join('、')}；灯光上，${pick(r, LIGHTING)}。`,
    palette: palette.colors,
    keywords: [...new Set([...words, ...sample(r, ['aigc','concept','prototype','cinematic','spatial','ritual','modular','artifact','interface'], 6)])].slice(0, 12),
    image_prompt: `${brief}, ${arch.label}, cinematic concept design, ${palette.mood}, materials: ${mats.join(', ')}, layered depth, human scale, precise lighting, high-detail visual development board, 16:9`,
  };
}
function renderConcept(c) {
  $('conceptTitle').textContent = c.title;
  $('creativeThesis').textContent = c.creative_thesis;
  $('audience').textContent = c.audience; $('outputFormat').textContent = c.output_format;
  $('worldview').textContent = c.worldview;
  $('palette').innerHTML = c.palette.map(col => `<span style="background:${col}" title="${col}"></span>`).join('');
  $('keywords').innerHTML = c.keywords.map(k => `<span>${escapeHtml(k)}</span>`).join('');
  $('imagePrompt').textContent = c.image_prompt;
  $('copyPrompt').textContent = '复制 Prompt';
}
function runGenerate() {
  const input = $('briefInput'), btn = $('generateBtn'), status = $('reactorState'), brief = input.value.trim();
  if (!brief) { input.focus(); status.textContent = '写下一句你真正想做的事。'; return; }
  btn.disabled = true; btn.querySelector('span').textContent = '正在推演'; status.textContent = '本地拆解 brief …';
  setTimeout(() => {
    const c = generateLocal(brief); renderConcept(c);
    setEngineOpen(false); setResultOpen(true);
    status.textContent = '已生成（本地确定性推演，未请求外部接口）。';
    btn.disabled = false; btn.querySelector('span').textContent = '生成创意档案';
  }, state.reduced ? 0 : 420);
}

/* ============================================================
   事件 & 启动
   ============================================================ */
function renderQuickPrompts() {
  const root = $('quickPrompts');
  root.innerHTML = quickPrompts.map(p => `<button type="button">${escapeHtml(p)}</button>`).join('');
  root.querySelectorAll('button').forEach((b, i) => b.addEventListener('click', () => { $('briefInput').value = quickPrompts[i]; $('briefInput').focus(); }));
}
function bindEvents() {
  $('engineToggle')?.addEventListener('click', () => setEngineOpen(!$('engine').classList.contains('is-open')));
  $('resumeToggle')?.addEventListener('click', () => setResumeOpen(!$('resumeDossier').classList.contains('is-open')));
  [['closeResume', () => setResumeOpen(false)], ['closeEngine', () => setEngineOpen(false)], ['closeResult', () => setResultOpen(false)],
   ['closeProjectFile', closeProjectFile], ['generateBtn', runGenerate], ['launchProject', launchActiveProject]].forEach(([id, fn]) => $(id)?.addEventListener('click', fn));
  $('copyPrompt')?.addEventListener('click', (e) => {
    const t = $('imagePrompt').textContent;
    navigator.clipboard?.writeText(t).then(() => { e.currentTarget.textContent = '已复制'; setTimeout(() => e.currentTarget.textContent = '复制 Prompt', 1200); }).catch(() => {});
  });
  $('briefInput')?.addEventListener('keydown', e => { if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') runGenerate(); });
  addEventListener('keydown', (e) => {
    if (e.key === 'Escape') { closeProjectFile(); setEngineOpen(false); setResultOpen(false); setResumeOpen(false); return; }
    if ($('projectFile').classList.contains('is-open') || document.activeElement.tagName === 'TEXTAREA') {
      if (document.activeElement.tagName === 'TEXTAREA') return;
    }
    if (e.key === 'ArrowRight' || e.key === 'ArrowLeft') {
      const n = projects.length, cur = state.activeProject < 0 ? 0 : (state.activeProject + (e.key === 'ArrowRight' ? 1 : n - 1)) % n;
      showProjectFile(cur);
    }
  });
  let rt; addEventListener('resize', () => { clearTimeout(rt); rt = setTimeout(() => { const was = !!orbitState; const narrow = isNarrow();
    if ((!narrow && !was) || (narrow && was)) setupOrbitMode(); }, 180); });
}

async function init() {
  initPreloader();
  initCursor();
  renderQuickPrompts();
  bindEvents();
  initFallback();
  renderOrbit();
  $('serverStatus').textContent = 'STATIC / OFFLINE-READY';

  // 用 LoadingManager 跟踪模型进度；另设一道保险，任何情况都要放开首屏
  let webglOk = false;
  try {
    const THREE = window.THREE;
    if (THREE && THREE.GLTFLoader && THREE.LoadingManager) {
      const manager = new THREE.LoadingManager();
      let settled = false;
      manager.onProgress = (u, loaded, total) => setPreload((loaded / total) * 92, `加载 3D 模型 ${loaded}/${total}`);
      manager.onLoad = () => setPreload(96, '正在进入展厅 …');
      webglOk = initThree(manager);
    } else webglOk = initThree();
  } catch { webglOk = false; }
  if (!webglOk) setPreload(80, '当前设备使用 2D 氛围模式');

  // 保险：最长 5.5s 一定放开
  let min = 0; const tick = setInterval(() => { min += 8; setPreload(Math.max(min, webglOk ? min : Math.max(min, 70))); if (min >= 100) { clearInterval(tick); finishPreload(); } }, 140);
  setTimeout(() => { clearInterval(tick); finishPreload(); }, 5500);
  // 模型动画 mixer 起来后即可放开（不等全部资源）
  setTimeout(() => finishPreload(), 1500);
  // 深链：#p0 直达项目 / #cv 履历 / #engine 终端
  setTimeout(applyHash, 1700);
  addEventListener('hashchange', applyHash);
}
init();
