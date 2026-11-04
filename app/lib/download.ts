/**
 * Dispara o download de um Blob no navegador.
 *
 * O link precisa estar no DOM (Firefox ignora clique em <a> solto) e a URL
 * só pode ser revogada depois que o navegador começou o download --
 * revogar logo após o click() cancelava o download em alguns navegadores.
 */
export function baixarBlob(blob: Blob, nomeArquivo: string) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = nomeArquivo;
  link.style.display = "none";
  document.body.appendChild(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

/** "arquivo.xml" / "arquivo.XML" -> "arquivo_LIMPO.xml" (mesma regra do backend). */
export function nomeLimpo(nomeOriginal: string) {
  const base = nomeOriginal.replace(/\.[^./\\]+$/, "") || "arquivo";
  return `${base}_LIMPO.xml`;
}
