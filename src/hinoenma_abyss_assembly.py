"""Small pure source assembler, shared by the portable Abyss source builders."""
import struct
from source_assembler import Ks, KS_ARCH_X86, KS_MODE_64

def assemble(plan, module_base, allocation):
    assembler = Ks(KS_ARCH_X86, KS_MODE_64)
    output = []
    for hook in plan['hooks']:
        site = module_base+hook['rva']
        target = allocation+hook['code_offset']
        values = {key: hex(module_base+rva) for key,rva in plan['targets'].items()}
        values.update(data=hex(allocation+plan['data_offset']), **{'return': hex(site+hook['length'])})
        payload = bytes(assembler.asm(hook['asm'].format(**values), target)[0])
        if len(payload) > hook['code_capacity']:
            raise ValueError('Code capacity exceeded: '+hook['name'])
        delta = target-site-5
        if not -(1<<31) <= delta < (1<<31):
            raise ValueError('Allocation outside rel32 range')
        output.append(dict(hook, site=site, target=target, payload=payload,
                           patched=b'\xE9'+struct.pack('<i', delta)+b'\x90'*(hook['length']-5)))
    return output
