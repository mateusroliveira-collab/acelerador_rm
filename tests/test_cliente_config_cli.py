import json
import os
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(RAIZ / "scripts"))
for _v in ("DATABASE_URL", "POSTGRES_URL", "POSTGRES_PRISMA_URL", "DATABASE_URL_UNPOOLED", "PGHOST", "VERCEL"):
    os.environ.pop(_v, None)
os.environ["DATABASE_URL"] = f"sqlite:///{tempfile.mkdtemp()}/cli.db"

import cliente_config as cli  # noqa: E402
from api._lib.clientes import config_do_cliente  # noqa: E402


def test_definir_listar_mostrar_e_desativar(capsys):
    assert cli.main(["definir", "cli-teste", "--nome", "Cliente Teste",
                     "--codigos-acesso", "Acesso01, Acesso02", "--versao-rm", "12.1"]) == 0
    assert config_do_cliente("cli-teste", "glb-usuario") == {
        "codigos_acesso": ["Acesso01", "Acesso02"], "versao_rm": "12.1"}

    capsys.readouterr()
    assert cli.main(["listar"]) == 0
    assert "cli-teste" in capsys.readouterr().out

    # atualizar mantém o que já existia
    assert cli.main(["definir", "cli-teste", "--codigos-acesso", "Acesso03"]) == 0
    cfg = config_do_cliente("cli-teste", "glb-usuario")
    assert cfg["codigos_acesso"] == ["Acesso03"] and cfg["versao_rm"] == "12.1"

    # lista vazia remove a restrição
    assert cli.main(["definir", "cli-teste", "--codigos-acesso", ""]) == 0
    assert "codigos_acesso" not in config_do_cliente("cli-teste", "glb-usuario")

    assert cli.main(["desativar", "cli-teste"]) == 0
    assert config_do_cliente("cli-teste", "glb-usuario") is None  # inativo: sem config
    assert cli.main(["ativar", "cli-teste"]) == 0
    assert config_do_cliente("cli-teste", "glb-usuario") is not None


def test_cliente_inexistente_devolve_erro(capsys):
    assert cli.main(["mostrar", "nao-existe"]) == 1
    assert cli.main(["desativar", "nao-existe"]) == 1


def test_destino_nao_mostra_senha():
    from api._lib import db as banco
    original = banco.DATABASE_URL
    try:
        banco.DATABASE_URL = "postgresql+psycopg2://usuario:segredo123@host.exemplo/banco"
        destino = cli._destino()
        assert "segredo123" not in destino and "usuario" not in destino and "host.exemplo" in destino
    finally:
        banco.DATABASE_URL = original
