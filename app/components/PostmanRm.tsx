"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import {
  PORTA_PADRAO,
  StatusConector,
  atalhoWindows,
  comandoConector,
  lerConexaoSalva,
  mensagemConectorInacessivel,
  salvarConexao,
  urlConector,
  versaoAtende,
} from "../lib/conector";
import { baixarBlob } from "../lib/download";
import {
  Registro,
  chaveDoRegistro,
  chaveNaUrl,
  descricaoDoRegistro,
  extrairRegistros,
  lerRegistros,
  limparParaEnvio,
  mensagemDoRm,
  textoEnvelope,
  trocarColigada,
} from "../lib/registros";

/**
 * "Postman facilitado" para o REST DataServer do RM, pelo conector local.
 *
 * - O corpo aceita o JSON no formato do GET ({"messages","length","data"}),
 *   uma lista ou um registro; dá para anexar arquivos .json de outros lugares.
 * - POST/PUT enviam um registro por chamada, já limpos (sem id, sem null, sem
 *   credenciais/campos do RM) e, em POST, pulam ou alteram o que já existe.
 * - Com o conector aberto para várias bases, consulta numa e envia para outra.
 *
 * Usuário e senha ficam só na memória do componente.
 */

type Metodo = "GET" | "POST" | "PUT" | "DELETE";
type SeExistir = "erro" | "pular" | "alterar";

type RespostaRm = {
  ok: boolean;
  status?: number;
  tempo_ms?: number;
  corpo?: unknown;
  truncado?: boolean;
  dica?: string | null;
  erro?: string;
  como_corrigir?: string;
};

type ItemLote = {
  indice: number; // posição no corpo (1 = primeiro registro)
  chave: string | null;
  ok: boolean;
  status: number | null;
  acao?: "incluido" | "alterado" | "pulado" | null;
  resposta?: unknown;
  dica?: string | null;
  erro?: string;
  como_corrigir?: string;
};

type ResultadoLote = { total: number; sucesso: number; falhas: number; pulados: number; itens: ItemLote[] };

const PREFIXO_DS = "/rmsrestdataserver/rest/";
const MAX_POR_CHAMADA = 500; // limite do conector por lote
const MAX_GET_COMPLETO = 300;

const ACAO: Record<string, string> = { incluido: "incluído", alterado: "alterado", pulado: "pulado (já existe)" };

function parsearParametros(texto: string): Record<string, string> {
  const saida: Record<string, string> = {};
  for (const linha of texto.split("\n")) {
    const i = linha.indexOf("=");
    if (i > 0) saida[linha.slice(0, i).trim()] = linha.slice(i + 1).trim();
  }
  return saida;
}

function textoResposta(corpo: unknown) {
  return typeof corpo === "string" ? corpo : JSON.stringify(corpo, null, 2);
}

export type PostmanRmProps = {
  /** Nome do DataServer (ex.: GlbUsuarioData). Vazio = o analista informa. */
  dataserverPadrao: string;
  /** Campo(s) chave, separados por vírgula (ex.: "CODUSUARIO" ou "CODCOLIGADA,CODEVENTO"). */
  campoChavePadrao: string;
  /** Campos que nunca vão no envio (credenciais, campos controlados pelo RM). */
  camposNaoEnviar?: string[];
  /** Registros para já vir no corpo (ex.: o lote validado). */
  registrosIniciais?: Registro[];
  metodoInicial?: Metodo;
  /** Mostra "Trocar coligada" (útil para copiar entre bases/coligadas). */
  permitirTrocarColigada?: boolean;
  /** Lembra DataServer e campo chave neste navegador (chave do localStorage). */
  lembrarComo?: string;
  /** Trava o DataServer (o caminho ainda pode ser editado à mão). */
  dataserverFixo?: boolean;
  nomeArquivo?: string;
};

export function PostmanRm({
  dataserverPadrao,
  campoChavePadrao,
  camposNaoEnviar = [],
  registrosIniciais,
  metodoInicial = "GET",
  permitirTrocarColigada = false,
  lembrarComo,
  dataserverFixo = false,
  nomeArquivo = "registros",
}: PostmanRmProps) {
  // Conexão
  const [porta, setPorta] = useState(PORTA_PADRAO);
  const [token, setToken] = useState("");
  const [status, setStatus] = useState<StatusConector | null>(null);
  const [conectando, setConectando] = useState(false);
  const [comoAbrir, setComoAbrir] = useState(false);
  const [basesTexto, setBasesTexto] = useState("");
  const [autoassinado, setAutoassinado] = useState(false);
  const [origem, setOrigem] = useState("");
  const [usuario, setUsuario] = useState("");
  const [senha, setSenha] = useState("");
  const [baseConsulta, setBaseConsulta] = useState("");
  const [baseEnvio, setBaseEnvio] = useState("");

  // Requisição
  const [metodo, setMetodo] = useState<Metodo>(metodoInicial);
  const [dataserver, setDataserver] = useState(dataserverPadrao);
  const [campoChave, setCampoChave] = useState(campoChavePadrao);
  const [chave, setChave] = useState("");
  const [parametros, setParametros] = useState("");
  const [caminhoManual, setCaminhoManual] = useState<string | null>(null);
  const [corpo, setCorpo] = useState("");
  const [aba, setAba] = useState<"corpo" | "parametros" | "opcoes">(metodoInicial === "GET" ? "parametros" : "corpo");
  const [selecionados, setSelecionados] = useState<Set<number>>(new Set());

  // Opções de envio
  const [seExistir, setSeExistir] = useState<SeExistir>("pular");
  const [removerNulos, setRemoverNulos] = useState(true);
  const [manterId, setManterId] = useState(false);
  const [pararNoErro, setPararNoErro] = useState(false);
  const [soPrimeiro, setSoPrimeiro] = useState(true);
  const [trazerCompleto, setTrazerCompleto] = useState(false);
  const [coligadaNova, setColigadaNova] = useState("");
  const [tambemContas, setTambemContas] = useState(true);

  // Resultado
  const [enviando, setEnviando] = useState<string | null>(null);
  const [resposta, setResposta] = useState<RespostaRm | null>(null);
  const [lote, setLote] = useState<ResultadoLote | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const [copiado, setCopiado] = useState<string | null>(null);
  const arquivoRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    setOrigem(window.location.origin);
    const salva = lerConexaoSalva();
    if (salva) {
      setPorta(salva.porta);
      setToken(salva.token);
    }
    if (lembrarComo) {
      try {
        const v = JSON.parse(localStorage.getItem(`postman_rm:${lembrarComo}`) || "null");
        if (v?.dataserver && !dataserverFixo) setDataserver(v.dataserver);
        if (v?.campoChave) setCampoChave(v.campoChave);
      } catch {
        /* preferência corrompida: ignora */
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!lembrarComo) return;
    localStorage.setItem(`postman_rm:${lembrarComo}`, JSON.stringify({ dataserver, campoChave }));
  }, [lembrarComo, dataserver, campoChave]);

  // Lote novo vindo da tela (ex.: planilha revalidada): recomeça.
  useEffect(() => {
    if (!registrosIniciais) return;
    setCorpo(registrosIniciais.length ? textoEnvelope(registrosIniciais) : "");
    setSelecionados(new Set(registrosIniciais.map((_, i) => i)));
    setMetodo(metodoInicial);
    setAba("corpo");
    setLote(null);
    setResposta(null);
    setSoPrimeiro(true);
  }, [registrosIniciais, metodoInicial]);

  useEffect(() => {
    if (dataserverFixo) setDataserver(dataserverPadrao);
  }, [dataserverFixo, dataserverPadrao]);

  const leitura = useMemo(() => {
    try {
      return { registros: lerRegistros(corpo), erro: null as string | null };
    } catch (e) {
      return { registros: [] as Registro[], erro: e instanceof Error ? e.message : "JSON inválido." };
    }
  }, [corpo]);
  const registros = leitura.registros;

  // Mudou a quantidade de registros: seleciona todos de novo.
  useEffect(() => {
    setSelecionados(new Set(registros.map((_, i) => i)));
  }, [registros.length]); // eslint-disable-line react-hooks/exhaustive-deps

  const variasBases = (status?.bases?.length ?? 0) > 1;
  const conectorAntigo = status !== null && !versaoAtende(status.versao);
  const raiz = PREFIXO_DS + dataserver.trim();
  const caminhoAuto =
    chave.trim() && (metodo === "GET" || metodo === "DELETE") ? `${raiz}/${chaveNaUrl(chave.trim())}` : raiz;
  const caminho = caminhoManual ?? caminhoAuto;
  const base = metodo === "GET" ? baseConsulta : baseEnvio;
  const alvos = registros.map((r, i) => ({ r, i })).filter(({ i }) => selecionados.has(i));
  const enviar = soPrimeiro ? alvos.slice(0, 1) : alvos;
  const opcoesLimpeza = { removerNulos, manterId, camposNaoEnviar };

  async function chamarConector(rota: "/rm" | "/rm/lote", pedido: Record<string, unknown>) {
    const r = await fetch(`${urlConector(porta)}${rota}`, {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-Conector-Token": token.trim() },
      body: JSON.stringify({ ...pedido, usuario, senha, base: base || undefined }),
    });
    const dados = await r.json().catch(() => null);
    if (!dados) throw new Error("Resposta inválida do conector.");
    if (rota === "/rm/lote" && (!r.ok || dados.resultados === undefined)) {
      throw new Error(`${dados.erro ?? "O conector recusou o envio."} ${dados.como_corrigir ?? ""}`.trim());
    }
    return dados;
  }

  function tratarFalha(e: unknown) {
    const msg = e instanceof Error ? e.message : "";
    if (!msg || msg === "Failed to fetch" || msg.includes("NetworkError")) {
      setErro(mensagemConectorInacessivel(porta));
      setStatus(null);
    } else {
      setErro(msg);
    }
  }

  async function conectar() {
    setConectando(true);
    setErro(null);
    setStatus(null);
    try {
      const r = await fetch(`${urlConector(porta)}/status`, { headers: { "X-Conector-Token": token.trim() } });
      const dados = await r.json().catch(() => ({}));
      if (!r.ok) throw new Error(`${dados.erro ?? "Conector recusou."} ${dados.como_corrigir ?? ""}`.trim());
      const bases = Array.isArray(dados.bases) && dados.bases.length ? dados.bases : [{ nome: "", rm: dados.rm }];
      setStatus({ versao: dados.versao, rm: dados.rm, bases });
      setBaseConsulta(bases[0].nome);
      setBaseEnvio(bases[bases.length > 1 ? 1 : 0].nome);
      salvarConexao({ porta, token: token.trim() });
    } catch (e) {
      tratarFalha(e);
    } finally {
      setConectando(false);
    }
  }

  async function executar() {
    setErro(null);
    setResposta(null);
    setLote(null);
    if (metodo === "GET") return consultar();
    if (metodo === "DELETE") return excluir();
    return enviarLote();
  }

  async function consultar() {
    setEnviando("Consultando...");
    try {
      const dados: RespostaRm = await chamarConector("/rm", {
        metodo: "GET", caminho, parametros: parsearParametros(parametros),
      });
      if (dados.ok && trazerCompleto && !chave.trim()) {
        const lista = extrairRegistros(dados.corpo);
        if (lista.length > MAX_GET_COMPLETO) {
          setErro(`A consulta trouxe ${lista.length} registros; o "completo" busca no máximo ${MAX_GET_COMPLETO}. Filtre mais.`);
        } else {
          const completos: Registro[] = [];
          for (let n = 0; n < lista.length; n++) {
            setEnviando(`Trazendo completo ${n + 1}/${lista.length}...`);
            const k = chaveDoRegistro(lista[n], campoChave);
            if (!k) {
              completos.push(lista[n]);
              continue;
            }
            const um: RespostaRm = await chamarConector("/rm", { metodo: "GET", caminho: `${raiz}/${chaveNaUrl(k)}` });
            completos.push(...(um.ok ? extrairRegistros(um.corpo) : [lista[n]]));
          }
          dados.corpo = { messages: [], length: completos.length, data: completos };
        }
      }
      setResposta(dados);
    } catch (e) {
      tratarFalha(e);
    } finally {
      setEnviando(null);
    }
  }

  async function excluir() {
    if (!chave.trim() && caminhoManual === null) {
      setErro("Informe a chave do registro a excluir.");
      return;
    }
    if (!window.confirm(`Excluir no RM${base ? ` (base ${base})` : ""}?\n\n${caminho}\n\nNão dá para desfazer pelo Acelerador.`)) return;
    setEnviando("Excluindo...");
    try {
      setResposta(await chamarConector("/rm", { metodo: "DELETE", caminho }));
    } catch (e) {
      tratarFalha(e);
    } finally {
      setEnviando(null);
    }
  }

  async function enviarLote() {
    if (leitura.erro) return setErro(leitura.erro);
    if (enviar.length === 0) return setErro("Nenhum registro selecionado no corpo.");
    if (!dataserver.trim() && caminhoManual === null) return setErro("Informe o DataServer.");
    const precisaChave = metodo === "PUT" || (seExistir !== "erro" && !conectorAntigo);
    if (precisaChave && !campoChave.trim()) return setErro("Informe o campo chave (aba Opções).");
    const acao = metodo === "POST" ? "Incluir" : "Alterar";
    const extra =
      metodo === "POST" && !conectorAntigo && seExistir !== "erro"
        ? `\nO que já existir no RM será ${seExistir === "pular" ? "pulado" : "alterado (PUT)"}.`
        : "";
    if (!window.confirm(`${acao} ${enviar.length} registro(s) no RM${base ? ` -- base ${base}` : ""}?\n\n${metodo} ${caminho}${extra}\n\nConfira se é o ambiente certo (de preferência homologação).`)) return;

    const itens: ItemLote[] = [];
    try {
      for (let ini = 0; ini < enviar.length; ini += MAX_POR_CHAMADA) {
        const parte = enviar.slice(ini, ini + MAX_POR_CHAMADA);
        setEnviando(`Enviando ${ini + 1}-${ini + parte.length} de ${enviar.length}...`);
        const dados = await chamarConector("/rm/lote", {
          metodo,
          caminho,
          registros: parte.map(({ r }) => limparParaEnvio(r, opcoesLimpeza)),
          campo_chave: campoChave.trim() || null,
          parar_no_erro: pararNoErro,
          se_existir: metodo === "POST" && !conectorAntigo ? seExistir : undefined,
        });
        for (const it of dados.resultados as ItemLote[]) itens.push({ ...it, indice: parte[it.indice - 1].i + 1 });
        if (pararNoErro && dados.falhas > 0) break;
      }
    } catch (e) {
      tratarFalha(e);
    } finally {
      setEnviando(null);
    }
    if (!itens.length) return;
    setLote({
      total: enviar.length,
      sucesso: itens.filter((x) => x.ok).length,
      falhas: itens.filter((x) => !x.ok).length,
      pulados: itens.filter((x) => x.acao === "pulado").length,
      itens,
    });
    // O que deu certo sai da seleção: o próximo clique manda só o resto.
    const certos = new Set(itens.filter((x) => x.ok).map((x) => x.indice - 1));
    setSelecionados((s) => new Set([...s].filter((i) => !certos.has(i))));
    if (soPrimeiro && certos.size > 0) setSoPrimeiro(false);
  }

  async function anexarArquivos(lista: FileList | null) {
    if (!lista?.length) return;
    if (leitura.erro && corpo.trim()) return setErro("Corrija o JSON do corpo antes de anexar.");
    setErro(null);
    const novos: Registro[] = [];
    for (const f of Array.from(lista)) {
      try {
        novos.push(...extrairRegistros(JSON.parse(await f.text())));
      } catch {
        setErro(`"${f.name}" não é um JSON válido: não foi anexado.`);
      }
    }
    if (novos.length) {
      setCorpo(textoEnvelope([...registros, ...novos]));
      setMetodo((m) => (m === "GET" || m === "DELETE" ? "POST" : m));
      setAba("corpo");
    }
    if (arquivoRef.current) arquivoRef.current.value = "";
  }

  function usarResposta(anexar: boolean) {
    if (!resposta?.corpo) return;
    const novos = extrairRegistros(resposta.corpo);
    if (!novos.length) return setErro("A resposta não tem registros (data vazio).");
    setCorpo(textoEnvelope(anexar ? [...registros, ...novos] : novos));
    setMetodo("POST");
    setChave("");
    setCaminhoManual(null);
    setAba("corpo");
    setResposta(null);
  }

  function aplicarColigada() {
    const n = Number(coligadaNova);
    if (!Number.isInteger(n) || n <= 0) return setErro("Informe a coligada de destino (número).");
    setCorpo(textoEnvelope(registros.map((r) => trocarColigada(r, n, tambemContas))));
  }

  async function copiar(texto: string, id: string) {
    try {
      await navigator.clipboard.writeText(texto);
      setCopiado(id);
      setTimeout(() => setCopiado(null), 1500);
    } catch {
      setErro("O navegador bloqueou a cópia: selecione o texto e copie manualmente.");
    }
  }

  function baixarJson(texto: string, nome: string) {
    baixarBlob(new Blob([texto], { type: "application/json;charset=utf-8" }), nome);
  }

  const campo = "w-full rounded-md border border-line bg-paper px-3 py-2 text-sm text-ink focus:border-brand focus:outline-none";
  const rotulo = "text-xs font-medium text-muted";
  const botaoSec = "rounded-md border border-line px-3 py-1.5 text-xs text-ink transition hover:border-brand disabled:opacity-50";
  const podeExecutar = !!status && !!usuario.trim() && !!senha && !enviando && (!!dataserver.trim() || caminhoManual !== null);
  const previa = enviar[0] ? JSON.stringify(limparParaEnvio(enviar[0].r, opcoesLimpeza), null, 2) : "";

  return (
    <div className="rounded-lg border border-brand/40 bg-surface p-4">
      {/* --- Conexão ---------------------------------------------------- */}
      <div className="flex flex-wrap items-end gap-3">
        <label className="flex flex-col gap-1">
          <span className={rotulo}>Porta</span>
          <input value={porta} onChange={(e) => setPorta(e.target.value.replace(/\D/g, ""))} className={`${campo} w-20`} />
        </label>
        <label className="flex flex-col gap-1">
          <span className={rotulo}>Código de pareamento</span>
          <input
            value={token}
            onChange={(e) => setToken(e.target.value.toUpperCase())}
            placeholder="da janela do conector"
            className={`${campo} w-44 font-mono`}
          />
        </label>
        <button
          onClick={conectar}
          disabled={!token.trim() || !porta || conectando}
          className="rounded-md bg-action px-4 py-2 text-sm font-medium text-white transition hover:bg-action-hover disabled:opacity-50"
        >
          {conectando ? "Conectando..." : status ? "Reconectar" : "Conectar"}
        </button>
        <label className="flex flex-col gap-1">
          <span className={rotulo}>Usuário do RM</span>
          <input value={usuario} onChange={(e) => setUsuario(e.target.value)} autoComplete="off" className={`${campo} w-36`} />
        </label>
        <label className="flex flex-col gap-1">
          <span className={rotulo}>Senha</span>
          <input
            type="password"
            value={senha}
            onChange={(e) => setSenha(e.target.value)}
            autoComplete="new-password"
            className={`${campo} w-36`}
          />
        </label>
        <button onClick={() => setComoAbrir((v) => !v)} className={`${botaoSec} ml-auto`}>
          {comoAbrir ? "Fechar ajuda" : "Como abrir o conector"}
        </button>
      </div>
      {status && (
        <p className="mt-2 text-xs text-emerald-700 dark:text-emerald-300">
          ✓ Conectado (conector {status.versao}) · base{status.bases.length > 1 ? "s" : ""}:{" "}
          {status.bases.map((b) => `${b.nome ? `${b.nome} = ` : ""}${b.rm}`).join(" · ")}
        </p>
      )}
      {conectorAntigo && (
        <p className="mt-2 rounded-md border border-amber-300 bg-amber-50 px-3 py-2 text-xs text-amber-900 dark:border-amber-500/30 dark:bg-amber-500/10 dark:text-amber-200">
          Este conector é antigo ({status?.versao}): sem várias bases e sem &quot;se já existir&quot;. Baixe o novo em
          &quot;Como abrir o conector&quot; e abra de novo.
        </p>
      )}
      {!status && (
        <p className="mt-2 text-xs text-muted">
          Usuário e senha ficam só na memória desta aba e vão da sua máquina direto para o RM.
        </p>
      )}

      {comoAbrir && (
        <div className="mt-3 rounded-md border border-line bg-paper p-3 text-xs text-muted">
          <p>
            O site não enxerga o RM do cliente: quem chama é o <strong>conector</strong>, um programa pequeno que roda na
            sua máquina (Python 3.9+, nada para instalar).
          </p>
          <ol className="mt-2 list-decimal space-y-1 pl-5 text-ink">
            <li>Informe as bases do RM abaixo (uma por linha, <code>nome=endereço</code>, ou só o endereço).</li>
            <li>
              Baixe os <strong>dois arquivos</strong> e salve na <strong>mesma pasta</strong>: o{" "}
              <code>conector_rm.py</code> e o atalho <code>abrir_conector.bat</code>.
            </li>
            <li>
              Dê <strong>dois cliques no abrir_conector.bat</strong>. A janela fica aberta e mostra o{" "}
              <strong>código de pareamento</strong> em destaque, que já vai copiado: é só colar (Ctrl+V) no campo acima.
            </li>
            <li>O código fica guardado: nas próximas vezes é o mesmo. Deixe a janela aberta enquanto usa a tela.</li>
          </ol>
          <label className="mt-3 flex flex-col gap-1">
            <span className={rotulo}>Bases do RM (uma por linha)</span>
            <textarea
              value={basesTexto}
              onChange={(e) => setBasesTexto(e.target.value)}
              rows={2}
              placeholder={"homolog=https://rm-homolog.cliente.com.br:8051\nproducao=https://rm.cliente.com.br:8051"}
              className={`${campo} font-mono text-xs`}
            />
          </label>
          <label className="mt-2 flex items-center gap-2 text-ink">
            <input type="checkbox" checked={autoassinado} onChange={(e) => setAutoassinado(e.target.checked)} />
            O RM usa certificado HTTPS próprio (autoassinado)
          </label>
          <div className="mt-2 flex flex-wrap gap-2">
            <a
              href="/conector/conector_rm.py"
              download
              className="rounded-md bg-action px-3 py-1.5 font-medium text-white transition hover:bg-action-hover"
            >
              1. Baixar conector_rm.py
            </a>
            <button
              onClick={() =>
                baixarBlob(
                  new Blob([atalhoWindows(basesTexto, origem, porta, autoassinado)], { type: "application/x-bat" }),
                  "abrir_conector.bat"
                )
              }
              disabled={!basesTexto.trim()}
              title={basesTexto.trim() ? "" : "Informe as bases do RM acima"}
              className="rounded-md bg-action px-3 py-1.5 font-medium text-white transition hover:bg-action-hover disabled:opacity-50"
            >
              2. Baixar atalho abrir_conector.bat (Windows)
            </button>
          </div>
          <details className="mt-3">
            <summary className="cursor-pointer">Prefere o terminal (ou não usa Windows)?</summary>
            <p className="mt-1">
              Rode este comando no terminal, na pasta do arquivo. Também dá para dar dois cliques no{" "}
              <code>conector_rm.py</code>: na primeira vez ele pergunta o endereço do RM e do site e guarda.
            </p>
            <pre className="mt-2 overflow-x-auto rounded-md border border-line bg-surface px-3 py-2 font-mono text-ink">
              {comandoConector(basesTexto, origem, porta, autoassinado)}
            </pre>
            <button
              onClick={() => copiar(comandoConector(basesTexto, origem, porta, autoassinado), "cmd")}
              className={`${botaoSec} mt-2`}
            >
              {copiado === "cmd" ? "Copiado!" : "Copiar comando"}
            </button>
          </details>
        </div>
      )}

      {/* --- Barra da requisição (estilo Postman) ------------------------- */}
      <div className="mt-4 flex flex-wrap items-end gap-2">
        <select
          value={metodo}
          onChange={(e) => {
            const m = e.target.value as Metodo;
            setMetodo(m);
            setAba(m === "GET" ? "parametros" : m === "DELETE" ? "opcoes" : "corpo");
          }}
          className={`${campo} w-auto font-mono font-bold`}
          aria-label="Método"
        >
          <option value="GET">GET</option>
          <option value="POST">POST</option>
          <option value="PUT">PUT</option>
          <option value="DELETE">DELETE</option>
        </select>
        {variasBases && (
          <select
            value={base}
            onChange={(e) => (metodo === "GET" ? setBaseConsulta : setBaseEnvio)(e.target.value)}
            className={`${campo} w-auto`}
            aria-label={metodo === "GET" ? "Base de consulta" : "Base de envio"}
            title={metodo === "GET" ? "Base onde consultar" : "Base para onde enviar"}
          >
            {status?.bases.map((b) => (
              <option key={b.nome} value={b.nome}>
                {metodo === "GET" ? "de: " : "para: "}
                {b.nome}
              </option>
            ))}
          </select>
        )}
        <input
          value={caminho}
          onChange={(e) => setCaminhoManual(e.target.value)}
          className={`${campo} min-w-[16rem] flex-1 font-mono text-xs`}
          aria-label="Caminho no RM"
        />
        <button
          onClick={executar}
          disabled={!podeExecutar}
          className={`rounded-md px-5 py-2 text-sm font-medium text-white transition disabled:opacity-50 ${
            metodo === "DELETE" ? "bg-red-600 hover:bg-red-700" : "bg-action hover:bg-action-hover"
          }`}
        >
          {enviando ??
            (metodo === "GET"
              ? "Consultar"
              : metodo === "DELETE"
                ? "Excluir"
                : `${metodo === "POST" ? "Incluir" : "Alterar"} ${enviar.length} registro(s)`)}
        </button>
      </div>
      {caminhoManual !== null && (
        <button onClick={() => setCaminhoManual(null)} className="mt-1 text-xs text-muted underline">
          voltar ao caminho automático
        </button>
      )}
      {!status && <p className="mt-1 text-xs text-muted">Conecte para enviar.</p>}
      {status && (!usuario.trim() || !senha) && <p className="mt-1 text-xs text-muted">Informe usuário e senha do RM.</p>}

      <div className="mt-3 grid gap-3 sm:grid-cols-3">
        <label className="flex flex-col gap-1">
          <span className={rotulo}>DataServer</span>
          <input
            value={dataserver}
            onChange={(e) => {
              setDataserver(e.target.value.trim());
              setCaminhoManual(null);
            }}
            disabled={dataserverFixo}
            placeholder="nome em /rmsrestdataserver/rest/<NOME>"
            className={`${campo} font-mono text-xs disabled:opacity-60`}
          />
        </label>
        <label className="flex flex-col gap-1">
          <span className={rotulo}>Campo(s) chave</span>
          <input
            value={campoChave}
            onChange={(e) => setCampoChave(e.target.value)}
            placeholder="ex.: CODCOLIGADA,CODEVENTO"
            className={`${campo} font-mono text-xs`}
          />
        </label>
        {(metodo === "GET" || metodo === "DELETE") && (
          <label className="flex flex-col gap-1">
            <span className={rotulo}>Chave {metodo === "GET" ? "(opcional: um registro)" : "(obrigatória)"}</span>
            <input
              value={chave}
              onChange={(e) => {
                setChave(e.target.value);
                setCaminhoManual(null);
              }}
              placeholder="ex.: maria.silva ou 1$_$1"
              className={`${campo} font-mono text-xs`}
            />
          </label>
        )}
      </div>

      {/* --- Abas ---------------------------------------------------------- */}
      <div className="mt-4 flex gap-1 border-b border-line text-xs">
        {(
          [
            ["corpo", `Corpo${registros.length ? ` (${registros.length})` : ""}`],
            ["parametros", "Parâmetros (GET)"],
            ["opcoes", "Opções de envio"],
          ] as const
        ).map(([id, texto]) => (
          <button
            key={id}
            onClick={() => setAba(id)}
            className={`-mb-px rounded-t-md border px-3 py-1.5 ${
              aba === id ? "border-line border-b-surface bg-surface font-bold text-ink" : "border-transparent text-muted hover:text-ink"
            }`}
          >
            {texto}
          </button>
        ))}
      </div>

      {aba === "corpo" && (
        <div className="mt-3">
          <div className="flex flex-wrap gap-2">
            <label className={`${botaoSec} cursor-pointer`}>
              Anexar arquivos .json
              <input
                ref={arquivoRef}
                type="file"
                accept=".json,application/json"
                multiple
                className="hidden"
                onChange={(e) => anexarArquivos(e.target.files)}
              />
            </label>
            <button onClick={() => !leitura.erro && setCorpo(textoEnvelope(registros))} disabled={!!leitura.erro || !corpo} className={botaoSec}>
              Formatar (padrão do GET)
            </button>
            <button onClick={() => baixarJson(corpo, `${nomeArquivo}.json`)} disabled={!corpo} className={botaoSec}>
              Baixar corpo
            </button>
            <button onClick={() => setCorpo("")} disabled={!corpo} className={botaoSec}>
              Limpar
            </button>
          </div>
          <textarea
            value={corpo}
            onChange={(e) => setCorpo(e.target.value)}
            rows={12}
            spellCheck={false}
            placeholder={'Cole o JSON no formato do GET: {"messages": [], "length": 1, "data": [ {...} ]}\nou anexe arquivos .json, ou faça um GET e clique "Usar como corpo".'}
            className={`${campo} mt-2 font-mono text-xs`}
          />
          {leitura.erro && <p className="mt-1 text-xs text-red-600 dark:text-red-300">{leitura.erro}</p>}

          {registros.length > 0 && (
            <div className="mt-3">
              <div className="flex flex-wrap items-center gap-3 text-xs text-muted">
                <span>
                  {selecionados.size} de {registros.length} selecionado(s)
                </span>
                <button onClick={() => setSelecionados(new Set(registros.map((_, i) => i)))} className="underline">
                  todos
                </button>
                <button onClick={() => setSelecionados(new Set())} className="underline">
                  nenhum
                </button>
              </div>
              <div className="mt-1 max-h-56 overflow-auto rounded-md border border-line">
                <table className="w-full text-left text-xs">
                  <tbody className="divide-y divide-line">
                    {registros.slice(0, 500).map((r, i) => (
                      <tr key={i} className="bg-paper">
                        <td className="w-8 px-2 py-1">
                          <input
                            type="checkbox"
                            checked={selecionados.has(i)}
                            onChange={(e) =>
                              setSelecionados((s) => {
                                const n = new Set(s);
                                if (e.target.checked) n.add(i);
                                else n.delete(i);
                                return n;
                              })
                            }
                            aria-label={`Selecionar registro ${i + 1}`}
                          />
                        </td>
                        <td className="w-10 px-2 py-1 font-mono text-muted">{i + 1}</td>
                        <td className="px-2 py-1 font-mono text-ink">{chaveDoRegistro(r, campoChave) || "—"}</td>
                        <td className="px-2 py-1 text-ink">{descricaoDoRegistro(r)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {permitirTrocarColigada && registros.length > 0 && (
            <div className="mt-3 flex flex-wrap items-end gap-3 rounded-md border border-line bg-paper p-3 text-xs">
              <label className="flex flex-col gap-1">
                <span className={rotulo}>Trocar para a coligada</span>
                <input
                  value={coligadaNova}
                  onChange={(e) => setColigadaNova(e.target.value.replace(/\D/g, ""))}
                  className={`${campo} w-24`}
                />
              </label>
              <label className="flex items-center gap-2 text-ink">
                <input type="checkbox" checked={tambemContas} onChange={(e) => setTambemContas(e.target.checked)} />
                também a coligada das contas (CODCOLCONTA)
              </label>
              <button onClick={aplicarColigada} disabled={!coligadaNova} className={botaoSec}>
                Aplicar em todos os registros
              </button>
            </div>
          )}
        </div>
      )}

      {aba === "parametros" && (
        <div className="mt-3">
          <textarea
            value={parametros}
            onChange={(e) => setParametros(e.target.value)}
            rows={3}
            placeholder={"um por linha, nome=valor\nfilter=CODCOLIGADA = 1"}
            className={`${campo} font-mono text-xs`}
          />
          <label className="mt-2 flex items-center gap-2 text-xs text-ink">
            <input type="checkbox" checked={trazerCompleto} onChange={(e) => setTrazerCompleto(e.target.checked)} />
            Trazer completo, com as tabelas filhas (um GET por registro, até {MAX_GET_COMPLETO})
          </label>
        </div>
      )}

      {aba === "opcoes" && (
        <div className="mt-3 grid gap-2 text-xs text-ink">
          <label className="flex flex-wrap items-center gap-2">
            Em POST, se o registro já existir no RM:
            <select
              value={conectorAntigo ? "erro" : seExistir}
              onChange={(e) => setSeExistir(e.target.value as SeExistir)}
              disabled={conectorAntigo}
              className={`${campo} w-auto py-1 text-xs`}
            >
              <option value="pular">pular (não envia)</option>
              <option value="alterar">alterar (envia PUT)</option>
              <option value="erro">enviar POST mesmo assim</option>
            </select>
          </label>
          <label className="flex items-center gap-2">
            <input type="checkbox" checked={soPrimeiro} onChange={(e) => setSoPrimeiro(e.target.checked)} />
            Enviar só o primeiro selecionado (teste)
          </label>
          <label className="flex items-center gap-2">
            <input type="checkbox" checked={pararNoErro} onChange={(e) => setPararNoErro(e.target.checked)} />
            Parar no primeiro erro
          </label>
          <label className="flex items-center gap-2">
            <input type="checkbox" checked={removerNulos} onChange={(e) => setRemoverNulos(e.target.checked)} />
            Não enviar campos vazios (null) -- num PUT, null apaga o valor que está no RM
          </label>
          <label className="flex items-center gap-2">
            <input type="checkbox" checked={manterId} onChange={(e) => setManterId(e.target.checked)} />
            Enviar &quot;id&quot; e &quot;parent_id&quot; do GET (normalmente não precisa)
          </label>
          {camposNaoEnviar.length > 0 && (
            <p className="text-muted">Nunca enviados: {camposNaoEnviar.join(", ")}.</p>
          )}
          {previa && (
            <details>
              <summary className="cursor-pointer text-muted">Ver como o primeiro registro vai ser enviado</summary>
              <pre className="mt-1 max-h-64 overflow-auto rounded-md border border-line bg-paper p-2 font-mono text-[11px]">{previa}</pre>
            </details>
          )}
        </div>
      )}

      {erro && (
        <p className="mt-3 rounded-md border border-red-300 bg-red-50 px-3 py-2 text-xs text-red-700 dark:border-red-500/30 dark:bg-red-500/10 dark:text-red-300">
          {erro}
        </p>
      )}

      {/* --- Resposta ------------------------------------------------------ */}
      {resposta && (
        <div className="mt-4 rounded-md border border-line bg-paper p-3">
          <div className="flex flex-wrap items-center gap-2 text-sm">
            <span
              className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                resposta.ok
                  ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-500/15 dark:text-emerald-300"
                  : "bg-red-100 text-red-800 dark:bg-red-500/15 dark:text-red-300"
              }`}
            >
              {resposta.status ? `HTTP ${resposta.status}` : "Falhou"}
            </span>
            {resposta.tempo_ms !== undefined && <span className="text-xs text-muted">{resposta.tempo_ms} ms</span>}
            {resposta.ok && resposta.corpo !== undefined && extrairRegistros(resposta.corpo).length > 0 && (
              <>
                <span className="text-xs text-muted">{extrairRegistros(resposta.corpo).length} registro(s)</span>
                <button onClick={() => usarResposta(false)} className={`${botaoSec} ml-auto`}>
                  Usar como corpo (para enviar)
                </button>
                <button onClick={() => usarResposta(true)} className={botaoSec}>
                  Anexar ao corpo
                </button>
              </>
            )}
            {resposta.corpo !== undefined && (
              <>
                <button
                  onClick={() => copiar(textoResposta(resposta.corpo), "resp")}
                  className={`${botaoSec} ${resposta.ok ? "" : "ml-auto"}`}
                >
                  {copiado === "resp" ? "Copiado!" : "Copiar"}
                </button>
                <button onClick={() => baixarJson(textoResposta(resposta.corpo), `${nomeArquivo}_resposta.json`)} className={botaoSec}>
                  Baixar
                </button>
              </>
            )}
          </div>
          {(resposta.erro || !resposta.ok) && (
            <p className="mt-2 text-sm text-ink">
              {resposta.erro ?? (mensagemDoRm(resposta.corpo) || resposta.dica)}
              {resposta.como_corrigir && <span className="block text-muted">Como corrigir: {resposta.como_corrigir}</span>}
            </p>
          )}
          {resposta.corpo !== undefined && (
            <pre className="mt-2 max-h-96 overflow-auto rounded-md border border-line bg-surface p-2 font-mono text-xs text-ink">
              {textoResposta(resposta.corpo)}
            </pre>
          )}
          {resposta.truncado && <p className="mt-1 text-xs text-muted">Resposta grande: mostrando só o começo.</p>}
        </div>
      )}

      {lote && (
        <div className="mt-4">
          <p className="text-sm text-ink">
            <strong>{lote.sucesso}</strong> de {lote.total} com sucesso
            {lote.pulados > 0 && <span className="text-muted"> · {lote.pulados} pulado(s) por já existir</span>}
            {lote.falhas > 0 && <span className="text-red-600 dark:text-red-300"> · {lote.falhas} com erro</span>}
          </p>
          {selecionados.size > 0 && lote.sucesso > 0 && (
            <p className="mt-1 text-xs text-muted">
              Os enviados com sucesso saíram da seleção: o próximo clique manda os outros {selecionados.size}.
            </p>
          )}
          <div className="mt-2 max-h-72 overflow-auto rounded-md border border-line">
            <table className="w-full text-left text-xs">
              <thead className="bg-paper text-muted">
                <tr>
                  <th className="px-3 py-2">#</th>
                  <th className="px-3 py-2">Registro</th>
                  <th className="px-3 py-2">HTTP</th>
                  <th className="px-3 py-2">Resultado</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-line">
                {lote.itens.map((it) => (
                  <tr key={it.indice}>
                    <td className="px-3 py-2 font-mono">{it.indice}</td>
                    <td className="px-3 py-2 font-mono">
                      {it.chave ?? (chaveDoRegistro(registros[it.indice - 1] ?? {}, campoChave) || "—")}
                    </td>
                    <td className="px-3 py-2 font-mono">{it.status ?? "—"}</td>
                    <td className={`px-3 py-2 ${it.ok ? "text-emerald-700 dark:text-emerald-300" : "text-red-700 dark:text-red-300"}`}>
                      {it.ok
                        ? ACAO[it.acao ?? ""] ?? "OK"
                        : [it.erro, it.como_corrigir, mensagemDoRm(it.resposta), it.dica].filter(Boolean).join(" — ")}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
