"use client";

import { useEffect, useState } from "react";
import { Header } from "../components/Header";

type Grupo = { codigo: string; label: string | null; descricao?: string | null };

export default function BuscadorXmlPage() {
  const [grupos, setGrupos] = useState<Grupo[]>([]);
  const [grupoSelecionado, setGrupoSelecionado] = useState<string | null>(
    null
  );
  const [busca, setBusca] = useState("");
  const [arquivos, setArquivos] = useState<string[]>([]);
  const [carregando, setCarregando] = useState(false);
  const [baixando, setBaixando] = useState<string | null>(null);
  const [erro, setErro] = useState<string | null>(null);

  useEffect(() => {
    fetch("/api/xml/grupos")
      .then((r) => r.json())
      .then(setGrupos)
      .catch(() =>
        setErro("Não foi possível carregar os grupos de movimento.")
      );
  }, []);

  useEffect(() => {
    if (!grupoSelecionado) {
      setArquivos([]);
      return;
    }
    setCarregando(true);
    setErro(null);
    const params = new URLSearchParams({ grupo: grupoSelecionado, busca });
    fetch(`/api/xml/buscar?${params}`)
      .then((r) => {
        if (!r.ok) throw new Error();
        return r.json();
      })
      .then((data) => setArquivos(data.arquivos))
      .catch(() =>
        setErro("Não foi possível buscar os arquivos desse grupo.")
      )
      .finally(() => setCarregando(false));
  }, [grupoSelecionado, busca]);

  async function baixarLimpo(arquivo: string) {
    if (!grupoSelecionado) return;
    setBaixando(arquivo);
    setErro(null);
    try {
      const params = new URLSearchParams({
        grupo: grupoSelecionado,
        arquivo,
      });
      const resposta = await fetch(`/api/xml/limpar?${params}`, {
        method: "POST",
      });
      if (!resposta.ok) throw new Error();
      const blob = await resposta.blob();
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = arquivo.replace(".xml", "_LIMPO.xml");
      link.click();
      URL.revokeObjectURL(url);
    } catch {
      setErro(`Não foi possível higienizar "${arquivo}".`);
    } finally {
      setBaixando(null);
    }
  }

  return (
    <main className="min-h-screen px-6 py-12 md:px-12 lg:px-20">
      <div className="mx-auto max-w-4xl">
        <Header />
        <h1 className="mt-6 font-display text-4xl font-bold text-ink md:text-5xl">
          Buscador de XML
        </h1>
        <p className="mt-3 max-w-xl text-muted">
          Selecione o tipo de movimento, encontre o template certo e gere a
          versão higienizada, pronta para parametrização.
        </p>

        {/* Seletor de grupo -- estilo fichário técnico */}
        <div className="mt-10 grid grid-cols-3 gap-3 sm:grid-cols-6">
          {grupos.map((g) => (
            <button
              key={g.codigo}
              onClick={() => setGrupoSelecionado(g.codigo)}
              title={g.descricao ?? undefined}
              className={`rounded-lg border px-3 py-4 text-left transition ${
                grupoSelecionado === g.codigo
                  ? "border-brand bg-brand text-white"
                  : "border-line bg-surface text-ink hover:border-brand"
              }`}
            >
              <span className="block font-mono text-xl font-bold tabular-nums">
                {g.codigo}
              </span>
              <span
                className={`mt-1 block text-xs ${
                  grupoSelecionado === g.codigo
                    ? "text-white/70"
                    : "text-muted"
                }`}
              >
                {g.label ?? "Sem descrição"}
              </span>
            </button>
          ))}
        </div>

        {/* Busca */}
        {grupoSelecionado && (
          <div className="mt-8">
            <label className="sr-only" htmlFor="busca">
              Buscar movimento
            </label>
            <input
              id="busca"
              type="text"
              value={busca}
              onChange={(e) => setBusca(e.target.value)}
              placeholder={`Buscar dentro do grupo ${grupoSelecionado}...`}
              className="w-full rounded-lg border border-line bg-surface px-4 py-3 text-ink placeholder:text-muted focus:border-brand"
            />
          </div>
        )}

        {erro && (
          <p className="mt-4 rounded-md border border-red-300 bg-red-50 px-4 py-3 text-sm text-red-700 dark:border-red-500/30 dark:bg-red-500/10 dark:text-red-300">
            {erro}
          </p>
        )}

        {/* Resultados */}
        <div className="mt-6 divide-y divide-line rounded-lg border border-line bg-surface">
          {!grupoSelecionado && (
            <p className="px-4 py-8 text-center text-sm text-muted">
              Escolha um tipo de movimento acima para ver os arquivos
              disponíveis.
            </p>
          )}

          {grupoSelecionado && carregando && (
            <p className="px-4 py-8 text-center text-sm text-muted">
              Buscando...
            </p>
          )}

          {grupoSelecionado && !carregando && arquivos.length === 0 && (
            <p className="px-4 py-8 text-center text-sm text-muted">
              Nenhum arquivo encontrado{busca ? ` para "${busca}"` : ""} no
              grupo {grupoSelecionado}.
            </p>
          )}

          {arquivos.map((arquivo) => (
            <div
              key={arquivo}
              className="flex items-center justify-between gap-4 px-4 py-3"
            >
              <span className="font-mono text-sm text-ink">{arquivo}</span>
              <button
                onClick={() => baixarLimpo(arquivo)}
                disabled={baixando === arquivo}
                className="shrink-0 rounded-md bg-action px-4 py-2 text-sm font-medium text-white transition hover:bg-action-hover disabled:opacity-50"
              >
                {baixando === arquivo ? "Gerando..." : "Limpar e baixar"}
              </button>
            </div>
          ))}
        </div>
      </div>
    </main>
  );
}
