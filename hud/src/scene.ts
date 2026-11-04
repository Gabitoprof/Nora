import * as THREE from "three";
import { onda, aleatorio } from "./scene-math";
import { cores, inicial, type Modelo } from "./state";
type Qualidade = "alta" | "baixa" | "canvas";
export class Cena {
  private modelo: Modelo = inicial;
  private renderer?: THREE.WebGLRenderer;
  private scene = new THREE.Scene();
  private camera = new THREE.OrthographicCamera(-8, 8, 4.5, -4.5, 0.1, 100);
  private linhas: THREE.Line[] = [];
  private particulas?: THREE.Points;
  private positions?: Float32Array;
  private contexto?: CanvasRenderingContext2D;
  private canvas: HTMLCanvasElement;
  private observador: ResizeObserver;
  private frame = 0;
  private anterior = 0;
  private ultimoTempo = 0;
  private densidade: Qualidade = "alta";
  private fps = 30;
  private reduzido = matchMedia("(prefers-reduced-motion: reduce)");
  private parar = false;
  private sprite?: THREE.CanvasTexture;
  private brilhos?: THREE.Points;
  private aoReduzir = () => {
    cancelAnimationFrame(this.frame);
    this.animar(0);
  };
  constructor(private container: HTMLElement) {
    this.canvas = document.createElement("canvas");
    this.canvas.setAttribute("aria-hidden", "true");
    container.append(this.canvas);
    this.camera.position.z = 12;
    this.preparar();
    this.observador = new ResizeObserver(() => this.redimensionar());
    this.observador.observe(container);
    this.reduzido.addEventListener("change", this.aoReduzir);
    this.animar(0);
  }
  get motor() {
    return this.renderer ? "WebGL" : "Canvas";
  }
  configurar(qualidade: Qualidade, fps: number) {
    this.densidade = qualidade;
    this.fps = fps === 60 ? 60 : 30;
    this.preparar();
    this.redimensionar();
  }
  atualizar(modelo: Modelo) {
    this.modelo = modelo;
    if (this.reduzido.matches) this.desenhar(this.ultimoTempo);
  }
  private limpar() {
    this.linhas.forEach((l) => {
      l.geometry.dispose();
      (l.material as THREE.Material).dispose();
    });
    if (this.particulas) {
      this.particulas.geometry.dispose();
      (this.particulas.material as THREE.Material).dispose();
    }
    if (this.brilhos) {
      this.brilhos.geometry.dispose();
      (this.brilhos.material as THREE.Material).dispose();
      this.brilhos = undefined;
    }
    this.sprite?.dispose();
    this.scene.clear();
    this.linhas = [];
    this.particulas = undefined;
    this.renderer?.dispose();
    this.renderer = undefined;
  }
  private preparar() {
    this.limpar();
    // Contextos Canvas/WebGL não podem compartilhar o mesmo elemento após criação.
    const novo = document.createElement("canvas");
    novo.setAttribute("aria-hidden", "true");
    this.canvas.replaceWith(novo);
    this.canvas = novo;
    this.contexto = undefined;
    if (this.densidade !== "canvas") {
      try {
        this.renderer = new THREE.WebGLRenderer({
          canvas: this.canvas,
          alpha: true,
          antialias: true,
          powerPreference: "low-power",
        });
        this.renderer.setPixelRatio(Math.min(devicePixelRatio, 1.5));
        this.renderer.setClearColor(0x000000, 0);
        const numero = this.densidade === "alta" ? 38 : 22;
        for (let i = 0; i < numero; i++) {
          const geo = new THREE.BufferGeometry();
          geo.setAttribute(
            "position",
            new THREE.BufferAttribute(new Float32Array(241 * 3), 3).setUsage(
              THREE.DynamicDrawUsage,
            ),
          );
          const material = new THREE.LineBasicMaterial({
            color: 0xdedede,
            transparent: true,
            opacity:
              0.14 + 0.45 * Math.pow(Math.sin((i / numero) * Math.PI), 5),
            blending: THREE.AdditiveBlending,
            depthWrite: false,
          });
          const linha = new THREE.Line(geo, material);
          this.linhas.push(linha);
          this.scene.add(linha);
        }
        const numeroPontos = this.densidade === "alta" ? 12500 : 4800;
        this.positions = new Float32Array(numeroPontos * 3);
        const geo = new THREE.BufferGeometry();
        geo.setAttribute(
          "position",
          new THREE.BufferAttribute(this.positions, 3).setUsage(
            THREE.DynamicDrawUsage,
          ),
        );
        const coresParticulas = new Float32Array(numeroPontos * 3);
        for (let i = 0; i < numeroPontos; i++) {
          const brilho = 0.2 + aleatorio(i + 5) * 0.8;
          coresParticulas.set([brilho, brilho, brilho], i * 3);
        }
        geo.setAttribute(
          "color",
          new THREE.BufferAttribute(coresParticulas, 3),
        );
        const stamp = document.createElement("canvas");
        stamp.width = stamp.height = 24;
        const c = stamp.getContext("2d")!;
        const grad = c.createRadialGradient(12, 12, 0, 12, 12, 12);
        grad.addColorStop(0, "#ffffff");
        grad.addColorStop(0.2, "#ffffff");
        grad.addColorStop(1, "#ffffff00");
        c.fillStyle = grad;
        c.fillRect(0, 0, 24, 24);
        this.sprite = new THREE.CanvasTexture(stamp);
        this.particulas = new THREE.Points(
          geo,
          new THREE.PointsMaterial({
            size: 0.028,
            map: this.sprite,
            vertexColors: true,
            transparent: true,
            opacity: 0.74,
            blending: THREE.AdditiveBlending,
            depthWrite: false,
            sizeAttenuation: true,
          }),
        );
        this.scene.add(this.particulas);
        const brilhoGeo = new THREE.BufferGeometry();
        brilhoGeo.setAttribute(
          "position",
          new THREE.BufferAttribute(new Float32Array(12), 3),
        );
        this.brilhos = new THREE.Points(
          brilhoGeo,
          new THREE.PointsMaterial({
            size: 0.13,
            map: this.sprite,
            color: 0xffffff,
            transparent: true,
            opacity: 0.6,
            blending: THREE.AdditiveBlending,
            depthWrite: false,
          }),
        );
        this.scene.add(this.brilhos);
        this.canvas.addEventListener(
          "webglcontextlost",
          (e) => {
            e.preventDefault();
            this.configurar("canvas", this.fps);
          },
          { once: true },
        );
      } catch {
        this.renderer = undefined;
      }
    }
    if (!this.renderer) {
      const canvas = document.createElement("canvas");
      canvas.setAttribute("aria-hidden", "true");
      this.canvas.replaceWith(canvas);
      this.canvas = canvas;
      this.contexto = canvas.getContext("2d") ?? undefined;
    }
    this.container.dataset.motor = this.motor;
  }
  private redimensionar() {
    const w = this.container.clientWidth,
      h = this.container.clientHeight;
    const aspecto = w / Math.max(h, 1);
    const altura = aspecto < 1 ? 12 : 9.5;
    this.camera.left = (-altura * aspecto) / 2;
    this.camera.right = (altura * aspecto) / 2;
    this.camera.top = altura / 2;
    this.camera.bottom = -altura / 2;
    this.camera.updateProjectionMatrix();
    if (this.renderer) this.renderer.setSize(w, h);
    else {
      this.canvas.width = w * Math.min(devicePixelRatio, 1.5);
      this.canvas.height = h * Math.min(devicePixelRatio, 1.5);
    }
    this.desenhar(this.ultimoTempo);
  }
  private ponto(i: number, tempo: number): [number, number, number] {
    const a = aleatorio(i),
      b = aleatorio(i + 15001),
      c = aleatorio(i + 31002);
    if (i % 5 === 0) {
      const x = (a - 0.5) * 20,
        z = b * 6;
      return [
        x,
        -4.1 + Math.sin(x * 0.55 + tempo * 0.12 + z) * 0.28 + z * 0.055,
        -0.5,
      ];
    }
    const t = a * Math.PI * 2 + tempo * 0.018;
    const r = 4.4 + (b - 0.5) * 0.72;
    const giro = i % 3 === 0 ? -0.45 : 0.35;
    let x = Math.cos(t) * r * 1.57;
    let y = Math.sin(t) * r * 0.52 + Math.sin(t * 3 + b) * 0.24;
    const xx = x * Math.cos(giro) - y * Math.sin(giro);
    y = x * Math.sin(giro) + y * Math.cos(giro);
    x = xx;
    return [x, y, (c - 0.5) * 1.5];
  }
  private desenhar(tempo: number) {
    this.ultimoTempo = tempo;
    const cor = new THREE.Color(cores[this.modelo.emocao] ?? cores.neutro);
    const nivel = this.modelo.conectado ? this.modelo.nivel_audio : 0;
    if (this.renderer) {
      this.linhas.forEach((linha, i) => {
        const coords = linha.geometry.getAttribute(
          "position",
        ) as THREE.BufferAttribute;
        for (let j = 0; j <= 240; j++) {
          const p = onda(
            (j / 240) * Math.PI * 2,
            i / this.linhas.length,
            tempo,
            this.modelo.estado,
            nivel,
          );
          coords.setXYZ(j, ...p);
        }
        coords.needsUpdate = true;
        (linha.material as THREE.LineBasicMaterial).color.copy(
          i % 5 === 0 ? cor : new THREE.Color(0xc9c9c9),
        );
      });
      if (this.particulas && this.positions) {
        for (let i = 0; i < this.positions.length / 3; i++)
          this.positions.set(this.ponto(i, tempo), i * 3);
        this.particulas.geometry.getAttribute("position").needsUpdate = true;
      }
      if (this.brilhos) {
        const pontos = this.brilhos.geometry.getAttribute("position");
        for (let i = 0; i < 4; i++)
          pontos.setXYZ(i, ...this.ponto([124, 319, 2481, 4768][i], tempo));
        pontos.needsUpdate = true;
      }
      this.renderer.render(this.scene, this.camera);
    } else if (this.contexto) {
      const c = this.contexto,
        w = this.canvas.width,
        h = this.canvas.height;
      c.clearRect(0, 0, w, h);
      const escala = h / (w / h < 1 ? 12 : 9.5);
      c.save();
      c.translate(w / 2, h / 2);
      c.scale(escala, -escala);
      const numero = this.densidade === "baixa" ? 20 : 34;
      for (let i = 0; i < numero; i++) {
        c.beginPath();
        for (let j = 0; j <= 200; j++) {
          const [x, y] = onda(
            (j / 200) * Math.PI * 2,
            i / numero,
            tempo,
            this.modelo.estado,
            nivel,
          );
          if (!j) c.moveTo(x, y);
          else c.lineTo(x, y);
        }
        c.strokeStyle = i % 5 === 0 ? `#${cor.getHexString()}` : "#d4d4d4";
        c.lineWidth = 0.009;
        c.globalAlpha = 0.12 + Math.sin((i / numero) * Math.PI) ** 5 * 0.45;
        c.stroke();
      }
      const pontos = this.densidade === "baixa" ? 1900 : 4200;
      c.fillStyle = "#eeeeee";
      for (let i = 0; i < pontos; i++) {
        const [x, y] = this.ponto(i, tempo);
        c.globalAlpha = 0.15 + aleatorio(i + 9) * 0.5;
        c.fillRect(x, y, 0.009, 0.009);
      }
      c.restore();
    }
  }
  private animar = (agora: number) => {
    if (this.parar) return;
    if (document.hidden) {
      this.frame = requestAnimationFrame(this.animar);
      return;
    }
    if (
      agora - this.anterior >=
        1000 / (this.modelo.estado === "modo_jogo" ? 8 : this.fps) ||
      agora === 0
    ) {
      this.anterior = agora;
      this.desenhar(this.reduzido.matches ? 0 : agora / 1000);
    }
    if (!this.reduzido.matches) this.frame = requestAnimationFrame(this.animar);
  };
  fechar() {
    this.parar = true;
    cancelAnimationFrame(this.frame);
    this.observador.disconnect();
    this.reduzido.removeEventListener("change", this.aoReduzir);
    this.limpar();
  }
}
