"""Pin numeric meaning independently of Keystone's mutable default radix."""
from pathlib import Path
import struct
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from source_assembler import Ks, KS_ARCH_X86, KS_MODE_64


class NumericAssemblerTests(unittest.TestCase):
    def assemble(self, source, address=0):
        return bytes(Ks(KS_ARCH_X86, KS_MODE_64).asm(source, address)[0])

    def test_decimal_hundred_keeps_short_immediate(self):
        self.assertEqual(self.assemble('cmp eax, 100'), bytes.fromhex('83f864'))

    def test_explicit_hex_keeps_its_value(self):
        self.assertEqual(self.assemble('cmp eax, 0x100'), bytes.fromhex('3d00010000'))

    def test_inline_table_values_are_decimal(self):
        self.assertEqual(self.assemble('.byte 10,100,232,255'), bytes((10,100,232,255)))

    def test_signed_immediate(self):
        self.assertEqual(self.assemble('mov rax, -1'), bytes.fromhex('48c7c0ffffffff'))

    def test_identifiers_and_registers_keep_digit_suffixes(self):
        self.assertEqual(self.assemble('jmp label100\nnop\nlabel100:\nmov r8d, 100\nret'),
                         bytes.fromhex('eb019041b864000000c3'))

    def test_decimal_native_call_address(self):
        address, target = 0x144000000, 0x1408B0B10
        self.assertEqual(self.assemble(f'call {target}', address),
                         b'\xe8' + struct.pack('<i', target - address - 5))

    def test_fresh_and_reused_handles_are_stable(self):
        reusable = Ks(KS_ARCH_X86, KS_MODE_64)
        for _ in range(128):
            self.assertEqual(bytes(reusable.asm(b'cmp eax, 100', as_bytes=True)[0]),
                             bytes.fromhex('83f864'))
            self.assertEqual(self.assemble('cmp eax, 100'), bytes.fromhex('83f864'))


if __name__ == '__main__':
    unittest.main()
