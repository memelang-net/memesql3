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
A         = 0
R         = 1
B         = 2
E         = 3
Q         = 4
SEMILEN   = 0.5
ARB       = [I['@'], I['['], I[']']]
ARBE      = ARB + [I['==']]
ARBEQ     = ARBE + [I['.']]
ARBES     = ARBE + [I['$']]
IMPL      = [I['['], I[']'], I['=='], I['.'], I['&&'], I['['], I[']'], I['=='], I['.']]

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
	I['opr']: { # Actually starts operators, treat as close of non-existant prior statement
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
STRTOK = {
	"!"  : [INCOMPLETE, False, False],
	"{"  : [INCOMPLETE, False, False],
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


#### POSTGRES QUERIES #####

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


#### MEMELANG QUERY PARSING ####

def precode(mqry: str) -> str:

	def lookup(match): return str(K[int(match.group(1))])

	mqry = re.sub(r'\s+', ' ', mqry) # Remove multiple spaces
	mqry = re.sub(r';;+', ';', mqry) # Remove multiple semicolons
	mqry = re.sub(r'(\.[0-9]*[1-9])0+', r'\1', mqry) # Remove trailing zeros
	mqry = re.sub(r'\s*([#;!<>=]+)\s*', r'\1', mqry) # Remove spaces around operators
	mqry = re.sub(r'\{(\d+)\}', lookup, mqry) # Replace {34} with >
	return mqry.replace('#=1.0', '=t').replace('#=0.0', '=f')


# Input: Memelang string operator1operand1operator2operand2
# Output: [operator1, operator2, ...], [operand1, operand2, ...]
def decode(mqry: str):

	# Remove comments
	mqry = re.sub(r'\s*//.*$', '', mqry, flags=re.MULTILINE)

	if len(mqry) == 0: raise Exception("Error: Empty query provided.")

	mqry += ';'

	operators = [I['opr'], I[';']]
	operands = [I['mix'],SEMILEN]
	beg=1

	parts = re.split(r'(?<!\\)"', mqry)
	for p,part in enumerate(parts):
		
		# quote
		if p%2==1:
			operators.append(I['$'])
			operands.append(part)
			operands[beg]+=1
			continue

		tokens = re.split(SPLIT_OPERATOR, precode(part))
		tlen=len(tokens)
		t=0
		while t<tlen:
			token=tokens[t]

			if len(token)==0: pass

			# operators
			elif STRTOK.get(token):
				completeness, operator, operand = STRTOK[token]

				if completeness!=COMPLETE:
					if t<tlen-3 and STRTOK.get(token+tokens[t+2]):
						completeness, operator, operand = STRTOK[token+tokens[t+2]]
						t+=2
					elif completeness==INCOMPLETE: raise Exception(f"Invalid token {token}")

				if OPR[operator]['aftr']==I['@']:
					# A[R]B assumes =t
					if operators[-2]==I['['] and operators[-1]==I[']']:
						operators.extend([I['=='], I['.']])
						operands.extend([I['#='], I['t']])
						operands[beg]+=2

				# [ and ] are followed by operands
				elif OPR[operator]['aftr']==STR:
					operand=tokens[t+1]
					if operand=='': operand=None
					elif re.match(r'^-?[0-9]+$', operand): operand=int(operand)
					t+=1

				if operator==I[';']: beg=len(operators)
				else: operands[beg]+=1

				operators.append(operator)
				operands.append(operand)

			# string/int/float
			else:
				if not re.match(r'[a-z0-9]', token):
					raise Exception(f"Unexpected '{token}' in {mqry}")

				if token in TFG: 
					token=I[token]
					if operators[-1]==I['==']: operands[-1]=I['#=']
					else: raise Exception('sequence error')

				elif '.' in token: token=float(token)

				elif re.match(r'^-?[0-9]+$', token): token=int(token)

				if OPR[operators[-1]]['aftr'] in (I['@'], I['.']): operator=OPR[operators[-1]]['aftr']
				else: raise Exception(f'sequence error {operators[-1]} {token}')

				operators.append(operator)
				operands.append(token)
				operands[beg]+=1
			t+=1

	operators.pop()
	operands.pop()
	return operators, operands


# Input: operators, operands
# Output: Memelang string operator1operand1operator2operand2
def encode(operators: list, operands: list, encode_set=None) -> str:

	if not encode_set: encode_set={}
	mqry = ''

	for o,operator in enumerate(operators):
		if o<2: continue
		expression=''
		for fld in OPR[operator]['out']:
			if fld == FLT: operand = operands[o]
			elif fld == STR: operand = '' if operands[o] is None else operands[o]
			elif fld == AID: operand = operands[o] if not isinstance(operands[o], int) else K[operands[o]]
			else: operand=fld

			expression+=str(operand)

		# Append the encoded expression
		if encode_set.get('html'): mqry += '<var class="v' + str(operator) + '">' + html.escape(expression) + '</var>'
		else: mqry += expression

	if encode_set.get('html'): mqry = '<code class="meme">' + mqry + '</code>'

	return precode(mqry)


def out (operators: list, operands: list):
	print(encode(operators, operands, {'newline': True}))


def nxt(operators: list, operands: list, beg: int = 1):
	olen=len(operators)
	if beg>=olen: return False
	elif operators[beg]!=I[';']: raise Exception(f'Operator counting error at {beg} for {operators[beg]}')
	return beg+1+int(operands[beg])


#### MEMELANG-SQL CONVERSION ####

# Input: Memelang query string
# Output: SQL query string

# I stumbled onto something profound here.
# Memelang input generates Memelang output.

def querify(mqry: str, meme_table: str = None, name_table: str = None):
	if not meme_table: meme_table=DB_TABLE_MEME
	if not name_table: name_table=DB_TABLE_NAME

	operators, operands = decode(identify(mqry))

	ctes    = []
	selects = []
	params  = []

	end=1
	while (end := nxt(operators, operands, (beg := end))):
		beg+=1
		if end-beg<1: continue
		cte, select, param = subquerify(operators[beg:end], operands[beg:end], meme_table, len(ctes))
		ctes.extend(cte)
		selects.extend(select)
		params.extend(param)

	return ['WITH ' + ', '.join(ctes) + " SELECT string_agg(arbeq, '') AS arbeq FROM (" + ' UNION '.join(selects) + ')', params]


# Input: operators and operands for one Memelang command
# Output: One SQL query string
def subquerify(operators: list, operands: list, meme_table: str = None, cte_beg: int = 0):
	if not meme_table: meme_table=DB_TABLE_MEME
	qry_set = {'all': False, 'of': False}
	groups={'false':{0:[]},'get':{0:[]}, 'true':{}}

	skip = False
	gkey='true'
	gnum=1000

	o=0
	beg=o
	olen=len(operators)
	while o<olen:
		if operators[o]==I['@'] and operands[o]==I['qry']:
			qry_set[operands[o+1]]=True
			skip=True

		elif operators[o] == I['=='] and operands[o] == I['#=']:
			# Handle =f (false)
			if operands[o+1]==I['f']:
				gkey='false'
				gnum=0
			# Handle =g (get)
			elif operands[o+1] == I['g']:
				gkey='get'
				gnum=0

		# Handle =tn (OR groups)
		elif operators[o] == I['||']:
			gkey = 'true'
			gnum = operands[o]

		elif operands[o]==I[' '] or o==olen-1:
			if not skip: 
				if not groups[gkey].get(gnum): groups[gkey][gnum]=[]
				groups[gkey][gnum].append([operators[beg:o+1], operands[beg:o+1]])
			skip=False
			beg=o
			gnum=1000+o
			gkey='true'
		o+=1

	or_cnt = len(groups['true'])
	false_cnt = len(groups['false'][0])

	# If qry_set['all'] and no true/false/or conditions
	if qry_set.get(I['all']) and false_cnt == 0 and or_cnt == 0:
		qry_select, _ = selectify([], [], meme_table)
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

		for suboperators, suboperands in groups['false'][0]:
			qry_select, qry_params = selectify(suboperators, suboperands, meme_table, True)
			notwhere += f" AND m0.aid NOT IN ({qry_select})"
			notparams.extend(qry_params)

	# Process OR groups
	for gnum in groups['true']:
		or_selects = []
		for suboperators, suboperands in groups['true'][gnum]:

			qry_select, qry_params = selectify(suboperators, suboperands, meme_table)

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
		qry_select, qry_params = selectify([I['[']], [], meme_table)
		sel_sqls.append(f"{qry_select} WHERE m0.aid IN (SELECT a0 FROM z{z})")

	# get groups
	else:
		for suboperators, suboperands in groups['get'][0]:
			qry_select, qry_params = selectify(suboperators, suboperands, meme_table)
			sel_sqls.append(f"{qry_select} AND a0 IN (SELECT a0 FROM z{z})")
			params.extend(qry_params)

	for cte_out in range(cte_beg, z):
		sel_sqls.append(f"SELECT arbeq FROM z{cte_out+1}" + ('' if cte_out+1 == z else f" WHERE a0 IN (SELECT a0 FROM z{z})"))

	return cte_sqls, sel_sqls, params


# Input: operators and operands for one Memelang statement
# Output: SELECT string, FROM string, WHERE string, and depth int
def selectify(operators: list, operands: list, meme_table=None, aidOnly=False):
	if not meme_table: meme_table=DB_TABLE_MEME

	qparts = {
		'select': ["(aid0) AS a0", "(aid0)::text || '[' || (rid0)::text"],
		'join': [f" FROM {meme_table} m0"],
		'where': []
	}

	params = []
	inversions = [False]
	m = 0
	cpr='='
	prev_operator = None

	for i, operator in enumerate(operators):
		operand = operands[i]
		form = OPR[operator]['form']
		dcol = OPR[operator]['dcol']

		if dcol == 'cpr':
			cpr=K[int(operand)]
			print('set cpr',cpr, operators, operands)
			continue

		# New row
		if (operator == I[']'] and prev_operator==I[']']) or (operator == I['['] and prev_operator in (I['['], I[']'])):
			m+=1
			qparts['select'][1]+=(f" || ']' || (bid{m-1})::text" if prev_operator==I[']'] else '') + f" || '[' || (rid{m})::text"
			qparts['join'].append(f"JOIN {meme_table} m{m} ON (bid{m-1})=(aid{m})")
			inversions.append(False)

		# Inversion
		if operator == I['['] and operand is not None and operand<0: inversions[m]=True

		prev_operator = operator

		if dcol and operand is not None:
			if form in (INT, AID): operand=int(operand)
			elif form == FLT: operand=float(operand)
			else: raise Exception('invalid form')

			# FIX LATER
			if dcol=='qnt' and cpr=='#=': continue

			eop = cpr if dcol=='qnt' else '='

			qparts['where'].append(f"({dcol}{m}){eop}%s")
			params.append(operand)


	if aidOnly: qparts['select'].pop(1)
	else: qparts['select'][1] += f" || ']' || (bid{m})::text || '{{' || m{m}.cpr::text || '}}' || m{m}.qnt::text || ';' AS arbeq"

	for i,inv in enumerate(inversions):
		for qpart in qparts:
			for p, _ in enumerate(qparts[qpart]):
				for op in OPR:
					if OPR[op]['dcol']:
						newcol = 'icol' if inv else 'dcol'
						qparts[qpart][p]=qparts[qpart][p].replace(f"({OPR[op]['dcol']}{i})", f"(m{i}.{OPR[op][newcol]})")
		
	return ('SELECT '
		+ ', '.join(qparts['select'])
		+ ' '.join(qparts['join'])
		+ ('' if not qparts['where'] else ' WHERE ' + ' AND '.join(qparts['where']))
	), params


#### KEY-ID CONVERSION ####

# Input list of key strings ['george_washington', 'john_adams']
# Load key->aids in I and K caches
# I['john_adams']=123
# K[123]='john_adams'
def aidcache(keys: list, name_table: str = None):
	if not name_table: name_table=DB_TABLE_NAME
	if not keys: return

	uncached_keys = list(set([key for key in keys if isinstance(key, str) and key not in I]))

	if not uncached_keys: return

	rows=selectin({'bid':[I['key']], 'str':uncached_keys}, name_table)

	for row in rows:
		I[row[2]] = int(row[0])
		K[int(row[0])] = row[2]


def identify(mqry: str, name_table: str = None):
	lookups=[]

	if not mqry: return mqry

	parts = re.split(r'(?<!\\)"', mqry)
	for p,part in enumerate(parts):
		if p%2==1: continue
		parts[p] = re.split(SPLIT_OPERAND, part)
		lookups.extend(parts[p])

	aidcache(lookups, name_table)

	for p,part in enumerate(parts):
		if not isinstance(part, list): continue
		for o,operand in enumerate(part):
			if operand in TFG: continue
			if re.match(r'[a-z]', operand):
				if operand.startswith('-'): parts[p][o]=str(I[operand[1:]]*-1)
				else: parts[p][o]=str(I[operand])

		parts[p]=''.join(parts[p])

	return '"'.join(parts)


def namify(mqry: str, bids: list, name_table: str = None):
	lookups=[]

	if not mqry: return mqry

	output={}
	for b,bid in enumerate(bids):
		bids[b]=int(bid)
		output[int(bid)]=[]

	parts = re.split(r'(?<!\\)"', mqry)
	for p,part in enumerate(parts):
		if p%2==1: continue
		parts[p] = re.split(SPLIT_OPERAND, part)

		for operand in parts[p]:
			if operand.isdigit(): lookups.append(operand)
			elif operand.startswith('-') and operand[1:].isdigit(): lookups.append(operand[1:])

	names = selectin({'aid' : lookups, 'bid': bids}, name_table)
	
	namemap = {}
	for name in names:
		if not namemap.get(name[0]): namemap[int(name[0])]={}
		namemap[int(name[0])][int(name[1])]=name[2]

	for p, part in enumerate(parts):
		for bid in bids: output[bid].append(part)

		if not isinstance(part, list): continue

		for o, operand in enumerate(part):

			sign=''
			if operand.startswith('-') and operand[1:].isdigit():
				operand=operand[1:]
				sign='-'

			if operand.isdigit():
				operand=int(operand)

				for bid in bids:
					if namemap.get(operand) and namemap[operand].get(bid): output[bid][p][o] = sign + namemap[operand][bid]
					else: output[bid][p][o] = f'\t{operand}NOTFOUND\t'

		for bid in bids: output[bid][p]=''.join(output[bid][p])

	for bid in bids: output[bid]='"'.join(output[bid])

	return list(output.values())


#### PROCESS MEMELANG QUERY FOR SQL QUERY ####

# Input a Memelang query string
def get(mqry: str, bid: int = None, meme_table: str = None, name_table: str = None) -> str:
	if not meme_table: meme_table=DB_TABLE_MEME
	if not name_table: name_table=DB_TABLE_NAME

	sql, params = querify(mqry, meme_table, name_table)
	res = select(sql, params)
	return [] if not res or not res[0] else precode(res[0][0] if not bid else namify(res[0][0], [bid], name_table)[0])


# Input a Memelang query string
def gets(mqry: str, meme_table: str = None, name_table: str = None) -> list[str]:
	if not meme_table: meme_table=DB_TABLE_MEME
	if not name_table: name_table=DB_TABLE_NAME

	sql, params = querify(mqry, meme_table, name_table)
	res = select(sql, params)
	if not res or not res[0]: return []
	output = [ precode(res[0][0]) ]

	namekeys=[]
	pattern = r'qry\[nam\]([a-z]+)'
	for match in re.finditer(pattern, mqry): namekeys.append(identify(match.group(1)))
	if namekeys: output.extend(namify(output[0], namekeys, name_table))

	return output

# Return meme count of above results
def count(mqry: str, meme_table: str = None, name_table: str = None):
	sql, params = querify(mqry, meme_table, name_table)
	mres=select(sql, params)
	return 0 if not mres or not mres[0] or not mres[0][0] else mres[0][0].count(';')


def put (operators: list, operands: list, meme_table: str = None, name_table: str = None):
	if not operators: return operators, operands
	if not meme_table: meme_table=DB_TABLE_MEME
	if not name_table: name_table=DB_TABLE_NAME

	# Load IDs
	aidcache(operands, name_table)

	missings = {}
	sqls = {meme_table:[], name_table:[]}
	params = {meme_table:[], name_table:[]}

	# Swap keys with IDs or mark key missing
	o=2
	olen=len(operators)
	while o<olen:
		if OPR[operators[o]]['form']==AID:
			if isinstance(operands[o], int): pass

			operand=str(operands[o])
			if operand.startswith('-'): 
				operand=operand[1:]
				sign=-1
			else: sign=1

			if operand.isdigit(): operands[o]=int(operands[o])
			elif I.get(operand): operands[o]=I[operand]*sign
			else: missings[operand]=1
		o+=1

	# Mark id-key for writing from id[nam]key="xyz"
	end=1
	while (end := nxt(operators, operands, (beg := end))):
		beg+=1
		if operators[beg:end]==ARBES and operands[beg+R]==I['nam'] and operands[beg+B]==I['key']:
			key = operands[beg+Q]
			aid = operands[beg+A]
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
	o=2
	while o<olen:
		if OPR[operators[o]]['form']==AID and isinstance(operands[o], str):
			if operands[o].startswith('-'): operands[o]=I[operands[o][1:]]*-1
			else: operands[o]=I[operands[o]]
		o+=1

	# Pull out non-key names and truths
	varmin=0
	end=1
	while (end := nxt(operators, operands, (beg := end))):
		beg+=1
		if end-beg==0: continue

		elif operators[beg:end]==ARBES:
			if operands[beg+B]!=I['key']:
				params[name_table].extend([operands[beg+A], operands[beg+B], operands[beg+Q]])
				sqls[name_table].append('(%s,%s,%s)')

		elif operators[beg:end]==ARBEQ:
			params[meme_table].extend(operands[beg:end])
			sqls[meme_table].append('(%s,%s,%s,%s,%s)')

		elif operators[beg:end]==IMPL and operands[beg+4]==I['>>']:
			if varmin==0: 
				varmin=aggnum('aid', 'MIN', meme_table)
				if varmin==0: varmin=I['cor']*-1
			varmin-=1
			params[meme_table].extend([operands[beg+1], operands[beg]*-1, varmin, operands[beg+2], operands[beg+3]])
			params[meme_table].extend([varmin, operands[beg+5], operands[beg+6], operands[beg+7], operands[beg+8]])
			sqls[meme_table].append('(%s,%s,%s,%s,%s)')
			sqls[meme_table].append('(%s,%s,%s,%s,%s)')

		else:
			print('OPERATORS:', [K[op] for op in operators[beg:end]])
			print('OPERANDS:', [op if not K.get(op) else K[op] for op in operands[beg:end]])
			out(operators[beg:end], [op if not K.get(op) else K[op] for op in operands[beg:end]])
			raise Exception('Could not write')

	for tbl in params:
		if params[tbl]:
			insert(f"INSERT INTO {tbl} VALUES " + ','.join(sqls[tbl]) + " ON CONFLICT DO NOTHING", params[tbl])

	return operators, operands


#### MEME FILE ####

def read (file_path: str):
	output = [[I['opr']],[I['mix']]]
	with open(file_path, 'r', encoding='utf-8') as f:
		for ln, line in enumerate(f, start=1):
			if line.strip() == '' or line.strip().startswith('//'): continue
			operators, operands = decode(line)
			if len(operators)>2:
				output[0].extend(operators[1:])
				output[1].extend(operands[1:])

	return output[0], output[1]


def write (file_path: str, operators: list, operands: list):
	with open(file_path, 'w', encoding='utf-8') as file:
		file.write(encode(operators, operands, {'newline':True}))


#### CLI ####

# Execute and output an SQL query
def sql(qry_sql):
	rows = select(qry_sql, [])
	for row in rows: print(row)


# Search for memes from a memelang query string
def qry(mqry):
	operators, operands = decode(mqry)
	print ("QUERY:    ", encode(operators, operands))
	print("OPERATORS:", [K[op] for op in operators])
	print("OPERANDS: ", operands)

	sql, params = querify(mqry, DB_TABLE_MEME, False)
	full_sql = morfigy(sql, params)
	print(f"SQL: {full_sql}\n")

	# Execute query
	print(f"RESULTS:")
	print(get(mqry, I['key']))
	print()
	print()


# Read a meme file and save it
def putfile(file_path):
	operators, operands = read(file_path)
	operators, operands = put(operators, operands)
	out(operators, operands)


#### DB ADMIN ####

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


def qrytest():
	queries=[
		'george_washington',
		'george_washington]',
		'george_washington[',
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
		'george_washington;; john_adams;;',
	]
	errcnt=0

	for mqry in queries:
		operators, operands = decode(mqry)
		print('Operators:', [K[op] for op in operators])
		print('Operands:', operands)

		print('Query 1:  ', mqry)

		for i in range(2,5):
			mqry2 = encode(operators, operands)
			operators, operands = decode(mqry2)
			print(f'Query {i}: ', mqry2)

		sql, params = querify(mqry)
		print('SQL: ', morfigy(sql, params))
		
		c1=count(mqry)
		c2=count(mqry2)
		print ('First Count:  ', c1)
		print ('Second Count: ', c2)

		if not c1 or c1!=c2:
			print()
			print('*** COUNT ERROR ABOVE ***')
			errcnt+=1

		print()
	print("ERRORS:", errcnt)
	print()


def coreadd():
	mqry=''
	for key in I: mqry+=f'{I[key]}[nam]key="{key}";'
	operators, operands = decode(mqry)
	put(operators, operands)
	out(operators, operands)


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

	else:
		sys.exit("MAIN.PY ERROR: Invalid command");