"""
Gera uma planilha de TESTE (dados 100% fictícios) a partir do modelo oficial:
30 usuários, sendo 3 com erro de propósito, pra ver a validação funcionando.

Uso (da raiz do projeto, com o venv ativo):
  python scripts/gerar_planilha_teste.py [caminho_de_saida.xlsx]

Nenhum dado real: nomes e e-mails inventados, domínio exemplo.com.
"""

import io
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from openpyxl import load_workbook  # noqa: E402

from api._lib.dataserver import xlsx as px  # noqa: E402
from api._lib.dataserver.glb_usuario import MODULO  # noqa: E402

NOMES = [
    "Ana", "Bruno", "Carla", "Diego", "Elisa", "Fabio", "Gisele", "Hugo", "Iara", "Joao",
    "Karina", "Lucas", "Marina", "Nelson", "Olivia", "Paulo", "Quiteria", "Rafael", "Sara", "Tiago",
    "Ursula", "Victor", "Wanda", "Xavier", "Yara", "Zeca", "Alice", "Bento", "Clara", "Davi",
]


def main(saida: str = "cadastro_usuarios_ficticio.xlsx") -> None:
    wb = load_workbook(io.BytesIO(px.gerar_modelo_xlsx(MODULO)))
    ws = wb["Dados"]

    for i, nome in enumerate(NOMES):
        linha = 2 + i
        login = f"{nome.lower()}.teste"
        ws.cell(row=linha, column=1, value=login)
        ws.cell(row=linha, column=2, value=f"{nome} de Teste")
        ws.cell(row=linha, column=4, value=f"{login}@exemplo.com")
        ws.cell(row=linha, column=5, value="Acesso01" if i % 2 == 0 else "Acesso02")
        ws.cell(row=linha, column=6, value="Sim")
        ws.cell(row=linha, column=7, value="Não")
        ws.cell(row=linha, column=8, value="Sim")
        ws.cell(row=linha, column=10, value=datetime(2026, 12, 1 + i % 28))
        ws.cell(row=linha, column=14, value="Não")

    # Três erros de propósito:
    ws.cell(row=6, column=4, value="isto-nao-e-um-email")      # linha 6: e-mail inválido
    ws.cell(row=12, column=5).value = None                     # linha 12: sem código de acesso (obrigatório)
    ws.cell(row=20, column=1, value=ws.cell(row=2, column=1).value)  # linha 20: usuário repetido da linha 2

    Path(saida).write_bytes(_salvar(wb))
    print(f"Planilha de teste gerada: {saida}")
    print("Esperado ao validar: 30 linhas, 27 válidas, 3 com erro (linhas 6, 12 e 20).")


def _salvar(wb) -> bytes:
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


if __name__ == "__main__":
    main(*sys.argv[1:2])
