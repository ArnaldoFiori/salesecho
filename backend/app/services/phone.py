import re


def normalize_phone(phone: str) -> str:
    """
    Normaliza telefone para formato: somente dígitos com DDI Brasil.
    Resultado: '5511999998888'
    """
    digits = re.sub(r'\D', '', phone)
    if digits.startswith('0'):
        digits = digits[1:]
    if not digits.startswith('55'):
        digits = '55' + digits
    return digits
