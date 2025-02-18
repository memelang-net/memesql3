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

#          AID       CID     DID     BID
ACDB     = [I['-]'], I['['], I['['], I[']']]

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
		'dcol' : 'bid',
		'dval' : None,
		'out'  : [']', STR]
	},
	I['[']: {
		'form' : AID,
		'dcol' : 'did',
		'dval' : I['is'],
		'out'  : ['[', STR],
	},
	I['==']: {
		'form' : AID,
		'dcol' : 'wop',
		'dval' : I['#='],
		'out'  : [AID],
	},
	I['"']: {
		'form' : STR,
		'dcol' : 'str',
		'dval' : None,
		'out'  : ['"', STR, '"'],
	},
	I['.']: {
		'form' : DEC,
		'dcol' : 'wal',
		'dval' : I['t'],
		'out'  : [DEC],
	},
	I['||']: {
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
		'dcol' : 'aid',
		'dval' : None,
		'out'  : [STR],
	},
	I['-==']: {
		'form' : AID,
		'dcol' : 'vop',
		'dval' : I['#='],
		'out'  : [AID],
	},
	I['-.']: {
		'form' : DEC,
		'dcol' : 'val',
		'dval' : I['t'],
		'out'  : [DEC],
	},
}

# For operate()
INCOMPLETE = 1
INTERMEDIATE = 2
COMPLETE = 3
STRTOK = {
	"!"  : [INCOMPLETE, None, None],
	"{"  : [INCOMPLETE, None, None],
	"#"  : [INCOMPLETE, None, None],
	">"  : [INTERMEDIATE, I['=='], I['>']],
	"<"  : [INTERMEDIATE,I['=='], I['<']],
	"="  : [COMPLETE, I['=='], I['=']],
	"!=" : [COMPLETE, I['=='], I['!=']],
	"#=" : [COMPLETE, I['=='], I['#=']],
	">=" : [COMPLETE, I['=='], I['>=']],
	"<=" : [COMPLETE, I['=='], I['<=']],
	"["  : [COMPLETE, I['['], 'next'],
	"]"  : [COMPLETE, I[']'], 'next'],
	";"  : [COMPLETE, I[';'], SEMILEN],
	' '  : [COMPLETE, I['&&'], I['&']]
}


# For resequence()
SEQ = {
	0 : { # Determine equalities
		(I['=='], I['?']) : ('keep', I['.']),
		(I['-?'], I['-==']) : (I['-.'], 'keep'),
		(I['-=='], I['-?']) : ('keep', I['-]']),
		(I[';'], I['-?']) : ('keep', I['-]']),
	},
	1 : { # Remove unnecessary operators
		(I[';'], I['-]']) : ['keep','empty'],
		(I['=='], I['-]']) : ['keep','empty'],
		(I['['], I[']']) : ['keep','empty'],
		(I['-]'], I[']']) : ['keep','empty'],
		(I[';'], I[';']) 	: ('kill', 'keep'),
	},
	2 : { # Expand and normalize to V=A[C]D]B=W
		#(I['['], I['['])    : ('insert', I[']']),
		(I[';'], I['-]'])   : ('insert', I['-.'], I['-==']),
		(I[']'], I[';'])    : ('insert', I['=='], I['.']),
	},
	3 : { # Add [is
		(I['-]'], I['['], I[']'], I['=='])    : ('insert', I['[']),
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
	operators, operands  = operate(mqry)
	resequence(operators, operands)
	return operators, operands


# Input: Memelang string: ax[dy]bz>=w
# Output: [operator1, operator2, ...], [operand1, operand2, ...]
def operate(mqry: str):
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

	operators = [I['opr'], I[';']]
	operands = [I['mix'],SEMILEN]
	onext = False
	beg=1
	side=-1

	i = 0
	while i < mqry_len:
		token = mqry[i]

		# Double-quote string token "George Washtingon's Horse \"Blueskin\""
		if token == '"':
			while i < mqry_len-1:
				i += 1
				if mqry[i]=='\\': continue
				token += mqry[i]
				if mqry[i]=='"': break

			operators.append(I['"'])
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

			if operand=='next':
				onext=True
				operand=None
				side=1
			else: 
				onext=False

			if operator==I[';']:
				beg=len(operators)
				side=-1
			else:
				operands[beg]+=1
				operator*=side
			
			operators.append(operator)
			operands.append(operand)
			i += 1

		# key/int/float token
		else:
			m = re.match(r'[a-z0-9\_\.\-]+', mqry[i:])
			if not m: raise Exception(f"Memelang parse error: Unexpected '{mqry[i]}' at char {i} in {mqry}")

			# format
			operand = m.group()
			if operand in ('f','t','g'):            operand=I[operand]
			elif '.' in operand:                    operand=float(operand)
			elif re.match(r'^-?[0-9]+$', operand):  operand=int(operand)

			if onext: operands[-1]=operand
			else:
				operators.append((I['.'] if isinstance(operand, float) else I['?'])*side)
				operands.append(operand)
				operands[beg]+=1

			i += len(m.group())

	return operators, operands


# Input: operators, operands
# Rationalizes operators and operands
# Output: (mutates operators operands)
def resequence(operators: list, operands: list, phase = 0):

	if operators[-1]!=I[';']:
		operators.append(I[';'])
		operands.append(SEMILEN)

	olen=len(operators)
	o=0
	while o<olen:
		if operators[o]==I[';']: beg=o
		matched=False

		for seq in SEQ[phase]:
			if tuple(operators[o:o+len(seq)])!=seq: continue
			matched=True
			i=0
			offset=0
			instrs=SEQ[phase][seq]
			ilen=len(instrs)
			while i<ilen:
				instr=instrs[i]
				if instr == 'keep': pass
				elif instr == 'insert':
					i+=1
					while i<ilen:
						operators.insert(o+i, instrs[i])
						operands.insert(o+i, OPR[instrs[i]]['dval'])
						offset += 1
						i+=1
				elif isinstance(instr, int): operators[o+i+offset]=instr
				elif instr == 'kill':
					operators.pop(o+i+offset)
					operands.pop(o+i+offset)
					olen-=1
				elif instr == 'empty':
					if operands[o+i+offset] is None:
						operators.pop(o+i+offset)
						operands.pop(o+i+offset)
						offset-=1
				i+=1
			
			olen+=offset
			operands[beg]+=offset

		if not matched: o+=1

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
	mqry = mqry.replace('1.0=T', 't=').replace('=T1.0', '=t').replace('1.0#=', 't=').replace('#=1.0', '=t').replace(';;', ';')

	return mqry

def out (operators: list, operands: list):
	print(deparse(operators, operands, {'newline': True}))


def nxt(operators: list, operands: list, beg: int = 1):
	olen=len(operators)
	if beg>=olen: return False
	elif operators[beg]!=I[';']: raise Exception(f'Operator counting error at {beg} for {operators[beg]}')
	return beg+1+int(operands[beg])


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
	groups={'false':{0:[]},'get':{0:[]}, 'true':{}}

	skip = False
	gkey='true'
	gnum=1000

	o=0
	beg=o
	olen=len(operators)
	while o<olen:
		if operators[o]==-I['-]'] and operands[o]==I['qry']:
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

		elif operators[o]==I['&&'] or o==olen-1:
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
		select_sql, from_sql, where_sql, qry_params = selectify([], [], meme_table)
		return [f"SELECT select_sql FROM {meme_table}", []]

	cte_cnt  = cte_beg
	params   = []
	cte_sqls = []
	sel_sqls = []
	notwheres = []
	notparams = []

	# Process NOT groups
	if false_cnt:
		if or_cnt < 1: raise Exception('A query with a false statement must contain at least one true statement.')

		for suboperators, suboperands in groups['false'][0]:
			select_sql, from_sql, where_sql, qry_params = selectify(suboperators, suboperands, meme_table, True)
			notwheres.append(f"m0.aid NOT IN (SELECT {select_sql} {from_sql} WHERE {where_sql})")
			notparams.extend(qry_params)

	# Process OR groups
	for gnum in groups['true']:
		or_selects = []
		for suboperators, suboperands in groups['true'][gnum]:
			select_sql, from_sql, where_sql, qry_params = selectify(suboperators, suboperands, meme_table)

			or_sql = f"SELECT {select_sql} {from_sql} WHERE {where_sql}"
			if cte_cnt==cte_beg:
				# FIX LATER
				if notwheres: 
					or_sql+=' AND ' + ' AND '.join(notwheres)
					qry_params.extend(notparams)
					notwheres=[]

			else: or_sql+=f" AND m0.aid IN (SELECT a0 FROM z{cte_cnt})"

			or_selects.append(or_sql)
			params.extend(qry_params)
		cte_cnt += 1
		cte_sqls.append(f"z{cte_cnt} AS ({' UNION '.join(or_selects)})")

	# select all data related to the matching As
	if qry_set.get(I['all']):
		select_sql, from_sql, where_sql, qry_params = selectify([I['[']], [], meme_table)
		sel_sqls.append(f"SELECT {select_sql} {from_sql} WHERE m0.aid IN (SELECT a0 FROM z{cte_cnt})")

	# get groups
	else:
		for suboperators, suboperands in groups['get'][0]:
			select_sql, from_sql, where_sql, qry_params = selectify(suboperators, suboperands, meme_table)
			sel_sqls.append(f"SELECT {select_sql} {from_sql} WHERE {where_sql} AND a0 IN (SELECT a0 FROM z{cte_cnt})")
			params.extend(qry_params)

	for cte_out in range(cte_beg, cte_cnt):
		sel_sqls.append(f"SELECT acdb FROM z{cte_out+1}" + ('' if cte_out+1 == cte_cnt else f" WHERE a0 IN (SELECT a0 FROM z{cte_cnt})"))

	# FIX LATER
	# Apply logic to As
	#if qry_set.get(I['of']):
	#	sel_sqls.append(f"SELECT m0.val AS v0, m0.vop AS o0, m0.aid AS a0, '{I['of']}' AS c0, z.did AS r0, z.bid AS b0, z.wop AS wo0, z.wal AS w0 FROM {meme_table} m0 JOIN z{cte_cnt} AS z ON m0.aid = z.bid AND m0.cid = z.did WHERE m0.cid={I['is']}")

	return cte_sqls, sel_sqls, params


# Input: operators and operands for one Memelang statement
# Output: SELECT string, FROM string, WHERE string, and depth int
def selectify(operators: list, operands: list, meme_table=None, aidOnly=False):
	if not meme_table: meme_table=DB_TABLE_MEME

	params = []
	wheres = []
	selects = [
		"m0.aid AS a0",
		"m0.val::text || '{' || m0.vop::text || '}' || m0.aid::text || '[' || m0.cid::text"
	]
	joins = [f"FROM {meme_table} m0"]
	m = 0
	wop='='
	prev_right = None

	for i, operator in enumerate(operators):
		operand = operands[i]
		form = OPR[operator]['form']
		dcol = OPR[operator]['dcol']

		if operator in (I['-=='], I['-.']):
			raise Exception(f'Operator {K[operator]} is not supported yet')

		elif dcol=='wop': 
			wop=K[int(operand)]
			continue

		elif operator == I['[']:
			if prev_right: m+=1

			# FIX LATER
			if operand in (I['is'], -I['is']): dcol='cid'

			else:
				if operand is not None and operand<0:
					operand*=-1
					left=f"m{m}.bid"
					did=f"(m{m}.did*-1)"
					right=f"m{m}.aid"
					if m==0:
						selects[0]=selects[0].replace('m0.aid', 'm0.bid')
						selects[1]=selects[1].replace('m0.aid', 'm0.bid')
				else:
					left=f"m{m}.aid"
					did=f"m{m}.did"
					right=f"m{m}.bid"

				if m>0: joins.append(f"JOIN {meme_table} m{m} ON {prev_right}={left}")
				selects[1] += f" || '[' || {did}::text || ']' || {right}::text"
				prev_right = right

		
		if dcol and operand is not None:
			if form in (INT, AID): operand=int(operand)
			elif form == DEC: operand=float(operand)
			else: raise Exception('invalid form')

			eql = wop if dcol=='wal' else '='

			wheres.append(f'm{m}.{dcol}{eql}%s')
			params.append(operand)


	if aidOnly: selects.pop(1)
	else: selects[1] += f" || '{{' || m{m}.wop::text || '}}' || m{m}.wal::text AS acdb"
		
	return [
		', '.join(selects),
		' '.join(joins),
		' AND '.join(wheres),
		params
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

# Input a Memelang query string
# Replace keys with aids
# Execute in DB
# Return results (optionally with "qry.nam:key=1")
def get(mqry: str, meme_table: str = None, name_table: str = None):
	if not meme_table: meme_table=DB_TABLE_MEME
	if not name_table: name_table=DB_TABLE_NAME
	output=[[], []]
	mqry, namekeys = dename(mqry)
	sql, params = querify(mqry, meme_table, name_table)
	memes = select(sql, params)

	mres=''
	for meme in memes: mres+=meme[0]+';'
	output[0], output[1] = parse(mres)

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
	aidcache(operands, name_table)

	# Normalize memes
	resequence(operators, operands, 2)
	resequence(operators, operands, 3)

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
		if end-beg==0: continue
		elif end-beg!=MEMELEN or operators[beg:end-2]!=VOACDB:
			print(end-beg, MEMELEN, operators[beg:end-2], VOACDB)
			print([K[op] for op in operators[beg:end]])
			print([K[op] for op in operands[beg:end]])
			out(operators[beg:end], [K[op] for op in operands[beg:end]])
			raise Exception('Could not write')

		# String name
		if operators[beg+W]==I['"']:
			if operands[beg+B]!=I['key']:
				params[name_table].extend([operands[beg+A], operands[beg+B], operands[beg+W]])
				sqls[name_table].append('(%s,%s,%s)')

		# True/False/Float V=A[C]D]B=W
		else:
			params[meme_table].extend(operands[beg:end])
			sqls[meme_table].append('(%s,%s,%s,%s,%s,%s,%s,%s)')

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

	# Pull out A[C[D]B logic rules
	end=1
	while (end := nxt(operators, operands, (beg := end))):
		beg+=1
		if end-beg==MEMELEN+1 and operators[beg:end-2]==VOACDB and operands[beg+C]!=I['is']:
			if not ACs.get(operands[beg+A]): ACs[operands[beg+A]]={}
			if not ACs[operands[beg+A]].get(operands[beg+C]): ACs[operands[beg+A]][operands[beg+C]]=[]
			ACs[operands[beg+A]][operands[beg+C]].append(beg)

	# Apply A[-C]X[D]B=t rules to X for X[C]A => X[D]B=t
	end=1
	while (end := nxt(operators, operands, (beg := end))):
		beg+=1
		if operators[beg:end-2] == VOACDB and operands[beg+C]==I['is'] and ACs.get(operands[beg+B]) and ACs[operands[beg+B]].get(operands[beg+D]):
			for lobeg in ACs[operands[beg+B]][operands[beg+D]]:
				operators.extend([I[';']] + VOACDB)
				operands.extend([SEMILEN+MEMELEN, I['t'], I['#='], operands[beg+A], I['of'], operands[lobeg+D], operands[lobeg+B], operands[lobeg+WO], operands[lobeg+W]])


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
