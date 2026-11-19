"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import {
  PORTA_PADRAO,
  lerConexaoSalva,
  mensagemConectorInacessivel,
  salvarConexao,
  urlConector,
} from "../lib/conector";

type ResultadoItem = {
  indice: number;
  chave: string | null;
  ok: boolean;
  status: number | null;
  resposta?: unknown;
  dica?: string | null;
  erro?: string;
  como_corrigir?: string;
};

type ResultadoLoteRm = {
  total: number;
  enviados: number;
  sucesso: number;
  falhas: number;
  nao_enviados: number;
  resultados: ResultadoItem[];
};

const PREFIXO_DS = "/rmsrestdataserver/rest/";

function mensagemDoRm(item: ResultadoItem): string {
  if (item.erro) return item.como_corrigir ? `${item.erro} ${item.como_corrigir}` : item.erro;
  const r = item.resposta as Record<string, unknown> | string | undefined;
  const msg =
    typeof r === "string"
      ? r
      : (r?.message as string) ?? (r?.Message as string) ?? (r?.detail as string) ?? (r?.mensagem as string);
  if (item.ok) return "OK";
  const texto = msg ?? (r ? JSON.stringify(r) : "");
  return [texto.slice(0, 300), item.dica].filter(Boolean).join(" — ");
}

/**
 * Envia os registros válidos do lote direto ao RM pelo conector local.
 * Usuário e senha ficam só na memória deste componente.
 */
export function EnviarAoRm({
  dataserver,
  campoChave,
  operacao,
  registros,
}: {
  dataserver: string;
  campoChave: string | null;
  operacao: string;
  registros: Record<string, unknown>[];
}) {
  const metodo = operacao === "alterar" ? "PUT" : "POST";
  const [porta, setPorta] = useState(PORTA_PADRAO);
  const [token, setToken] = useState("");
  const [usuario, setUsuario] = useState("");
  const [senha, setSenha] = useState("");
  const [caminho, setCaminho] = useState(PREFIXO_DS + dataserver);
  const [soPrimeiro, setSoPrimeiro] = useState(true);
  const [pararNoErro, setPararNoErro] = useState(false);
  const [enviando, setEnviando] = useState(false);
  const [resultado, setResultado] = useState<ResultadoLoteRm | null>(null);
  const [enviadosNoResultado, setEnviadosNoResultado] = useState<Record<string, unknown>[]>([]);
  // Depois de um teste bem-sucedido com o 1º registro, o envio seguinte começa do 2º.
  const [inicio, setInicio] = useState(0);
  const [erro, setErro] = useState<string | null>(null);

  useEffect(() => {
    const salva = lerConexaoSalva();
    if (salva) {
      setPorta(salva.porta);
      setToken(salva.token);
    }
  }, []);

  useEffect(() => setCaminho(PREFIXO_DS + dataserver), [dataserver]);
  // Lote novo (revalidado): recomeça do primeiro registro, em modo teste.
  useEffect(() => {
    setInicio(0);
    setSoPrimeiro(true);
    setResultado(null);
  }, [registros]);

  const alvo = soPrimeiro ? registros.slice(inicio, inicio + 1) : registros.slice(inicio);

  async function enviar() {
    setErro(null);
    setResultado(null);
    const confirmacao =
      `${metodo === "POST" ? "Incluir" : "Alterar"} ${alvo.length} registro(s) no RM?\n\n` +
      `${metodo} ${caminho}\n\nConfira se é o ambiente certo (de preferência homologação).`;
    if (!window.confirm(confirmacao)) return;
    setEnviando(true);
    try {
      const r = await fetch(`${urlConector(porta)}/rm/lote`, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-Conector-Token": token.trim() },
        body: JSON.stringify({
          metodo,
          caminho,
          registros: alvo,
          campo_chave: campoChave,
          parar_no_erro: pararNoErro,
          usuario,
          senha,
        }),
      });
      const dados = await r.json().catch(() => null);
      if (!r.ok || !dados || dados.resultados === undefined) {
        throw new Error(
          dados?.erro ? `${dados.erro} ${dados.como_corrigir ?? ""}`.trim() : "O conector recusou o envio."
        );
      }
      salvarConexao({ porta, token: token.trim() });
      setResultado(dados);
      setEnviadosNoResultado(alvo);
      if (soPrimeiro && dados.sucesso === 1 && inicio + 1 < registros.length) {
        setInicio(inicio + 1);
        setSoPrimeiro(false);
      }
    } catch (e) {
      const msg = e instanceof Error ? e.message : "";
      setErro(msg && msg !== "Failed to fetch" && !msg.includes("NetworkError") ? msg : mensagemConectorInacessivel(porta));
    } finally {
      setEnviando(false);
    }
  }

  const campo =
    "w-full rounded-md border border-line bg-surface px-3 py-2 text-sm text-ink focus:border-brand focus:outline-none";
  const rotulo = "text-xs font-medium text-muted";

  return (
    <div className="mt-6 rounded-lg border border-brand/40 bg-surface p-4">
      <h3 className="font-display text-sm font-bold text-ink">Enviar direto ao RM (conector local)</h3>
      <p className="mt-1 text-xs text-muted">
        Precisa do conector aberto na sua máquina. Ainda não abriu?{" "}
        <Link href="/conector-rm" target="_blank" className="underline">
          Veja como na tela Conector RM
        </Link>
        . Usuário e senha vão da sua máquina direto para o RM e não são guardados.
      </p>

      <div className="mt-3 grid gap-3 sm:grid-cols-4">
        <label className="flex flex-col gap-1">
          <span className={rotulo}>Porta</span>
          <input value={porta} onChange={(e) => setPorta(e.target.value.replace(/\D/g, ""))} className={campo} />
        </label>
        <label className="flex flex-col gap-1">
          <span className={rotulo}>Código de pareamento</span>
          <input
            value={token}
            onChange={(e) => setToken(e.target.value.toUpperCase())}
            className={`${campo} font-mono`}
          />
        </label>
        <label className="flex flex-col gap-1">
          <span className={rotulo}>Usuário do RM</span>
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
      <label className="mt-3 flex flex-col gap-1">
        <span className={rotulo}>
          Caminho no RM ({metodo}
          {metodo === "PUT" && campoChave ? ` + /<${campoChave}>` : ""})
        </span>
        <input value={caminho} onChange={(e) => setCaminho(e.target.value)} className={`${campo} font-mono text-xs`} />
      </label>
      <div className="mt-3 flex flex-wrap gap-4 text-xs text-ink">
        <label className="flex items-center gap-2">
          <input type="checkbox" checked={soPrimeiro} onChange={(e) => setSoPrimeiro(e.target.checked)} />
          Enviar só o primeiro registro (teste)
        </label>
        <label className="flex items-center gap-2">
          <input type="checkbox" checked={pararNoErro} onChange={(e) => setPararNoErro(e.target.checked)} />
          Parar no primeiro erro
        </label>
      </div>
      <button
        onClick={enviar}
        disabled={enviando || !token.trim() || !usuario.trim() || !senha || !caminho || alvo.length === 0}
        className="mt-3 rounded-md bg-action px-4 py-2 text-sm font-medium text-white transition hover:bg-action-hover disabled:opacity-50"
      >
        {enviando
          ? "Enviando..."
          : `${metodo === "POST" ? "Incluir" : "Alterar"} ${alvo.length} registro(s) no RM`}
      </button>

      {erro && (
        <p className="mt-3 rounded-md border border-red-300 bg-red-50 px-3 py-2 text-xs text-red-700 dark:border-red-500/30 dark:bg-red-500/10 dark:text-red-300">
          {erro}
        </p>
      )}

      {resultado && (
        <div className="mt-3">
          <p className="text-sm text-ink">
            <strong>{resultado.sucesso}</strong> de {resultado.total} com sucesso
            {resultado.falhas > 0 && <span className="text-red-600 dark:text-red-300"> · {resultado.falhas} com erro</span>}
            {resultado.nao_enviados > 0 && <span className="text-muted"> · {resultado.nao_enviados} não enviados</span>}
          </p>
          {inicio > 0 && !soPrimeiro && resultado.total === 1 && resultado.sucesso === 1 && (
            <p className="mt-1 text-xs text-emerald-700 dark:text-emerald-300">
              Teste OK. Confira o registro no RM; se estiver certo, o próximo clique envia os outros{" "}
              {registros.length - inicio} (o primeiro não é reenviado).
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
                {resultado.resultados.map((it) => (
                  <tr key={it.indice}>
                    <td className="px-3 py-2 font-mono">{it.indice}</td>
                    <td className="px-3 py-2 font-mono">
                      {it.chave ?? String(enviadosNoResultado[it.indice - 1]?.[campoChave ?? ""] ?? "—")}
                    </td>
                    <td className="px-3 py-2 font-mono">{it.status ?? "—"}</td>
                    <td className={`px-3 py-2 ${it.ok ? "text-emerald-700 dark:text-emerald-300" : "text-red-700 dark:text-red-300"}`}>
                      {mensagemDoRm(it)}
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
