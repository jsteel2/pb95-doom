import re

PRINT = 0
LET = 1
GOTO = 2
IF = 3
INPUT = 4
DGOTO = 5
DLET = 6
DIF = 7

def increment_string(s):
    if not s: return "a"
    last_char = s[-1]
    if last_char == '9':
        return increment_string(s[:-1]) + 'a'
    elif last_char == 'Z':
        if len(s) == 1:
            return increment_string(s[:-1]) + 'a'
        else:
            return s[:-1] + '0'
    elif last_char == 'z':
        return s[:-1] + 'A'
    else:
        return s[:-1] + chr(ord(last_char) + 1)

lbl = 0
def gen_label():
    global lbl
    lbl += 1
    return f"CMPLBL{lbl}"

cur_var = ""
labels = {}
labels2 = {}
variables = {}
i = 1
i2 = 0
a = []
b = []
p1 = re.compile(r"([A-Za-z]+[A-Za-z0-9]*)(?=[^\"]*(?:\"[^\"]*\"[^\"]*)*$)")

def var_replace(x):
    if type(x) != str: return x
    def replace(x):
        try:
            return str(labels[x.group(1)])
        except KeyError:
            try: return variables[x.group(1)]
            except KeyError: return x.group(1)

    return re.sub(p1, replace, x)

def bprint(x):
    global i
    a.append((PRINT, x))
    i += 1

def gen_var():
    global cur_var
    cur_var = increment_string(cur_var)
    return cur_var

def plet(v, x):
    global i
    a.append((LET, v, x))
    i += 1

def label(x):
    labels[x] = i
    return i

def let(v, x):
    global i
    if v not in variables:
        n = gen_var()
        variables[v] = n
    else:
        n = variables[v]
    a.append((DLET, v, x))
    i += 1

def pgoto(x):
    global i
    a.append((GOTO, x))
    i += 1

def goto(x):
    global i
    a.append((DGOTO, x))
    i += 1

def pbif(cond, then):
    global i
    a.append((IF, cond, then))
    i += 1

def bif(cond, then):
    global i
    a.append((DIF, cond, then))
    i += 1

def pbinput(x):
    global i
    a.append((INPUT, x))
    i += 1

def defer():
    global a, b, i2, i, labels, labels2
    l = gen_label()
    goto(l)
    c = a
    a = b
    b = c
    c = labels
    labels = labels2
    labels2 = c
    c = i2
    i2 = i
    i = c
    label(l)

def defer_end():
    global a, b, i, i2, labels, labels2
    l = gen_label()
    goto(l)
    c = a
    a = b
    b = c
    c = labels
    labels = labels2
    labels2 = c
    c = i2
    i2 = i
    i = c
    label(l)

def defer_gen():
    global a
    a += b
    d = label("DEFERRED")
    for k, v in labels2.items():
        labels[k] = d + v

def compile():
    for i, x in enumerate(a):
        i += 1
        match x[0]:
            case 0: # PRINT (i dont feel like googling what a name capture is and why i cant do one!) (nvm i realized why its bitching, i should make it an enum anyway... whenever i get to it of course)
                if x[1][0] == '"': print(f'{i} PRINT {x[1]}')
                else: print(f'{i} PRINT {var_replace(x[1])}')
            case 1: # LET
                print(f'{i} LET {x[1]}={x[2]}')
            case 2: # GOTO
                print(f'{i} GOTO {x[1]}')
            case 3: # IF
                print(f'{i} IF {x[1]} THEN {x[2]}')
            case 4: # INPUT
                print(f'{i} INPUT {x[1]}')
            case 5: # DGOTO
                print(f'{i} GOTO {var_replace(x[1])}')
            case 6: # DLET
                print(f'{i} LET {variables[x[1]]}={var_replace(x[2])}')
            case 7: # DIF
                print(f'{i} IF {var_replace(x[1])} THEN {var_replace(x[2])}')
            case _: raise Exception(f"Unimplemented {x}")