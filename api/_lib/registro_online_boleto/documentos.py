"""
Validação de CPF e CNPJ via algoritmo de dígito verificador (módulo 11).

Isso é regra PÚBLICA e UNIVERSAL -- definida pela Receita Federal, igual
pra qualquer banco. Não depende de manual de banco nenhum, diferente do
resto do módulo de CNAB/Registro Online.
"""

import re


def _somente_digitos(texto: str) -> str:
    return re.sub(r"\D", "", texto or "")


def _eh_sequencia_repetida(digitos: str) -> bool:
    """CPF/CNPJ com todos os dígitos iguais (ex: '11111111111') são
    matematicamente 'válidos' pelo cálculo, mas são sempre inválidos na
    prática -- a Receita nunca emite documento assim."""
    return len(set(digitos)) == 1


def validar_cpf(cpf: str) -> bool:
    """Valida CPF pelo algoritmo oficial de dígito verificador."""
    digitos = _somente_digitos(cpf)
    if len(digitos) != 11 or _eh_sequencia_repetida(digitos):
        return False

    numeros = [int(d) for d in digitos]

    soma = sum(numeros[i] * (10 - i) for i in range(9))
    resto = soma % 11
    digito1 = 0 if resto < 2 else 11 - resto
    if digito1 != numeros[9]:
        return False

    soma = sum(numeros[i] * (11 - i) for i in range(10))
    resto = soma % 11
    digito2 = 0 if resto < 2 else 11 - resto
    if digito2 != numeros[10]:
        return False

    return True


def validar_cnpj(cnpj: str) -> bool:
    """Valida CNPJ pelo algoritmo oficial de dígito verificador."""
    digitos = _somente_digitos(cnpj)
    if len(digitos) != 14 or _eh_sequencia_repetida(digitos):
        return False

    numeros = [int(d) for d in digitos]

    pesos1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    soma = sum(numeros[i] * pesos1[i] for i in range(12))
    resto = soma % 11
    digito1 = 0 if resto < 2 else 11 - resto
    if digito1 != numeros[12]:
        return False

    pesos2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    soma = sum(numeros[i] * pesos2[i] for i in range(13))
    resto = soma % 11
    digito2 = 0 if resto < 2 else 11 - resto
    if digito2 != numeros[13]:
        return False

    return True


def validar_documento(documento: str) -> tuple[bool, str]:
    """
    Detecta se é CPF (11 dígitos) ou CNPJ (14 dígitos) pelo tamanho, e
    valida de acordo. Devolve (é_válido, tipo_detectado).
    """
    digitos = _somente_digitos(documento)
    if len(digitos) == 11:
        return validar_cpf(digitos), "CPF"
    if len(digitos) == 14:
        return validar_cnpj(digitos), "CNPJ"
    return False, "desconhecido"
