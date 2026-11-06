import { describe, expect, it } from "vitest";
import { EnvelopeVisual, SILENCIO, aproximar, cadenciaVisual, energiaBanda, faixaAcustica, type Acustica } from "../src/scene-audio";
import { onda } from "../src/scene-math";
import { cores, desconectar, inicial, leituraDoPainel, lerAcustica, lerFala, nivelPerceptivo, reduzir, snapshot, type FalaTemporizada } from "../src/state";
import { RelogioFala } from "../src/word-particles";
const amostra=(alteracoes:Partial<Acustica>={}):Acustica=>({fonte:"voz",rms:.45,pico:.8,envelope:.65,bandas:[.7,.4,.3,.15,.1,.05],centroide:.2,fluxo:.25,ativo:true,reproducao_id:1,posicao_ms:50,duracao_ms:1000,...alteracoes});
const fala:FalaTemporizada={id:1,duracao_ms:1000,precisao:"estimada",palavras:[{texto:"Olá",inicio_ms:0,fim_ms:300,destaque:false},{texto:"Nora",inicio_ms:500,fim_ms:1000,destaque:true}]};
const evento=(tipo:string,dados:object,sequencia=3)=>({versao:1,sequencia,tipo,dados,instante:"2026-11-06T12:00:00"});
describe("contrato acústico e privacidade",()=>{
  it("valida amplitudes, seis bandas e cronologia de palavras",()=>{
    expect(lerAcustica(amostra())).toEqual(amostra());
    for(const parcial of [{rms:NaN},{rms:1.1},{bandas:[.2]},{posicao_ms:-1},{reproducao_id:1.5},{ativo:1}])expect(lerAcustica({...amostra(),...parcial})).toBeNull();
    expect(lerFala(fala)).toEqual(fala);
    for(const parcial of [{duracao_ms:NaN},{palavras:[{...fala.palavras[0],fim_ms:1001}]},{palavras:[fala.palavras[1],fala.palavras[0]]},{palavras:[{...fala.palavras[0],texto:"x".repeat(121)}]}])expect(lerFala({...fala,...parcial})).toBeNull();
  });
  it("nível legado acompanha RMS real nos eventos acústicos",()=>{
    const m=reduzir({...inicial,conectado:true},evento("acustica",amostra()));
    expect(m.nivel_audio).toBe(.45);expect(reduzir(m,evento("acustica",amostra({ativo:false}),4)).nivel_audio).toBe(0);
  });
  it("palavras pessoais ficam fora de snapshots e eventos privados",()=>{
    expect(snapshot({...inicial,conectado:true,fala_temporizada:fala}).fala_temporizada).toBeNull();
    expect(reduzir({...inicial,conectado:true},evento("fala_temporizada",fala)).fala_temporizada).toBeNull();
    let m=reduzir({...inicial,conectado:true,privacidade:false},evento("fala_temporizada",fala));
    expect(m.fala_temporizada).toEqual(fala);
    expect(desconectar(m).fala_temporizada).toBeNull();
    expect(reduzir(m,evento("privacidade",{privacidade:true},4)).fala_temporizada).toBeNull();
    m=reduzir(m,evento("acustica",amostra({ativo:false}),4));expect(m.fala_temporizada).toBeNull();
  });
  it("paleta canônica contém as cores emocionais e aliases reais",()=>{
    expect(cores.calma).toBe("#66D4CB");expect(cores.triste).toBe("#AA9ACF");expect(cores.curiosa).toBe("#DF876A");
    for(const [a,b] of [["neutra","neutro"],["alegre","empolgada"],["seria","confiante"],["carinhosa","carinho"]])expect(cores[a]).toBe(cores[b]);
  });
});
describe("áudio derivado controla geometria",()=>{
  it("intensidade, pausas e fim soltam os envelopes sem manter dados antigos",()=>{
    const baixo=new EnvelopeVisual(),alto=new EnvelopeVisual();baixo.alimentar(amostra({rms:.1,envelope:.1,pico:.1}),0);alto.alimentar(amostra(),0);
    baixo.passo(100,100);alto.passo(100,100);expect(alto.voz.rms).toBeGreaterThan(baixo.voz.rms);
    const antes=alto.voz.envelope;alto.passo(100,401);expect(alto.voz.envelope).toBeLessThan(antes);
    for(let i=0;i<22;i++)alto.passo(100,501+i*100);
    expect(alto.voz.envelope).toBe(0);expect(alto.voz.bandas).toEqual([0,0,0,0,0,0]);
  });
  it("microfone não reaproveita a cauda da Nora",()=>{
    const e=new EnvelopeVisual();e.alimentar(amostra(),0);e.passo(100,100);const antes=e.voz.envelope;
    e.alimentar(amostra({ativo:false}),110);e.alimentar(amostra({fonte:"microfone",rms:0,envelope:0,pico:0,reproducao_id:0,posicao_ms:0,duracao_ms:0}),120);e.passo(50,170);
    expect(e.microfone.rms).toBe(0);expect(e.voz.envelope).toBeGreaterThan(0);expect(e.voz.envelope).toBeLessThan(antes);
  });
  it("suavização independe de FPS para áudio e cores",()=>{
    const a=new EnvelopeVisual(),b=new EnvelopeVisual();a.alimentar(amostra(),0);b.alimentar(amostra(),0);
    for(let i=1;i<=6;i++)a.passo(1000/30,i*1000/30);
    for(let i=1;i<=12;i++)b.passo(1000/60,i*1000/60);
    expect(a.voz.envelope).toBeCloseTo(b.voz.envelope,10);
    let c=0,d=0;for(let i=0;i<30;i++)c=aproximar(c,1,1000/30,550);for(let i=0;i<60;i++)d=aproximar(d,1,1000/60,550);expect(c).toBeCloseTo(d,10);
  });
  it("faixa só reage à voz e bandas não criam saltos de energia ou fase",()=>{
    const baixo={...SILENCIO,fonte:"voz" as const,rms:.5,envelope:.6,pico:.7,bandas:[1,.1,0,0,0,0]},alto={...baixo,bandas:[0,0,0,0,.1,1]};
    expect(faixaAcustica(-6,0,1,baixo)).not.toBe(faixaAcustica(-6,0,1,alto));
    expect(faixaAcustica(2,0,1,SILENCIO)).toBe(0);
    for(const x of [-6,-2,2,6])expect(Math.abs(faixaAcustica(x-1e-5,0,1,baixo)-faixaAcustica(x+1e-5,0,1,baixo))).toBeLessThan(.001);
    expect(energiaBanda(baixo.bandas,.2-1e-6)).toBeCloseTo(energiaBanda(baixo.bandas,.2+1e-6),4);
  });
  it("perfis mic/voz diferentes preservam centro vazio e repouso",()=>{
    const voz={...SILENCIO,...amostra()},mic={...voz,fonte:"microfone" as const};
    expect(onda(1,.5,1,"falando",0,voz)).not.toEqual(onda(1,.5,1,"ouvindo",0,mic));
    for(let i=0;i<100;i++){const [x,y]=onda(i/100*Math.PI*2,.5,1,"falando",0,voz);expect(Math.hypot(x,y)).toBeGreaterThan(2);}
    expect(onda(1,.5,1,"ociosa",0,voz)).toEqual(onda(1,.5,1,"ociosa",0,mic));
  });
  it("reutiliza buffer da geometria e respeita orçamento de quadros",()=>{
    const buffer:[number,number,number]=[0,0,0];for(let i=0;i<1000;i++)expect(onda(i,.5,1,"ouvindo",0,SILENCIO,buffer)).toBe(buffer);
    expect(cadenciaVisual(30,false,false,false)).toBe(30);expect(cadenciaVisual(60,false,false,false)).toBe(60);expect(cadenciaVisual(60,true,false,false)).toBe(8);expect(cadenciaVisual(60,false,true,false)).toBe(0);expect(cadenciaVisual(60,false,false,true)).toBe(0);
  });
});
describe("palavras seguem a posição de reprodução",()=>{
  it("não avança por estado, não pisca quando RAF precede chegada do pacote",()=>{
    const r=new RelogioFala();r.atualizar(amostra({posicao_ms:100}),110);
    expect(r.palavra(fala,100)?.palavra.texto).toBe("Olá");expect(r.palavra(fala,110)?.posicao).toBe(100);
    expect(r.palavra(fala,350)).toBeNull(); // lacuna temporal real, não próximo estado
    expect(r.palavra(fala,411)).toBeNull(); // amostra expirada
  });
  it("silêncio limpa palavra, preserva timeline e retoma na posição real",()=>{
    const r=new RelogioFala();r.atualizar(amostra({rms:0,envelope:0,posicao_ms:250}),0);expect(r.palavra(fala,50)).toBeNull();
    r.atualizar(amostra({posicao_ms:600}),100);expect(r.palavra(fala,110)?.palavra.texto).toBe("Nora");
    r.atualizar(amostra({ativo:false,posicao_ms:1000}),120);expect(r.palavra(fala,130)).toBeNull();
    r.atualizar(amostra({posicao_ms:600}),140);expect(r.palavra(fala,150)).toBeNull();
  });
  it("ignora reprodução antiga e usa timeline tardia sem recomeçar",()=>{
    const r=new RelogioFala();r.atualizar(amostra({reproducao_id:2,posicao_ms:650}),100);
    expect(r.palavra(fala,120)).toBeNull();expect(r.palavra({...fala,id:2},120)?.palavra.texto).toBe("Nora");
    r.atualizar(amostra({reproducao_id:1,posicao_ms:50}),130);expect(r.palavra({...fala,id:2},140)?.palavra.texto).toBe("Nora");
    r.limpar();expect(r.palavra({...fala,id:2},150)).toBeNull();
  });
});

describe("painel lateral acompanha a onda central (regressão)",()=>{
  // Antes: o painel mostrava Math.round(rms*100)%, e uma fala baixa (RMS 0,004) virava "0%"
  // enquanto a onda central, movida pelo envelope e pelo pico do mesmo evento, já se mexia.
  const conectado={...inicial,conectado:true,estado:"ouvindo" as const};
  const baixa=amostra({fonte:"microfone",rms:.004,envelope:.003,pico:.03,reproducao_id:0,posicao_ms:0,duracao_ms:0});
  it("fala baixa: a onda se deforma e o painel não mostra zero",()=>{
    const m=reduzir(conectado,evento("acustica",baixa));
    const env=new EnvelopeVisual();env.alimentar(m.acustica,0);for(let i=1;i<=6;i++)env.passo(50,i*50);
    const comSinal=onda(1,.5,0,"ouvindo",0,env.microfone),semSinal=onda(1,.5,0,"ouvindo",0,SILENCIO);
    expect(Math.hypot(comSinal[0]-semSinal[0],comSinal[1]-semSinal[1])).toBeGreaterThan(0);
    const painel=leituraDoPainel(m);
    expect(painel.nivel).toBeGreaterThan(0);
    expect(painel.rotulo).not.toBe("0%");expect(painel.rotulo).not.toBe("Em silêncio");
  });
  it("usa o envelope na soltura, como a onda, e zera quando o sinal acaba",()=>{
    const soltando=reduzir(conectado,evento("acustica",{...baixa,rms:0,envelope:.02}));
    expect(leituraDoPainel(soltando).nivel).toBeGreaterThan(0);
    const fim=reduzir(soltando,evento("acustica",{...baixa,ativo:false},4));
    expect(leituraDoPainel(fim)).toEqual({nivel:0,rotulo:"Em silêncio"});
    expect(leituraDoPainel({...fim,conectado:false}).rotulo).toBe("Sem dados");
  });
  it("pensando ou em repouso, a última medida do microfone não aparece (a onda também a ignora)",()=>{
    const ouvindo=reduzir(conectado,evento("acustica",{...baixa,rms:.2,envelope:.2}));
    expect(leituraDoPainel(ouvindo).nivel).toBeGreaterThan(0);
    for(const estado of ["pensando","transcrevendo","ociosa","modo_jogo"]){
      const m=reduzir(ouvindo,evento(estado,{},4));
      expect(leituraDoPainel(m)).toEqual({nivel:0,rotulo:"Em silêncio"});
    }
    const falando=reduzir(reduzir(ouvindo,evento("falando",{},4)),evento("acustica",amostra(),5));
    expect(leituraDoPainel(falando).nivel).toBeGreaterThan(0);
    expect(leituraDoPainel({...falando,estado:"ouvindo"}).nivel).toBe(0); // voz não vale ouvindo
  });
  it("escala em decibéis: −60 dBFS é zero, 0 dBFS é cheio, fala comum fica no meio",()=>{
    expect(nivelPerceptivo(0)).toBe(0);expect(nivelPerceptivo(.001)).toBeCloseTo(0);expect(nivelPerceptivo(1)).toBe(1);
    expect(nivelPerceptivo(.01)).toBeCloseTo(1/3);expect(nivelPerceptivo(.1)).toBeCloseTo(2/3);
    expect(nivelPerceptivo(NaN)).toBe(0);
  });
});
