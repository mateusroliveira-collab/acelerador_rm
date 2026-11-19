"use client";

import { useEffect, useState } from "react";
import { Header } from "../components/Header";

type Modulo = {
  chave: string;
  nome: string;
  planilha_modelo_url?: string | null;
  planilha_modelo_xlsx_url?: string | null;
};

const MODULO = "glb-usuario";

/**
 * Página pública para o CLIENTE: só entrega o modelo da planilha de cadastro
 * de usuários e explica como preencher. Não tem nenhuma ferramenta de
 * validação nem de geração de arquivos -- isso é do analista.
 */
export default function PlanilhaModeloPage() {
  const [modulo, setModulo] = useState<Modulo | null>(null);
  const [carregado, setCarregado] = useState(false);

  useEffect(() => {
    fetch("/api/v1/dataserver/modulos")
      .then((r) => (r.ok ? r.json() : []))
      .then((dados: Modulo[]) => {
        if (Array.isArray(dados)) setModulo(dados.find((m) => m.chave === MODULO) ?? null);
      })
      .catch(() => setModulo(null))
      .finally(() => setCarregado(true));
  }, []);

  const botao =
    "inline-block rounded-md px-5 py-2.5 text-sm font-medium transition";

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
          <h2 className="font-display text-sm font-bold text-ink">Escolha como obter a planilha</h2>

          {carregado && modulo?.planilha_modelo_url ? (
            <div className="mt-4 flex flex-wrap gap-3">
              <a
                href={modulo.planilha_modelo_url}
                target="_blank"
                rel="noopener noreferrer"
                className={`${botao} bg-action text-white hover:bg-action-hover`}
              >
                Criar minha cópia no Google Sheets
              </a>
              {modulo.planilha_modelo_xlsx_url && (
                <a
                  href={modulo.planilha_modelo_xlsx_url}
                  className={`${botao} border border-line text-ink hover:border-brand`}
                >
                  Baixar em Excel (.xlsx)
                </a>
              )}
              <a
                href={`/api/v1/dataserver/${MODULO}/modelo-csv`}
                className={`${botao} border border-line text-ink hover:border-brand`}
              >
                Baixar em CSV
              </a>
            </div>
          ) : carregado ? (
            <div className="mt-4">
              <p className="text-sm text-muted">
                O modelo online ainda não está disponível. Você pode baixar o modelo em CSV (abre no
                Excel e no Google Sheets):
              </p>
              <a
                href={`/api/v1/dataserver/${MODULO}/modelo-csv`}
                className={`${botao} mt-3 border border-line text-ink hover:border-brand`}
              >
                Baixar em CSV
              </a>
            </div>
          ) : (
            <p className="mt-4 text-sm text-muted">Carregando...</p>
          )}

          <ul className="mt-4 list-disc space-y-1 pl-5 text-xs text-muted">
            <li>
              <strong>Criar minha cópia no Google Sheets:</strong> abre uma cópia só sua (precisa de
              conta Google). Cada pessoa que clica recebe a sua própria planilha.
            </li>
            <li>
              <strong>Baixar em Excel / CSV:</strong> não precisa de conta Google.
            </li>
            <li>Se o seu analista enviou um link próprio, use o link dele.</li>
          </ul>
        </div>

        <div className="mt-6 rounded-lg border border-line bg-surface p-5">
          <h2 className="font-display text-sm font-bold text-ink">Como preencher</h2>
          <ol className="mt-3 list-decimal space-y-1 pl-5 text-sm text-muted">
            <li>Preencha a aba <strong>Dados</strong>, uma linha por usuário.</li>
            <li>Colunas com <strong>*</strong> e fundo amarelo são obrigatórias.</li>
            <li>
              Colunas com seta têm uma lista: escolha o valor (Sim/Não, código de acesso). Se a lista
              de códigos de acesso estiver vazia ou com valores de exemplo, peça os códigos corretos ao
              seu analista.
            </li>
            <li>Datas no formato DD/MM/AAAA.</li>
            <li>
              <strong>Não informe senha.</strong> Ela não faz parte deste cadastro.
            </li>
            <li>Não altere o cabeçalho (primeira linha) nem a ordem das colunas.</li>
            <li>Ao terminar, envie a planilha ao seu analista (ou compartilhe o link dela com ele).</li>
          </ol>
          <p className="mt-4 text-xs text-muted">
            Esta página só fornece o modelo: nada do que você preencher é enviado para este site.
          </p>
        </div>
      </div>
    </main>
  );
}
