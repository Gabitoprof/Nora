import { describe, expect, it } from "vitest";
import { NuvemLetras, SEM_VIDA } from "../src/text-particle-field";
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
  contexto={clearRect:()=>{this.limpezas++;},fillRect:()=>{},fillText:()=>{},beginPath:()=>{},moveTo:()=>{},lineTo:()=>{},stroke:()=>{},measureText:(t:string)=>({width:Math.max(40,t.length*30)}),getImageData:()=>{
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

describe("faixa superior: linha da fala sem piscar e sem adiantar palavras",()=>{
  beforeEach(()=>vi.stubGlobal("document",{createElement:()=>new CanvasDeTeste()}));
  afterEach(()=>vi.unstubAllGlobals());
  const linha:FalaTemporizada={id:7,duracao_ms:1600,precisao:"alinhada",palavras:[
    {texto:"um",inicio_ms:0,fim_ms:200,destaque:false},{texto:"dois",inicio_ms:280,fim_ms:500,destaque:false},
    {texto:"tres",inicio_ms:1200,fim_ms:1400,destaque:false}]};
  const criar=()=>{
    const canvas=new CanvasDeTeste(),legenda={hidden:true,textContent:""};
    const p=new PalavrasParticulas(canvas as unknown as HTMLCanvasElement,legenda as unknown as HTMLElement);
    const m:Modelo={...inicial,conectado:true,privacidade:false,estado:"falando",fala_temporizada:linha};
    return {p,canvas,legenda,m};
  };
  const tocar=(p:PalavrasParticulas,m:Modelo,pos:number,agora:number)=>{p.atualizar({...m,acustica:audio(pos,7)},true,false,agora);p.desenhar(agora,"#d8e1e5",false,16);};
  it("pausa curta entre palavras: a palavra segura, sem dispersar",()=>{
    const {p,canvas,m}=criar();
    tocar(p,m,100,0);expect(canvas.attrs.get("aria-label")).toContain("um");
    tocar(p,m,240,140);expect(canvas.dataset.fase).not.toBe("dispersando");expect(canvas.attrs.get("aria-label")).toContain("um");
    tocar(p,m,300,200);expect(canvas.attrs.get("aria-label")).toContain("dois");
  });
  it("pausa longa: depois do limite a linha se desfaz",()=>{
    const {p,canvas,m}=criar();
    tocar(p,m,300,0);
    for(let t=50,pos=550;t<=500;t+=50,pos+=50)tocar(p,m,pos,t);
    expect(canvas.dataset.fase).toBe("dispersando");expect(canvas.attrs.has("aria-label")).toBe(false);
  });
  it("palavras já ditas entram apagadas na mesma nuvem; as próximas nunca aparecem antes",()=>{
    const {p,m}=criar();
    const chamadas:{texto:string;anteriores:readonly string[]}[]=[];
    const original=p.campo.definirTexto.bind(p.campo);
    p.campo.definirTexto=(texto,agora,imediato,anteriores=[])=>{chamadas.push({texto,anteriores:[...anteriores]});original(texto,agora,imediato,anteriores);};
    tocar(p,m,100,0);tocar(p,m,300,200);
    expect(chamadas.map(c=>c.texto)).toEqual(["um","dois"]);
    expect(chamadas[1].anteriores).toEqual(["um"]);
    for(const c of chamadas)expect(c.anteriores).not.toContain("tres");
    // os destinos da palavra anterior têm peso menor (mais apagados)
    const pesos=Array.from(p.campo.nuvem.peso.subarray(0,p.campo.nuvem.alvos));
    expect(Math.min(...pesos)).toBeLessThan(1);expect(Math.max(...pesos)).toBe(1);
  });
  it("fala nova começa a linha do zero",()=>{
    const {p,m}=criar();
    const vistos:(readonly string[])[]=[];
    const original=p.campo.definirTexto.bind(p.campo);
    p.campo.definirTexto=(texto,agora,imediato,anteriores=[])=>{vistos.push([...anteriores]);original(texto,agora,imediato,anteriores);};
    tocar(p,m,100,0);tocar(p,m,300,200);
    const nova={...linha,id:8};
    p.atualizar({...m,fala_temporizada:nova,acustica:audio(100,8)},true,false,260);p.desenhar(260,"#d8e1e5",false,16);
    expect(vistos[vistos.length-1]).toEqual([]);
  });
});

import contrato from "../../src/nora/hud_contrato.json";
import { reduzir } from "../src/state";
describe("contrato do fim da reprodução",()=>{
  it("o backend e a HUD conhecem reproducao_encerrada, só com números e o motivo",()=>{
    expect(contrato.campos.reproducao_encerrada).toEqual(["id","posicao_ms","duracao_ms","interrompida"]);
    const m:Modelo={...inicial,conectado:true,sequencia:3,estado:"falando"};
    const depois=reduzir(m,{...evFim(),sequencia:5});
    expect(depois.sequencia).toBe(5);expect(depois.estado).toBe("falando");
  });
});

describe("marca viva: a letra formada não fica parada",()=>{
  const forma=new Float32Array(Array.from({length:400},(_,i)=>i%2?60+(i%7):100+i));
  const viva=(energia=0)=>{const n=new NuvemLetras(800,960,180);n.vida={...SEM_VIDA,tremor:1.1,fluxo:.07,poeira:.16,extras:320};n.energia=energia;n.definirAlvos(forma,0,true);return n;};
  const desvio=(n:NuvemLetras)=>{let soma=0,soltos=0;for(let i=0;i<n.alvos;i++){const d=Math.hypot(n.x[i]-n.alvoX[i],n.y[i]-n.alvoY[i]);soma+=d;if(d>15)soltos++;}return {medio:soma/n.alvos,soltos:soltos/n.alvos};};
  const rodar=(n:NuvemLetras,ate:number)=>{for(let t=16;t<=ate;t+=16)n.passo(t,16);};
  it("os pontos se mexem em volta da letra e continuam legíveis",()=>{
    const n=viva();rodar(n,3000);const x=Float32Array.from(n.x);n.passo(3016,16);
    expect(n.x.some((v,i)=>v!==x[i])).toBe(true);
    const {medio,soltos}=desvio(n);expect(medio).toBeGreaterThan(.3);expect(soltos).toBeLessThan(.2);
  });
  it("uns pontos se soltam para a poeira e voltam (troca contínua)",()=>{
    const n=viva();const vistos=new Set<number>();
    for(let t=16;t<=12000;t+=16){n.passo(t,16);for(let i=0;i<n.alvos;i++)if(Math.hypot(n.x[i]-n.alvoX[i],n.y[i]-n.alvoY[i])>15)vistos.add(i);}
    expect(vistos.size/n.alvos).toBeGreaterThan(.5);expect(desvio(n).soltos).toBeLessThan(.2);
    // poeira livre em volta, visível
    expect(n.quantidade).toBe(n.alvos+320);expect(n.alpha[n.alvos+5]).toBeGreaterThan(.1);
  });
  it("a voz aumenta o movimento",()=>{
    const calma=viva(0),falando=viva(.8);rodar(calma,2000);rodar(falando,2000);
    expect(desvio(falando).medio).toBeGreaterThan(desvio(calma).medio*1.5);
  });
  it("movimento reduzido: parada, exatamente na letra",()=>{
    const n=viva(.8);n.passo(500,16,true);
    for(let i=0;i<n.alvos;i++){expect(n.x[i]).toBe(n.alvoX[i]);expect(n.y[i]).toBe(n.alvoY[i]);}
  });
  it("sem vida (padrão), a letra assenta parada como antes",()=>{
    const n=new NuvemLetras(800,960,180);n.definirAlvos(forma,0,true);rodar(n,1000);
    expect(desvio(n).medio).toBeLessThan(.01);
  });
});

describe("letras feitas da poeira da cena (origem)",()=>{
  const forma=new Float32Array(Array.from({length:200},(_,i)=>i%2?90:300+i));
  const criar=()=>{
    const n=new NuvemLetras(400,960,180);
    n.vida={...SEM_VIDA,chegada:1000,rigidezChegada:7,extras:0};
    // poeira girando longe da letra
    n.origem=(i,s)=>{s[0]=-400+Math.cos(i)*50;s[1]=900+Math.sin(i)*50;return true;};
    return n;
  };
  it("cada ponto parte do seu grão de poeira, em fluxo (escalonado), e chega à letra",()=>{
    const n=criar();n.passo(0,16);n.definirAlvos(forma,0);
    n.passo(16,16);
    const longe=(i:number)=>Math.hypot(n.x[i]-n.alvoX[i],n.y[i]-n.alvoY[i]);
    // no começo todos estão na poeira, longe da letra
    for(let i=0;i<n.alvos;i++)expect(longe(i)).toBeGreaterThan(300);
    for(let t=32;t<=600;t+=16)n.passo(t,16);
    // a meio caminho: uns já saíram, outros ainda esperam a vez
    const saiu=[...Array(n.alvos).keys()].filter(i=>longe(i)<600).length;
    expect(saiu).toBeGreaterThan(0);expect(saiu).toBeLessThan(n.alvos);
    for(let t=616;t<=3000;t+=16)n.passo(t,16);
    expect(n.fase).toBe("retendo");
    for(let i=0;i<n.alvos;i++)expect(longe(i)).toBeLessThan(3);
  });
  it("ao dispersar, os pontos voltam para a poeira e somem",()=>{
    const n=criar();n.passo(0,16);n.definirAlvos(forma,0,true);n.dispersar(100);
    for(let t=116;t<=650;t+=16)n.passo(t,16);
    const media=[...Array(n.alvos).keys()].reduce((s,i)=>s+Math.hypot(n.x[i]-(-400+Math.cos(i)*50),n.y[i]-(900+Math.sin(i)*50)),0)/n.alvos;
    expect(media).toBeLessThan(300);
    for(let t=666;t<=900;t+=16)n.passo(t,16);
    expect(n.fase).toBe("poeira");
  });
});
