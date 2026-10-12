"""Player-owned package references, retained at spawn and released after cleanup.

Native helpers expand the actual template's dependencies symmetrically. The
private bounded pool stores frozen owners, so later selection/capture changes
and overlapping old/new actors cannot move or drop a living owner's reference.
"""
from copy import deepcopy
from hinoenma_abyss_actions import SAVES, RESTORES, pointer
from hinoenma_abyss_assembly import assemble

CODE_OFFSET = 0x51000
ACQUIRE_OFFSET = 0x800
DATA_OFFSET = 0x53000
DATA_DELTA = DATA_OFFSET-0xF000
DATA_SIZE = 0x2000
SLOT_COUNT = 64
ROW_OFFSET = 0x100
ROW_SIZE = 0x40
STATE_EMPTY, STATE_ACQUIRING, STATE_ACTIVE = 0, 1, 2
STATE_UNCERTAIN, STATE_RELEASING, STATE_CONSUMED, STATE_DEFERRED = 3, 4, 5, 6

def lock(prefix):
    # No native call is made with this lock held; a scan is bounded to 64 rows.
    return f'''mov rsi, {{data}}
add rsi, 0x{DATA_DELTA:X}
{prefix}_wait:
xor eax, eax
mov edx, 1
lock cmpxchg dword ptr [rsi], edx
je {prefix}_locked
pause
jmp {prefix}_wait
{prefix}_locked:
'''

def unlock():
    return 'mov dword ptr [rsi], 0\n'

def acquire_asm():
    return SAVES+'''mov dword ptr [rsp+0xB4], 0
mov qword ptr [rsp+0x80], rcx
'''+pointer('rcx', 'ap_acquire_done')+'''mov edx, dword ptr [rcx]
cmp edx, 0x58E5E
je ap_acquire_header
cmp edx, 0x51BE1
jne ap_acquire_done
ap_acquire_header:
cmp dword ptr [rcx+4], 0x10000
jne ap_acquire_done
mov r11, {data}
cmp qword ptr [r11+0x10], rcx
jne ap_acquire_done
mov dword ptr [rsp+0x88], edx
'''+lock('ap_acquire')+'''lea rbx, [rsi+0x100]
xor edi, edi
xor r8d, r8d
ap_acquire_scan:
mov eax, dword ptr [rbx]
test eax, eax
je ap_acquire_free
cmp eax, 5
je ap_acquire_free
mov rax, qword ptr [rsp+0x80]
cmp qword ptr [rbx+8], rax
jne ap_acquire_next
mov eax, dword ptr [rsp+0x88]
cmp dword ptr [rbx+4], eax
jne ap_acquire_conflict
cmp dword ptr [rbx], 2
jne ap_acquire_conflict
inc qword ptr [rbx+0x20]
inc qword ptr [rsi+0x10]
mov dword ptr [rsp+0xB4], 1
jmp ap_acquire_unlock_done
ap_acquire_free:
test rdi, rdi
jne ap_acquire_next
mov rdi, rbx
ap_acquire_next:
add rbx, 0x40
inc r8d
cmp r8d, 64
jb ap_acquire_scan
test rdi, rdi
je ap_acquire_full
mov rbx, rdi
mov qword ptr [rsp+0x90], rbx
mov dword ptr [rbx], 1
mov eax, dword ptr [rsp+0x88]
mov dword ptr [rbx+4], eax
mov rax, qword ptr [rsp+0x80]
mov qword ptr [rbx+8], rax
mov qword ptr [rbx+0x10], 0
mov qword ptr [rbx+0x18], 1
mov qword ptr [rbx+0x20], 0
mov qword ptr [rbx+0x28], 0
mov r11, {data}
mov eax, dword ptr [r11+0x1C]
mov dword ptr [rbx+0x30], eax
mov dword ptr [rbx+0x34], 0
inc qword ptr [rsi+0x38]
mov rax, qword ptr [rsi+0x38]
mov qword ptr [rbx+0x38], rax
inc qword ptr [rsi+8]
inc qword ptr [rsi+0x40]
'''+unlock()+'''mov ecx, dword ptr [rsp+0x88]
mov edx, ecx
call {abyss_native_retain}
mov qword ptr [rsp+0x98], rax
'''+lock('ap_acquire_return')+'''mov rbx, qword ptr [rsp+0x90]
mov rax, qword ptr [rsp+0x98]
mov qword ptr [rbx+0x10], rax
cmp dword ptr [rbx], 6
je ap_acquire_deferred_release
cmp dword ptr [rbx], 1
jne ap_acquire_conflict
test rax, rax
je ap_acquire_uncertain
mov dword ptr [rbx], 2
mov dword ptr [rsp+0xB4], 1
jmp ap_acquire_unlock_done
ap_acquire_uncertain:
mov dword ptr [rbx], 3
inc qword ptr [rsi+0x30]
jmp ap_acquire_unlock_done
ap_acquire_deferred_release:
mov dword ptr [rbx], 4
inc qword ptr [rbx+0x28]
inc qword ptr [rsi+0x18]
'''+unlock()+'''mov ecx, dword ptr [rsp+0x88]
mov edx, ecx
call {abyss_native_release}
'''+lock('ap_acquire_release_return')+'''mov rbx, qword ptr [rsp+0x90]
mov dword ptr [rbx], 5
dec qword ptr [rsi+0x40]
jmp ap_acquire_unlock_done
ap_acquire_full:
inc qword ptr [rsi+0x28]
jmp ap_acquire_unlock_done
ap_acquire_conflict:
inc qword ptr [rsi+0x20]
ap_acquire_unlock_done:
'''+unlock()+'''ap_acquire_done:
mov eax, dword ptr [rsp+0xB4]
mov qword ptr [rsp+0x108], rax
'''+RESTORES+'ret\n'

def release_asm():
    # Native interior JMP arrives with RSP aligned; adapt to the CALL ABI save.
    return 'lea rsp, [rsp-8]\n'+SAVES+'''mov qword ptr [rsp+0x80], rdi
'''+lock('ap_cleanup')+'''lea rbx, [rsi+0x100]
xor r8d, r8d
ap_cleanup_scan:
mov eax, dword ptr [rbx]
test eax, eax
je ap_cleanup_next
cmp eax, 5
je ap_cleanup_next
mov rax, qword ptr [rsp+0x80]
cmp qword ptr [rbx+8], rax
jne ap_cleanup_next
mov eax, dword ptr [rbx]
cmp eax, 1
je ap_cleanup_defer
cmp eax, 2
je ap_cleanup_release
cmp eax, 3
je ap_cleanup_release
jmp ap_cleanup_unlock_done
ap_cleanup_next:
add rbx, 0x40
inc r8d
cmp r8d, 64
jb ap_cleanup_scan
jmp ap_cleanup_unlock_done
ap_cleanup_defer:
mov dword ptr [rbx], 6
inc qword ptr [rsi+0x48]
jmp ap_cleanup_unlock_done
ap_cleanup_release:
mov qword ptr [rsp+0x90], rbx
mov eax, dword ptr [rbx+4]
mov dword ptr [rsp+0x88], eax
mov dword ptr [rbx], 4
inc qword ptr [rbx+0x28]
inc qword ptr [rsi+0x18]
'''+unlock()+'''mov ecx, dword ptr [rsp+0x88]
mov edx, ecx
call {abyss_native_release}
'''+lock('ap_cleanup_return')+'''mov rbx, qword ptr [rsp+0x90]
mov dword ptr [rbx], 5
dec qword ptr [rsi+0x40]
ap_cleanup_unlock_done:
'''+unlock()+RESTORES+'''lea rsp, [rsp+8]
mov rcx, qword ptr [rsi]
mov rdx, rdi
jmp {return}
'''

def cleanup_hook(plan):
    hook = dict(name='HE_PlayerResourceLifetimeCleanup', rva=0x753616,
        length=6, original='48 8B 0E 48 8B D7', code_offset=CODE_OFFSET,
        code_capacity=0x2000, asm=release_asm(),
        purpose='Release each frozen player resource ticket after component cleanup and before actor free')
    test = deepcopy(plan)
    test['hooks'] = [hook]
    size = len(assemble(test, 0x140000000, 0x144000000)[0]['payload'])
    if size > ACQUIRE_OFFSET:
        raise ValueError('Cleanup overlaps fixed acquire entry')
    hook['asm'] += '\n'+'.byte 0\n'*(ACQUIRE_OFFSET-size)+acquire_asm()
    return hook

def spawn_hook(old):
    hook = deepcopy(old)
    marker = 'inc dword ptr [r11+0x1C]\njmp {return}'
    if hook['asm'].count(marker) != 1:
        raise ValueError('Exact captured spawn boundary required')
    hook['asm'] = hook['asm'].replace(marker, '''inc dword ptr [r11+0x1C]
pushfq
push rax
push rcx
sub rsp, 0x28
mov rcx, rax
call {data} + 0x42800
add rsp, 0x28
pop rcx
pop rax
popfq
jmp {return}''')
    hook['purpose'] += '; retain actual Hino player dependencies once per surviving actor'
    return hook
