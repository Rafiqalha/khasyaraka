"""
Cipher Service - Factory Pattern Implementation

Extensible cipher factory for Sandi Pramuka encryption/decryption.
"""

from abc import ABC, abstractmethod
from typing import Dict
from app.modules.cyber.models import SandiType


class BaseCipher(ABC):
    """Abstract base class for all cipher implementations"""
    
    def __init__(self, sandi_type: SandiType):
        self.sandi_type = sandi_type
    
    @abstractmethod
    def encrypt(self, text: str) -> str:
        """Encrypt plaintext to ciphertext"""
        pass
    
    @abstractmethod
    def decrypt(self, text: str) -> str:
        """Decrypt ciphertext to plaintext"""
        pass


class MorseCipher(BaseCipher):
    """Morse Code Cipher Implementation"""
    
    # Morse code dictionary
    MORSE_TO_TEXT: Dict[str, str] = {
        '.-': 'A', '-...': 'B', '-.-.': 'C', '-..': 'D', '.': 'E',
        '..-.': 'F', '--.': 'G', '....': 'H', '..': 'I', '.---': 'J',
        '-.-': 'K', '.-..': 'L', '--': 'M', '-.': 'N', '---': 'O',
        '.--.': 'P', '--.-': 'Q', '.-.': 'R', '...': 'S', '-': 'T',
        '..-': 'U', '...-': 'V', '.--': 'W', '-..-': 'X', '-.--': 'Y',
        '--..': 'Z',
        '-----': '0', '.----': '1', '..---': '2', '...--': '3',
        '....-': '4', '.....': '5', '-....': '6', '--...': '7',
        '---..': '8', '----.': '9',
        '.-.-.-': '.', '--..--': ',', '..--..': '?', '-.-.--': '!',
        '/': ' '  # Space separator
    }
    
    TEXT_TO_MORSE: Dict[str, str] = {v: k for k, v in MORSE_TO_TEXT.items()}
    
    def encrypt(self, text: str) -> str:
        """Convert text to Morse code"""
        result = []
        text_upper = text.upper()
        
        for char in text_upper:
            if char == ' ':
                result.append('/')
            elif char in self.TEXT_TO_MORSE:
                result.append(self.TEXT_TO_MORSE[char])
            else:
                result.append(char)  # Keep unknown characters
        
        return ' '.join(result)
    
    def decrypt(self, text: str) -> str:
        """Convert Morse code to text"""
        result = []
        # Split by spaces, but preserve '/' as word separator
        parts = text.replace('/', ' / ').split()
        
        for part in parts:
            if part == '/':
                result.append(' ')
            elif part in self.MORSE_TO_TEXT:
                result.append(self.MORSE_TO_TEXT[part])
            else:
                result.append(part)  # Keep unknown patterns
        
        return ''.join(result)


class AnRot13Cipher(BaseCipher):
    """AN/ROT13 Cipher Implementation (Caesar cipher with shift 13)"""
    
    ALPHABET = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
    
    def encrypt(self, text: str) -> str:
        """Encrypt using ROT13 (shift 13)"""
        result = []
        text_upper = text.upper()
        
        for char in text_upper:
            if char in self.ALPHABET:
                index = self.ALPHABET.index(char)
                shifted_index = (index + 13) % 26
                result.append(self.ALPHABET[shifted_index])
            else:
                result.append(char)  # Keep non-alphabetic characters
        
        return ''.join(result)
    
    def decrypt(self, text: str) -> str:
        """Decrypt ROT13 (same as encrypt, it's symmetric)"""
        return self.encrypt(text)  # ROT13 is self-reciprocal


class PlaceholderCipher(BaseCipher):
    """Placeholder cipher for unimplemented types"""
    
    def encrypt(self, text: str) -> str:
        """Placeholder encryption"""
        return f"[Not Implemented] ENCRYPT: {text}"
    
    def decrypt(self, text: str) -> str:
        """Placeholder decryption"""
        return f"[Not Implemented] DECRYPT: {text}"


class CipherFactory:
    """Factory class to create cipher instances based on codename"""
    
    _cipher_classes: Dict[str, type] = {
        'morse': MorseCipher,
        'an_rot13': AnRot13Cipher,
        # Add more cipher implementations here as they are developed
    }
    
    @classmethod
    def create_cipher(cls, sandi_type: SandiType) -> BaseCipher:
        """
        Create cipher instance based on sandi codename.
        
        Args:
            sandi_type: SandiType model instance
            
        Returns:
            BaseCipher instance
        """
        codename = sandi_type.codename.lower()
        
        cipher_class = cls._cipher_classes.get(codename, PlaceholderCipher)
        return cipher_class(sandi_type)
    
    @classmethod
    def register_cipher(cls, codename: str, cipher_class: type):
        """
        Register a new cipher implementation.
        
        Args:
            codename: Unique codename for the cipher
            cipher_class: Class that inherits from BaseCipher
        """
        if not issubclass(cipher_class, BaseCipher):
            raise ValueError(f"Cipher class must inherit from BaseCipher")
        cls._cipher_classes[codename.lower()] = cipher_class
