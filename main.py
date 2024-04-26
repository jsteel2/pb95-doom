#!/usr/bin/env python3

from elftools.elf.elffile import ELFFile
import colorsys
from compile import *
import arr
import sys
import math

# TODO: more efficient rounding

def get_reg(reg):
    if reg == 0: return 0
    return arr.arrays["REGS"][2][reg]

def set_reg(reg, val):
    if reg == 0: let("LITTER", 0)
    else: plet(get_reg(reg), val)

def sign_extend(val, bits):
    if val >= 1 << (bits - 1): return val + ((1 << 32) - (1 << bits))
    return val

def to_signed(val):
    if val >= 1 << 31: return val - (1 << 32)
    return val

def pbto_signed(val):
    pbif(f"{val}>{(1 << 31) - 1}", f"{val}={val}+(-{1 << 32})")

def pbsign_extend(val, bits):
    pbif(f"{val}>{(1 << (bits - 1)) - 1}", f"{val}={val}+{(1 << 32) - (1 << bits)}")

def pshl(x, by):
    return f"(({x})*{by})"

def shl(x, by):
    return f"(({x})*{1 << by})"

def shr(d, val, by):
    plet(variables[d], f"{val}/{1 << by}+{variables['POW2OF52']}+(-{variables['POW2OF52']})")
    pbif(f"{variables[d]}>({val}/{1 << by})", f"{variables[d]}={variables[d]}+(-1)")

def pshr(d, val, by):
    plet(variables[d], f"{val}/{by}+{variables['POW2OF52']}+(-{variables['POW2OF52']})")
    pbif(f"{variables[d]}>({val}/{by})", f"{variables[d]}={variables[d]}+(-1)")

def snip(x, y, by):
    return f"(({x})+(-1)*{shl(y, by)})"

def bitlut(lut, rd, x, y):
    defer()
    shr("LITTER", x, 8)
    shr("LITTER2", y, 8)
    arr.read(lut, f"{snip(x, variables['LITTER'], 8)}+{shl(snip(y, variables['LITTER2'], 8), 8)}")
    plet(variables["REGTEMP"], variables[lut + "RVALUE"])
    shr("LITTER3", variables["LITTER"], 8)
    shr("LITTER4", variables["LITTER2"], 8)
    arr.read(lut, f"{snip(variables['LITTER'], variables['LITTER3'], 8)}+{shl(snip(variables['LITTER2'], variables['LITTER4'], 8), 8)}")
    plet(variables["REGTEMP"], f"{variables['REGTEMP']}+{shl(variables[lut + 'RVALUE'], 8)}")
    shr("LITTER", variables["LITTER3"], 8)
    shr("LITTER2", variables["LITTER4"], 8)
    arr.read(lut, f"{snip(variables['LITTER3'], variables['LITTER'], 8)}+{shl(snip(variables['LITTER4'], variables['LITTER2'], 8), 8)}")
    plet(variables["REGTEMP"], f"{variables['REGTEMP']}+{shl(variables[lut + 'RVALUE'], 16)}")
    arr.read(lut, f"{variables['LITTER']}+{shl(variables['LITTER2'], 8)}")
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
                        plet(variables["LITTER"], f"{get_reg(rs1)}+{imm}")
                        pbif(f"{variables['LITTER']}>{((1 << 32) - 1)}", f"{variables['LITTER']}={variables['LITTER']}+(-{1 << 32})")
                        arr.read("RAM", f"{variables['LITTER']}+(-{ram_begin})")
                        set_reg(rd, variables["RAMRVALUE"])
                        pbsign_extend(get_reg(rd), 8)
                        defer_end()
                    case 1: # lh
                        defer()
                        plet(variables["LITTER"], f"{get_reg(rs1)}+{imm}")
                        pbif(f"{variables['LITTER']}>{((1 << 32) - 1)}", f"{variables['LITTER']}={variables['LITTER']}+(-{1 << 32})")
                        arr.read("RAM", f"{variables['LITTER']}+(-{ram_begin})")
                        plet(variables["REGTEMP"], variables["RAMRVALUE"])
                        arr.read("RAM", f"{variables['LITTER']}+1+(-{ram_begin})")
                        set_reg(rd, f"{variables['REGTEMP']}+{shl(variables['RAMRVALUE'], 8)}")
                        pbsign_extend(get_reg(rd), 16)
                        defer_end()
                    case 2: # lw
                        defer()
                        plet(variables["LITTER"], f"{get_reg(rs1)}+{imm}")
                        pbif(f"{variables['LITTER']}>{((1 << 32) - 1)}", f"{variables['LITTER']}={variables['LITTER']}+(-{1 << 32})")
                        arr.read("RAM", f"{variables['LITTER']}+(-{ram_begin})")
                        plet(variables["REGTEMP"], variables["RAMRVALUE"])
                        arr.read("RAM", f"{variables['LITTER']}+1+(-{ram_begin})")
                        plet(variables["REGTEMP"], f"{variables['REGTEMP']}+{shl(variables['RAMRVALUE'], 8)}")
                        arr.read("RAM", f"{variables['LITTER']}+2+(-{ram_begin})")
                        plet(variables["REGTEMP"], f"{variables['REGTEMP']}+{shl(variables['RAMRVALUE'], 16)}")
                        arr.read("RAM", f"{variables['LITTER']}+3+(-{ram_begin})")
                        set_reg(rd, f"{variables['REGTEMP']}+{shl(variables['RAMRVALUE'], 24)}")
                        defer_end()
                    case 4: # lbu
                        defer()
                        if rs1 == 0 and imm == 1:
                            bprint('"INPUT:"')
                            pbinput(get_reg(rd))
                        else:
                            plet(variables["LITTER"], f"{get_reg(rs1)}+{imm}")
                            pbif(f"{variables['LITTER']}>{((1 << 32) - 1)}", f"{variables['LITTER']}={variables['LITTER']}+(-{1 << 32})")
                            arr.read("RAM", f"{variables['LITTER']}+(-{ram_begin})")
                            set_reg(rd, variables["RAMRVALUE"])
                        defer_end()
                    case 5: # lhu
                        defer()
                        plet(variables["LITTER"], f"{get_reg(rs1)}+{imm}")
                        pbif(f"{variables['LITTER']}>{((1 << 32) - 1)}", f"{variables['LITTER']}={variables['LITTER']}+(-{1 << 32})")
                        arr.read("RAM", f"{variables['LITTER']}+(-{ram_begin})")
                        plet(variables["REGTEMP"], variables["RAMRVALUE"])
                        arr.read("RAM", f"{variables['LITTER']}+1+(-{ram_begin})")
                        set_reg(rd, f"{variables['REGTEMP']}+{shl(variables['RAMRVALUE'], 8)}")
                        defer_end()
                    case _:
                        raise Exception("Unimplemened insruction %x" % instr)
            case 0x13: # immediate
                match funct3:
                    case 0: # addi
                        if imm == 0:
                            set_reg(rd, get_reg(rs1))
                        else:
                            defer()
                            set_reg(rd, f"{get_reg(rs1)}+{imm}")
                            pbif(f"{get_reg(rd)}>{((1 << 32) - 1)}", f"{get_reg(rd)}={get_reg(rd)}+(-{1 << 32})")
                            defer_end()
                    case 1: # slli
                        defer()
                        for i in range(shamt):
                            set_reg(rd, shl(get_reg(rs1) if i == 0 else get_reg(rd), 1))
                            pbif(f"{get_reg(rd)}>{((1 << 32) - 1)}", f"{get_reg(rd)}={get_reg(rd)}+(-{1 << 32})")
                        defer_end()
                    case 2: # slti
                        defer()
                        plet(variables["REGTEMP"], 0)
                        plet(variables["LITTER"], get_reg(rs1))
                        pbto_signed(variables["LITTER"])
                        pbif(f"{variables['LITTER']}<({to_signed(imm)})", f"{variables['REGTEMP']}=1")
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
                        defer()
                        if shtype == 0: # srli
                            shr("REGTEMP", get_reg(rs1), shamt)
                            set_reg(rd, variables["REGTEMP"])
                        else: # srai
                            shr("REGTEMP", get_reg(rs1), shamt)
                            pbif(f"{get_reg(rs1)}>{(1 << 31) - 1}", f"{variables['REGTEMP']}={variables['REGTEMP']}+{(~((1 << (32 - shamt)) - 1)) & ((1 << 32) - 1)}")
                            set_reg(rd, variables["REGTEMP"])
                        defer_end()
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
                        defer()
                        if rs1 == 0 and simm == 1:
                            shr("LITTER", get_reg(rs2), 8)
                            bprint(snip(get_reg(rs2), variables["LITTER"], 8))
                        elif rs1 == 0 and simm == 2:
                            pfor(variables["LITTER"], 1, 200)
                            pfor(variables["LITTER2"], 1, 320)
                            arr.read("RAM", f"{get_reg(rs2)}+({variables['LITTER']}+(-1))*320+({variables['LITTER2']}+(-1))+(-{ram_begin})")
                            arr.read("PALETTE", variables["RAMRVALUE"])
                            pcolor(variables["PALETTERVALUE"])
                            pplot(variables["LITTER2"], variables["LITTER"])
                            pnext(variables["LITTER2"])
                            pnext(variables["LITTER"])
                        else:
                            plet(variables["LITTER"], f"{get_reg(rs1)}+{simm}")
                            pbif(f"{variables['LITTER']}>{((1 << 32) - 1)}", f"{variables['LITTER']}={variables['LITTER']}+(-{1 << 32})")
                            shr("LITTER2", get_reg(rs2), 8)
                            arr.write("RAM", f"{variables['LITTER']}+(-{ram_begin})", snip(get_reg(rs2), variables["LITTER2"], 8))
                        defer_end()
                    case 1: # sh
                        defer()
                        plet(variables["LITTER"], f"{get_reg(rs1)}+{simm}")
                        pbif(f"{variables['LITTER']}>{((1 << 32) - 1)}", f"{variables['LITTER']}={variables['LITTER']}+(-{1 << 32})")
                        shr("LITTER2", get_reg(rs2), 8)
                        arr.write("RAM", f"{variables['LITTER']}+(-{ram_begin})", snip(get_reg(rs2), variables["LITTER2"], 8))
                        shr("LITTER3", variables["LITTER2"], 8)
                        arr.write("RAM", f"{variables['LITTER']}+1+(-{ram_begin})", snip(variables["LITTER2"], variables["LITTER3"], 8))
                        defer_end()
                    case 2: # sw
                        defer()
                        plet(variables["LITTER"], f"{get_reg(rs1)}+{simm}")
                        pbif(f"{variables['LITTER']}>{((1 << 32) - 1)}", f"{variables['LITTER']}={variables['LITTER']}+(-{1 << 32})")
                        shr("LITTER2", get_reg(rs2), 8)
                        arr.write("RAM", f"{variables['LITTER']}+(-{ram_begin})", snip(get_reg(rs2), variables["LITTER2"], 8))
                        shr("LITTER3", variables["LITTER2"], 8)
                        arr.write("RAM", f"{variables['LITTER']}+1+(-{ram_begin})", snip(variables["LITTER2"], variables["LITTER3"], 8))
                        shr("LITTER2", variables["LITTER3"], 8)
                        arr.write("RAM", f"{variables['LITTER']}+2+(-{ram_begin})", snip(variables["LITTER3"], variables["LITTER2"], 8))
                        arr.write("RAM", f"{variables['LITTER']}+3+(-{ram_begin})", variables["LITTER2"])
                        defer_end()
                    case _:
                        raise Exception("Unimplemened insruction %x" % instr)
            case 0x33: # register
                match funct3:
                    case 0: # add/sub
                        defer()
                        if funct7 == 0: # add
                            set_reg(rd, f"{get_reg(rs1)}+{get_reg(rs2)}")
                            pbif(f"{get_reg(rd)}>{((1 << 32) - 1)}", f"{get_reg(rd)}={get_reg(rd)}+(-{1 << 32})")
                        else: # sub
                            set_reg(rd, f"{get_reg(rs1)}+({(1 << 32) - 1}+(-{get_reg(rs2)}))+1")
                            pbif(f"{get_reg(rd)}>{((1 << 32) - 1)}", f"{get_reg(rd)}={get_reg(rd)}+(-{1 << 32})")
                        defer_end()
                    case 1: # sll
                        defer()
                        shr("LITTER", get_reg(rs2), 5)
                        plet(variables["REGTEMP"], get_reg(rs1))
                        pfor(variables["LITTER2"], 1, snip(get_reg(rs2), variables["LITTER"], 5))
                        plet(variables["REGTEMP"], shl(variables["REGTEMP"], 1))
                        pbif(f"{variables['REGTEMP']}>{(1 << 32) - 1}", f"{variables['REGTEMP']}={variables['REGTEMP']}+(-{1 << 32})")
                        pnext(variables["LITTER2"])
                        set_reg(rd, variables["REGTEMP"])
                        defer_end()
                    case 2: # slt
                        defer()
                        plet(variables["REGTEMP"], 0)
                        plet(variables["LITTER"], get_reg(rs1))
                        pbto_signed(variables["LITTER"])
                        plet(variables["LITTER2"], get_reg(rs2))
                        pbto_signed(variables["LITTER2"])
                        pbif(f"{variables['LITTER']}<{variables['LITTER2']}", f"{variables['REGTEMP']}=1")
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
                            shr("LITTER", get_reg(rs2), 5)
                            arr.read("POWLUT", snip(get_reg(rs2), variables["LITTER"], 5))
                            pshr("REGTEMP", get_reg(rs1), variables["POWLUTRVALUE"])
                            set_reg(rd, variables["REGTEMP"])
                            defer_end()
                        else: # sra
                            defer()
                            shr("LITTER", get_reg(rs2), 5)
                            arr.read("POWLUT", snip(get_reg(rs2), variables["LITTER"], 5))
                            arr.read("SRALUT", snip(get_reg(rs2), variables["LITTER"], 5)) # TODO: This is stupid...
                            pshr("REGTEMP", get_reg(rs1), variables["POWLUTRVALUE"])
                            pbif(f"{get_reg(rs1)}>{(1 << 31) - 1}", f"{variables['REGTEMP']}={variables['REGTEMP']}+{variables['SRALUTRVALUE']}")
                            set_reg(rd, variables["REGTEMP"])
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
                        defer()
                        plet(variables["LITTER"], get_reg(rs1))
                        pbto_signed(variables["LITTER"])
                        plet(variables["LITTER2"], get_reg(rs2))
                        pbto_signed(variables["LITTER2"])
                        bif(f"{variables['LITTER']}<{variables['LITTER2']}", f"GOTO {rom + ((pc - 4 + bimm) & ((1 << 32) - 1)) // 4}")
                        defer_end()
                    case 5: # bge
                        defer()
                        plet(variables["LITTER"], get_reg(rs1))
                        pbto_signed(variables["LITTER"])
                        plet(variables["LITTER2"], get_reg(rs2))
                        pbto_signed(variables["LITTER2"])
                        bif(f"{variables['LITTER']}>({variables['LITTER2']}+(-1))", f"GOTO {rom + ((pc - 4 + bimm) & ((1 << 32) - 1)) // 4}")
                        defer_end()
                    case 6: # bltu
                        bif(f"{get_reg(rs1)}<{get_reg(rs2)}", f"GOTO {rom + ((pc - 4 + bimm) & ((1 << 32) - 1)) // 4}")
                    case 7: # bgeu
                        bif(f"{get_reg(rs1)}>({get_reg(rs2)}+(-1))", f"GOTO {rom + ((pc - 4 + bimm) & ((1 << 32) - 1)) // 4}")
                    case _:
                        raise Exception("Unimplemened insruction %x" % instr)
            case 0x67: # jalr
                if imm % 4 != 0: raise Exception("I sure hope this never happens!")
                defer()
                plet(variables["REGTEMP"], f"{get_reg(rs1)}+{imm}")
                pbif(f"{variables['REGTEMP']}>{((1 << 32) - 1)}", f"{variables['REGTEMP']}={variables['REGTEMP']}+(-{1 << 32})")
                set_reg(rd, pc)
                goto(f"{rom}+{variables['REGTEMP']}/4")
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
    let("LITTER", 0)
    let("LITTER2", 0)
    let("LITTER3", 0)
    let("LITTER4", 0)
    let("REGTEMP", 0)
    let("POW2OF52", 2 ** 52)

    arr.init("ORLUT", [(x & 0xff) | (x >> 8) for x in range(1 << 16)], 1 << 16, readonly=True)
    arr.init("XORLUT", [(x & 0xff) ^ (x >> 8) for x in range(1 << 16)], 1 << 16, readonly=True)
    arr.init("ANDLUT", [(x & 0xff) & (x >> 8) for x in range(1 << 16)], 1 << 16, readonly=True)
    arr.init("POWLUT", [1 << x for x in range(32)], 32, readonly=True)
    arr.init("SRALUT", [~((1 << (32 - x)) - 1) & ((1 << 32) - 1) for x in range(32)], 32, readonly=True)
    # TODO: duplicate the LUTs like with defer() so we can get rid of the LUTRET lines

    doom_palette = [
        0x000000,
        0x1f170b,
        0x170f07,
        0x4b4b4b,
        0xffffff,
        0x1b1b1b,
        0x131313,
        0x0b0b0b,
        0x070707,
        0x2f371f,
        0x232b0f,
        0x171f07,
        0x0f1700,
        0x4f3b2b,
        0x473323,
        0x3f2b1b,
        0xffb7b7,
        0xf7abab,
        0xf3a3a3,
        0xeb9797,
        0xe78f8f,
        0xdf8787,
        0xdb7b7b,
        0xd37373,
        0xcb6b6b,
        0xc76363,
        0xbf5b5b,
        0xbb5757,
        0xb34f4f,
        0xaf4747,
        0xa73f3f,
        0xa33b3b,
        0x9b3333,
        0x972f2f,
        0x8f2b2b,
        0x8b2323,
        0x831f1f,
        0x7f1b1b,
        0x771717,
        0x731313,
        0x6b0f0f,
        0x670b0b,
        0x5f0707,
        0x5b0707,
        0x530707,
        0x4f0000,
        0x470000,
        0x430000,
        0xffebdf,
        0xffe3d3,
        0xffdbc7,
        0xffd3bb,
        0xffcfb3,
        0xffc7a7,
        0xffbf9b,
        0xffbb93,
        0xffb383,
        0xf7ab7b,
        0xefa373,
        0xe79b6b,
        0xdf9363,
        0xd78b5b,
        0xcf8353,
        0xcb7f4f,
        0xbf7b4b,
        0xb37347,
        0xab6f43,
        0xa36b3f,
        0x9b633b,
        0x8f5f37,
        0x875733,
        0x7f532f,
        0x774f2b,
        0x6b4727,
        0x5f4323,
        0x533f1f,
        0x4b371b,
        0x3f2f17,
        0x332b13,
        0x2b230f,
        0xefefef,
        0xe7e7e7,
        0xdfdfdf,
        0xdbdbdb,
        0xd3d3d3,
        0xcbcbcb,
        0xc7c7c7,
        0xbfbfbf,
        0xb7b7b7,
        0xb3b3b3,
        0xababab,
        0xa7a7a7,
        0x9f9f9f,
        0x979797,
        0x939393,
        0x8b8b8b,
        0x838383,
        0x7f7f7f,
        0x777777,
        0x6f6f6f,
        0x6b6b6b,
        0x636363,
        0x5b5b5b,
        0x575757,
        0x4f4f4f,
        0x474747,
        0x434343,
        0x3b3b3b,
        0x373737,
        0x2f2f2f,
        0x272727,
        0x232323,
        0x77ff6f,
        0x6fef67,
        0x67df5f,
        0x5fcf57,
        0x5bbf4f,
        0x53af47,
        0x4b9f3f,
        0x439337,
        0x3f832f,
        0x37732b,
        0x2f6323,
        0x27531b,
        0x1f4317,
        0x17330f,
        0x13230b,
        0x0b1707,
        0xbfa78f,
        0xb79f87,
        0xaf977f,
        0xa78f77,
        0x9f876f,
        0x9b7f6b,
        0x937b63,
        0x8b735b,
        0x836b57,
        0x7b634f,
        0x775f4b,
        0x6f5743,
        0x67533f,
        0x5f4b37,
        0x574333,
        0x533f2f,
        0x9f8363,
        0x8f7753,
        0x836b4b,
        0x775f3f,
        0x675333,
        0x5b472b,
        0x4f3b23,
        0x43331b,
        0x7b7f63,
        0x6f7357,
        0x676b4f,
        0x5b6347,
        0x53573b,
        0x474f33,
        0x3f472b,
        0x373f27,
        0xffff73,
        0xebdb57,
        0xd7bb43,
        0xc39b2f,
        0xaf7b1f,
        0x9b5b13,
        0x874307,
        0x732b00,
        0xffdbdb,
        0xffbbbb,
        0xff9b9b,
        0xff7b7b,
        0xff5f5f,
        0xff3f3f,
        0xff1f1f,
        0xff0000,
        0xef0000,
        0xe30000,
        0xd70000,
        0xcb0000,
        0xbf0000,
        0xb30000,
        0xa70000,
        0x9b0000,
        0x8b0000,
        0x7f0000,
        0x730000,
        0x670000,
        0x5b0000,
        0xe7e7ff,
        0xc7c7ff,
        0xababff,
        0x8f8fff,
        0x7373ff,
        0x5353ff,
        0x3737ff,
        0x1b1bff,
        0x0000ff,
        0x0000e3,
        0x0000cb,
        0x0000b3,
        0x00009b,
        0x000083,
        0x00006b,
        0x000053,
        0xffebdb,
        0xffd7bb,
        0xffc79b,
        0xffb37b,
        0xffa35b,
        0xff8f3b,
        0xff7f1b,
        0xf37317,
        0xeb6f0f,
        0xdf670f,
        0xd75f0b,
        0xcb5707,
        0xc34f00,
        0xb74700,
        0xaf4300,
        0xffffd7,
        0xffffb3,
        0xffff8f,
        0xffff6b,
        0xffff47,
        0xffff23,
        0xffff00,
        0xa73f00,
        0x9f3700,
        0x932f00,
        0x872300,
        0x4f3b27,
        0x432f1b,
        0x372313,
        0x2f1b0b,
        0x000047,
        0x00003b,
        0x00002f,
        0x000023,
        0x000017,
        0x00000b,
        0xff9f43,
        0xffe74b,
        0xff7bff,
        0xff00ff,
        0xcf00cf,
        0x9f009b,
        0x6f006b,
        0xa76b6b,
        0,
        0,
        0,
        0,
        0,
        0,
        0
    ]

    pyrus_rgb = [[0, 0, 0],[0,0,128],[0,128,0],[0,128,128],[128,0,0],[128,0,128],[128,128,0], [170,170,170],[85,85,85],[0,0,255],[0,255,0],[0,255,255],[255,0,0],[255,0,255],[255,255,0],[255,255,255]]

    pyrus_hsv = [colorsys.rgb_to_hsv(x[0] / 255, x[1] / 255, x[2] / 255) for x in pyrus_rgb]

    pyrus_palette = []
    for color in doom_palette:
        r = color >> 16
        g = (color >> 8) & 0xff
        b = color & 0xff
        h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
        d = {}
        for i, a in enumerate(pyrus_hsv):
            dh = min(abs(h-a[0]),360-abs(h-a[0])) /180.0
            ds = abs(s-a[1])
            dv = abs(v-a[2])/255
            distance = math.sqrt(dh*dh+ds*ds+dv*dv)
            d[i+1] = distance
        m = 9
        kk = 1
        for k, v in d.items():
            if v < m:
                m = v
                kk = k

        pyrus_palette.append(kk)

    # TODO: make the array function set the COLOR instead of a variable
    arr.init("PALETTE", pyrus_palette, 256, readonly=True)

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
