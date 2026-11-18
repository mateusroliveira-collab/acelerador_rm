"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Header } from "../components/Header";
import { baixarBlob, nomeLimpo } from "../lib/download";

type Grupo = { codigo: string; label: string | null; descricao?: string | null };
type ArquivoResultado = { nome: string; personalizado: boolean; id?: number };
type ResultadoPesquisa = {
  grupo: string;
  codigo: string;
  nome: string;
  personalizado: boolean;
  id?: number;
};
type SugestaoGrupo = { grupo: string; pontuacao: number; sinais: string[] };
type MovimentoAnalisado = {
  nome_movimento: string | null;
  sugestoes: SugestaoGrupo[];
};

export default function BuscadorXmlPage() {
  const [grupos, setGrupos] = useState<Grupo[]>([]);
  const [grupoSelecionado, setGrupoSelecionado] = useState<string | null>(
    null
  );
  const [busca, setBusca] = useState("");
  const [arquivos, setArquivos] = useState<ArquivoResultado[]>([]);
  const [carregando, setCarregando] = useState(false);
  const [baixando, setBaixando] = useState<string | null>(null);
  const [excluindo, setExcluindo] = useState<number | null>(null);
  const [erro, setErro] = useState<string | null>(null);

  const [arquivoParaEnviar, setArquivoParaEnviar] = useState<File | null>(
    null
  );
  const [enviando, setEnviando] = useState(false);

  const [arquivoAvulso, setArquivoAvulso] = useState<File | null>(null);
  const [limpandoAvulso, setLimpandoAvulso] = useState(false);

  const [textoMit41, setTextoMit41] = useState("");
  const [movimentos, setMovimentos] = useState<MovimentoAnalisado[] | null>(
    null
  );
  const [sugerindo, setSugerindo] = useState(false);

  // Pesquisa global (todos os grupos)
  const [pesquisa, setPesquisa] = useState("");
  const [achados, setAchados] = useState<ResultadoPesquisa[] | null>(null);
  const [totalAchados, setTotalAchados] = useState(0);
  const [pesquisando, setPesquisando] = useState(false);
  const idPesquisaAtual = useRef(0);
  const listaRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const idPesquisa = ++idPesquisaAtual.current;
    if (!pesquisa.trim()) {
      setAchados(null);
      setPesquisando(false);
      return;
    }
    setPesquisando(true);
    const timer = setTimeout(async () => {
      try {
        const params = new URLSearchParams({ q: pesquisa });
        const resposta = await fetch(`/api/xml/pesquisar?${params}`);
        if (!resposta.ok) throw new Error();
        const dados = await resposta.json();
        if (idPesquisa === idPesquisaAtual.current) {
          setAchados(dados.resultados ?? []);
          setTotalAchados(dados.total ?? 0);
        }
      } catch {
        if (idPesquisa === idPesquisaAtual.current) {
          setAchados([]);
          setTotalAchados(0);
          setErro("Não foi possível pesquisar os movimentos.");
        }
      } finally {
        if (idPesquisa === idPesquisaAtual.current) setPesquisando(false);
      }
    }, 250);
    return () => clearTimeout(timer);
  }, [pesquisa]);

  function irParaResultado(r: ResultadoPesquisa) {
    setErro(null);
    setGrupoSelecionado(r.grupo);
    // Filtra o grupo pelo nome do arquivo (sem extensão) pra cair direto nele.
    setBusca(r.nome.replace(/\.xml$/i, ""));
    setTimeout(
      () => listaRef.current?.scrollIntoView({ behavior: "smooth", block: "start" }),
      300
    );
  }

  useEffect(() => {
    fetch("/api/xml/grupos")
      .then((r) => {
        if (!r.ok) throw new Error();
        return r.json();
      })
      .then((dados) => {
        // Resposta de erro vem como objeto ({detail}), não lista -- sem
        // essa checagem, grupos.map() derrubava a página inteira.
        if (!Array.isArray(dados)) throw new Error();
        setGrupos(dados);
      })
      .catch(() =>
        setErro("Não foi possível carregar os grupos de movimento.")
      );
  }, []);

  // Incrementado a cada busca disparada: só a resposta da busca MAIS
  // RECENTE pode atualizar a lista. Sem isso, digitando rápido, uma
  // resposta antiga chegando por último sobrescrevia o resultado certo.
  const idBuscaAtual = useRef(0);

  const buscarArquivos = useCallback(async () => {
    const idBusca = ++idBuscaAtual.current;
    if (!grupoSelecionado) {
      setArquivos([]);
      return;
    }
    setCarregando(true);
    setErro(null);
    try {
      const params = new URLSearchParams({ grupo: grupoSelecionado, busca });
      const resposta = await fetch(`/api/xml/buscar?${params}`);
      if (!resposta.ok) throw new Error();
      const dados = await resposta.json();
      if (idBusca === idBuscaAtual.current) setArquivos(dados.arquivos ?? []);
    } catch {
      if (idBusca === idBuscaAtual.current) {
        setArquivos([]);
        setErro("Não foi possível buscar os arquivos desse grupo.");
      }
    } finally {
      if (idBusca === idBuscaAtual.current) setCarregando(false);
    }
  }, [grupoSelecionado, busca]);

  useEffect(() => {
    // Pequeno atraso pra não disparar uma requisição a cada tecla.
    const timer = setTimeout(buscarArquivos, 250);
    return () => clearTimeout(timer);
  }, [buscarArquivos]);

  const chaveItem = (item: ArquivoResultado) =>
    item.personalizado ? `p-${item.id}` : `b-${item.nome}`;

  async function baixarLimpo(item: ArquivoResultado) {
    if (!grupoSelecionado) return;
    setBaixando(chaveItem(item));
    setErro(null);
    try {
      const rota = item.personalizado
        ? `/api/xml/baixar-personalizado/${item.id}`
        : `/api/xml/limpar?${new URLSearchParams({ grupo: grupoSelecionado, arquivo: item.nome })}`;
      const resposta = await fetch(rota, {
        method: item.personalizado ? "GET" : "POST",
      });
      if (!resposta.ok) throw new Error();
      const blob = await resposta.blob();
      baixarBlob(blob, nomeLimpo(item.nome));
    } catch {
      setErro(`Não foi possível higienizar "${item.nome}".`);
    } finally {
      setBaixando(null);
    }
  }

  async function excluirPersonalizado(item: ArquivoResultado) {
    if (!item.personalizado || item.id === undefined) return;
    const ok = window.confirm(
      `Excluir "${item.nome}"?

Ele some das buscas de todo mundo. (A exclusão é registrada e pode ser desfeita por quem administra o banco.)`
    );
    if (!ok) return;
    setExcluindo(item.id);
    setErro(null);
    try {
      const resposta = await fetch(`/api/xml/personalizado/${item.id}`, {
        method: "DELETE",
      });
      if (!resposta.ok) throw new Error();
      await buscarArquivos();
      // Se a pesquisa global estiver aberta, tira o item excluído de lá também.
      setAchados((a) =>
        a ? a.filter((r) => !(r.personalizado && r.id === item.id)) : a
      );
    } catch {
      setErro(`Não foi possível excluir "${item.nome}".`);
    } finally {
      setExcluindo(null);
    }
  }

  async function limparXmlAvulso() {
    if (!arquivoAvulso) return;
    setLimpandoAvulso(true);
    setErro(null);
    try {
      const formData = new FormData();
      formData.append("arquivo", arquivoAvulso);
      const resposta = await fetch("/api/xml/limpar-avulso", {
        method: "POST",
        body: formData,
      });
      if (!resposta.ok) {
        const dados = await resposta.json().catch(() => null);
        throw new Error(dados?.detail || "Não foi possível limpar esse arquivo.");
      }
      const blob = await resposta.blob();
      baixarBlob(blob, nomeLimpo(arquivoAvulso.name));
      setArquivoAvulso(null);
    } catch (e) {
      setErro(e instanceof Error && e.message ? e.message : "Não foi possível limpar esse arquivo.");
    } finally {
      setLimpandoAvulso(false);
    }
  }

  async function enviarXmlPersonalizado() {
    if (!arquivoParaEnviar || !grupoSelecionado) return;
    setEnviando(true);
    setErro(null);
    try {
      const formData = new FormData();
      formData.append("arquivo", arquivoParaEnviar);
      const params = new URLSearchParams({ grupo: grupoSelecionado });
      const resposta = await fetch(`/api/xml/enviar?${params}`, {
        method: "POST",
        body: formData,
      });
      if (!resposta.ok) {
        const dados = await resposta.json().catch(() => null);
        throw new Error(dados?.detail || "Erro ao enviar o arquivo.");
      }
      setArquivoParaEnviar(null);
      await buscarArquivos();
    } catch (e) {
      setErro(
        e instanceof Error ? e.message : "Não foi possível enviar o XML."
      );
    } finally {
      setEnviando(false);
    }
  }

  async function sugerirGrupo() {
    if (!textoMit41.trim()) return;
    setSugerindo(true);
    setMovimentos(null);
    setErro(null);
    try {
      const resposta = await fetch("/api/xml/sugerir-grupo", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ texto: textoMit41 }),
      });
      if (!resposta.ok) {
        const dadosErro = await resposta.json().catch(() => null);
        throw new Error(dadosErro?.detail || "Não foi possível analisar o texto do MIT 41.");
      }
      const dados = await resposta.json();
      setMovimentos(dados.movimentos);
      // Se colou só 1 movimento e ele tem uma sugestão clara, já
      // seleciona sozinho -- com vários movimentos, deixa o analista
      // escolher qual quer buscar agora.
      if (
        dados.movimentos.length === 1 &&
        dados.movimentos[0].sugestoes.length > 0
      ) {
        setGrupoSelecionado(dados.movimentos[0].sugestoes[0].grupo);
        setBusca(dados.movimentos[0].nome_movimento ?? "");
      }
    } catch (e) {
      // O backend devolve 400 com explicação quando não reconhece nenhum
      // campo -- antes essa mensagem era descartada.
      setErro(
        e instanceof Error && e.message ? e.message : "Não foi possível analisar o texto do MIT 41."
      );
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
          versão limpa pronta para parametrização.
        </p>

        {/* Limpeza avulsa -- pra qualquer XML de qualquer projeto, sem
            salvar em lugar nenhum. Não depende de escolher um grupo. */}
        <div className="mt-8 rounded-lg border border-line bg-surface p-4">
          <h2 className="font-display text-sm font-bold text-ink">
            Só quer limpar um XML seu? (não salva em lugar nenhum)
          </h2>
          <p className="mt-1 text-xs text-muted">
            Para usar em um outro projeto, sem virar parte da base
            compartilhada -- submeta, baixe limpo, pronto.
          </p>
          <div className="mt-3 flex flex-wrap items-center gap-3">
            <label className="flex-1 cursor-pointer text-sm text-muted">
              {arquivoAvulso
                ? arquivoAvulso.name
                : "Clique aqui para escolher um arquivo XML"}
              <input
                type="file"
                accept=".xml"
                className="hidden"
                onChange={(e) =>
                  setArquivoAvulso(e.target.files?.[0] ?? null)
                }
              />
            </label>
            {arquivoAvulso && (
              <button
                onClick={limparXmlAvulso}
                disabled={limpandoAvulso}
                className="shrink-0 rounded-md bg-action px-4 py-2 text-sm font-medium text-white transition hover:bg-action-hover disabled:opacity-50"
              >
                {limpandoAvulso ? "Limpando..." : "Limpar e baixar"}
              </button>
            )}
          </div>
        </div>

        {/* Ponte com o Interpretador de MIT 41 -- opcional, sugere o
            grupo com base nos campos extraídos, sem decidir sozinho */}
        <div className="mt-8 rounded-lg border border-line bg-surface p-4">
          <h2 className="font-display text-sm font-bold text-ink">
            Colar saída do Interpretador de MIT 41 (opcional)
          </h2>
          <p className="mt-1 text-xs text-muted">
            Cola aqui um trecho da resposta do Interpretador -- a ferramenta sugere
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

          {movimentos && movimentos.length > 0 && (
            <div className="mt-4 space-y-2">
              <p className="text-xs text-muted">
                {movimentos.length === 1
                  ? "1 movimento encontrado:"
                  : `${movimentos.length} movimentos encontrados -- clique no grupo certo pra cada um:`}
              </p>
              {movimentos.map((mov, idxMov) => (
                <div
                  key={idxMov}
                  className="rounded-md border border-line px-3 py-2"
                >
                  <p className="text-xs font-bold text-ink">
                    {mov.nome_movimento ?? `Movimento ${idxMov + 1}`}
                  </p>
                  {mov.sugestoes.length === 0 && (
                    <p className="mt-1 text-xs italic text-muted">
                      Sem sinal suficiente pra sugerir um grupo -- escolha
                      manualmente abaixo.
                    </p>
                  )}
                  {mov.sugestoes.slice(0, 2).map((s) => (
                    <button
                      key={s.grupo}
                      onClick={() => {
                        setGrupoSelecionado(s.grupo);
                        // Já filtra a lista abaixo pelo nome do movimento,
                        // pra cair direto nos arquivos que interessam.
                        setBusca(mov.nome_movimento ?? "");
                      }}
                      className="mt-1 block w-full rounded border border-line px-2 py-1 text-left text-xs transition hover:border-brand"
                    >
                      <span className="font-mono font-bold text-ink">
                        {s.grupo}
                      </span>
                      <span className="ml-2 text-muted">
                        ({s.pontuacao} pts) -- {s.sinais.join("; ")}
                      </span>
                    </button>
                  ))}
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Pesquisa global: acha o movimento em qualquer grupo, por código
            (1.1.01 ou 1101) ou descrição, ignorando acentos e maiúsculas. */}
        <div className="mt-10">
          <div className="flex gap-2">
            <div className="flex-1">
              <label className="sr-only" htmlFor="pesquisa-global">
                Pesquisar movimento em todos os grupos
              </label>
              <input
                id="pesquisa-global"
                type="text"
                value={pesquisa}
                onChange={(e) => setPesquisa(e.target.value)}
                placeholder="Pesquisar em todos os grupos: código (ex.: 1.1.01) ou descrição..."
                className="w-full rounded-lg border border-line bg-surface px-4 py-3 text-ink placeholder:text-muted focus:border-brand"
              />
            </div>
            {pesquisa && (
              <button
                onClick={() => setPesquisa("")}
                className="shrink-0 rounded-lg border border-line bg-surface px-4 py-3 text-sm text-muted transition hover:border-brand hover:text-ink"
              >
                Limpar
              </button>
            )}
          </div>

          {achados !== null && (
            <div className="mt-2 divide-y divide-line rounded-lg border border-line bg-surface">
              {pesquisando && achados.length === 0 && (
                <p className="px-4 py-4 text-center text-sm text-muted">Pesquisando...</p>
              )}
              {!pesquisando && achados.length === 0 && (
                <p className="px-4 py-4 text-center text-sm text-muted">
                  Nenhum movimento encontrado para &quot;{pesquisa}&quot;.
                </p>
              )}
              {achados.map((r) => (
                <button
                  key={r.personalizado ? `p-${r.id}` : `b-${r.grupo}-${r.nome}`}
                  onClick={() => irParaResultado(r)}
                  className="flex w-full items-center gap-3 px-4 py-2 text-left transition hover:bg-paper"
                >
                  <span className="shrink-0 rounded bg-brand/20 px-2 py-0.5 font-mono text-xs font-bold text-brand-light">
                    {r.grupo}
                  </span>
                  <span className="font-mono text-sm text-ink">{r.nome}</span>
                  {r.personalizado && (
                    <span className="rounded-full bg-brand/20 px-2 py-0.5 text-[10px] font-medium text-brand-light">
                      contribuído
                    </span>
                  )}
                </button>
              ))}
              {totalAchados > achados.length && (
                <p className="px-4 py-2 text-xs text-muted">
                  Mostrando {achados.length} de {totalAchados} -- refine a pesquisa.
                </p>
              )}
            </div>
          )}
        </div>

        {/* Seletor de grupo -- estilo fichário técnico */}
        <div className="mt-4 grid grid-cols-3 gap-3 sm:grid-cols-6">
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
          <div className="mt-8 flex gap-2">
            <div className="flex-1">
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
            {busca && (
              <button
                onClick={() => setBusca("")}
                className="shrink-0 rounded-lg border border-line bg-surface px-4 py-3 text-sm text-muted transition hover:border-brand hover:text-ink"
              >
                Limpar filtro
              </button>
            )}
          </div>
        )}

        {/* Upload de XML fora da base padrão -- fica salvo pra sempre no
            banco (não na pasta, que não persiste em produção), e passa
            a aparecer na busca de QUALQUER PESSOA junto com os demais.
            Ação separada e deliberada, diferente da limpeza avulsa. */}
        {grupoSelecionado && (
          <div className="mt-4 flex flex-wrap items-center gap-3 rounded-lg border border-dashed border-line bg-surface px-4 py-3">
            <label className="flex-1 cursor-pointer text-sm text-muted">
              {arquivoParaEnviar
                ? arquivoParaEnviar.name
                : `Ou contribua um XML de referência pro grupo ${grupoSelecionado} -- fica salvo e visível pra todo mundo que buscar aqui depois.`}
              <input
                type="file"
                accept=".xml"
                className="hidden"
                onChange={(e) =>
                  setArquivoParaEnviar(e.target.files?.[0] ?? null)
                }
              />
            </label>
            {arquivoParaEnviar && (
              <button
                onClick={enviarXmlPersonalizado}
                disabled={enviando}
                className="shrink-0 rounded-md bg-action px-4 py-2 text-sm font-medium text-white transition hover:bg-action-hover disabled:opacity-50"
              >
                {enviando ? "Enviando..." : "Contribuir"}
              </button>
            )}
          </div>
        )}

        {erro && (
          <p className="mt-4 rounded-md border border-red-300 bg-red-50 px-4 py-3 text-sm text-red-700 dark:border-red-500/30 dark:bg-red-500/10 dark:text-red-300">
            {erro}
          </p>
        )}

        {/* Resultados */}
        <div ref={listaRef} className="mt-6 divide-y divide-line rounded-lg border border-line bg-surface">
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

          {arquivos.map((item) => (
            <div
              key={chaveItem(item)}
              className="flex items-center justify-between gap-4 px-4 py-3"
            >
              <span className="flex items-center gap-2">
                <span className="font-mono text-sm text-ink">
                  {item.nome}
                </span>
                {item.personalizado && (
                  <span className="rounded-full bg-brand/20 px-2 py-0.5 text-[10px] font-medium text-brand-light">
                    contribuído
                  </span>
                )}
              </span>
              <span className="flex shrink-0 items-center gap-2">
                {item.personalizado && (
                  <button
                    onClick={() => excluirPersonalizado(item)}
                    disabled={excluindo === item.id}
                    className="rounded-md border border-red-300 px-3 py-2 text-sm text-red-700 transition hover:bg-red-50 disabled:opacity-50 dark:border-red-500/30 dark:text-red-300 dark:hover:bg-red-500/10"
                  >
                    {excluindo === item.id ? "Excluindo..." : "Excluir"}
                  </button>
                )}
                <button
                  onClick={() => baixarLimpo(item)}
                  disabled={baixando === chaveItem(item)}
                  className="rounded-md bg-action px-4 py-2 text-sm font-medium text-white transition hover:bg-action-hover disabled:opacity-50"
                >
                  {baixando === chaveItem(item) ? "Gerando..." : "Limpar e baixar"}
                </button>
              </span>
            </div>
          ))}
        </div>
      </div>
    </main>
  );
}
