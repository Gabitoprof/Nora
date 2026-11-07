import { describe, expect, it } from "vitest";
import { NuvemLetras } from "../src/text-particle-field";
import { RelogioFala, ultimaPalavraDevida } from "../src/word-particles";
import type { Acustica } from "../src/scene-audio";
import type { FalaTemporizada } from "../src/state";
const alvos = new Float32Array([200,50,205,55,210,60,215,65,220,70,225,75]);
const fala: FalaTemporizada = {id:4,duracao_ms:1000,precisao:"alinhada",palavras:[{texto:"primeira",inicio_ms:0,fim_ms:240,destaque:false},{texto:"última",inicio_ms:800,fim_ms:1000,destaque:false}]};
const audio = (posicao_ms:number,id=4):Acustica=>({fonte:"voz",rms:.2,pico:.3,envelope:.2,bandas:[0,0,0,0,0,0],centroide:0,fluxo:0,ativo:true,reproducao_id:id,posicao_ms,duracao_ms:1000});
const erro = (n:NuvemLetras)=>{let soma=0;for(let i=0;i<n.alvos;i++)soma+=Math.hypot(n.x[i]-n.alvoX[i],n.y[i]-n.alvoY[i]);return soma/n.alvos;};
describe("poeira constrói materialmente o glifo",()=>{
  it("inicia solta, migra sem saltar, retém legível e desagrega",()=>{
    const n=new NuvemLetras(100);n.definirAlvos(alvos,0);
    const inicial=erro(n),x0=n.x[0];expect(inicial).toBeGreaterThan(30);expect(n.fase).toBe("formando");
    n.passo(16,16);expect(n.x[0]).not.toBe(x0);expect(erro(n)).toBeGreaterThan(1);expect(erro(n)).toBeLessThan(inicial);
    for(let t=32;t<=192;t+=16)n.passo(t,16);
    expect(erro(n)).toBeLessThan(1);expect(n.fase).toBe("retendo");expect(n.alpha[0]).toBeGreaterThan(.5);
    const x=n.x[0],alpha=n.alpha[0];n.dispersar(200);n.passo(232,32);
    expect(n.fase).toBe("dispersando");expect(n.x[0]).not.toBe(x);expect(n.alpha[0]).toBeLessThan(alpha);
    n.passo(1000,100);expect(n.fase).toBe("poeira");expect(n.quantidade).toBe(0);
  });
  it("pool e IDs sobrevivem ao glifo seguinte sem novas arrays por quadro",()=>{
    const n=new NuvemLetras(80),x=n.x,v=n.vx,alpha=n.alpha,ids=n.ids;
    n.definirAlvos(alvos,0);n.passo(100,100);const antes=n.x[0];
    n.definirAlvos(new Float32Array([600,50,610,60]),120);expect(n.x[0]).toBe(antes);
    for(let t=136;t<500;t+=16)n.passo(t,16);
    expect(n.x).toBe(x);expect(n.vx).toBe(v);expect(n.alpha).toBe(alpha);expect(n.ids).toBe(ids);expect(n.ids[0]).toBe(0);expect(n.quantidade).toBeLessThanOrEqual(80);
  });
  it("simulação analítica corresponde em 30, 60 e 120 FPS",()=>{
    const simular=(fps:number)=>{const n=new NuvemLetras(80);n.definirAlvos(alvos,0);for(let i=1;i<=fps/5;i++)n.passo(i*1000/fps,1000/fps);return n;};
    const a=simular(30),b=simular(60),c=simular(120);
    for(let i=0;i<a.alvos;i++){expect(a.x[i]).toBeCloseTo(b.x[i],3);expect(b.x[i]).toBeCloseTo(c.x[i],3);expect(a.alpha[i]).toBeCloseTo(c.alpha[i],5);}
  });
  it("movimento reduzido mantém máscara estática e privacidade apaga destinos e velocidades",()=>{
    const n=new NuvemLetras(80);n.definirAlvos(alvos,0);n.passo(0,0,true);
    expect(n.x[0]).toBe(n.alvoX[0]);expect(n.vx[0]).toBe(0);expect(n.alpha[0]).toBeGreaterThan(.5);
    n.limpar();expect(n.quantidade).toBe(0);expect(n.alvos).toBe(0);
    for(const buffer of [n.alpha,n.alvoX,n.alvoY,n.vx,n.vy])expect(buffer.every(v=>v===0)).toBe(true);
  });
  it("cap de partículas e frames extremos não geram explosão nem valores não finitos",()=>{
    const n=new NuvemLetras(128);n.definirAlvos(new Float32Array(5000).fill(45),0);expect(n.alvos).toBe(128);
    for(const dt of [-20,0,8,16,33,125,20000])n.passo(100,dt);
    for(const buffer of [n.x,n.y,n.vx,n.vy,n.alpha])expect(buffer.every(Number.isFinite)).toBe(true);
  });
});
describe("agenda usa somente playback e protege final/alinhamento",()=>{
  it("pacote atrasado de offset menor não rebobina palavra no mesmo id",()=>{
    const r=new RelogioFala();r.atualizar(audio(850),100);expect(r.palavra(fala,100)?.palavra.texto).toBe("última");
    r.atualizar(audio(50),110);expect(r.palavra(fala,110)?.palavra.texto).toBe("última");
  });
  it("timeline incremental só revela a palavra temporalmente devida",()=>{
    const r=new RelogioFala();r.atualizar(audio(100),10);
    expect(r.palavra({...fala,palavras:[fala.palavras[0]]},10)?.palavra.texto).toBe("primeira");
    expect(r.palavra(fala,10)?.palavra.texto).toBe("primeira");expect(r.palavra(fala,320)).toBeNull();
    r.atualizar(audio(820),400);expect(r.palavra(fala,400)?.palavra.texto).toBe("última");
  });
  it("fim natural protege a última palavra, cancelamento não a ressuscita",()=>{
    expect(ultimaPalavraDevida(fala,4,1000,1000,false)?.texto).toBe("última");
    expect(ultimaPalavraDevida(fala,4,850,1000,false)).toBeNull();
    expect(ultimaPalavraDevida(fala,4,1000,1000,true)).toBeNull();
    expect(ultimaPalavraDevida(fala,3,1000,1000,false)).toBeNull();
    expect(ultimaPalavraDevida(null,4,1000,1000,false)).toBeNull();
  });
});

// DOM mínimo para exercitar o controlador Canvas sem introduzir outra dependência.
import { afterEach, beforeEach, vi } from "vitest";
import { PalavrasParticulas } from "../src/word-particles";
import { inicial, type Evento, type Modelo } from "../src/state";
class CanvasDeTeste {
  width=1200; height=140; hidden=true; dataset:Record<string,string>={}; attrs=new Map<string,string>();
  limpezas=0;
  contexto={clearRect:()=>{this.limpezas++;},fillRect:()=>{},fillText:()=>{},measureText:()=>({width:300}),getImageData:()=>{
    const data=new Uint8ClampedArray(this.width*this.height*4);for(let y=40;y<80;y+=2)for(let x=350;x<450;x+=2)data[(y*this.width+x)*4+3]=255;return {data};
  }};
  getContext(){return this.contexto;}
  setAttribute(k:string,v:string){this.attrs.set(k,v);}
  removeAttribute(k:string){this.attrs.delete(k);}
}
const evFim=(interrompida=false):Evento=>({versao:1,sequencia:4,tipo:"reproducao_encerrada",dados:{id:4,posicao_ms:1000,duracao_ms:1000,interrompida},instante:"2026-11-07T00:00:00"});
describe("controlador: privacidade, último glifo e acessibilidade",()=>{
  beforeEach(()=>vi.stubGlobal("document",{createElement:()=>new CanvasDeTeste()}));
  afterEach(()=>vi.unstubAllGlobals());
  const criar=()=>{
    const canvas=new CanvasDeTeste(),legenda={hidden:true,textContent:""};
    const p=new PalavrasParticulas(canvas as unknown as HTMLCanvasElement,legenda as unknown as HTMLElement);
    const m:Modelo={...inicial,conectado:true,privacidade:false,estado:"falando",fala_temporizada:fala,acustica:audio(100)};
    return {p,canvas,legenda,m};
  };
  it("privacidade interrompe no mesmo evento, sem aguardar RAF, apagando máscara e legenda",()=>{
    const {p,canvas,legenda,m}=criar();p.atualizar(m,true,false,0);p.desenhar(50,"#d8e1e5",false,50);
    expect(canvas.attrs.get("aria-label")).toContain("primeira");expect(p.campo.nuvem.quantidade).toBeGreaterThan(0);
    p.atualizar({...m,privacidade:true,fala_temporizada:null},true,false,60);
    expect(canvas.hidden).toBe(true);expect(legenda.textContent).toBe("");expect(canvas.attrs.has("aria-label")).toBe(false);
    expect(p.campo.nuvem.quantidade).toBe(0);expect(p.campo.nuvem.alvoX.every(v=>v===0)).toBe(true);
  });
  it("fim natural oferece último glifo devido e dissolve sem reaparecer por atualização de estado",()=>{
    const {p,canvas,m}=criar();p.atualizar({...m,acustica:audio(850)},true,false,0);p.desenhar(10,"#d8e1e5",false,10);
    p.receberEvento(evFim(),20);
    const terminado={...m,fala_temporizada:null,estado:"ouvindo" as const,acustica:{...audio(1000),ativo:false}};
    p.atualizar(terminado,true,false,20);p.desenhar(50,"#d8e1e5",false,30);
    expect(canvas.attrs.get("aria-label")).toContain("última");
    p.desenhar(160,"#d8e1e5",false,100);expect(canvas.dataset.fase).toBe("dispersando");
    p.atualizar(terminado,true,false,180);p.desenhar(190,"#d8e1e5",false,30);
    expect(canvas.dataset.fase).toBe("dispersando");expect(canvas.attrs.has("aria-label")).toBe(false);
  });
  it("interrupção, desconexão e resposta nova eliminam conteúdo anterior imediatamente",()=>{
    const {p,canvas,m}=criar();p.atualizar(m,true,false,0);p.desenhar(50,"#d8e1e5",false,50);
    p.receberEvento(evFim(true),60);expect(canvas.hidden).toBe(true);
    p.receberEvento({...evFim(),tipo:"conectado",dados:{}},70);expect(p.campo.nuvem.quantidade).toBe(0);
    p.atualizar({...m,acustica:audio(100,5),fala_temporizada:{...fala,id:5}},true,false,80);p.desenhar(100,"#d8e1e5",false,20);
    p.receberEvento(evFim(),110);expect(canvas.attrs.get("aria-label")).toContain("primeira");
    p.atualizar({...m,acustica:audio(850,4)},true,false,120);p.desenhar(130,"#d8e1e5",false,30);
    expect(canvas.attrs.get("aria-label") ?? "").not.toContain("última");
  });
  it("reduzido entrega palavra estática autorizada, sem animação, e retorna às partículas",()=>{
    const {p,canvas,legenda,m}=criar();p.atualizar(m,true,true,0);
    expect(canvas.hidden).toBe(true);expect(legenda.hidden).toBe(false);expect(legenda.textContent).toContain("primeira");expect(p.campo.nuvem.quantidade).toBe(0);
    p.atualizar(m,true,false,20);p.desenhar(30,"#d8e1e5",false,30);
    expect(canvas.hidden).toBe(false);expect(p.campo.nuvem.quantidade).toBeGreaterThan(0);
  });
  it("atualizações de estado não renovam relógio vencido nem exibem texto sem consentimento",()=>{
    const {p,canvas,legenda,m}=criar();p.atualizar(m,true,false,0);p.desenhar(50,"#d8e1e5",false,50);
    p.atualizar({...m,emocao:"calma"},true,false,600);p.desenhar(610,"#d8e1e5",false,30);
    expect(legenda.textContent).toBe("");expect(canvas.attrs.has("aria-label")).toBe(false);
    p.atualizar({...m,privacidade:true},true,true,620);expect(legenda.textContent).toBe("");
  });
});
