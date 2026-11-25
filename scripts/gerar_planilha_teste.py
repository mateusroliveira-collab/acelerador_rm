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
    col = {c.value: c.column for c in ws[1]}  # cabeçalho = nomes dos campos do RM

    for i, nome in enumerate(NOMES):
        linha = 2 + i
        login = f"{nome.lower()}.teste"
        valores = {
            "CODUSUARIO": login,
            "NOME": f"{nome} de Teste",
            "CODACESSO": "Acesso01" if i % 2 == 0 else "Acesso02",
            "STATUS": 1,
            "DATAINICIO": datetime(2026, 12, 1 + i % 28),
            "IGNORARAUTENTICACAOLDAP": "F",
            "EMAIL": f"{login}@exemplo.com",
            "OIDC_ENABLED": 0,
            "OBRIGAALTERARSENHA": 1,
        }
        for campo, valor in valores.items():
            ws.cell(row=linha, column=col[campo], value=valor)

    # Três erros de propósito:
    ws.cell(row=6, column=col["EMAIL"], value="isto-nao-e-um-email")  # linha 6: e-mail inválido
    ws.cell(row=12, column=col["CODACESSO"]).value = None             # linha 12: sem código de acesso
    ws.cell(row=20, column=col["CODUSUARIO"], value=ws.cell(row=2, column=col["CODUSUARIO"]).value)  # linha 20: repetido

    Path(saida).write_bytes(_salvar(wb))
    print(f"Planilha de teste gerada: {saida}")
    print("Esperado ao validar: 30 linhas, 27 válidas, 3 com erro (linhas 6, 12 e 20).")


def _salvar(wb) -> bytes:
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


if __name__ == "__main__":
    main(*sys.argv[1:2])
