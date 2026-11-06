// HUD real (nora hud) + Chromium headless (WebGL por software): FPS desenhado e CPU por /proc.
const { chromium } = require('playwright');
const { spawn } = require('child_process');
const fs = require('fs');
const PORTA = 8796, SEG = 30, HZ = 100, NUCLEOS = require('os').cpus().length;
const tick = (pid) => { try { const c = fs.readFileSync(`/proc/${pid}/stat`, 'utf8').split(') ')[1].split(' '); return +c[11] + +c[12]; } catch { return 0; } };
const filhos = (raiz) => { const todos = fs.readdirSync('/proc').filter(n => /^\d+$/.test(n)); const pai = {}; for (const p of todos) { try { pai[p] = fs.readFileSync(`/proc/${p}/stat`, 'utf8').split(') ')[1].split(' ')[1]; } catch {} } const r = new Set([String(raiz)]); let m = true; while (m) { m = false; for (const p of todos) if (!r.has(p) && r.has(pai[p])) { r.add(p); m = true; } } return [...r]; };
const navegador = () => fs.readdirSync('/proc').filter(n => /^\d+$/.test(n)).filter(n => { try { return /chrom|headless/.test(fs.readFileSync(`/proc/${n}/comm`, 'utf8')); } catch { return false; } });
const espera = ms => new Promise(r => setTimeout(r, ms));
(async () => {
  const srv = spawn('python3', ['-m', 'nora', 'hud', '--porta', String(PORTA)], { cwd: '/home/user/nora' });
  await espera(3000);
  const b = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
  const p = await b.newPage({ viewport: { width: 1600, height: 900 } });
  // Conta quadros em que a cena desenhou de verdade (chamadas WebGL), não o rAF do navegador.
  await p.addInitScript(() => {
    window.__desenhos = 0; let sujo = false;
    for (const C of [window.WebGLRenderingContext, window.WebGL2RenderingContext]) if (C) for (const m of ['drawArrays', 'drawElements']) {
      const o = C.prototype[m]; C.prototype[m] = function (...a) { sujo = true; return o.apply(this, a); };
    }
    const f = () => { if (sujo) { window.__desenhos++; sujo = false; } requestAnimationFrame(f); }; requestAnimationFrame(f);
  });
  const erros = []; p.on('pageerror', e => erros.push(e.message));
  await p.goto(`http://127.0.0.1:${PORTA}/`); await espera(4000);
  const res = { ambiente: `Linux x86_64 (nuvem), ${NUCLEOS} núcleos, Chromium headless, WebGL SwiftShader (sem GPU), 1600x900`, motor: await p.evaluate(() => document.getElementById('render-mode')?.textContent), versao: await p.evaluate(() => document.getElementById('versao')?.textContent), medicoes: [] };
  for (const [qual, fps] of [['alta','30'], ['alta','60'], ['baixa','30']]) {
    await p.click('#settings-button'); await p.selectOption('#quality', qual); await p.selectOption('#fps', fps); res.motor = await p.evaluate(() => document.getElementById('render-mode')?.textContent); await p.click('#settings-button'); await espera(2000);
    const pidsB = navegador(), cpuB0 = pidsB.reduce((s, x) => s + tick(x), 0), cpuS0 = tick(srv.pid);
    // quadros desenhados pela cena: conta chamadas reais de desenho do renderer/canvas
    const d0 = await p.evaluate(() => performance.now());
    const q0 = await p.evaluate(() => window.__desenhos);
    await espera(SEG * 1000);
    const q1 = await p.evaluate(() => window.__desenhos), d1 = await p.evaluate(() => performance.now());
    const cpuB = pidsB.reduce((s, x) => s + tick(x), 0) - cpuB0, cpuS = tick(srv.pid) - cpuS0;
    const seg = (d1 - d0) / 1000;
    res.medicoes.push({ qualidade: qual, motor: res.motor, limite_fps: +fps, segundos: +seg.toFixed(1), fps_desenhado: +((q1 - q0) / seg).toFixed(1),
      cpu_navegador_pct_maquina: +(100 * cpuB / HZ / seg / NUCLEOS).toFixed(1), cpu_navegador_pct_nucleo: +(100 * cpuB / HZ / seg).toFixed(1),
      cpu_nora_pct_nucleo: +(100 * cpuS / HZ / seg).toFixed(1) });
  }
  res.erros = erros;
  console.log(JSON.stringify(res, null, 1));
  await b.close(); srv.kill();
})().catch(e => { console.error(e); process.exit(1); });
