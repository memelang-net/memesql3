import re
import html
import psycopg2
from conf import *

#### SETUP ####
# These are settings for handling Memelang queries. Storing 
# these in variables makes them overly explicit, but reduces
# encoding if/else logic in the later functions.

# Column order
V  = 0
VO = 1
A  = 2
C  = 3
D  = 4
B  = 5
WO = 6
W  = 7
MEMELEN = 8
SEMILEN = 0.5

ACDB     = [I['-:'], I['-]'], I[']'], I[':']]
VOACDB   = [I['-.'], I['-==']] + ACDB
MEMEROW  = VOACDB + [I['=='], I['.']]
NAMEROW  = VOACDB + [I['=='], I['"']]

# Forms
NON    = 1.1		# Value has no form, like END
INT    = 1.2		# Value is integer, like True, False, Get
DEC    = 1.3		# Value is decimal number
AID    = 1.4		# Value is an ID integer
STR    = 1.5		# Value is a string

# Each operator and its meaning
OPR = {
	I[']']: {
		'form' : AID,
		'dcol' : 'did',
		'dval' : I['is'],
		'out'  : [']', STR],
	},
	I[']]']: {
		'form' : AID,
		'dcol' : 'did',
		'dval' : None,
		'out'  : [']', STR],
	},
	I[':']: {
		'form' : AID,
		'dcol' : 'bid',
		'dval' : None,
		'out'  : [']', STR]
	},
	I['==']: {
		'form' : AID,
		'dcol' : 'wop',
		'dval' : I['=T'],
		'out'  : [AID],
	},
	I['"']: {
		'form' : STR,
		'dcol' : 'str',
		'dval' : None,
		'out'  : [STR, '"'],
	},
	I['.']: {
		'form' : DEC,
		'dcol' : 'wal',
		'dval' : I['t'],
		'out'  : [DEC],
	},
	I['|']: {
		'form' : INT,
		'dcol' : None,
		'dval' : None,
		'out'  : [''],
	},
	I['&&']: {
		'form' : AID,
		'dcol' : None,
		'dval' : I['&'],
		'out'  : [' '],
	},
	I[';']: {
		'form' : NON,
		'dcol' : None,
		'dval' : SEMILEN,
		'out'  : [';'],
	},
	I['opr']: { # Actually starts operators, treat as close of non-existant prior statement
		'form' : NON,
		'dcol' : None,
		'dval' : I['mix'],
		'out'  : [''],
	},

	I['-]']: {
		'form' : AID,
		'dcol' : 'cid',
		'dval' : I['is'],
		'out'  : ['[', STR],
	},
	I['-]]']: {
		'form' : AID,
		'dcol' : 'cid',
		'dval' : None,
		'out'  : ['[', STR],
	},
	I['-:']: {
		'form' : AID,
		'dcol' : 'aid',
		'dval' : None,
		'out'  : [STR],
	},
	I['-==']: {
		'form' : AID,
		'dcol' : 'vop',
		'dval' : I['=T'],
		'out'  : [AID],
	},
	I['-.']: {
		'form' : DEC,
		'dcol' : 'val',
		'dval' : I['t'],
		'out'  : [DEC],
	},
}

# For tokenize()
INCOMPLETE = 1
INTERMEDIATE = 2
COMPLETE = 3
STRTOK = {
	"!"  : INCOMPLETE,
	">"  : INTERMEDIATE,
	"<"  : INTERMEDIATE,
	"="  : COMPLETE,
	"!=" : COMPLETE,
	">=" : COMPLETE,
	"<=" : COMPLETE,
	"["  : COMPLETE,
	"]"  : COMPLETE,
	";"  : COMPLETE,
	' '  : COMPLETE,
}

# For operize()
TOKOPR = {
	">"  : [I['=='], I['>']],
	"<"  : [I['=='], I['<']],
	"="  : [I['=='], I['=']],
	"!=" : [I['=='], I['!=']],
	">=" : [I['=='], I['>=']],
	"<=" : [I['=='], I['<=']],
	"["  : [I['-]'], 'next'],
	"]"  : [I[']'], 'next'],
	";"  : [I[';'], SEMILEN],
	' '  : [I['&&'], I['&']],
}

# For resequence()
SEQ = {
	0 : { # V= and =W
		(I['=='], I['?']) : ('keep', I['.']),
		(I['-?'], I['-==']) : (I['-.'], 'keep'),
	},
	1 : { # First A
		(I[';'], I['-?']) : ('keep', I['-:']),
		# Turn last ]D into ]B
		(I[']'], I[';']) : (I[':'], 'keep'),
		(I[']'], I['&&']) : (I[':'], 'keep'),
		(I[']'], I['==']) : (I[':'], 'keep'),
	},
	2 : { # Turn ] into ]]
		(I[']'], I[']']) : ('keep', I[']]']),
		(I[']]'], I[']']) : ('keep', I[']]']),
		(I['-]'], I['-]']) : (I['-]]'], 'keep'),
		(I['-]'], I['-]]']) : (I['-]]'], 'keep'),
	},
	3 : { # Remove extras
		(I['-]'], I[']']) : ('removeEmpty', 'keep'),
	},
	4 : { # Expand and normalize to V=A[C]D]B=W
		(I['-:'], I[']'])          : ('keep', I['-]'], 'keep'),
		(I[';'], I['-:'])          : ('keep', I['-=='], 'keep'),
		(I[':'], I[';'])           : ('keep', I['=='], 'keep'),
	},
	5 : { # Expand and normalize to V=A[C]D]B=W
		(I[';'], I['-=='])          : ('keep', I['-.'], 'keep'),
		(I['=='], I[';'])           : ('keep', I['.'], 'keep'),
	},
	6 : { # Merge double semi-colon
		(I[';'], I[';']) : ('kill', 'keep'),
	}
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


def maxnum(col: str = 'aid', table: str = None):
	if not table: table=DB_TABLE_MEME
	result = select(f"SELECT MAX({col}) FROM {table}")
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
def parse(mqry: str):
	tokens = tokenize(mqry)
	operators, operands = operize(tokens)
	resequence(operators, operands)
	return operators, operands


# Input: Memelang string: ax]dy]bz>=w
# Output: list of tokens ['ax', ']', 'dy', ']', 'bz', '>=', 'w']
def tokenize(mqry: str):
	# Replace multiple spaces with a single space
	mqry = ' '.join(str(mqry).strip().split())

	# Remove comments
	mqry = re.sub(r'\s*//.*$', '', mqry, flags=re.MULTILINE)

	# Remove spaces around operators
	mqry = re.sub(r'\s*([;!<>=]+)\s*', r'\1', mqry)

	# Prepend zero before decimals, such as =.5 to =0.5
	mqry = re.sub(r'([<>=])(\-?)\.([0-9])', lambda m: f"{m.group(1)}{m.group(2)}0.{m.group(3)}", mqry)

	mqry_len = len(mqry)
	if mqry_len == 0: raise Exception("Error: Empty query provided.")

	tokens = []

	i = 0
	while i < mqry_len:
		token = mqry[i]

		# Operators
		if STRTOK.get(token):
			if STRTOK[token]<COMPLETE:
				if i < mqry_len-1 and STRTOK.get(token+mqry[i+1]):
					token+=mqry[i+1]
					i+=1
				elif STRTOK[token] == INCOMPLETE:
					raise Exception(f"Incomplete operator {token} at {token} in {mqry}")

			tokens.append(token)
			i += 1

		# Double-quote string ="George Washtingon's Horse \"Blueskin\""
		elif token == '"':
			while i < mqry_len-1:
				i += 1
				if mqry[i]=='\\': continue
				token += mqry[i]
				if mqry[i]=='"': break

			tokens.append(token)
			i += 1

		# key/int/float
		else:
			m = re.match(r'[a-z0-9\_\.\-]+', mqry[i:])
			if not m: raise Exception(f"Memelang parse error: Unexpected '{mqry[i]}' at char {i} in {mqry}")
			tokens.append(m.group())
			i += len(m.group())

	return tokens


# Input: list of string tokens
# Outout: operators, operands
def operize(tokens: list):
	operators = [I['opr']]
	operands = [I['mix']]

	if tokens[0]!=';': tokens.insert(0, ';')
	if tokens[-1]!=';': tokens.append(';')

	beg = 0
	side = -1
	t = 0
	tlen = len(tokens)
	while t < tlen:
		token=tokens[t]
		operand = token

		# Operator
		if TOKOPR.get(token):
			operator, operand = TOKOPR[token]

			if operand=='next':
				if t+1 < tlen and re.match(r'[a-z0-9]', tokens[t+1]):
					t+=1
					operand = tokens[t]
				else: operand = None
	
		# Quote
		elif operand[0]=='"':
			operator = I['"']
			operand = operand[1:-1]

		# Floating point
		elif '.' in operand: operator = I['.']

		# String or Int ID
		else:
			operator = I['?']
			if operand in ('f','t','g'): operand=I[operand]


		if operator==I[';']:
			beg=len(operators)
			side=-1

		else:
			operands[beg]+=1
			if operator==I[']']: side=1

			# Float or Int operand
			if operator != I['"'] and isinstance(operand, str):
				if '.' in operand: operand=float(operand)
				elif re.match(r'^-?[0-9]+$', operand): operand=int(operand)
	
		operators.append(operator*(1 if operator<0 or operator==I[';'] else side))
		operands.append(operand)

		t+=1

	return operators, operands


# Input: operators, operands
# Rationalizes operators and operands
# Output: (mutates operators operands)
def resequence(operators: list, operands: list, phases: list = [0,1,2,3]):
	olen=len(operators)
	for phase in phases:
		o=0
		while o<olen:
			if operators[o]==I[';']: beg=o
			if SEQ[phase].get(tuple(operators[o:o+2])):
				offset=0
				instructions=SEQ[phase].get(tuple(operators[o:o+2]))

				for i, instr in enumerate(instructions):
					if i==1 and len(instructions)>2:
						operators.insert(o+i+offset, instr)
						operands.insert(o+i+offset, OPR[instr]['dval'])
						offset += 1
					elif isinstance(instr, int): operators[o+i+offset]=instr
					elif instr == 'keep': continue
					elif instr == 'kill':
						operators.pop(o+i+offset)
						operands.pop(o+i+offset)
						olen-=1
					elif instr == 'remove':
						operators.pop(o+i+offset)
						operands.pop(o+i+offset)
						offset-=1
					elif instr == 'removeEmpty':
						if operands[o+i+offset] is None:
							operators.pop(o+i+offset)
							operands.pop(o+i+offset)
							offset-=1
				olen+=offset
				operands[beg]+=offset
			o+=1


# Input: operators, operands
# Output: Memelang string operator1operand1operator2operand2
def deparse(operators: list, operands: list, deparse_set=None) -> str:

	if not deparse_set: deparse_set={}
	mqry = ''

	for o,operator in enumerate(operators):
		if o<2: continue
		expression=''
		for fld in OPR[operator]['out']:
			if fld == DEC:
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

		if operator == I[';'] and deparse_set.get('newline'): expression+="\n"

		# Append the deparsed expression
		if deparse_set.get('html'): mqry += '<var class="v' + str(operator) + '">' + html.escape(expression) + '</var>'
		else: mqry += expression

	if deparse_set.get('html'): mqry = '<code class="meme">' + mqry + '</code>'

	# FIX LATER
	mqry = mqry.replace('1.0=T', 't=').replace('=T1.0', '=t').replace(';;', ';')

	return mqry

def out (operators: list, operands: list):
	print(deparse(operators, operands, {'newline': True}))



#### MEMELANG-SQL CONVERSION ####

# Input: Memelang query string
# Output: SQL query string
def querify(mqry: str, meme_table: str = None, name_table: str = None):
	if not meme_table: meme_table=DB_TABLE_MEME
	if not name_table: name_table=DB_TABLE_NAME

	operators, operands = parse(mqry)

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

	return ['WITH ' + ', '.join(ctes) + ' ' + ' UNION '.join(selects), params]

# Input: operators and operands for one Memelang command
# Output: One SQL query string
def subquerify(operators: list, operands: list, meme_table: str = None, cte_beg: int = 0):
	if not meme_table: meme_table=DB_TABLE_MEME
	qry_set = {'all': False, 'of': False}
	or_groups = {}
	false_group = []
	get_group = []
	or_cnt = 0
	false_cnt = 0
	skip = False

	olen=len(operators)
	o=0
	beg=0
	markers=[]
	while o<olen:
		if operators[o]==-I[':'] and operands[o]==I['qry']:
			qry_set[operands[o+1]]=True
			skip=True
		elif operators[o]==I['&&']:
			if not skip: markers.append([beg, o])
			skip=False
			beg=o
		elif o==olen-1 and not skip: markers.append([beg, o+1])
		o+=1

	for beg, end in markers:
		found=False
		for o, operator in enumerate(operators):
			operand=operands[o]
			if operator == I['==']: 
				# Handle =f (false)
				if operand == I['=F']:
					false_cnt += 1
					false_group.append([operators[beg:end], operands[beg:end]])
					found=True
					break
				# Handle =g (get)
				if operand == I['=G']:
					get_group.append([operators[beg:end], operands[beg:end]])
					found=True
					break
			# Handle =tn (OR groups)
			elif operator == I['|']:
				or_cnt += 1
				if not or_groups.get(operand): or_groups[operand]=[]
				or_groups[operand].append([operators[beg:end], operands[beg:end]])
				found=True
				break

		# Default: Add to true conditions
		if not found:
			or_cnt += 1
			or_groups[99+or_cnt]=[[operators[beg:end], operands[beg:end]]]

	# If qry_set['all'] and no true/false/or conditions
	if qry_set.get(I['all']) and false_cnt == 0 and or_cnt == 0:
		return [f"SELECT * FROM {meme_table}", []]

	cte_cnt  = cte_beg
	params   = []
	cte_sqls = []
	cte_outs = []
	sql_outs = []

	# Process OR groups
	for or_group in or_groups.values():
		max_depth = 0
		or_selects = []
		for suboperators, suboperands in or_group:
			select_sql, from_sql, where_sql, qry_params, qry_depth = selectify(suboperators, suboperands, meme_table)
			max_depth = max(max_depth, qry_depth)

			if cte_cnt > cte_beg: where_sql += f" AND m0.aid IN (SELECT a0 FROM z{cte_cnt})"

			or_selects.append(f"SELECT {select_sql} {from_sql} WHERE {where_sql}")
			params.extend(qry_params)

		cte_cnt += 1
		cte_sqls.append(f"z{cte_cnt} AS ({' UNION '.join(or_selects)})")
		cte_outs.append((cte_cnt, max_depth))

	# Process NOT conditions (false_group)
	if false_cnt:
		if or_cnt < 1:
			raise Exception('A query with a false statement must contain at least one non-OR true statement.')

		wheres = []
		for suboperators, suboperands in false_group:
			select_sql, from_sql, where_sql, qry_params, qry_depth = selectify(suboperators, suboperands, meme_table, True)
			wheres.append(f"a0 NOT IN (SELECT {select_sql} {from_sql} WHERE {where_sql})")
			params.extend(qry_params)

		fsql = f"SELECT aid FROM z{cte_cnt} WHERE " + ' AND '.join(wheres)
		cte_cnt += 1
		cte_sqls.append(f"z{cte_cnt} AS ({fsql})")


	# select all data related to the matching As
	if qry_set.get(I['all']):
		sql_outs.append(f"SELECT val as v0, vop as vo0, aid as a0, cid as c0, did as r0, bid as b0, wop as wo0, wal as w0 FROM {meme_table} m0 WHERE m0.aid IN (SELECT a0 FROM z{cte_cnt})")

	else:
		for suboperators, suboperands in get_group:
			select_sql, from_sql, where_sql, qry_params, qry_depth = selectify(suboperators, suboperands, meme_table)
			sql_outs.append(f"SELECT {select_sql} {from_sql} WHERE {where_sql} AND m0.aid IN (SELECT a0 FROM z{cte_cnt})")
			params.extend(qry_params)

	for zNum, mNum in cte_outs:
		cWhere='';
		if zNum < cte_cnt: cWhere=f" WHERE a0 IN (SELECT a0 FROM z{cte_cnt})"

		m=0;
		while mNum>=m:
			sql_outs.append(f"SELECT DISTINCT v{m}, vo{m}, a{m}, c{m}, r{m}, b{m}, wo{m}, w{m} FROM z{zNum}{cWhere}")
			m+=1

	# Apply logic to As
	if qry_set.get(I['of']):
		sql_outs.append(f"SELECT m0.val AS v0, m0.vop AS o0, m0.aid AS a0, '{I['of']}' AS c0, z.did AS r0, z.bid AS b0, z.wop AS wo0, z.wal AS w0 FROM {meme_table} m0 JOIN z{cte_cnt} AS z ON m0.aid = z.bid AND m0.cid = z.did WHERE m0.cid={I['is']}")

	return cte_sqls, sql_outs, params


# Input: operators and operands for one Memelang statement
# Output: SELECT string, FROM string, WHERE string, and depth int
def selectify(operators: list, operands: list, meme_table=None, aidOnly=False):
	if not meme_table: meme_table=DB_TABLE_MEME

	params = []
	wheres = []
	joins = [f"FROM {meme_table} m0"]
	selects = ['m0.val AS v0','m0.vop AS vo0','m0.aid AS a0','m0.cid AS c0','m0.did AS r0','m0.bid AS b0','m0.wop AS wo0','m0.wal AS w0']
	m = 0
	last_rel_end='bid'
	wop='='

	for i, operator in enumerate(operators):
		operand = operands[i]
		form = OPR[operator]['form']
		dcol = OPR[operator]['dcol']

		if operator in (I['-]]'], I['-=='], I['-.']):
			raise Exception(f'Operator {K[operator]} is not supported yet')

		elif dcol=='wop': 
			wop=K[int(operand)]
			continue

		# Invert first meme
		elif operator == I[']'] and operand is not None and operand<0:
			selects = ['m0.val AS v0','m0.vop AS vo0','m0.bid AS a0','m0.cid AS c0','m0.did*-1 AS r0','m0.aid AS b0','m0.wop AS wo0','m0.wal AS w0']

		# Chain memes
		elif operator == I[']]']:
			m += 1
			wheres.extend([f'm{m}.cid=%s'])
			params.extend([I['is']])

			if operand is not None and operand<0:
				joins.append(f"JOIN {meme_table} m{m} ON m{m-1}.{last_rel_end}=m{m}.bid")
				selects.append(f"m{m}.val AS v{m}")
				selects.append(f"m{m}.vop AS vo{m}")
				selects.append(f"m{m}.bid AS a{m}")
				selects.append(f"m{m}.cid AS c{m}")
				selects.append(f"m{m}.did*-1 AS r{m}")
				selects.append(f"m{m}.aid AS b{m}")
				selects.append(f"m{m}.wop AS wo{m}")
				selects.append(f"m{m}.wal AS w{m}")
			else:
				joins.append(f"JOIN {meme_table} m{m} ON m{m-1}.{last_rel_end}=m{m}.aid")
				selects.append(f"m{m}.val AS v{m}")
				selects.append(f"m{m}.vop AS vo{m}")
				selects.append(f"m{m}.aid AS a{m}")
				selects.append(f"m{m}.cid AS c{m}")
				selects.append(f"m{m}.did AS r{m}")
				selects.append(f"m{m}.bid AS b{m}")
				selects.append(f"m{m}.wop AS wo{m}")
				selects.append(f"m{m}.wal AS w{m}")

			last_rel_end = 'aid' if operand is not None and operand<0 else 'bid'

		
		if dcol and operand is not None:
			if form in (INT, AID): operand=int(operand)
			elif form == DEC: operand=float(operand)
			else: raise Exception('invalid form')

			eql = wop if dcol=='wal' else '='

			wheres.append(f'm{m}.{dcol}{eql}%s')
			params.append(operand)

	if aidOnly: selects = ['m0.aid AS a0']

	return [
		', '.join(selects),
		' '.join(joins),
		' AND '.join(wheres),
		params,
		m
	]


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
def identify(keys: list, name_table: str = None):
	if not name_table: name_table=DB_TABLE_NAME
	ids = []

	if not keys: return ids

	lookups=[]
	for key in keys:
		if isinstance(key, str):
			lookups.append(key if key[0]!='-' else key[1:])

	aidcache(lookups, name_table)

	for key in keys:
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

def nxt(operators: list, operands: list, beg: int = 1):
	olen=len(operators)
	if beg>=olen: return False
	elif operators[beg]!=I[';']: raise Exception(f'Operator counting error at {beg} for {operators[beg]}')
	return beg+1+int(operands[beg])


# Input a Memelang query string
# Replace keys with aids
# Execute in DB
# Return results (optionally with "qry.nam:key=1")
def get(mqry: str, meme_table: str = None, name_table: str = None):
	if not meme_table: meme_table=DB_TABLE_MEME
	if not name_table: name_table=DB_TABLE_NAME
	output=[[I['opr']], [I['id']]]
	mqry, namekeys = dename(mqry)
	sql, params = querify(mqry, meme_table)
	memes = select(sql, params)

	for meme in memes:
		output[0].extend([I[';']] + MEMEROW)
		output[1].extend([SEMILEN+MEMELEN] + meme)

	if namekeys: output.extend(namify(output[1], namekeys, name_table))

	return output

# Return meme count of above results
def count(mqry: str, meme_table: str = None, name_table: str = None):
	sql, params = querify(mqry, meme_table, name_table)
	return len(select(sql, params))


def put (operators: list, operands: list, meme_table: str = None, name_table: str = None):
	if not operators: return operators, operands
	if not meme_table: meme_table=DB_TABLE_MEME
	if not name_table: name_table=DB_TABLE_NAME

	# Load IDs
	aidcache(operands)

	# Normalize memes
	resequence(operators, operands, [4,5,6])

	missings = {}
	sqls = {meme_table:[], name_table:[]}
	params = {meme_table:[], name_table:[]}

	# Swap keys with IDs or mark key missing
	o=2
	olen=len(operators)
	while o<olen:
		if OPR[abs(operators[o])]['form']==AID:
			if isinstance(operands[o], int): pass
			elif str(operands[o]).isdigit(): operands[o]=int(operands[o])
			elif I.get(operands[o]): operands[o]=I[operands[o]]
			else: missings[operands[o]]=1
		o+=1

	# Mark id-key for writing from id]nam]key="xyz"
	end=1
	while (end := nxt(operators, operands, (beg := end))):
		beg+=1
		if end-beg==MEMELEN and operators[beg:end]==NAMEROW and operands[beg+D]==I['nam'] and operands[beg+B]==I['key']:
			key = operands[beg+W]
			aid = operands[beg+A]
			missings.pop(key, None)
			sqls[name_table].append("(%s,%s,%s)")
			params[name_table].extend([aid, I['key'], key])
			I[key]=aid
			K[aid]=key

	# Select new ID for missing keys with no associated ID
	if missings:
		aid = maxnum('aid', name_table) or I['cor']
		for key, val in missings.items():
			aid += 1
			sqls[name_table].append("(%s,%s,%s)")
			params[name_table].extend([aid, I['key'], key])
			I[key]=aid
			K[aid]=key

	# Swap missing keys for new IDs
	o=2
	while o<olen:
		if OPR[abs(operators[o])]['form']==AID and isinstance(operands[o], str): operands[o]=I[operands[o]]
		o+=1

	# Pull out non-key names and truths
	end=1
	while (end := nxt(operators, operands, (beg := end))):
		beg+=1
		if end-beg==MEMELEN and operators[beg:end-2]==VOACDB:

			# String name
			if operators[beg+W]==I['"']:
				if operands[beg+B]!=I['key']:
					params[name_table].extend([operands[beg+A], operands[beg+B], operands[beg+W]])
					sqls[name_table].append('(%s,%s,%s)')

			# True/False/Float V=A[C]D]B=W
			else:
				params[meme_table].extend(operands[beg:end])
				sqls[meme_table].append('(%s,%s,%s,%s,%s,%s,%s,%s)')
		#else: print('skip', operators[beg:end-2], VOACDB, operators[beg:end], operands[beg:end])

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


# Apply logic
def logify (operators: list, operands: list):
	ACs = {}

	# Pull out A[C]D]B logic rules
	end=1
	while (end := nxt(operators, operands, (beg := end))):
		beg+=1
		if end-beg==MEMELEN+1 and operators[beg:end-2]==VOACDB and operands[beg+C]!=I['is']:
			if not ACs.get(operands[beg+A]): ACs[operands[beg+A]]={}
			if not ACs[operands[beg+A]].get(operands[beg+C]): ACs[operands[beg+A]][operands[beg+C]]=[]
			ACs[operands[beg+A]][operands[beg+C]].append(beg)

	# Apply A[C]D]B=t rules to C for X]C]A => X]D]B=t
	end=1
	while (end := nxt(operators, operands, (beg := end))):
		beg+=1
		if slen and operators[beg:end-2] == VOACDB and operands[beg+C]==I['is'] and ACs.get(operands[beg+B]) and ACs[operands[beg+B]].get(operands[beg+D]):
			for lobeg in ACs[operands[beg+B]][operands[beg+D]]:
				operators.extend([I[';']] + VOACDB)
				operands.extend([SEMILEN+MEMELEN, I['t'], I['=T'], operands[beg+A], I['of'], operands[lobeg+D], operands[lobeg+B], operands[lobeg+WO], operands[lobeg+W]])


#### MEME FILE ####

def read (file_path: str):
	output = [[I['opr']],[I['mix']]]
	with open(file_path, 'r', encoding='utf-8') as f:
		for ln, line in enumerate(f, start=1):
			if line.strip() == '' or line.strip().startswith('//'): continue
			operators, operands = parse(line)
			if len(operators)>2:
				output[0].extend(operators[1:])
				output[1].extend(operands[1:])

	return output[0], output[1]


def write (file_path: str, operators: list, operands: list):
	with open(file_path, 'w', encoding='utf-8') as file:
		file.write(deparse(operators, operands, {'newline':True}))
