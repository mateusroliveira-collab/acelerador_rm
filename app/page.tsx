import Link from "next/link";
import { Header } from "./components/Header";

const ferramentas = [
  {
    href: "/pre-processador-mit41",
    codigo: "01",
    titulo: "Interpretador de MIT 41",
    descricao:
      "Organiza o MIT 41 bruto em subprocessos via regra pura.",
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
          Acelerador de implantação SPUB com IA
        </h1>
        <p className="mt-3 max-w-xl text-muted">
          Agentes aceleraradores
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
      </div>
    </main>
  );
}
