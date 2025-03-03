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

# Column order
A         = 1
R         = 3
B         = 5
C         = 7
Q         = 9

SEMILEN   = 0.5
THEBEG    = 4
ODD       = 1
EVEN      = 2
ALL       = 4

# Forms
FLT    = 1.1	# Value is decimal number
AID    = 1.2	# Value is an ID integer
STR    = 1.3	# Value is a string

# Each operator and its meaning
OPR = {
	I[']']: {
		'form' : AID,
		'dcol' : 'bid',
		'icol' : 'aid',
	},
	I['[']: {
		'form' : AID,
		'dcol' : 'rid',
		'icol' : 'rid*-1',
	},
	I['.']: {
		'form' : FLT,
		'dcol' : 'qnt',
		'icol' : 'qnt',
	},
	I['$']: {
		'form' : STR,
		'dcol' : 'str',
		'icol' : None,
	},
	I['|']: {
		'form' : FLT,
		'dcol' : None,
		'icol' : None,
	},
	I['==']: {
		'form' : AID,
		'dcol' : None,
		'icol' : None,
	},
	I['~']: {
		'form' : AID,
		'dcol' : None,
		'icol' : None,
	},
	I[';']: {
		'form' : None,
		'dcol' : None,
		'icol' : None,
	},
	# Placeholders to avoid key error
	I['id']: {
		'form' : None,
		'dcol' : None,
		'icol' : None,
	},
	I['mix']: {
		'form' : None,
		'dcol' : None,
		'icol' : None,
	},
	I['key']: {
		'form' : None,
		'dcol' : None,
		'icol' : None,
	},
}

# For decode()
INCOMPLETE = 1
INTERMEDIATE = 2
COMPLETE = 3
STROPR = {
	"!"  : [INCOMPLETE, False, False, False, False],
	"#"  : [INCOMPLETE, False, False, False, False],
	">"  : [INTERMEDIATE, I['=='], I['>'], I['.'], None],
	"<"  : [INTERMEDIATE,I['=='], I['<'], I['.'], None],
	"="  : [COMPLETE, I['=='], I['='], I['.'], None],
	"!=" : [COMPLETE, I['=='], I['!='], I['.'], None],
	"#=" : [COMPLETE, I['=='], I['#='], I['.'], None],
	">=" : [COMPLETE, I['=='], I['>='], I['.'], None],
	"<=" : [COMPLETE, I['=='], I['<='], I['.'], None],
	"["  : [COMPLETE, I['['], None, None, None],
	"]"  : [COMPLETE, I[']'], None, None, None],
	";"  : [COMPLETE, I[';'], SEMILEN, I[']'], None],
	' '  : [COMPLETE, I['~'], I[' '], I[']'], None],
	">>" : [COMPLETE, I['~'], I['>>'], I[']'], None],
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
#                       MEMELANG STRING PROCESSING
###############################################################################

# Input: Memelang string
# Output: list of normalized Memelang strings, which should be joined by double quote (")
# This splits by quotes so quoted string aren't altered
def normalize(memestr: str, newline = False) -> list[str]:

	parts = re.split(r'(?<!\\)"', memestr.strip())
	for p,part in enumerate(parts):

		# quote
		if p%2==1:
			parts[p]=part
			continue

		# memelang code
		part = re.sub(r'[;\n]+', ';', part) # Newlines are semicolons
		part = re.sub(r'\s+', ' ', part) # Remove multiple spaces
		part = re.sub(r'\s*([#;!<>=]+)\s*', r'\1', part) # Remove spaces around operators
		part = re.sub(r';+', ';', part) # Double semicolons
		part = re.sub(r'(\.[0-9][1-9]*)0+', r'\1', part) # Remove trailing zeros

		if newline: part = part.replace(";", "\n")
		parts[p]=part

	return parts


# Input: Memelang string "operator1operand1operator2operand2"
# Output: [operator1, operand1, operator2, operand2, ...]
def decode(memestr: str) -> list:

	# Remove comments
	memestr = re.sub(r'\s*//.*$', '', memestr, flags=re.MULTILINE)

	if len(memestr) == 0: raise Exception("Error: Empty query provided.")

	tokens = [I['id'], I['mix']]
	beg=3

	parts = normalize(';'+memestr+';')

	for p,part in enumerate(parts):
		
		# quote
		if p%2==1:
			tokens.extend([I['$'], part])
			tokens[beg]+=1
			continue

		strtoks = re.split(SPLITOPR, part)
		tlen = len(strtoks)
		t = 0
		while t<tlen:
			strtok=strtoks[t]

			# skip empty
			if len(strtok)==0: pass

			# operators
			elif STROPR.get(strtok):

				completeness, operator, operand, next_operator, next_operand = STROPR[strtok]

				if completeness!=COMPLETE:
					if t<tlen-3 and STROPR.get(strtok+strtoks[t+2]):
						completeness, operator, operand, next_operator, next_operand = STROPR[strtok+strtoks[t+2]]
						t+=2
					elif completeness==INCOMPLETE: raise Exception(f"Invalid strtok {strtok}")

				if operator==I[';']: beg=len(tokens)+1
				else: tokens[beg]+=1

				tokens.extend([operator, operand])

				if next_operator:
					tokens.extend([next_operator, next_operand])
					tokens[beg]+=1

			# string/int/float
			else:
				if tokens[-1]!=None: raise Exception(f'Sequence error {tokens[-2]} {tokens[-1]} {strtok}')
				if not re.search(r'[a-z0-9]', strtok): raise Exception(f"Unexpected '{strtok}' in {memestr}")

				if strtok in TFG: 
					tokens[-1]=I[strtok]
					if tokens[-4]!=I['==']: raise Exception('Compare sequence error')
					tokens[-3]=I['#=']
				elif '.' in strtok: tokens[-1]=float(strtok)
				elif re.match(r'-?[0-9]+', strtok): tokens[-1]=int(strtok)
				else: tokens[-1]=strtok

			t+=1

	return tokens[:-4]


# Input: tokens [operator1, operand1, operator2, operand2, ...]
# Output: Memelang string "operator1operand1operator2operand2"
def encode(tokens: list, encode_set=None) -> str:
	if not encode_set: encode_set={}
	memestr = ''

	o=THEBEG
	olen=len(tokens)
	while o<olen:

		if tokens[o]==I[';']: memestr += ';'
		elif tokens[o]==I['[']: memestr += '['+str('' if tokens[o+1] is None else str(tokens[o+1]))
		elif tokens[o]==I['~']: memestr += K[tokens[o+1]]
		elif tokens[o]==I['|']: memestr += str(tokens[o+1])

		elif tokens[o]==I[']']:
			operand = '' if tokens[o+1] is None else str(tokens[o+1])
			if o==THEBEG or tokens[o-2] in (I[';'],I['~']): memestr += operand
			else: memestr += ']'+operand

		elif tokens[o]==I['==']:
			if tokens[o+1]==I['#=']: pass #memestr += '='+K[tokens[o+3]]
			else:
				memestr+=' '+K[tokens[o+1]]+' '
				if tokens[o+2]==I['$']: memestr += ' "'+tokens[o+3]+'"'
				elif tokens[o+2]==I['.']: memestr += str(tokens[o+3])
			o+=2
		o+=2

	if encode_set.get('newline'): memestr=memestr.replace(";", "\n")

	return memestr


# Jump to next statement in tokens
def nxt(tokens: list, beg: int = 2):
	olen=len(tokens)
	if beg>=olen: return False
	elif tokens[beg]!=I[';']: raise Exception(f'Operator counting error at {beg} for {tokens[beg]}')
	return beg + 2 + (int(tokens[beg+1])*2)


# Do these statements match?
# False is wildcard
def tokfit (atoks: list, btoks: list) -> bool:
	if len(atoks)!=len(btoks): return False
	for p, btok in enumerate(btoks):
		if btok!=False and atoks[p]!=btok: return False
	return True


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
	tokids=[]

	if not tokens: return tokens

	for t,tok in enumerate(tokens):
		if not isinstance(tok, str) or (mode==ODD and t%2==0) or (mode==EVEN and t%2==1): continue
		if tok.startswith('-'): tok = tok[1:]
		if not I.get(tok): lookups.append(tok)

	namecache(lookups, 'str', name_table)

	for t,tok in enumerate(tokens):
		if not isinstance(tok, str) or (mode==ODD and t%2==0) or (mode==EVEN and t%2==1):  tokids.append(tok)
		elif tok.startswith('-'): tokids.append(I[tok[1:]]*-1)
		else: tokids.append(I[tok])

	return tokids


def keyify(tokens: list, mode: int = ODD, name_table: str = None) -> list:
	lookups=[]
	tokeys=[]

	if not tokens: return tokens

	for t,tok in enumerate(tokens):
		if not isinstance(tok, int) or t%2==0 or abs(tok)<I['cor']: continue
		elif not K.get(abs(tok)): lookups.append(abs(tok))

	namecache(lookups, 'aid', name_table)

	for t,tok in enumerate(tokens):
		if not isinstance(tok, int) or t%2==0 or abs(tok)<I['cor']: tokeys.append(tok)
		elif tok<0: tokeys.append('-'+K[abs(tok)])
		else: tokeys.append(K[tok])

	return tokeys


###############################################################################
#                         MEMELANG -> SQL QUERIES
###############################################################################

# Input: Memelang query string
# Output: SQL query string
def querify(tokens: list, meme_table: str = None, name_table: str = None):
	if not meme_table: meme_table=DB['table_meme']
	if not name_table: name_table=DB['table_name']

	ctes    = []
	selects = []
	params  = []

	end=2
	while (end := nxt(tokens, (beg := end))):
		beg+=2
		if end-beg<1: continue
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
	while o<olen:
		if tokens[o] == I[']'] and tokens[o+1] == I['qry']:
			qry_set[tokens[o+2]]=True
			skip=True

		elif tokens[o] == I['=='] and tokens[o+1] == I['#=']:
			# Handle =f (false)
			if tokens[o+2]==I['f']:
				gkey='false'
				gnum=0
			# Handle =g (get)
			elif tokens[o+2] == I['g']:
				gkey='get'
				gnum=0

		# Handle =tn (OR groups)
		elif tokens[o] == I['|']:
			gkey = 'true'
			gnum = tokens[o+1]

		elif o==olen-2 or tokens[o+2]==I['~']:
			if not skip: 
				if not groups[gkey].get(gnum): groups[gkey][gnum]=[]
				groups[gkey][gnum].append(tokens[beg:o+2])
			skip=False
			beg=o+4
			gnum=1000+o
			gkey='true'
		o+=2

	or_cnt = len(groups['true'])
	false_cnt = len(groups['false'][0])

	# If qry_set['all'] and no true/false/or conditions
	if qry_set.get(I['all']) and false_cnt == 0 and or_cnt == 0:
		qry_select, _ = selectify([I[']']], meme_table)
		# FIX LATER
		return [], [qry_select], []

	z  = cte_beg
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

	ROWLEN=SEMILEN+5
	qparts = {
		'select': [f"(aid0) AS a0", f"concat_ws(' ', ';', ROWLEN"],
		'join': [f" FROM {meme_table} m0"],
		'where': []
	}

	params = []
	inversions = [False]
	m = 0
	cpr = '='

	o=0
	olen=len(tokens)
	while o<olen:
		operator = tokens[o]
		operand = tokens[o+1]
		dcol = OPR[operator]['dcol']

		# =
		if operator==I['==']: cpr=K[int(operand)]

		else:

			# Starting ]A
			if o==0:
				if operator != I[']']: raise Exception('A error')
				dcol='aid'
				qparts['select'][1] += f", {I[']']}, ({dcol}{m})"

			# [R
			elif operator == I['['] and str(operand).startswith('-'): inversions[m]=True

			# Chained [R[R or ]B]B or [R[]R
			if o>2 and (operator == I['['] or (tokens[o-2]==I[']'] and operator==I[']'])):
					# select previous [R
					qparts['select'][1] += f", {I['[']}, (rid{m})"
					ROWLEN+=1

					# select previous ]B
					if tokens[o-2]==I[']']:
						qparts['select'][1] += f", {I[']']}, (bid{m})"
						ROWLEN+=1

					# join
					m+=1
					qparts['join'].append(f"JOIN {meme_table} m{m} ON (bid{m-1})=(aid{m})")
					inversions.append(False)

			# where
			if dcol and operand is not None and (dcol!='qnt' or cpr!='#='):
				eop = cpr if dcol=='qnt' else '='
				qparts['where'].append(f"({dcol}{m}){eop}%s")
				params.append(operand)

		o+=2

	if aidOnly: qparts['select'].pop(1)
	else: 
		qparts['select'][1] += f", {I['[']}, (rid{m}), {I[']']}, (bid{m}), {I['==']}, m{m}.cpr, {I['.']}, m{m}.qnt) AS arbeq"
		qparts['select'][1] = qparts['select'][1].replace('ROWLEN', str(ROWLEN))

	for i,inv in enumerate(inversions):
		for qpart in qparts:
			for p, _ in enumerate(qparts[qpart]):
				for op in OPR:
					if OPR[op]['icol']:
						newdcol = 'icol' if inv else 'dcol'
						newicol = 'icol' if not inv else 'dcol'
						qparts[qpart][p]=qparts[qpart][p].replace(f"({OPR[op]['dcol']}{i})", f"m{i}.{OPR[op][newdcol]}").replace(f"({OPR[op]['icol']}{i})", f"m{i}.{OPR[op][newicol]}")
		
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
	o=THEBEG
	olen=len(tokens)
	while o<olen:
		if OPR[tokens[o]]['form']==FLT: tokens[o+1]=float(tokens[o+1])
		elif OPR[tokens[o]]['form']==AID and not isinstance(tokens[o+1], int):
			operand=str(tokens[o+1])
			if operand.startswith('-'): 
				operand=operand[1:]
				sign=-1
			else: sign=1

			if operand.isdigit(): tokens[o+1]=int(tokens[o+1])
			elif I.get(operand): tokens[o+1]=I[operand]*sign
			else: missings[operand]=1
		o+=2

	# Mark id-key for writing from id[nam]key="xyz"
	end=2
	while (end := nxt(tokens, (beg := end))):
		beg+=2
		if tokfit(tokens[beg:end], [I[']'], False, I['['], I['nam'], I[']'], I['key'], I['=='], I['='], I['$'], False]):
			key = tokens[beg+Q]
			aid = tokens[beg+A]
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
	o=THEBEG
	while o<olen:
		if OPR[tokens[o]]['form']==AID and isinstance(tokens[o+1], str):
			if tokens[o+1].startswith('-'): tokens[o+1]=I[tokens[o+1][1:]]*-1
			else: tokens[o+1]=I[tokens[o+1]]
		o+=2

	# Pull out non-key names and truths
	end=2
	while (end := nxt(tokens, (beg := end))):
		beg+=2
		if end-beg==0: continue

		# A[nam]B = "String"
		elif tokfit(tokens[beg:end], [I[']'], False, I['['], I['nam'], I[']'], False, I['=='], I['='], I['$'], False]):
			if tokens[beg+B]!=I['key']:
				params[name_table].extend([tokens[beg+A], tokens[beg+B], tokens[beg+Q]])
				sqls[name_table].append('(%s,%s,%s)')

		# A[R]B
		elif tokfit(tokens[beg:end], [I[']'], False, I['['], False, I[']'], False]):
			params[meme_table].extend([tokens[beg+1],tokens[beg+3],tokens[beg+5],I['#='],I['t']])
			sqls[meme_table].append('(%s,%s,%s,%s,%s)')

		# A[R]B=Q
		elif tokfit(tokens[beg:end], [I[']'], False, I['['], False, I[']'], False, I['=='], False, I['.'], False]):
			params[meme_table].extend([tokens[beg+1],tokens[beg+3],tokens[beg+5],tokens[beg+7],tokens[beg+9]])
			sqls[meme_table].append('(%s,%s,%s,%s,%s)')

		# [Ry]By >> Rz[Bz]
		# -By[Ry]X = t
		# -X[Rz]Bz = t
		elif tokfit(tokens[beg:end], [I[']'], None, I['['], False, I[']'], False, I['~'], I['>>'], I[']'], None, I['['], False, I[']'], False]):
			aid+=1
			sqls[name_table].append("(%s,%s,%s)")
			params[name_table].extend([aid, I['key'], f'VAR{aid}'])

			params[meme_table].extend([tokens[beg+5]*-1, tokens[beg+3]*-1, aid, I['#='], I['t']])
			params[meme_table].extend([aid*-1, tokens[beg+13], tokens[beg+15], I['#='], I['t']])
			sqls[meme_table].append('(%s,%s,%s,%s,%s)')
			sqls[meme_table].append('(%s,%s,%s,%s,%s)')


		# [Ry]By=Qy >> Rz[Bz]=Qz
		# -By[Ry]X = Qy
		# -X[Rz]Bz = Qz
		elif tokfit(tokens[beg:end], [I[']'], None, I['['], False, I[']'], False, I['=='], False, I['.'], False, I['~'], I['>>'], I[']'], None, I['['], False, I[']'], False, I['=='], False, I['.'], False]):

			aid+=1
			sqls[name_table].append("(%s,%s,%s)")
			params[name_table].extend([aid, I['key'], f'VAR{aid}'])

			params[meme_table].extend([tokens[beg+5]*-1, tokens[beg+3]*-1, aid, tokens[beg+7], tokens[beg+9]])
			params[meme_table].extend([aid*-1, tokens[beg+15], tokens[beg+17], tokens[beg+19], tokens[beg+21]])
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
	print(encode(query(memestr+';', I['key']), {'newline':True}))
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
		print('Operands:', tokens)
		print('Query 1:', memestr)

		for i in range(2,4):
			memestr2 = encode(tokens)
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
	print(encode(tokens, {'newline':True}))


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