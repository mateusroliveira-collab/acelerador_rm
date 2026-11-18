"use client";

import { useEffect, useState } from "react";
import { Header } from "../components/Header";
import { baixarBlob } from "../lib/download";

type Campo = {
  nome: string;
  rotulo: string;
  tipo: "texto" | "email" | "inteiro" | "booleano" | "data";
  obrigatorio: boolean;
  padrao: string | number | boolean | null;
  ajuda: string;
  aba: string;
};
type Modulo = {
  chave: string;
  nome: string;
  dataserver: string;
  descricao: string;
  operacoes: string[];
  campos: Campo[];
  nao_validado: string[];
};
type Valores = Record<string, string | boolean>;
type Resultado = {
  json: string;
  nome_arquivo: string;
  instrucoes: string[];
  avisos: string[];
};

function hojeISO() {
  const d = new Date();
  const mes = String(d.getMonth() + 1).padStart(2, "0");
  const dia = String(d.getDate()).padStart(2, "0");
  return `${d.getFullYear()}-${mes}-${dia}`;
}

function valoresIniciais(modulo: Modulo): Valores {
  const v: Valores = {};
  for (const c of modulo.campos) {
    if (c.tipo === "booleano") v[c.nome] = Boolean(c.padrao);
    else if (c.tipo === "data" && c.nome === "DATAINICIO") v[c.nome] = hojeISO();
    else v[c.nome] = c.padrao != null ? String(c.padrao) : "";
  }
  return v;
}

const OPERACAO_ROTULO: Record<string, string> = {
  incluir: "Incluir usuário novo",
  alterar: "Alterar usuário existente",
};

export default function GeradorDataServerPage() {
  const [modulos, setModulos] = useState<Modulo[]>([]);
  const [chave, setChave] = useState<string | null>(null);
  const [operacao, setOperacao] = useState("incluir");
  const [valores, setValores] = useState<Valores>({});
  const [errosCampo, setErrosCampo] = useState<Record<string, string>>({});
  const [erro, setErro] = useState<string | null>(null);
  const [gerando, setGerando] = useState(false);
  const [resultado, setResultado] = useState<Resultado | null>(null);
  const [copiado, setCopiado] = useState(false);

  const modulo = modulos.find((m) => m.chave === chave) ?? null;

  useEffect(() => {
    fetch("/api/dataserver/modulos")
      .then((r) => {
        if (!r.ok) throw new Error();
        return r.json();
      })
      .then((dados: Modulo[]) => {
        if (!Array.isArray(dados)) throw new Error();
        setModulos(dados);
        if (dados.length > 0) {
          setChave(dados[0].chave);
          setValores(valoresIniciais(dados[0]));
        }
      })
      .catch(() => setErro("Não foi possível carregar os módulos do gerador."));
  }, []);

  function trocarModulo(nova: string) {
    const m = modulos.find((x) => x.chave === nova);
    if (!m) return;
    setChave(nova);
    setOperacao(m.operacoes[0]);
    setValores(valoresIniciais(m));
    setErrosCampo({});
    setResultado(null);
    setErro(null);
  }

  function alterar(nome: string, valor: string | boolean) {
    setValores((v) => ({ ...v, [nome]: valor }));
    setResultado(null); // a prévia antiga não vale mais
    setErrosCampo((e) => {
      if (!e[nome]) return e;
      const { [nome]: _removido, ...resto } = e;
      return resto;
    });
  }

  async function gerar() {
    if (!modulo) return;
    setGerando(true);
    setErro(null);
    setErrosCampo({});
    setResultado(null);
    try {
      const resposta = await fetch(`/api/dataserver/${modulo.chave}/gerar`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ operacao, valores }),
      });
      const dados = await resposta.json().catch(() => null);
      if (resposta.status === 422 && dados?.detail?.erros) {
        const porCampo: Record<string, string> = {};
        for (const e of dados.detail.erros as { campo: string; mensagem: string }[]) {
          porCampo[e.campo] = e.mensagem;
        }
        setErrosCampo(porCampo);
        setErro("Corrija os campos destacados e gere novamente.");
        return;
      }
      if (!resposta.ok) throw new Error();
      setResultado(dados);
    } catch {
      setErro("Não foi possível gerar o arquivo.");
    } finally {
      setGerando(false);
    }
  }

  function baixar() {
    if (!resultado) return;
    baixarBlob(
      new Blob([resultado.json], { type: "application/json;charset=utf-8" }),
      resultado.nome_arquivo
    );
  }

  async function copiar() {
    if (!resultado) return;
    try {
      await navigator.clipboard.writeText(resultado.json);
      setCopiado(true);
      setTimeout(() => setCopiado(false), 1500);
    } catch {
      setErro("Não foi possível copiar -- use o botão Baixar.");
    }
  }

  const abas = modulo ? Array.from(new Set(modulo.campos.map((c) => c.aba))) : [];

  return (
    <main className="min-h-screen px-6 py-12 md:px-12 lg:px-20">
      <div className="mx-auto max-w-4xl">
        <Header />
        <h1 className="mt-6 font-display text-4xl font-bold text-ink md:text-5xl">
          Gerador de DataServer
        </h1>
        <p className="mt-3 max-w-xl text-muted">
          Preencha os campos, confira a prévia e baixe o arquivo pronto. A
          ferramenta <strong>não conecta ao RM</strong> e não guarda nada do
          que você digita -- o envio é feito por você.
        </p>

        {/* Módulos -- mais entram aqui conforme forem criados */}
        {modulos.length > 0 && (
          <div className="mt-8 flex flex-wrap gap-2">
            {modulos.map((m) => (
              <button
                key={m.chave}
                onClick={() => trocarModulo(m.chave)}
                className={`rounded-lg border px-4 py-2 text-left text-sm transition ${
                  chave === m.chave
                    ? "border-brand bg-brand text-white"
                    : "border-line bg-surface text-ink hover:border-brand"
                }`}
              >
                <span className="block font-bold">{m.nome}</span>
                <span className={chave === m.chave ? "text-white/70" : "text-muted"}>
                  <span className="font-mono text-xs">{m.dataserver}</span>
                </span>
              </button>
            ))}
          </div>
        )}

        {erro && (
          <p className="mt-4 rounded-md border border-red-300 bg-red-50 px-4 py-3 text-sm text-red-700 dark:border-red-500/30 dark:bg-red-500/10 dark:text-red-300">
            {erro}
          </p>
        )}

        {modulo && (
          <>
            <p className="mt-4 text-sm text-muted">{modulo.descricao}</p>

            {modulo.nao_validado.length > 0 && (
              <details className="mt-3 rounded-md border border-line bg-surface px-4 py-2 text-xs text-muted">
                <summary className="cursor-pointer font-medium text-ink">
                  Pontos do schema ainda não confirmados contra o RM
                </summary>
                <ul className="mt-2 list-disc space-y-1 pl-5">
                  {modulo.nao_validado.map((t) => (
                    <li key={t}>{t}</li>
                  ))}
                </ul>
              </details>
            )}

            <div className="mt-6 flex flex-wrap gap-4 text-sm">
              {modulo.operacoes.map((op) => (
                <label key={op} className="flex cursor-pointer items-center gap-2 text-ink">
                  <input
                    type="radio"
                    name="operacao"
                    checked={operacao === op}
                    onChange={() => {
                      setOperacao(op);
                      setResultado(null);
                    }}
                  />
                  {OPERACAO_ROTULO[op] ?? op}
                </label>
              ))}
            </div>

            {abas.map((aba) => (
              <fieldset
                key={aba}
                className="mt-6 rounded-lg border border-line bg-surface p-4"
              >
                <legend className="px-2 font-display text-sm font-bold text-ink">
                  {aba}
                </legend>
                <div className="grid gap-4 sm:grid-cols-2">
                  {modulo.campos
                    .filter((c) => c.aba === aba)
                    .map((c) => {
                      const id = `campo-${c.nome}`;
                      const msg = errosCampo[c.nome];
                      return (
                        <div key={c.nome} className={c.tipo === "booleano" ? "flex items-end" : ""}>
                          {c.tipo === "booleano" ? (
                            <label htmlFor={id} className="flex cursor-pointer items-center gap-2 text-sm text-ink">
                              <input
                                id={id}
                                type="checkbox"
                                checked={Boolean(valores[c.nome])}
                                onChange={(e) => alterar(c.nome, e.target.checked)}
                              />
                              <span className={c.obrigatorio ? "font-bold" : ""}>{c.rotulo}</span>
                            </label>
                          ) : (
                            <>
                              <label
                                htmlFor={id}
                                className={`block text-sm text-ink ${c.obrigatorio ? "font-bold" : ""}`}
                              >
                                {c.rotulo}
                              </label>
                              <input
                                id={id}
                                type={
                                  c.tipo === "data"
                                    ? "date"
                                    : c.tipo === "inteiro"
                                      ? "number"
                                      : c.tipo === "email"
                                        ? "email"
                                        : "text"
                                }
                                min={c.tipo === "inteiro" ? 0 : undefined}
                                value={String(valores[c.nome] ?? "")}
                                onChange={(e) => alterar(c.nome, e.target.value)}
                                className={`mt-1 w-full rounded-lg border bg-paper px-3 py-2 text-sm text-ink focus:border-brand ${
                                  msg ? "border-red-400" : "border-line"
                                }`}
                              />
                            </>
                          )}
                          {c.ajuda && !msg && (
                            <p className="mt-1 text-xs text-muted">{c.ajuda}</p>
                          )}
                          {msg && <p className="mt-1 text-xs text-red-600 dark:text-red-300">{msg}</p>}
                        </div>
                      );
                    })}
                </div>
              </fieldset>
            ))}

            <p className="mt-3 text-xs text-muted">
              Campos em <strong>negrito</strong> são obrigatórios (igual à tela do RM).
              A senha não é gerada nem pedida por esta ferramenta.
            </p>

            <button
              onClick={gerar}
              disabled={gerando}
              className="mt-4 rounded-md bg-action px-5 py-2.5 text-sm font-medium text-white transition hover:bg-action-hover disabled:opacity-50"
            >
              {gerando ? "Gerando..." : "Validar e gerar prévia"}
            </button>
          </>
        )}

        {resultado && (
          <div className="mt-8 rounded-lg border border-line bg-surface p-4">
            <h2 className="font-display text-sm font-bold text-ink">Prévia -- {resultado.nome_arquivo}</h2>
            {resultado.avisos.length > 0 && (
              <ul className="mt-2 list-disc space-y-1 pl-5 text-xs text-amber-700 dark:text-amber-300">
                {resultado.avisos.map((a) => (
                  <li key={a}>{a}</li>
                ))}
              </ul>
            )}
            <pre className="mt-3 max-h-96 overflow-auto rounded-md border border-line bg-paper p-3 font-mono text-xs text-ink">
              {resultado.json}
            </pre>
            <div className="mt-3 flex flex-wrap gap-2">
              <button
                onClick={baixar}
                className="rounded-md bg-action px-4 py-2 text-sm font-medium text-white transition hover:bg-action-hover"
              >
                Baixar JSON
              </button>
              <button
                onClick={copiar}
                className="rounded-md border border-line px-4 py-2 text-sm text-ink transition hover:border-brand"
              >
                {copiado ? "Copiado!" : "Copiar"}
              </button>
            </div>

            <h3 className="mt-5 font-display text-sm font-bold text-ink">Como enviar</h3>
            <ol className="mt-2 list-decimal space-y-1 pl-5 text-xs text-muted">
              {resultado.instrucoes.map((i) => (
                <li key={i} className="break-words">{i}</li>
              ))}
            </ol>
          </div>
        )}
      </div>
    </main>
  );
}
