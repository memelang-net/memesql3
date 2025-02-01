import re
import html
import db
from conf import *

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
def lowify(string: str) -> str:
	return re.sub(r'__+', '_', re.sub(r'[^a-z0-9]', '_', string.lower())).strip('_')


# Input: int, int
# Output: concatinated intint
def oprjoin (a: int, b: int) -> int:
	return int(bin(a)[2:] + bin(b)[2:].zfill(9), 2)


# Input: intint
# Output: int, int split at 9 bits
def oprsplit (value: int) -> tuple[int, int]:
	binary_string = bin(value)[2:].zfill(9)
	return (int(binary_string[:-9], 2) if a_bits else 0), int(binary_string[-9:], 2)


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

	if not mqry.endswith('End'): mqry+='End'

	if mqry == 'End': raise Exception("Error: Empty query provided.")

	mqry_chars = list(mqry)
	mqry_len = len(mqry_chars)

	side = LEFT
	operators = [OPER]
	operands = [MIX]
	opstr = ''

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
			opstr = c
			j = 1

			# Collect up to 3 more valid operator characters
			while j < 3 and (i + j) < mqry_len:
				cc = mqry_chars[i + j]
				if not PARSE.get(cc) or OPR_CHR[cc] < 2: break
				opstr += cc
				j += 1

			if OPSIDE[side].get(opstr):
				raise Exception(f"Memelang parse error: Operator {opstr} not recognized at char {i} in {mqry}")

			operator = OPSIDE[side][opstr]
			
			# SWITCH SIDES
			if OPR[operator]['side']!=side:
				side=OPR[operator]['side']

			# LEFT SIDE: V = A[RR[RR[R|
			elif side==LEFT: 

				if operators[-1]==OPER or OPR[operators[-1]]['side']!=LEFT: pass

				# If starting value was #a, followed by #eq, change to decimal
				elif OPR[operator]['func'] == EQL and OPR[operators[-1]]['func'] == AB: operators[-1]=I['Ldec']

				# Previous Lr is an Lr2
				elif operator == I['Lr'] and operators[-1]==I['Lr']: operators[-1]=I['Lr2']

				# Sequence error
				elif OPR[operator]['func']<OPR[operators[-1]]['func']:
					raise Exception(f"Memelang parse error: Operator order for {opstr} at char {i} in {mqry}")

			# RIGHT SIDE: |R]RR]RR]B = V
			elif side==RIGHT:

				# Sequence error
				if OPR[operator]['func']>OPR[operators[-1]]['func']:
					raise Exception(f"Memelang parse error: Operator order for {opstr} at char {i} in {mqry}")

				# Current Rr is Rr2
				elif operator == I['Rr'] and OPR[operators[-1]]['func']==REL: operator=I['Rr2']

				# Ending ]R becomes B
				elif OPR[operator]['func'] > AB and OPR[operators[-1]]['func']==REL: operators[-1]=I['Ra']

			operators.append(operator)

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

		# String/number
		else:
			while i < mqry_len and re.match(r'[a-z0-9_\.\-]', mqry_chars[i]):
				operand += mqry_chars[i]
				i += 1

			# True/false/get
			if operand in ('0','1','t','f','g'):
				if operand=='0': operand='f'
				elif operand=='1': operand='t'
				operators.append(OPSIDE[side]['1'])
				operands.append(I[operand])
				

			# =tn for or-group
			elif (tm := re.match(r't([0-9])$', operand)):
				operators.append(I['Or'])
				operands.append(int(tm.group(1)))
				operators.append(I['#v'])
				operands.append(I['t'])

			# Decimal
			elif '.' in operand:
				operators.append(OPSIDE[side]['.'])
				operands.append(float(operand))

			else:
				if operand.isdigit(): operand=int(operand)

				# Starting a
				elif len(operators)==1:
					operators.append(OPSIDE[side]['a'])
					operands.append(operand)

				# Fill in r operand
				elif OPR[operators[-1]]['func']==REL: operands[-1]=operand

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
			if '.' not in str(operand):
				if float(operand)>0:
					if float(operand)>1: operand = str(operand) + '.0'
					else: operand = '0.' + str(operand)
				else:
					if float(operand)<-1: operand = str(operand) + '.0'
					else: operand = '-0.' + str(abs(operand))

		elif if OPR[operator]['form'] == NON:
			operand = OPR[operator]['str']
			if OPR[operator]['func'] == END and interlace_set.get('newline'): operand+="\n"

		# Append the interlaced expression
		if interlace_set.get('html'):
			mqry += '<var class="v' + str(operator) + '">' + html.escape(OPR[operator]['pre'] + operand + OPR[operator]['post']) + '</var>'
		else:
			mqry += OPR[operator]['pre'] + operand + OPR[operator]['post']

	if interlace_set.get('html'):
		mqry = '<code class="meme">' + mqry + '</code>'

	return mqry


def alrbeqify (operators: list, operands: list):

	if operators[-1]!=I['End']:
		operators.append(I['End'])
		operands.append(None)

	o=0
	olen=len(operators)
	while o<olen:
		o+=1
		operator=operators[o]
		if o+3>=olen: break

		# A|R]B or A[R]B => A[is|R]B
		if operator==I['La'] and OPR[operators[o+1]]['func']==REL and operators[o+2]==I['Ra']:
			operators.insert(o+1, I['Lr'])
			operands.insert(o+1, I['is'])
			operators[o+2]=I['Mid']
			olen += 1

		# ;A => ;t=A
		if OPR[operators[o]]['func']==END and operators[o+1]==I['La']:
			operators.insert(o+1, I['Lint'])
			operands.insert(o+1, I['t'])
			operators.insert(o+2, I['L='])
			operands.insert(o+2, None)
			olen += 2

		# B; => B=t;
		elif operators[o]==I['Ra'] and OPR[operators[o+1]]['func']==END:
			operators.insert(o+1, I['R='])
			operands.insert(o+1, None)
			operators.insert(o+2, I['Rint'])
			operands.insert(o+2, I['t'])
			olen += 2


# Input: operators, operands
# Output [[[operator, operator], [operand, operand]]]
def cmdify(operators: list, operands: list, cmdify_set={}, table=DB_ALRBEQ):

	if not operators: return []

	if operators[-1]!=I['End']:
		operators.append(I['End'])
		operands.append(None)

	cmds = []
	cmd = []
	state = [[], []]

	for o,operator in enumerate(operators):
		if o==0: continue
		elif OPR[operator]['func'] == END:
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
def querify(mqry: str, alrbeq_table=None, abs_table=None):
	if not alrbeq_table: alrbeq_table=DB_ALRBEQ
	if abs_table is None: abs_table=DB_ABS

	operators, operands = delace(mqry)

	if abs_table: 
		operands = identify(operands, abs_table)
		missings = [x for x in operands if isinstance(x, str)]
		if missings:
			raise Exception("Unknown keys: " + ", ".join(missings))

	cmds = cmdify(operators, operands)

	queries = []
	params = []

	for cmd in cmds:
		sql, param = subquerify(cmd, alrbeq_table)
		queries.append(sql)
		params.extend(param)

	return [' UNION '.join(queries), params]


# Input: One mcmd memelang cmd array
# Output: One SQL query string
def subquerify(cmd: list, table=DB_ALRBEQ):
	qry_set = {'all': False, 'lgc': False}
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
		elif statement[0][0]==I['La'] and statement[1][0]==I['qry']:
			qry_set[statement[1][1]]=True
			continue

		last_operator = statement[0][-1]
		last_operand = statement[1][-1]

		# Handle =f (false)
		if last_operator == I['Rint'] and last_operand == I['f']:
			false_cnt += 1
			false_group.append(statement)
			continue

		# Handle =g (get)
		if last_operator == I['Rint'] and last_operand == I['g']:
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
			wheres.append(f"aid NOT IN (SELECT {select_sql} {from_sql} WHERE {where_sql})")
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
	if qry_set.get(I['lgc']):
		sql_outs.append(f"SELECT m0.aid AS a0, '{I['of']}' AS l0, z.rid AS r0, z.bid AS b0, z.eid AS r0, z.qnt AS q0 FROM {table} m0 JOIN z{cte_cnt} AS z ON m0.aid = z.bid AND m0.lid = z.rid WHERE m0.lid={I['is']}")

	return ['WITH ' + ', '.join(cte_sqls) + ' ' + ' UNION '.join(sql_outs), params]


# Input: One Memelang statement array
# Output: SELECT string, FROM string, WHERE string, and depth int
def selectify(statement, table='meme', aidOnly=False):

	params = []
	wheres = []
	joins = [f"FROM {table} m0"]
	selects = ['m0.aid AS a0','m0.lid AS l0','m0.rid AS r0','m0.bid AS b0','m0.eid AS e0','m0.qnt AS q0']
	m = 0
	opr='!='
	val='0'

	for i, operator in enumerate(statement[0]):
		operand = statement[1][i]
		side = OPR[operator]['side']
		func = OPR[operator]['func']
		dpth = OPR[operator]['dpth']
		string = OPR[operator]['str']
		form = OPR[operator]['form']

		# A/B
		if func == AB:
			fld = 'aid' if side==LEFT else 'bid'
			wheres.append(f'm{m}.{fld}=%s')
			params.append(operand)

		# equality operators # > <
		elif func == EQL:
			opr = string

		# value
		elif func == VAL:
			# t/f
			if form==NUM:
				opr='!='
				val='0'
			elif form==DEC:
				val = float(operand)
			else: exit('invalid form')

		# REL
		# TODO: Redo this logic, which is probably wrong
		elif func == REL:
			if dpth == 1:
				if operand<0:
					# flip the prior A to a B
					selects[0] = f'm{m}.bid AS a{m}'
					selects[1] = f"m{m}.rid AS l{m}"
					selects[2] = f"m{m}.lid AS r{m}"
					selects[3] = f'm{m}.aid AS b{m}'
					if i > 0 and OPS[operators[i-1]]['func']==AB:
						wheres[-1] = f'm{m}.bid=%s'

			elif dpth == 2:
				lm = m
				m += 1

				wheres.append(f"m{lm}.qnt!=0")

				joins.append(f"JOIN {table} m{m} ON {selects[-3][:6]}=m{m}.aid")
				selects.append(f"m{m}.aid AS a{m}")
				selects.append(f"m{m}.lid AS l{m}")
				selects.append(f"m{m}.rid AS r{m}")
				selects.append(f"m{m}.bid AS b{m}")
				selects.append(f"m{m}.eid AS e{m}")
				selects.append(f"m{m}.qnt AS q{m}")

			if operand is not None:
				fld = 'lid' if side==LEFT else 'rid'
				wheres.append(f'm{m}.{fld}=%s')
				params.append(operand)

		else:
			raise Exception('Error: unknown operator')

	# last qnt condition
	wheres.append(f"m{m}.qnt{opr}{val}")

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
def aidcache(keys, table=DB_ABS):
	if not keys: return

	uncached_keys = [key for key in keys if key not in I]

	if not uncached_keys: return

	rows=db.namegets([], [KEY], uncached_keys, table)

	for row in rows:
		I[row[2]] = int(row[0])
		K[int(row[0])] = row[2]


# Input value is a list of strings ['a', 'b', 'c', 'd']
# Load key->aid
# Return the data with any keys with ids
def identify(keys: list, table=DB_ABS):
	ids = []

	if not keys: return ids

	aidcache([key for key in keys if isinstance(key, str)]) #  and not key.isdigit()

	for key in keys:
		if not isinstance(key, str): ids.append(key)
		#eqlif key.isdigit(): ids.append(int(key))
		elif I.get(key): ids.append(I[key])
		else: ids.append(key)

	return ids


def identify1(val, table=DB_ABS):
	ids = identify([val], table)
	return ids[0] if isinstance(ids[0], int) else False


# Input value is a list of ints [123,456,789]
# Load aid->key
# Return the data with any aids replaced with keys
def namify(operands: list, bids: list, table=DB_ABS):
	missings=[]

	output = {}
	for bid in bids:
		output[bid]=[bid]

	matches = []
	for i,operand in enumerate(operands):
		if isinstance(operand, int): # or (isinstance(operand, str) and operand.isdigit())
			operands[i] = int(operands[i])
			matches.append(operands[i])

	names = db.namegets(matches, bids)

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
def get(mqry, alrbeq_table=DB_ALRBEQ, abs_table=DB_ABS):
	output=[[OPER], [ID]]
	mqry, namekeys = dename(mqry)
	sql, params = querify(mqry, alrbeq_table)	
	memes = db.select(sql, params)

	for meme in memes:
		output[0].extend(ALRB + oprsplit(meme[4]) + [I['End']])
		output[1].extend([int(meme[0]), int(meme[1]), int(meme[2]), int(meme[3]), None, float(meme[5]), None])

	if namekeys: output.extend(namify(output[1], namekeys, abs_table))

	return output


# Return meme count of above results
def count(mqry, alrbeq_table=DB_ALRBEQ, abs_table=DB_ABS):
	sql, params = querify(mqry, alrbeq_table)
	return len(db.select(sql, params))


def put (operators: list, operands: list, alrbeq_table=None, abs_table=None):
	if not operators: return operators, operands
	if not alrbeq_table: alrbeq_table=DB_ALRBEQ
	if not abs_table: abs_table=DB_ABS

	# Load IDs
	aidcache(operands)

	# Normalize memes
	alrbeqify(operators, operands)

	missings = {}
	name_sqls = []
	name_params = []
	sqls = {alrbeq_table:[], abs_table:[]}
	params = {alrbeq_table:[], abs_table:[]}

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
		for cmd_tors, cmd_ands in cmd:
			if cmd_tors==ALRBES and cmd_ands[2]==NAM and cmd_ands[3]==KEY:
				missings.pop(cmd_ands[5], None)
				aid = int(cmd_ands[0])
				key = cmd_ands[5]
				sqls[abs_table].append("(%s,%s,%s)")
				params[abs_table].extend([aid, KEY, key])
				I[key]=aid
				K[aid]=key

	# Missing keys with no associated ID
	if missings:
		aid = db.maxnum('aid', abs_table) or I['cor']
		for key, val in missings.items():
			aid += 1
			sqls[abs_table].append("(%s,%s,%s)")
			params[abs_table].extend([aid, KEY, key])
			I[key]=aid
			K[aid]=key

	# Pull out names and trues
	for cmd in cmds:
		for cmd_tors, cmd_ands in cmd:
			if cmd_tors[0:4]!=ALRB: continue

			# Convert to new IDs
			for ca,cmd_and in enumerate(cmd_ands):
				if isinstance(cmd_and, str):
					cmd_ands[i]=I[cmd_and]

			# A[L|R]B=String
			if cmd_tors[5]==I['Rstr']:
				if cmd_ands[3]==KEY: continue # Keys are already done
				params[abs_table].extend([cmd_ands[0], cmd_ands[3], cmd_ands[5]])
				sqls[abs_table].append('(%s,%s,%s)')

			# A[L|R]B=Decimal/True
			else:
				cmd_ands[5] = oprjoin(cmd_tors[5], cmd_tors[6])
				params[alrbeq_table].extend(cmd_ands)
				sqls[alrbeq_table].append('(%s,%s,%s,%s,%s,%s)')

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
	output = [[OPER],[MIX]]
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
		for cmd_tors, cmd_ands in cmd:
			if cmd_tors[0:4] == ALRB and cmd_ands[1]!=I['is']:
				if not ais.get(cmd_ands[0]): ais[cmd_ands[0]]={}
				if not ais[cmd_ands[0]].get(cmd_ands[1]): ais[cmd_ands[0]][cmd_ands[1]]=[]
				ais[cmd_ands[0]][cmd_ands[1]].append([cmd_tors[3:], cmd_ands[2:]])

	# Apply A[L]R]B rules to C for A[L[C => C]R]B
	for cmd in cmds:
		for cmd_tors, cmd_ands in cmd:
			if cmd_tors[0:4] == ALRB and cmd_ands[1]==I['is'] and ais.get(cmd_ands[3]) and ais[cmd_ands[3]].get(cmd_ands[2]):
				for logioperators, logioperands in ais[cmd_ands[3]][cmd_ands[2]]:
					operators.extend([I['#a'], I['#r'], I['Mid']] + logioperators + [I['End']])
					operands.extend(cmd_ands[0:1] + [I['of']] + logioperands + [I['End']])
