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
IMPL       = [I['['], I[']'], I['=='], I['.'], I['&&'], I['['], I[']'], I['=='], I['.']]

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

# Input: Memelang string operator1operand1operator2operand2
# Output: [operator1, operator2, ...], [operand1, operand2, ...]
def decode(mqry: str):

	# Replace multiple spaces with a single space
	mqry = ' '.join(str(mqry).strip().split())

	# Remove comments
	mqry = re.sub(r'\s*//.*$', '', mqry, flags=re.MULTILINE)

	# Remove spaces around operators
	mqry = re.sub(r'\s*([;!<>=]+)\s*', r'\1', mqry)

	# Append semicolon
	mqry+=';'

	mqry_len = len(mqry)
	if mqry_len == 0: raise Exception("Error: Empty query provided.")

	operators = [I['opr'], I[';']]
	operands = [I['mix'],SEMILEN]
	onext = False
	beg=1

	i = 0
	while i < mqry_len:
		token = mqry[i]

		# Double-quote string token "George Washtingon's Horse \"Blueskin\""
		if token == '"':
			while i < mqry_len-1:
				i += 1
				if mqry[i]=='\\': continue
				token += mqry[i]
				if mqry[i]== '"' and mqry[i-1]!='\\': break

			operators.append(I['$'])
			operands.append(token[1:-1])
			operands[beg]+=1
			i += 1

		# Operator token
		elif STRTOK.get(token):

			# Transform "{106}" token to ">="
			if token == '{':
				while i < mqry_len-1 and mqry[i]!='}':
					i += 1
					token += mqry[i]
				token=K[int(token[1:-1])]

			elif STRTOK[token][0]<COMPLETE and i < mqry_len-1 and STRTOK.get(token+mqry[i+1]):
				token+=mqry[i+1]
				i+=1

			if not STRTOK.get(token) or STRTOK[token][0] == INCOMPLETE:
				raise Exception(f"Incomplete operator {token} at {token} in {mqry}")

			completeness, operator, operand = STRTOK[token]

			if OPR[operator]['aftr']==I['@']:
				if operators[-1]==I[']']:
					operators.extend([I['=='], I['.']])
					operands.extend([I['#='], I['t']])
					operands[beg]+=2

			if operator==I[';']:
				# Skip double semicolons ;;
				if operators[-1]==I[';']:
					i += 1
					continue
				else: beg=len(operators)
			else: operands[beg]+=1

			operators.append(operator)
			operands.append(operand)
			i += 1

		# key/int/float token
		else:
			m = re.match(r'[a-z0-9\_\.\-]+', mqry[i:])
			if not m: raise Exception(f"Memelang decode error: Unexpected '{mqry[i]}' at char {i} in {mqry}")

			operator=I['?']
			if OPR[operators[-1]]['aftr']: operator=OPR[operators[-1]]['aftr']

			# format
			operand = m.group()
			if operand in ('f','t','g'): 
				operand=I[operand]
				operator=I['.']
				if operators[-1]==I['==']: operands[-1]=I['#=']
				else: raise Exception('True/float error')

			elif '.' in operand:
				operand=float(operand)
				operator=I['.']
			elif re.match(r'^-?[0-9]+$', operand):
				operand=int(operand)

			if OPR[operators[-1]]['aftr']==STR: operands[-1]=operand
			else:
				operators.append(operator)
				operands.append(operand)
				operands[beg]+=1

			i += len(m.group())

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
			if fld == FLT:
				sign = '-' if operands[o] < 0 else ''
				ones = str(abs(operands[o]))
				tenths = ''
				if '.' in ones: ones, tenths = ones.split('.')
				operand = sign + (ones.lstrip('0') or '0') + '.' + (tenths.rstrip('0') or '0')

			elif fld == STR: operand = '' if operands[o] is None else operands[o]

			elif fld == AID:
				if isinstance(operands[o], int): operand = K[operands[o]]
				else: operand = operands[o]

			else: operand=fld

			expression+=str(operand)

		if operator == I[';'] and encode_set.get('newline'): expression+="\n"

		# Append the encoded expression
		if encode_set.get('html'): mqry += '<var class="v' + str(operator) + '">' + html.escape(expression) + '</var>'
		else: mqry += expression

	if encode_set.get('html'): mqry = '<code class="meme">' + mqry + '</code>'

	# FIX LATER
	mqry = mqry.replace('t#=', 't=').replace('#=t', '=t').replace('1.0=T', 't=').replace('=T1.0', '=t').replace('1.0#=', 't=').replace('#=1.0', '=t').replace(';;', ';')

	return mqry


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

	operators, operands = decode(mqry)

	if name_table: 
		operands = identify(operands, name_table)
		missings = [x for x in operands if isinstance(x, str)]
		if missings: raise Exception("Unknown keys: " + ", ".join(missings))

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
		if operators[o]==-I['@'] and operands[o]==I['qry']:
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
	notwhere = None
	notparams = []

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
		sel_sqls.append(f"SELECT {qry_select} {from_sql} WHERE m0.aid IN (SELECT a0 FROM z{z})")

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

		# New row
		if (operator == I[']'] and prev_operator==I[']']) or (operator == I['['] and prev_operator in (I['['], I[']'])):
			m+=1
			qparts['select'][1]+=(f" || ']' || (bid{m-1})::text" if prev_operator==I[']'] else '') + f" || '[' || (rid{m})::text"
			qparts['join'].append(f"JOIN {meme_table} m{m} ON (bid{m-1})=(aid{m})")
			inversions.append(False)

		# Inversion
		if operator == I['['] and operand is not None and operand<0: inversions[m]=True

		prev_operator = operator

		if dcol == 'cpr':
			cpr=K[int(operand)]
			continue
	
		elif dcol and operand is not None:
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

	uncached_keys = [key for key in keys if isinstance(key, str) and key not in I]

	if not uncached_keys: return

	rows=selectin({'bid':[I['key']], 'str':uncached_keys}, name_table)

	for row in rows:
		I[row[2]] = int(row[0])
		K[int(row[0])] = row[2]


# Input value is a list of strings ['a', 'b', 'c', 'd']
# Load key->aid
# Return the data with any keys with ids
def identify(operands: list, name_table: str = None):
	if not name_table: name_table=DB_TABLE_NAME
	ids = []

	if not operands: return ids

	lookups=[]
	for key in operands:
		if isinstance(key, str):
			lookups.append(key if key[0]!='-' else key[1:])

	aidcache(lookups, name_table)

	for key in operands:
		if not isinstance(key, str): ids.append(key)
		elif key[0]=='-':
			if I.get(key[1:]): ids.append(I[key[1:]]*-1)
			else: ids.append(key)
		elif I.get(key): ids.append(I[key])
		else: ids.append(key)

	return ids


def identify1(val: str, name_table: str = None):
	if not name_table: name_table=DB_TABLE_NAME
	ids = identify([val], name_table)
	return ids[0] if isinstance(ids[0], int) else False


# Input value is a list of ints [123,456,789]
# Load aid->key
# Return the data with any aids replaced with keys
def namify(operands: list, bids: list, name_table: str = None):
	if not name_table: name_table=DB_TABLE_NAME
	missings=[]

	output = {}
	for bid in bids: output[bid]=[bid]

	matches = []
	for i,operand in enumerate(operands):
		if isinstance(operand, int): matches.append(abs(operands[i]))

	names = selectin({'aid' : matches, 'bid': bids}, name_table)

	namemap = {}
	for name in names:
		if not namemap.get(name[0]): namemap[int(name[0])]={}
		namemap[int(name[0])][int(name[1])]=name[2]

	for i,operand in enumerate(operands):
		if i==0: continue
		for bid in bids:
			if isinstance(operand, int):
				oprabs=abs(operand)
				if namemap.get(oprabs) and namemap[oprabs].get(bid): output[bid].append(('-' if operand<0 else '') + namemap[oprabs][bid])
				else: output[bid].append(False)
			else: output[bid].append(operand)

	return list(output.values())


#### PROCESS MEMELANG QUERY FOR SQL QUERY ####

# Input a Memelang query string
def get(mqry: str, meme_table: str = None, name_table: str = None):
	if not meme_table: meme_table=DB_TABLE_MEME
	if not name_table: name_table=DB_TABLE_NAME
	output=[[], []]
	mqry, namekeys = dename(mqry)
	sql, params = querify(mqry, meme_table, name_table)
	mres = select(sql, params)
	output[0], output[1] = decode(mres[0][0])

	if namekeys: output.extend(namify(output[1], namekeys, name_table))

	return output

# Return meme count of above results
def count(mqry: str, meme_table: str = None, name_table: str = None):
	sql, params = querify(mqry, meme_table, name_table)
	mres=select(sql, params)
	return 0 if not mres else mres[0][0].count(';')


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

	# Mark id-key for writing from id]nam]key="xyz"
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
				varmin=aggnum(aid, 'MIN', meme_table)
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


# Remove name statement from query
def dename(mqry: str):
	terms = re.split(r'[\s\;]+', mqry)
	remaining_terms = []

	pattern = re.compile(r'^qry\]nam\]([a-z]+)')
	extracted_terms = []
	for term in terms:
		m = pattern.match(term)
		if m: extracted_terms.append(m.group(1))
		elif term: remaining_terms.append(term)

	# Reconstruct the remaining string
	return ' '.join(remaining_terms), identify(list(set(extracted_terms)))


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
	for row in rows:
		print(row)


# Search for memes from a memelang query string
def qry(mqry):
	operators, operands = decode(mqry)
	print ("QUERY:    ", encode(operators, operands))
	print("OPERATORS:", [K[op] for op in operators])
	print("OPERANDS: ", operands)

	sql, params = querify(mqry, DB_TABLE_MEME, False)
	params = identify(params)
	full_sql = morfigy(sql, params)
	print(f"SQL: {full_sql}\n")

	# Execute query
	print(f"RESULTS:")
	memes = get(mqry+' qry[nam]key')
	out(memes[0], memes[2])
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
		print('First Query:  ', mqry)
		operators, operands = decode(mqry)
		print('Operators:', [K[op] for op in operators])
		print('Operands:', operands)
		mqry2 = encode(operators, operands)
		print('Second Query: ', mqry2)
		sql, params = querify(mqry, DB_TABLE_MEME, False)
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