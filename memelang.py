import re
import html
import db
from conf import *

ALRB   = [I['A'], I['L'], I['R'], I['B']]
ALRBES = ALRB + [I['R='], I['R"']]

NAM    = I['nam']
KEY    = I['key']

LEFT   = 0
RIGHT  = 1
CLOSE  = 2

REL    = 0
AB     = 1
EQL    = 2
VAL    = 3
OR     = 4
AND    = 5
END    = 6

NON    = 0
INT    = 1
DEC    = 2
AID    = 3
STR    = 4

OPR = {
	I['L1']: {
		'side' : LEFT,
		'func' : VAL,
		'form' : INT,
		'dpth' : 0,
		'$beg' : '',
		'$mid' : '',
		'$end' : '',
	},
	I['L"']: {
		'side' : LEFT,
		'func' : VAL,
		'form' : STR,
		'dpth' : 0,
		'$beg' : '"',
		'$mid' : '',
		'$end' : '"',
	},
	I['L.']: {
		'side' : LEFT,
		'func' : VAL,
		'form' : DEC,
		'dpth' : 0,
		'$beg' : '',
		'$mid' : '',
		'$end' : '',
	},
	I['R1']: {
		'side' : RIGHT,
		'func' : VAL,
		'form' : INT,
		'dpth' : 0,
		'$beg' : '',
		'$mid' : '',
		'$end' : '',
	},
	I['R"']: {
		'side' : RIGHT,
		'func' : VAL,
		'form' : STR,
		'dpth' : 0,
		'$beg' : '"',
		'$mid' : '',
		'$end' : '"',
	},
	I['R.']: {
		'side' : RIGHT,
		'func' : VAL,
		'form' : DEC,
		'dpth' : 0,
		'$beg' : '',
		'$mid' : '',
		'$end' : '',
	},

	I['L=']: {
		'side' : LEFT,
		'func' : EQL,
		'form' : NON,
		'dpth' : 0,
		'$beg' : '=',
		'$end' : '',
	},
	I['L>']: {
		'side' : LEFT,
		'func' : EQL,
		'form' : NON,
		'dpth' : 0,
		'$beg' : '',
		'$mid' : '>',
		'$end' : '',
	},
	I['L<']: {
		'side' : LEFT,
		'func' : EQL,
		'form' : NON,
		'dpth' : 0,
		'$beg' : '',
		'$mid' : '<',
		'$end' : '',
	},
	I['L>=']: {
		'side' : LEFT,
		'func' : EQL,
		'form' : NON,
		'dpth' : 0,
		'$beg' : '',
		'$mid' : '>=',
		'$end' : '',
	},
	I['L<=']: {
		'side' : LEFT,
		'func' : EQL,
		'form' : NON,
		'dpth' : 0,
		'$beg' : '',
		'$mid' : '<=',
		'$end' : '',
	},
	I['L!=']: {
		'side' : LEFT,
		'func' : EQL,
		'form' : NON,
		'dpth' : 0,
		'$beg' : '',
		'$mid' : '!=',
		'$end' : '',
	},
	I['R=']: {
		'side' : RIGHT,
		'func' : EQL,
		'form' : NON,
		'dpth' : 0,
		'$beg' : '=',
		'$end' : '',
	},
	I['R>']: {
		'side' : RIGHT,
		'func' : EQL,
		'form' : NON,
		'dpth' : 0,
		'$beg' : '',
		'$mid' : '>',
		'$end' : '',
	},
	I['R<']: {
		'side' : RIGHT,
		'func' : EQL,
		'form' : NON,
		'dpth' : 0,
		'$beg' : '',
		'$mid' : '<',
		'$end' : '',
	},
	I['R>=']: {
		'side' : RIGHT,
		'func' : EQL,
		'form' : NON,
		'dpth' : 0,
		'$beg' : '',
		'$mid' : '>=',
		'$end' : '',
	},
	I['R<=']: {
		'side' : RIGHT,
		'func' : EQL,
		'form' : NON,
		'dpth' : 0,
		'$beg' : '',
		'$mid' : '<=',
		'$end' : '',
	},
	I['R!=']: {
		'side' : RIGHT,
		'func' : EQL,
		'form' : NON,
		'dpth' : 0,
		'$beg' : '',
		'$mid' : '!=',
		'$end' : '',
	},

	I['A']: {
		'side' : LEFT,
		'func' : AB,
		'form' : AID,
		'dpth' : 0,
		'$beg' : '[',
		'$mid' : '',
		'$end' : '',
	},
	I['LL']: {
		'side' : LEFT,
		'func' : REL,
		'form' : AID,
		'dpth' : 2,
		'$beg' : '[',
		'$mid' : '',
		'$end' : '',
	},
	I['L']: {
		'side' : LEFT,
		'func' : REL,
		'form' : AID,
		'dpth' : 1,
		'$beg' : '[',
		'$mid' : '',
		'$end' : '',
	},
	I['B']: {
		'side' : RIGHT,
		'func' : AB,
		'form' : AID,
		'dpth' : 0,
		'$beg' : ']',
		'$mid' : '',
		'$end' : '',
	},
	I['RR']: {
		'side' : RIGHT,
		'func' : REL,
		'form' : AID,
		'dpth' : 2,
		'$beg' : ']',
		'$mid' : '',
		'$end' : '',
	},
	I['R']: {
		'side' : RIGHT,
		'func' : REL,
		'form' : AID,
		'dpth' : 1,
		'$beg' : ']',
		'$mid' : '',
		'$end' : '',
	},

	I['Or']: {
		'side' : CLOSE,
		'func' : OR,
		'form' : INT,
		'dpth' : 0,
		'$beg' : '',
		'$mid' : '',
		'$end' : '',
	},
	I['And']: {
		'side' : CLOSE,
		'func' : AND,
		'form' : NON,
		'dpth' : 0,
		'$beg' : '',
		'$mid' : ' ',
		'$end' : '',
	},
	I['End']: {
		'side' : CLOSE,
		'func' : END,
		'form' : NON,
		'dpth' : 0,
		'$beg' : '',
		'$mid' : ';',
		'$end' : '',
	},
	# Actually starts operators, treat as close of non-existant prior statement
	I['opr']: {
		'side' : CLOSE,
		'func' : END,
		'form' : NON,
		'dpth' : 0,
		'$beg' : '',
		'$mid' : '',
		'$end' : '',
	},
}

OPR_CHR = {
	"[": 1,
	"]": 1,
	' ': 1,
	";": 1,
	"=": 1,
	"!": 2,
	">": 2,
	"<": 2,
}

OPSIDE = {
	LEFT: {
		'a' : I['A'],
		'.' : I['L.'],
		'1' : I['L1'],
		'"' : I['L"'],
		'=' : I['L='],
		'>' : I['L>'],
		'<' : I['L<'],
		'>=' : I['L>='],
		'<=' : I['L<='],
		'!=' : I['L!='],
		'[' : I['L'],
		'|' : I['R'],
		']' : I['R'],
		' ' : I['And'],
		';' : I['End'],
	},
	RIGHT: {
		'.' : I['R.'],
		'1' : I['R1'],
		'"' : I['R"'],
		'=' : I['R='],
		'>' : I['R>'],
		'<' : I['R<'],
		'>=' : I['R>='],
		'<=' : I['R<='],
		'!=' : I['R!='],
		']' : I['R'],
		' ' : I['And'],
		';' : I['End'],
	}
}

# When delacing, replace [O1, O2] with [O3, O4]
OPRSEQ = {
	# We assumed the first item wan an A, but its actually a Decimal
	(I['A'], I['L=']): (I['L.'], I['L=']),
	(I['A'], I['L>']): (I['L.'], I['L>']),
	(I['A'], I['L<']): (I['L.'], I['L<']),
	(I['A'], I['L>=']): (I['L.'], I['L>=']),
	(I['A'], I['L<=']): (I['L.'], I['L<=']),
	(I['A'], I['L!=']): (I['L.'], I['L!=']),

	# Chained relations
	(I['L'], I['L']): (I['LL'], I['L']),
	(I['R'], I['R']): (I['R'], I['RR']),

	# Last ]R is actually ]B
	(I['R'], I['R=']): (I['B'], I['R=']),
	(I['R'], I['R>']): (I['B'], I['R>']),
	(I['R'], I['R<']): (I['B'], I['R<']),
	(I['R'], I['R>=']): (I['B'], I['R>=']),
	(I['R'], I['R<=']): (I['B'], I['R<=']),
	(I['R'], I['R!=']): (I['B'], I['R!=']),
	(I['R'], I['And']): (I['B'], I['And']),
	(I['R'], I['End']): (I['B'], I['End']),
	(I['RR'], I['R=']): (I['B'], I['R=']),
	(I['RR'], I['R>']): (I['B'], I['R>']),
	(I['RR'], I['R<']): (I['B'], I['R<']),
	(I['RR'], I['R>=']): (I['B'], I['R>=']),
	(I['RR'], I['R<=']): (I['B'], I['R<=']),
	(I['RR'], I['R!=']): (I['B'], I['R!=']),
	(I['RR'], I['And']): (I['B'], I['And']),
	(I['RR'], I['End']): (I['B'], I['End']),
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
def delace(mqry: str):

	# Replace multiple spaces with a single space
	mqry = ' '.join(str(mqry).strip().split())

	# Remove spaces around operators
	mqry = re.sub(r'\s*([!<>=]+)\s*', r'\1', mqry)

	# Prepend zero before decimals, such as =.5 to =0.5
	mqry = re.sub(r'([<>=])(\-?)\.([0-9])', lambda m: f"{m.group(1)}{m.group(2)}0.{m.group(3)}", mqry)

	if not mqry.endswith(';'): mqry+=';'

	if mqry == ';': raise Exception("Error: Empty query provided.")

	mqry_chars = list(mqry)
	mqry_len = len(mqry_chars)

	side = CLOSE
	operators = [I['opr']]
	operands = [I['mix']]

	i = 0
	while i < mqry_len:
		c = mqry_chars[i]
		operand = ''

		# Comment: skip until newline
		if c == '/' and i+1 < mqry_len and mqry_chars[i+1] == '/':
			while i < mqry_len and mqry_chars[i] != '\n': i += 1
			i += 1

		# Operators
		elif c in OPR_CHR:

			# Collect up to 3 more valid operator characters
			opstr = c
			j = 1
			while j < 2 and (i + j) < mqry_len:
				cc = mqry_chars[i + j]
				if not OPR_CHR.get(cc) or OPR_CHR[cc] < 2: break
				opstr += cc
				j += 1

			if not OPSIDE[side].get(opstr):
				raise Exception(f"Memelang parse error: Operator {opstr} not recognized at char {i} in {mqry}")

			operator = OPSIDE[side][opstr]
			
			if OPRSEQ.get((operators[-1], operator)):
				operators[-1], operator = OPRSEQ[(operators[-1], operator)]

			elif OPR[operator]['side']!=side:
				if side!=CLOSE and OPR[operator]['side']<side:
					raise Exception(f"Memelang parse error: Side order for {opstr} at char {i} in {mqry}")

			elif side==LEFT:
				if OPR[operator]['func']>OPR[operators[-1]]['func']:
					raise Exception(f"Memelang parse error: Left operator order for {opstr} after {K[operators[-1]]} at char {i} in {mqry}")

			elif side==RIGHT:
				if OPR[operator]['func']<OPR[operators[-1]]['func']:
					raise Exception(f"Memelang parse error: Right operator order for {opstr} after {K[operators[-1]]} at char {i} in {mqry}")

			side=OPR[operator]['side']
			operators.append(operator)
			operands.append(None)

			i += j

		# Double-quote string ="George Washtingon's Horse \"Blueskin\""
		elif c == '"':
			while i < mqry_len-1:
				i += 1
				ch = mqry_chars[i]
				if ch=='\\':
					i+=1
					operand += mqry_chars[i]
				elif ch=='"':
					i+=1
					break
				else:
					operand += ch

			operators.append(OPSIDE[side]['"'])
			operands.append(operand)

		# key/int/float
		else:
			while i < mqry_len and re.match(r'[a-z0-9_\.\-]', mqry_chars[i]):
				operand += mqry_chars[i]
				i += 1

			if operand.isdigit(): operand=int(operand)

			# = True/false/get
			if operand in (0,1,'t','f','g'):
				if operand=='f': operand=0
				elif operand=='t': operand=1
				elif operand=='g': operand=2
				else: operand=int(operand)
				operators.append(OPSIDE[side]['1'])
				operands.append(operand)

			# =tn for or-group
			elif isinstance(operand, str) and (tm := re.match(r't([0-9])$', operand)):
				operators.append(I['Or'])
				operands.append(int(tm.group(1)))
				operators.append(I['1'])
				operands.append(1)

			# L/LL/R/RR fill operand
			elif OPR[operators[-1]]['func']==REL: operands[-1]=operand

			# Start of statement, assume A, might switch to Decimal later
			elif side==CLOSE:
				side=LEFT
				operators.append(OPSIDE[side]['a'])
				operands.append(operand)

			# Decimal
			elif (isinstance(operand, str) and '.' in operand) or isinstance(operand, int):
				operators.append(OPSIDE[side]['.'])
				operands.append(float(operand))

			else: raise Exception(f"Memelang parse error: Unexpected '{operand}' at char {i} in {mqry}")

	return operators, operands


# Input: operators, operands
# Output: Memelang string operator1operand1operator2operand2
def interlace(operators: list, operands: list, interlace_set={}):
	mqry = ''

	for i,operator in enumerate(operators):
		if i==0: continue
		
		operand = str(operands[i])

		# Special case: decimal number
		if OPR[operator]['form'] == DEC:
			if '.' not in operand:
				if float(operand)>0:
					if float(operand)>1: operand = operand + '.0'
					else: operand = '0.' + operand
				else:
					if float(operand)<-1: operand = operand + '.0'
					else: operand = '-0.' + operand[1:]

		elif OPR[operator]['form'] == NON:
			operand = OPR[operator]['$mid']
			if operator == I['End'] and interlace_set.get('newline'): operand+="\n"

		# Append the interlaced expression
		if interlace_set.get('html'):
			mqry += '<var class="v' + str(operator) + '">' + html.escape(OPR[operator]['$beg'] + operand + OPR[operator]['$end']) + '</var>'
		else:
			mqry += OPR[operator]['$beg'] + operand + OPR[operator]['$end']

	if interlace_set.get('html'):
		mqry = '<code class="meme">' + mqry + '</code>'

	return mqry


def normalize (operators: list, operands: list):

	if operators[-1]!=I['End']:
		operators.append(I['End'])
		operands.append(None)

	o=0
	olen=len(operators)
	while o<olen-2:
		o+=1
		operator=operators[o]

		# A]R] => A[is]R]
		if operator==I['A'] and operators[o+1]==I['R']:
			operators.insert(o+1, I['L'])
			operands.insert(o+1, I['is'])
			olen += 1

		# A[R]B => A[is]R]B
		elif operator==I['A'] and operators[o+1]==I['L'] and operators[o+2]==I['B']:
			operators.insert(o+1, I['L'])
			operands.insert(o+1, I['is'])
			operators[o+2]=I['R']
			olen += 1

		# ;A => ;t=A
		elif False and OPR[operators[o]]['side']==CLOSE and operators[o+1]==I['A']:
			operators.insert(o+1, I['L1'])
			operands.insert(o+1, 1)
			operators.insert(o+2, I['L='])
			operands.insert(o+2, None)
			olen += 2

		# B; => B=t;
		elif operators[o]==I['B'] and OPR[operators[o+1]]['side']==CLOSE:
			operators.insert(o+1, I['R='])
			operands.insert(o+1, None)
			operators.insert(o+2, I['R1'])
			operands.insert(o+2, 1)
			olen += 2


# Input: operators, operands
# Output [[[operator, operator], [operand, operand]]]
def cmdify(operators: list, operands: list, cmdify_set={}):
	if not operators: return []

	if operators[-1]!=I['End']:
		operators.append(I['End'])
		operands.append(None)

	cmds = []
	cmd = []
	state = [[], []]

	for o,operator in enumerate(operators):
		if o==0: continue
		elif OPR[operator]['side'] == CLOSE:
			if state[0]:
				cmd.append(state)
				state = [[], []]

			if operator == I['End'] and cmd:
				cmds.append(cmd)
				cmd = []

		else:
			state[0].append(operator)
			state[1].append(operands[o])

	return cmds


#### MEMELANG-SQL CONVERSION ####

# Input: Memelang query string
# Output: SQL query string
def querify(mqry: str, meme_table=None, name_table=None):
	if not meme_table: meme_table=DB_TABLE_MEME
	if not name_table: name_table=DB_TABLE_NAME

	operators, operands = delace(mqry)

	if name_table: 
		operands = identify(operands, name_table)
		missings = [x for x in operands if isinstance(x, str)]
		if missings:
			raise Exception("Unknown keys: " + ", ".join(missings))

	cmds = cmdify(operators, operands)

	queries = []
	params = []

	for cmd in cmds:
		sql, param = subquerify(cmd, meme_table)
		queries.append(sql)
		params.extend(param)

	return [' UNION '.join(queries), params]


# Input: One mcmd memelang cmd array
# Output: One SQL query string
def subquerify(cmd: list, table=DB_TABLE_MEME):
	qry_set = {'all': False, 'of': False}
	true_groups = {}
	false_group = []
	get_statements = []
	or_groups = {}
	true_cnt = 0
	or_cnt = 0
	false_cnt = 0

	# Group statements logically
	for statement in cmd:
		if not statement or not statement[0]: continue
		elif statement[0][0]==I['A'] and statement[1][0]==I['qry']:
			qry_set[statement[1][1]]=True
			continue

		last_operator = statement[0][-1]
		last_operand = statement[1][-1]

		# Handle =f (false)
		if last_operator == I['R1'] and last_operand == I['f']:
			false_cnt += 1
			false_group.append(statement)
			continue

		# Handle =g (get)
		if last_operator == I['R1'] and last_operand == I['g']:
			get_statements.append(statement)
			continue

		# Handle =tn (OR groups)
		if last_operator == I['Or']:
			or_cnt += 1
			if not or_groups.get(last_operand):
				or_groups[last_operand]=[]
			or_groups[last_operand].append(statement)
			continue

		# Default: Add to true conditions
		if OPR[last_operator]['func'] == VAL: tg=interlace(statement[0][:-2], statement[1][:-2])
		else: tg=interlace(statement[0], statement[1])

		if not true_groups.get(tg): true_groups[tg]=[]
		true_groups[tg].append(statement)
		true_cnt += 1

	# If qry_set['all'] and no true/false/or conditions
	if qry_set.get(I['all']) and true_cnt == 0 and false_cnt == 0 and or_cnt == 0:
		return [f"SELECT * FROM {table}", []]

	params = []
	cte_sqls = []
	cte_outs = []
	sql_outs = []
	cte_cnt = -1

	# Process AND conditions (true_groups)
	for true_group in true_groups.values():
		wheres = []
		cte_cnt += 1
		# Each bid_group is a list of 
		for statement in true_group:
			select_sql, from_sql, where_sql, qry_params, qry_depth = selectify(statement, table)
			if not wheres:
				wheres.append(where_sql)
				params.extend(qry_params)
			else:
				wheres.append(where_sql[0:where_sql.find('qnt')-4])
				params.extend(qry_params[:-1])

		# If not the first CTE, link it to previous CTE
		if cte_cnt > 0:
			wheres.append(f"{select_sql[:6]} IN (SELECT aid FROM z{cte_cnt-1})")

		cte_sqls.append(f"z{cte_cnt} AS (SELECT {select_sql} {from_sql} WHERE {' AND '.join(wheres)})")
		cte_outs.append((cte_cnt, qry_depth))

	# Process OR groups
	# Each key in or_groups is an integer (the tn), or_groups[key] is a list of 
	for or_group in or_groups.values():
		cte_cnt += 1
		max_depth = 0
		or_selects = []
		for statement in or_group:
			select_sql, from_sql, where_sql, qry_params, qry_depth = selectify(statement, table)
			max_depth = max(max_depth, qry_depth)
			
			if cte_cnt > 0:
				where_sql += f" AND m0.aid IN (SELECT a0 FROM z{cte_cnt-1})"
			
			or_selects.append(f"SELECT {select_sql} {from_sql} WHERE {where_sql}")
			params.extend(qry_params)
		
		cte_sqls.append(f"z{cte_cnt} AS ({' UNION '.join(or_selects)})")
		cte_outs.append((cte_cnt, max_depth))

	# Process NOT conditions (false_group)
	if false_cnt:
		if true_cnt < 1:
			raise Exception('A query with a false statement must contain at least one non-OR true statement.')

		wheres = []
		for statement in false_group:
			select_sql, from_sql, where_sql, qry_params, qry_depth = selectify(statement, table, True)
			wheres.append(f"a0 NOT IN (SELECT {select_sql} {from_sql} WHERE {where_sql})")
			params.extend(qry_params)

		fsql = f"SELECT aid FROM z{cte_cnt} WHERE " + ' AND '.join(wheres)
		cte_cnt += 1
		cte_sqls.append(f"z{cte_cnt} AS ({fsql})")


	# select all data related to the matching As
	if qry_set.get(I['all']):
		sql_outs.append(f"SELECT aid as a0, lid as l0, rid as r0, bid as b0, eid as e0, qnt as q0 FROM {table} m0 WHERE m0.aid IN (SELECT a0 FROM z{cte_cnt})")

	else:
		for statement in get_statements:
			select_sql, from_sql, where_sql, qry_params, qry_depth = selectify(statement, table)
			sql_outs.append(f"SELECT {select_sql} {from_sql} WHERE {where_sql} AND m0.aid IN (SELECT a0 FROM z{cte_cnt})")
			params.extend(qry_params)

	for zmNum in cte_outs:
		zNum, mNum = zmNum

		cWhere=[];
		if zNum < cte_cnt:
			cWhere.append(f"a0 IN (SELECT a0 FROM z{cte_cnt})")

		m=0;
		while mNum>=m:
			sql_outs.append(f"SELECT DISTINCT a{m}, l{m}, r{m}, b{m}, e{m}, q{m} FROM z{zNum}" + ('' if len(cWhere)==0 else ' WHERE '+' AND '.join(cWhere) ))
			m+=1

	# Apply logic to As
	if qry_set.get(I['of']):
		sql_outs.append(f"SELECT m0.aid AS a0, '{I['of']}' AS l0, z.rid AS r0, z.bid AS b0, z.eid AS e0, z.qnt AS q0 FROM {table} m0 JOIN z{cte_cnt} AS z ON m0.aid = z.bid AND m0.lid = z.rid WHERE m0.lid={I['is']}")

	return ['WITH ' + ', '.join(cte_sqls) + ' ' + ' UNION '.join(sql_outs), params]


# Input: One Memelang statement array
# Output: SELECT string, FROM string, WHERE string, and depth int
def selectify(statement, table=None, aidOnly=False):
	if not table: table=DB_TABLE_MEME

	params = []
	wheres = []
	joins = [f"FROM {table} m0"]
	selects = ['m0.aid AS a0','m0.lid AS l0','m0.rid AS r0','m0.bid AS b0','m0.eid AS e0','m0.qnt AS q0']
	m = 0
	opr=None
	val=None

	for i, operator in enumerate(statement[0]):
		operand = statement[1][i]
		side = OPR[operator]['side']
		func = OPR[operator]['func']
		form = OPR[operator]['form']

		# A/B
		if func == AB:
			fld = 'aid' if side==LEFT else 'bid'
			wheres.append(f'm{m}.{fld}=%s')
			params.append(operand)

		# equality operators # > <
		elif func == EQL: 
			opr = OPR[operator]['$mid']
			#if side==LEFT: wheres.append(f"m{m}.qnt{opr}{val}")

		# value
		elif func == VAL:
			# t/f
			if form==INT:
				opr='!='
				val='0'
			elif form==DEC: val = str(float(operand))
			else: raise Exception('invalid form')
			if side==RIGHT: wheres.append(f"m{m}.qnt{opr}{val}")

		# REL
		elif func == REL:
			fld = 'lid' if side==LEFT else 'rid'
			if OPR[operator]['dpth'] == 2:
				if side==LEFT: raise Exception('What does it mean to look up an L chain?')

				lm = m
				m += 1
				wheres.append(f"m{lm}.qnt!=0")
				joins.append(f"JOIN {table} m{m} ON m{lm}.bid=m{m}.aid")
				selects.append(f"m{m}.aid AS a{m}")
				selects.append(f"m{m}.lid AS l{m}")
				selects.append(f"m{m}.rid AS r{m}")
				selects.append(f"m{m}.bid AS b{m}")
				selects.append(f"m{m}.eid AS e{m}")
				selects.append(f"m{m}.qnt AS q{m}")

			if operand is not None:
				wheres.append(f'm{m}.{fld}=%s')
				params.append(operand)

		else:
			raise Exception('Error: unknown operator')


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
def aidcache(keys, name_table=None):
	if not name_table: name_table=DB_TABLE_NAME
	if not keys: return

	uncached_keys = [key for key in keys if key not in I]

	if not uncached_keys: return

	rows=db.namegets([], [KEY], uncached_keys, name_table)

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

	aidcache([key for key in keys if isinstance(key, str)], name_table) #  and not key.isdigit()

	for key in keys:
		if not isinstance(key, str): ids.append(key)
		#eqlif key.isdigit(): ids.append(int(key))
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
		if isinstance(operand, int): # or (isinstance(operand, str) and operand.isdigit())
			operands[i] = int(operands[i])
			matches.append(operands[i])

	names = db.namegets(matches, bids, [], name_table)

	namemap = {}
	for name in names:
		if not namemap.get(name[0]): namemap[int(name[0])]={}
		namemap[int(name[0])][int(name[1])]=name[2]

	for i,operand in enumerate(operands):
		if i==0: continue
		for bid in bids:
			if isinstance(operand, int):
				if namemap.get(operand) and namemap[operand].get(bid): output[bid].append(namemap[operand][bid])
				else: output[bid].append(False)
			else:
				output[bid].append(operand)

	return list(output.values())


# Input a Memelang query string
# Replace keys with aids
# Execute in DB
# Return results (optionally replacing aids with keys with statement "qry.nam:key=1")
def get(mqry, meme_table=None, name_table=None):
	if not meme_table: meme_table=DB_TABLE_MEME
	if not name_table: name_table=DB_TABLE_NAME
	output=[[I['opr']], [I['id']]]
	mqry, namekeys = dename(mqry)
	sql, params = querify(mqry, meme_table)	
	memes = db.select(sql, params)

	for meme in memes:
		v=float(meme[5])
		eo=int(meme[4])
		vo = I['R1'] if v in (0,1) and eo==I['R='] else I['R.']
		#if v in (0,1): e=I['R1']
		output[0].extend(ALRB + [eo, vo, I['End']])
		output[1].extend([int(meme[0]), int(meme[1]), int(meme[2]), int(meme[3]), None, v, None])

	if namekeys: output.extend(namify(output[1], namekeys, name_table))

	return output


# Return meme count of above results
def count(mqry, meme_table=DB_TABLE_MEME, name_table=DB_TABLE_NAME):
	sql, params = querify(mqry, meme_table)
	return len(db.select(sql, params))


def put (operators: list, operands: list, meme_table=None, name_table=None):
	if not operators: return operators, operands
	if not meme_table: meme_table=DB_TABLE_MEME
	if not name_table: name_table=DB_TABLE_NAME

	# Load IDs
	aidcache(operands)

	# Normalize memes
	normalize(operators, operands)

	missings = {}
	name_sqls = []
	name_params = []
	sqls = {meme_table:[], name_table:[]}
	params = {meme_table:[], name_table:[]}

	# Convert operands to IDs where possible
	for o, operator in enumerate(operators):
		if o==0: continue
		elif OPR[operator]['form']==AID:
			if isinstance(operands[o], int): pass
			elif I.get(operands[o]): operands[o]=I[operands[o]]
			else: missings[operands[o]]=1

	# Structure input
	cmds=cmdify(operators, operands)

	# Pull out ID-KEYs
	for cmd in cmds:
		for subopertors, suboperands in cmd:
			if subopertors==ALRBES and suboperands[2]==NAM and suboperands[3]==KEY:
				missings.pop(suboperands[5], None)
				aid = int(suboperands[0])
				key = suboperands[5]
				sqls[name_table].append("(%s,%s,%s)")
				params[name_table].extend([aid, KEY, key])
				I[key]=aid
				K[aid]=key

	# Missing keys with no associated ID
	if missings:
		aid = db.maxnum('aid', name_table) or I['cor']
		for key, val in missings.items():
			aid += 1
			sqls[name_table].append("(%s,%s,%s)")
			params[name_table].extend([aid, KEY, key])
			I[key]=aid
			K[aid]=key

	# Pull out names and trues
	for cmd in cmds:
		for subopertors, suboperands in cmd:
			if subopertors[0:4]!=ALRB: continue

			# Convert to new IDs
			for ca,suboperand in enumerate(suboperands):
				if isinstance(suboperand, str): suboperands[ca]=I[suboperand]

			if len(subopertors)<6:
				print(subopertors, suboperands)
				exit()

			# A[L|R]B=String
			if subopertors[5]==I['R"']:
				if suboperands[3]==KEY: continue # Keys are already done
				params[name_table].extend([suboperands[0], suboperands[3], suboperands[5]])
				sqls[name_table].append('(%s,%s,%s)')

			# A[L|R]B=Decimal/True
			else:
				suboperands[4] = subopertors[4]
				params[meme_table].extend(suboperands)
				sqls[meme_table].append('(%s,%s,%s,%s,%s,%s)')

	for tbl in params:
		if params[tbl]:
			db.insert(f"INSERT INTO {tbl} VALUES " + ','.join(sqls[tbl]) + " ON CONFLICT DO NOTHING", params[tbl])

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


#### MEME FILE ####

def read (file_path):
	output = [[I['opr']],[I['mix']]]
	with open(file_path, 'r', encoding='utf-8') as f:
		for ln, line in enumerate(f, start=1):

			if line.strip() == '' or line.strip().startswith('//'):
				continue

			line = re.sub(r'\s*//.*$', '', line, flags=re.MULTILINE)

			operators, operands = delace(line)

			if len(operators)<2: continue

			# End with semi colon
			elif operators[-1]!=I['End']:
				operators.append(I['End'])
				operands.append(None)
			
			output[0].extend(operators[1:])
			output[1].extend(operands[1:])

	return output[0], output[1]


def write (file_path, operators: list, operands: list):
	with open(file_path, 'w', encoding='utf-8') as file:
		file.write(interlace(operators, operands, {'newline':True}))


def logify (operators: list, operands: list):
	ais = {}
	cmds=cmdify(operators, operands)

	# Pull out A[L]R]B logic rules
	for cmd in cmds:
		for subopertors, suboperands in cmd:
			if subopertors[0:4] == ALRB and suboperands[1]!=I['is']:
				if not ais.get(suboperands[0]): ais[suboperands[0]]={}
				if not ais[suboperands[0]].get(suboperands[1]): ais[suboperands[0]][suboperands[1]]=[]
				ais[suboperands[0]][suboperands[1]].append([subopertors[3:], suboperands[2:]])

	# Apply A[L]R]B rules to C for A[L]C => C[R]B
	for cmd in cmds:
		for subopertors, suboperands in cmd:
			if subopertors[0:4] == ALRB and suboperands[1]==I['is'] and ais.get(suboperands[3]) and ais[suboperands[3]].get(suboperands[2]):
				for logioperators, logioperands in ais[suboperands[3]][suboperands[2]]:
					operators.extend([I['A'], I['L'], I['R']] + logioperators + [I['End']])
					operands.extend(suboperands[0:1] + [I['of']] + logioperands + [I['End']])
