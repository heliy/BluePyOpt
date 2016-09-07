#coding:UTF-8

def read_p(fname, delimiter="\t"):
    lines = []
    for line in open(fname).read().splitlines():
        if len(line) <= 2:
            continue
        if line[0] == '*' or line[0] == '/':
            continue
        lines.append(line.split(delimiter))
    return lines

PMAP = {
    'soma': 1,
    'axon': 2,
    'dend': 3,
    'd': 3,
    }

def maps(lines, pre_map=PMAP):
    term_map = {}
    mae_map = {}
    type_map = {}
    for i, line in enumerate(lines):
        print(line)
        term_map[line[0]] = i
        if line[1] == 'none':
            mae_map[line[0]] = -1
        elif line[1] == '.':
            mae_map[line[0]] = i-1
        else:
            mae_map[line[0]] = term_map[line[1]]
        type_map[line[0]] = -1
        for key in pre_map:
            if key in line[0]:
                type_map[line[0]] = pre_map[key]
                break
    return term_map, mae_map, type_map

def write_swc(fname, ps, maps):
    lines = []
    term_map, mae_map, type_map = maps
    for p in ps:
        label = p[0]
        line = "%d %d %s %s %s %f %d" % (term_map[label], type_map[label],
                                         p[2], p[3], p[4], float(p[5])/2, mae_map[label])
        lines.append(line)
    with open(fname, 'w') as f:
        f.write("\n".join(lines))


def main(rname, wname, delimiter):
    lines = read_p(rname, delimiter)
    ms = maps(lines)
    write_swc(wname, lines, ms)

if __name__ == '__main__':
    import sys
    if len(sys.argv) == 3:
        sys.argv.append("\t")
    elif len(sys.argv) != 4:
        print('''
from gensis .p file to .swc morphology file.

usage:
python p2swc.py gensis_filename.p swc_filename.swc

        ''')
        exit()
    main(sys.argv[1], sys.argv[2], sys.argv[3])
    
