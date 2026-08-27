"use client";

import { useEffect, useState } from "react";
import { Header } from "../components/Header";

type Grupo = { codigo: string; label: string | null; descricao?: string | null };
type SugestaoGrupo = { grupo: string; pontuacao: number; sinais: string[] };

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

  const [textoMit41, setTextoMit41] = useState("");
  const [sugestoes, setSugestoes] = useState<SugestaoGrupo[] | null>(null);
  const [sugerindo, setSugerindo] = useState(false);

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

  async function sugerirGrupo() {
    if (!textoMit41.trim()) return;
    setSugerindo(true);
    setSugestoes(null);
    setErro(null);
    try {
      const resposta = await fetch("/api/xml/sugerir-grupo", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ texto: textoMit41 }),
      });
      if (!resposta.ok) throw new Error();
      const dados = await resposta.json();
      setSugestoes(dados.sugestoes);
      if (dados.sugestoes.length > 0) {
        setGrupoSelecionado(dados.sugestoes[0].grupo);
      }
    } catch {
      setErro("Não foi possível analisar o texto do MIT 41.");
    } finally {
      setSugerindo(false);
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

        {/* Ponte com o Interpretador de MIT 41 -- opcional, sugere o
            grupo com base nos campos extraídos, sem decidir sozinho */}
        <div className="mt-8 rounded-lg border border-line bg-surface p-4">
          <h2 className="font-display text-sm font-bold text-ink">
            Colar saída do Interpretador de MIT 41 (opcional)
          </h2>
          <p className="mt-1 text-xs text-muted">
            Cola aqui um trecho da resposta do Gem -- a ferramenta sugere
            o grupo de movimento com base nos campos extraídos. Você
            confirma antes de usar.
          </p>
          <textarea
            value={textoMit41}
            onChange={(e) => setTextoMit41(e.target.value)}
            rows={5}
            placeholder={"[INICIO_MOVIMENTO]\nPROCESSO_ORIGEM=...\n..."}
            className="mt-3 w-full rounded-lg border border-line bg-paper px-3 py-2 font-mono text-xs text-ink placeholder:text-muted focus:border-brand"
          />
          <button
            onClick={sugerirGrupo}
            disabled={!textoMit41.trim() || sugerindo}
            className="mt-2 rounded-md bg-action px-4 py-2 text-sm font-medium text-white transition hover:bg-action-hover disabled:opacity-50"
          >
            {sugerindo ? "Analisando..." : "Sugerir grupo"}
          </button>

          {sugestoes && sugestoes.length > 0 && (
            <div className="mt-4 space-y-2">
              {sugestoes.slice(0, 3).map((s, idx) => (
                <button
                  key={s.grupo}
                  onClick={() => setGrupoSelecionado(s.grupo)}
                  className={`block w-full rounded-md border px-3 py-2 text-left text-xs transition ${
                    idx === 0
                      ? "border-brand bg-brand/10"
                      : "border-line hover:border-brand"
                  }`}
                >
                  <span className="font-mono font-bold text-ink">
                    {s.grupo}
                  </span>
                  <span className="ml-2 text-muted">
                    ({s.pontuacao} pontos)
                  </span>
                  <ul className="mt-1 list-inside list-disc text-muted">
                    {s.sinais.map((sinal, i) => (
                      <li key={i}>{sinal}</li>
                    ))}
                  </ul>
                </button>
              ))}
            </div>
          )}
        </div>

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
