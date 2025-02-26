import sys
import os
import re
import glob
import html
import psycopg2
from conf import *

#### SETUP ####
# These are settings for handling Memelang queries. Encoding 
# these in variables makes them overly explicit, but reduces
# encoding them in if/else logic in the later functions.

# Column order
A         = 1
R         = 3
B         = 5
E         = 7
Q         = 9

SEMILEN   = 0.5
THEBEG    = 4

# Forms
NON    = 1.1		# Value has no form, like END
INT    = 1.2		# Value is integer, like True, False, Get
FLT    = 1.3		# Value is decimal number
AID    = 1.4		# Value is an ID integer
STR    = 1.5		# Value is a string

# Each operator and its meaning
OPR = {
	I['@']: {
		'form' : AID,
		'dcol' : 'aid',
		'icol' : 'bid',
		'dval' : None,
		'out'  : [STR],
		'aftr' : None,
	},
	I[']']: {
		'form' : AID,
		'dcol' : 'bid',
		'icol' : 'aid',
		'dval' : None,
		'out'  : [']', STR],
		'aftr' : STR,
	},
	I['[']: {
		'form' : AID,
		'dcol' : 'rid',
		'icol' : 'rid*-1',
		'dval' : None,
		'out'  : ['[', STR],
		'aftr' : STR,
	},
	I['==']: {
		'form' : AID,
		'dcol' : 'cpr',
		'icol' : 'cpr',
		'dval' : I['#='],
		'out'  : [AID],
		'aftr' : I['.'],
	},
	I['.']: {
		'form' : FLT,
		'dcol' : 'qnt',
		'icol' : 'qnt',
		'dval' : I['t'],
		'out'  : [FLT],
		'aftr' : None,
	},
	I['$']: {
		'form' : STR,
		'dcol' : 'str',
		'icol' : 'str',
		'dval' : None,
		'out'  : ['"', STR, '"'],
		'aftr' : None,
	},
	I['||']: {
		'form' : INT,
		'dcol' : None,
		'icol' : None,
		'dval' : None,
		'out'  : [''],
		'aftr' : None,
	},
	I['&&']: {
		'form' : AID,
		'dcol' : None,
		'icol' : None,
		'dval' : I[' '],
		'out'  : [' ',AID,' '],
		'aftr' : I['@'],
	},
	I[';']: {
		'form' : NON,
		'dcol' : None,
		'icol' : None,
		'dval' : SEMILEN,
		'out'  : [';'],
		'aftr' : I['@'],
	},
	I['id']: { # Actually starts operators, treat as close of non-existant prior statement
		'form' : NON,
		'dcol' : None,
		'icol' : None,
		'dval' : I['mix'],
		'out'  : [''],
		'aftr' : None,
	},
}

# For decode()
INCOMPLETE = 1
INTERMEDIATE = 2
COMPLETE = 3
STROPR = {
	"!"  : [INCOMPLETE, False, False],
	"#"  : [INCOMPLETE, False, False],
	">"  : [INTERMEDIATE, I['=='], I['>']],
	"<"  : [INTERMEDIATE,I['=='], I['<']],
	"="  : [COMPLETE, I['=='], I['=']],
	"!=" : [COMPLETE, I['=='], I['!=']],
	"#=" : [COMPLETE, I['=='], I['#=']],
	">=" : [COMPLETE, I['=='], I['>=']],
	"<=" : [COMPLETE, I['=='], I['<=']],
	"["  : [COMPLETE, I['['], None],
	"]"  : [COMPLETE, I[']'], None],
	";"  : [COMPLETE, I[';'], SEMILEN],
	' '  : [COMPLETE, I['&&'], I[' ']],
	">>" : [COMPLETE, I['&&'], I['>>']],
}

SPLIT_OPERATOR = r'([#;\[\]><=\s])'
SPLIT_OPERAND = r'([#;\[\]><=\s]+)'
TFG = ('t', 'f', 'g')


#### GENERAL STRINGS #####

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


#### MEMELANG STRING PARSING ####

def precode(memestr: str, newline=False) -> str:
	memestr = re.sub(r'\n+', ';', memestr) # Newlines are semicolons
	memestr = re.sub(r'\s+', ' ', memestr) # Remove multiple spaces
	memestr = re.sub(r'(\.[0-9][1-9]*)0+', r'\1', memestr) # Remove trailing zeros
	memestr = re.sub(r'\s*([#;!<>=]+)\s*', r'\1', memestr) # Remove spaces around operators
	memestr = re.sub(r';;+', ';', memestr) # Remove multiple semicolons

	if newline: memestr = memestr.replace(";", ";\n")

	return memestr.replace('#=1;', '=t;').replace('#=1.0;', '=t;').replace('#=0.0;', '=f;')


# Input: Memelang string "operator1operand1operator2operand2"
# Output: [operator1, operand1, operator2, operand2, ...]
def decode(memestr: str) -> list:

	# Remove comments
	memestr = re.sub(r'\s*//.*$', '', memestr, flags=re.MULTILINE)

	if len(memestr) == 0: raise Exception("Error: Empty query provided.")

	memestr += ';'

	tokens = [I['id'], I['mix'], I[';'], SEMILEN]
	beg=3

	parts = re.split(r'(?<!\\)"', memestr)
	for p,part in enumerate(parts):
		
		# quote
		if p%2==1:
			tokens.extend([I['$'], part])
			tokens[beg]+=1
			continue

		strtoks = re.split(SPLIT_OPERATOR, precode(part))
		tlen = len(strtoks)
		t = 0
		while t<tlen:
			strtok=strtoks[t]

			if len(strtok)==0: pass

			# operators
			elif STROPR.get(strtok):
				completeness, operator, operand = STROPR[strtok]

				if completeness!=COMPLETE:
					if t<tlen-3 and STROPR.get(strtok+strtoks[t+2]):
						completeness, operator, operand = STROPR[strtok+strtoks[t+2]]
						t+=2
					elif completeness==INCOMPLETE: raise Exception(f"Invalid strtok {strtok}")

				# A[R]B assumes =t
				if OPR[operator]['aftr'] == I['@']:
					if tokens[-4]==I['['] and tokens[-2] == I[']']:
						tokens.extend([I['=='], I['#='], I['.'], I['t']])
						tokens[beg]+=2

				# [ and ] are followed by operands
				elif OPR[operator]['aftr'] == STR:
					operand=strtoks[t+1]
					if operand=='': operand=None
					elif re.match(r'^-?[0-9]+$', operand): operand=int(operand)
					t+=1

				if operator==I[';']: beg=len(tokens)+1
				else: tokens[beg]+=1

				tokens.extend([operator, operand])

			# string/int/float
			else:
				if not re.match(r'[a-z0-9]', strtok): raise Exception(f"Unexpected '{strtok}' in {memestr}")

				if strtok in TFG: 
					strtok=I[strtok]
					if tokens[-2]!=I['==']: raise Exception('sequence error')
					tokens[-1]=I['#=']

				elif '.' in strtok: strtok=float(strtok)

				elif re.match(r'^-?[0-9]+$', strtok): strtok=int(strtok)

				if OPR[tokens[-2]]['aftr'] in (I['@'], I['.']): operator=OPR[tokens[-2]]['aftr']
				else: raise Exception(f'sequence error {tokens[-2]} {strtok}')

				tokens.extend([operator, strtok])
				tokens[beg]+=1
			t+=1

	tokens.pop()
	tokens.pop()

	return tokens


# Input: tokens [operator1, operand1, operator2, operand2, ...]
# Output: Memelang string "operator1operand1operator2operand2"
def encode(tokens: list, encode_set=None) -> str:

	if not encode_set: encode_set={}
	memestr = ''

	o=THEBEG
	olen=len(tokens)
	while o<olen:
		expression=''
		for fld in OPR[tokens[o]]['out']:
			if fld == FLT:   expression += str(tokens[o+1])
			elif fld == STR: expression += '' if tokens[o+1] is None else str(tokens[o+1])
			elif fld == AID: expression += str(tokens[o+1]) if not isinstance(tokens[o+1], int) else K[tokens[o+1]]
			else:            expression += str(fld)

		# Append the encoded expression
		if encode_set.get('html'): memestr += '<var class="v' + str(tokens[o]) + '">' + html.escape(expression) + '</var>'
		else: memestr += expression

		o+=2

	if encode_set.get('html'): memestr = '<code class="meme">' + memestr + '</code>'

	return precode(memestr, encode_set.get('newline'))


# Jump to next statement in tokens
def nxt(tokens: list, beg: int = 2):
	olen=len(tokens)
	if beg>=olen: return False
	elif tokens[beg]!=I[';']: raise Exception(f'Operator counting error at {beg} for {tokens[beg]}')
	return beg + 2 + (int(tokens[beg+1])*2)


# Do these statements match?
# False is wildcard
def tokfit (atoks: list, btoks):
	if len(atoks)!=len(btoks): return False
	for p, btok in enumerate(btoks):
		if btok!=False and atoks[p]!=btok: return False
	return True


#### POSTGRES HELPERS #####

def select(query: str, params: list = []):
	conn_str = f"host={DB_HOST} dbname={DB_NAME} user={DB_USER} password={DB_PASSWORD}"
	with psycopg2.connect(conn_str) as conn:
		cursor = conn.cursor()
		cursor.execute(query, params)
		rows=cursor.fetchall()
		return [list(row) for row in rows]


def insert(query: str, params: list = []):
	conn_str = f"host={DB_HOST} dbname={DB_NAME} user={DB_USER} password={DB_PASSWORD}"
	with psycopg2.connect(conn_str) as conn:
		cursor = conn.cursor()
		cursor.execute(query, params)


def aggnum(col: str = 'aid', agg: str = 'MAX', table: str = None):
	if not table: table=DB_TABLE_MEME
	result = select(f"SELECT {agg}({col}) FROM {table}")
	return int(0 if not result or not result[0] or not result[0][0] else result[0][0])


def selectin(cols: dict = {}, table: str = None):
	if not table: table=DB_TABLE_NAME

	conds = []
	params = []

	for col in cols:
		conds.append(f"{col} IN ("+ ','.join(['%s'] * len(cols[col])) +")")
		params.extend(cols[col])

	if not conds: return []

	return select(f"SELECT DISTINCT aid, bid, str FROM {table} WHERE " + ' AND '.join(conds), params)


#### KEY-ID CONVERSION ####

# Input list of key strings ['george_washington', 'john_adams']
# Load key->aids in I and K caches
# I['john_adams']=123
# K[123]='john_adams'
def namecache(toks: list, fld: str = 'str', name_table: str = None):
	if not toks: return
	if not name_table: name_table=DB_TABLE_NAME

	if fld=='str': uncaches = list(set([tok for tok in toks if isinstance(tok, str) and tok not in I]))
	elif fld=='aid': uncaches = list(set([tok for tok in toks if isinstance(tok, int) and tok not in K]))
	else: raise Exception('fld')

	if not uncaches: return

	rows=selectin({'bid':[I['key']], fld:uncaches}, name_table)

	for row in rows:
		I[row[2]] = int(row[0])
		K[int(row[0])] = row[2]


def identify(tokens: list = [], name_table: str = None) -> list:
	lookups=[]
	tokids=[]

	if not tokens: return tokens

	for tok in tokens:
		if not isinstance(tok, str): continue
		if tok.startswith('-'): tok = tok[1:]
		if not I.get(tok): lookups.append(tok)

	namecache(lookups, 'str', name_table)

	for t,tok in enumerate(tokens):
		if not isinstance(tok, str): tokids.append(tok)
		elif tok.startswith('-'): tokids.append(I[tok[1:]]*-1)
		else: tokids.append(I[tok])

	return tokids


def keyify(tokens: list, name_table: str = None) -> list:
	lookups=[]
	tokeys=[]

	if not tokens: return tokens

	for tok in tokens:
		if not isinstance(tok, int): continue
		elif not K.get(abs(tok)): lookups.append(abs(tok))

	namecache(lookups, 'aid', name_table)

	for t,tok in enumerate(tokens):
		if t%2==0 or not isinstance(tok, int): tokeys.append(tok)
		elif tok<0: tokeys.append(K[abs(tok)]*-1)
		else: tokeys.append(K[tok])

	return tokeys


#### MEMELANG-SQL CONVERSION ####

# Input: Memelang query string
# Output: SQL query string

# I stumbled onto something profound here.
# Memelang input generates Memelang output.

def querify(tokens: list, meme_table: str = None, name_table: str = None):
	if not meme_table: meme_table=DB_TABLE_MEME
	if not name_table: name_table=DB_TABLE_NAME

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
	if not meme_table: meme_table=DB_TABLE_MEME
	qry_set = {'all': False, 'of': False}
	groups={'false':{0:[]},'get':{0:[]}, 'true':{}}

	skip = False
	gkey='true'
	gnum=1000

	o=0
	beg=o
	olen=len(tokens)
	while o<olen:
		if tokens[o] == I['@'] and tokens[o+1] == I['qry']:
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
		elif tokens[o] == I['||']:
			gkey = 'true'
			gnum = tokens[o+1]

		elif o==olen-2 or tokens[o+2]==I['&&']:
			if not skip: 
				if not groups[gkey].get(gnum): groups[gkey][gnum]=[]
				groups[gkey][gnum].append(tokens[beg:o+2])
			skip=False
			beg=o+2
			gnum=1000+o
			gkey='true'
		o+=2

	or_cnt = len(groups['true'])
	false_cnt = len(groups['false'][0])

	# If qry_set['all'] and no true/false/or conditions
	if qry_set.get(I['all']) and false_cnt == 0 and or_cnt == 0:
		qry_select, _ = selectify([], meme_table)
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
		qry_select, qry_params = selectify([I['[']], meme_table)
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
	if not meme_table: meme_table=DB_TABLE_MEME

	ROWLEN=SEMILEN+5
	qparts = {
		'select': [f"(aid0) AS a0", f"concat_ws(' ', {I[';']}, ROWLEN, {I['@']}, (aid0), {I['[']}, (rid0)"],
		'join': [f" FROM {meme_table} m0"],
		'where': []
	}

	params = []
	inversions = [False]
	m = 0
	cpr = '='
	prev_operator = None

	o=0
	olen=len(tokens)
	while o<olen:
		operator = tokens[o]
		operand = tokens[o+1]
		form = OPR[operator]['form']
		dcol = OPR[operator]['dcol']

		if dcol == 'cpr': cpr=K[int(operand)]

		else:
			# New row
			if (operator == I[']'] and prev_operator==I[']']) or (operator == I['['] and prev_operator in (I['['], I[']'])):
				m+=1
				if prev_operator==I[']']:
					qparts['select'][1] += f", {I[']']}, (bid{m-1})"
					ROWLEN+=1
					
				qparts['select'][1] += f", {I['[']}, (rid{m})"
				ROWLEN+=1

				qparts['join'].append(f"JOIN {meme_table} m{m} ON (bid{m-1})=(aid{m})")
				inversions.append(False)

			# Inversion
			if operator == I['['] and operand is not None and operand<0: inversions[m]=True

			prev_operator = operator

			if dcol and operand is not None:
				if form in (INT, AID): operand=int(operand)
				elif form == FLT: operand=float(operand)
				else: raise Exception('invalid form')

				if dcol!='qnt' or cpr!='#=':
					eop = cpr if dcol=='qnt' else '='
					qparts['where'].append(f"({dcol}{m}){eop}%s")
					params.append(operand)

		o+=2


	if aidOnly: qparts['select'].pop(1)
	else: 
		qparts['select'][1] += f", {I[']']}, (bid{m}), {I['==']}, m{m}.cpr, {I['.']}, m{m}.qnt) AS arbeq"
		qparts['select'][1] = qparts['select'][1].replace('ROWLEN', str(ROWLEN))

	for i,inv in enumerate(inversions):
		for qpart in qparts:
			for p, _ in enumerate(qparts[qpart]):
				for op in OPR:
					if OPR[op]['dcol']:
						newcol = 'icol' if inv else 'dcol'
						qparts[qpart][p]=qparts[qpart][p].replace(f"({OPR[op]['dcol']}{i})", f"m{i}.{OPR[op][newcol]}")
		
	return ('SELECT '
		+ ', '.join(qparts['select'])
		+ ' '.join(qparts['join'])
		+ ('' if not qparts['where'] else ' WHERE ' + ' AND '.join(qparts['where']))
	), params


#### PROCESS MEMELANG QUERY FOR SQL QUERY ####

# Input a Memelang query string
def query(memestr: str, bid: int = None, meme_table: str = None, name_table: str = None) -> list:

	tokens = identify(decode(memestr), name_table)
	sql, params = querify(tokens, meme_table, name_table)
	res = select(sql, params)
	if not res or not res[0]: return []

	strtoks=res[0][0].split()
	tokens=[I['id'], I['id']]

	for tok in strtoks:
		if tok == '': continue
		elif '.' in tok: tokens.append(float(tok))
		else: tokens.append(int(tok))

	if bid==I['key']: return keyify(tokens)
	return tokens


# Return meme count of above results
def count(memestr: str, meme_table: str = None, name_table: str = None):
	tokens = identify(decode(memestr), name_table)
	sql, params = querify(tokens, meme_table, name_table)
	mres=select(sql, params)
	return 0 if not mres or not mres[0] or not mres[0][0] else mres[0][0].count(f" {I[';']} ")+1


def put (tokens: list, meme_table: str = None, name_table: str = None):
	if not meme_table: meme_table=DB_TABLE_MEME
	if not name_table: name_table=DB_TABLE_NAME

	# Load IDs
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
		if tokfit(tokens[beg:end], [I['@'], False, I['['], I['nam'], I[']'], I['key'], I['=='], I['='], I['$'], False]):
			key = tokens[beg+Q]
			aid = tokens[beg+A]
			missings.pop(key, None)
			sqls[name_table].append("(%s,%s,%s)")
			params[name_table].extend([aid, I['key'], key])
			I[key]=aid
			K[aid]=key

	# Select new ID for missing keys with no associated ID
	if missings:
		aid = aggnum('aid', 'MAX', name_table) or I['cor']
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
	varmin=0
	end=2
	while (end := nxt(tokens, (beg := end))):
		beg+=2
		if end-beg==0: continue

		# A[nam]B = "String"
		elif tokfit(tokens[beg:end], [I['@'], False, I['['], I['nam'], I[']'], False, I['=='], I['='], I['$'], False]):
			if tokens[beg+B]!=I['key']:
				params[name_table].extend([tokens[beg+A], tokens[beg+B], tokens[beg+Q]])
				sqls[name_table].append('(%s,%s,%s)')

		# A[R]B=Q
		elif tokfit(tokens[beg:end], [I['@'], False, I['['], False, I[']'], False, I['=='], False, I['.'], False]):
			params[meme_table].extend([tokens[beg+1],tokens[beg+3],tokens[beg+5],tokens[beg+7],tokens[beg+9]])
			sqls[meme_table].append('(%s,%s,%s,%s,%s)')

		# [Rx]Bx=Qx >> Ry[By]=Qy
		elif tokfit(tokens[beg:end], [I['['], False, I[']'], False, I['=='], False, I['.'], False, I['&&'], I['>>'], I['['], False, I[']'], False, I['=='], False, I['.'], False]):
			if varmin==0: 
				varmin=aggnum('aid', 'MIN', meme_table)
				if varmin==0: varmin=I['cor']*-1
			varmin-=1
			params[meme_table].extend([tokens[beg+3], tokens[beg+1]*-1, varmin, tokens[beg+5], tokens[beg+7]])
			params[meme_table].extend([varmin, tokens[beg+11], tokens[beg+13], tokens[beg+15], tokens[beg+17]])
			sqls[meme_table].append('(%s,%s,%s,%s,%s)')
			sqls[meme_table].append('(%s,%s,%s,%s,%s)')

		else:
			print('TOKENS:', [tok if not K.get(tok) else K[tok] for tok in tokens[beg:end]])
			raise Exception('Could not write')

	for tbl in params:
		if params[tbl]:
			insert(f"INSERT INTO {tbl} VALUES " + ','.join(sqls[tbl]) + " ON CONFLICT DO NOTHING", params[tbl])

	return tokens


#### MEME FILE ####

def read (file_path: str):
	with open(file_path, 'r', encoding='utf-8') as f: tokens = decode(f.read())
	return tokens


def write (file_path: str, tokens: list):
	with open(file_path, 'w', encoding='utf-8') as file:
		file.write(encode(tokens, {'newline':True}))


#### CLI ####

# Execute and output an SQL query
def sql(qry_sql):
	rows = select(qry_sql, [])
	for row in rows: print(row)


# Execute and output a Memelang query
def qry(memestr):
	tokens = decode(memestr)
	tokids = identify(tokens)
	print ("TOKENS:", tokens)
	print ("QUERY:", encode(tokens))

	sql, params = querify(tokids)
	full_sql = morfigy(sql, params)
	print(f"SQL: {full_sql}\n")

	# Execute query
	print(f"RESULTS:")
	print(encode(query(memestr+';', I['key']), {'newline':True}))
	print()
	print()


# Read a meme file and save it to DB
def putfile(file_path):
	tokens = read(file_path)
	tokens = put(tokens)
	print(encode(keyify(tokens), {'newline':True}))


# Test various Memelang queries
def qrytest():
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
def dbadd():
	commands = [
		f"sudo -u postgres psql -c \"CREATE DATABASE {DB_NAME};\"",
		f"sudo -u postgres psql -c \"CREATE USER {DB_USER} WITH PASSWORD '{DB_PASSWORD}'; GRANT ALL PRIVILEGES ON DATABASE {DB_NAME} to {DB_USER};\"",
		f"sudo -u postgres psql -c \"GRANT ALL PRIVILEGES ON DATABASE {DB_NAME} to {DB_USER};\""
	]

	for command in commands:
		print(command)
		os.system(command)


# Add database table
def tableadd():
	commands = [
		f"sudo -u postgres psql -d {DB_NAME} -c \"CREATE TABLE {DB_TABLE_MEME} (aid BIGINT, rid BIGINT, bid BIGINT, cpr SMALLINT, qnt DECIMAL(20,6)); CREATE UNIQUE INDEX {DB_TABLE_MEME}_aid_idx ON {DB_TABLE_MEME} (aid,rid,bid); CREATE INDEX {DB_TABLE_MEME}_rid_idx ON {DB_TABLE_MEME} (rid); CREATE INDEX {DB_TABLE_MEME}_bid_idx ON {DB_TABLE_MEME} (bid);\"",
		f"sudo -u postgres psql -d {DB_NAME} -c \"CREATE TABLE {DB_TABLE_NAME} (aid BIGINT, bid BIGINT, str VARCHAR(511)); CREATE UNIQUE INDEX {DB_TABLE_NAME}_aid_idx ON {DB_TABLE_NAME} (aid,bid,str); CREATE INDEX {DB_TABLE_NAME}_str_idx ON {DB_TABLE_NAME} (str);\"",
		f"sudo -u postgres psql -d {DB_NAME} -c \"GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE {DB_TABLE_MEME} TO {DB_USER};\"",
		f"sudo -u postgres psql -d {DB_NAME} -c \"GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE {DB_TABLE_NAME} TO {DB_USER};\"",
	]

	for command in commands:
		print(command)
		os.system(command)


# Delete database table
def tabledel():
	commands = [
		f"sudo -u postgres psql -d {DB_NAME} -c \"DROP TABLE {DB_TABLE_MEME};\"",
		f"sudo -u postgres psql -d {DB_NAME} -c \"DROP TABLE {DB_TABLE_NAME};\"",
	]
	for command in commands:
		print(command)
		os.system(command)


# Save aid->key relations in conf.py to name DB table
def coreadd():
	memestr=''
	for key in I: memestr+=f'{I[key]}[nam]key="{key}";'
	tokens = identify(decode(memestr))
	print(encode(tokens, {'newline':True}))


if __name__ == "__main__":
	LOCAL_DIR = os.path.dirname(os.path.abspath(__file__))

	if sys.argv[1] == 'sql': sql(sys.argv[2])
	elif sys.argv[1] == 'query' or sys.argv[1] == 'qry' or sys.argv[1] == 'q' or sys.argv[1] == 'get' or sys.argv[1] == 'g': qry(sys.argv[2])
	elif sys.argv[1] == 'file' or sys.argv[1] == 'import': putfile(sys.argv[2])
	elif sys.argv[1] == 'dbadd' or sys.argv[1] == 'adddb': dbadd()
	elif sys.argv[1] == 'tableadd' or sys.argv[1] == 'addtable': tableadd()
	elif sys.argv[1] == 'tabledel' or sys.argv[1] == 'deltable': tabledel()
	elif sys.argv[1] == 'coreadd' or sys.argv[1] == 'addcore': coreadd()
	elif sys.argv[1] == 'qrytest': qrytest()

	elif sys.argv[1] == 'install':
		dbadd()
		tableadd()
		coreadd()

	elif sys.argv[1] == 'reinstall':
		tabledel()
		tableadd()
		coreadd()
		if len(sys.argv)>2 and sys.argv[2]=='-presidents': putfile(LOCAL_DIR+'/presidents.meme')

	elif sys.argv[1] == 'fileall' or sys.argv[1] == 'allfile':
		files = glob.glob(LOCAL_DIR+'/*.meme') + glob.glob(LOCAL_DIR+'/data/*.meme')
		for file in files: putfile(file)

	else: sys.exit("MAIN.PY ERROR: Invalid command");