"use client";

import Image from "next/image";
import Link from "next/link";
import { useEffect, useState } from "react";

type Tema = "light" | "dark";

function aplicarTema(tema: Tema) {
  document.documentElement.classList.toggle("dark", tema === "dark");
  window.localStorage.setItem("tema", tema);
}

/**
 * Cabeçalho com logo (troca sozinha entre a versão clara/escura conforme o
 * tema) e o botão de alternar dia/noite. Os dois arquivos de logo ficam em
 * public/totvs-logo-escura.png (pro modo dia, fundo claro) e
 * public/totvs-logo-branca.png (pro modo noite, fundo escuro).
 */
export function Header() {
  const [tema, setTema] = useState<Tema>("dark");

  useEffect(() => {
    const salvo = window.localStorage.getItem("tema") as Tema | null;
    const temaInicial =
      salvo ??
      (window.matchMedia("(prefers-color-scheme: light)").matches
        ? "light"
        : "dark");
    setTema(temaInicial);
    aplicarTema(temaInicial);
  }, []);

  function alternarTema() {
    const novoTema = tema === "dark" ? "light" : "dark";
    setTema(novoTema);
    aplicarTema(novoTema);
  }

  return (
    <div className="flex items-center justify-between">
      <div className="flex items-center gap-3">
        <Image
          src={tema === "dark" ? "/totvs-logo-branca.png" : "/totvs-logo-escura.png"}
          alt="TOTVS"
          width={150}
          height={65}
          className="shrink-0"
          priority
        />
        <Link
          href="/"
          className="font-mono text-xs uppercase tracking-[0.2em] text-muted hover:text-ink"
        >
          Ferramentas RM
        </Link>
      </div>

      <button
        onClick={alternarTema}
        aria-label={
          tema === "dark" ? "Mudar para modo dia" : "Mudar para modo noite"
        }
        className="flex items-center gap-2 rounded-full border border-line px-3 py-1.5 text-xs text-muted transition hover:border-brand hover:text-ink"
      >
        {tema === "dark" ? (
          <>
            <svg
              width="14"
              height="14"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <circle cx="12" cy="12" r="4" />
              <path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M6.34 17.66l-1.41 1.41M19.07 4.93l-1.41 1.41" />
            </svg>
            Dia
          </>
        ) : (
          <>
            <svg
              width="14"
              height="14"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
            </svg>
            Noite
          </>
        )}
      </button>
    </div>
  );
}