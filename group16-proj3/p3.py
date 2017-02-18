import csv
import sys


csvfilename = sys.argv[1]
minsup_rate = float(sys.argv[2])
minconf_rate = float(sys.argv[3])


csvfile = open(csvfilename, 'rb')
reader = csv.reader(csvfile)

rows = []
for row in reader:
	rows.append(row)

minsup = 1.0 * minsup_rate * len(rows)


num_rows = len(rows)
num_cols = len(rows[0])


encode_map = {}
cur_code = 1
for j in range(num_cols):
	for i in range(num_rows):
		if rows[i][j] in encode_map:
			rows[i][j] = encode_map[rows[i][j]]
		else:
			encode_map[rows[i][j]] = cur_code
			rows[i][j] = cur_code
			cur_code = cur_code + 1


encode_map_rev = {}
for s in encode_map:
	encode_map_rev[encode_map[s]] = s

all_encode = range(1,cur_code)

def contained_in_helper(a, b, idx_a, idx_b):
	if len(a) == idx_a:
		return True
	if len(b) == idx_b:
		return False
	if a[idx_a] == b[idx_b]:
		return contained_in_helper(a,b,idx_a+1,idx_b+1)
	else:
		return contained_in_helper(a,b,idx_a,idx_b+1)

# determine if list a is contained in list b, both are sorted
def contained_in(a, b):
	return contained_in_helper(a,b,0,0)

setof_lk = {}
setof_lk_support = {}

setof_lk[1] = []
setof_lk_support[1] = []

for i in all_encode:
	cnt = 0
	for r in rows:
		if contained_in([i],r):
			cnt = cnt + 1
	if cnt >= minsup:
		setof_lk[1].append([i])
		setof_lk_support[1].append(cnt)


def apripri_gen(prev_lk,k):
	lr = len(prev_lk)
	ck = []

	# join step
	for i in range(lr):
		for j in range(lr):
			flag = True
			for t in range(k - 2):
				if prev_lk[i][t] != prev_lk[j][t]:
					flag = False
					break
			if flag == True:
				if prev_lk[i][k-2] < prev_lk[j][k-2]:
					tmpl = list(prev_lk[i])
					tmpl.append(prev_lk[j][k-2])
					ck.append(tmpl)

	# prune step
	i = 0
	while i < len(ck):
		row = ck[i]
		for j in range(len(row)):
			tmp = row[j]
			row.pop(j)
			if row in prev_lk:
				row.insert(j,tmp)
			else:
				ck.pop(i)
				i = i - 1
				break
		i = i + 1

	return ck


k = 2
while len(setof_lk[k-1]) > 0:
	setof_lk[k] = []
	setof_lk_support[k] = []
	ck = apripri_gen(setof_lk[k-1],k)
	for c in ck:
		cnt = 0
		for r in rows:
			if contained_in(c,r):
				cnt = cnt + 1
		if cnt >= minsup:
			setof_lk[k].append(c)
			setof_lk_support[k].append(cnt)
	k = k + 1

k = k - 1



def get_support(lhs):
	k = len(lhs)
	l = len(setof_lk[k])
	for i in range(l):
		if contained_in(lhs,setof_lk[k][i]):
			return setof_lk_support[k][i]


all_support = []
all_conf = []

tmp_k = k

while k >= 1:
	l = len(setof_lk[k])
	for i in range(l):
		all_support.append([setof_lk[k][i],"{:.3f}".format(100.0*setof_lk_support[k][i]/len(rows))])
	k = k - 1

all_support.sort(key = lambda t: (float)(t[1]), reverse = True)


k = tmp_k
while k >= 2:
	l = len(setof_lk[k])
	for i in range(l):
		union_sup = setof_lk_support[k][i]
		r = setof_lk[k][i]
		for j in range(k):
			tmp = r[j]
			r.pop(j)
			lhs_sup = get_support(r)
			conf = 1.0*union_sup/lhs_sup
			if conf >= minconf_rate:
				all_conf.append([list(r),tmp,"{:.3f}".format(conf*100),"{:.3f}".format(100.0*union_sup/len(rows))])
			r.insert(j,tmp)
	k = k - 1

all_conf.sort(key = lambda t: float(t[2]), reverse = True)


def decode_stuff(input):
	l = 0
	try:
		l = len(input)
	except Exception as e:
		return encode_map_rev[input]

	for i in range(l):
		input[i] = decode_stuff(input[i])

	return input


for s in all_support:
	s[0] = decode_stuff(s[0])
	s[1] = str(s[1])+'%'

for s in all_conf:
	s[0] = decode_stuff(s[0])
	s[1] = decode_stuff(s[1])
	s[2] = str(s[2])+'%'
	s[3] = str(s[3])+'%'

target = open('output.txt', 'w')

target.write('\n')



target.write('==Frequent itemsets (min_sup=' + str("{:.3f}".format(minsup_rate*100.0)) + '%)\n')
for s in all_support:
	target.write('[')
	for i in range(len(s[0])):
		target.write(s[0][i])
		if i < len(s[0]) - 1:
			target.write(', ')
	target.write('], ')
	target.write(s[1])
	target.write('\n')

target.write('\n')

target.write('==High-confidence association rules (min_conf=' + str("{:.3f}".format(minconf_rate*100.0)) + '%)\n')

for s in all_conf:
	target.write('[')
	for i in range(len(s[0])):
		target.write(s[0][i])
		if i < len(s[0]) - 1:
			target.write(', ')
	target.write(']=>[')
	target.write(s[1])
	target.write('] (Conf: ')
	target.write(s[2])
	target.write(', Supp: ')
	target.write(s[3])
	target.write(')\n')

target.write('\n')

print '!!!Result has been written to output.txt!!!'






