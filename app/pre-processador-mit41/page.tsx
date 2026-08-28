"use client";

import { useState } from "react";
import { Header } from "../components/Header";

type SubProcesso = {
  numero: string;
  titulo: string;
  processo_relacionado: string | null;
  texto_as_is: string | null;
  texto_to_be: string | null;
  gap: string | null;
  campos_que_precisam_de_ia: string[];
};

export default function PreProcessadorMit41Page() {
  const [texto, setTexto] = useState("");
  const [subprocessos, setSubprocessos] = useState<SubProcesso[] | null>(
    null
  );
  const [carregando, setCarregando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);

  async function processar() {
    if (!texto.trim()) return;
    setCarregando(true);
    setErro(null);
    setSubprocessos(null);
    try {
      const resposta = await fetch("/api/xml/pre-processar-mit41", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ texto }),
      });
      if (!resposta.ok) throw new Error();
      const dados = await resposta.json();
      setSubprocessos(dados.subprocessos);
    } catch {
      setErro("Não foi possível processar o documento.");
    } finally {
      setCarregando(false);
    }
  }

  return (
    <main className="min-h-screen px-6 py-12 md:px-12 lg:px-20">
      <div className="mx-auto max-w-4xl">
        <Header />
        <h1 className="mt-6 font-display text-4xl font-bold text-ink md:text-5xl">
          Pré-processador de MIT 41
        </h1>
        <p className="mt-3 max-w-2xl text-muted">
          Organiza o documento MIT 41 <strong>bruto</strong> (colado do
          Word/PDF, antes de qualquer IA) em uma lista de subprocessos --
          via regra pura, sem inteligência artificial. Mostra exatamente
          até onde isso resolve sozinho, e onde a interpretação de
          negócio (efeito em estoque, financeiro, fiscal) precisaria de
          um passo a mais.
        </p>

        <div className="mt-8">
          <textarea
            value={texto}
            onChange={(e) => setTexto(e.target.value)}
            rows={10}
            placeholder="Cole aqui o texto bruto do MIT 41 -- pode incluir a tabela-índice (ex: '4.1.1.1 Cadastro de Produtos Processos relacionados...') e/ou o detalhamento de cada subprocesso (Processo Relacionado, AS IS, TO BE, GAP)."
            className="w-full rounded-lg border border-line bg-surface px-4 py-3 font-mono text-xs text-ink placeholder:text-muted focus:border-brand"
          />
          <button
            onClick={processar}
            disabled={!texto.trim() || carregando}
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
          <div className="mt-8 space-y-4">
            <p className="text-sm text-muted">
              {subprocessos.length} subprocesso
              {subprocessos.length === 1 ? "" : "s"} identificado
              {subprocessos.length === 1 ? "" : "s"} -- lista organizada a
              partir da tabela-índice do documento.
            </p>

            {subprocessos.map((sp, idx) => (
              <div
                key={idx}
                className="rounded-lg border border-line bg-surface p-4"
              >
                <div className="flex items-baseline gap-3">
                  <span className="font-mono text-sm font-bold text-brand-light">
                    {sp.numero}
                  </span>
                  <span className="font-display text-lg font-bold text-ink">
                    {sp.titulo}
                  </span>
                </div>

                {!sp.processo_relacionado && !sp.texto_to_be && (
                  <p className="mt-2 text-xs italic text-muted">
                    Só o nome veio da tabela-índice -- cole também o
                    detalhamento desse subprocesso (a seção com "Processo
                    Relacionado", "AS IS", "TO BE") pra ver o resto.
                  </p>
                )}

                {sp.processo_relacionado && (
                  <p className="mt-2 text-xs text-muted">
                    <span className="font-medium text-ink">
                      Processo Relacionado:
                    </span>{" "}
                    {sp.processo_relacionado}
                  </p>
                )}

                {sp.texto_as_is && (
                  <div className="mt-3">
                    <p className="text-xs font-bold text-ink">AS IS</p>
                    <p className="mt-1 text-sm text-muted">
                      {sp.texto_as_is}
                    </p>
                  </div>
                )}

                {sp.texto_to_be && (
                  <div className="mt-3">
                    <p className="text-xs font-bold text-ink">TO BE</p>
                    <p className="mt-1 text-sm text-muted">
                      {sp.texto_to_be}
                    </p>
                  </div>
                )}

                {sp.gap && (
                  <div className="mt-3">
                    <p className="text-xs font-bold text-ink">GAP</p>
                    <p className="mt-1 text-sm text-muted">{sp.gap}</p>
                  </div>
                )}

                {sp.campos_que_precisam_de_ia.length > 0 && (
                  <div className="mt-4 rounded-md border border-dashed border-action/50 bg-action/10 px-3 py-2">
                    <p className="text-xs font-bold text-action">
                      Precisa de interpretação (IA) pra virar campo
                      estruturado:
                    </p>
                    <p className="mt-1 font-mono text-xs text-muted">
                      {sp.campos_que_precisam_de_ia.join(", ")}
                    </p>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </main>
  );
}
