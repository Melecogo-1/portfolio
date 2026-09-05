const state = {
  concept: null,
  mood: { hue: 0.08, energy: 0.38, warmth: 0.48 },
  three: null,
  fallback: null,
  assetGroup: null,
  portrait: null,
  mixers: [],
  activeProject: -1,
};

window.portfolioState = state;

const projects = [
  {
    title: 'Dream Weaver',
    type: 'AI 叙事模拟',
    outcome: '让一句自由输入，成为会留下记忆与后果的世界行动。',
    description: '玩家不只是在选择预设分支。DeepSeek 会基于角色、地点、事件与历史记录，持续判断行动能否成立，并把每一次回应写回世界。',
    tags: ['DeepSeek', 'Python', '叙事模拟'],
    cover: './assets/projects/dream-weaver-cover.png',
    launchUrl: 'http://127.0.0.1:5003',
    launchLabel: '进入 Dream Weaver',
    credential: 'DEEPSEEK / WORLD MEMORY',
    proof: ['自由输入判定', '因果卡持续写入', '四地点叙事地图'],
  },
  {
    title: 'Silent Asylum',
    type: '互动惊悚体验',
    outcome: '把规则、侵蚀与选择做成一段会反噬玩家判断的调查。',
    description: '以封闭疗养院为舞台，把场景推进、线索收集、侵蚀反馈和不同结局收束为一段可反复体验的互动叙事。',
    tags: ['Python', '分支叙事', '状态系统'],
    cover: './assets/projects/silent-asylum-cover.png',
    launchUrl: 'http://127.0.0.1:8080',
    launchLabel: '进入 Silent Asylum',
    credential: 'RULE HORROR / STATE SYSTEM',
    proof: ['侵蚀度实时结算', '分场景证据图', '同化结局收束'],
  },
  {
    title: 'Creative Engine Lab',
    type: 'AIGC 创意工具',
    outcome: '把模糊的 brief 拆成可以继续执行的创意方向。',
    description: '一个将创意意图转译为世界观、视觉线索、关键词与生成提示词的本地创意引擎，也是这一作品集的交互入口。',
    tags: ['DeepSeek', 'Three.js', 'Python'],
    cover: null,
    launchUrl: null,
    launchLabel: '打开创意引擎',
    credential: 'AIGC / CREATIVE DIRECTION',
    proof: ['概念方向拆解', '视觉世界观生成', '可复制创作提示词'],
  },
];

const quickPrompts = [
  '为一个关于深海遗迹的独立游戏设计第一幕',
  '把城市夜跑做成一支反乌托邦短片的视觉概念',
  '设计一个会记录玩家记忆的奇幻旅店',
];

function element(id) {
  return document.getElementById(id);
}

function escapeHtml(value) {
  return String(value)
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#039;');
}

function setPanelVisible(panel, open) {
  if (!panel) return;
  panel.classList.toggle('is-open', open);
  panel.setAttribute('aria-hidden', String(!open));
}

function setProjectAtmosphere(index = null) {
  const stage = element('stage');
  const signal = element('projectSignal');
  if (!stage || !signal) return;

  if (index === null || !projects[index]) {
    delete stage.dataset.project;
    signal.classList.remove('is-active');
    return;
  }

  const project = projects[index];
  stage.dataset.project = String(index);
  signal.querySelector('small').textContent = `${project.title.toUpperCase()} / LINKED`;
  signal.classList.add('is-active');
}

function closeProjectFile() {
  state.activeProject = -1;
  setPanelVisible(element('projectFile'), false);
  document.querySelectorAll('.project-node').forEach((node) => node.classList.remove('is-selected'));
  setProjectAtmosphere();
}

function setEngineOpen(open) {
  setPanelVisible(element('engine'), open);
  element('engineToggle')?.classList.toggle('is-active', open);
  if (open) closeProjectFile();
}

function setResultOpen(open) {
  setPanelVisible(element('resultPanel'), open);
}
function setResumeOpen(open) {
  setPanelVisible(element('resumeDossier'), open);
  const trigger = element('resumeToggle');
  trigger?.setAttribute('aria-expanded', String(open));
  if (open) {
    closeProjectFile();
    setEngineOpen(false);
    setResultOpen(false);
  }
}


function showProjectFile(index) {
  const project = projects[index];
  if (!project) return;

  state.activeProject = index;
  setProjectAtmosphere(index);
  element('fileType').textContent = `项目 ${String(index + 1).padStart(2, '0')} / ${project.type}`;
  element('fileTitle').textContent = project.title;
  element('fileOutcome').textContent = project.outcome;
  element('fileDesc').textContent = project.description;
  element('fileCredential').textContent = project.credential;
  element('fileProof').innerHTML = project.proof.map((item, proofIndex) => `<span><b>0${proofIndex + 1}</b>${escapeHtml(item)}</span>`).join('');
  element('fileTags').innerHTML = project.tags.map((tag) => `<span>${escapeHtml(tag)}</span>`).join('');

  const cover = element('fileCover');
  const coverFrame = cover?.parentElement;
  if (cover && coverFrame) {
    if (project.cover) {
      cover.src = project.cover;
      cover.alt = `${project.title} 项目封面`;
      coverFrame.classList.remove('abstract');
    } else {
      cover.removeAttribute('src');
      cover.alt = '';
      coverFrame.classList.add('abstract');
    }
  }

  const launch = element('launchProject');
  launch.textContent = project.launchLabel;
  launch.dataset.project = String(index);
  setEngineOpen(false);
  setPanelVisible(element('projectFile'), true);

  document.querySelectorAll('.project-node').forEach((node) => {
    node.classList.toggle('is-selected', Number(node.dataset.project) === index);
  });
}

function renderProjectOrbit() {
  const orbit = element('projectOrbit');
  if (!orbit) return;

  orbit.innerHTML = projects.map((project, index) => {
    const thumb = project.cover
      ? `<span class="node-thumb" style="background-image:url('${project.cover}')"></span>`
      : '<span class="node-thumb node-thumb-engine">AI</span>';
    return `
      <button class="project-node project-node-${index + 1}" type="button" data-project="${index}" aria-label="查看 ${escapeHtml(project.title)} 项目档案">
        ${thumb}
<span class="node-label"><strong>${escapeHtml(project.title)}</strong><small>${escapeHtml(project.type)}</small></span>
      </button>
    `;
  }).join('');

  const orbitState = {
    nodes: [...orbit.querySelectorAll('.project-node')],
    phase: -0.18,
    lastFrame: performance.now(),
    paused: false,
  };
  state.projectOrbit = orbitState;

  const pauseOrbit = () => {
    orbitState.paused = true;
    orbit.classList.add('is-paused');
  };
  const resumeOrbit = () => {
    orbitState.paused = false;
    orbit.classList.remove('is-paused');
  };

  orbitState.nodes.forEach((node) => {
    node.addEventListener('click', () => showProjectFile(Number(node.dataset.project)));
    node.addEventListener('pointerenter', () => { pauseOrbit(); setProjectAtmosphere(Number(node.dataset.project)); });
    node.addEventListener('pointerleave', () => { resumeOrbit(); if (state.activeProject < 0) setProjectAtmosphere(); });
    node.addEventListener('focus', pauseOrbit);
    node.addEventListener('blur', resumeOrbit);
  });

  const animateOrbit = (now) => {
    const delta = Math.min((now - orbitState.lastFrame) / 1000, 0.05);
    orbitState.lastFrame = now;
    if (!orbitState.paused) orbitState.phase += delta * 0.22;

    const width = window.innerWidth;
    const height = window.innerHeight;
    const radiusX = Math.min(width * 0.255, 450);
    const radiusY = Math.min(height * 0.095, 102);
    const centerY = height * 0.51;

    orbitState.nodes.forEach((node, index) => {
      const angle = orbitState.phase + (Math.PI * 2 * index) / orbitState.nodes.length;
      const depth = (Math.sin(angle) + 1) / 2;
      const x = Math.cos(angle) * radiusX;
      const y = (depth - 0.5) * radiusY;
      const scale = 0.68 + depth * 0.34;
      const opacity = 0.42 + depth * 0.56;
      const inFront = depth > 0.48;

      node.style.setProperty('--orbit-x', `${x.toFixed(1)}px`);
      node.style.setProperty('--orbit-y', `${(centerY + y - height / 2).toFixed(1)}px`);
      node.style.setProperty('--orbit-scale', scale.toFixed(3));
      node.style.setProperty('--orbit-opacity', opacity.toFixed(3));
      node.style.zIndex = inFront ? String(15 + Math.round(depth * 4)) : '2';
      node.classList.toggle('is-behind', !inFront);
    });

    requestAnimationFrame(animateOrbit);
  };
  requestAnimationFrame(animateOrbit);
}
function renderQuickPrompts() {
  const root = element('quickPrompts');
  if (!root) return;
  root.innerHTML = quickPrompts.map((prompt) => `<button type="button">${escapeHtml(prompt)}</button>`).join('');
  root.querySelectorAll('button').forEach((button, index) => {
    button.addEventListener('click', () => {
      const input = element('briefInput');
      input.value = quickPrompts[index];
      input.focus();
    });
  });
}

function renderConcept(concept) {
  element('conceptTitle').textContent = concept.title || '未命名概念';
  element('creativeThesis').textContent = concept.creative_thesis || '等待创意引擎生成方向。';
  element('audience').textContent = concept.audience || '—';
  element('outputFormat').textContent = concept.output_format || '—';
  element('worldview').textContent = concept.worldview || '—';
  element('palette').innerHTML = (concept.palette || []).map((color) => `<span style="background:${escapeHtml(color)}" title="${escapeHtml(color)}"></span>`).join('');
  element('keywords').innerHTML = (concept.keywords || []).map((keyword) => `<span>${escapeHtml(keyword)}</span>`).join('');
  element('imagePrompt').textContent = concept.image_prompt || '—';
  element('copyPrompt').textContent = concept.copy_prompt || '—';
}

async function generateConcept() {
  const input = element('briefInput');
  const button = element('generateBtn');
  const status = element('reactorState');
  const brief = input.value.trim();

  if (!brief) {
    input.focus();
    status.textContent = '写下一句你真正想做的事。';
    return;
  }

  button.disabled = true;
  button.textContent = '正在拆解';
  status.textContent = '正在把 brief 转译为一个可继续生长的世界...';

  try {
    const response = await fetch('/api/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ brief }),
    });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.detail || '生成失败');

    state.concept = payload;
    state.mood = payload.mood || state.mood;
    renderConcept(payload);
    updateSceneFromMood(payload.mood || {});
    setEngineOpen(false);
    setResultOpen(true);
    status.textContent = payload.source === 'deepseek' ? '引擎已完成本次创意推演。' : '引擎已生成本地创意草案。';
  } catch (error) {
    status.textContent = error.message || '生成暂时不可用，请检查后端服务。';
  } finally {
    button.disabled = false;
    button.textContent = '开始推演';
  }
}

async function copyText(id, source) {
  const text = element(id).textContent;
  try {
    await navigator.clipboard.writeText(text);
    source.textContent = '已复制';
    window.setTimeout(() => { source.textContent = '复制'; }, 1200);
  } catch {
    source.textContent = '复制失败';
  }
}

function launchActiveProject() {
  const index = Number(element('launchProject').dataset.project);
  const project = projects[index];
  if (!project) return;

  if (project.launchUrl) {
    window.open(project.launchUrl, '_blank', 'noopener');
    return;
  }

  closeProjectFile();
  setEngineOpen(true);
  element('briefInput')?.focus();
}

function setPortfolioStatus() {
  const status = element('serverStatus');
  if (status) status.textContent = '展厅模式';
}

function initFallbackStage() {
  const canvas = element('fallbackStage');
  const ctx = canvas.getContext('2d');
  state.fallback = { canvas, ctx, tick: 0 };

  const resize = () => {
    const rect = canvas.getBoundingClientRect();
    canvas.width = Math.max(1, Math.floor(rect.width * devicePixelRatio));
    canvas.height = Math.max(1, Math.floor(rect.height * devicePixelRatio));
    ctx.setTransform(devicePixelRatio, 0, 0, devicePixelRatio, 0, 0);
  };
  resize();
  window.addEventListener('resize', resize);

  const paint = () => {
    const { width, height } = canvas.getBoundingClientRect();
    state.fallback.tick += 0.012;
    ctx.clearRect(0, 0, width, height);
    const glow = ctx.createRadialGradient(width * 0.5, height * 0.63, 12, width * 0.5, height * 0.63, Math.min(width, height) * 0.48);
    glow.addColorStop(0, 'rgba(225, 146, 72, 0.26)');
    glow.addColorStop(0.52, 'rgba(44, 28, 14, 0.13)');
    glow.addColorStop(1, 'rgba(0,0,0,0)');
    ctx.fillStyle = glow;
    ctx.fillRect(0, 0, width, height);
    ctx.strokeStyle = 'rgba(236, 191, 110, 0.22)';
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.ellipse(width * 0.5, height * 0.77, width * 0.16, height * 0.035, 0, 0, Math.PI * 2);
    ctx.stroke();
    requestAnimationFrame(paint);
  };
  paint();
}

async function initThreeStage() {
  const host = element('threeStage');
  const fallback = element('fallbackStage');
  if (!window.THREE || !window.THREE.GLTFLoader) return;

  const THREE = window.THREE;
  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(30, 1, 0.1, 100);
  camera.position.set(0, 0.15, 7.25);

  const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.18;
  renderer.domElement.className = 'three-canvas';
  host.appendChild(renderer.domElement);

  const world = new THREE.Group();
  scene.add(world);
  state.assetGroup = world;

  const key = new THREE.DirectionalLight(0xffc77c, 2.4);
  key.position.set(3.2, 4.2, 5.2);
  scene.add(key);
  const fill = new THREE.DirectionalLight(0x88cbd1, 1.15);
  fill.position.set(-4, 1.6, 2.4);
  scene.add(fill);
  const rim = new THREE.PointLight(0xff7f38, 8.5, 13);
  rim.position.set(-2.7, 1.3, 2.4);
  scene.add(rim);
  scene.add(new THREE.AmbientLight(0x17212b, 1.18));

  const loader = new THREE.GLTFLoader();
  try {
    const gltf = await loader.loadAsync('./assets/models/autumn-explorer.glb');
    const portrait = gltf.scene;
    const portraitScale = 1.05;
    const portraitBaseY = -0.24;
    portrait.scale.setScalar(portraitScale);
    portrait.position.set(0, portraitBaseY, 0);
    portrait.rotation.y = -0.05;
    portrait.traverse((child) => {
      if (child.isMesh) {
        child.castShadow = false;
        child.frustumCulled = true;
      }
    });
    world.add(portrait);
    state.portrait = portrait;

    if (gltf.animations?.length) {
      const mixer = new THREE.AnimationMixer(portrait);
      gltf.animations.forEach((clip) => mixer.clipAction(clip).play());
      state.mixers.push(mixer);
    }
    fallback.classList.add('is-hidden');
  } catch {
    fallback.classList.remove('is-hidden');
  }

  const clock = new THREE.Clock();
  const resize = () => {
    const rect = host.getBoundingClientRect();
    camera.aspect = rect.width / Math.max(rect.height, 1);
    camera.updateProjectionMatrix();
    renderer.setSize(rect.width, rect.height, true);
  };
  resize();
  window.addEventListener('resize', resize);

  const render = () => {
    const elapsed = clock.getElapsedTime();
    const delta = clock.getDelta();
    state.mixers.forEach((mixer) => mixer.update(delta));

    if (state.portrait) {
      state.portrait.position.y = -0.24 + Math.sin(elapsed * 1.15) * 0.025;
      state.portrait.rotation.y = -0.05 + Math.sin(elapsed * 0.46) * 0.028;
      const breathe = 1 + Math.sin(elapsed * 1.2) * 0.007;
      state.portrait.scale.setScalar(1.05 * breathe);
    }

    rim.intensity = 7.7 + Math.sin(elapsed * 0.78) * 0.7;
    renderer.render(scene, camera);
    requestAnimationFrame(render);
  };
  render();

  state.three = { scene, camera, renderer, key, fill, rim };
}

function updateSceneFromMood(mood) {
  if (!state.three || !window.THREE) return;
  const THREE = window.THREE;
  const hue = Number.isFinite(mood.hue) ? mood.hue : state.mood.hue;
  const warmth = Number.isFinite(mood.warmth) ? mood.warmth : state.mood.warmth;
  state.three.key.color.setHSL((hue + 0.08) % 1, 0.72, 0.66);
  state.three.fill.color.setHSL((hue + 0.52) % 1, 0.52, 0.57);
  state.three.rim.color.setHSL((hue + 0.02) % 1, 0.78, 0.56 + warmth * 0.15);
  document.documentElement.style.setProperty('--mood-hue', `${Math.round(hue * 360)}deg`);
  void THREE;
}

function bindEvents() {
  element('engineToggle')?.addEventListener('click', () => setEngineOpen(!element('engine').classList.contains('is-open')));
  element('resumeToggle')?.addEventListener('click', () => setResumeOpen(!element('resumeDossier').classList.contains('is-open')));
  element('closeResume')?.addEventListener('click', () => setResumeOpen(false));
  element('closeEngine')?.addEventListener('click', () => setEngineOpen(false));
  element('closeResult')?.addEventListener('click', () => setResultOpen(false));
  element('closeProjectFile')?.addEventListener('click', closeProjectFile);
  element('generateBtn')?.addEventListener('click', generateConcept);
  element('launchProject')?.addEventListener('click', launchActiveProject);
  element('copyPrompt')?.addEventListener('click', (event) => copyText('imagePrompt', event.currentTarget));
  element('briefInput')?.addEventListener('keydown', (event) => {
    if ((event.ctrlKey || event.metaKey) && event.key === 'Enter') generateConcept();
  });
  window.addEventListener('keydown', (event) => {
    if (event.key !== 'Escape') return;
    closeProjectFile();
    setEngineOpen(false);
    setResultOpen(false);
    setResumeOpen(false);
  });
}

async function init() {
  renderProjectOrbit();
  renderQuickPrompts();
  bindEvents();
  initFallbackStage();
  setPortfolioStatus();
  await initThreeStage();
}

init();
