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
  opcoes?: string[] | null;
};
type Modulo = {
  chave: string;
  nome: string;
  dataserver: string;
  descricao: string;
  operacoes: string[];
  campos: Campo[];
  nao_validado: string[];
  planilha_modelo_url?: string | null;
  planilha_modelo_xlsx_url?: string | null;
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

type LinhaLote = {
  linha: number;
  chave: string | null;
  valido: boolean;
  erros: { campo: string; mensagem: string }[];
  avisos: string[];
};
type ResultadoLote = {
  total: number;
  validos: number;
  invalidos: number;
  avisos_gerais: string[];
  linhas: LinhaLote[];
  jsonl?: string;
  json?: string;
  nome_arquivo?: string;
  instrucoes?: string[];
};

const OPERACAO_ROTULO: Record<string, string> = {
  incluir: "Incluir usuário novo",
  alterar: "Alterar usuário existente",
};

export default function GeradorDataServerPage() {
  const [modulos, setModulos] = useState<Modulo[]>([]);
  // Código do cliente (opcional): aplica a configuração dele (ex.: lista de códigos de acesso).
  const [cliente, setCliente] = useState("");
  const [chave, setChave] = useState<string | null>(null);
  const [operacao, setOperacao] = useState("incluir");
  const [valores, setValores] = useState<Valores>({});
  const [errosCampo, setErrosCampo] = useState<Record<string, string>>({});
  const [erro, setErro] = useState<string | null>(null);
  const [gerando, setGerando] = useState(false);
  const [resultado, setResultado] = useState<Resultado | null>(null);
  const [copiado, setCopiado] = useState(false);

  // Modo lote (planilha)
  const [modo, setModo] = useState<"formulario" | "lote">("lote");
  const [textoLote, setTextoLote] = useState("");
  const [nomeArquivoLote, setNomeArquivoLote] = useState<string | null>(null);
  const [lote, setLote] = useState<ResultadoLote | null>(null);
  const [processandoLote, setProcessandoLote] = useState(false);
  const [relatorioCopiado, setRelatorioCopiado] = useState(false);
  const [linkClienteCopiado, setLinkClienteCopiado] = useState(false);

  const modulo = modulos.find((m) => m.chave === chave) ?? null;

  function carregarModulos(codigoCliente: string, manterSelecao: boolean) {
    const q = codigoCliente.trim() ? `?cliente=${encodeURIComponent(codigoCliente.trim())}` : "";
    fetch(`/api/v1/dataserver/modulos${q}`)
      .then((r) => {
        if (!r.ok) throw new Error();
        return r.json();
      })
      .then((dados: Modulo[]) => {
        if (!Array.isArray(dados)) throw new Error();
        setModulos(dados);
        if (!manterSelecao && dados.length > 0) {
          setChave(dados[0].chave);
          setValores(valoresIniciais(dados[0]));
        }
      })
      .catch(() => setErro("Não foi possível carregar os módulos do gerador."));
  }

  useEffect(() => {
    carregarModulos("", false);
    // eslint-disable-next-line react-hooks/exhaustive-deps
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
      const resposta = await fetch(`/api/v1/dataserver/${modulo.chave}/gerar`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ operacao, valores, cliente: cliente.trim() || null }),
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

  async function lerArquivoLote(arquivo: File | null) {
    if (!arquivo) return;
    setErro(null);
    setLote(null);
    try {
      setTextoLote(await arquivo.text());
      setNomeArquivoLote(arquivo.name);
    } catch {
      setErro("Não foi possível ler o arquivo.");
    }
  }

  async function validarLote() {
    if (!modulo) return;
    setProcessandoLote(true);
    setErro(null);
    setLote(null);
    try {
      const resposta = await fetch(`/api/v1/dataserver/${modulo.chave}/lote`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ operacao, texto: textoLote, cliente: cliente.trim() || null }),
      });
      const dados = await resposta.json().catch(() => null);
      if (!resposta.ok) {
        throw new Error(
          typeof dados?.detail === "string" ? dados.detail : "Não foi possível processar o lote."
        );
      }
      setLote(dados);
    } catch (e) {
      setErro(e instanceof Error && e.message ? e.message : "Não foi possível processar o lote.");
    } finally {
      setProcessandoLote(false);
    }
  }

  async function baixarModelo() {
    if (!modulo) return;
    try {
      const resposta = await fetch(`/api/v1/dataserver/${modulo.chave}/modelo-csv`);
      if (!resposta.ok) throw new Error();
      baixarBlob(await resposta.blob(), `${modulo.dataserver}_modelo.csv`);
    } catch {
      setErro("Não foi possível baixar o modelo.");
    }
  }

  // Relatório de erros pra devolver ao cliente corrigir a planilha.
  function textoRelatorio(): string {
    if (!lote) return "";
    return lote.linhas
      .filter((l) => !l.valido)
      .map((l) => `Linha ${l.linha}${l.chave ? ` (${l.chave})` : ""}: ${l.erros.map((e) => e.mensagem).join(" · ")}`)
      .join("\n");
  }

  // Endereço da página pública que o analista manda ao cliente.
  async function copiarLinkCliente() {
    try {
      await navigator.clipboard.writeText(`${window.location.origin}/planilha-modelo`);
      setLinkClienteCopiado(true);
      setTimeout(() => setLinkClienteCopiado(false), 1500);
    } catch {
      setErro("Não foi possível copiar o link.");
    }
  }

  async function copiarRelatorio() {
    try {
      await navigator.clipboard.writeText(textoRelatorio());
      setRelatorioCopiado(true);
      setTimeout(() => setRelatorioCopiado(false), 1500);
    } catch {
      setErro("Não foi possível copiar -- use o botão de baixar o relatório.");
    }
  }

  function baixarRelatorioCsv() {
    if (!lote) return;
    const aspas = (v: string) => `"${v.replace(/"/g, '""')}"`;
    const linhas = lote.linhas
      .filter((l) => !l.valido)
      .map((l) => [String(l.linha), l.chave ?? "", l.erros.map((e) => e.mensagem).join(" | ")].map(aspas).join(";"));
    const csv = "\ufeff" + ["Linha;Usuário;Problemas", ...linhas].join("\r\n") + "\r\n";
    baixarBlob(new Blob([csv], { type: "text/csv;charset=utf-8" }), "relatorio_de_erros.csv");
  }

  function baixarLote(formato: "jsonl" | "json") {
    if (!lote?.jsonl || !lote.json || !lote.nome_arquivo) return;
    const conteudo = formato === "jsonl" ? lote.jsonl : lote.json;
    const nome = formato === "jsonl" ? lote.nome_arquivo : lote.nome_arquivo.replace(/\.jsonl$/, ".json");
    baixarBlob(new Blob([conteudo], { type: "application/json;charset=utf-8" }), nome);
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

            <div className="mt-6 flex flex-wrap items-end gap-3 text-sm">
              <div>
                <label htmlFor="cliente" className="block text-xs text-muted">
                  Cliente (opcional)
                </label>
                <input
                  id="cliente"
                  type="text"
                  value={cliente}
                  onChange={(e) => {
                    setCliente(e.target.value);
                    setResultado(null);
                  }}
                  onBlur={() => carregarModulos(cliente, true)}
                  placeholder="código do cliente"
                  className="mt-1 w-48 rounded-lg border border-line bg-paper px-3 py-1.5 text-sm text-ink placeholder:text-muted focus:border-brand"
                />
              </div>
              <p className="max-w-md text-xs text-muted">
                Se o cliente tiver configuração cadastrada, o Código de Acesso vira uma lista com os
                valores dele e o que estiver fora da lista é recusado.
              </p>
            </div>

            <div className="mt-4 flex flex-wrap gap-4 text-sm">
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

            <div className="mt-6 flex gap-2 text-sm">
              {(["lote", "formulario"] as const).map((m) => (
                <button
                  key={m}
                  onClick={() => {
                    setModo(m);
                    setErro(null);
                  }}
                  className={`rounded-md border px-4 py-1.5 transition ${
                    modo === m
                      ? "border-brand bg-brand text-white"
                      : "border-line bg-surface text-ink hover:border-brand"
                  }`}
                >
                  {m === "formulario" ? "Um por vez (formulário)" : "Em lote (planilha)"}
                </button>
              ))}
            </div>

            {modo === "lote" && (
              <div className="mt-6 rounded-lg border border-line bg-surface p-4">
                <h2 className="font-display text-sm font-bold text-ink">Carga em lote</h2>
                <p className="mt-1 text-xs text-muted">
                  Cole as linhas copiadas do Excel (com o cabeçalho) ou envie um CSV. Máximo de
                  500 linhas. O cabeçalho aceita o nome do campo (ex.: CODUSUARIO) ou o rótulo
                  da tela. Datas podem estar em DD/MM/AAAA. Nada do que você cola é salvo.
                </p>
                {modulo.planilha_modelo_url ? (
                  <div className="mt-3 rounded-md border border-line bg-paper p-3">
                    <a
                      href={modulo.planilha_modelo_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-block rounded-md bg-action px-4 py-2 text-sm font-medium text-white transition hover:bg-action-hover"
                    >
                      Abrir planilha modelo (Google Sheets)
                    </a>
                    <p className="mt-2 text-xs text-muted">
                      Abre a tela &quot;Fazer uma cópia&quot;. Preencha os códigos de acesso do cliente na aba
                      &quot;Listas&quot;, compartilhe a cópia com o cliente, e depois cole aqui as linhas
                      preenchidas (Ctrl+A, Ctrl+C na aba &quot;Dados&quot;).
                    </p>
                    <div className="mt-3 border-t border-line pt-3">
                      <p className="text-xs text-muted">
                        <strong>Para enviar ao cliente:</strong> mande o endereço da página do modelo. Ele
                        escolhe entre criar a própria cópia no Google ou baixar o arquivo (Excel/CSV).
                      </p>
                      <div className="mt-2 flex flex-wrap items-center gap-2">
                        <code className="rounded border border-line bg-surface px-2 py-1 text-xs text-ink">
                          {typeof window !== "undefined" ? `${window.location.origin}/planilha-modelo` : "/planilha-modelo"}
                        </code>
                        <button
                          onClick={copiarLinkCliente}
                          className="rounded-md border border-line px-3 py-1.5 text-xs text-ink transition hover:border-brand"
                        >
                          {linkClienteCopiado ? "Link copiado!" : "Copiar link para o cliente"}
                        </button>
                      </div>
                    </div>
                  </div>
                ) : (
                  <p className="mt-3 text-xs text-muted">
                    O link da planilha modelo ainda não foi configurado (variável de ambiente
                    PLANILHA_MODELO_GLB_USUARIO). Enquanto isso, baixe o modelo CSV abaixo.
                  </p>
                )}
                <div className="mt-3 flex flex-wrap items-center gap-3">
                  <button
                    onClick={baixarModelo}
                    className="rounded-md border border-line px-3 py-1.5 text-xs text-ink transition hover:border-brand"
                  >
                    Baixar modelo CSV
                  </button>
                  <label className="cursor-pointer rounded-md border border-line px-3 py-1.5 text-xs text-ink transition hover:border-brand">
                    {nomeArquivoLote ?? "Enviar arquivo CSV"}
                    <input
                      type="file"
                      accept=".csv,.txt,text/csv"
                      className="hidden"
                      onChange={(e) => lerArquivoLote(e.target.files?.[0] ?? null)}
                    />
                  </label>
                </div>
                <textarea
                  value={textoLote}
                  onChange={(e) => {
                    setTextoLote(e.target.value);
                    setNomeArquivoLote(null);
                    setLote(null);
                  }}
                  rows={8}
                  placeholder={"CODUSUARIO;NOME;CODACESSO;DATAINICIO\nana.teste;Ana Teste;Acesso01;18/11/2026"}
                  className="mt-3 w-full rounded-lg border border-line bg-paper px-3 py-2 font-mono text-xs text-ink placeholder:text-muted focus:border-brand"
                />
                <button
                  onClick={validarLote}
                  disabled={!textoLote.trim() || processandoLote}
                  className="mt-3 rounded-md bg-action px-5 py-2.5 text-sm font-medium text-white transition hover:bg-action-hover disabled:opacity-50"
                >
                  {processandoLote ? "Validando..." : "Validar lote"}
                </button>

                {lote && (
                  <div className="mt-5">
                    <p className="text-sm text-ink">
                      <strong>{lote.validos}</strong> válido(s) de {lote.total}
                      {lote.invalidos > 0 && (
                        <span className="text-red-600 dark:text-red-300">
                          {" "}-- {lote.invalidos} com erro (ficam de fora do arquivo)
                        </span>
                      )}
                    </p>
                    {lote.avisos_gerais.length > 0 && (
                      <ul className="mt-2 list-disc space-y-1 pl-5 text-xs text-amber-700 dark:text-amber-300">
                        {lote.avisos_gerais.map((a) => (
                          <li key={a}>{a}</li>
                        ))}
                      </ul>
                    )}

                    {lote.invalidos > 0 && (
                      <div className="mt-3 flex flex-wrap gap-2">
                        <button
                          onClick={copiarRelatorio}
                          className="rounded-md border border-line px-3 py-1.5 text-xs text-ink transition hover:border-brand"
                        >
                          {relatorioCopiado ? "Relatório copiado!" : "Copiar relatório de erros"}
                        </button>
                        <button
                          onClick={baixarRelatorioCsv}
                          className="rounded-md border border-line px-3 py-1.5 text-xs text-ink transition hover:border-brand"
                        >
                          Baixar relatório (CSV)
                        </button>
                      </div>
                    )}

                    {lote.invalidos > 0 && (
                      <div className="mt-3 max-h-72 overflow-auto rounded-md border border-line">
                        <table className="w-full text-left text-xs">
                          <thead className="bg-paper text-muted">
                            <tr>
                              <th className="px-3 py-2">Linha</th>
                              <th className="px-3 py-2">Usuário</th>
                              <th className="px-3 py-2">Problemas</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-line">
                            {lote.linhas
                              .filter((l) => !l.valido)
                              .slice(0, 200)
                              .map((l) => (
                                <tr key={l.linha}>
                                  <td className="px-3 py-2 font-mono">{l.linha}</td>
                                  <td className="px-3 py-2 font-mono">{l.chave ?? "—"}</td>
                                  <td className="px-3 py-2 text-red-700 dark:text-red-300">
                                    {l.erros.map((e) => e.mensagem).join(" · ")}
                                  </td>
                                </tr>
                              ))}
                          </tbody>
                        </table>
                      </div>
                    )}

                    {lote.jsonl && (
                      <>
                        <div className="mt-4 flex flex-wrap gap-2">
                          <button
                            onClick={() => baixarLote("jsonl")}
                            className="rounded-md bg-action px-4 py-2 text-sm font-medium text-white transition hover:bg-action-hover"
                          >
                            Baixar JSONL (para o script)
                          </button>
                          <button
                            onClick={() => baixarLote("json")}
                            className="rounded-md border border-line px-4 py-2 text-sm text-ink transition hover:border-brand"
                          >
                            Baixar JSON (lista)
                          </button>
                        </div>
                        <h3 className="mt-5 font-display text-sm font-bold text-ink">Como enviar</h3>
                        <ol className="mt-2 list-decimal space-y-2 pl-5 text-xs text-muted">
                          {(lote.instrucoes ?? []).map((i) => {
                            const [primeira, ...resto] = i.split("\n");
                            return (
                              <li key={i} className="break-words">
                                {primeira}
                                {resto.length > 0 && (
                                  <pre className="mt-1 overflow-auto rounded-md border border-line bg-paper p-2 font-mono text-[11px] text-ink">
                                    {resto.join("\n")}
                                  </pre>
                                )}
                              </li>
                            );
                          })}
                        </ol>
                      </>
                    )}
                  </div>
                )}
              </div>
            )}

            {modo === "formulario" && abas.map((aba) => (
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
                              {c.opcoes && c.opcoes.length > 0 ? (
                                <select
                                  id={id}
                                  value={String(valores[c.nome] ?? "")}
                                  onChange={(e) => alterar(c.nome, e.target.value)}
                                  className={`mt-1 w-full rounded-lg border bg-paper px-3 py-2 text-sm text-ink focus:border-brand ${
                                    msg ? "border-red-400" : "border-line"
                                  }`}
                                >
                                  <option value="">Selecione...</option>
                                  {c.opcoes.map((o) => (
                                    <option key={o} value={o}>
                                      {o}
                                    </option>
                                  ))}
                                </select>
                              ) : (
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
                              )}
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

            {modo === "formulario" && (<>
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
            </>)}
          </>
        )}

        {modo === "formulario" && resultado && (
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
