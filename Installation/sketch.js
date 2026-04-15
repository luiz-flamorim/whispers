//  CONFIG
const FONT_PATH         = 'fonts/CutiveMono-Regular.ttf';
const LINE_HEIGHT_RATIO = 1.65;   // lineHeight = fontSize * this
const PADDING_X         = 0.06;   // horizontal padding as fraction of canvas width
const PADDING_Y         = 0.05;   // vertical padding as fraction of canvas height
const COLOR_REST        = 30;     // resting word brightness (0–255)
const COLOR_LIT         = 255;    // highlighted word brightness
const LERP_SPEED        = 0.10;   // hover fade speed
const FADE_OUT_SPEED    = 0.07;   // transition fade-out speed

let font             = null;
let fontSize         = 18;                          // computed by fitFontSize()
let lineHeight       = fontSize * LINE_HEIGHT_RATIO; // recomputed alongside fontSize

let hops             = [];   // populated by loader.js via transitionTo()
let words            = [];   // [{ text, x, y, cx, brightness, blockIdx }]
let blocks           = [];   // [{ yTop, yBottom }]
let lastSpokenBlock  = -1;
let sketchReady      = false;

let transitionState  = 'idle';
let pendingHops      = null;


function transitionTo(newHops) {
  window.speechSynthesis.cancel();
  lastSpokenBlock = -1;

  if (!sketchReady || words.length === 0) {
    hops = newHops;
    if (sketchReady) { fitFontSize(); buildLayout(); }
    return;
  }

  pendingHops     = newHops;
  transitionState = 'fading-out';
}


function preload() {
  font = loadFont(FONT_PATH);
}

function setup() {
  pixelDensity(1);
  createCanvas(windowWidth, windowHeight);
  textFont(font);
  fitFontSize();
  buildLayout();
  sketchReady = true;
}

function draw() {
  background(0);
  noStroke();
  textFont(font);
  textSize(fontSize);

  //  Transition: fade out, swap, fit, fade in 
  if (transitionState === 'fading-out') {
    let allDark = true;
    for (let i = 0; i < words.length; i++) {
      words[i].brightness = lerp(words[i].brightness, 0, FADE_OUT_SPEED);
      if (words[i].brightness > 1) allDark = false;
      fill(words[i].brightness);
      text(words[i].text, words[i].x, words[i].y);
    }
    if (allDark) {
      hops            = pendingHops;
      pendingHops     = null;
      transitionState = 'idle';
      fitFontSize();
      buildLayout();
    }
    return;
  }

  const active = activeBlock();

  if (active !== lastSpokenBlock) {
    lastSpokenBlock = active;
    if (active !== -1) speakHop(active);
    else window.speechSynthesis.cancel();
  }

  for (let i = 0; i < words.length; i++) {
    const target        = words[i].blockIdx === active ? COLOR_LIT : COLOR_REST;
    words[i].brightness = lerp(words[i].brightness, target, LERP_SPEED);
    fill(words[i].brightness);
    text(words[i].text, words[i].x, words[i].y);
  }
}

function windowResized() {
  resizeCanvas(windowWidth, windowHeight);
  fitFontSize();
  buildLayout();
}

// Font size: Binary-searches for the largest font size where all text fits in the canvas
// without overflowing vertically. Sets the module-level fontSize / lineHeight.
function fitFontSize() {
  if (!hops.length) return;

  const padX      = width  * PADDING_X;
  const padY      = height * PADDING_Y;
  const maxW      = width  - padX * 2;
  const availH    = height - padY * 2;

  let lo = 6, hi = 120;

  while (lo < hi - 1) {
    const mid = Math.floor((lo + hi) / 2);
    textFont(font);
    textSize(mid);
    const numLines = countLines(maxW);
    const totalH   = numLines * mid * LINE_HEIGHT_RATIO;
    if (totalH <= availH) lo = mid; else hi = mid;
  }

  fontSize   = lo;
  lineHeight = lo * LINE_HEIGHT_RATIO;
}

// Dry-runs the line-wrapping pass at the current textSize and returns line count.
function countLines(maxW) {
  const tokens = [];
  for (let bi = 0; bi < hops.length; bi++) {
    const parts = hops[bi].trim().split(/\s+/);
    for (let pi = 0; pi < parts.length; pi++) tokens.push(parts[pi]);
  }

  let numLines  = 1;
  let lineW     = 0;
  const spaceW  = textWidth(' ');

  for (let ti = 0; ti < tokens.length; ti++) {
    const tw = textWidth(tokens[ti]);
    if (lineW + tw > maxW && lineW > 0) { numLines++; lineW = tw + spaceW; }
    else lineW += tw + spaceW;
  }

  return numLines;
}

// hit detection
function activeBlock() {
  let best     = -1;
  let bestDist = Infinity;

  for (let i = 0; i < words.length; i++) {
    const d = dist(mouseX, mouseY, words[i].cx, words[i].y);
    if (d < bestDist) { bestDist = d; best = words[i].blockIdx; }
  }

  return bestDist <= lineHeight * 1.2 ? best : -1;
}

function buildLayout() {
  words  = [];
  blocks = [];
  textFont(font);
  textSize(fontSize);

  if (!hops.length) return;

  const padX = width  * PADDING_X;
  const padY = height * PADDING_Y;
  const maxW = width  - padX * 2;

  // Flatten all hops into one token list, each token tagged with its blockIdx
  const tokens = [];
  for (let bi = 0; bi < hops.length; bi++) {
    const parts = hops[bi].trim().split(/\s+/);
    for (let pi = 0; pi < parts.length; pi++) {
      tokens.push({ text: parts[pi], blockIdx: bi });
    }
  }

  // Pass 1 — wrap into lines
  const lines = [];
  let line    = [];
  for (let ti = 0; ti < tokens.length; ti++) {
    const token = tokens[ti];
    const probe = line.reduce(function (s, w) { return s + textWidth(w.text + ' '); }, 0)
                + textWidth(token.text + ' ');
    if (probe > maxW && line.length > 0) { lines.push(line); line = [token]; }
    else line.push(token);
  }
  if (line.length) lines.push(line);

  // Pass 2 — justify and record positions; track block y-extents
  const blockYMap = {};
  const totalH    = lines.length * lineHeight;
  const startY    = max(padY + lineHeight, (height - totalH) / 2 + lineHeight);

  for (let li = 0; li < lines.length; li++) {
    const row      = lines[li];
    const y        = startY + li * lineHeight;
    const lastLine = li === lines.length - 1;

    if (row.length === 1 || lastLine) {
      let x = padX;
      for (let ri = 0; ri < row.length; ri++) {
        const tw = textWidth(row[ri].text);
        words.push({ text: row[ri].text, x: x, y: y, cx: x + tw * 0.5,
                     brightness: 0, blockIdx: row[ri].blockIdx });
        trackBlock(blockYMap, row[ri].blockIdx, y);
        x += tw + textWidth(' ');
      }
    } else {
      const widths  = row.map(function (w) { return textWidth(w.text); });
      const totalWW = widths.reduce(function (a, b) { return a + b; }, 0);
      const gap     = (maxW - totalWW) / (row.length - 1);
      let x         = padX;
      for (let ri = 0; ri < row.length; ri++) {
        words.push({ text: row[ri].text, x: x, y: y, cx: x + widths[ri] * 0.5,
                     brightness: 0, blockIdx: row[ri].blockIdx });
        trackBlock(blockYMap, row[ri].blockIdx, y);
        x += widths[ri] + gap;
      }
    }
  }

  for (let bi = 0; bi < hops.length; bi++) {
    const b = blockYMap[bi];
    if (b) blocks.push({ yTop:    b.yTop    - lineHeight * 0.5,
                         yBottom: b.yBottom + lineHeight * 0.5 });
  }
}

// speech
function speakHop(blockIdx) {
  window.speechSynthesis.cancel();
  const utterance = new SpeechSynthesisUtterance(hops[blockIdx]);
  utterance.rate  = 0.85;
  utterance.pitch = 1;
  window.speechSynthesis.speak(utterance);
}

function trackBlock(map, bi, y) {
  if (!map[bi]) { map[bi] = { yTop: y, yBottom: y }; return; }
  if (y < map[bi].yTop)    map[bi].yTop    = y;
  if (y > map[bi].yBottom) map[bi].yBottom = y;
}
