import re
import html
import psycopg2
from conf import *

#### SETUP ####
# These are settings for handling Memelang queries. Storing 
# these in variables makes them overly explicit, but reduces
# encoding if/else logic in the later functions.

# Column order
V = 0
A = 1
C = 2
D = 3
B = 4
W = 5
VO = 6
WO = 7

ACDB    = [I['-:'], I['-]'], I[']'], I[':']]
VACDB   = [I['-#']] + ACDB
VACDBS  = VACDB + [I['$']]

NAM    = I['nam']
KEY    = I['key']
FALSE  = 0
TRUE   = 1
GET    = 2
ENDVAL = 0.5

# Forms
NON    = 10		# Value has no form, like END
INT    = 11		# Value is integer, like True, False, Get
DEC    = 12		# Value is decimal number
AID    = 13		# Value is an ID integer
STR    = 14		# Value is a string

# Each operator and its meaning
OPR = {
	I['#']: {
		'form' : INT,
		'dcol' : 'wal',
		'dpth' : 0,
		'dval' : TRUE,
		'$beg' : '=',
		'$end' : '',
	},
	I['$']: {
		'form' : STR,
		'dcol' : 'str',
		'dpth' : 0,
		'dval' : None,
		'$beg' : '="',
		'$end' : '"',
	},
	I['.']: {
		'form' : DEC,
		'dcol' : 'wal',
		'dpth' : 0,
		'dval' : None,
		'$beg' : '=',
		'$end' : '',
	},
	I['>']: {
		'form' : DEC,
		'dcol' : 'wal',
		'dpth' : 0,
		'dval' : None,
		'$beg' : '>',
		'$end' : '',
	},
	I['<']: {
		'form' : DEC,
		'dcol' : 'wal',
		'dpth' : 0,
		'dval' : None,
		'$beg' : '<',
		'$end' : '',
	},
	I['>=']: {
		'form' : DEC,
		'dcol' : 'wal',
		'dpth' : 0,
		'dval' : None,
		'$beg' : '>=',
		'$end' : '',
	},
	I['<=']: {
		'form' : DEC,
		'dcol' : 'wal',
		'dpth' : 0,
		'dval' : None,
		'$beg' : '<=',
		'$end' : '',
	},
	I['!=']: {
		'form' : DEC,
		'dcol' : 'wal',
		'dpth' : 0,
		'dval' : None,
		'$beg' : '!=',
		'$end' : '',
	},
	I[':']: {
		'form' : AID,
		'dcol' : 'bid',
		'dpth' : 0,
		'dval' : None,
		'$beg' : ']',
		'$end' : '',
	},
	I[']']: {
		'form' : AID,
		'dcol' : 'did',
		'dpth' : 1,
		'dval' : I['is'],
		'$beg' : ']',
		'$end' : '',
	},
	I[']]']: {
		'form' : AID,
		'dcol' : 'did',
		'dpth' : 2,
		'dval' : None,
		'$beg' : ']',
		'$end' : '',
	},
	I['&']: {
		'form' : AID,
		'dcol' : 'did',
		'dpth' : 3,
		'dval' : None,
		'$beg' : ' ]',
		'$end' : '',
	},
	I['|']: {
		'form' : INT,
		'dcol' : None,
		'dpth' : 0,
		'dval' : None,
		'$beg' : '',
		'$end' : '',
	},
	I[';']: {
		'form' : NON,
		'dcol' : None,
		'dpth' : 3,
		'dval' : ENDVAL,
		'$beg' : ';',
		'$end' : '',
	},
	I['opr']: { # Actually starts operators, treat as close of non-existant prior statement
		'form' : NON,
		'dcol' : None,
		'dpth' : 3,
		'dval' : I['mix'],
		'$beg' : '',
		'$end' : '',
	},
}

OPRINV={
	']' : '[',
	' ]' : ' [',
	']]' : '[[',
	'wal' : 'val',
	'did' : 'cid',
	'wop' : 'vop',
	'bid' : 'aid',
}

CHRTOK = {
	"[": 1,
	"]": 1,
	";": 1,
	' ': 1,
	"=": 1,
	"!": 1,
	">": 1,
	"<": 1,
}

REMOVE_OPERATOR=-3
REMOVE_IF_EMPTY=-2
LEFTSHIFT_OPERAND=-1
KEEP_OPERATOR=1
SERIAL = {
	0 : { # Merge > and =
		('>', '=') : ('>=', REMOVE_OPERATOR),
		('<', '=') : ('<=', REMOVE_OPERATOR),
		('!', '=') : ('!=', REMOVE_OPERATOR),
	},
	1 : { # Merge <>= and 123.456
		(';', '$') : (KEEP_OPERATOR, ']'), # Not sure about this
		(';', '#') : (KEEP_OPERATOR, ']'),  # Not sure about this
		('>', '#') : (KEEP_OPERATOR, LEFTSHIFT_OPERAND),
		('<', '#') : (KEEP_OPERATOR, LEFTSHIFT_OPERAND),
		('>=', '#') : (KEEP_OPERATOR, LEFTSHIFT_OPERAND),
		('<=', '#') : (KEEP_OPERATOR, LEFTSHIFT_OPERAND),
		('!=', '#') : (KEEP_OPERATOR, LEFTSHIFT_OPERAND),
		('>', '.') : (KEEP_OPERATOR, LEFTSHIFT_OPERAND),
		('<', '.') : (KEEP_OPERATOR, LEFTSHIFT_OPERAND),
		('>=', '.') : (KEEP_OPERATOR, LEFTSHIFT_OPERAND),
		('<=', '.') : (KEEP_OPERATOR, LEFTSHIFT_OPERAND),
		('!=', '.') : (KEEP_OPERATOR, LEFTSHIFT_OPERAND),
		('=', '@') : ('#', LEFTSHIFT_OPERAND),
		('=', '#') : ('.', LEFTSHIFT_OPERAND),
		('=', '.') : ('.', LEFTSHIFT_OPERAND),
		('=', '"') : ('"', LEFTSHIFT_OPERAND),
	},
	2 : { # Merge ] with D
		(']', '#') : (KEEP_OPERATOR, LEFTSHIFT_OPERAND),
		(']', '$') : (KEEP_OPERATOR, LEFTSHIFT_OPERAND),
	},
	3 : { # Turn last ]D into ]B
		(']', ';') : (':', KEEP_OPERATOR),
		(']', ' ') : (':', KEEP_OPERATOR),
		(']', '.') : (':', KEEP_OPERATOR),
		(']', '#') : (':', KEEP_OPERATOR),
		(']', '"') : (':', KEEP_OPERATOR),
		(']', '>') : (':', KEEP_OPERATOR),
		(']', '<') : (':', KEEP_OPERATOR),
		(']', '>=') : (':', KEEP_OPERATOR),
		(']', '<=') : (':', KEEP_OPERATOR),
		(']', '!=') : (':', KEEP_OPERATOR),
	},
	4 : { # Turn ] into ]] or &]
		(']', ']') : (KEEP_OPERATOR, ']]'),
		(']]', ']') : (KEEP_OPERATOR, ']]'),
		(' ', ']') : ('&', LEFTSHIFT_OPERAND),
		('"', ';') : ('$', KEEP_OPERATOR),
	},
	5 : {
		('&', ']') : (KEEP_OPERATOR, ']]'),
	},
	6 : {
		('[', ']') : (REMOVE_IF_EMPTY, KEEP_OPERATOR),
		(';', ';') : (KEEP_OPERATOR, LEFTSHIFT_OPERAND),
	}
}


SEQ = {
	'expand': {
		(I[';'], I['-:'])          : (I[';'], I['-#'], I['-:']),
		(I['-:'], I[']'])          : (I['-:'], I['-]'], I[']']),
		(I[':'], I[';'])           : (I[':'], I['#'], I[';']),
		(I[':'], I['&'])           : (I[':'], I['#'], I['&']),
	}
}


# Conbine SQL and parameters into a string
def morfigy(sql: str, params: list) -> str:
	new_query = sql
	for param in params:

		if isinstance(param, str): param = "'"+str(param).replace("'", "''")+"'"
		else: param = str(param)

		new_query = new_query.replace("%s", param, 1)
	return new_query


# Input: string "John Adams"
# Output: lowercase underscored string "john_adams"
def slugify(string: str) -> str:
	return re.sub(r'__+', '_', re.sub(r'[^a-z0-9]', '_', string.lower())).strip('_')


#### MEMELANG QUERY PARSING ####

# Input: Memelang string operator1operand1operator2operand2
# Output: [operator1, operator2, ...], [operand1, operand2, ...]
def parse(mqry: str):

	# Replace multiple spaces with a single space
	mqry = ' '.join(str(mqry).strip().split())

	# Remove comments
	mqry = re.sub(r'\s*//.*$', '', mqry, flags=re.MULTILINE)

	# Remove spaces around operators
	mqry = re.sub(r'\s*([;!<>=]+)\s*', r'\1', mqry)

	# Prepend zero before decimals, such as =.5 to =0.5
	mqry = re.sub(r'([<>=])(\-?)\.([0-9])', lambda m: f"{m.group(1)}{m.group(2)}0.{m.group(3)}", mqry)

	if len(mqry) == 0: raise Exception("Error: Empty query provided.")

	mqry_chars = list(mqry)
	mqry_len = len(mqry_chars)

	preoperators = ['opr', ';']
	preoperands = [I['mix'], ENDVAL]
	beg = 1

	i = 0
	while i < mqry_len:
		c = mqry_chars[i]
		operand = ''

		# Comment: skip until newline
		if c == '/' and i+1 < mqry_len and mqry_chars[i+1] == '/':
			while i < mqry_len and mqry_chars[i] != '\n': i += 1
			i += 1

		# Operators
		elif c in CHRTOK:
			preoperators.append(c)
			preoperands.append(None)

			if c==';':
				beg=len(preoperators)-1
				preoperands[-1]=ENDVAL
			else:
				preoperands[beg]+=1

			i += 1

		# Double-quote string ="George Washtingon's Horse \"Blueskin\""
		elif c == '"':
			while i < mqry_len-1:
				i += 1
				ch = mqry_chars[i]
				if ch=='\\': pass
				elif ch=='"':
					i+=1
					break
				else: operand += ch

			preoperators.append('"')
			preoperands.append(operand)
			preoperands[beg]+=1

		# key/int/float
		else:
			while i < mqry_len and re.match(r'[a-z0-9_\.\-]', mqry_chars[i]):
				operand += mqry_chars[i]
				i += 1

			if not len(operand): raise Exception(f"Memelang parse error: Unexpected '{c}' at char {i} in {mqry}")

			if '.' in operand: preoperators.append('.')
			elif operand in ('0','1','2','t','f','g'):
				preoperators.append('@')
				operand=I[operand]
			elif re.match(r'^-?[0-9]+$', operand): preoperators.append('#')
			else: preoperators.append('$')
			
			preoperands.append(operand)
			preoperands[beg]+=1

	operators=['opr']
	operands=[I['mix']]

	# Merge > and =
	preoperators, preoperands = serialize(preoperators, preoperands, False, [0])

	o=1
	olen=len(preoperators)
	while o<olen:
		if preoperators[o]!=';': raise Exception(f'Operator counting error at {o} for {preoperators[o]}')
		slen=int(preoperands[o])
		if not slen: o+=1
		else:
			o+=1
			left=0
			beg=len(operators)
			operators.append(';')
			operands.append(ENDVAL)

			# Divide statement into left/right sides
			while left<slen:
				if preoperators[o+left]==']': break
				left+=1

			#print(preoperators[o:o+slen], left, slen)

			# Process left side
			if left>0:
				leftoperators, leftoperands = serialize(preoperators[o:o+left][::-1], preoperands[o:o+left][::-1], True, [1,2,3,4,5])
				operators.extend([f'-{op}' for op in leftoperators[::-1]])
				operands.extend(leftoperands[::-1])
				operands[beg]+=len(leftoperators)

			# Process right side
			if left<slen:
				rightoperators, rightoperands = serialize(preoperators[o+left:o+slen], preoperands[o+left:o+slen], True, [1,2,3,4,5])
				operators.extend(rightoperators)
				operands.extend(rightoperands)
				operands[beg]+=len(rightoperators)
			else:
				operators.append(']')
				operands.append(None)
				operands[beg]+=1

			o+=slen

	# Merge ;;
	operators, operands = serialize(operators, operands, False, [6])

	o=0
	olen=len(operators)
	while o<olen:
		if I.get(operators[o]): 
			operators[o]=I[operators[o]]
			form = OPR[abs(operators[o])]['form']
			if form == INT: operands[o]=int(operands[o])
			elif form == DEC: operands[o]=float(operands[o])

		else: 
			print(operators)
			raise Exception(f'Invalid "{operators[o]}" at {o}')
		o+=1

	return operators, operands


def serialize (operators: list, operands: list, allRight: bool = False, phases: list = [0, 1, 2, 3, 4, 5, 6]):

	#print(operators)
	#print(operands)

	# FIX LATER
	if allRight: operators = [']' if x == '[' else x for x in operators]

	pop0=False
	pop1=False
	if operators[0]!=';':
		pop0=True
		operators.insert(0, ';')
		operands.insert(0, ENDVAL)
	if operators[-1]!=';':
		pop1=True
		operators.append(';')
		operands.append(ENDVAL)

	olen=len(operators)
	for phase in phases:
		o=0
		while o<olen:
			if SERIAL[phase].get(tuple(operators[o:o+2])):
				offset=0
				instructions=SERIAL[phase].get(tuple(operators[o:o+2]))
				for i, instr in enumerate(instructions):
					if isinstance(instr, str): operators[o+i+offset]=instr
					elif instr == KEEP_OPERATOR: continue
					elif instr == REMOVE_OPERATOR:
						operators.pop(o+i+offset)
						operands.pop(o+i+offset)
						offset-=1
					elif instr == REMOVE_IF_EMPTY:
						if operands[o+i+offset] is None:
							operators.pop(o+i+offset)
							operands.pop(o+i+offset)							
					elif instr == LEFTSHIFT_OPERAND:
						operators.pop(o+i+offset)
						operands[o+i+offset-1]=operands.pop(o+i+offset)
						offset-=1
				olen+=offset
			o+=1

	if pop0:
		operators.pop(0)
		operands.pop(0)
	if pop1:
		operators.pop()
		operands.pop()
	olen-=2

	#print(operators)
	#print(operands)
	#print()

	return operators, operands


# Input operators, operands
# Modifies the sequence according to rules in SEQ
def sequence (operators: list, operands: list, mode: str = 'expand'):
	if not operators: return

	operators.insert(0, I[';'])
	operands.insert(0, ENDVAL)
	operators.append(I[';'])
	operands.append(ENDVAL)

	olen=len(operators)
	o=0
	slen=2
	while o<olen:
		if operators[o]==I[';']: beg=o
		if SEQ[mode].get(tuple(operators[o:o+slen])):
			suboperators=SEQ[mode][tuple(operators[o:o+slen])]

			# Insert operator at o+1, insert operator's dval value as operand
			if len(suboperators)>slen:
				operators.insert(o+1, suboperators[1])
				operands.insert(o+1, OPR[abs(suboperators[1])]['dval'])
				olen += 1
				operands[beg] += 1

			for so, suboperator in enumerate(suboperators):
				# Change operator
				if suboperator: operators[o+so]=suboperator
		o+=1
	operators.pop(0)
	operands.pop(0)
	operators.pop()
	operands.pop()


# Input: operators, operands
# Output: Memelang string operator1operand1operator2operand2
def deparse(operators: list, operands: list, deparse_set=None) -> str:

	if not deparse_set: deparse_set={}
	mqry = ''

	for o,operator in enumerate(operators):
		aperator=abs(operator)
		if o<2 and OPR[aperator]['form'] == NON: continue
		
		elif operands[o] is None or OPR[aperator]['form'] == NON: operand = ''

		# Decimal number must have a decimal
		elif OPR[aperator]['form'] == DEC:
			operand = str(operands[o])
			if '.' not in operand:
				if float(operand)>0:
					if float(operand)>1: operand = operand + '.0'
					else: operand = '0.' + operand
				else:
					if float(operand)<-1: operand = operand + '.0'
					else: operand = '-0.' + operand[1:]

		else: operand = str(operands[o])

		beg = OPR[aperator]['$beg']
		end = OPR[aperator]['$end']
		if operator < 0:
			if OPRINV.get(beg): beg=OPRINV[beg]
			if OPRINV.get(end): end=OPRINV[end]
			[beg, end] = [end, beg]

		if operator == I[';'] and deparse_set.get('newline'): end="\n"
		
		# Append the deparsed expression
		if deparse_set.get('html'):
			mqry += '<var class="v' + str(operator) + '">' + html.escape(beg + operand + end) + '</var>'
		else:
			mqry += beg + operand + end

	if deparse_set.get('html'):
		mqry = '<code class="meme">' + mqry + '</code>'

	return mqry.replace('[]', ']')


#### MEMELANG-SQL CONVERSION ####

# Input: Memelang query string
# Output: SQL query string
def querify(mqry: str, meme_table=None, name_table=None):
	if not meme_table: meme_table=DB_TABLE_MEME
	if not name_table: name_table=DB_TABLE_NAME

	operators, operands = parse(mqry)

	if name_table: 
		operands = identify(operands, name_table)
		missings = [x for x in operands if isinstance(x, str)]
		if missings: raise Exception("Unknown keys: " + ", ".join(missings))

	ctes = []
	selects = []
	params = []

	o=1
	olen=len(operators)
	while o<olen:
		if operators[o]!=I[';']: raise Exception(f'Operator counting error at {o} for {operators[o]}')
		slen=int(operands[o])
		o+=1
		if slen:
			cte, select, param = subquerify(operators[o:o+slen], operands[o:o+slen], meme_table, o*100)
			ctes.extend(cte)
			selects.extend(select)
			params.extend(param)
		o+=slen

	#print('WITH ' + ', '.join(ctes) + ' ' + ' UNION '.join(selects))
	return ['WITH ' + ', '.join(ctes) + ' ' + ' UNION '.join(selects), params]

# Input: operators and operands for one Memelang command
# Output: One SQL query string
def subquerify(operators: list, operands: list, meme_table=None, cte_beg:int=-1):
	if not meme_table: meme_table=DB_TABLE_MEME
	qry_set = {'all': False, 'of': False}
	true_group = []
	or_groups = {}
	false_group = []
	get_group = []
	true_cnt = 0
	or_cnt = 0
	false_cnt = 0

	skip = False
	suboperators = []
	suboperands = []

	olen=len(operators)
	o=0
	beg=0
	slen=0
	markers=[]
	while o<olen:
		aperator=abs(operators[o])
		if operators[o]==-I[':'] and operands[o]==I['qry']:
			qry_set[operands[o+1]]=True
			skip=True
		elif OPR[aperator]['dpth']==3:
			if not skip: markers.append([beg, o])
			skip=False
			beg=o
		elif o==olen-1 and not skip: markers.append([beg, o+1])
		o+=1

	for beg, end in markers:
		last_operator = operators[end-1]
		last_operand = operands[end-1]

		# Handle =f (false)
		if last_operator == I['#'] and last_operand == I['f']:
			false_cnt += 1
			false_group.append([operators[beg:end], operands[beg:end]])
		
		# Handle =g (get)
		elif last_operator == I['#'] and last_operand == I['g']:
			get_group.append([operators[beg:end], operands[beg:end]])
			continue

		# Handle =tn (OR groups)
		elif last_operator == I['|']:
			or_cnt += 1
			if not or_groups.get(last_operand): or_groups[last_operand]=[]
			or_groups[last_operand].append([operators[beg:end], operands[beg:end]])
		
		# Default: Add to true conditions
		else:
			true_group.append([operators[beg:end], operands[beg:end]])
			true_cnt += 1

	# If qry_set['all'] and no true/false/or conditions
	if qry_set.get(I['all']) and true_cnt == 0 and false_cnt == 0 and or_cnt == 0:
		return [f"SELECT * FROM {meme_table}", []]

	cte_cnt  = cte_beg
	params   = []
	cte_sqls = []
	cte_outs = []
	sql_outs = []

	# Process AND conditions
	for suboperators, suboperands in true_group:
		select_sql, from_sql, where_sql, qry_params, qry_depth = selectify(suboperators, suboperands, meme_table)
		wheres = [where_sql]
		params.extend(qry_params)
		if cte_cnt > cte_beg: wheres.append(f"{select_sql[14:21]} IN (SELECT a0 FROM z{cte_cnt})")
		cte_cnt += 1
		cte_sqls.append(f"z{cte_cnt} AS (SELECT {select_sql} {from_sql} WHERE {' AND '.join(wheres)})")
		cte_outs.append((cte_cnt, qry_depth))

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
		if true_cnt < 1:
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
		sql_outs.append(f"SELECT val as v0, aid as a0, cid as c0, did as r0, bid as b0, wal as w0, vop as vo0, wop as wo0 FROM {meme_table} m0 WHERE m0.aid IN (SELECT a0 FROM z{cte_cnt})")

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
			sql_outs.append(f"SELECT DISTINCT v{m}, a{m}, c{m}, r{m}, b{m}, w{m}, vo{m}, wo{m} FROM z{zNum}{cWhere}")
			m+=1

	# Apply logic to As
	if qry_set.get(I['of']):
		sql_outs.append(f"SELECT m0.val AS v0, m0.aid AS a0, '{I['of']}' AS c0, z.did AS r0, z.bid AS b0, z.wal AS w0, m0.vop AS o0, z.wop AS wo0 FROM {meme_table} m0 JOIN z{cte_cnt} AS z ON m0.aid = z.bid AND m0.cid = z.did WHERE m0.cid={I['is']}")

	#return ['WITH ' + ', '.join(cte_sqls) + ' ' + ' UNION '.join(sql_outs), params]
	return cte_sqls, sql_outs, params


# Input: operators and operands for one Memelang statement
# Output: SELECT string, FROM string, WHERE string, and depth int
def selectify(operators: list, operands: list, meme_table=None, aidOnly=False):
	if not meme_table: meme_table=DB_TABLE_MEME

	params = []
	wheres = []
	joins = [f"FROM {meme_table} m0"]
	selects = ['m0.val AS v0','m0.aid AS a0','m0.cid AS c0','m0.did AS r0','m0.bid AS b0','m0.wal AS w0','m0.vop AS vo0','m0.wop AS wo0']
	m = 0
	opr=None
	val=None
	last_rel_end=None
	waldone=False

	for i, operator in enumerate(operators):
		operand = operands[i]
		aperator = abs(operator)
		form = OPR[aperator]['form']
		dcol = OPR[aperator]['dcol']

		# REL
		# TO DO: Work on switching V-O and E-Q
		if OPR[aperator]['dpth']>0:
			if OPR[aperator]['dpth'] != 2:
				if operator>0 and operand is not None and operand<0:
					selects = ['m0.val AS v0','m0.bid AS a0','m0.cid AS c0','m0.did*-1 AS r0','m0.aid AS b0','m0.wal AS w0','m0.vop AS vo0','m0.wop AS wo0']
			
			elif operator<0: raise Exception('What does it mean to look up a C chain?')

			else:
				m += 1
				wheres.extend([f"m{m-1}.wal!=%s", f'm{m}.cid=%s'])
				params.extend([FALSE, I['is']])

				if operand is not None and operand<0:
					joins.append(f"JOIN {meme_table} m{m} ON m{m-1}.{last_rel_end}=m{m}.bid")
					selects.append(f"m{m}.val AS v{m}")
					selects.append(f"m{m}.bid AS a{m}")
					selects.append(f"m{m}.cid AS c{m}")
					selects.append(f"m{m}.did*-1 AS r{m}")
					selects.append(f"m{m}.aid AS b{m}")
					selects.append(f"m{m}.wal AS w{m}")
					selects.append(f"m{m}.vop AS vo{m}")
					selects.append(f"m{m}.wop AS wo{m}")
				else:
					joins.append(f"JOIN {meme_table} m{m} ON m{m-1}.{last_rel_end}=m{m}.aid")
					selects.append(f"m{m}.val AS v{m}")
					selects.append(f"m{m}.aid AS a{m}")
					selects.append(f"m{m}.cid AS c{m}")
					selects.append(f"m{m}.did AS r{m}")
					selects.append(f"m{m}.bid AS b{m}")
					selects.append(f"m{m}.wal AS w{m}")
					selects.append(f"m{m}.vop AS vo{m}")
					selects.append(f"m{m}.wop AS wo{m}")

			last_rel_end = 'aid' if operand is not None and operand<0 else 'bid'


		if dcol and operand is not None:

			if operator<0: dcol=OPRINV[dcol]
			elif dcol=='wal': waldone=True

			if form in (INT, AID):
				operand=int(operand)
				eql = '='
				# Special case =t to !=f
				if operand in (TRUE, GET):
					eql='!='
					operand=FALSE

			elif form == DEC:
				operand=float(operand)
				eql = OPR[aperator]['$beg']

			else:
				raise Exception('invalid form')

			wheres.append(f'm{m}.{dcol}{eql}%s')
			params.append(operand)

	if not waldone:
		wheres.append(f'm{m}.wal!=%s')
		params.append(0)

	if aidOnly: selects = ['m0.aid AS a0']

	return [
		', '.join(selects),
		' '.join(joins),
		' AND '.join(wheres),
		params,
		m
	]


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


def selnum(query: str):
	result = select(query)
	return int(0 if not result or not result[0] or not result[0][0] else result[0][0])


def maxnum(col: str = 'aid', table: str = None):
	if not table: table=DB_TABLE_MEME
	result = select(f"SELECT MAX({col}) FROM {table}")
	return int(0 if not result or not result[0] or not result[0][0] else result[0][0])


# Input list of aids and list of bids
# Output names from DB
def selectnames(aids: list = [], bids: list = [], strings: list = [], table: str = None):
	if not table: table=DB_TABLE_NAME

	conds = []
	params = []
	if bids: 
		conds.append(f"bid IN ("+ ','.join(['%s'] * len(bids)) +")")
		params.extend(map(int, bids))
	if aids: 
		conds.append(f"aid IN ("+ ','.join(['%s'] * len(aids)) +")")
		params.extend(map(int, aids))
	if strings: 
		conds.append(f"str IN ("+ ','.join(['%s'] * len(strings)) +")")
		params.extend(map(str, strings))

	if not conds: raise Exception('No conds')

	return select(f"SELECT DISTINCT aid, bid, str FROM {table} WHERE " + ' AND '.join(conds), params)


#### KEY-ID CONVERSION ####

# Input list of key strings ['george_washington', 'john_adams']
# Load key->aids in I and K caches
# I['john_adams']=123
# K[123]='john_adams'
def aidcache(keys, name_table=None):
	if not name_table: name_table=DB_TABLE_NAME
	if not keys: return

	uncached_keys = [key for key in keys if key not in I]

	if not uncached_keys: return

	rows=selectnames([], [KEY], uncached_keys, name_table)

	for row in rows:
		I[row[2]] = int(row[0])
		K[int(row[0])] = row[2]


# Input value is a list of strings ['a', 'b', 'c', 'd']
# Load key->aid
# Return the data with any keys with ids
def identify(keys: list, name_table=None):
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


def identify1(val, name_table=None):
	if not name_table: name_table=DB_TABLE_NAME
	ids = identify([val], name_table)
	return ids[0] if isinstance(ids[0], int) else False


# Input value is a list of ints [123,456,789]
# Load aid->key
# Return the data with any aids replaced with keys
def namify(operands: list, bids: list, name_table=None):
	if not name_table: name_table=DB_TABLE_NAME
	missings=[]

	output = {}
	for bid in bids:
		output[bid]=[bid]

	matches = []
	for i,operand in enumerate(operands):
		if isinstance(operand, int): matches.append(abs(operands[i]))

	names = selectnames(matches, bids, [], name_table)

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
			else:
				output[bid].append(operand)

	return list(output.values())


#### PROCESS MEMELANG QUERY FOR SQL QUERY ####

# Input a Memelang query string
# Replace keys with aids
# Execute in DB
# Return results (optionally with "qry.nam:key=1")
def get(mqry, meme_table=None, name_table=None):
	if not meme_table: meme_table=DB_TABLE_MEME
	if not name_table: name_table=DB_TABLE_NAME
	output=[[I['opr']], [I['id']]]
	mqry, namekeys = dename(mqry)
	sql, params = querify(mqry, meme_table)
	memes = select(sql, params)

	for meme in memes:
		output[0].extend([I[';'], int(meme[VO])] + ACDB + [int(meme[WO])])
		output[1].extend([ENDVAL+6, float(meme[V]), int(meme[A]), int(meme[C]), int(meme[D]), int(meme[B]), float(meme[W])])

	if namekeys: output.extend(namify(output[1], namekeys, name_table))

	return output


# Return meme count of above results
def count(mqry, meme_table=DB_TABLE_MEME, name_table=DB_TABLE_NAME):
	sql, params = querify(mqry, meme_table)
	return len(select(sql, params))


def put (operators: list, operands: list, meme_table=None, name_table=None):
	if not operators: return operators, operands
	if not meme_table: meme_table=DB_TABLE_MEME
	if not name_table: name_table=DB_TABLE_NAME

	# Load IDs
	aidcache(operands)

	# Normalize memes
	sequence(operators, operands, 'expand')

	missings = {}
	name_sqls = []
	name_params = []
	sqls = {meme_table:[], name_table:[]}
	params = {meme_table:[], name_table:[]}

	# Swap in ID or mark missing
	o=2
	olen=len(operators)
	while o<olen:
		if OPR[abs(operators[o])]['form']==AID:
			if isinstance(operands[o], int): pass
			elif operands[o].isdigit(): operands[o]=int(operands[o])
			elif I.get(operands[o]): operands[o]=I[operands[o]]
			else: missings[operands[o]]=1
		o+=1

	# Pull out keys
	o=1
	while o<olen:
		if operators[o]!=I[';']: raise Exception(f'Operator counting error at {o} for {operators[o]}')
		slen=int(operands[o])
		o+=1
		if slen and operators[o:o+slen]==VACDBS and operands[o+D]==NAM and operands[o+B]==KEY:
			key = operands[o+W]
			aid = operands[o+A]
			missings.pop(key, None)
			sqls[name_table].append("(%s,%s,%s)")
			params[name_table].extend([aid, KEY, key])
			I[key]=aid
			K[aid]=key
		o+=slen

	# Missing keys with no associated ID
	if missings:
		aid = maxnum('aid', name_table) or I['cor']
		for key, val in missings.items():
			aid += 1
			sqls[name_table].append("(%s,%s,%s)")
			params[name_table].extend([aid, KEY, key])
			I[key]=aid
			K[aid]=key

	# Swap in new IDs
	o=2
	while o<olen:
		if OPR[abs(operators[o])]['form']==AID and isinstance(operands[o], str): operands[o]=I[operands[o]]
		o+=1
		
	# Pull out names and trues
	o=1
	while o<olen:
		if operators[o]!=I[';']: raise Exception(f'Operator counting error at {o} for {operators[o]}')
		slen=int(operands[o])
		o+=1

		if slen and operators[o:o+slen-1]==VACDB:

			# String name
			if operators[o+W]==I['$']:
				if operands[o+B]!=KEY:
					params[name_table].extend([operands[o+A], operands[o+B], operands[o+W]])
					sqls[name_table].append('(%s,%s,%s)')

			# True/False/Float V=A[C]D]B=W
			else:
				params[meme_table].extend(operands[o:o+slen] + [operators[o+V], operators[o+W]])
				sqls[meme_table].append('(%s,%s,%s,%s,%s,%s,%s,%s)')

		o+=slen

	for tbl in params:
		if params[tbl]:
			insert(f"INSERT INTO {tbl} VALUES " + ','.join(sqls[tbl]) + " ON CONFLICT DO NOTHING", params[tbl])

	return operators, operands


# Remove name statement from query
def dename(mqry: str):
	terms = re.split(r'\s+', mqry)
	remaining_terms = []

	pattern = re.compile(r'^([a-z0-9_]+)?\.(nam)(?:\:([a-z0-9_]+))?(?:=([0-9]+))?$')
	extracted_terms = []
	for term in terms:
		m = pattern.match(term)
		if m: extracted_terms.append(m.groups()[2])
		else: remaining_terms.append(term)

	# Reconstruct the remaining string
	return ' '.join(remaining_terms), identify(list(set(extracted_terms)))


# Apply logic
def logify (operators: list, operands: list):
	ACs = {}

	# Pull out A[C]D]B logic rules
	o=1
	olen=len(operators)
	while o<olen:
		if operators[o]!=I[';']: raise Exception(f'Operator counting error at {o} for {operators[o]}')
		slen=int(operands[o])
		o+=1
		if slen==6 and operators[o:o+slen-1]==VACDB and operands[o+C]!=I['is']:
			if not ACs.get(operands[o+A]): ACs[operands[o+A]]={}
			if not ACs[operands[o+A]].get(operands[o+C]): ACs[operands[o+A]][operands[o+C]]=[]
			ACs[operands[o+A]][operands[o+C]].append(o)
		o+=slen

	# Apply A[C]D]B=t rules to C for X]C]A => X]D]B=t
	o=1
	while o<olen:
		if operators[o]!=I[';']: raise Exception(f'Operator counting error at {o} for {operators[o]}')
		slen=int(operands[o])
		o+=1
		if slen and operators[o:o+slen-1] == VACDB and operands[o+C]==I['is'] and ACs.get(operands[o+B]) and ACs[operands[o+B]].get(operands[o+D]):
			for lobeg in ACs[operands[o+B]][operands[o+D]]:
				operators.extend([I[';']] + VACDB + [operators[lobeg+W]])
				operands.extend([ENDVAL+6, TRUE, operands[o+A], I['of'], operands[lobeg+D], operands[lobeg+B], operands[lobeg+W]])
				olen+=7
		o+=slen


#### MEME FILE ####

def read (file_path):
	output = [[I['opr']],[I['mix']]]
	with open(file_path, 'r', encoding='utf-8') as f:
		for ln, line in enumerate(f, start=1):
			if line.strip() == '' or line.strip().startswith('//'): continue
			operators, operands = parse(line)
			if len(operators)>2:
				output[0].extend(operators[1:])
				output[1].extend(operands[1:])

	return output[0], output[1]


def write (file_path, operators: list, operands: list):
	with open(file_path, 'w', encoding='utf-8') as file:
		file.write(deparse(operators, operands, {'newline':True}))
