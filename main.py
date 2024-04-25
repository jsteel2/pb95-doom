#!/usr/bin/env python3

from elftools.elf.elffile import ELFFile
from compile import *
import arr
import sys

def get_reg(reg):
    if reg == 0: return 0
    return arr.arrays["REGS"][2][reg]

def set_reg(reg, val):
    if reg == 0: let("LITTER", 0)
    else: plet(get_reg(reg), val)

def sign_extend(val, bits):
    if val >= 1 << (bits - 1): return val + ((1 << 32) - (1 << bits))
    return val

def pbsign_extend(x, bits):
    return f"(({x})+{(1 << 32) - (1 << bits)}*{shr(x, bits - 1)})"

def to_signed(x):
    return f"(({x})+(-1)*({1 << 32}*{shr(x, 31)}))"

def pshl(x, by):
    return f"(({x})*{by})"

def shl(x, by):
    return f"(({x})*{1 << by})"

def pshr(x, by):
    return f"(({x})/{by}+{variables['POINT5']}+{variables['POW2OF52']}+(-1)*{variables['POW2OF52']}+(-1))"

def shr(x, by):
    return f"(({x})/{1 << by}+{variables['POINT5']}+{variables['POW2OF52']}+(-1)*{variables['POW2OF52']}+(-1))"

def snip(x, bits):
    return f"(({x})+(-1)*{shl(shr(x, bits), bits)})"

def bitlut(lut, rd, x, y):
    defer()
    arr.read(lut, f"{snip(x, 8)}+{shl(snip(y, 8), 8)}")
    plet(variables["REGTEMP"], variables[lut + "RVALUE"])
    arr.read(lut, f"{snip(shr(x, 8), 8)}+{shl(snip(shr(y, 8), 8), 8)}")
    plet(variables["REGTEMP"], f"{variables['REGTEMP']}+{shl(variables[lut + 'RVALUE'], 8)}")
    arr.read(lut, f"{snip(shr(x, 16), 8)}+{shl(snip(shr(y, 16), 8), 8)}")
    plet(variables["REGTEMP"], f"{variables['REGTEMP']}+{shl(variables[lut + 'RVALUE'], 16)}")
    arr.read(lut, f"{snip(shr(x, 24), 8)}+{shl(snip(shr(y, 24), 8), 8)}")
    set_reg(rd, f"{variables['REGTEMP']}+{shl(variables[lut + 'RVALUE'], 24)}")
    defer_end()

def gen_instrs(instrs, ram_begin):
    pc = 0
    rom = label('ROM')
    while pc < len(instrs):
        instr = instrs[pc] | (instrs[pc + 1] << 8) | (instrs[pc + 2] << 16) | (instrs[pc + 3] << 24)
        pc = pc + 4
        opcode = instr & 0b1111111
        rd = (instr >> 7) & 0b11111
        funct3 = (instr >> 12) & 0b111
        rs1 = (instr >> 15) & 0b11111
        rs2 = (instr >> 20) & 0b11111
        uimm = instr & 0b11111111111111111111000000000000
        imm = sign_extend(instr >> 20, 12)
        bimm = sign_extend((rd & 0b11110) | ((rd & 1) << 11) | ((instr >> 20) & 0b11111100000) | ((instr >> 19) & 0b1000000000000), 13)
        simm = sign_extend(rd | ((instr >> 20) & 0b111111100000), 12)
        jimm = sign_extend((instr & 0b11111111000000000000) | ((instr >> 20) & 0b11111111110) | ((instr >> 9) & 0b100000000000) | ((instr >> 11) & 0b100000000000000000000), 21)
        shamt = (instr >> 20) & 0b11111
        shtype = funct7 = instr >> 25
        match opcode:
            case 0x03: # load
                match funct3:
                    case 0: # lb
                        defer()
                        arr.read("RAM", snip(f"{get_reg(rs1)}+{imm}", 32) + f"+(-{ram_begin})")
                        set_reg(rd, pbsign_extend(variables["RAMRVALUE"], 8))
                        defer_end()
                    case 1: # lh
                        defer()
                        arr.read("RAM", snip(f"{get_reg(rs1)}+{imm}", 32) + f"+(-{ram_begin})")
                        plet(variables["REGTEMP"], variables["RAMRVALUE"])
                        arr.read("RAM", snip(f"{get_reg(rs1)}+{imm}+1", 32) + f"+(-{ram_begin})")
                        set_reg(rd, pbsign_extend(f"{variables['REGTEMP']}+{shl(variables['RAMRVALUE'], 8)}", 16))
                        defer_end()
                    case 2: # lw
                        defer()
                        arr.read("RAM", snip(f"{get_reg(rs1)}+{imm}", 32) + f"+(-{ram_begin})")
                        plet(variables["REGTEMP"], variables["RAMRVALUE"])
                        arr.read("RAM", snip(f"{get_reg(rs1)}+{imm}+1", 32) + f"+(-{ram_begin})")
                        plet(variables["REGTEMP"], f"{variables['REGTEMP']}+{shl(variables['RAMRVALUE'], 8)}")
                        arr.read("RAM", snip(f"{get_reg(rs1)}+{imm}+2", 32) + f"+(-{ram_begin})")
                        plet(variables["REGTEMP"], f"{variables['REGTEMP']}+{shl(variables['RAMRVALUE'], 16)}")
                        arr.read("RAM", snip(f"{get_reg(rs1)}+{imm}+3", 32) + f"+(-{ram_begin})")
                        set_reg(rd, f"{variables['REGTEMP']}+{shl(variables['RAMRVALUE'], 24)}")
                        defer_end()
                    case 4: # lbu
                        if rs1 == 0 and imm == 1:
                            pbinput(get_reg(rd))
                        else:
                            defer()
                            arr.read("RAM", snip(f"{get_reg(rs1)}+{imm}", 32) + f"+(-{ram_begin})")
                            set_reg(rd, variables["RAMRVALUE"])
                            defer_end()
                    case 5: # lhu
                        defer()
                        arr.read("RAM", snip(f"{get_reg(rs1)}+{imm}", 32) + f"+(-{ram_begin})")
                        plet(variables["REGTEMP"], variables["RAMRVALUE"])
                        arr.read("RAM", snip(f"{get_reg(rs1)}+{imm}+1", 32) + f"+(-{ram_begin})")
                        set_reg(rd, f"{variables['REGTEMP']}+{shl(variables['RAMRVALUE'], 8)}")
                        defer_end()
                    case _:
                        raise Exception("Unimplemened insruction %x" % instr)
            case 0x13: # immediate
                match funct3:
                    case 0: # addi
                        set_reg(rd, snip(f"{get_reg(rs1)}+{imm}", 32))
                    case 1: # slli
                        set_reg(rd, snip(shl(get_reg(rs1), shamt), 32))
                    case 2: # slti
                        defer()
                        plet(variables["REGTEMP"], 0)
                        pbif(f"{to_signed(get_reg(rs1))}<{to_signed(imm)}", f"{variables['REGTEMP']}=1")
                        set_reg(rd, variables["REGTEMP"])
                        defer_end()
                    case 3: # sltiu
                        defer()
                        plet(variables["REGTEMP"], 0)
                        pbif(f"{get_reg(rs1)}<{imm}", f"{variables['REGTEMP']}=1")
                        set_reg(rd, variables["REGTEMP"])
                        defer_end()
                    case 4: # xori
                        # TODO: This can be optimized further
                        bitlut("XORLUT", rd, get_reg(rs1), imm)
                    case 5: # srxi
                        if shtype == 0: # srli
                            set_reg(rd, shr(get_reg(rs1), shamt))
                        else: # srai
                            set_reg(rd, f"{shr(get_reg(rs1), shamt)}+{shr(get_reg(rs1), 31)}*{(~((1 << (32 - shamt)) - 1)) & ((1 << 32) - 1)}")
                    case 6: # ori
                        # TODO: This can be optimized further
                        bitlut("ORLUT", rd, get_reg(rs1), imm)
                    case 7: # andi
                        # TODO: This can be optimized further
                        bitlut("ANDLUT", rd, get_reg(rs1), imm)
                    case _:
                        raise Exception("Unimplemened insruction %x" % instr)
            case 0x17: # auipc
                set_reg(rd, (pc - 4 + uimm) & ((1 << 32) - 1))
            case 0x23: # store
                match funct3:
                    case 0: # sb
                        if rs1 == 0 and simm == 1:
                            bprint(snip(get_reg(rs2), 8))
                        else:
                            defer()
                            arr.write("RAM", snip(f"{get_reg(rs1)}+{simm}", 32) + f"+(-{ram_begin})", snip(get_reg(rs2), 8))
                            defer_end()
                    case 1: # sh
                        defer()
                        arr.write("RAM", snip(f"{get_reg(rs1)}+{simm}", 32) + f"+(-{ram_begin})", snip(get_reg(rs2), 8))
                        arr.write("RAM", snip(f"{get_reg(rs1)}+{simm}+1", 32) + f"+(-{ram_begin})", snip(shr(get_reg(rs2), 8), 8))
                        defer_end()
                    case 2: # sw
                        defer()
                        arr.write("RAM", snip(f"{get_reg(rs1)}+{simm}", 32) + f"+(-{ram_begin})", snip(get_reg(rs2), 8))
                        arr.write("RAM", snip(f"{get_reg(rs1)}+{simm}+1", 32) + f"+(-{ram_begin})", snip(shr(get_reg(rs2), 8), 8))
                        arr.write("RAM", snip(f"{get_reg(rs1)}+{simm}+2", 32) + f"+(-{ram_begin})", snip(shr(get_reg(rs2), 16), 8))
                        arr.write("RAM", snip(f"{get_reg(rs1)}+{simm}+3", 32) + f"+(-{ram_begin})", shr(get_reg(rs2), 24))
                        defer_end()
                    case _:
                        raise Exception("Unimplemened insruction %x" % instr)
            case 0x33: # register
                match funct3:
                    case 0: # add/sub
                        if funct7 == 0: # add
                            set_reg(rd, snip(f"{get_reg(rs1)}+{get_reg(rs2)}", 32))
                        else: # sub
                            set_reg(rd, snip(f"{get_reg(rs1)}+(-1)*{get_reg(rs2)}", 32))
                    case 1: # sll
                        defer()
                        arr.read("POWLUT", snip(get_reg(rs2), 5))
                        set_reg(rd, pshl(get_reg(rs1), variables["POWLUTRVALUE"]))
                        defer_end()
                    case 2: # slt
                        defer()
                        plet(variables["REGTEMP"], 0)
                        pbif(f"{to_signed(get_reg(rs1))}<{to_signed(get_reg(rs2))}", f"{variables['REGTEMP']}=1")
                        set_reg(rd, variables["REGTEMP"])
                        defer_end()
                    case 3: # sltu
                        defer()
                        plet(variables["REGTEMP"], 0)
                        pbif(f"{get_reg(rs1)}<{get_reg(rs2)}", f"{variables['REGTEMP']}=1")
                        set_reg(rd, variables["REGTEMP"])
                        defer_end()
                    case 4: # xor
                        bitlut("XORLUT", rd, get_reg(rs1), get_reg(rs2))
                    case 5: # srx
                        if shtype == 0: # srl
                            defer()
                            arr.read("POWLUT", snip(get_reg(rs2), 5))
                            set_reg(rd, pshr(get_reg(rs1), variables["POWLUTRVALUE"]))
                            defer_end()
                        else: # sra
                            defer()
                            arr.read("POWLUT", snip(get_reg(rs2), 5))
                            arr.read("SRALUT", snip(get_reg(rs2), 5)) # TODO: This is stupid...
                            set_reg(rd, f"{pshr(get_reg(rs1), variables['POWLUTRVALUE'])}+{shr(get_reg(rs1), 31)}*{variables['SRALUTRVALUE']}")
                            defer_end()
                    case 6: # or
                        bitlut("ORLUT", rd, get_reg(rs1), get_reg(rs2))
                    case 7: # and
                        bitlut("ANDLUT", rd, get_reg(rs1), get_reg(rs2))
                    case _:
                        raise Exception("Unimplemened insruction %x" % instr)
            case 0x37: # lui
                set_reg(rd, uimm)
            case 0x63:  # branch
                if bimm % 4 != 0: raise Exception("I sure hope this never happens!")
                match funct3:
                    case 0: # beq
                        bif(f"{get_reg(rs1)}=={get_reg(rs2)}", f"GOTO {rom + ((pc - 4 + bimm) & ((1 << 32) - 1)) // 4}")
                    case 1: # bne
                        defer()
                        bif(f"{get_reg(rs1)}=={get_reg(rs2)}", f"GOTO {rom + pc // 4}")
                        goto(rom + ((pc - 4 + bimm) & ((1 << 32) - 1)) // 4)
                        defer_end()
                    case 4: # blt
                        bif(f"{to_signed(get_reg(rs1))}<{to_signed(get_reg(rs2))}", f"GOTO {rom + ((pc - 4 + bimm) & ((1 << 32) - 1)) // 4}")
                    case 5: # bge
                        bif(f"{to_signed(get_reg(rs1))}>({to_signed(get_reg(rs2))}+(-1))", f"GOTO {rom + ((pc - 4 + bimm) & ((1 << 32) - 1)) // 4}")
                    case 6: # bltu
                        bif(f"{get_reg(rs1)}<{get_reg(rs2)}", f"GOTO {rom + ((pc - 4 + bimm) & ((1 << 32) - 1)) // 4}")
                    case 7: # bgeu
                        bif(f"{get_reg(rs1)}>({get_reg(rs2)}+(-1))", f"GOTO {rom + ((pc - 4 + bimm) & ((1 << 32) - 1)) // 4}")
                    case _:
                        raise Exception("Unimplemened insruction %x" % instr)
            case 0x67: # jalr
                if imm % 4 != 0: raise Exception("I sure hope this never happens!")
                defer()
                plet(variables["REGTEMP"], get_reg(rs1))
                set_reg(rd, pc)
                goto(f"{rom}+" + snip(f"REGTEMP+{imm}", 32) + "/4")
                defer_end()
            case 0x6f: # jal
                if jimm % 4 != 0: raise Exception("I sure hope this never happens!")
                defer()
                set_reg(rd, pc)
                goto(rom + ((pc - 4 + jimm) & ((1 << 32) - 1)) // 4)
                defer_end()
            case 0x73: # ebreak and friends
                let("LITTER", 0)
            case _:
                raise Exception("Unimplemened insruction %x" % instr)

def gen(elf):
    arr.init("REGS", [0] * 32, 32)
    let("POINT5", 0.5000000001)
    let("POW2OF52", 2 ** 52)
    let("REGTEMP", 0)

    arr.init("ORLUT", [(x & 0xff) | (x >> 8) for x in range(1 << 16)], 1 << 16, readonly=True)
    arr.init("XORLUT", [(x & 0xff) ^ (x >> 8) for x in range(1 << 16)], 1 << 16, readonly=True)
    arr.init("ANDLUT", [(x & 0xff) & (x >> 8) for x in range(1 << 16)], 1 << 16, readonly=True)
    arr.init("POWLUT", [1 << x for x in range(32)], 32, readonly=True)
    arr.init("SRALUT", [~((1 << (32 - x)) - 1) & ((1 << 32) - 1) for x in range(32)], 32, readonly=True)
    # TODO: duplicate the LUTs like with defer() so we can get rid of the LUTRET lines

    for sec in ELFFile(elf).iter_sections():
        if sec.name == ".text":
            text = sec.data()
        elif sec.name == ".data": # TODO: put readonly memory in a different section so we can make a readonly array for it, which takes up a third of the space
            arr.init("RAM", sec.data(), 12 * 1024 * 1024) # TODO: mess with the doom source to reduce ram usage
            ram_begin = sec.header.sh_addr

    gen_instrs(text, ram_begin)

    arr.gen()
    defer_gen()
    label("END")
    bprint('"GOODBYE"')
    compile()

if __name__ == "__main__":
    gen(open(sys.argv[1], "rb"))
