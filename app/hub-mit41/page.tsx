"use client";

import { Fragment, useMemo, useState } from "react";
import { Header } from "../components/Header";
import { baixarBlob, nomeLimpo } from "../lib/download";

type Status = "pronto" | "ajustar" | "criar" | "sem_dados";

type Evidencia = { valor: string; trecho: string };

type Candidato = {
  grupo: string;
  arquivo: string;
  id: number | null;
  codigo: string;
  nome: string;
  resumo: string[];
  pontos: number;
  divergencias: string[];
  coincidencias: string[];
  semelhanca_nome: number;
};

type Ajuste = {
  dimensao: string;
  rotulo: string;
  mit_pede: string;
  xml_base_faz: string;
  area: string;
  propriedade: string;
  trecho: string;
};

type Ficha = {
  grupo: string | null;
  codigo_sugerido: string | null;
  nome: string;
  xml_base: { grupo: string; arquivo: string; id: number | null; codigo: string; nome: string } | null;
  ajustes: Ajuste[];
  pendencias: string[];
  regra_desejada: string[];
  segue_para_no_xml_base: string[];
};

type Fluxo = { numero: string; titulo: string; direcao: "origem" | "destino" | "citado"; trecho: string };

type Movimento = {
  numero: string;
  titulo: string;
  status: Status;
  confianca?: "alta" | "media" | "baixa";
  grupo: string | null;
  origem_grupo: string | null;
  requisitos: {
    valores: Record<string, string | null>;
    ambiguas: string[];
    evidencias: Record<string, Evidencia[]>;
  };
  candidatos: Candidato[];
  ficha: Ficha | null;
  fluxo: Fluxo[];
  avisos: string[];
};

type Resultado = {
  resumo: { total: number; pronto: number; ajustar: number; criar: number; sem_dados: number; xmls_na_biblioteca: number };
  movimentos: Movimento[];
};

// Do interpretador: o subprocesso como está na MIT (AS IS / TO BE / GAP).
type SugestaoGrupo = { grupo: string; pontuacao: number; sinais: string[] };
type SubProcesso = {
  numero: string;
  titulo: string;
  processo_relacionado: string | null;
  texto_as_is: string | null;
  texto_to_be: string | null;
  gap: string | null;
  sugestao_aproximada: SugestaoGrupo[];
};
type RespostaHub = { analise: Resultado | null; subprocessos: SubProcesso[]; texto_para_ponte: string };

const STATUS: Record<Status, { rotulo: string; descricao: string; classe: string }> = {
  pronto: {
    rotulo: "Pronto",
    descricao: "Há XML na biblioteca que atende",
    classe: "bg-emerald-100 text-emerald-800 dark:bg-emerald-500/15 dark:text-emerald-300",
  },
  ajustar: {
    rotulo: "Ajustar",
    descricao: "Há XML-base, com parâmetros a mudar",
    classe: "bg-amber-100 text-amber-800 dark:bg-amber-500/15 dark:text-amber-300",
  },
  criar: {
    rotulo: "Criar",
    descricao: "Nada parecido: seguir a ficha",
    classe: "bg-red-100 text-red-800 dark:bg-red-500/15 dark:text-red-300",
  },
  sem_dados: {
    rotulo: "Sem dados",
    descricao: "Não é movimento ou a MIT não detalha",
    classe: "bg-surface text-muted border border-line",
  },
};

const DIMENSOES: Record<string, string> = {
  estoque: "Estoque",
  financeiro: "Financeiro",
  escritura_fiscal: "Escrituração fiscal",
  natureza: "Natureza da nota",
  emite_nfe: "Emissão de NF-e",
  emite_nfse: "Emissão de NFS-e",
  orcamento: "Orçamento",
  contabiliza: "Contabilização",
  aprovacao: "Aprovação",
  gera_contrato: "Gera contrato",
};

const VALORES: Record<string, string> = {
  aumenta: "aumenta",
  diminui: "diminui",
  nenhum: "nenhum",
  transfere: "transfere",
  pagar: "a pagar",
  receber: "a receber",
  gera: "gera (sem direção)",
  sim: "sim",
  nao: "não",
  E: "entrada",
  S: "saída",
  afeta: "afeta",
  estorna: "estorna",
};

const DIRECAO: Record<Fluxo["direcao"], string> = {
  origem: "vem de",
  destino: "segue para",
  citado: "cita",
};

function csvCelula(v: string) {
  return /[";\n]/.test(v) ? `"${v.replace(/"/g, '""')}"` : v;
}

function gerarCsv(r: Resultado, subs: Map<string, SubProcesso>) {
  const cab = [
    "Número", "Movimento", "Status", "Confiança", "Grupo", "Código sugerido",
    "XML-base", "Ajustes", "Pendências", "Avisos", "Processo relacionado", "GAP",
  ];
  const linhas = r.movimentos.map((m) => [
    m.numero,
    m.titulo,
    STATUS[m.status].rotulo,
    m.confianca ?? "",
    m.grupo ?? "",
    m.ficha?.codigo_sugerido ?? "",
    m.ficha?.xml_base ? `${m.ficha.xml_base.grupo} / ${m.ficha.xml_base.arquivo}` : "",
    (m.ficha?.ajustes ?? []).map((a) => `${a.rotulo}: ${a.mit_pede} (XML: ${a.xml_base_faz}) -> ${a.propriedade}`).join(" | "),
    (m.ficha?.pendencias ?? []).join(" | "),
    m.avisos.join(" | "),
    subs.get(m.numero)?.processo_relacionado ?? "",
    subs.get(m.numero)?.gap ?? "",
  ]);
  // BOM + ";" para o Excel em português abrir com acentos e colunas certas.
  return "﻿" + [cab, ...linhas].map((l) => l.map(csvCelula).join(";")).join("\r\n");
}

function gerarMarkdown(r: Resultado, subs: Map<string, SubProcesso>) {
  const s = r.resumo;
  const out: string[] = [
    "# Hub MIT 41: análise x biblioteca de XMLs",
    "",
    `${s.total} movimentos: ${s.pronto} prontos, ${s.ajustar} a ajustar, ${s.criar} a criar, ${s.sem_dados} sem dados. ` +
      `Biblioteca: ${s.xmls_na_biblioteca} XMLs.`,
    "",
    "> Análise por regras (sem IA). Confira cada ficha antes de parametrizar.",
    "",
  ];
  for (const m of r.movimentos) {
    out.push(`## ${m.numero} ${m.titulo} — ${STATUS[m.status].rotulo}${m.confianca ? ` (confiança ${m.confianca})` : ""}`);
    out.push("");
    if (m.grupo) out.push(`- **Grupo:** ${m.grupo} (pelo ${m.origem_grupo ?? "-"})`);
    const sp = subs.get(m.numero);
    if (sp?.processo_relacionado) out.push(`- **Processo relacionado:** ${sp.processo_relacionado}`);
    if (sp?.texto_as_is) out.push(`- **AS IS:** ${sp.texto_as_is}`);
    if (sp?.texto_to_be) out.push(`- **TO BE:** ${sp.texto_to_be}`);
    if (sp?.gap) out.push(`- **GAP:** ${sp.gap}`);
    const f = m.ficha;
    if (f) {
      if (f.codigo_sugerido) out.push(`- **Código sugerido:** ${f.codigo_sugerido}`);
      if (f.xml_base) out.push(`- **XML-base:** ${f.xml_base.grupo} / ${f.xml_base.arquivo}`);
      if (f.regra_desejada.length) out.push(`- **O que a MIT pede:** ${f.regra_desejada.join(" ")}`);
      if (f.ajustes.length) {
        out.push("- **Ajustes:**");
        for (const a of f.ajustes) {
          out.push(`  - ${a.rotulo}: MIT pede "${a.mit_pede}", XML-base faz "${a.xml_base_faz}". ` +
            `Mexer em ${a.area} (\`${a.propriedade}\`). Trecho da MIT: "${a.trecho}"`);
        }
      }
      if (f.pendencias.length) {
        out.push("- **Confirmar com o cliente:**");
        for (const p of f.pendencias) out.push(`  - ${p}`);
      }
    }
    if (m.fluxo.length) {
      out.push(`- **Fluxo:** ${m.fluxo.map((x) => `${DIRECAO[x.direcao]} ${x.numero} ${x.titulo}`).join("; ")}`);
    }
    for (const a of m.avisos) out.push(`- ⚠ ${a}`);
    out.push("");
  }
  return out.join("\n");
}

/** "Nenhum", "-", "não há" etc. não contam como GAP. */
function temGap(gap: string | null | undefined) {
  if (!gap) return false;
  const t = gap.trim().toLowerCase();
  return !!t && !/^(nenhum|nenhuma|n[aã]o h[aá]|n[aã]o|-+|n\/a|sem gap)\.?$/.test(t);
}

export default function HubMit41Page() {
  const [arquivo, setArquivo] = useState<File | null>(null);
  const [texto, setTexto] = useState("");
  const [resultado, setResultado] = useState<Resultado | null>(null);
  const [subprocessos, setSubprocessos] = useState<SubProcesso[] | null>(null);
  const [textoPonte, setTextoPonte] = useState("");
  const [aba, setAba] = useState<"movimentos" | "subprocessos">("movimentos");
  const [subAberto, setSubAberto] = useState<number | null>(null);
  const [copiado, setCopiado] = useState(false);
  const [filtro, setFiltro] = useState<Status | "todos">("todos");
  const [aberto, setAberto] = useState<string | null>(null);
  const [carregando, setCarregando] = useState(false);
  const [baixando, setBaixando] = useState<string | null>(null);
  const [erro, setErro] = useState<string | null>(null);

  const porNumero = useMemo(
    () => new Map((subprocessos ?? []).filter((s) => s.numero).map((s) => [s.numero, s])),
    [subprocessos]
  );

  const visiveis = useMemo(
    () => (resultado?.movimentos ?? []).filter((m) => filtro === "todos" || m.status === filtro),
    [resultado, filtro]
  );

  async function analisar() {
    if (!arquivo && !texto.trim()) return;
    setCarregando(true);
    setErro(null);
    setResultado(null);
    setSubprocessos(null);
    setTextoPonte("");
    setAberto(null);
    setSubAberto(null);
    setFiltro("todos");
    try {
      let resposta: Response;
      if (arquivo) {
        const form = new FormData();
        form.append("arquivo", arquivo);
        resposta = await fetch("/api/xml/hub-mit41-pdf", { method: "POST", body: form });
      } else {
        resposta = await fetch("/api/xml/hub-mit41", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ texto }),
        });
      }
      if (!resposta.ok) {
        const dados = await resposta.json().catch(() => null);
        throw new Error(dados?.detail || "Não foi possível analisar a MIT.");
      }
      const dados: RespostaHub = await resposta.json();
      setResultado(dados.analise);
      setSubprocessos(dados.subprocessos);
      setTextoPonte(dados.texto_para_ponte);
      setAba(dados.analise ? "movimentos" : "subprocessos");
    } catch (e) {
      setErro(e instanceof Error && e.message ? e.message : "Não foi possível analisar a MIT.");
    } finally {
      setCarregando(false);
    }
  }

  async function baixarXmlBase(base: NonNullable<Ficha["xml_base"]>) {
    const chave = `${base.grupo}/${base.arquivo}/${base.id ?? ""}`;
    setBaixando(chave);
    setErro(null);
    try {
      const resposta = base.id
        ? await fetch(`/api/xml/baixar-personalizado/${base.id}`)
        : await fetch(`/api/xml/limpar?${new URLSearchParams({ grupo: base.grupo, arquivo: base.arquivo })}`, {
            method: "POST",
          });
      if (!resposta.ok) throw new Error();
      baixarBlob(await resposta.blob(), nomeLimpo(base.arquivo));
    } catch {
      setErro(`Não foi possível baixar "${base.arquivo}".`);
    } finally {
      setBaixando(null);
    }
  }

  function exportar(formato: "csv" | "md") {
    if (!resultado) return;
    if (formato === "csv") {
      baixarBlob(new Blob([gerarCsv(resultado, porNumero)], { type: "text/csv;charset=utf-8" }), "hub_mit41.csv");
    } else {
      baixarBlob(new Blob([gerarMarkdown(resultado, porNumero)], { type: "text/markdown;charset=utf-8" }), "hub_mit41.md");
    }
  }

  async function copiarParaPonte() {
    try {
      await navigator.clipboard.writeText(textoPonte);
      setCopiado(true);
      setTimeout(() => setCopiado(false), 2000);
    } catch {
      setErro("O navegador bloqueou a cópia automática -- selecione e copie o texto manualmente.");
    }
  }

  const botaoSec = "rounded-md border border-line px-3 py-1.5 text-xs text-ink transition hover:border-brand";

  return (
    <main className="min-h-screen px-6 py-12 md:px-12 lg:px-20">
      <div className="mx-auto max-w-5xl">
        <Header />
        <h1 className="mt-6 font-display text-4xl font-bold text-ink md:text-5xl">Hub MIT 41</h1>
        <p className="mt-3 max-w-2xl text-muted">
          Envie a MIT 041 (Especificação dos Processos) uma vez e tenha tudo num lugar: cada subprocesso
          como está na MIT (AS IS, TO BE, GAP), o que o movimento pede (estoque, financeiro, fiscal,
          orçamento...), o XML da biblioteca que atende e, quando não houver, a ficha de criação. Tudo por
          regras, com a frase da MIT que justifica cada conclusão.
        </p>

        <div className="mt-8 grid gap-4 md:grid-cols-2">
          <label className="flex cursor-pointer flex-col items-start gap-2 rounded-lg border border-dashed border-line bg-surface px-4 py-6 hover:border-brand">
            <span className="text-sm font-medium text-ink">PDF da MIT 41</span>
            <span className="text-sm text-muted">{arquivo ? arquivo.name : "Clique para escolher o PDF"}</span>
            <input
              type="file"
              accept=".pdf"
              className="hidden"
              onChange={(e) => {
                setArquivo(e.target.files?.[0] ?? null);
                setTexto("");
                setResultado(null);
              }}
            />
          </label>
          <div className="flex flex-col gap-2">
            <span className="text-sm font-medium text-ink">…ou cole o texto</span>
            <textarea
              value={texto}
              onChange={(e) => {
                setTexto(e.target.value);
                setArquivo(null);
                setResultado(null);
              }}
              rows={5}
              placeholder="Texto da MIT (subprocessos com TO BE) ou a saída do interpretador com [INICIO_MOVIMENTO]"
              className="w-full rounded-md border border-line bg-surface px-3 py-2 font-mono text-xs text-ink placeholder:text-muted focus:border-brand focus:outline-none"
            />
          </div>
        </div>
        <button
          onClick={analisar}
          disabled={(!arquivo && !texto.trim()) || carregando}
          className="mt-3 rounded-md bg-action px-4 py-2 text-sm font-medium text-white transition hover:bg-action-hover disabled:opacity-50"
        >
          {carregando ? "Analisando..." : "Analisar MIT"}
        </button>

        {subprocessos && subprocessos.length > 0 && (
          <div className="mt-8 flex flex-wrap items-center gap-2 border-b border-line">
            {(
              [
                ["movimentos", `Movimentos x biblioteca${resultado ? ` (${resultado.resumo.total})` : ""}`],
                ["subprocessos", `Todos os subprocessos (${subprocessos.length})`],
              ] as const
            ).map(([id, rotulo]) => (
              <button
                key={id}
                onClick={() => setAba(id)}
                disabled={id === "movimentos" && !resultado}
                className={`-mb-px rounded-t-md border px-4 py-2 text-sm disabled:opacity-40 ${
                  aba === id ? "border-line border-b-paper bg-paper font-bold text-ink" : "border-transparent text-muted hover:text-ink"
                }`}
              >
                {rotulo}
              </button>
            ))}
            {textoPonte && (
              <button
                onClick={copiarParaPonte}
                title="Texto no formato que a caixa do Buscador de XML reconhece"
                className="mb-1 ml-auto rounded-md border border-line px-3 py-1.5 text-xs text-ink transition hover:border-brand"
              >
                {copiado ? "Copiado!" : "Copiar para o Buscador de XML"}
              </button>
            )}
          </div>
        )}

        {erro && (
          <p className="mt-4 rounded-md border border-red-300 bg-red-50 px-4 py-3 text-sm text-red-700 dark:border-red-500/30 dark:bg-red-500/10 dark:text-red-300">
            {erro}
          </p>
        )}

        {resultado && aba === "movimentos" && (
          <div className="mt-6">
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              {(Object.keys(STATUS) as Status[]).map((s) => (
                <button
                  key={s}
                  onClick={() => setFiltro(filtro === s ? "todos" : s)}
                  aria-pressed={filtro === s}
                  className={`rounded-lg border bg-surface p-4 text-left transition ${
                    filtro === s ? "border-brand" : "border-line hover:border-brand"
                  }`}
                >
                  <span className={`rounded-full px-2 py-0.5 text-[11px] font-medium ${STATUS[s].classe}`}>
                    {STATUS[s].rotulo}
                  </span>
                  <p className="mt-2 font-display text-3xl font-bold text-ink">{resultado.resumo[s]}</p>
                  <p className="text-xs text-muted">{STATUS[s].descricao}</p>
                </button>
              ))}
            </div>
            <div className="mt-3 flex flex-wrap items-center gap-2">
              <p className="mr-auto text-xs text-muted">
                {resultado.resumo.total} movimentos na MIT · {resultado.resumo.xmls_na_biblioteca} XMLs comparados
                {filtro !== "todos" && ` · mostrando: ${STATUS[filtro].rotulo}`}
              </p>
              <button onClick={() => exportar("csv")} className={botaoSec}>
                Exportar planilha (CSV)
              </button>
              <button onClick={() => exportar("md")} className={botaoSec}>
                Exportar relatório (.md)
              </button>
            </div>

            <div className="mt-4 divide-y divide-line rounded-lg border border-line bg-surface">
              {visiveis.map((m) => {
                const chave = `${m.numero}-${m.titulo}`;
                const estaAberto = aberto === chave;
                const base = m.ficha?.xml_base;
                return (
                  <div key={chave} className="px-4 py-3">
                    <button
                      onClick={() => setAberto(estaAberto ? null : chave)}
                      aria-expanded={estaAberto}
                      className="flex w-full flex-wrap items-center gap-3 text-left"
                    >
                      <span className={`rounded-full px-2 py-0.5 text-[11px] font-medium ${STATUS[m.status].classe}`}>
                        {STATUS[m.status].rotulo}
                      </span>
                      <span className="font-mono text-xs text-muted">{m.numero}</span>
                      <span className="flex-1 text-sm font-medium text-ink">{m.titulo}</span>
                      {m.grupo && <span className="font-mono text-xs text-muted">grupo {m.grupo}</span>}
                      {base && (
                        <span className="max-w-xs truncate font-mono text-xs text-muted" title={base.arquivo}>
                          {base.arquivo}
                        </span>
                      )}
                      {m.confianca && <span className="text-xs text-muted">confiança {m.confianca}</span>}
                      {temGap(porNumero.get(m.numero)?.gap) && (
                        <span className="rounded-full bg-amber-100 px-2 py-0.5 text-[11px] font-medium text-amber-800 dark:bg-amber-500/15 dark:text-amber-300">
                          GAP
                        </span>
                      )}
                    </button>

                    {estaAberto && (
                      <div className="mt-3 space-y-4 text-sm">
                        {m.avisos.length > 0 && (
                          <ul className="space-y-1 rounded-md border border-amber-300 bg-amber-50 px-3 py-2 text-amber-900 dark:border-amber-500/30 dark:bg-amber-500/10 dark:text-amber-200">
                            {m.avisos.map((a) => (
                              <li key={a}>⚠ {a}</li>
                            ))}
                          </ul>
                        )}

                        <NaMit sp={porNumero.get(m.numero)} grupoAnalise={m.grupo} />

                        {m.ficha && (
                          <div className="rounded-md border border-line bg-paper p-3">
                            <h3 className="font-display text-sm font-bold text-ink">Ficha do movimento</h3>
                            <dl className="mt-2 grid gap-x-4 gap-y-1 text-xs sm:grid-cols-[auto_1fr]">
                              <dt className="text-muted">Grupo</dt>
                              <dd className="text-ink">
                                {m.ficha.grupo ?? "-"}
                                {m.origem_grupo && <span className="text-muted"> (pelo {m.origem_grupo})</span>}
                              </dd>
                              <dt className="text-muted">Código sugerido</dt>
                              <dd className="font-mono text-ink">
                                {m.ficha.codigo_sugerido ?? "-"}{" "}
                                <span className="font-sans text-muted">(próximo livre na biblioteca; use a numeração do cliente)</span>
                              </dd>
                              <dt className="text-muted">XML-base</dt>
                              <dd className="text-ink">
                                {base ? (
                                  <span className="flex flex-wrap items-center gap-2">
                                    <span className="font-mono">{base.grupo} / {base.arquivo}</span>
                                    <button
                                      onClick={() => baixarXmlBase(base)}
                                      disabled={baixando === `${base.grupo}/${base.arquivo}/${base.id ?? ""}`}
                                      className={botaoSec}
                                    >
                                      Baixar higienizado
                                    </button>
                                  </span>
                                ) : (
                                  "nenhum"
                                )}
                              </dd>
                            </dl>

                            {m.ficha.regra_desejada.length > 0 && (
                              <>
                                <p className="mt-3 text-xs font-bold text-ink">O que a MIT pede</p>
                                <ul className="mt-1 list-disc pl-5 text-xs text-ink">
                                  {m.ficha.regra_desejada.map((r) => (
                                    <li key={r}>{r}</li>
                                  ))}
                                </ul>
                              </>
                            )}

                            {m.ficha.ajustes.length > 0 && (
                              <>
                                <p className="mt-3 text-xs font-bold text-ink">Ajustes no XML-base</p>
                                <div className="mt-1 overflow-x-auto">
                                  <table className="w-full text-left text-xs">
                                    <thead className="text-muted">
                                      <tr>
                                        <th className="py-1 pr-3 font-medium">O quê</th>
                                        <th className="py-1 pr-3 font-medium">MIT pede</th>
                                        <th className="py-1 pr-3 font-medium">XML-base faz</th>
                                        <th className="py-1 pr-3 font-medium">Onde mexer</th>
                                      </tr>
                                    </thead>
                                    <tbody className="align-top text-ink">
                                      {m.ficha.ajustes.map((a) => (
                                        <tr key={a.dimensao} className="border-t border-line">
                                          <td className="py-1 pr-3">{a.rotulo}</td>
                                          <td className="py-1 pr-3">
                                            {a.mit_pede}
                                            <p className="mt-0.5 italic text-muted">“{a.trecho}”</p>
                                          </td>
                                          <td className="py-1 pr-3">{a.xml_base_faz}</td>
                                          <td className="py-1 pr-3">
                                            {a.area}
                                            <p className="font-mono text-muted">{a.propriedade}</p>
                                          </td>
                                        </tr>
                                      ))}
                                    </tbody>
                                  </table>
                                </div>
                              </>
                            )}

                            {m.ficha.pendencias.length > 0 && (
                              <>
                                <p className="mt-3 text-xs font-bold text-ink">Confirmar com o cliente</p>
                                <ul className="mt-1 list-disc pl-5 text-xs text-ink">
                                  {m.ficha.pendencias.map((p) => (
                                    <li key={p}>{p}</li>
                                  ))}
                                </ul>
                              </>
                            )}
                          </div>
                        )}

                        {m.fluxo.length > 0 && (
                          <div>
                            <p className="text-xs font-bold text-ink">Fluxo na MIT</p>
                            <ul className="mt-1 space-y-1 text-xs text-ink">
                              {m.fluxo.map((x) => (
                                <li key={x.numero}>
                                  {DIRECAO[x.direcao]} <span className="font-mono">{x.numero}</span> {x.titulo}
                                  <span className="italic text-muted"> — “{x.trecho}”</span>
                                </li>
                              ))}
                            </ul>
                          </div>
                        )}

                        <div>
                          <p className="text-xs font-bold text-ink">Evidências na MIT</p>
                          {Object.keys(m.requisitos.evidencias).length === 0 ? (
                            <p className="mt-1 text-xs text-muted">A MIT não descreve o comportamento deste movimento.</p>
                          ) : (
                            <ul className="mt-1 space-y-1 text-xs">
                              {Object.entries(m.requisitos.evidencias).map(([dim, evs]) =>
                                evs.map((e, i) => (
                                  <li key={`${dim}-${i}`} className="text-ink">
                                    <span className="font-medium">{DIMENSOES[dim] ?? dim}:</span>{" "}
                                    {VALORES[e.valor] ?? e.valor}
                                    {m.requisitos.ambiguas.includes(dim) && (
                                      <span className="text-amber-700 dark:text-amber-300"> (contraditório)</span>
                                    )}
                                    <span className="italic text-muted"> — “{e.trecho}”</span>
                                  </li>
                                ))
                              )}
                            </ul>
                          )}
                        </div>

                        {m.candidatos.length > 0 && (
                          <div>
                            <p className="text-xs font-bold text-ink">XMLs mais parecidos</p>
                            <ol className="mt-1 space-y-2 text-xs">
                              {m.candidatos.map((c) => (
                                <li key={`${c.grupo}/${c.arquivo}/${c.id ?? ""}`} className="rounded-md border border-line p-2">
                                  <p className="font-mono text-ink">
                                    {c.grupo} / {c.arquivo}
                                  </p>
                                  <p className="text-muted">
                                    pontos {c.pontos} · nome {Math.round(c.semelhanca_nome * 100)}% ·{" "}
                                    {c.divergencias.length === 0
                                      ? "sem divergências"
                                      : `diverge em: ${c.divergencias.map((d) => DIMENSOES[d] ?? d).join(", ")}`}
                                  </p>
                                  <p className="mt-1 text-ink">{c.resumo.join(" ")}</p>
                                </li>
                              ))}
                            </ol>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                );
              })}
              {visiveis.length === 0 && (
                <p className="px-4 py-6 text-center text-sm text-muted">Nenhum movimento neste filtro.</p>
              )}
            </div>
            <p className="mt-3 text-xs text-muted">
              Análise por regras, sem IA: confira cada ficha antes de parametrizar. O nome das abas da
              parametrização em &quot;Onde mexer&quot; foi deduzido dos formulários do XML; a propriedade é a exata.
            </p>
          </div>
        )}
        {subprocessos && subprocessos.length > 0 && aba === "subprocessos" && (
          <div className="mt-6">
            <p className="mb-3 text-sm text-muted">
              Todos os subprocessos da MIT, inclusive os que não são movimento. Clique numa linha para ver AS IS / TO
              BE. O status vem da análise, quando o subprocesso é um movimento.
            </p>
            <div className="overflow-x-auto rounded-lg border border-line">
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="border-b border-line bg-surface text-xs">
                    <th className="px-3 py-2 font-mono text-muted">Nº</th>
                    <th className="px-3 py-2 font-bold text-ink">Subprocesso</th>
                    <th className="px-3 py-2 font-bold text-ink">Status</th>
                    <th className="px-3 py-2 font-bold text-ink">Grupo</th>
                    <th className="px-3 py-2 font-bold text-ink">GAP</th>
                  </tr>
                </thead>
                <tbody>
                  {subprocessos.map((sp, idx) => {
                    const mov = resultado?.movimentos.find((m) => m.numero && m.numero === sp.numero);
                    const grupo = mov?.grupo ?? sp.sugestao_aproximada[0]?.grupo;
                    const estaAberto = subAberto === idx;
                    return (
                      <Fragment key={`${sp.numero}-${idx}`}>
                        <tr
                          onClick={() => setSubAberto(estaAberto ? null : idx)}
                          className="cursor-pointer border-b border-line bg-paper transition hover:bg-surface"
                        >
                          <td className="px-3 py-2 font-mono text-xs text-muted">{sp.numero}</td>
                          <td className="px-3 py-2 text-ink">{sp.titulo}</td>
                          <td className="px-3 py-2">
                            {mov ? (
                              <span className={`rounded-full px-2 py-0.5 text-[11px] font-medium ${STATUS[mov.status].classe}`}>
                                {STATUS[mov.status].rotulo}
                              </span>
                            ) : (
                              <span className="text-xs text-muted">não é movimento</span>
                            )}
                          </td>
                          <td className="px-3 py-2 font-mono text-xs text-ink">{grupo ?? <span className="text-muted">--</span>}</td>
                          <td className="px-3 py-2 text-xs text-muted">{temGap(sp.gap) ? "sim" : "--"}</td>
                        </tr>
                        {estaAberto && (
                          <tr className="border-b border-line bg-surface">
                            <td colSpan={5} className="px-3 py-3">
                              <NaMit sp={sp} grupoAnalise={mov?.grupo ?? null} />
                              {mov && (
                                <button
                                  onClick={() => {
                                    setAba("movimentos");
                                    setFiltro("todos");
                                    setAberto(`${mov.numero}-${mov.titulo}`);
                                  }}
                                  className="mt-2 rounded-md border border-line px-3 py-1.5 text-xs text-ink transition hover:border-brand"
                                >
                                  Ver ficha e XML-base deste movimento
                                </button>
                              )}
                            </td>
                          </tr>
                        )}
                      </Fragment>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </main>
  );
}

/** O subprocesso como está escrito na MIT (vem do interpretador). */
function NaMit({ sp, grupoAnalise }: { sp: SubProcesso | undefined; grupoAnalise: string | null }) {
  if (!sp) return null;
  const sugestao = sp.sugestao_aproximada[0];
  const temTexto = sp.processo_relacionado || sp.texto_as_is || sp.texto_to_be || temGap(sp.gap);
  return (
    <div className="rounded-md border border-line bg-paper p-3 text-xs">
      <h3 className="font-display text-sm font-bold text-ink">Na MIT</h3>
      {!temTexto && (
        <p className="mt-1 italic text-muted">
          Só o nome veio da tabela-índice: o PDF não tem (ou não trouxe) o detalhamento deste subprocesso.
        </p>
      )}
      {sp.processo_relacionado && (
        <p className="mt-1 text-muted">
          <span className="font-medium text-ink">Processo relacionado:</span> {sp.processo_relacionado}
        </p>
      )}
      {sp.texto_as_is && (
        <p className="mt-2 text-muted">
          <span className="font-bold text-ink">AS IS:</span> {sp.texto_as_is}
        </p>
      )}
      {sp.texto_to_be && (
        <p className="mt-2 text-muted">
          <span className="font-bold text-ink">TO BE:</span> {sp.texto_to_be}
        </p>
      )}
      {temGap(sp.gap) && (
        <p className="mt-2 text-amber-800 dark:text-amber-300">
          <span className="font-bold">GAP:</span> {sp.gap}
        </p>
      )}
      {sugestao && sugestao.grupo !== grupoAnalise && (
        <p className="mt-2 text-muted">
          <span className="font-medium text-ink">Outra leitura de grupo (pelos sinais do texto):</span>{" "}
          <span className="font-mono font-bold text-ink">{sugestao.grupo}</span> ({sugestao.pontuacao} pts) --{" "}
          {sugestao.sinais.join("; ")}
        </p>
      )}
    </div>
  );
}
