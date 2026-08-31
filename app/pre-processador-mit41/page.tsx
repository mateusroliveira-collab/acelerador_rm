"use client";

import { useState } from "react";
import { Header } from "../components/Header";

type SugestaoGrupo = { grupo: string; pontuacao: number; sinais: string[] };

type SubProcesso = {
  numero: string;
  titulo: string;
  processo_relacionado: string | null;
  texto_as_is: string | null;
  texto_to_be: string | null;
  gap: string | null;
  campos_que_precisam_de_ia: string[];
  sugestao_aproximada: SugestaoGrupo[];
};

export default function PreProcessadorMit41Page() {
  const [arquivo, setArquivo] = useState<File | null>(null);
  const [subprocessos, setSubprocessos] = useState<SubProcesso[] | null>(
    null
  );
  const [textoParaPonte, setTextoParaPonte] = useState<string | null>(null);
  const [copiado, setCopiado] = useState(false);
  const [linhaAberta, setLinhaAberta] = useState<number | null>(null);
  const [carregando, setCarregando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);

  async function processar() {
    if (!arquivo) return;
    setCarregando(true);
    setErro(null);
    setSubprocessos(null);
    try {
      const formData = new FormData();
      formData.append("arquivo", arquivo);
      const resposta = await fetch("/api/xml/pre-processar-mit41", {
        method: "POST",
        body: formData,
      });
      if (!resposta.ok) {
        const dados = await resposta.json().catch(() => null);
        throw new Error(dados?.detail || "Erro ao processar o arquivo.");
      }
      const dados = await resposta.json();
      setSubprocessos(dados.subprocessos);
      setTextoParaPonte(dados.texto_para_ponte);
    } catch (e) {
      setErro(
        e instanceof Error ? e.message : "Não foi possível processar o arquivo."
      );
    } finally {
      setCarregando(false);
    }
  }

  return (
    <main className="min-h-screen px-6 py-12 md:px-12 lg:px-20">
      <div className="mx-auto max-w-5xl">
        <Header />
        <h1 className="mt-6 font-display text-4xl font-bold text-ink md:text-5xl">
          Interpretador de MIT 41
        </h1>
        <p className="mt-3 max-w-2xl text-muted">
          Submeta o PDF <strong>bruto</strong> do MIT 41 e organiza os subprocessos numa tabela -- via regra pura.
          Cada linha já vem com uma sugestão aproximada de grupo de XML,
          e mostra onde está a interpretação de negócio.
        </p>

        <div className="mt-8">
          <label className="flex cursor-pointer flex-col items-start gap-2 rounded-lg border border-dashed border-line bg-surface px-4 py-6 hover:border-brand">
            <span className="text-sm text-muted">
              {arquivo ? arquivo.name : "Clique para escolher o PDF do MIT 41"}
            </span>
            <input
              type="file"
              accept=".pdf"
              className="hidden"
              onChange={(e) => {
                setArquivo(e.target.files?.[0] ?? null);
                setSubprocessos(null);
                setErro(null);
              }}
            />
          </label>
          <button
            onClick={processar}
            disabled={!arquivo || carregando}
            className="mt-3 rounded-md bg-action px-4 py-2 text-sm font-medium text-white transition hover:bg-action-hover disabled:opacity-50"
          >
            {carregando ? "Processando..." : "Processar"}
          </button>
        </div>

        {erro && (
          <p className="mt-4 rounded-md border border-red-300 bg-red-50 px-4 py-3 text-sm text-red-700 dark:border-red-500/30 dark:bg-red-500/10 dark:text-red-300">
            {erro}
          </p>
        )}

        {subprocessos && subprocessos.length > 0 && (
          <div className="mt-8">
            <div className="mb-4 flex flex-wrap items-center gap-3 rounded-lg border border-line bg-surface p-4">
              <div className="flex-1">
                <p className="text-sm font-bold text-ink">
                  Continuar no Buscador de XML
                </p>
                <p className="mt-1 text-xs text-muted">
                  Copia esse texto e cola na caixa "Colar saída do
                  Interpretador de MIT 41" do Buscador de XML -- já vem
                  no formato que ela reconhece (não é a tabela visual,
                  que não daria certo colar direto).
                </p>
              </div>
              <button
                onClick={() => {
                  if (textoParaPonte) {
                    navigator.clipboard.writeText(textoParaPonte);
                    setCopiado(true);
                    setTimeout(() => setCopiado(false), 2000);
                  }
                }}
                className="shrink-0 rounded-md bg-action px-4 py-2 text-sm font-medium text-white transition hover:bg-action-hover"
              >
                {copiado ? "Copiado!" : "Copiar pra ponte"}
              </button>
            </div>

            <p className="mb-3 text-sm text-muted">
              {subprocessos.length} subprocesso
              {subprocessos.length === 1 ? "" : "s"} encontrado
              {subprocessos.length === 1 ? "" : "s"} -- clique numa linha
              pra ver o detalhamento (AS IS / TO BE).
            </p>

            <div className="overflow-x-auto rounded-lg border border-line">
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="border-b border-line bg-surface">
                    <th className="px-3 py-2 font-mono text-xs text-muted">
                      Nº
                    </th>
                    <th className="px-3 py-2 text-xs font-bold text-ink">
                      Movimento
                    </th>
                    <th className="px-3 py-2 text-xs font-bold text-ink">
                      Sugestão de grupo
                    </th>
                    <th className="px-3 py-2 text-xs font-bold text-ink">
                      GAP
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {subprocessos.map((sp, idx) => {
                    const topSugestao = sp.sugestao_aproximada[0];
                    const aberta = linhaAberta === idx;
                    return (
                      <>
                        <tr
                          key={idx}
                          onClick={() =>
                            setLinhaAberta(aberta ? null : idx)
                          }
                          className="cursor-pointer border-b border-line bg-paper transition hover:bg-surface"
                        >
                          <td className="px-3 py-2 font-mono text-xs text-muted">
                            {sp.numero}
                          </td>
                          <td className="px-3 py-2 text-ink">{sp.titulo}</td>
                          <td className="px-3 py-2">
                            {topSugestao ? (
                              <span className="font-mono text-xs font-bold text-brand-light">
                                {topSugestao.grupo}
                              </span>
                            ) : (
                              <span className="text-xs italic text-muted">
                                sem sinal
                              </span>
                            )}
                          </td>
                          <td className="px-3 py-2 text-xs text-muted">
                            {sp.gap ? "sim" : "--"}
                          </td>
                        </tr>
                        {aberta && (
                          <tr className="border-b border-line bg-surface">
                            <td colSpan={4} className="px-3 py-3">
                              {sp.processo_relacionado && (
                                <p className="text-xs text-muted">
                                  <span className="font-medium text-ink">
                                    Processo Relacionado:
                                  </span>{" "}
                                  {sp.processo_relacionado}
                                </p>
                              )}
                              {sp.texto_as_is && (
                                <p className="mt-2 text-xs text-muted">
                                  <span className="font-bold text-ink">
                                    AS IS:
                                  </span>{" "}
                                  {sp.texto_as_is}
                                </p>
                              )}
                              {sp.texto_to_be && (
                                <p className="mt-2 text-xs text-muted">
                                  <span className="font-bold text-ink">
                                    TO BE:
                                  </span>{" "}
                                  {sp.texto_to_be}
                                </p>
                              )}
                              {!sp.processo_relacionado && !sp.texto_to_be && (
                                <p className="text-xs italic text-muted">
                                  Só o nome veio da tabela-índice -- o PDF
                                  não tem (ou não trouxe) o detalhamento
                                  desse subprocesso.
                                </p>
                              )}
                              {sp.campos_que_precisam_de_ia.length > 0 && (
                                <div className="mt-3 rounded-md border border-dashed border-action/50 bg-action/10 px-3 py-2">
                                  <p className="text-xs font-bold text-action">
                                    Precisa de interpretação (IA) pra virar
                                    campo estruturado:
                                  </p>
                                  <p className="mt-1 font-mono text-xs text-muted">
                                    {sp.campos_que_precisam_de_ia.join(", ")}
                                  </p>
                                </div>
                              )}
                              {sp.sugestao_aproximada.length > 0 && (
                                <div className="mt-3">
                                  <p className="text-xs font-bold text-ink">
                                    Sinais da sugestão (aproximada, sem
                                    interpretação completa):
                                  </p>
                                  <ul className="mt-1 list-inside list-disc text-xs text-muted">
                                    {sp.sugestao_aproximada
                                      .slice(0, 2)
                                      .map((s) => (
                                        <li key={s.grupo}>
                                          <span className="font-mono font-bold text-ink">
                                            {s.grupo}
                                          </span>{" "}
                                          ({s.pontuacao} pts) --{" "}
                                          {s.sinais.join("; ")}
                                        </li>
                                      ))}
                                  </ul>
                                </div>
                              )}
                            </td>
                          </tr>
                        )}
                      </>
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
