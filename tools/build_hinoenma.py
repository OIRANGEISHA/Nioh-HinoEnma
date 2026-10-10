"""Pure public assembler compatibility for scoped menu source builders.

No game files, process readers, private verifiers or research data are imported.
"""
def assemble(plan, module_base, allocation):
    from build_profile import assemble as public_assemble
    return public_assemble(plan, module_base, allocation)
