import type { Acustica } from "./scene-audio";
import type { FalaTemporizada, Modelo, PalavraTemporizada } from "./state";
import { aleatorio } from "./scene-math";
/** Relógio da mídia, nunca do estado `falando` nem do tamanho do texto. */
export class RelogioFala {
  private amostra: Acustica | null = null;
  private recebida = -Infinity;
  private encerrado = -1;
  atualizar(amostra: Acustica | null, agora: number) {
    if(amostra?.fonte === "voz") {
      if(amostra.reproducao_id<=this.encerrado || this.amostra && amostra.reproducao_id<this.amostra.reproducao_id)return;
      this.amostra=amostra;this.recebida=agora;
      if(!amostra.ativo)this.encerrado=amostra.reproducao_id;
    }
  }
  limpar() { this.amostra=null; this.recebida=-Infinity; this.encerrado=-1; }
  palavra(fala:FalaTemporizada|null, agora:number): { palavra:PalavraTemporizada; posicao:number } | null {
    const a=this.amostra;
    // RAF entrega o timestamp do início do frame: pode preceder a chegada SSE.
    const decorrido=Math.max(0,agora-this.recebida);
    if(!a?.ativo||!fala||fala.id!==a.reproducao_id||decorrido>300||a.rms<.002) return null;
    const posicao=Math.min(a.duracao_ms || fala.duracao_ms, a.posicao_ms+Math.min(decorrido,250));
    const palavra=fala.palavras.find(p=>posicao>=p.inicio_ms&&posicao<p.fim_ms);
    return palavra ? {palavra,posicao} : null;
  }
}
export class PalavrasParticulas {
  private relogio=new RelogioFala();
  private ultimaAmostra: Acustica|null=null;
  private fala:FalaTemporizada|null=null;
  private ativa=false;
  private chave="";
  private pontos: number[]=[];
  private contexto:CanvasRenderingContext2D|null;
  private mascara=document.createElement("canvas");
  constructor(private canvas:HTMLCanvasElement, private legenda:HTMLElement) {
    canvas.width=1200;canvas.height=140;
    this.mascara.width=1200;this.mascara.height=140;
    this.contexto=canvas.getContext("2d");
  }
  atualizar(modelo:Modelo, habilitada:boolean, reduzido:boolean, agora=performance.now()) {
    this.ativa=habilitada&&!reduzido&&!modelo.privacidade&&modelo.conectado;
    if(!this.ativa) { this.limpar(); this.ultimaAmostra=modelo.acustica; return; }
    this.fala=modelo.fala_temporizada;
    if(modelo.acustica!==this.ultimaAmostra) {
      this.ultimaAmostra=modelo.acustica;
      this.relogio.atualizar(modelo.acustica,agora);
    }
    if(!this.fala) { this.apagar(); return; }
    if(modelo.acustica?.fonte==="voz"&&!modelo.acustica.ativo) this.apagar();
  }
  private apagar() {
    this.canvas.hidden=true;this.legenda.hidden=true;
    this.legenda.textContent="";this.canvas.removeAttribute("aria-label");
    this.contexto?.clearRect(0,0,1200,140);
    this.chave="";this.pontos=[];
  }
  limpar() { this.relogio.limpar();this.ultimaAmostra=null;this.fala=null;this.apagar(); }
  desenhar(agora:number,cor:string,reduzido:boolean) {
    const alvo=this.ativa&&!reduzido?this.relogio.palavra(this.fala,agora):null;
    const c=this.contexto;
    if(!alvo||!c) { if(!this.canvas.hidden) this.apagar();return; }
    const {palavra,posicao}=alvo;
    const chave=`${this.fala!.id}:${palavra.inicio_ms}:${palavra.texto}`;
    if(chave!==this.chave) {
      this.chave=chave;
      const m=this.mascara.getContext("2d",{willReadFrequently:true});
      if(!m)return;
      m.clearRect(0,0,1200,140);m.fillStyle="#fff";m.textAlign="center";m.textBaseline="middle";
      m.font="500 84px 'Segoe UI', sans-serif";
      const largura=m.measureText(palavra.texto).width;
      if(largura>1080)m.font=`500 ${84*1080/largura}px 'Segoe UI', sans-serif`;
      m.fillText(palavra.texto,600,70);
      const pixels=m.getImageData(0,0,1200,140).data;
      this.pontos=[];
      for(let y=8;y<132;y+=3)for(let x=20;x<1180;x+=3)if(pixels[(y*1200+x)*4+3]>90)this.pontos.push(x,y);
      if(this.pontos.length>3200) { const origem=this.pontos;this.pontos=[];const passo=origem.length/3200;for(let i=0;i<1600;i++){const j=Math.floor(i*passo/2)*2;this.pontos.push(origem[j],origem[j+1]);} }
      const estimada=this.fala!.precisao==="estimada";
      this.legenda.textContent=`${palavra.texto} · ${estimada?"tempo estimado no áudio":"tempo alinhado ao áudio"}`;
      this.canvas.setAttribute("aria-label",`Palavra atual: ${palavra.texto}`);
    }
    this.canvas.hidden=false;this.legenda.hidden=false;
    c.clearRect(0,0,1200,140);c.fillStyle=cor;
    const montagem=Math.max(0,Math.min(1,(posicao-palavra.inicio_ms)/75,(palavra.fim_ms-posicao)/65));
    const suave=montagem*montagem*(3-2*montagem);
    for(let i=0;i<this.pontos.length;i+=2) {
      const x=this.pontos[i], y=this.pontos[i+1], a=aleatorio(i)*Math.PI*2;
      const arco=(1-suave)*26;
      c.globalAlpha=.5+.5*suave;
      c.beginPath();c.arc(x+Math.cos(a+posicao*.002)*arco,y+Math.sin(a)*arco*.5,palavra.destaque?1.35:1.15,0,Math.PI*2);c.fill();
    }
    c.globalAlpha=1;
  }
}
