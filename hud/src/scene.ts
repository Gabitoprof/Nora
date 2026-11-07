import * as THREE from "three";
import { onda, aleatorio } from "./scene-math";
import { cores, inicial, expressaoEmocional, type Modelo } from "./state";
import { EnvelopeVisual, SILENCIO, aproximar, cadenciaVisual, faixaAcustica, type Dinamica } from "./scene-audio";
export interface QuadroVisual { agora: number; delta: number; reduzido: boolean; cor: string; }
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
  aoDesenhar?: (quadro: QuadroVisual) => void;
  private frame?: number;
  private envelope = new EnvelopeVisual();
  private ultimaAmostra: Modelo["acustica"] = null;
  private cor = new THREE.Color(cores.neutro);
  private alvoCor = new THREE.Color();
  private corParticulas = new THREE.Color();
  private saida: [number,number,number] = [0,0,0];
  private expressao=1;
  private sementes = new Float32Array();
  private faixas: THREE.Line[] = [];
  private anterior = 0;
  private densidade: Qualidade = "alta";
  private fps = 30;
  private reduzido = matchMedia("(prefers-reduced-motion: reduce)");
  private parar = false;
  private sprite?: THREE.CanvasTexture;
  private brilhos?: THREE.Points;
  private aoAmbiente = () => {
    if(this.frame!==undefined) cancelAnimationFrame(this.frame);
    this.frame=undefined;this.anterior=0;
    if(this.parar||document.hidden)return;
    if(this.reduzido.matches) this.desenhar(performance.now(),0);
    else this.agendar();
  };
  constructor(private container: HTMLElement) {
    this.canvas = document.createElement("canvas");
    this.canvas.setAttribute("aria-hidden", "true");
    container.append(this.canvas);
    this.camera.position.z = 12;
    this.preparar();
    this.observador = new ResizeObserver(() => this.redimensionar());
    this.observador.observe(container);
    this.reduzido.addEventListener("change", this.aoAmbiente);
    document.addEventListener("visibilitychange",this.aoAmbiente);
    this.aoAmbiente();
  }
  get motor() {
    return this.renderer ? "WebGL" : "Canvas";
  }
  configurar(qualidade: Qualidade, fps: number) {
    this.densidade = qualidade;
    this.fps = fps === 120 ? 120 : fps === 60 ? 60 : 30;
    this.preparar();
    this.redimensionar();
  }
  atualizar(modelo: Modelo) {
    const mudou=modelo.estado!==this.modelo.estado||modelo.emocao!==this.modelo.emocao||modelo.conectado!==this.modelo.conectado;
    this.modelo=modelo;
    if(modelo.acustica!==this.ultimaAmostra) {
      this.ultimaAmostra=modelo.acustica;
      this.envelope.alimentar(modelo.acustica,performance.now());
    }
    if(!modelo.conectado) this.envelope.silenciar();
    if(this.reduzido.matches&&mudou&&!document.hidden)this.desenhar(performance.now(),0);
  }
  private limpar() {
    [...this.linhas,...this.faixas].forEach((l) => {
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
    this.faixas = [];
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
    const numeroPontos=this.densidade === "alta" ? 12500 : this.densidade === "baixa" ? 4800 : 4200;
    this.sementes=new Float32Array(numeroPontos*6);
    for(let i=0;i<numeroPontos;i++) {
      const giro=i%3===0?-.45:.35;
      this.sementes.set([aleatorio(i),aleatorio(i+15001),aleatorio(i+31002),Math.cos(giro),Math.sin(giro),aleatorio(i+9)],i*6);
    }
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
        for(let i=0;i<5;i++) {
          const geo=new THREE.BufferGeometry();geo.setAttribute("position",new THREE.BufferAttribute(new Float32Array(241*3),3).setUsage(THREE.DynamicDrawUsage));
          const linha=new THREE.Line(geo,new THREE.LineBasicMaterial({color:0xc9c9c9,transparent:true,opacity:i===2?.24:.11,blending:THREE.AdditiveBlending,depthWrite:false}));
          this.faixas.push(linha);this.scene.add(linha);
        }
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
        this.limpar();
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
    if(!document.hidden)this.desenhar(performance.now(),0);
  }
  private ponto(i:number,tempo:number,sinal:Dinamica, destino: Float32Array | [number,number,number], offset=0) {
    const k=i*6,a=this.sementes[k],b=this.sementes[k+1],c=this.sementes[k+2];
    if(i%5===0) {
      const x=(a-.5)*20;
      destino[offset]=x;
      destino[offset+1]=-3.55+Math.sin(x*.55+tempo*.025+b*6)*(.035+sinal.envelope*.09)+b*.16+faixaAcustica(x,b,tempo,sinal);
      destino[offset+2]=-.5;return;
    }
    const t=a*Math.PI*2+tempo*.009,r=4.4+(b-.5)*.72;
    const x=Math.cos(t)*r*1.57,y=Math.sin(t)*r*.52+Math.sin(t*3+b)*.24;
    destino[offset]=x*this.sementes[k+3]-y*this.sementes[k+4];
    destino[offset+1]=x*this.sementes[k+4]+y*this.sementes[k+3];
    destino[offset+2]=(c-.5)*1.5;
  }
  private desenhar(agora:number,delta:number) {
    if(this.parar||document.hidden)return;
    const reduzido=this.reduzido.matches,tempo=reduzido?0:agora/1000;
    if(!reduzido)this.envelope.passo(delta,agora);
    const nivel=0;
    const sinal=reduzido?SILENCIO:this.modelo.estado === "falando"?this.envelope.voz:this.envelope.microfone;
    const voz=sinal;
    this.alvoCor.set(cores[this.modelo.emocao]??cores.neutro);
    this.cor.lerp(this.alvoCor,reduzido?1:aproximar(0,1,delta,550));
    const cor=this.cor;
    this.expressao=reduzido?expressaoEmocional(this.modelo.emocao):aproximar(this.expressao,expressaoEmocional(this.modelo.emocao),delta,550);
    this.corParticulas.set(0xeeeeee).lerp(cor,.28);
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
            nivel, sinal, this.saida, this.expressao,
          );
          coords.setXYZ(j, ...p);
        }
        coords.needsUpdate = true;
        (linha.material as THREE.LineBasicMaterial).color.copy(
          cor,
        );
      });
      this.faixas.forEach((linha,i)=>{
        const coords=linha.geometry.getAttribute("position") as THREE.BufferAttribute;
        for(let j=0;j<=240;j++){const x=j/240*20-10;coords.setXYZ(j,x,-3.5+(i-2)*.022+faixaAcustica(x,i/4,tempo,voz),-.4);}
        coords.needsUpdate=true;(linha.material as THREE.LineBasicMaterial).color.copy(cor);
      });
      if (this.particulas && this.positions) {
        (this.particulas.material as THREE.PointsMaterial).color.copy(this.corParticulas);
        for (let i = 0; i < this.positions.length / 3; i++)
          this.ponto(i,tempo,voz,this.positions,i*3);
        this.particulas.geometry.getAttribute("position").needsUpdate = true;
      }
      if (this.brilhos) {
        const pontos = this.brilhos.geometry.getAttribute("position");
        for (let i = 0; i < 4; i++)
          {const k=[124,319,2481,4768][i]%Math.floor(this.sementes.length/6);this.ponto(k,tempo,voz,this.saida);pontos.setXYZ(i,...this.saida);}
        (this.brilhos.material as THREE.PointsMaterial).color.copy(cor);
        (this.brilhos.material as THREE.PointsMaterial).opacity=.5+voz.envelope*.12*this.expressao;
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
            nivel, sinal, this.saida, this.expressao,
          );
          if (!j) c.moveTo(x, y);
          else c.lineTo(x, y);
        }
        c.strokeStyle = `#${cor.getHexString()}`;
        c.lineWidth = 0.009;
        c.globalAlpha = 0.12 + Math.sin((i / numero) * Math.PI) ** 5 * 0.45;
        c.stroke();
      }
      for(let i=0;i<5;i++) {
        c.beginPath();for(let j=0;j<=240;j++){const x=j/240*20-10,y=-3.5+(i-2)*.022+faixaAcustica(x,i/4,tempo,voz);if(!j)c.moveTo(x,y);else c.lineTo(x,y);}
        c.strokeStyle=`#${cor.getHexString()}`;c.lineWidth=.008;c.globalAlpha=i===2?.24:.11;c.stroke();
      }
      const pontos = this.densidade === "baixa" ? 1900 : 4200;
      c.fillStyle = `#${this.corParticulas.getHexString()}`;
      for (let i = 0; i < pontos; i++) {
        this.ponto(i,tempo,voz,this.saida);
        const [x,y]=this.saida;
        c.globalAlpha = 0.15 + this.sementes[i*6+5] * 0.5;
        c.fillRect(x, y, 0.009, 0.009);
      }
      c.restore();
    }
    this.aoDesenhar?.({agora,delta,reduzido,cor:`#${cor.getHexString()}`});
  }
  private agendar() {
    if(!this.parar&&!document.hidden&&!this.reduzido.matches&&this.frame===undefined)this.frame=requestAnimationFrame(this.animar);
  }
  private animar = (agora:number) => {
    this.frame=undefined;
    const fps=cadenciaVisual(this.fps,this.modelo.jogo||this.modelo.estado==="modo_jogo",this.reduzido.matches,document.hidden);
    if(this.parar||fps===0)return;
    const intervalo=1000/fps,delta=this.anterior===0?intervalo:agora-this.anterior;
    if(delta>=intervalo-.25){this.anterior=agora;this.desenhar(agora,Math.min(delta,250));}
    this.agendar();
  };
  fechar() {
    this.parar = true;
    if(this.frame!==undefined)cancelAnimationFrame(this.frame);
    this.observador.disconnect();
    this.reduzido.removeEventListener("change", this.aoAmbiente);
    document.removeEventListener("visibilitychange",this.aoAmbiente);
    this.limpar();
  }
}
