"use client";

import { useState } from "react";
import { Header } from "../components/Header";

type ErroValidacao = {
  mensagem: string;
  linha?: number | null;
  posicao_inicio?: number | null;
  posicao_fim?: number | null;
  campo: string | null;
  valor_encontrado: string | null;
  sugestao_rm: string | null;
  corrigivel_automaticamente?: boolean;
  valor_corrigido?: string | null;
};

type ResultadoValidacao = {
  valido: boolean;
  erros: ErroValidacao[];
  avisos?: string[];
};

type Correcao = {
  conteudo_corrigido: string;
  correcoes_aplicadas: unknown[];
  erros_restantes: ErroValidacao[];
  total_corrigido: number;
  total_pendente: number;
};

export default function ValidadorCnabPage() {
  const [tipoValidacao, setTipoValidacao] = useState<"240" | "400" | "registro_online">("registro_online");
  const [bancoCnab240, setBancoCnab240] = useState("caixa");
  const [bancoCnab400, setBancoCnab400] = useState("caixa");
  const [bancoRegistroOnline, setBancoRegistroOnline] = useState("caixa");
  const [arquivo, setArquivo] = useState<File | null>(null);
  const [xmlPayload, setXmlPayload] = useState("");
  const [carregando, setCarregando] = useState(false);
  const [resultado, setResultado] = useState<ResultadoValidacao | null>(null);
  const [correcao, setCorrecao] = useState<Correcao | null>(null);
  const [erro, setErro] = useState<string | null>(null);

  function limparResultados() {
    setResultado(null);
    setCorrecao(null);
    setErro(null);
  }

  async function validar() {
    setCarregando(true);
    limparResultados();
    try {
      let resposta;
      if (tipoValidacao === "registro_online") {
        if (!xmlPayload.trim()) {
          setErro("Cole o XML de requisição do log do RM para o Registro Online.");
          setCarregando(false);
          return;
        }
        const rotaXml =
          bancoRegistroOnline === "caixa"
            ? "/api/cnab/validar-xml-caixa"
            : "/api/cnab/validar-xml-bb";
        resposta = await fetch(rotaXml, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ xml: xmlPayload }),
        });
      } else {
        if (!arquivo) {
          setCarregando(false);
          return;
        }
        const formData = new FormData();
        formData.append("arquivo", arquivo);

        let rota = "/api/cnab/validar-240";
        if (tipoValidacao === "240") {
          if (bancoCnab240 === "caixa") rota = "/api/cnab/validar-240-caixa";
          else if (bancoCnab240 === "bb") rota = "/api/cnab/validar-240-bb";
          else rota = "/api/cnab/validar-240";
        } else if (tipoValidacao === "400") {
          if (bancoCnab400 === "caixa") rota = "/api/cnab/validar-400-caixa";
          else if (bancoCnab400 === "bb") rota = "/api/cnab/validar-400-bb";
          else rota = "/api/cnab/validar-400";
        }
        resposta = await fetch(rota, { method: "POST", body: formData });
      }

      const dados = await resposta.json();
      if (!resposta.ok) {
        setErro(dados?.detail || "Não foi possível processar a validação.");
        setCarregando(false);
        return;
      }
      setResultado(dados);
    } catch {
      setErro("Não foi possível processar a validação. O arquivo/XML pode estar mal formatado.");
    } finally {
      setCarregando(false);
    }
  }

  async function corrigir() {
    if (!arquivo || tipoValidacao !== "240") return;
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
      const dados: Correcao = await resposta.json();
      setCorrecao(dados);
    } catch {
      setErro("Não foi possível corrigir o arquivo.");
    } finally {
      setCarregando(false);
    }
  }

  function baixarCorrigido() {
    if (!correcao) return;
    const blob = new Blob([correcao.conteudo_corrigido], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = arquivo ? arquivo.name.replace(/(\.\w+)?$/, "_CORRIGIDO$1") : "corrigido.txt";
    link.click();
    URL.revokeObjectURL(url);
  }

  const errosParaMostrar = resultado?.erros ?? correcao?.erros_restantes ?? [];
  const avisosParaMostrar = resultado?.avisos ?? [];

  return (
    <main className="min-h-screen px-6 py-12 md:px-12 lg:px-20">
      <div className="mx-auto max-w-4xl">
        <Header />
        <h1 className="mt-6 font-display text-4xl font-bold text-ink md:text-5xl">
          Validador de CNAB e Registro Online
        </h1>
        <p className="mt-3 max-w-xl text-muted">
          Diagnóstico cirúrgico para arquivos de remessa/retorno (240 e 400) e Registro Online via API.
        </p>

        {/* Seletor de Tipo */}
        <div className="mt-10 flex flex-wrap gap-3">
          {(["registro_online", "240", "400"] as const).map((tipo) => (
            <button
              key={tipo}
              onClick={() => {
                setTipoValidacao(tipo);
                limparResultados();
              }}
              className={`rounded-lg border px-4 py-3 font-mono text-sm font-bold transition ${
                tipoValidacao === tipo
                  ? "border-brand bg-brand text-white"
                  : "border-line bg-surface text-ink hover:border-brand"
              }`}
            >
              {tipo === "registro_online"
                ? "Registro Online (XML)"
                : `CNAB ${tipo}`}
            </button>
          ))}
        </div>

        {/* Seletor do Banco - CNAB 240 */}
        {tipoValidacao === "240" && (
          <div className="mt-4">
            <label className="text-xs text-muted font-medium">Banco Específico (CNAB 240)</label>
            <select
              value={bancoCnab240}
              onChange={(e) => {
                setBancoCnab240(e.target.value);
                limparResultados();
              }}
              className="mt-1 block rounded-lg border border-line bg-surface px-4 py-2 text-sm text-ink focus:border-brand"
            >
              <option value="caixa">Caixa Econômica (Regras + Dicas RM)</option>
              <option value="bb">Banco do Brasil (Regras + Dicas RM)</option>
              <option value="generico">Genérico (Apenas Estrutura FEBRABAN)</option>
            </select>
          </div>
        )}

        {/* Seletor do Banco - CNAB 400 */}
        {tipoValidacao === "400" && (
          <div className="mt-4">
            <label className="text-xs text-muted font-medium">Banco Específico (CNAB 400)</label>
            <select
              value={bancoCnab400}
              onChange={(e) => {
                setBancoCnab400(e.target.value);
                limparResultados();
              }}
              className="mt-1 block rounded-lg border border-line bg-surface px-4 py-2 text-sm text-ink focus:border-brand"
            >
              <option value="caixa">Caixa Econômica (SIGCB)</option>
              <option value="bb">Banco do Brasil (CBR641/CBR643)</option>
              <option value="generico">Genérico (Tamanho e Registro 0/1/9)</option>
            </select>
          </div>
        )}

        {/* Seletor do Banco - Registro Online */}
        {tipoValidacao === "registro_online" && (
          <div className="mt-4">
            <label className="text-xs text-muted font-medium">API do Banco (Registro Online)</label>
            <select
              value={bancoRegistroOnline}
              onChange={(e) => {
                setBancoRegistroOnline(e.target.value);
                limparResultados();
              }}
              className="mt-1 block rounded-lg border border-line bg-surface px-4 py-2 text-sm text-ink focus:border-brand"
            >
              <option value="caixa">Caixa Econômica (API Cobrança)</option>
              <option value="bb">Banco do Brasil (API Cobrança)</option>
            </select>
          </div>
        )}

        {/* Área de Entrada */}
        <div className="mt-6">
          {tipoValidacao === "registro_online" ? (
            <textarea
              value={xmlPayload}
              onChange={(e) => {
                setXmlPayload(e.target.value);
                limparResultados();
              }}
              placeholder={`Cole aqui qualquer trecho do XML de requisição do log do RM (${
                bancoRegistroOnline === "caixa" ? "Caixa" : "BB"
              }). Aceita trechos com <ext:...> ou <sib:...>.`}
              className="h-64 w-full rounded-lg border border-line bg-surface p-4 font-mono text-xs text-ink focus:border-brand"
            />
          ) : (
            <label className="flex cursor-pointer flex-col items-start gap-2 rounded-lg border border-dashed border-line bg-surface px-4 py-6 hover:border-brand">
              <span className="text-sm text-muted">
                {arquivo ? arquivo.name : "Clique para escolher o arquivo de remessa/retorno (.TXT, .REM ou .RET)"}
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
          )}
        </div>

        {/* Botões de Ação */}
        <div className="mt-4 flex gap-3">
          <button
            onClick={validar}
            disabled={carregando || (tipoValidacao !== "registro_online" && !arquivo)}
            className="rounded-md bg-action px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-action-hover disabled:opacity-50"
          >
            {carregando ? "Analisando..." : "Validar e Diagnosticar"}
          </button>
          {tipoValidacao === "240" && (
            <button
              onClick={corrigir}
              disabled={!arquivo || carregando}
              className="rounded-md border border-line px-4 py-2.5 text-sm font-medium text-ink transition hover:border-brand disabled:opacity-50"
            >
              {carregando ? "Corrigindo..." : "Corrigir automatico (Constantes)"}
            </button>
          )}
          {correcao && (
            <button
              onClick={baixarCorrigido}
              className="rounded-md border border-brand bg-brand/10 px-4 py-2.5 text-sm font-medium text-brand transition hover:bg-brand/20"
            >
              Baixar TXT Corrigido
            </button>
          )}
        </div>

        {/* Mensagem de Erro do Sistema */}
        {erro && (
          <p className="mt-4 rounded-md border border-red-300 bg-red-50 px-4 py-3 text-sm text-red-700 dark:border-red-500/30 dark:bg-red-500/10 dark:text-red-300">
            {erro}
          </p>
        )}

        {/* Resumo */}
        {resultado && (
          <div className="mt-6">
            <ResumoValidacao valido={resultado.valido} totalErros={resultado.erros.length} />
          </div>
        )}

        {/* Avisos Extras */}
        {avisosParaMostrar.length > 0 && (
          <div className="mt-4 space-y-2">
            {avisosParaMostrar.map((aviso, idx) => (
              <p
                key={idx}
                className="rounded-md border border-dashed border-action/50 bg-action/10 px-4 py-3 text-sm text-ink"
              >
                {aviso}
              </p>
            ))}
          </div>
        )}

        {/* Lista de Erros Diagnosticados com Dicas RM */}
        {errosParaMostrar.length > 0 && (
          <div className="mt-4 divide-y divide-line rounded-lg border border-line bg-surface">
            {errosParaMostrar.map((e, idx) => (
              <ErroItem key={idx} erro={e} tipo={tipoValidacao} />
            ))}
          </div>
        )}
      </div>
    </main>
  );
}

function ResumoValidacao({ valido, totalErros }: { valido: boolean; totalErros: number }) {
  if (valido) {
    return (
      <div className="rounded-lg border border-emerald-300 bg-emerald-50 px-4 py-3 text-sm text-emerald-700 dark:border-emerald-500/30 dark:bg-emerald-500/10 dark:text-emerald-300">
        Validação concluída: Nenhum erro de estrutura ou preenchimento encontrado.
      </div>
    );
  }
  return (
    <div className="rounded-lg border border-line bg-surface px-4 py-3 text-sm text-ink">
      <span className="font-bold text-action">{totalErros}</span> problema{totalErros === 1 ? "" : "s"} identificado{totalErros === 1 ? "" : "s"}.
    </div>
  );
}

function ErroItem({ erro, tipo }: { erro: ErroValidacao; tipo: string }) {
  return (
    <div className="px-5 py-4">
      <div className="flex flex-wrap items-center gap-2">
        {tipo !== "registro_online" && erro.linha !== null && erro.linha !== undefined && (
          <span className="rounded bg-surface-hover px-2 py-0.5 font-mono text-xs text-muted">Linha {erro.linha}</span>
        )}
        {tipo !== "registro_online" && erro.posicao_inicio !== null && erro.posicao_inicio !== undefined && (
          <span className="rounded bg-surface-hover px-2 py-0.5 font-mono text-xs text-muted">
            pos. {erro.posicao_inicio}
            {erro.posicao_fim !== erro.posicao_inicio ? `-${erro.posicao_fim}` : ""}
          </span>
        )}
        {tipo === "registro_online" && erro.campo && (
          <span className="rounded bg-brand/10 px-2 py-0.5 font-mono text-xs font-bold text-brand">
            Campo: {erro.campo}
          </span>
        )}
        {erro.corrigivel_automaticamente && (
          <span className="rounded-full bg-emerald-500/20 px-2 py-0.5 text-[10px] font-medium text-emerald-600 dark:text-emerald-400">
            corrigível automaticamente
          </span>
        )}
      </div>

      <p className="mt-2 text-sm font-medium text-ink">{erro.mensagem}</p>

      {/* Caixa Destacada para Dica de Resolução no TOTVS RM */}
      {erro.sugestao_rm && (
        <div className="mt-3 rounded-md border border-brand/20 bg-brand/5 p-3 text-xs">
          <span className="font-bold text-brand">💡 Dica de Resolução TOTVS RM:</span>
          <p className="mt-1 text-ink leading-relaxed">{erro.sugestao_rm}</p>
        </div>
      )}
    </div>
  );
}