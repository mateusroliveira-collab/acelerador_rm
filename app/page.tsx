import Link from "next/link";
import { Header } from "./components/Header";

const ferramentas = [
  {
    href: "/pre-processador-mit41",
    codigo: "01",
    titulo: "Interpretador de MIT 41",
    descricao: "Organiza o MIT 41 bruto em subprocessos via regra pura.",
    disponivel: true,
  },
  {
    href: "/buscador-xml",
    codigo: "02",
    titulo: "Buscador de XML",
    descricao: "Encontre e higienize templates de tipos de movimento.",
    disponivel: true,
  },
  {
    href: "/validador-cnab",
    codigo: "03",
    titulo: "Validador de CNAB",
    descricao: "Valide arquivos CNAB 240, 400 e registros online.",
    disponivel: true,
  },
];

export default function HomePage() {
  return (
    <main className="min-h-screen px-6 py-12 md:px-12 lg:px-20">
      <div className="mx-auto max-w-4xl">
        <Header />
        
        <h1 className="mt-6 font-display text-4xl font-bold text-ink md:text-5xl">
          Aceleradores de implantação SPUB com IA
        </h1>
        <p className="mt-3 max-w-xl text-muted">
          Agentes aceleradores
        </p>

        <div className="mt-10 grid gap-4 sm:grid-cols-3">
          {ferramentas.map((f) => (
            <Link
              key={f.codigo}
              href={f.disponivel ? f.href : "#"}
              aria-disabled={!f.disponivel}
              className={`rounded-lg border border-line bg-surface p-5 transition ${
                f.disponivel
                  ? "hover:border-brand"
                  : "cursor-not-allowed opacity-50"
              }`}
            >
              <span className="font-mono text-xs text-muted">{f.codigo}</span>
              <h2 className="mt-2 font-display text-lg font-bold text-ink">
                {f.titulo}
              </h2>
              <p className="mt-1 text-sm text-muted">{f.descricao}</p>
              {!f.disponivel && (
                <span className="mt-3 inline-block text-xs font-medium text-muted">
                  Em breve
                </span>
              )}
            </Link>
          ))}
        </div>

        {/* FOOTER ELEGANTE PREMIUM */}
        <footer className="mt-24 mb-12 rounded-2xl border border-line bg-surface/50 p-6 shadow-sm md:p-8">
          <div className="flex flex-col gap-10 md:flex-row md:items-start md:justify-between">
            
            {/* Time Técnico */}
            <div className="flex-1">
              <h3 className="flex items-center gap-2 text-xs font-bold uppercase tracking-widest text-muted">
                <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
                </svg>
                Time Técnico
              </h3>
              <div className="mt-5 grid grid-cols-2 gap-4 sm:grid-cols-4">
                {[
                  { nome: "Adoninas", inicial: "A" },
                  { nome: "Bento", inicial: "B" },
                  { nome: "Mateus", inicial: "M" },
                  { nome: "Moises", inicial: "M" },
                  
                ].map((membro) => (
                  <div key={membro.nome} className="flex items-center gap-3 transition hover:opacity-80">
                    <div className="flex h-8 w-8 items-center justify-center rounded-full bg-brand/10 text-xs font-bold text-brand-light">
                      {membro.inicial}
                    </div>
                    <span className="text-sm font-medium text-ink">{membro.nome}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Divisor mobile */}
            <div className="h-px w-full bg-line md:hidden"></div>

            {/* Coordenação */}
            <div className="md:w-64 md:border-l md:border-line md:pl-8">
              <h3 className="flex items-center gap-2 text-xs font-bold uppercase tracking-widest text-muted">
                <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                </svg>
                Coordenação
              </h3>
              <div className="mt-5 flex items-center gap-3">
                <div className="flex h-8 w-8 items-center justify-center rounded-full bg-action/10 text-xs font-bold text-action">
                  R
                </div>
                <span className="text-sm font-medium text-ink">Rodrigo</span>
              </div>
            </div>

          </div>
        </footer>

      </div>
    </main>
  );
}