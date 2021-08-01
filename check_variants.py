import sys
import pysam
from collections import defaultdict

sample = sys.argv[1]
positions = sys.argv[2]
output = sys.argv[3]

counts = dict()


for line in positions.split(','):
    line = line.strip()
    counts[int(line)-1] = defaultdict(int)

samfile = pysam.AlignmentFile(sample, "rb")

for read in samfile.fetch():
    for qp, rp in read.get_aligned_pairs(matches_only=True):
        if rp in counts:
            counts[rp][read.query_sequence[qp]] +=1

# PAIR TUPLES
btuples = defaultdict(int)
for fread in samfile.fetch():
    reads = [fread]
    try:
        reads.append(samfile.mate(fread))
    except ValueError:
        pass
    bases =  {key:'-' for key in counts}
    warnings = []
    for read in reads:
        for qp, rp in read.get_aligned_pairs(matches_only=True):
            if rp in bases:
                if bases[rp]=='-':
                    bases[rp] = read.query_sequence[qp]
                elif bases[rp]!=read.query_sequence[qp]:
                    warnings.append((rp, bases[rp], read.query_sequence[qp]))

    for rp, rb, qb in warnings:
        bases[rp] = '-'

    pos_sort = sorted(counts.keys())
    btuples[''.join([bases[key] for key in pos_sort])] += 3-len(reads)

samfile.close()

with open(output,'w') as f:
    for p, d in counts.items():
        f.write(str(p+1) + ':' + str(dict(d))+ '\n')
    for bt, c in btuples.items():
        if bt.count('-') == 0:
            f.write(bt + ':' + str(c//2) + '\n')

