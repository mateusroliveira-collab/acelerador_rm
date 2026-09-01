"use client";

import { useState } from "react";
import { Header } from "../components/Header";

type ErroValidacao = {
  mensagem: string;
  linha: number | null;
  posicao_inicio: number | null;
  posicao_fim: number | null;
  campo: string | null;
  valor_encontrado: string | null;
  sugestao_rm: string | null;
  corrigivel_automaticamente: boolean;
  valor_corrigido: string | null;
};

type ResultadoValidacao = {
  valido: boolean;
  erros: ErroValidacao[];
};

type Correcao = {
  linha: number;
  posicao_inicio: number;
  posicao_fim: number;
  campo: string;
  valor_antigo: string;
  valor_novo: string;
};

type ResultadoCorrecao = {
  conteudo_corrigido: string;
  correcoes_aplicadas: Correcao[];
  erros_restantes: ErroValidacao[];
  total_corrigido: number;
  total_pendente: number;
};

const BANCOS = [
  { codigo: "bb", nome: "Banco do Brasil" },
  { codigo: "caixa", nome: "Caixa" },
  { codigo: "bradesco", nome: "Bradesco" },
  { codigo: "itau", nome: "Itaú" },
  { codigo: "santander", nome: "Santander" },
  { codigo: "sicoob", nome: "Sicoob" },
];

export default function ValidadorCnabPage() {
  const [tipoCnab, setTipoCnab] = useState<"240" | "400">("240");
  const [bancoCnab400, setBancoCnab400] = useState("generico");
  const [arquivo, setArquivo] = useState<File | null>(null);
  const [carregando, setCarregando] = useState(false);
  const [resultado, setResultado] = useState<ResultadoValidacao | null>(null);
  const [correcao, setCorrecao] = useState<ResultadoCorrecao | null>(null);
  const [erro, setErro] = useState<string | null>(null);

  const [banco, setBanco] = useState("bb");
  const [tabelaErro, setTabelaErro] = useState("retorno_400");
  const [codigoErro, setCodigoErro] = useState("");
  const [mensagemErro, setMensagemErro] = useState("");
  const [traducao, setTraducao] = useState<ErroValidacao | null>(null);
  const [traduzindo, setTraduzindo] = useState(false);

  function limparResultados() {
    setResultado(null);
    setCorrecao(null);
    setErro(null);
  }

  async function validar() {
    if (!arquivo) return;
    setCarregando(true);
    limparResultados();

    try {
      const formData = new FormData();
      formData.append("arquivo", arquivo);

      let rota = "/api/cnab/validar-240";
      
      if (tipoCnab === "400") {
        if (bancoCnab400 === "caixa") {
          rota = "/api/cnab/validar-400-caixa";
        } else if (bancoCnab400 === "bb") {
          rota = "/api/cnab/validar-400-bb";
        } else {
          rota = "/api/cnab/validar-400";
        }
      }

      const resposta = await fetch(rota, { method: "POST", body: formData });
      if (!resposta.ok) throw new Error();

      const dados = await resposta.json();
      setResultado(dados);
    } catch {
      setErro("Não foi possível validar o arquivo.");
    } finally {
      setCarregando(false);
    }
  }

  async function corrigir() {
    if (!arquivo) return;
    setCarregando(true);
    limparResultados();

    try {
      const formData = new FormData();
      formData.append("arquivo", arquivo);

      const resposta = await fetch("/api/cnab/corrigir-240", {
        method: "POST",
        body: formData,
      });
      if (!resposta.ok) throw new Error();

      const dados: ResultadoCorrecao = await resposta.json();
      setCorrecao(dados);
    } catch {
      setErro("Não foi possível corrigir o arquivo.");
    } finally {
      setCarregando(false);
    }
  }

  function baixarCorrigido() {
    if (!correcao) return;
    const blob = new Blob([correcao.conteudo_corrigido], {
      type: "text/plain",
    });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = arquivo
      ? arquivo.name.replace(/(\.\w+)?$/, "_CORRIGIDO$1")
      : "corrigido.txt";
    link.click();
    URL.revokeObjectURL(url);
  }

  async function traduzirErro() {
    if (!codigoErro) return;
    setTraduzindo(true);
    setTraducao(null);

    try {
      const params = new URLSearchParams({
        banco,
        codigo_erro: codigoErro,
        mensagem: mensagemErro,
      });

      if (banco === "caixa") {
        params.set("tabela", tabelaErro);
      }

      const resposta = await fetch(`/api/cnab/traduzir-erro?${params}`, {
        method: "POST",
      });

      if (!resposta.ok) throw new Error();

      const dados = await resposta.json();
      setTraducao(dados);
    } catch {
      setErro("Não foi possível traduzir o erro.");
    } finally {
      setTraduzindo(false);
    }
  }

  const errosParaMostrar = resultado?.erros ?? correcao?.erros_restantes ?? [];

  return (
    <main className="min-h-screen px-6 py-12 md:px-12 lg:px-20">
      <div className="mx-auto max-w-4xl">
        <Header />

        <h1 className="mt-6 font-display text-4xl font-bold text-ink md:text-5xl">
          Validador de CNAB
        </h1>
        <p className="mt-3 max-w-xl text-muted">
          Valide arquivos de remessa/retorno CNAB 240 e 400, com a linha e a
          posição exata de cada erro -- e uma dica de onde corrigir no RM.
        </p>

        {/* Seletor de tipo */}
        <div className="mt-10 flex gap-3">
          {(["240", "400"] as const).map((tipo) => (
            <button
              key={tipo}
              onClick={() => {
                setTipoCnab(tipo);
                limparResultados();
              }}
              className={`rounded-lg border px-4 py-3 font-mono text-sm font-bold transition ${
                tipoCnab === tipo
                  ? "border-brand bg-brand text-white"
                  : "border-line bg-surface text-ink hover:border-brand"
              }`}
            >
              CNAB {tipo}
            </button>
          ))}
        </div>

        {/* Seletor de banco -- só faz sentido pro CNAB 400 */}
        {tipoCnab === "400" && (
          <div className="mt-3">
            <label className="text-xs text-muted">
              Validação específica por banco (opcional)
            </label>
            <select
              value={bancoCnab400}
              onChange={(e) => {
                setBancoCnab400(e.target.value);
                limparResultados();
              }}
              className="mt-1 block rounded-lg border border-line bg-surface px-4 py-2 text-sm text-ink focus:border-brand"
            >
              <option value="generico">Genérico (qualquer banco)</option>
              <option value="bb">Banco do Brasil (campo a campo)</option>
              <option value="caixa">Caixa (campo a campo)</option>
            </select>
          </div>
        )}

        {/* Upload */}
        <div className="mt-6">
          <label className="flex cursor-pointer flex-col items-start gap-2 rounded-lg border border-dashed border-line bg-surface px-4 py-6 hover:border-brand">
            <span className="text-sm text-muted">
              {arquivo
                ? arquivo.name
                : "Clique para escolher o arquivo de remessa/retorno"}
            </span>
            <input
              type="file"
              className="hidden"
              onChange={(e) => {
                setArquivo(e.target.files?.[0] ?? null);
                limparResultados();
              }}
            />
          </label>
        </div>

        {/* Ações */}
        <div className="mt-4 flex gap-3">
          <button
            onClick={validar}
            disabled={!arquivo || carregando}
            className="rounded-md bg-action px-4 py-2 text-sm font-medium text-white transition hover:bg-action-hover disabled:opacity-50"
          >
            {carregando ? "Validando..." : "Validar"}
          </button>

          {tipoCnab === "240" && (
            <button
              onClick={corrigir}
              disabled={!arquivo || carregando}
              className="rounded-md border border-line px-4 py-2 text-sm font-medium text-ink transition hover:border-brand disabled:opacity-50"
            >
              {carregando ? "Corrigindo..." : "Corrigir automaticamente"}
            </button>
          )}
        </div>

        {erro && (
          <p className="mt-4 rounded-md border border-red-300 bg-red-50 px-4 py-3 text-sm text-red-700 dark:border-red-500/30 dark:bg-red-500/10 dark:text-red-300">
            {erro}
          </p>
        )}

        {/* Resultado da validação simples */}
        {resultado && (
          <div className="mt-6">
            <ResumoValidacao
              valido={resultado.valido}
              totalErros={resultado.erros.length}
            />
          </div>
        )}

        {/* Resultado da correção */}
        {correcao && (
          <div className="mt-6 space-y-4">
            <div className="flex flex-wrap items-center gap-3">
              <span className="rounded-full bg-brand px-3 py-1 text-xs font-medium text-white">
                {correcao.total_corrigido} corrigido
                {correcao.total_corrigido === 1 ? "" : "s"} automaticamente
              </span>
              <span className="rounded-full border border-line px-3 py-1 text-xs font-medium text-muted">
                {correcao.total_pendente} pendente
                {correcao.total_pendente === 1 ? "" : "s"}
              </span>

              {correcao.total_corrigido > 0 && (
                <button
                  onClick={baixarCorrigido}
                  className="rounded-md bg-action px-3 py-1.5 text-xs font-medium text-white hover:bg-action-hover"
                >
                  Baixar arquivo corrigido
                </button>
              )}
            </div>

            {correcao.correcoes_aplicadas.length > 0 && (
              <div className="rounded-lg border border-line bg-surface p-4">
                <h3 className="font-display text-sm font-bold text-ink">
                  O que foi corrigido
                </h3>
                <ul className="mt-2 space-y-1 font-mono text-xs text-muted">
                  {correcao.correcoes_aplicadas.map((c, idx) => (
                    <li key={idx}>
                      Linha {c.linha}, {c.campo}:{" "}
                      <span className="text-ink">
                        &quot;{c.valor_antigo}&quot;
                      </span>{" "}
                      →{" "}
                      <span className="text-ink">
                        &quot;{c.valor_novo}&quot;
                      </span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}

        {/* Lista de erros (compartilhada entre validação e correção) */}
        {errosParaMostrar.length > 0 && (
          <div className="mt-4 divide-y divide-line rounded-lg border border-line bg-surface">
            {errosParaMostrar.map((e, idx) => (
              <ErroItem key={idx} erro={e} />
            ))}
          </div>
        )}

        {/* Tradutor de erro de banco */}
        <div className="mt-16 border-t border-line pt-8">
          <h2 className="font-display text-2xl font-bold text-ink">
            Traduzir erro do banco
          </h2>
          <p className="mt-2 max-w-xl text-sm text-muted">
            Cole o código e a mensagem que o banco devolveu (registro online
            ou retorno) para receber uma dica de onde corrigir no RM.
          </p>

          <div className="mt-6 grid gap-3 sm:grid-cols-2">
            <select
              value={banco}
              onChange={(e) => setBanco(e.target.value)}
              className="rounded-lg border border-line bg-surface px-4 py-3 text-ink focus:border-brand"
            >
              {BANCOS.map((b) => (
                <option key={b.codigo} value={b.codigo}>
                  {b.nome}
                </option>
              ))}
            </select>
            <input
              type="text"
              value={codigoErro}
              onChange={(e) => setCodigoErro(e.target.value)}
              placeholder="Código do erro (ex: 4874915)"
              className="rounded-lg border border-line bg-surface px-4 py-3 text-ink placeholder:text-muted focus:border-brand"
            />
          </div>

          {/* A Caixa tem 3 tabelas de erro separadas */}
          {banco === "caixa" && (
            <select
              value={tabelaErro}
              onChange={(e) => setTabelaErro(e.target.value)}
              className="mt-3 w-full rounded-lg border border-line bg-surface px-4 py-3 text-sm text-ink focus:border-brand"
            >
              <option value="retorno_400">
                Rejeição no retorno (CNAB 400)
              </option>
              <option value="critica_remessa_400">
                Crítica da remessa (CNAB 400, pré-crítica)
              </option>
              <option value="entrada_240">
                Rejeição de entrada (CNAB 240)
              </option>
            </select>
          )}

          <input
            type="text"
            value={mensagemErro}
            onChange={(e) => setMensagemErro(e.target.value)}
            placeholder="Mensagem do banco (opcional, ajuda se o código não for conhecido)"
            className="mt-3 w-full rounded-lg border border-line bg-surface px-4 py-3 text-ink placeholder:text-muted focus:border-brand"
          />

          <button
            onClick={traduzirErro}
            disabled={!codigoErro || traduzindo}
            className="mt-3 rounded-md bg-action px-4 py-2 text-sm font-medium text-white transition hover:bg-action-hover disabled:opacity-50"
          >
            {traduzindo ? "Traduzindo..." : "Traduzir"}
          </button>

          {traducao && (
            <div className="mt-4 rounded-lg border border-line bg-surface p-4">
              <p className="text-sm text-ink">{traducao.mensagem}</p>
              {traducao.sugestao_rm && (
                <p className="mt-2 text-sm text-muted">
                  <span className="font-medium text-brand-light">
                    Dica:{" "}
                  </span>
                  {traducao.sugestao_rm}
                </p>
              )}
            </div>
          )}
        </div>
      </div>
    </main>
  );
}

function ResumoValidacao({
  valido,
  totalErros,
}: {
  valido: boolean;
  totalErros: number;
}) {
  if (valido) {
    return (
      <div className="rounded-lg border border-emerald-300 bg-emerald-50 px-4 py-3 text-sm text-emerald-700 dark:border-emerald-500/30 dark:bg-emerald-500/10 dark:text-emerald-300">
        Arquivo válido -- nenhum erro estrutural encontrado.
      </div>
    );
  }
  return (
    <div className="rounded-lg border border-line bg-surface px-4 py-3 text-sm text-ink">
      <span className="font-bold text-action">{totalErros}</span> erro
      {totalErros === 1 ? "" : "s"} encontrado{totalErros === 1 ? "" : "s"}.
    </div>
  );
}

function ErroItem({ erro }: { erro: ErroValidacao }) {
  return (
    <div className="px-4 py-3">
      <div className="flex flex-wrap items-center gap-2">
        {erro.linha !== null && (
          <span className="font-mono text-xs text-muted">
            Linha {erro.linha}
          </span>
        )}
        {erro.posicao_inicio !== null && (
          <span className="font-mono text-xs text-muted">
            pos. {erro.posicao_inicio}
            {erro.posicao_fim !== erro.posicao_inicio
              ? `-${erro.posicao_fim}`
              : ""}
          </span>
        )}
        {erro.corrigivel_automaticamente && (
          <span className="rounded-full bg-brand/20 px-2 py-0.5 text-[10px] font-medium text-brand-light">
            corrigível automaticamente
          </span>
        )}
      </div>
      <p className="mt-1 text-sm text-ink">{erro.mensagem}</p>
      {erro.sugestao_rm && (
        <p className="mt-1 text-sm text-muted">
          <span className="font-medium text-brand-light">Dica: </span>
          {erro.sugestao_rm}
        </p>
      )}
    </div>
  );
}