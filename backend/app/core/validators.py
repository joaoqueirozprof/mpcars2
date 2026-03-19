"""Validation utilities for CPF, CNPJ, and other Brazilian documents."""
import re
from typing import Optional


def validate_cpf(cpf: str) -> bool:
    """
    Validate Brazilian CPF number.
    
    Args:
        cpf: CPF number as string (with or without mask)
    
    Returns:
        True if valid, False otherwise
    """
    if not cpf:
        return False
    
    cpf = re.sub(r'[^0-9]', '', cpf)
    
    if len(cpf) != 11:
        return False
    
    if cpf == cpf[0] * 11:
        return False
    
    sum_val = 0
    for i in range(9):
        sum_val += int(cpf[i]) * (10 - i)
    
    first_digit = (sum_val * 10) % 11
    if first_digit == 10:
        first_digit = 0
    
    if int(cpf[9]) != first_digit:
        return False
    
    sum_val = 0
    for i in range(10):
        sum_val += int(cpf[i]) * (11 - i)
    
    second_digit = (sum_val * 10) % 11
    if second_digit == 10:
        second_digit = 0
    
    if int(cpf[10]) != second_digit:
        return False
    
    return True


def validate_cnpj(cnpj: str) -> bool:
    """
    Validate Brazilian CNPJ number.
    
    Args:
        cnpj: CNPJ number as string (with or without mask)
    
    Returns:
        True if valid, False otherwise
    """
    if not cnpj:
        return False
    
    cnpj = re.sub(r'[^0-9]', '', cnpj)
    
    if len(cnpj) != 14:
        return False
    
    if cnpj == cnpj[0] * 14:
        return False
    
    weights_1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    sum_val = sum(int(cnpj[i]) * weights_1[i] for i in range(12))
    first_digit = sum_val % 11
    if first_digit < 2:
        first_digit = 0
    else:
        first_digit = 11 - first_digit
    
    if int(cnpj[12]) != first_digit:
        return False
    
    weights_2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    sum_val = sum(int(cnpj[i]) * weights_2[i] for i in range(13))
    second_digit = sum_val % 11
    if second_digit < 2:
        second_digit = 0
    else:
        second_digit = 11 - second_digit
    
    if int(cnpj[13]) != second_digit:
        return False
    
    return True


def format_cpf(cpf: str) -> str:
    """Format CPF with mask (XXX.XXX.XXX-XX)."""
    cpf = re.sub(r'[^0-9]', '', cpf)
    if len(cpf) != 11:
        return cpf
    return f"{cpf[:3]}.{cpf[3:6]}.{cpf[6:9]}-{cpf[9:]}"


def format_cnpj(cnpj: str) -> str:
    """Format CNPJ with mask (XX.XXX.XXX/XXXX-XX)."""
    cnpj = re.sub(r'[^0-9]', '', cnpj)
    if len(cnpj) != 14:
        return cnpj
    return f"{cnpj[:2]}.{cnpj[2:5]}.{cnpj[5:8]}/{cnpj[8:12]}-{cnpj[12:]}"


def format_placa(placa: str) -> str:
    """Format Brazilian vehicle plate (XXX-XXXX or XXX-XXXX)."""
    placa = placa.upper().replace('-', '').replace(' ', '')
    if len(placa) != 7:
        return placa
    return f"{placa[:3]}-{placa[3:]}"


def validate_placa(placa: str) -> bool:
    """
    Validate Brazilian vehicle plate.
    Supports both old format (XXX-XXXX) and Mercosul (XXX0XX).
    """
    if not placa:
        return False
    
    placa = placa.upper().replace('-', '').replace(' ', '')
    
    if len(placa) != 7:
        return False
    
    old_format = re.match(r'^[A-Z]{3}[0-9]{4}$', placa)
    mercosul_format = re.match(r'^[A-Z]{3}[0-9][A-Z][0-9]{2}$', placa)
    
    return bool(old_format or mercosul_format)


def validate_cep(cep: str) -> bool:
    """Validate Brazilian CEP (XXXXX-XXX or XXXXXXXX)."""
    if not cep:
        return False
    
    cep = re.sub(r'[^0-9]', '', cep)
    
    return len(cep) == 8


def validate_phone(phone: str) -> bool:
    """Validate Brazilian phone number."""
    if not phone:
        return False
    
    phone = re.sub(r'[^0-9]', '', phone)
    
    if len(phone) < 10 or len(phone) > 13:
        return False
    
    return True


def validate_renavam(renavam: str) -> bool:
    """Validate Brazilian RENAVAM code."""
    if not renavam:
        return False
    
    renavam = re.sub(r'[^0-9]', '', renavam)
    
    if len(renavam) != 11:
        return False
    
    weights = [3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    sum_val = sum(int(renavam[i]) * weights[i] for i in range(10))
    
    check_digit = (sum_val * 10) % 11
    if check_digit == 10:
        check_digit = 0
    
    return int(renavam[10]) == check_digit


def validate_chassi(chassi: str) -> bool:
    """
    Validate vehicle chassis number (VIN - Vehicle Identification Number).
    Brazilian vehicles use 17-character VIN.
    """
    if not chassi:
        return False
    
    chassi = chassi.upper().replace(' ', '').replace('-', '')
    
    if len(chassi) != 17:
        return False
    
    if chassi[0] not in 'ABCDEFGHJKLMNPRSTUVWXYZ':
        return False
    
    if chassi[0] in '34567':
        if chassi[6] not in 'ABCDEFGHJKLMNPRSTUVWXYZ0123456789':
            return False
    
    return True
