from compile import *
arrays = {}

def init(name, val, s, quiet=False, readonly=False):
    arrays[name] = [s, readonly, []]
    variables[name + "RVALUE"] = gen_var()
    if readonly:
        arrays[name][2] = val
        return
    if not quiet: bprint(f'"INITIALIZING ARRAY {name}"')
    for i in range(s):
        if not quiet and i % 100 == 0: bprint(f'"{i}/{s}"')
        v = gen_var()
        plet(v, val[i] if i < len(val) else 0)
        arrays[name][2].append(v)
    if not quiet: bprint('"DONE"')

def read(name, i):
    lbl = gen_label()
    let(name + "RET", lbl)
    goto(f"{name}READ+({i})*2")
    label(lbl)

def write(name, i, v):
    lbl = gen_label()
    let(name + "WVALUE", v)
    let(name + "RET", lbl)
    goto(f"{name}WRITE+({i})*2")
    label(lbl)

def gen():
    for name, (s, readonly, a) in arrays.items():
        if name + "RET" not in variables: continue
        label(name + "READ")
        r = variables[name + "RET"]
        rv = variables[name + "RVALUE"]
        for i in range(s):
            plet(rv, a[i])
            pgoto(r)
        if not readonly and name + "WVALUE" in variables:
            w = variables[name + "WVALUE"]
            label(name + "WRITE")
            for i in range(s):
                plet(a[i], w)
                pgoto(r)
