# Extra code for AN.exe (Alien Nations / Die Völker, GOG v2.05).
#
# The bytes are written into the unused zero padding at the end of the .text section
# (VA 0x4a4690..0x4a5000); anpatch/exe.py extends the section's VirtualSize to cover it.
# Every entry point is pinned with .org so its address stays the same when other parts change.
# The addresses are mirrored in anpatch/exe.py (CAVE_*); tools/build_cave.py checks they match.
#
# Build:  python3 tools/build_cave.py   (needs GNU as/ld/objcopy with i386 support)
#
# Game globals used:
#   0x4af3a4 / 0x4af3a8   current screen width / height
#   0x4b39e8              text buffer used for the resolution label
#   0x4b44e8 / 0x4b44ec   scroll velocity x / y   (in 1/16 px per tick after the patch)
#   0x4b3ead              1 while multiplayer chat input is active
#   0x4b393e              1 while the in-game options menu is open
#   0x4b7250 / 0x4b7254   sub-pixel scroll remainders (new, in the extended .data section)
# Imports used (IAT slots): 0x4a51d0 wsprintfA, 0x4a523c GetKeyState

.intel_syntax noprefix
.text
.globl _start
_start:

# --- 0x4a4690: next_res -------------------------------------------------------------
# Resolution toggle: returns the entry after the current width x height in restab
# (wraps around; unknown current mode -> first entry). out: esi = width, edi = height
  .org 0x000, 0xcc
next_res:
  mov eax, dword ptr ds:0x4af3a4
  mov edx, dword ptr ds:0x4af3a8
  xor ecx, ecx
1: cmp eax, dword ptr [restab + ecx*8]
  jne 2f
  cmp edx, dword ptr [restab + ecx*8 + 4]
  je 3f
2: inc ecx
  cmp ecx, dword ptr [nres]
  jb 1b
  mov ecx, -1
3: inc ecx
  cmp ecx, dword ptr [nres]
  jb 4f
  xor ecx, ecx
4: mov esi, dword ptr [restab + ecx*8]
  mov edi, dword ptr [restab + ecx*8 + 4]
  ret

# --- 0x4a46e0: label ----------------------------------------------------------------
# Writes "<width> X <height>" into the label buffer; returns edi = buffer
# (the caller then copies the string onto itself, which is harmless).
  .org 0x050, 0xcc
label:
  push dword ptr ds:0x4af3a8
  push dword ptr ds:0x4af3a4
  push offset fmt
  push 0x4b39e8
  call dword ptr ds:0x4a51d0          # wsprintfA (cdecl)
  add esp, 16
  mov edi, 0x4b39e8
  ret

  .org 0x080, 0xcc
fmt: .asciz "%d X %d"

# --- 0x4a4720: resolution table -------------------------------------------------------
# Every width needs a matching INTERFACE<width> sidebar in Data/*/interface.gd
# (see anpatch/sidebar.py RESOLUTIONS). Widths must be unique.
  .org 0x090, 0xcc
nres: .long 6
restab:
  .long 800, 600
  .long 1024, 768
  .long 1280, 720
  .long 1600, 900
  .long 1920, 1080
  .long 2560, 1440
  .long 0,0, 0,0, 0,0, 0,0, 0,0, 0,0, 0,0, 0,0   # room for 8 more entries

# --- 0x4a47c0: scroll_move ----------------------------------------------------------
# Replaces "pos += velocity" in the scroll loop. Velocity is in 1/16 px, the remainder is
# carried over so slow speeds still move smoothly. in: ebx = view object, edi = velocity x
# Preserves eax (holds the current tick count in the caller).
  .org 0x130, 0xcc
scroll_move:
  push eax
  mov eax, dword ptr ds:0x4b7250
  add eax, edi
  mov ecx, eax
  sar ecx, 4
  and eax, 15
  mov dword ptr ds:0x4b7250, eax
  add dword ptr [ebx+0x1c], ecx
  mov eax, dword ptr ds:0x4b7254
  add eax, dword ptr ds:0x4b44ec
  mov ecx, eax
  sar ecx, 4
  and eax, 15
  mov dword ptr ds:0x4b7254, eax
  add dword ptr [ebx+0x20], ecx
  pop eax
  ret

# --- 0x4a4800 / 0x4a4850: zero_vx / zero_vy -----------------------------------------------
# Called where the mouse handler stops edge scrolling (mouse not at a screen edge).
# Only stop if no scroll key for that axis is held, so moving the mouse doesn't cancel
# keyboard scrolling. Preserves all registers.
  .org 0x170, 0xcc
zero_vx:
  pushad
  push 0x25                           # VK_LEFT
  call dword ptr ds:0x4a523c          # GetKeyState (stdcall)
  test ax, ax
  js 1f
  push 0x27                           # VK_RIGHT
  call dword ptr ds:0x4a523c
  test ax, ax
  js 1f
  push 0x41                           # 'A'
  call dword ptr ds:0x4a523c
  test ax, ax
  js 1f
  push 0x44                           # 'D'
  call dword ptr ds:0x4a523c
  test ax, ax
  js 1f
  mov dword ptr ds:0x4b44e8, 0
1: popad
  ret

  .org 0x1c0, 0xcc
zero_vy:
  pushad
  push 0x26                           # VK_UP
  call dword ptr ds:0x4a523c
  test ax, ax
  js 1f
  push 0x28                           # VK_DOWN
  call dword ptr ds:0x4a523c
  test ax, ax
  js 1f
  push 0x57                           # 'W'
  call dword ptr ds:0x4a523c
  test ax, ax
  js 1f
  push 0x53                           # 'S'
  call dword ptr ds:0x4a523c
  test ax, ax
  js 1f
  mov dword ptr ds:0x4b44ec, 0
1: popad
  ret

# --- 0x4a48a0 / 0x4a48c0: key_down_map / key_up_map --------------------------------------
# Replace "mov eax,[esi+0xc]; add eax,-0x21" (WM_KEYDOWN) and "...; add eax,-0x13" (WM_KEYUP)
# at the start of the game's key dispatch. W/A/S/D are turned into the arrow keys.
# On key-down this is skipped while chat input or the options menu is active.
  .org 0x210, 0xcc
key_down_map:
  mov eax, dword ptr [esi+0xc]
  cmp byte ptr ds:0x4b3ead, 0
  jne 9f
  cmp byte ptr ds:0x4b393e, 0
  jne 9f
  call wasd_map
9: sub eax, 0x21
  ret

  .org 0x230, 0xcc
key_up_map:
  mov eax, dword ptr [esi+0xc]
  call wasd_map
  sub eax, 0x13
  ret

# --- 0x4a48d0: wasd_map ---------------------------------------------------------------
# eax: 'W' -> VK_UP, 'A' -> VK_LEFT, 'S' -> VK_DOWN, 'D' -> VK_RIGHT, anything else unchanged
  .org 0x240, 0xcc
wasd_map:
  cmp eax, 0x57
  jne 1f
  mov eax, 0x26
  ret
1: cmp eax, 0x41
  jne 2f
  mov eax, 0x25
  ret
2: cmp eax, 0x53
  jne 3f
  mov eax, 0x28
  ret
3: cmp eax, 0x44
  jne 4f
  mov eax, 0x27
4: ret
