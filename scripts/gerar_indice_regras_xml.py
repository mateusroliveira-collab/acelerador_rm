"""
Regera data/regras_xml.json (regra de negócio de cada XML da biblioteca fixa).

Rode sempre que adicionar, trocar ou remover XML em data/xml_base:
  python scripts/gerar_indice_regras_xml.py

O teste tests/test_regras_xml.py falha se o índice estiver desatualizado.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from api._lib import regras_xml  # noqa: E402


def main() -> None:
    indice = regras_xml.calcular_indice()
    regras_xml.ARQUIVO_INDICE.write_text(
        json.dumps(indice, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(f"{len(indice['regras'])} XMLs indexados em {regras_xml.ARQUIVO_INDICE}")


if __name__ == "__main__":
    main()
