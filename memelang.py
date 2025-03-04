#!/usr/bin/env python3

import sys
import os
import re
import glob
import psycopg2
from conf import *


###############################################################################
#                           CONSTANTS & GLOBALS
###############################################################################

THEBEG	= 2
ODD		= 1
EVEN	= 2
ALL		= 4

FUNC 	= 0
FORM 	= 1
OUT 	= 2

# FUNC
A		= 'A'
R		= 'R'
B		= 'B'
Q		= 'Q'
OR		= 'OR'

# FORM
KEY		= 3		# Integer ID or string KEY
IDENT	= 4		# integer ID
INTEGER	= 5		# Integer (not ID)
FLOAT	= 6		# Floating point number
STRING	= 7		# String

# Each operator and its meaning
OPR = {
	I[';']: [A, KEY, False],
	I[' ']: [A, KEY, False],
	I['>>']: [A, KEY, False],
	I['[']: [R, KEY, False],
	I[']']: [B, KEY, False],
	I['=#']: [Q, IDENT, '='],
	I['=$']: [Q, STRING, '="'],
	I['=.']: [Q, FLOAT, '='],
	I['>']: [Q, FLOAT, False],
	I['<']: [Q, FLOAT, False],
	I['>=']: [Q, FLOAT, False],
	I['<=']: [Q, FLOAT, False],
	I['!=']: [Q, FLOAT, False],
	I['|']: [OR, INTEGER, ''],
}

# For decode()
INCOMPLETE = 1
INTERMEDIATE = 2
COMPLETE = 3
OPSTR = {
	'!'  : [INCOMPLETE, False],
	'>'  : [INTERMEDIATE, I['>']],
	'<'  : [INTERMEDIATE, I['<']],
	'='  : [COMPLETE, I['=.']],
	'!=' : [COMPLETE, I['!=']],
	'>=' : [COMPLETE, I['>=']],
	'<=' : [COMPLETE, I['<=']],
	'['  : [COMPLETE, I['[']],
	']'  : [COMPLETE, I[']']],
	';'  : [COMPLETE, I[';']],
	' '  : [COMPLETE, I[' ']],
	'>>' : [COMPLETE, I['>>']],
}

SPLITOPR = r'([#;\[\]!><=\s])'
TFG = ('t', 'f', 'g')


###############################################################################
#                        DATABASE HELPER FUNCTIONS
###############################################################################

def select(query: str, params: list = []) -> list:
	with psycopg2.connect(f"host={DB['host']} dbname={DB['name']} user={DB['user']} password={DB['pswd']}") as conn:
		cursor = conn.cursor()
		cursor.execute(query, params)
		rows=cursor.fetchall()
		return [list(row) for row in rows]


def insert(query: str, params: list = []):
	with psycopg2.connect(f"host={DB['host']} dbname={DB['name']} user={DB['user']} password={DB['pswd']}") as conn:
		cursor = conn.cursor()
		cursor.execute(query, params)


def aggnum(col: str = 'aid', agg: str = 'MAX', table: str = None) -> int:
	if not table: table=DB['table_meme']
	result = select(f"SELECT {agg}({col}) FROM {table}")
	return int(0 if not result or not result[0] or not result[0][0] else result[0][0])


def selectin(cols: dict = {}, table: str = None) -> list:
	if not table: table=DB['table_name']

	conds = []
	params = []

	for col in cols:
		conds.append(f"{col} IN ("+ ','.join(['%s'] * len(cols[col])) +")")
		params.extend(cols[col])

	if not conds: return []

	return select(f"SELECT DISTINCT aid, bid, str FROM {table} WHERE " + ' AND '.join(conds), params)


# Conbine SQL and parameters into a string
def morfigy(sql: str, params: list) -> str:
    for param in params:
        rep = param.replace("'", "''") if isinstance(param, str) else str(param)
        sql = sql.replace("%s", rep, 1)
    return sql


# Input: string "John Adams"
# Output: lowercase underscored string "john_adams"
def slugify(string: str) -> str:
	return re.sub(r'__+', '_', re.sub(r'[^a-z0-9]', '_', string.lower())).strip('_')


###############################################################################
#                       MEMELANG STRINGING PROCESSING
###############################################################################

# Input: Memelang string
# Output: list of normalized Memelang strings, which should be joined by double quote (")
# This splits by quotes so quoted string aren't altered
def normalize(memestr: str, newline = False) -> list[str]:

	parts = re.split(r'(?<!\\)"', ';'+memestr.strip())
	for p,part in enumerate(parts):

		# quote
		if p%2==1:
			parts[p]=part
			continue

		# memelang code
		part = re.sub(r'[;\n]+', ';', part)					# Newlines are semicolons
		part = re.sub(r'\s+', ' ', part)					# Remove multiple spaces
		part = re.sub(r'\s*([#;!<>=]+)\s*', r'\1', part)	# Remove spaces around operators
		part = re.sub(r';+', ';', part)						# Remove multiple semicolons
		part = re.sub(r'(\.[0-9][1-9]*)0+', r'\1', part)	# Remove trailing zeros from floats
		part = re.sub(r';+$', '', part)						# Remove ending ;

		if newline: part = part.replace(";", "\n")
		parts[p]=part

	return parts


# Input: Memelang string "operator1operand1operator2operand2"
# Output: [operator1, operand1, operator2, operand2, ...]
def decode(memestr: str) -> list:

	memestr = re.sub(r'\s*//.*$', '', memestr, flags=re.MULTILINE) # Remove comments
	if len(memestr) == 0: raise Exception("Error: Empty query provided.")

	tokens = [I['id'], I['mix']]

	parts = normalize(memestr)

	for p,part in enumerate(parts):
		
		# quote
		if p%2==1:
			if tokens[-2] != I['=.']: raise Exception('Errant quote')
			tokens[-2]=I['=$']
			tokens[-1]=part
			continue

		strtoks = re.split(SPLITOPR, part)
		tlen = len(strtoks)
		t = 0
		while t<tlen:
			strtok=strtoks[t]

			# skip empty
			if len(strtok)==0: pass

			# operators
			elif OPSTR.get(strtok):

				completeness, operator = OPSTR[strtok]

				if completeness!=COMPLETE:
					if t<tlen-3 and OPSTR.get(strtok+strtoks[t+2]):
						completeness, operator = OPSTR[strtok+strtoks[t+2]]
						t+=2
					elif completeness==INCOMPLETE: raise Exception(f"Invalid strtok {strtok}")

				tokens += [operator, None]

			# key/int/float
			else:
				if tokens[-1]!=None: raise Exception(f'Sequence error {tokens[-2]} {tokens[-1]} {strtok}')
				if not re.search(r'[a-z0-9]', strtok): raise Exception(f"Unexpected '{strtok}' in {memestr}")

				if strtok in TFG: 
					tokens[-1]=I[strtok]
					if tokens[-2] not in (I['=.'],I['=#']): raise Exception('Compare sequence error')
					tokens[-2]=I['=#']
				elif '.' in strtok or OPR[tokens[-2]][FORM]==FLOAT: tokens[-1]=float(strtok)
				elif re.match(r'-?[0-9]+', strtok): tokens[-1]=int(strtok)
				else: tokens[-1]=strtok

			t+=1

	return tokens


# Input: tokens [operator1, operand1, operator2, operand2, ...]
# Output: Memelang string "operator1operand1operator2operand2"
def encode(tokens: list, encode_set=None) -> str:
	if not encode_set: encode_set={}
	memestr = ''

	olen=len(tokens)
	for o in range(THEBEG, olen, 2):
		if o>THEBEG or tokens[o]!=I[';']: memestr += K[tokens[o]] if OPR[tokens[o]][OUT]==False else OPR[tokens[o]][OUT]

		if OPR[tokens[o]][FORM]==STRING: memestr += str(tokens[o+1]) + '"'
		elif tokens[o+1] is None: pass
		elif OPR[tokens[o]][FORM]==IDENT: memestr += K[tokens[o+1]]
		elif OPR[tokens[o]][FORM] in (KEY, INTEGER, FLOAT): memestr += str(tokens[o+1])

	if encode_set.get('newline'): memestr=memestr.replace(";", "\n")

	return memestr


# Jump to next statement in tokens
def nxt(tokens: list, beg: int = 2) -> int:
	olen=len(tokens)
	if beg>olen-2: return -1
	elif tokens[beg]!=I[';']: raise Exception(f'Operator counting error at {beg} for {tokens[beg]}')

	end = beg
	while end<olen-2:
		end+=2
		if tokens[end]==I[';']: return end
	return olen


# Compare two Memelang token lists
# False is wildcard
# TO DO: This needs its own Metamemelang query language
def tokfit (atoks: list, btoks: list) -> bool:
	if len(atoks)!=len(btoks): return False
	for p, btok in enumerate(btoks):
		if btok==False: continue
		elif p%2==0 and isinstance(btok, str):
			if OPR[atoks[p]][FUNC]!=btok: return False
		elif atoks[p]!=btok: return False
	return True


# Input: list of integers [operator, operand]
# Output: one big integer
def compress(tokens: list) -> int:
	tlen = len(tokens)
	if tlen%2: raise ValueError('Odd token count')
	
	operator_bitmask = (1<<7)-1
	operand_bitmask = (1<<57)-1
	bigint = 1<<63 # Version 0001

	for t in range(tlen-1, 2, -2):
		operand, operator = tokens[t], tokens[t-1]
		
		if operand is None: operand=0
		elif OPR[operator][FORM]==FLOAT: operand=int(operand*1000000000)

		if not (0<=operator<127): raise ValueError(f'operator range {operator}')
		if not (-1<<56<=operand<1<<56): raise ValueError(f'operand range {operand}')
		bigint = (bigint<<64)|(((operator&operator_bitmask)<<57)|(operand&operand_bitmask))

	return bigint


# Input: one big integer
# Output: list of integers [operator, operand]
def decompress(bigint: int) -> list:
	if bigint<1<<63:raise ValueError
	pairs=[I['id'],I['id']]
	while bigint>1<<63:
		chunk = bigint&((1<<64)-1);
		bigint >>= 64
		operator = chunk>>57;
		operand = chunk&((1<<57)-1)
		if operand >= (1<<56): operand-=1<<57
		
		if operand==0: operand=None
		elif OPR[operator][FORM]==FLOAT: operand=float(operand/1000000000)

		pairs += [operator, operand]
	if bigint != (1<<63): raise ValueError('Version error')
	return pairs


###############################################################################
#                           KEY <-> ID CONVERSIONS
###############################################################################

# Input list of key strings ['george_washington', 'john_adams']
# Load key->aids in I and K caches
# I['john_adams']=123
# K[123]='john_adams'
def namecache(tokens: list, fld: str = 'str', name_table: str = None):
	if not tokens: return
	if not name_table: name_table=DB['table_name']

	if fld=='str': uncaches = list(set([tok for tok in tokens if isinstance(tok, str) and tok not in I]))
	elif fld=='aid': uncaches = list(set([tok for tok in tokens if isinstance(tok, int) and tok not in K]))
	else: raise Exception('fld')

	if not uncaches: return

	rows=selectin({'bid':[I['key']], fld:uncaches}, name_table)

	for row in rows:
		I[row[2]] = int(row[0])
		K[int(row[0])] = row[2]


def identify(tokens: list = [], mode: int = ALL, name_table: str = None) -> list:
	lookups=[]
	tokids=[
		I['id'] if mode!=ODD else tokens[0],
		I['id'] if mode!=EVEN else tokens[1],
	]

	tlen = len(tokens)
	if not tlen: return tokens

	for t in range(THEBEG, tlen, 2):
		operator, operand = tokens[t], tokens[t+1]
		if isinstance(operator, str): operator = I[operator]
		if isinstance(operand, str) and OPR[operator][FORM]==KEY:
			if operand.startswith('-'): operand = operand[1:]
			if not I.get(operand): lookups.append(operand)

	namecache(lookups, 'str', name_table)

	for t in range(THEBEG, tlen, 2):
		operator, operand = tokens[t], tokens[t+1]
		if isinstance(operator, str): operator = I[operator]
		tokids.append(operator if mode!=ODD else tokens[t])
		if operand is None: tokids.append(operand)
		elif mode!=EVEN and isinstance(operand, str) and OPR[operator][FORM]==KEY:
			tokids.append(I[operand] if not operand.startswith('-') else I[operand[1:]]*-1)
		else: tokids.append(operand)

	return tokids


def keyify(tokens: list, mode: int = ODD, name_table: str = None) -> list:
	lookups=[]
	tokeys=[
		I['key'] if mode!=ODD else tokens[0],
		I['key'] if mode!=EVEN else tokens[1],
	]

	tlen = len(tokens)
	if not tlen: return tokens

	for t in range(THEBEG, tlen, 2):
		operator, operand = tokens[t], tokens[t+1]
		if isinstance(operator, str): operator = I[operator]
		if isinstance(operand, int) and OPR[operator][FORM]==KEY:
			lookups.append(abs(operand))

	namecache(lookups, 'aid', name_table)

	for t in range(THEBEG, tlen, 2):
		operator, operand = tokens[t], tokens[t+1]
		if isinstance(operator, str): operator = I[operator]
		tokeys.append(K[operator] if mode!=ODD else tokens[t])
		if operand is None: tokeys.append(operand)
		elif mode!=EVEN and isinstance(operand, int) and OPR[operator][FORM]==KEY:
			tokeys.append(K[operand] if operand>=0 else '-'+K[-1*operand])
		else: tokeys.append(operand)

	return tokeys


###############################################################################
#                         MEMELANG -> SQL QUERIES
###############################################################################

# Input: Memelang query string
# Output: SQL query string
def querify(tokens: list, meme_table: str = None, name_table: str = None):
	if not meme_table: meme_table=DB['table_meme']
	if not name_table: name_table=DB['table_name']

	ctes	= []
	selects	= []
	params	= []

	beg = 0
	end = THEBEG
	while (end := nxt(tokens, (beg := end)))>0:
		cte, select, param = subquerify(tokens[beg:end], meme_table, len(ctes))
		ctes.extend(cte)
		selects.extend(select)
		params.extend(param)

	return ['WITH ' + ', '.join(ctes) + " SELECT string_agg(arbeq, ' ') AS arbeq FROM (" + ' UNION '.join(selects) + ')', params]


# Input: tokens
# Output: One SQL query string
def subquerify(tokens: list, meme_table: str = None, cte_beg: int = 0):
	if not meme_table: meme_table=DB['table_meme']
	qry_set = {I['all']: False}
	groups={'false':{0:[]},'get':{0:[]}, 'true':{}}

	skip = False
	gkey='true'
	gnum=1000

	o=0
	beg=o
	olen=len(tokens)
	for o in range(0, olen, 2):
		if OPR[tokens[o]][FUNC] == A and tokens[o+1] == I['qry']:
			qry_set[tokens[o+3]]=True
			skip=True

		# =f or =g
		elif tokens[o] == I['=#']:
			gnum=0
			if tokens[o+1] == I['f']: gkey='false'
			elif tokens[o+1] == I['g']: gkey='get'

		# Handle =tn (OR groups)
		elif tokens[o] == I['|']:
			gkey = 'true'
			gnum = tokens[o+1]

		if o==olen-2 or tokens[o+2]==I[' ']:
			if not skip: 
				if not groups[gkey].get(gnum): groups[gkey][gnum]=[]
				groups[gkey][gnum].append(tokens[beg:o+2])
			skip=False
			beg=o+2
			gnum=1000+o
			gkey='true'

	or_cnt = len(groups['true'])
	false_cnt = len(groups['false'][0])

	# If qry_set['all'] and no true/false/or conditions
	if qry_set.get(I['all']) and false_cnt == 0 and or_cnt == 0:
		qry_select, _ = selectify([I[']']], meme_table)
		# FIX LATER
		return [], [qry_select], []

	z = cte_beg
	params   = []
	cte_sqls = []
	sel_sqls = []
	notparams = []
	notwhere = ''

	# Process NOT groups
	if false_cnt:
		if or_cnt < 1: raise Exception('A query with a false statement must contain at least one true statement.')

		for subtokens in groups['false'][0]:
			qry_select, qry_params = selectify(subtokens, meme_table, True)
			notwhere += f" AND m0.aid NOT IN ({qry_select})"
			notparams.extend(qry_params)

	# Process OR groups
	for gnum in groups['true']:
		or_selects = []
		for subtokens in groups['true'][gnum]:

			qry_select, qry_params = selectify(subtokens, meme_table)

			if z>cte_beg: qry_select+=f" AND m0.aid IN (SELECT a0 FROM z{z})"
			elif notwhere: 
				qry_select += notwhere
				qry_params.extend(notparams)
				notwhere=''

			or_selects.append(qry_select)
			params.extend(qry_params)
		z += 1
		cte_sqls.append(f"z{z} AS ({' UNION '.join(or_selects)})")

	# select all data related to the matching As
	if qry_set.get(I['all']):
		qry_select, qry_params = selectify([I[']']], meme_table)
		sel_sqls.append(f"{qry_select} WHERE m0.aid IN (SELECT a0 FROM z{z})")

	# get groups
	else:
		for subtokens in groups['get'][0]:
			qry_select, qry_params = selectify(subtokens, meme_table)
			sel_sqls.append(f"{qry_select} AND a0 IN (SELECT a0 FROM z{z})")
			params.extend(qry_params)

	for cte_out in range(cte_beg, z):
		sel_sqls.append(f"SELECT arbeq FROM z{cte_out+1}" + ('' if cte_out+1 == z else f" WHERE a0 IN (SELECT a0 FROM z{z})"))

	return cte_sqls, sel_sqls, params


# Input: tokens
# Output: SELECT string, FROM string, WHERE string, and depth int
def selectify(tokens: list, meme_table=None, aidOnly=False):
	if not meme_table: meme_table=DB['table_meme']

	qparts = {
		'select': [f"(A0) AS a0", f"concat_ws(' ', ';', (A0)"],
		'join': [f" FROM {meme_table} m0"],
		'where': []
	}

	params = []
	inversions = [False]
	m = 0
	cpr = '=.'

	olen=len(tokens)
	for o in range(0, olen, 2):
		operator = tokens[o]
		operand = tokens[o+1]
		func = OPR[operator][FUNC]

		# Starting A
		if o==0:
			if func != A: raise Exception('A error')

		# [R
		elif func == R and str(operand).startswith('-'): inversions[m]=True

		# Chained [R[R or ]B]B or [R[]R
		if o>2 and (func == R or (func == B and OPR[tokens[o-2]][FUNC] == B)):
			qparts['select'][1] += f", {I['[']}, (R{m})"
			if OPR[tokens[o-2]][FUNC] == B: qparts['select'][1] += f", {I[']']}, (B{m})"

			m+=1
			qparts['join'].append(f"JOIN {meme_table} m{m} ON (B{m-1})=(A{m})")
			inversions.append(False)

		# where
		if operand is not None:
			if operator == I['=#']: pass
			elif func == Q:
				cpr=K[operator] if OPR[operator][OUT]==False else OPR[operator][OUT]
				if   cpr == '=#': cpr='='
				elif cpr == '=.': cpr='='
				qparts['where'].append(f"m{m}.qnt{cpr}%s")
				params.append(operand)
			elif func in (A,R,B):
				qparts['where'].append(f"({func}{m})=%s")
				params.append(operand)

	if aidOnly: qparts['select'].pop(1)
	else: 
		qparts['select'][1] += f", {I['[']}, (R{m}), {I[']']}, (B{m}), m{m}.cpr, m{m}.qnt) AS arbeq"

	for i,inv in enumerate(inversions):
		for qpart in qparts:
			for p, _ in enumerate(qparts[qpart]):
				acol = 'aid' if not inv else 'bid'
				bcol = 'bid' if not inv else 'aid'
				rcol = 'rid' if not inv else 'rid*-1'
				qparts[qpart][p]=qparts[qpart][p].replace(f"(A{i})", f"m{i}.{acol}").replace(f"(R{i})", f"m{i}.{rcol}").replace(f"(B{i})", f"m{i}.{bcol}")
		
	return ('SELECT '
		+ ', '.join(qparts['select'])
		+ ' '.join(qparts['join'])
		+ ('' if not qparts['where'] else ' WHERE ' + ' AND '.join(qparts['where']))
	), params



def put (tokens: list, meme_table: str = None, name_table: str = None):
	if not meme_table: meme_table=DB['table_meme']
	if not name_table: name_table=DB['table_name']

	namecache(tokens, 'str', name_table)

	missings = {}
	sqls = {meme_table:[], name_table:[]}
	params = {meme_table:[], name_table:[]}

	# Swap keys with IDs or mark key missing
	olen=len(tokens)
	for o in range(THEBEG, olen, 2):
		if OPR[tokens[o]][FORM]==FLOAT: tokens[o+1]=float(tokens[o+1])
		elif OPR[tokens[o]][FORM]==KEY and isinstance(tokens[o+1], str):
			operand=tokens[o+1]
			if operand.startswith('-'): 
				operand=operand[1:]
				sign=-1
			else: sign=1

			if operand.isdigit(): tokens[o+1]=int(tokens[o+1])
			elif I.get(operand): tokens[o+1]=I[operand]*sign
			else: missings[operand]=1

	# Mark id-key for writing from id[nam]key="xyz"
	end = THEBEG
	while (end := nxt(tokens, (beg := end)))>0:
		if tokfit(tokens[beg:end], [A, False, R, I['nam'], B, I['key'], I['=$'], False]):
			aid = tokens[beg+1]
			key = tokens[beg+7]
			missings.pop(key, None)
			sqls[name_table].append("(%s,%s,%s)")
			params[name_table].extend([aid, I['key'], key])
			I[key]=aid
			K[aid]=key

	# Select new ID for missing keys with no associated ID
	aid = aggnum('aid', 'MAX', name_table) or I['cor']
	if missings:
		for key, val in missings.items():
			aid += 1
			sqls[name_table].append("(%s,%s,%s)")
			params[name_table].extend([aid, I['key'], key])
			I[key]=aid
			K[aid]=key

	# Swap missing keys for new IDs
	for o in range(THEBEG, olen, 2):
		if OPR[tokens[o]][FORM]==KEY and isinstance(tokens[o+1], str):
			if tokens[o+1].startswith('-'): tokens[o+1]=I[tokens[o+1][1:]]*-1
			else: tokens[o+1]=I[tokens[o+1]]

	# Pull out non-key names and truths
	end=THEBEG
	while (end := nxt(tokens, (beg := end)))>0:
		if end-beg==0: continue

		# A[nam]B = "String"
		elif tokfit(tokens[beg:end], [A, False, R, I['nam'], B, False, I['=$'], False]):
			if tokens[beg+5]!=I['key']:
				params[name_table].extend([tokens[beg+1], tokens[beg+5], tokens[beg+7]])
				sqls[name_table].append('(%s,%s,%s)')

		# A[R]B
		elif tokfit(tokens[beg:end], [A, False, R, False, B, False]):
			params[meme_table].extend([tokens[beg+1],tokens[beg+3],tokens[beg+5],I['=#'],I['t']])
			sqls[meme_table].append('(%s,%s,%s,%s,%s)')

		# A[R]B=Q
		elif tokfit(tokens[beg:end], [A, False, R, False, B, False, I['=.'], False]):
			params[meme_table].extend([tokens[beg+1],tokens[beg+3],tokens[beg+5],tokens[beg+6],tokens[beg+7]])
			sqls[meme_table].append('(%s,%s,%s,%s,%s)')

		# [Ry]By >> Rz[Bz]
		# -By[Ry]X = t
		# -X[Rz]Bz = t
		elif tokfit(tokens[beg:end], [A, None, R, False, B, False, I['>>'], None, R, False, B, False]):
			aid+=1
			sqls[name_table].append("(%s,%s,%s)")
			params[name_table].extend([aid, I['key'], f'VAR{aid}'])

			params[meme_table].extend([tokens[beg+5]*-1, tokens[beg+3]*-1, aid, I['=#'], I['t']])
			params[meme_table].extend([aid*-1, tokens[beg+9], tokens[beg+11], I['=#'], I['t']])
			sqls[meme_table].append('(%s,%s,%s,%s,%s)')
			sqls[meme_table].append('(%s,%s,%s,%s,%s)')

		# [Ry]By=t >> Rz[Bz]=t
		# -By[Ry]X = t
		# -X[Rz]Bz = t
		elif tokfit(tokens[beg:end], [A, None, R, False, B, False, Q, False, I['>>'], None, R, False, B, False, Q, False]):
			aid+=1
			sqls[name_table].append("(%s,%s,%s)")
			params[name_table].extend([aid, I['key'], f'VAR{aid}'])

			params[meme_table].extend([tokens[beg+5]*-1, tokens[beg+3]*-1, aid, tokens[beg+6], tokens[beg+7]])
			params[meme_table].extend([aid*-1, tokens[beg+11], tokens[beg+13], tokens[beg+14], tokens[beg+15]])
			sqls[meme_table].append('(%s,%s,%s,%s,%s)')
			sqls[meme_table].append('(%s,%s,%s,%s,%s)')

		else:
			print('TOKENS:', [tok if not K.get(tok) else K[tok] for tok in tokens[beg:end]])
			raise Exception('Could not write')

	for tbl in params:
		if params[tbl]:
			insert(f"INSERT INTO {tbl} VALUES " + ','.join(sqls[tbl]) + " ON CONFLICT DO NOTHING", params[tbl])

	return tokens


###############################################################################
#                         MEMELANG -> SQL -> EXECUTE
###############################################################################

# Input: Memelang query string
# Output: list of tokens match query from DB
def query(memestr: str, bid: int = None, meme_table: str = None, name_table: str = None) -> list:

	tokens = identify(decode(memestr), ALL, name_table)
	sql, params = querify(tokens, meme_table, name_table)
	res = select(sql, params)
	if not res or not res[0] or not res[0][0]: return []

	tokens=[I['id'], I['id']]

	strtoks=res[0][0].split()
	for tok in strtoks:
		if tok == '': continue
		elif tok==';': tokens.append(I[';'])
		elif '.' in tok: tokens.append(float(tok))
		else: tokens.append(int(tok))

	if bid==I['key']: return keyify(tokens, ODD, name_table)
	return tokens


# Return meme count of above results
def count(memestr: str, meme_table: str = None, name_table: str = None) -> int:
	tokens = identify(decode(memestr), ALL, name_table)
	sql, params = querify(tokens, meme_table, name_table)
	res=select(sql, params)
	return 0 if not res or not res[0] or not res[0][0] else res[0][0].count(';')


###############################################################################
#                                FILE I/O
###############################################################################

def read (file_path: str) -> list:
	with open(file_path, 'r', encoding='utf-8') as f: tokens = decode(f.read())
	return tokens


def write (file_path: str, tokens: list):
	with open(file_path, 'w', encoding='utf-8') as file:
		file.write(encode(tokens, {'newline':True}))


###############################################################################
#                                  CLI
###############################################################################

# Execute and output an SQL query
def cli_sql(qry_sql):
	rows = select(qry_sql, [])
	for row in rows: print(row)


# Execute and output a Memelang query
def cli_query(memestr):
	tokens = decode(memestr)
	print ("TOKENS:", tokens)
	print ("QUERY:", encode(tokens))

	sql, params = querify(identify(tokens))
	full_sql = morfigy(sql, params)
	print(f"SQL: {full_sql}\n")

	# Execute query
	print(f"RESULTS:")
	print(encode(query(memestr, I['key']), {'newline':True}))
	print()
	print()


# Read a meme file and save it to DB
def cli_putfile(file_path):
	tokens = read(file_path)
	tokens = put(tokens)
	print(encode(keyify(tokens), {'newline':True}))


# Test various Memelang queries
def cli_qrytest():
	queries=[
		'george_washington',
		' george_washington]',
		'george_washington[ ',
		'george_washington',
		'george_washington[',
		'george_washington[]',
		'george_washington[opt]',
		'george_washington[birth',
		'george_washington[birth]',
		'george_washington[birth[year',
		'george_washington[birth[year]',
		'george_washington[birth[year]adyear',
		'george_washington[birth[[',
		'george_washington[birth[[]',
		'george_washington[birth[][]',
		'martha_washington[-spouse]',
		'martha_washington[-spouse',
		'martha_washington[-spouse[birth[',
		'martha_washington[-spouse][birth[',
		']adyear',
		']adyear=t',
		'[year]adyear',
		'[birth[year]adyear',
		']adyear=1732',
		']adyear>=1900',
		'[year]adyear>1800',
		'[birth[year]adyear<=2000',
		'[spouse]',
		'[spouse] [child]',
		'[birth[year]adyear>=1800 [birth[year]adyear<1900',
		'[spouse [child [birth[year]adyear<1900',
		'george_washington; john_adams',
		'george_washington;; john_adams;; ; thomas_jefferson;',
	]
	errcnt=0

	for memestr in queries:
		tokens = decode(memestr)
		print('Tokens:', keyify(tokens, ALL))
		print('Query 1:', memestr)

		for i in range(2,4):
			memestr2 = encode(keyify(decompress(compress(identify(tokens, ALL)))))
			print(f'Query {i}:', memestr2)
			tokens = decode(memestr2)

		sql, params = querify(identify(tokens))
		print('SQL: ', morfigy(sql, params))
		
		c1=count(memestr)
		c2=count(memestr2)
		print ('First Count:  ', c1)
		print ('Second Count: ', c2)

		if not c1 or c1!=c2 or c1>200:
			print()
			print('*** COUNT ERROR ABOVE ***')
			errcnt+=1

		print()
	print("ERRORS:", errcnt)
	print()


# Add database and user
def cli_dbadd():
	commands = [
		f"sudo -u postgres psql -c \"CREATE DATABASE {DB['name']};\"",
		f"sudo -u postgres psql -c \"CREATE USER {DB['user']} WITH PASSWORD '{DB['pswd']}'; GRANT ALL PRIVILEGES ON DATABASE {DB['name']} to {DB['user']};\"",
		f"sudo -u postgres psql -c \"GRANT ALL PRIVILEGES ON DATABASE {DB['name']} to {DB['user']};\""
	]

	for command in commands:
		print(command)
		os.system(command)


# Add database table
def cli_tableadd():
	commands = [
		f"sudo -u postgres psql -d {DB['name']} -c \"CREATE TABLE {DB['table_meme']} (aid BIGINT, rid BIGINT, bid BIGINT, cpr SMALLINT, qnt DECIMAL(20,6)); CREATE UNIQUE INDEX {DB['table_meme']}_aid_idx ON {DB['table_meme']} (aid,rid,bid); CREATE INDEX {DB['table_meme']}_rid_idx ON {DB['table_meme']} (rid); CREATE INDEX {DB['table_meme']}_bid_idx ON {DB['table_meme']} (bid);\"",
		f"sudo -u postgres psql -d {DB['name']} -c \"CREATE TABLE {DB['table_name']} (aid BIGINT, bid BIGINT, str VARCHAR(511)); CREATE UNIQUE INDEX {DB['table_name']}_aid_idx ON {DB['table_name']} (aid,bid,str); CREATE INDEX {DB['table_name']}_str_idx ON {DB['table_name']} (str);\"",
		f"sudo -u postgres psql -d {DB['name']} -c \"GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE {DB['table_meme']} TO {DB['user']};\"",
		f"sudo -u postgres psql -d {DB['name']} -c \"GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE {DB['table_name']} TO {DB['user']};\"",
	]

	for command in commands:
		print(command)
		os.system(command)


# Delete database table
def cli_tabledel():
	commands = [
		f"sudo -u postgres psql -d {DB['name']} -c \"DROP TABLE {DB['table_meme']};\"",
		f"sudo -u postgres psql -d {DB['name']} -c \"DROP TABLE {DB['table_name']};\"",
	]
	for command in commands:
		print(command)
		os.system(command)


# Save aid->key relations in conf.py to name DB table
def cli_coreadd():
	memestr=''
	for key in I: memestr+=f'{I[key]}[nam]key="{key}";'
	tokens = identify(decode(memestr))
	print(encode(put(tokens), {'newline':True}))


if __name__ == "__main__":
	LOCAL_DIR = os.path.dirname(os.path.abspath(__file__))

	cmd = sys.argv[1]
	if cmd == 'sql': cli_sql(sys.argv[2])
	elif cmd in ('query','qry','q','get','g'): cli_query(sys.argv[2])
	elif cmd in ('file','import'): cli_putfile(sys.argv[2])
	elif cmd in ('dbadd','adddb'): cli_dbadd()
	elif cmd in ('tableadd','addtable'): cli_tableadd()
	elif cmd in ('tabledel','deltable'): cli_tabledel()
	elif cmd in ('coreadd','addcore'): cli_coreadd()
	elif cmd == 'qrytest': cli_qrytest()
	elif cmd == 'install':
		cli_dbadd()
		cli_tableadd()
		cli_coreadd()
	elif cmd == 'reinstall':
		cli_tabledel()
		cli_tableadd()
		cli_coreadd()
		if len(sys.argv)>2 and sys.argv[2]=='-presidents': cli_putfile(os.path.join(LOCAL_DIR,'presidents.meme'))
	elif cmd in ('fileall','allfile'):
		files = glob.glob(LOCAL_DIR+'/*.meme') + glob.glob(LOCAL_DIR+'/data/*.meme')
		for f in files: cli_putfile(f)
	else: sys.exit("Invalid command")
