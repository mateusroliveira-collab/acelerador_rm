"""
Registro dos módulos do gerador de DataServer. Pra acrescentar um módulo
novo (Eventos Contábeis, Tipos de Documento, Educacional...): crie o
subpacote, importe o MODULO aqui e inclua na lista.
"""

from .base import Modulo
from .glb_usuario import MODULO as GLB_USUARIO

MODULOS: dict[str, Modulo] = {m.chave: m for m in (GLB_USUARIO,)}
