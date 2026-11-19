"use client";

import { useEffect, useMemo, useState } from "react";
import { Header } from "../components/Header";
import {
  PORTA_PADRAO,
  lerConexaoSalva,
  mensagemConectorInacessivel,
  salvarConexao,
  urlConector,
} from "../lib/conector";

type Metodo = "GET" | "POST" | "PUT" | "DELETE";

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

type Historico = {
  quando: string;
  metodo: Metodo;
  caminho: string;
  status: number | null;
  tempo_ms: number | null;
  dataserver: string;
  chave: string;
  parametros: string;
  corpo: string;
};

const PREFIXO_DS = "/rmsrestdataserver/rest/";

function parsearParametros(texto: string): Record<string, string> {
  const saida: Record<string, string> = {};
  for (const linha of texto.split("\n")) {
    const i = linha.indexOf("=");
    if (i > 0) saida[linha.slice(0, i).trim()] = linha.slice(i + 1).trim();
  }
  return saida;
}

export default function ConectorRmPage() {
  // 1. Abrir o conector
  const [enderecoRm, setEnderecoRm] = useState("");
  const [porta, setPorta] = useState(PORTA_PADRAO);
  const [autoassinado, setAutoassinado] = useState(false);
  const [origem, setOrigem] = useState("");
  const [copiado, setCopiado] = useState<string | null>(null);

  // 2. Conectar
  const [token, setToken] = useState("");
  const [conectado, setConectado] = useState<{ rm: string; versao: string } | null>(null);
  const [conectando, setConectando] = useState(false);

  // 3. Credenciais (só memória)
  const [usuario, setUsuario] = useState("");
  const [senha, setSenha] = useState("");

  // 4. Chamada
  const [dataservers, setDataservers] = useState<string[]>([]);
  const [dataserver, setDataserver] = useState("GlbUsuarioData");
  const [metodo, setMetodo] = useState<Metodo>("GET");
  const [chave, setChave] = useState("");
  const [parametros, setParametros] = useState("");
  const [corpo, setCorpo] = useState("{\n  \n}");
  const [caminhoManual, setCaminhoManual] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);
  const [resposta, setResposta] = useState<RespostaRm | null>(null);
  const [historico, setHistorico] = useState<Historico[]>([]);
  const [erro, setErro] = useState<string | null>(null);

  useEffect(() => {
    setOrigem(window.location.origin);
    const salva = lerConexaoSalva();
    if (salva) {
      setPorta(salva.porta);
      setToken(salva.token);
    }
    fetch("/api/v1/dataserver/modulos")
      .then((r) => (r.ok ? r.json() : []))
      .then((mods: { dataserver?: string }[]) =>
        setDataservers(Array.isArray(mods) ? mods.map((m) => m.dataserver ?? "").filter(Boolean) : [])
      )
      .catch(() => setDataservers([]));
  }, []);

  const comando = useMemo(() => {
    const partes = ["python conector_rm.py", `--rm ${enderecoRm.trim() || "https://SERVIDOR-RM:PORTA"}`];
    if (origem) partes.push(`--origem ${origem}`);
    if (porta && porta !== PORTA_PADRAO) partes.push(`--porta ${porta}`);
    if (autoassinado) partes.push("--aceitar-certificado-autoassinado");
    return partes.join(" ");
  }, [enderecoRm, origem, porta, autoassinado]);

  const caminhoAuto = useMemo(() => {
    const base = PREFIXO_DS + encodeURIComponent(dataserver.trim());
    const precisaChave = metodo === "PUT" || metodo === "DELETE" || (metodo === "GET" && chave.trim());
    return precisaChave && chave.trim() ? `${base}/${encodeURIComponent(chave.trim())}` : base;
  }, [dataserver, metodo, chave]);
  const caminho = caminhoManual ?? caminhoAuto;

  async function copiar(texto: string, id: string) {
    try {
      await navigator.clipboard.writeText(texto);
      setCopiado(id);
      setTimeout(() => setCopiado(null), 2000);
    } catch {
      setErro("O navegador bloqueou a cópia: selecione o texto e copie manualmente.");
    }
  }

  async function conectar() {
    setConectando(true);
    setErro(null);
    setConectado(null);
    try {
      const r = await fetch(`${urlConector(porta)}/status`, {
        headers: { "X-Conector-Token": token.trim() },
      });
      const dados = await r.json().catch(() => ({}));
      if (!r.ok) throw new Error(`${dados.erro ?? "Conector recusou."} ${dados.como_corrigir ?? ""}`.trim());
      setConectado({ rm: dados.rm, versao: dados.versao });
      salvarConexao({ porta, token: token.trim() });
    } catch (e) {
      const msg = e instanceof Error ? e.message : "";
      setErro(
        msg && msg !== "Failed to fetch" && !msg.includes("NetworkError")
          ? msg
          : mensagemConectorInacessivel(porta)
      );
    } finally {
      setConectando(false);
    }
  }

  async function enviar() {
    setErro(null);
    setResposta(null);
    let corpoJson: unknown = undefined;
    if (metodo === "POST" || metodo === "PUT") {
      try {
        corpoJson = JSON.parse(corpo);
      } catch {
        setErro("O corpo não é um JSON válido.");
        return;
      }
    }
    if (metodo === "DELETE" && !window.confirm(`Excluir no RM?\n\n${caminho}\n\nEssa ação não pode ser desfeita pelo Acelerador.`)) {
      return;
    }
    setEnviando(true);
    const quando = new Date().toLocaleTimeString("pt-BR");
    try {
      const r = await fetch(`${urlConector(porta)}/rm`, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-Conector-Token": token.trim() },
        body: JSON.stringify({
          metodo,
          caminho,
          parametros: metodo === "GET" ? parsearParametros(parametros) : undefined,
          corpo: corpoJson,
          usuario,
          senha,
        }),
      });
      const dados: RespostaRm = await r.json().catch(() => ({ ok: false, erro: "Resposta inválida do conector." }));
      setResposta(dados);
      setHistorico((h) =>
        [
          {
            quando, metodo, caminho, status: dados.status ?? null, tempo_ms: dados.tempo_ms ?? null,
            dataserver, chave, parametros, corpo,
          },
          ...h,
        ].slice(0, 15)
      );
    } catch {
      setErro("Perdi a conexão com o conector. Ele ainda está aberto?");
      setConectado(null);
    } finally {
      setEnviando(false);
    }
  }

  function reabrir(h: Historico) {
    setMetodo(h.metodo);
    setDataserver(h.dataserver);
    setChave(h.chave);
    setParametros(h.parametros);
    setCorpo(h.corpo);
    setCaminhoManual(h.caminho === PREFIXO_DS + encodeURIComponent(h.dataserver) ||
      h.caminho.startsWith(PREFIXO_DS + encodeURIComponent(h.dataserver) + "/") ? null : h.caminho);
  }

  const campo = "w-full rounded-md border border-line bg-surface px-3 py-2 text-sm text-ink focus:border-brand focus:outline-none";
  const rotulo = "text-xs font-medium text-muted";
  const botaoSec = "rounded-md border border-line px-3 py-1.5 text-xs text-ink transition hover:border-brand";
  const podeEnviar = conectado && usuario.trim() && senha && caminho && !enviando;

  return (
    <main className="min-h-screen px-6 py-12 md:px-12 lg:px-20">
      <div className="mx-auto max-w-4xl">
        <Header />
        <h1 className="mt-6 font-display text-4xl font-bold text-ink md:text-5xl">Conector RM</h1>
        <p className="mt-3 max-w-2xl text-muted">
          Consulte, inclua, altere e exclua registros no RM do cliente (REST DataServer), como um Postman
          simplificado. As chamadas saem da <strong>sua máquina</strong>, por um conector local: o site não se
          conecta ao RM e não recebe sua senha.
        </p>

        {erro && (
          <p className="mt-6 rounded-md border border-red-300 bg-red-50 px-4 py-3 text-sm text-red-700 dark:border-red-500/30 dark:bg-red-500/10 dark:text-red-300">
            {erro}
          </p>
        )}

        {/* 1 */}
        <section className="mt-8 rounded-lg border border-line bg-surface p-5">
          <h2 className="font-display text-sm font-bold text-ink">1. Abra o conector na sua máquina</h2>
          <p className="mt-1 text-xs text-muted">
            Precisa de Python 3.9 ou mais novo (nada para instalar). A máquina precisa enxergar o RM (VPN do cliente,
            se for o caso).
          </p>
          <div className="mt-3 grid gap-3 sm:grid-cols-[2fr_1fr]">
            <label className="flex flex-col gap-1">
              <span className={rotulo}>Endereço do RM (REST/Host)</span>
              <input
                value={enderecoRm}
                onChange={(e) => setEnderecoRm(e.target.value)}
                placeholder="https://rm.cliente.com.br:8051"
                className={campo}
              />
            </label>
            <label className="flex flex-col gap-1">
              <span className={rotulo}>Porta local</span>
              <input value={porta} onChange={(e) => setPorta(e.target.value.replace(/\D/g, ""))} className={campo} />
            </label>
          </div>
          <label className="mt-2 flex items-center gap-2 text-xs text-ink">
            <input type="checkbox" checked={autoassinado} onChange={(e) => setAutoassinado(e.target.checked)} />
            O RM usa certificado HTTPS próprio (autoassinado)
          </label>
          <pre className="mt-3 overflow-x-auto rounded-md border border-line bg-paper px-3 py-2 font-mono text-xs text-ink">
            {comando}
          </pre>
          <div className="mt-2 flex flex-wrap gap-2">
            <a href="/conector/conector_rm.py" download className="rounded-md bg-action px-3 py-1.5 text-xs font-medium text-white transition hover:bg-action-hover">
              Baixar conector_rm.py
            </a>
            <button onClick={() => copiar(comando, "comando")} className={botaoSec}>
              {copiado === "comando" ? "Copiado!" : "Copiar comando"}
            </button>
          </div>
          <p className="mt-2 text-xs text-muted">
            Rode o comando na pasta onde salvou o arquivo. A janela mostra um <strong>código de pareamento</strong>:
            deixe-a aberta enquanto usa esta tela.
          </p>
        </section>

        {/* 2 */}
        <section className="mt-4 rounded-lg border border-line bg-surface p-5">
          <h2 className="font-display text-sm font-bold text-ink">2. Conecte</h2>
          <div className="mt-3 flex flex-wrap items-end gap-3">
            <label className="flex flex-col gap-1">
              <span className={rotulo}>Código de pareamento</span>
              <input
                value={token}
                onChange={(e) => setToken(e.target.value.toUpperCase())}
                placeholder="ex.: 7F3A91C2"
                className={`${campo} w-40 font-mono`}
              />
            </label>
            <button
              onClick={conectar}
              disabled={!token.trim() || !porta || conectando}
              className="rounded-md bg-action px-4 py-2 text-sm font-medium text-white transition hover:bg-action-hover disabled:opacity-50"
            >
              {conectando ? "Conectando..." : "Conectar"}
            </button>
            {conectado && (
              <span className="text-sm text-emerald-700 dark:text-emerald-300">
                ✓ Conectado ao RM <span className="font-mono">{conectado.rm}</span> (conector {conectado.versao})
              </span>
            )}
          </div>
        </section>

        {/* 3 */}
        <section className="mt-4 rounded-lg border border-line bg-surface p-5">
          <h2 className="font-display text-sm font-bold text-ink">3. Usuário do RM</h2>
          <div className="mt-3 grid gap-3 sm:grid-cols-2">
            <label className="flex flex-col gap-1">
              <span className={rotulo}>Usuário</span>
              <input value={usuario} onChange={(e) => setUsuario(e.target.value)} autoComplete="off" className={campo} />
            </label>
            <label className="flex flex-col gap-1">
              <span className={rotulo}>Senha</span>
              <input
                type="password"
                value={senha}
                onChange={(e) => setSenha(e.target.value)}
                autoComplete="new-password"
                className={campo}
              />
            </label>
          </div>
          <p className="mt-2 text-xs text-muted">
            Fica só na memória desta aba (some ao fechar ou recarregar) e vai da sua máquina direto para o RM.
            Use um usuário de homologação sempre que possível.
          </p>
        </section>

        {/* 4 */}
        <section className="mt-4 rounded-lg border border-line bg-surface p-5">
          <h2 className="font-display text-sm font-bold text-ink">4. Chamada</h2>
          <div className="mt-3 grid gap-3 sm:grid-cols-[auto_2fr_1fr]">
            <label className="flex flex-col gap-1">
              <span className={rotulo}>Método</span>
              <select value={metodo} onChange={(e) => setMetodo(e.target.value as Metodo)} className={campo}>
                <option value="GET">GET (consultar)</option>
                <option value="POST">POST (incluir)</option>
                <option value="PUT">PUT (alterar)</option>
                <option value="DELETE">DELETE (excluir)</option>
              </select>
            </label>
            <label className="flex flex-col gap-1">
              <span className={rotulo}>DataServer</span>
              <input
                value={dataserver}
                onChange={(e) => {
                  setDataserver(e.target.value);
                  setCaminhoManual(null);
                }}
                list="lista-dataservers"
                className={`${campo} font-mono`}
              />
              <datalist id="lista-dataservers">
                {dataservers.map((d) => (
                  <option key={d} value={d} />
                ))}
              </datalist>
            </label>
            <label className="flex flex-col gap-1">
              <span className={rotulo}>
                Chave {metodo === "GET" ? "(opcional)" : metodo === "POST" ? "(não usa)" : "(obrigatória)"}
              </span>
              <input
                value={chave}
                onChange={(e) => {
                  setChave(e.target.value);
                  setCaminhoManual(null);
                }}
                disabled={metodo === "POST"}
                placeholder="ex.: maria.silva"
                className={`${campo} font-mono disabled:opacity-50`}
              />
            </label>
          </div>

          <label className="mt-3 flex flex-col gap-1">
            <span className={rotulo}>
              Caminho no RM{" "}
              {caminhoManual !== null && (
                <button onClick={() => setCaminhoManual(null)} className="ml-2 underline">
                  voltar ao automático
                </button>
              )}
            </span>
            <input
              value={caminho}
              onChange={(e) => setCaminhoManual(e.target.value)}
              className={`${campo} font-mono text-xs`}
            />
          </label>

          {metodo === "GET" && (
            <label className="mt-3 flex flex-col gap-1">
              <span className={rotulo}>Parâmetros (um por linha, nome=valor)</span>
              <textarea
                value={parametros}
                onChange={(e) => setParametros(e.target.value)}
                rows={2}
                placeholder="filter=CODUSUARIO = 'maria.silva'"
                className={`${campo} font-mono text-xs`}
              />
            </label>
          )}

          {(metodo === "POST" || metodo === "PUT") && (
            <label className="mt-3 flex flex-col gap-1">
              <span className={rotulo}>Corpo (JSON)</span>
              <textarea
                value={corpo}
                onChange={(e) => setCorpo(e.target.value)}
                rows={8}
                spellCheck={false}
                className={`${campo} font-mono text-xs`}
              />
            </label>
          )}

          <button
            onClick={enviar}
            disabled={!podeEnviar}
            className={`mt-4 rounded-md px-4 py-2 text-sm font-medium text-white transition disabled:opacity-50 ${
              metodo === "DELETE" ? "bg-red-600 hover:bg-red-700" : "bg-action hover:bg-action-hover"
            }`}
          >
            {enviando ? "Enviando..." : `Enviar ${metodo}`}
          </button>
          {!conectado && <span className="ml-3 text-xs text-muted">Conecte primeiro (passo 2).</span>}
          {conectado && (!usuario.trim() || !senha) && (
            <span className="ml-3 text-xs text-muted">Informe usuário e senha (passo 3).</span>
          )}

          {resposta && (
            <div className="mt-4 rounded-md border border-line bg-paper p-3">
              <div className="flex flex-wrap items-center gap-3 text-sm">
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
                {resposta.corpo !== undefined && (
                  <button
                    onClick={() =>
                      copiar(typeof resposta.corpo === "string" ? resposta.corpo : JSON.stringify(resposta.corpo, null, 2), "resposta")
                    }
                    className={`${botaoSec} ml-auto`}
                  >
                    {copiado === "resposta" ? "Copiado!" : "Copiar resposta"}
                  </button>
                )}
              </div>
              {(resposta.erro || resposta.dica) && (
                <p className="mt-2 text-sm text-ink">
                  {resposta.erro ?? resposta.dica}
                  {resposta.como_corrigir && <span className="block text-muted">Como corrigir: {resposta.como_corrigir}</span>}
                </p>
              )}
              {resposta.corpo !== undefined && (
                <pre className="mt-2 max-h-96 overflow-auto rounded-md border border-line bg-surface p-2 font-mono text-xs text-ink">
                  {typeof resposta.corpo === "string" ? resposta.corpo : JSON.stringify(resposta.corpo, null, 2)}
                </pre>
              )}
              {resposta.truncado && <p className="mt-1 text-xs text-muted">Resposta grande: mostrando só o começo.</p>}
            </div>
          )}
        </section>

        {historico.length > 0 && (
          <section className="mt-4 rounded-lg border border-line bg-surface p-5">
            <h2 className="font-display text-sm font-bold text-ink">Histórico desta sessão</h2>
            <ul className="mt-2 divide-y divide-line text-xs">
              {historico.map((h, i) => (
                <li key={`${h.quando}-${i}`} className="flex flex-wrap items-center gap-3 py-1.5">
                  <span className="text-muted">{h.quando}</span>
                  <span className="font-mono font-medium text-ink">{h.metodo}</span>
                  <span className="flex-1 truncate font-mono text-ink" title={h.caminho}>
                    {h.caminho}
                  </span>
                  <span className="text-muted">{h.status ?? "falhou"}</span>
                  <button onClick={() => reabrir(h)} className={botaoSec}>
                    Repetir
                  </button>
                </li>
              ))}
            </ul>
            <p className="mt-2 text-xs text-muted">Sem senha: o histórico some ao fechar a aba.</p>
          </section>
        )}
      </div>
    </main>
  );
}
