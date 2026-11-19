"use client";

import { useEffect, useState } from "react";
import { Header } from "../components/Header";

type Modulo = {
  chave: string;
  nome: string;
  planilha_modelo_url?: string | null;
};

const MODULO = "glb-usuario";

/**
 * Página pública para o CLIENTE: só entrega o modelo da planilha de cadastro
 * de usuários e explica como preencher. Não tem nenhuma ferramenta de
 * validação nem de geração de arquivos -- isso é do analista.
 */
export default function PlanilhaModeloPage() {
  // Opcional: se houver uma planilha do Google configurada, oferece criar cópia.
  const [linkGoogle, setLinkGoogle] = useState<string | null>(null);

  useEffect(() => {
    fetch("/api/v1/dataserver/modulos")
      .then((r) => (r.ok ? r.json() : []))
      .then((dados: Modulo[]) => {
        if (Array.isArray(dados)) {
          setLinkGoogle(dados.find((m) => m.chave === MODULO)?.planilha_modelo_url ?? null);
        }
      })
      .catch(() => setLinkGoogle(null));
  }, []);

  const botao = "inline-block rounded-md px-5 py-2.5 text-sm font-medium transition";

  return (
    <main className="min-h-screen px-6 py-12 md:px-12 lg:px-20">
      <div className="mx-auto max-w-3xl">
        <Header />
        <h1 className="mt-6 font-display text-4xl font-bold text-ink md:text-5xl">
          Planilha de cadastro de usuários
        </h1>
        <p className="mt-3 max-w-xl text-muted">
          Use esta planilha para informar os usuários que serão cadastrados no sistema. Preencha,
          confira e devolva ao seu analista.
        </p>

        <div className="mt-8 rounded-lg border border-line bg-surface p-5">
          <h2 className="font-display text-sm font-bold text-ink">Baixe a planilha</h2>
          <div className="mt-4 flex flex-wrap gap-3">
            <a
              href={`/api/v1/dataserver/${MODULO}/modelo-xlsx`}
              className={`${botao} bg-action text-white hover:bg-action-hover`}
            >
              Baixar planilha Excel (.xlsx)
            </a>
            {linkGoogle && (
              <a
                href={linkGoogle}
                target="_blank"
                rel="noopener noreferrer"
                className={`${botao} border border-line text-ink hover:border-brand`}
              >
                Criar cópia no Google Sheets
              </a>
            )}
            <a
              href={`/api/v1/dataserver/${MODULO}/modelo-csv`}
              className={`${botao} border border-line text-ink hover:border-brand`}
            >
              Baixar em CSV
            </a>
          </div>
          <p className="mt-4 text-xs text-muted">
            O arquivo Excel é o recomendado: vem com listas de opções, datas e e-mails conferidos
            enquanto você digita, e com o cabeçalho protegido. Se o seu analista enviou uma planilha
            própria, use a dele.
          </p>
        </div>

        <div className="mt-6 rounded-lg border border-line bg-surface p-5">
          <h2 className="font-display text-sm font-bold text-ink">Como preencher</h2>
          <ol className="mt-3 list-decimal space-y-1 pl-5 text-sm text-muted">
            <li>Preencha a aba <strong>Dados</strong>, uma linha por usuário.</li>
            <li>Colunas com <strong>*</strong> e fundo amarelo são obrigatórias.</li>
            <li>
              Colunas com seta têm uma lista: escolha o valor (Sim/Não, código de acesso). Se a lista
              de códigos de acesso vier com valores de exemplo, peça os códigos corretos ao seu
              analista.
            </li>
            <li>Datas no formato DD/MM/AAAA.</li>
            <li>
              <strong>Não informe senha.</strong> Ela não faz parte deste cadastro.
            </li>
            <li>Não altere o cabeçalho (primeira linha) nem a ordem das colunas.</li>
            <li>Salve o arquivo e envie ao seu analista.</li>
          </ol>
          <p className="mt-4 text-xs text-muted">
            Esta página só fornece o modelo: nada do que você preencher é enviado para este site.
          </p>
        </div>
      </div>
    </main>
  );
}
