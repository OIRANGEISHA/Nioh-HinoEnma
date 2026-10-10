"""Assemble the project's decimal Intel sources with an explicit radix.

The Windows Keystone 0.9.2 engine can reuse an indeterminate default radix;
ks_option also selects radix16 even for the plain Intel syntax option.
Encode every numeric token explicitly before calling that engine. The hook
source, labels, register names and generated runtime payloads stay unchanged.
"""
import re

from keystone import (Ks as _Keystone, KS_ARCH_X86, KS_MODE_64,
                      KS_OPT_SYNTAX_INTEL, KS_OPT_SYNTAX_RADIX16)

_NUMBER = re.compile(r'(?<![\w{}])(?:0x[0-9A-Fa-f]+|[0-9]+)(?![\w{}])')


class Ks(_Keystone):
    """Project-only x64 Intel assembler; bare source integers are decimal."""
    def __init__(self, arch, mode):
        if arch != KS_ARCH_X86 or mode != KS_MODE_64:
            raise ValueError('Project source requires x64 Intel assembly')
        super().__init__(arch, mode)
        self.syntax = KS_OPT_SYNTAX_INTEL | KS_OPT_SYNTAX_RADIX16

    def asm(self, source, addr=0, as_bytes=False):
        if isinstance(source, bytes):
            source = source.decode('ascii')
        explicit = _NUMBER.sub(
            lambda m: hex(int(m.group(0), 16 if m.group(0).lower().startswith('0x') else 10)),
            source)
        return super().asm(explicit, addr, as_bytes)
