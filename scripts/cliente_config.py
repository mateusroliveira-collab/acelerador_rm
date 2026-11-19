"""
Administra a configuração por cliente (tabela `cliente`).

Não existe rota de escrita na API de propósito (a API é aberta): a manutenção
é feita por aqui, na sua máquina, apontando para o banco via DATABASE_URL.

Uso (da raiz do projeto, com o venv ativo):
  python scripts/cliente_config.py listar
  python scripts/cliente_config.py mostrar acme
  python scripts/cliente_config.py definir acme --nome "ACME S.A." \
        --codigos-acesso Acesso01,Acesso02 --versao-rm 12.1.2310
  python scripts/cliente_config.py desativar acme
  python scripts/cliente_config.py ativar acme

ATENÇÃO: sem DATABASE_URL o script usa o SQLite local (dev.db). Para mexer no
Neon, defina DATABASE_URL na sua sessão -- NUNCA grave a URL em arquivo
versionado. O script mostra o servidor de destino antes de gravar.
Só guarde configuração aqui; nunca dado pessoal nem credencial.
"""

import argparse
import json
import sys
from pathlib import Path
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from api._lib import db as banco  # noqa: E402
from api._lib.models import Cliente  # noqa: E402

MODULO_PADRAO = "glb-usuario"


def _destino() -> str:
    url = urlparse(banco.DATABASE_URL.replace("+psycopg2", ""))
    if url.scheme.startswith("sqlite"):
        return f"SQLite local ({url.path})"
    return f"{url.scheme}://{url.hostname}{url.path}"  # sem usuário nem senha


def _sessao():
    banco.criar_tabelas()
    return banco.SessionLocal()


def _config(linha: Cliente) -> dict:
    try:
        dados = json.loads(linha.config or "{}")
        return dados if isinstance(dados, dict) else {}
    except ValueError:
        return {}


def cmd_listar(args) -> int:
    db = _sessao()
    try:
        linhas = db.query(Cliente).order_by(Cliente.codigo).all()
        if not linhas:
            print("Nenhum cliente cadastrado.")
        for c in linhas:
            print(f"{c.codigo:20s} {'ativo  ' if c.ativo else 'inativo'} {c.nome or ''}")
    finally:
        db.close()
    return 0


def cmd_mostrar(args) -> int:
    db = _sessao()
    try:
        c = db.query(Cliente).filter_by(codigo=args.codigo).first()
        if not c:
            print(f"Cliente '{args.codigo}' não encontrado.")
            return 1
        print(f"{c.codigo} ({'ativo' if c.ativo else 'inativo'}) -- {c.nome or ''}")
        print(json.dumps(_config(c), ensure_ascii=False, indent=2))
    finally:
        db.close()
    return 0


def cmd_definir(args) -> int:
    print(f"Destino: {_destino()}")
    db = _sessao()
    try:
        c = db.query(Cliente).filter_by(codigo=args.codigo).first()
        if not c:
            c = Cliente(codigo=args.codigo, ativo=True)
            db.add(c)
        if args.nome:
            c.nome = args.nome
        dados = _config(c)
        modulo = dados.setdefault(args.modulo, {})
        if args.codigos_acesso is not None:
            lista = [x.strip() for x in args.codigos_acesso.split(",") if x.strip()]
            if lista:
                modulo["codigos_acesso"] = lista
            else:
                modulo.pop("codigos_acesso", None)
        if args.versao_rm:
            modulo["versao_rm"] = args.versao_rm
        c.config = json.dumps(dados, ensure_ascii=False)
        db.commit()
        print(f"Cliente '{args.codigo}' atualizado:")
        print(json.dumps(dados, ensure_ascii=False, indent=2))
    finally:
        db.close()
    return 0


def _alterar_ativo(codigo: str, ativo: bool) -> int:
    print(f"Destino: {_destino()}")
    db = _sessao()
    try:
        c = db.query(Cliente).filter_by(codigo=codigo).first()
        if not c:
            print(f"Cliente '{codigo}' não encontrado.")
            return 1
        c.ativo = ativo
        db.commit()
        print(f"Cliente '{codigo}' agora está {'ativo' if ativo else 'inativo'}.")
    finally:
        db.close()
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Configuração por cliente do Acelerador RM.")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("listar").set_defaults(fn=cmd_listar)
    m = sub.add_parser("mostrar"); m.add_argument("codigo"); m.set_defaults(fn=cmd_mostrar)
    d = sub.add_parser("definir"); d.add_argument("codigo")
    d.add_argument("--nome"); d.add_argument("--modulo", default=MODULO_PADRAO)
    d.add_argument("--codigos-acesso", help="lista separada por vírgula; vazio remove a lista")
    d.add_argument("--versao-rm"); d.set_defaults(fn=cmd_definir)
    a = sub.add_parser("ativar"); a.add_argument("codigo"); a.set_defaults(fn=lambda x: _alterar_ativo(x.codigo, True))
    z = sub.add_parser("desativar"); z.add_argument("codigo"); z.set_defaults(fn=lambda x: _alterar_ativo(x.codigo, False))
    args = p.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
