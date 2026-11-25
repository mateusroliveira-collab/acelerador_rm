"use client";

import { Header } from "../components/Header";
import { PostmanRm } from "../components/PostmanRm";

/**
 * Evento Contábil Automático: "Postman facilitado" focado no DataServer de
 * eventos contábeis. Puxa eventos de uma base (GET, completo com os itens),
 * junta com arquivos .json de outros lugares, troca a coligada se precisar e
 * envia para a base de destino -- tudo no formato JSON do GET do RM.
 */
export default function EventoContabilAutomaticoPage() {
  return (
    <main className="min-h-screen px-6 py-12 md:px-12 lg:px-20">
      <div className="mx-auto max-w-5xl">
        <Header />
        <h1 className="mt-6 font-display text-4xl font-bold text-ink md:text-5xl">Evento Contábil Automático</h1>
        <p className="mt-3 max-w-2xl text-muted">
          Um Postman simplificado para os eventos contábeis do RM: consulte numa base, junte com arquivos JSON de
          outros lugares e envie para a base que quiser. As chamadas saem da <strong>sua máquina</strong>, pelo
          conector; o site não se conecta ao RM e não recebe sua senha.
        </p>

        <ol className="mt-6 grid gap-3 text-sm sm:grid-cols-3">
          <li className="rounded-lg border border-line bg-surface p-4">
            <p className="font-display font-bold text-ink">1. Puxe</p>
            <p className="mt-1 text-xs text-muted">
              <strong>GET</strong> na base de origem. Marque &quot;Trazer completo&quot; (aba Parâmetros) para vir
              com os itens de débito e crédito. Depois, <strong>Usar como corpo</strong>.
            </p>
          </li>
          <li className="rounded-lg border border-line bg-surface p-4">
            <p className="font-display font-bold text-ink">2. Junte e ajuste</p>
            <p className="mt-1 text-xs text-muted">
              <strong>Anexar arquivos .json</strong> de outras bases ou colegas (formato do GET), edite o JSON e, se a
              coligada for outra, use <strong>Trocar para a coligada</strong>.
            </p>
          </li>
          <li className="rounded-lg border border-line bg-surface p-4">
            <p className="font-display font-bold text-ink">3. Envie</p>
            <p className="mt-1 text-xs text-muted">
              <strong>POST</strong> para a base de destino. Um evento por chamada; o que já existir é pulado (ou
              alterado, em Opções). Teste com o primeiro antes de mandar todos.
            </p>
          </li>
        </ol>

        <div className="mt-6">
          <PostmanRm
            dataserverPadrao=""
            campoChavePadrao="CODCOLIGADA,CODEVENTO"
            metodoInicial="GET"
            permitirTrocarColigada
            lembrarComo="evento-contabil"
            nomeArquivo="eventos_contabeis"
          />
        </div>

        <div className="mt-6 rounded-lg border border-line bg-surface p-4 text-xs text-muted">
          <p className="font-display text-sm font-bold text-ink">Dicas</p>
          <ul className="mt-2 list-disc space-y-1 pl-5">
            <li>
              <strong>DataServer:</strong> informe o nome que aparece no endereço do GET que você já usa
              (<code>/rmsrestdataserver/rest/&lt;NOME&gt;</code>). Ele fica lembrado neste navegador.
            </li>
            <li>
              <strong>Chave:</strong> o evento é identificado por coligada + código (<code>CODCOLIGADA,CODEVENTO</code>);
              no RM a chave vira <code>1$_$1</code>. Para consultar um só, digite a chave assim no GET.
            </li>
            <li>
              <strong>Filtro:</strong> na aba Parâmetros, ex.: <code>filter=CODCOLIGADA = 1</code>.
            </li>
            <li>
              <strong>Contas, fórmulas e centros de custo</strong> precisam existir na base de destino; senão o RM
              recusa (erro 0007), e a tela explica o motivo.
            </li>
            <li>
              Para outros DataServers, troque o nome e o campo chave: a tela funciona com qualquer um.
            </li>
          </ul>
        </div>
      </div>
    </main>
  );
}
