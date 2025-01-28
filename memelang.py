import re
import html
import db
from conf import *

# Conbine SQL and parameters into a string
def morfigy(sql, params):
	new_query = sql
	for param in params:

		if isinstance(param, str): param = "'"+str(param).replace("'", "''")+"'"
		else: param = str(param)

		new_query = new_query.replace("%s", param, 1)
	return new_query


# Input: string "John Adams"
# Output: lowercase underscored string "john_adams"
def lowify(string):
	return re.sub(r'__+', '_', re.sub(r'[^a-z0-9]', '_', string.lower())).strip('_')


#### MEMELANG QUERY PARSING ####

# Input: Memelang string operator1operand1operator2operand2
# Output: [operator1, operator2, ...], [operand1, operand2, ...]
def delace(mqry, delace_set={}):

	if not delace_set.get(' '):
		delace_set[' ']='&'

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

	operators = [OPER]
	operands = [MIX]
	sequence = SEQ_A
	opstr = ''

	i = 0
	while i < mqry_len:
		c = mqry_chars[i]
		operand = ''

		# Space char is variable
		if c == ' ': c = delace_set[' ']


		# Comment: skip until newline
		if c == '/' and i+1 < mqry_len and mqry_chars[i+1] == '/':
			while i < mqry_len and mqry_chars[i] != '\n': i += 1
			i += 1

		# Operators
		elif c in OPR_CHR:
			opstr = c
			j = 1

			# [xx]
			if c == '[':
				# Collect up to 6 more characters or until you find a ']'
				while j < 6 and (i + j) < mqry_len:
					cc = mqry_chars[i + j]
					opstr += cc
					j += 1
					if cc == ']': break
			else:
				# Collect up to 3 more valid operator characters
				while j < 3 and (i + j) < mqry_len:
					cc = mqry_chars[i + j]
					if not OPR_CHR.get(cc) or OPR_CHR[cc] < 2: break
					opstr += cc
					j += 1

			operator = I[opstr]

			if operator not in OPR:
				raise Exception(f"Memelang parse error: Operator {opstr} not recognized at char {i} in {mqry}")

			# Semicolon separates commands, space separates statements
			elif OPR[operator]['seq'] >= SEQ_AND:
				sequence = SEQ_A

			# Short -> long for second . or '
			elif sequence == SEQ_R and OPR[operator]['seq'] == SEQ_R:
				if operator == I['.']: operator=I['[.]']   # .R.R
				elif operator == I["'"]: operator=I["[']"] # 'R'R
				sequence = OPR[operator]['seq']

			elif OPR[operator]['seq'] < sequence:
				raise Exception(f"Memelang parse error: Unexpected operator {opstr} at char {i} in {mqry}")

			else: sequence = OPR[operator]['seq']

			operators.append(operator)
			operands.append(None)

			i += j

		# Double-quote string ="George Washtingon's Horse \"Blueskin\""
		elif c == '"':
			if operators[-1]!=I['=']: raise Exception(f"Errant quote at char {i} in {mqry}")

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

			operators[-1]=I['$']
			operands[-1]=operand
			sequence=SEQ_EQL

		# String/number following equal sign
		elif sequence == SEQ_EQL:

			while i < mqry_len and re.match(r'[a-z0-9_\.\-]', mqry_chars[i]):
				operand += mqry_chars[i]
				i += 1

			if operand=='0': operand='f'
			elif operand=='1': operand='t'

			if not re.match(r'[a-z]', operand):
				operators[-1]=I['#']
				operands[-1]=float(operand)
				sequence=SEQ_EQL

			elif operators[-1]!=I['=']: raise Exception(f"Memelang parse error: {operand} not after =")

			elif operand in ('t','f','g'):
				operands[-1]=I[operand]
				sequence=SEQ_EQL
		
			# =tn for or-group
			elif (tm := re.match(r't([0-9])$', operand)):
				operands[-1]='t'
				operators.append(I['|'])
				operands.append(int(tm.group(1)))
				sequence=SEQ_OR
			
			else: raise Exception(f"Memelang parse error: Unrecognized =Q at char {i} in {mqry}")
			

		else:
			while i < mqry_len and re.match(r'[a-z0-9_]', mqry_chars[i]):
				operand += mqry_chars[i]
				i += 1

			if operand.isdigit():
				operand=int(operand)

			# A string
			if sequence == SEQ_A:
				operators.append(I['@'])
				operands.append(operand)

			# String following R B or [xx]
			elif sequence in (SEQ_R, SEQ_RR, SEQ_B): operands[-1]=operand

			else: raise Exception(f"Memelang parse error: Unexpected character '{mqry_chars[i]}' at char {i} in {mqry}")

	return operators, operands


# Input: operators, operands
# Output: Memelang string operator1operand1operator2operand2
def interlace(operators, operands, interlace_set={}):
	mqry = ''

	if interlace_set.get('html'):
		mqry+='<code class="meme">'

	for i,operator in enumerate(operators):
		if i==0: continue
		
		opstr = OPR[operator]['shrt'] 

		if interlace_set.get('opr'):
			if interlace_set['opr']=='long': opstr = OPR[operator]['long']
			elif interlace_set['opr']=='id': opstr = f"[{operator}]"
			else: exit('interlace opr')

		operand = None if OPR[operator]['frm']=='slf' else operands[i]
		eopstr = None

		# Special cases
		if operator == I['#']:
			if '.' not in str(operand):
				operand = str(operand) + '.0'

		elif operator == I[';'] and interlace_set.get('newline'):
			opstr+="\n"

		elif operator == I['$']:
			eopstr='"'

		# Append the interlaced expression
		if interlace_set.get('html'):
			if opstr: mqry += html.escape(opstr)
			if operand is not None: mqry += '<var class="v' + str(operator) + '">' + html.escape(str(operand)) + '</var>'
			if eopstr: mqry += html.escape(eopstr)
		else:
			mqry += opstr + (str(operand) if operand is not None else '') + (eopstr if eopstr is not None else '')

	if interlace_set.get('html'):
		mqry+='</code>'

	return mqry


def airbeqify (operators: list, operands: list):

	o=0
	olen=len(operators)

	if operators[-1]!=I[';']:
		operators.append(I[';'])
		operands.append(I[';'])
		olen += 1

	while o<olen:
		operator=operators[o]
		if o+3>=olen: break
		elif operator!=I['@'] or operators[o+1]!=I["."] or operators[o+2]!=I[":"]:
			o+=1
			continue

		# A.R:B; => A'is.R:B=t
		elif OPR[operators[o+3]]['seq']>=SEQ_AND:
			operators.insert(o+1, I["'"])
			operands.insert(o+1, I['is'])
			operators[o+2]=I['[.]']
			operators.insert(o+4, I['='])
			operands.insert(o+4, I['t'])
			olen += 2
			o+=4

		# A.R:B=Q => A'is.R:B=Q
		elif OPR[operators[o+3]]['seq']==SEQ_EQL:
			operators.insert(o+1, I["'"])
			operands.insert(o+1, I['is'])
			operators[o+2]=I['[.]']
			olen += 1
			o+=4
			continue

		else:
			raise Exception(operators[o:o+5])


# Input: operators, operands
# Output [[[operator, operator], [operand, operand]]]
def cmdify(operators: list, operands: list, cmdify_set={}, table=DB_AIRBEQ):

	if not operators: return []

	if operators[-1]!=I[';']:
		operators.append(I[';'])
		operands.append(I[';'])

	cmds = []
	cmd = []
	state = [[], []]

	for o,operator in enumerate(operators):
		if o==0: continue
		elif OPR[operator]['seq'] >= SEQ_AND:
			if state[0]:
				cmd.append(state)
				state = [[], []]

			if OPR[operator]['seq'] >= SEQ_END and cmd:
				cmds.append(cmd)
				cmd = []

		else:
			state[0].append(operator)
			state[1].append(operands[o])

	return cmds


#### MEMELANG-SQL CONVERSION ####

# Input: Memelang query string
# Output: SQL query string
def querify(mqry: str, airbeq_table=None, abs_table=None):
	if not airbeq_table: airbeq_table=DB_AIRBEQ
	if abs_table is None: abs_table=DB_ABS

	operators, operands = delace(mqry, {' ':'&'})

	if abs_table: 
		operands = identify(operands, abs_table)
		missings = [x for x in operands if isinstance(x, str)]
		if missings:
			raise Exception("Unknown keys: " + ", ".join(missings))

	cmds = cmdify(operators, operands)

	queries = []
	params = []

	for cmd in cmds:
		sql, val = subquerify(cmd, airbeq_table)
		queries.append(sql)
		params.extend(val)

	return [' UNION '.join(queries), params]


# Input: One mcmd memelang cmd array
# Output: One SQL query string
def subquerify(cmd: list, table=DB_AIRBEQ):
	qry_set = {'all': False}
	true_groups = {}
	false_group = []
	get_statements = []
	or_groups = {}
	true_cnt = 0
	or_cnt = 0
	false_cnt = 0

	# Group statements logically
	for statement in cmd:
		if statement[0][0]==I['@'] and statement[1][0]==I['qry']:
			qry_set[statement[1][1]]=True
			continue

		# Trim trailing semi-colon
		if statement[0][-1]==I[';']:
			statement[0].pop()
			statement[1].pop()

		last_operator = statement[0][-1] if statement else None
		last_operand = statement[1][-1] if statement else None
		if not last_operator: continue

		# Handle =f (false)
		if last_operator == I['t'] and last_operand == I['f']:
			false_cnt += 1
			# all but last mexpression
			false_group.append(statement)
			continue

		# Handle =g (get)
		if last_operator == I['t'] and last_operand == I['g']:
			get_statements.append(statement)
			continue

		# Handle =tn (OR groups)
		if last_operator == I['|']:
			or_cnt += 1
			if not or_groups.get(last_operand):
				or_groups[last_operand]=[]
			or_groups[last_operand].append(statement)
			continue

		# Default: Add to true conditions
		if OPR[last_operator]['seq'] >= SEQ_EQL: tg=interlace(statement[0][:-1], statement[1][:-1])
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
		sql_outs.append(f"SELECT aid as a0, iid as i0, rid as r0, bid as b0, eid as e0, qnt as q0 FROM {table} m0 WHERE m0.aid IN (SELECT a0 FROM z{cte_cnt})")
		
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
			#if m>0:
				#cWhere.append(f"a{m} IS NOT NULL AND r{m} NOT LIKE '?%'")

			sql_outs.append(f"SELECT DISTINCT a{m}, i{m}, r{m}, b{m}, e{m}, q{m} FROM z{zNum}" + ('' if len(cWhere)==0 else ' WHERE '+' AND '.join(cWhere) ))
			m+=1

	return ['WITH ' + ', '.join(cte_sqls) + ' ' + ' UNION '.join(sql_outs), params]


# Input: One Memelang statement array
# Output: SELECT string, FROM string, WHERE string, and depth int
def selectify(statement, table='meme', aidOnly=False):

	params = []
	wheres = []
	joins = [f"FROM {table} m0"]
	selects = ['m0.aid AS a0','m0.iid AS i0','m0.rid AS r0','m0.bid AS b0','m0.eid AS e0','m0.qnt AS q0']
	m = 0
	opr='!='
	qnt='0'

	for i, operator in enumerate(statement[0]):
		operand = statement[1][i]

		# A
		if operator == I['@']:
			wheres.append(f'm{m}.aid=%s')
			params.append(operand)

		# R
		elif operator == I['.']:
			if operand is not None:
				wheres.append(f'm{m}.rid=%s')
				params.append(operand)

		# RI
		elif operator == I["'"]:
			# flip the prior A to a B
			selects[0] = f'm{m}.bid AS a{m}'
			selects[1] = f"m{m}.rid AS i{m}"
			selects[2] = f"m{m}.iid AS r{m}"
			selects[3] = f'm{m}.aid AS b{m}'
			if i > 0:
				# the previous is presumably m0.aid=A
				wheres[0] = f'm{m}.bid=%s'
				params[0] = str(statement[1][i-1])

			if operand is not None:
				wheres.append(f'm{m}.rid=%s')
				params.append(operand)

		# B
		elif operator == I[':']:
			# inverse if previous was RI or BB
			if i > 0 and statement[0][i-1] in (I["'"], I["[']"]):
				wheres.append(f'm{m}.aid=%s')
				params.append(operand)
			else:
				wheres.append(f'm{m}.bid=%s')
				params.append(operand)

		# true/false
		elif operator == I['=']:
			operand = '=' if operator==I['f'] else '!='
			qnt=FALQNT

		# equality operators # > <
		elif OPR[operator]['seq'] == SEQ_EQL:
			opr = '=' if operator==I['#'] else K[operator]
			qnt = float(operand)

		# JOINS [b=a] [b=b]
		else:
			lm = m
			m += 1

			if operand is not None:
				wheres.append(f'm{m}.rid=%s')
				params.append(operand)

			wheres.append(f"m{lm}.qnt!=0")

			if operator == I['[.]']:
				joins.append(f"JOIN {table} m{m} ON {selects[-3][:6]}=m{m}.aid")
				selects.append(f"m{m}.aid AS a{m}")
				selects.append(f"m{m}.iid AS i{m}")
				selects.append(f"m{m}.rid AS r{m}")
				selects.append(f"m{m}.bid AS b{m}")
				selects.append(f"m{m}.eid AS e{m}")
				selects.append(f"m{m}.qnt AS q{m}")
			elif operator == I["[']"]:
				joins.append(f"JOIN {table} m{m} ON {selects[-3][:6]}=m{m}.bid")
				selects.append(f"m{m}.bid AS a{m}")
				selects.append(f"m{m}.rid AS i{m}")
				selects.append(f"m{m}.iid AS r{m}")
				selects.append(f"m{m}.aid AS b{m}")
				selects.append(f"m{m}.eid AS e{m}")
				selects.append(f"(CASE WHEN m{m}.qnt = 0.0 THEN 0 ELSE 1.0 / m{m}.qnt END) AS q{m}")
			else:
				raise Exception('Error: unknown operator')

	# last qnt condition
	wheres.append(f"m{m}.qnt{opr}{qnt}")

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
		#elif key.isdigit(): ids.append(int(key))
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
def get(mqry, airbeq_table=DB_AIRBEQ, abs_table=DB_ABS):
	output=[[OPER], [ID]]
	mqry, namekeys = dename(mqry)
	sql, params = querify(mqry, airbeq_table)	
	memes = db.select(sql, params)

	for meme in memes:
		output[0].extend(AIRB + [meme[4], I[';']])
		output[1].extend([int(meme[0]), int(meme[1]), int(meme[2]), int(meme[3]), float(meme[5]), I[';']])

	if 'qry.logi' in mqry:
		logioperators, logioperands = logify(output[0], output[1])
		output[0].extend(logioperators)
		output[1].extend(logioperands)

	if namekeys: output.extend(namify(output[1], namekeys, abs_table))

	return output


# Return meme count of above results
def count(mqry, airbeq_table=DB_AIRBEQ, abs_table=DB_ABS):
	sql, params = querify(mqry, airbeq_table)
	return len(db.select(sql, params))


def put (operators: list, operands: list, airbeq_table=None, abs_table=None):
	if not operators: return operators, operands
	if not airbeq_table: airbeq_table=DB_AIRBEQ
	if not abs_table: abs_table=DB_ABS

	# Load IDs
	aidcache(operands)

	# Normalize memes
	airbeqify(operators, operands)

	missings = {}
	name_sqls = []
	name_params = []
	sqls = {airbeq_table:[], abs_table:[]}
	params = {airbeq_table:[], abs_table:[]}

	# Convert operands to IDs where possible
	for o, operator in enumerate(operators):
		if o==0: continue
		elif OPR[operator]['frm']=='aid':
			if isinstance(operands[o], int): pass
			#elif isinstance(operands[o], str) and operands[o].isdigit(): operands[o]=int(operands[o])
			elif I.get(operands[o]): operands[o]=I[operands[o]]

			# Missing keys with no associated ID
			elif operator in (I['.'],I["'"]): missings[operands[o]]=-1
			elif not missings.get(operands[o]): missings[operands[o]]=1

	# Structure input
	cmds=cmdify(operators, operands)

	# Pull out ID-KEYs
	for cmd in cmds:
		for suboperators, suboperands in cmd:
			if suboperators==AIRB+[I['$']] and suboperands[2]==NAM and suboperands[3]==KEY:
				missings[suboperands[4]]=0
				name_sqls.append("(%s,%s,%s)")
				name_params.extend([int(suboperands[0]), KEY, suboperands[4]])

	# Missing keys with no associated ID
	if missings:
		aid = db.maxnum('aid', abs_table) or I['cor']
		for key, val in missings.items():
			if val==0: continue
			aid +=1
			if val==-1 and aid%2: aid+=1
			name_sqls.append("(%s,%s,%s)")
			name_params.extend([aid, KEY, key])

	# Write keys and reload IDs
	if name_sqls:
		db.insert(f"INSERT INTO {abs_table} (aid, bid, str) VALUES " + ','.join(name_sqls) + " ON CONFLICT DO NOTHING", name_params)
		operand_ids=identify(operands)
		cmds=cmdify(operators, operand_ids)
		name_sqls = []
		name_params = []

	# Pull out names and trues
	for cmd in cmds:
		for suboperators, suboperands in cmd:
			if suboperators[0:4]!=AIRB: continue

			# A'I.R:B=String
			if suboperators[4]==I['$']:
				if suboperands[3]==KEY: continue # Keys are already done
				params[abs_table].extend([suboperands[0], suboperands[3], suboperands[4]])
				sqls[abs_table].append('(%s,%s,%s)')

			# A'I.R:B=Q
			else:
				suboperands.insert(4, suboperators[4])
				params[airbeq_table].extend(suboperands)
				sqls[airbeq_table].append('(%s,%s,%s,%s,%s,%s)')


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
			elif operators[-1]!=I[';']:
				operators.append(I[';'])
				operands.append(I[';'])
			
			output[0].extend(operators[1:])
			output[1].extend(operands[1:])

	return output[0], output[1]


def write (file_path, operators: list, operands: list):
	with open(file_path, 'w', encoding='utf-8') as file:
		file.write(interlace(operators, operands, {'newline':True}))



#### LOGIC ####

# A'I.R:B=Q
# person'kind.species:homosapien=t

def logify (aid: int, operators: list, operands: list):
	logioperators, logioperands = logiget (aid, operators, operands)
	operators+=logioperators[1:]
	operands+logioperands[1:]
	logirb(operators, operands)

def logiget (aid: int, operators: list, operands: list):

	ais=[]
	params=[]
	logioperators = [OPER]
	logioperands = [ID]
	cmds=cmdify(operators, operands)

	for cmd in cmds:
		for operators, operands in cmd:
			if operands[0]==aid and operators[0:4]==AIRB:
				ais.append(f"(aid=%s AND iid=%s)")
				params.extend([operands[3], operands[2]])

	if not ais: return logioperators, logioperands

	logis = db.select(f"SELECT * FROM {DB_AIRBEQ} WHERE " + ' OR '.join(ais), params)

	for logi in logis:
		logioperators.extend(AIRB + [suboperands[4], I[';']])
		logioperands.extend(suboperands[0:4] + suboperands[5:] + [I[';']])

	return logioperators, logioperands


def logirb (operators: list, operands: list):

	ais = {}
	cmds=cmdify(operators, operands)

	# Pull out .R:B logic rules
	for cmd in cmds:
		for suboperators, suboperands in cmd:
			if suboperators[0:4] == AIRB and suboperands[1]!=I['is']:
				if not ais.get(suboperands[0]): ais[suboperands[0]]={}
				if not ais[suboperands[0]].get(suboperands[1]): ais[suboperands[0]][suboperands[1]]=[]
				ais[suboperands[0]][suboperands[1]].append([suboperators[2:], suboperands[2:]])

	# Apply logic rules to A where A'is.R:B=t
	for cmd in cmds:
		for suboperators, suboperands in cmd:
			if suboperators[0:4] == AIRB and suboperands[1]==I['is'] and ais.get(suboperands[3]) and ais[suboperands[3]].get(suboperands[2]):
				for logioperators, logioperands in ais[suboperands[3]][suboperands[2]]:
					operators.extend([I['@'], I["'"]] + logioperators + [I[';']])
					operands.extend(suboperands[0:2] + logioperands + [I[';']])