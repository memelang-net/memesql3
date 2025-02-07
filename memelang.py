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

ACDB    = [I['A'], I['C'], I['D'], I['B']]
VACDB   = [I['C=I']] + ACDB
VACDBS  = VACDB + [I['D=S']]

NAM    = I['nam']
KEY    = I['key']
TRUE   = 1
FALSE  = 0

# Sides
COND   = -1		# Left side conditions
DECL   =  1		# Right side declarations

# Contexts
STAT   =  2 	# Statement
META   =  3		# Meta (And, END)

# Statement Funcs
REL    =  4		# Condition or Declaration
NOD    =  5		# A or B node
VAL    =  6		# Value (e.g. decimal number)
OR     =  7		# OR operator

# Meta funcs
AND    =  8		# AND operator
END    =  9		# END operator (;)

# Forms
NON    = 10		# Value has no form, like END
INT    = 11		# Value is integer, like True, False, Get
DEC    = 12		# Value is decimal number
AID    = 13		# Value is an ID integer
STR    = 14		# Value is a string

# Each operator in a Memelang and its meaning
OPR = {
	I['C=?']: { 		# Operator ID
		'side' : COND,	# Which side is it on? COND or DECL
		'cont' : STAT,  # What's the context? STAT or META
		'func' : VAL,	# What function does it do? REL, NOD, VAL, OR, AND, or END
		'form' : NON,	# What's it's output form? NON, INT, DEC, AID, or STR
		'dcol' : 'vop', # What's the DB column name?
		'dpth' : 0,		# For relations: 1 or 2
		'dfid' : None, 	# Default value ID
		'$beg' : '',	# Output string before
		'$mid' : '',	# Connstant output string in middle
		'$end' : '=',	# Output string end
	},
	I['C=I']: {
		'side' : COND,
		'cont' : STAT,
		'func' : VAL,
		'form' : INT,
		'dcol' : 'vop',
		'dpth' : 0,
		'dfid' : TRUE, 	# Default value ID
		'$beg' : '',
		'$mid' : '',
		'$end' : '=',
	},
	I['C=S']: {
		'side' : COND,
		'cont' : STAT,
		'func' : VAL,
		'form' : STR,
		'dcol' : False, # Not allowed yet
		'dpth' : 0,
		'dfid' : None,
		'$beg' : '"',
		'$mid' : '',
		'$end' : '"=',
	},
	I['C=D']: {
		'side' : COND,
		'cont' : STAT,
		'func' : VAL,
		'form' : DEC,
		'dcol' : 'vop',
		'dpth' : 0,
		'dfid' : None,
		'$beg' : '',
		'$mid' : '',
		'$end' : '=',
	},
	I['C>']: {
		'side' : COND,
		'cont' : STAT,
		'func' : VAL,
		'form' : DEC,
		'dcol' : 'vop',
		'dpth' : 0,
		'$beg' : '',
		'$mid' : '',
		'$end' : '>',
	},
	I['C<']: {
		'side' : COND,
		'cont' : STAT,
		'func' : VAL,
		'form' : DEC,
		'dcol' : 'vop',
		'dpth' : 0,
		'dfid' : None,
		'$beg' : '',
		'$mid' : '',
		'$end' : '<',
	},
	I['C>=']: {
		'side' : COND,
		'cont' : STAT,
		'func' : VAL,
		'form' : DEC,
		'dcol' : 'vop',
		'dpth' : 0,
		'dfid' : None,
		'$beg' : '',
		'$mid' : '',
		'$end' : '>=',
	},
	I['C<=']: {
		'side' : COND,
		'cont' : STAT,
		'func' : VAL,
		'form' : DEC,
		'dcol' : 'vop',
		'dpth' : 0,
		'$beg' : '',
		'$mid' : '',
		'$end' : '<=',
	},
	I['C!=']: {
		'side' : COND,
		'cont' : STAT,
		'func' : VAL,
		'form' : DEC,
		'dcol' : 'vop',
		'dpth' : 0,
		'dfid' : None,
		'$beg' : '',
		'$mid' : '',
		'$end' : '!=',
	},
	I['D=?']: {
		'side' : DECL,
		'cont' : STAT,
		'func' : VAL,
		'form' : NON,
		'dcol' : 'wop',
		'dpth' : 0,
		'dfid' : None,
		'$beg' : '=',
		'$mid' : '',
		'$end' : '',
	},
	I['D=I']: {
		'side' : DECL,
		'cont' : STAT,
		'func' : VAL,
		'form' : INT,
		'dcol' : 'wop',
		'dpth' : 0,
		'dfid' : TRUE,
		'$beg' : '=',
		'$mid' : '',
		'$end' : '',
	},
	I['D=S']: {
		'side' : DECL,
		'cont' : STAT,
		'func' : VAL,
		'form' : STR,
		'dcol' : 'str',
		'dpth' : 0,
		'dfid' : None,
		'$beg' : '="',
		'$mid' : '',
		'$end' : '"',
	},
	I['D=D']: {
		'side' : DECL,
		'cont' : STAT,
		'func' : VAL,
		'form' : DEC,
		'dcol' : 'wop',
		'dpth' : 0,
		'dfid' : None,
		'$beg' : '=',
		'$mid' : '',
		'$end' : '',
	},
	I['D>']: {
		'side' : DECL,
		'cont' : STAT,
		'func' : VAL,
		'form' : DEC,
		'dcol' : 'wop',
		'dpth' : 0,
		'dfid' : None,
		'$beg' : '>',
		'$mid' : '',
		'$end' : '',
	},
	I['D<']: {
		'side' : DECL,
		'cont' : STAT,
		'func' : VAL,
		'form' : DEC,
		'dcol' : 'wop',
		'dpth' : 0,
		'dfid' : None,
		'$beg' : '<',
		'$mid' : '',
		'$end' : '',
	},
	I['D>=']: {
		'side' : DECL,
		'cont' : STAT,
		'func' : VAL,
		'form' : DEC,
		'dcol' : 'wop',
		'dpth' : 0,
		'dfid' : None,
		'$beg' : '>=',
		'$mid' : '',
		'$end' : '',
	},
	I['D<=']: {
		'side' : DECL,
		'cont' : STAT,
		'func' : VAL,
		'form' : DEC,
		'dcol' : 'wop',
		'dpth' : 0,
		'dfid' : None,
		'$beg' : '<=',
		'$mid' : '',
		'$end' : '',
	},
	I['D!=']: {
		'side' : DECL,
		'cont' : STAT,
		'func' : VAL,
		'form' : DEC,
		'dcol' : 'wop',
		'dpth' : 0,
		'dfid' : None,
		'$beg' : '!=',
		'$mid' : '',
		'$end' : '',
	},
	I['A']: {
		'side' : COND,
		'cont' : STAT,
		'func' : NOD,
		'form' : AID,
		'dcol' : 'aid',
		'dpth' : 0,
		'dfid' : None,
		'$beg' : '',
		'$mid' : '',
		'$end' : '',
	},
	I['C2']: {
		'side' : COND,
		'cont' : STAT,
		'func' : REL,
		'form' : AID,
		'dcol' : 'cid',
		'dpth' : 2,
		'dfid' : None,
		'$beg' : '[',
		'$mid' : '',
		'$end' : '',
	},
	I['C']: {
		'side' : COND,
		'cont' : STAT,
		'func' : REL,
		'form' : AID,
		'dcol' : 'cid',
		'dpth' : 1,
		'dfid' : I['is'],
		'$beg' : '[',
		'$mid' : '',
		'$end' : '',
	},
	I['B']: {
		'side' : DECL,
		'cont' : STAT,
		'func' : NOD,
		'form' : AID,
		'dcol' : 'bid',
		'dpth' : 0,
		'dfid' : None,
		'$beg' : ']',
		'$mid' : '',
		'$end' : '',
	},
	I['D2']: {
		'side' : DECL,
		'cont' : STAT,
		'func' : REL,
		'form' : AID,
		'dcol' : 'did',
		'dpth' : 2,
		'dfid' : None,
		'$beg' : ']',
		'$mid' : '',
		'$end' : '',
	},
	I['D']: {
		'side' : DECL,
		'cont' : STAT,
		'func' : REL,
		'form' : AID,
		'dcol' : 'did',
		'dpth' : 1,
		'dfid' : None,
		'$beg' : ']',
		'$mid' : '',
		'$end' : '',
	},
	I['C|']: {
		'side' : COND,
		'cont' : STAT,
		'func' : OR,
		'form' : INT,
		'dcol' : None,
		'dpth' : 0,
		'dfid' : None,
		'$beg' : '',
		'$mid' : '',
		'$end' : '',
	},
	I['D|']: {
		'side' : DECL,
		'cont' : STAT,
		'func' : OR,
		'form' : INT,
		'dcol' : None,
		'dpth' : 0,
		'dfid' : None,
		'$beg' : '',
		'$mid' : '',
		'$end' : '',
	},

	I['C&']: {
		'side' : COND,
		'cont' : META,
		'func' : AND,
		'form' : NON,
		'dcol' : None,
		'dpth' : 0,
		'dfid' : None,
		'$beg' : '',
		'$mid' : ' ',
		'$end' : '',
	},
	I['D&']: {
		'side' : DECL,
		'cont' : META,
		'func' : AND,
		'form' : NON,
		'dcol' : None,
		'dpth' : 0,
		'dfid' : None,
		'$beg' : '',
		'$mid' : ' ',
		'$end' : '',
	},

	I['END']: {
		'side' : COND,
		'cont' : META,
		'func' : END,
		'form' : NON,
		'dcol' : None,
		'dpth' : 0,
		'dfid' : None,
		'$beg' : '',
		'$mid' : ';',
		'$end' : '',
	},
	# Actually starts operators, treat as close of non-existant prior statement
	I['opr']: {
		'side' : COND,
		'cont' : META,
		'func' : END,
		'form' : NON,
		'dcol' : None,
		'dpth' : 0,
		'dfid' : I['mix'],
		'$beg' : '',
		'$mid' : '',
		'$end' : '',
	},
}

# Characters in operators
OPR_CHR = {
	"[": 1,
	"]": 1,
	' ': 1,
	";": 1,
	"=": 2,
	"!": 2,
	">": 2,
	"<": 2,
}

# How to proccess an operator character on left/right side
OPSIDE = {
	# Left side conditions
	COND: {
		'a'  : I['A'],
		'=D' : I['C=D'],
		'=I' : I['C=I'],
		'=S' : I['C=S'],
		'='  : I['C=?'],
		'>'  : I['C>'],
		'<'  : I['C<'],
		'>=' : I['C>='],
		'<=' : I['C<='],
		'!=' : I['C!='],
		'=>' : I['C>='], # backwards
		'=<' : I['C<='], # backwards
		'=!' : I['C!='], # backwards
		'['  : I['C'],
		']'  : I['D'],
		'|'  : I['C|'],
		' '  : I['C&'],
		';'  : I['END'],
	},
	# Right side declarations
	DECL: {
		'=D' : I['D=D'],
		'=I' : I['D=I'],
		'=S' : I['D=S'],
		'='  : I['D=?'],
		'>'  : I['D>'],
		'<'  : I['D<'],
		'>=' : I['D>='],
		'<=' : I['D<='],
		'!=' : I['D!='],
		']'  : I['D'],
		'|'  : I['D|'],
		' '  : I['D&'],
		';'  : I['END'],
	},
}


SEQ = {
	# When delacing, replace [O1, O2] with [O3, O4]
	'delace': {
		# We assumed the first item on Left was A, but its actually a Decimal
		(I['A'], I['C=?'])  : (I['C=D'], None),
		(I['A'], I['C>'])   : (I['C>'], None),
		(I['A'], I['C<'])   : (I['C<'], None),
		(I['A'], I['C>='])  : (I['C>='], None),
		(I['A'], I['C<='])  : (I['C<='], None),
		(I['A'], I['C!='])  : (I['C!='], None),

		# Left value-equals
		(I['C=I'], I['C=?']) : (I['C=I'], None),
		(I['C=S'], I['C=?']) : (I['C=S'], None),
		(I['C=D'], I['C=?']) : (I['C=D'], None),
		(I['C=D'], I['C>'])  : (I['C>'], None),
		(I['C=D'], I['C<'])  : (I['C<'], None),
		(I['C=D'], I['C>=']) : (I['C>='], None),
		(I['C=D'], I['C<=']) : (I['C<='], None),
		(I['C=D'], I['C!=']) : (I['C!='], None),
		(I['C=I'], I['C>'])  : (I['C>'], None),
		(I['C=I'], I['C<'])  : (I['C<'], None),
		(I['C=I'], I['C>=']) : (I['C>='], None),
		(I['C=I'], I['C<=']) : (I['C<='], None),

		# Right equals-value
		(I['D=?'], I['D=I']) : (None, I['D=I']),
		(I['D=?'], I['D=S']) : (None, I['D=S']),
		(I['D=?'], I['D=D']) : (None, I['D=D']),
		(I['D>'], I['D=D'])  : (None, I['D>']),
		(I['D<'], I['D=D'])  : (None, I['D<']),
		(I['D>='], I['D=D']) : (None, I['D>=']),
		(I['D<='], I['D=D']) : (None, I['D<=']),
		(I['D!='], I['D=D']) : (None, I['D!=']),
		(I['D>'], I['D=I'])  : (None, I['D>']),
		(I['D<'], I['D=I'])  : (None, I['D<']),
		(I['D>='], I['D=I']) : (None, I['D>=']),
		(I['D<='], I['D=I']) : (None, I['D<=']),

		# Chained declarations
		(I['C'], I['C'])     : (I['C2'], I['C']),
		(I['D'], I['D'])     : (I['D'], I['D2']),

		# Last ]D is actually ]B
		(I['D'], I['D=?'])   : (I['B'], I['D=?']),
		(I['D'], I['D=I'])   : (I['B'], I['D=I']),
		(I['D'], I['D=S'])   : (I['B'], I['D=S']),
		(I['D'], I['D=D'])   : (I['B'], I['D=D']),
		(I['D'], I['D>'])    : (I['B'], I['D>']),
		(I['D'], I['D<'])    : (I['B'], I['D<']),
		(I['D'], I['D>='])   : (I['B'], I['D>=']),
		(I['D'], I['D<='])   : (I['B'], I['D<=']),
		(I['D'], I['D!='])   : (I['B'], I['D!=']),
		(I['D'], I['D&'])   : (I['B'], I['D&']),
		(I['D'], I['END'])   : (I['B'], I['END']),
		(I['D2'], I['D=?'])  : (I['B'], I['D=?']),
		(I['D2'], I['D>'])   : (I['B'], I['D>']),
		(I['D2'], I['D<'])   : (I['B'], I['D<']),
		(I['D2'], I['D>='])  : (I['B'], I['D>=']),
		(I['D2'], I['D<='])  : (I['B'], I['D<=']),
		(I['D2'], I['D!='])  : (I['B'], I['D!=']),
		(I['D2'], I['D&'])  : (I['B'], I['D&']),
		(I['D2'], I['END'])  : (I['B'], I['END']),
	},

	# Expand A]D]B into V=A[C]D]B=W
	'expand': {
		(I['A'], I['D'])  : (I['A'], I['C'], I['D']),
		(I['A'], I['C'], I['B'])  : (I['A'], I['C'], I['D'], I['B']),
		(I['opr'], I['A'])  : (I['opr'], I['C=I'], I['A']),
		(I['END'], I['A'])  : (I['END'], I['C=I'], I['A']),
		(I['C&'], I['A'])  : (I['C&'], I['C=I'], I['A']),
		(I['B'], I['END'])  : (I['B'], I['D=I'], I['END']),
		(I['B'], I['D&'])  : (I['B'], I['D=I'], I['D&']),

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
def delace(mqry: str):

	# Replace multiple spaces with a single space
	mqry = ' '.join(str(mqry).strip().split())

	# Remove comments
	mqry = re.sub(r'\s*//.*$', '', mqry, flags=re.MULTILINE)

	# Remove spaces around operators
	mqry = re.sub(r'\s*([!<>=]+)\s*', r'\1', mqry)

	# Prepend zero before decimals, such as =.5 to =0.5
	mqry = re.sub(r'([<>=])(\-?)\.([0-9])', lambda m: f"{m.group(1)}{m.group(2)}0.{m.group(3)}", mqry)

	if len(mqry) == 0: raise Exception("Error: Empty query provided.")

	mqry_chars = list(mqry)
	mqry_len = len(mqry_chars)

	side = COND
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

			# Collect valid operator characters
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
			
			# Check statement operators are in allowable sequence
			if OPR[operator]['cont']==STAT and OPR[operators[-1]]['cont']==STAT:
				if OPR[operator]['func']*side<OPR[operators[-1]]['func']*side:
					raise Exception(f"Memelang parse error: Left operator order for {opstr} after {K[operators[-1]]} at char {i} in {mqry}")

			side=OPR[operator]['side']
			operators.append(operator)
			operands.append(OPR[operator]['dfid'])

			i += j

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

			operators.append(OPSIDE[side]['=S'])
			operands.append(operand)

		# key/int/float
		else:
			while i < mqry_len and re.match(r'[a-z0-9_\.\-]', mqry_chars[i]):
				operand += mqry_chars[i]
				i += 1

			if not len(operand): raise Exception(f"Memelang parse error: Unexpected '{c}' at char {i} in {mqry}")
			elif operand.isdigit(): operand=int(operand)

			# = True/false/get
			if operand in (0,1,'t','f','g'):
				if operand=='f': operand=0
				elif operand=='t': operand=1
				elif operand=='g': operand=2
				else: operand=int(operand)
				operators.append(OPSIDE[side]['=I'])
				operands.append(operand)

			# =tn for or-group
			elif isinstance(operand, str) and (tm := re.match(r't([0-9])$', operand)):
				operators.append(OPSIDE[side]['|'])
				operands.append(int(tm.group(1)))

			# C/C2/D/D2 fill operand
			elif OPR[operators[-1]]['func']==REL: operands[-1]=operand

			# Start of statement, assume A, might switch to Decimal later
			elif OPR[operators[-1]]['cont']==META:
				operators.append(OPSIDE[side]['a'])
				operands.append(operand)

			# Decimal
			elif (isinstance(operand, str) and '.' in operand) or isinstance(operand, int):
				operators.append(OPSIDE[side]['=D'])
				operands.append(float(operand))

			else: raise Exception(f"Memelang parse error: Unexpected '{operand}' at char {i} in {mqry}")

	sequence(operators, operands, 'delace')

	return operators, operands


# Input: operators, operands
# Output: Memelang string operator1operand1operator2operand2
def interlace(operators: list, operands: list, interlace_set=None) -> str:

	if not interlace_set: interlace_set={}
	mqry = ''

	for i,operator in enumerate(operators):
		if i==0: continue
		
		operand = str(operands[i])

		# Decimal number must have a decimal
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
			if operator == I['END'] and interlace_set.get('newline'): operand+="\n"

		# Append the interlaced expression
		if interlace_set.get('html'):
			mqry += '<var class="v' + str(operator) + '">' + html.escape(OPR[operator]['$beg'] + operand + OPR[operator]['$end']) + '</var>'
		else:
			mqry += OPR[operator]['$beg'] + operand + OPR[operator]['$end']

	if interlace_set.get('html'):
		mqry = '<code class="meme">' + mqry + '</code>'

	return mqry


# Input operators, operands
# Modifies the sequence according to rules in SEQ
def sequence (operators: list, operands: list, mode: str = 'delace'):

	if not operators: return

	if operators[-1]!=I['END']:
		operators.append(I['END'])
		operands.append(OPR[I['END']]['dfid'])

	olen=len(operators)
	o=0
	while o<olen:
		for slen in range(2,4):
			if o+slen>olen: break
			if not SEQ[mode].get(tuple(operators[o:o+slen])): continue
			suboperators=SEQ[mode][tuple(operators[o:o+slen])]

			# Insert operator at o+1, insert operator's dfid value as operand
			if len(suboperators)>slen:
				operators.insert(o+1, suboperators[1])
				operands.insert(o+1, OPR[suboperators[1]]['dfid'])
				olen+=1

			for so, suboperator in enumerate(suboperators):
				# Change operator
				if suboperator: operators[o+so]=suboperator

				# Remove operator
				else:
					operators.pop(o+so)
					operands.pop(o+so)
					olen-=1
					o-=1
		o+=1



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

	queries = []
	params = []

	suboperators = []
	suboperands = []
	for o, operator in enumerate(operators):
		if o==0: continue
		suboperators.append(operator)
		suboperands.append(operands[o])
		
		if OPR[operator]['func'] == END:
			if suboperators:
				sql, param = subquerify(suboperators, suboperands, meme_table)
				queries.append(sql)
				params.extend(param)

			suboperators = []
			suboperands = []


	return [' UNION '.join(queries), params]


# Input: operators and operands for one Memelang command
# Output: One SQL query string
def subquerify(operators: list, operands: list, meme_table=None):
	if not meme_table: meme_table=DB_TABLE_MEME
	qry_set = {'all': False, 'of': False}
	true_groups = {}
	or_groups = {}
	false_group = []
	get_group = []
	true_cnt = 0
	or_cnt = 0
	false_cnt = 0

	skip = False
	suboperators = []
	suboperands = []
	for o, operator in enumerate(operators):
		
		if operator==I['A'] and operands[o]==I['qry']:
			qry_set[operands[o+1]]=True
			skip=True
		
		elif OPR[operator]['cont'] != META:
			suboperators.append(operator)
			suboperands.append(operands[o])
		
		elif skip or not suboperators:
			skip = False
			suboperators = []
			suboperands = []
		
		else:
			last_operator = suboperators[-1]
			last_operand = suboperands[-1]

			# Handle =f (false)
			if last_operator == I['D=I'] and last_operand == I['f']:
				false_cnt += 1
				false_group.append([suboperators, suboperands])
			
			# Handle =g (get)
			elif last_operator == I['D=I'] and last_operand == I['g']:
				get_group.append([suboperators, suboperands])
				continue

			# Handle =tn (OR groups)
			elif last_operator == I['D|']:
				or_cnt += 1
				if not or_groups.get(last_operand): or_groups[last_operand]=[]
				or_groups[last_operand].append([suboperators, suboperands])
			
			# Default: Add to true conditions
			else:
				if OPR[last_operator]['func'] == VAL: tg=interlace(suboperators[:-1], suboperands[:-1])
				else: tg=interlace(suboperators, suboperands)

				if not true_groups.get(tg): true_groups[tg]=[]
				true_groups[tg].append([suboperators, suboperands])
				true_cnt += 1

			suboperators = []
			suboperands = []

	# If qry_set['all'] and no true/false/or conditions
	if qry_set.get(I['all']) and true_cnt == 0 and false_cnt == 0 and or_cnt == 0:
		return [f"SELECT * FROM {meme_table}", []]

	params   = []
	cte_sqls = []
	cte_outs = []
	sql_outs = []
	cte_cnt  = -1

	# Process AND conditions (true_groups)
	for true_group in true_groups.values():
		wheres = []
		cte_cnt += 1
		# Each bid_group is a list of 
		for suboperators, suboperands in true_group:
			select_sql, from_sql, where_sql, qry_params, qry_depth = selectify(suboperators, suboperands, meme_table)
			if not wheres:
				wheres.append(where_sql)
				params.extend(qry_params)
			else:
				wheres.append(where_sql[0:where_sql.find('wal')-4])
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
		for suboperators, suboperands in or_group:
			select_sql, from_sql, where_sql, qry_params, qry_depth = selectify(suboperators, suboperands, meme_table)
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

	for zmNum in cte_outs:
		zNum, mNum = zmNum

		cWhere=[];
		if zNum < cte_cnt:
			cWhere.append(f"a0 IN (SELECT a0 FROM z{cte_cnt})")

		m=0;
		while mNum>=m:
			sql_outs.append(f"SELECT DISTINCT v{m}, a{m}, c{m}, r{m}, b{m}, w{m}, vo{m}, wo{m} FROM z{zNum}" + ('' if len(cWhere)==0 else ' WHERE '+' AND '.join(cWhere) ))
			m+=1

	# Apply logic to As
	if qry_set.get(I['of']):
		sql_outs.append(f"SELECT m0.val AS v0, m0.aid AS a0, '{I['of']}' AS c0, z.did AS r0, z.bid AS b0, z.wal AS w0, m0.vop AS o0, z.wop AS wo0 FROM {meme_table} m0 JOIN z{cte_cnt} AS z ON m0.aid = z.bid AND m0.cid = z.did WHERE m0.cid={I['is']}")

	return ['WITH ' + ', '.join(cte_sqls) + ' ' + ' UNION '.join(sql_outs), params]


# Input: operators and operands for one Memelang statement
# Output: SELECT string, FROM string, WHERE string, and depth int
def selectify(operators: list, operands: list, meme_table=None, aidOnly=False):
	if not meme_table: meme_table=DB_TABLE_MEME

	params = []
	wheres = []
	joins = [f"FROM {meme_table} m0"]
	selects = ['m0.val AS v0','m0.vop AS vo0','m0.aid AS a0','m0.cid AS c0','m0.did AS r0','m0.bid AS b0','m0.wop AS wo0','m0.wal AS w0']
	m = 0
	opr=None
	val=None
	last_rel_end=None

	for i, operator in enumerate(operators):
		operand = operands[i]
		side = OPR[operator]['side']
		func = OPR[operator]['func']
		form = OPR[operator]['form']
		dcol = OPR[operator]['dcol']

		# REL
		# TO DO: Work on switching V-O and E-Q
		if func == REL:
			if OPR[operator]['dpth'] == 1:
				if side==DECL and operand is not None and operand<0:
					selects = ['m0.val AS v0','m0.bid AS a0','m0.cid AS c0','m0.did*-1 AS r0','m0.aid AS b0','m0.wal AS w0','m0.vop AS vo0','m0.wop AS wo0']
			
			elif side==COND: raise Exception('What does it mean to look up a C chain?')

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

			if form in (INT, AID): operand=int(operand)
			elif form == DEC:      operand=float(operand)
			else:                  raise Exception('invalid form')

			eql  = '=' if func != VAL else OPR[operator]['$mid']

			# Special case =t to !=f
			if form==INT and eql=='=' and operand==TRUE:
				eql='!='
				operand=FALSE

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
# Return results (optionally replacing aids with keys with statement "qry.nam:key=1")
def get(mqry, meme_table=None, name_table=None):
	if not meme_table: meme_table=DB_TABLE_MEME
	if not name_table: name_table=DB_TABLE_NAME
	output=[[I['opr']], [I['id']]]
	mqry, namekeys = dename(mqry)
	sql, params = querify(mqry, meme_table)	
	memes = select(sql, params)

	for meme in memes:
		output[0].extend([int(meme[VO])] + ACDB + [int(meme[WO]), I['END']])
		output[1].extend([float(meme[V]), int(meme[A]), int(meme[C]), int(meme[D]), int(meme[B]), float(meme[W]), None])

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


	# Pull out ID-KEYs
	suboperators=[] 
	suboperands=[]
	for o, operator in enumerate(operators):
		if o==0: continue
		elif OPR[operator]['cont'] != META:
			if OPR[operator]['form']==AID:
				# Swap in ID or mark missing
				if isinstance(operands[o], int): pass
				elif I.get(operands[o]): operands[o]=I[operands[o]]
				else: missings[operands[o]]=1

			suboperators.append(operator)
			suboperands.append(operands[o])
		else:
			if suboperators==VACDBS and suboperands[D]==NAM and suboperands[B]==KEY:
				key = suboperands[W]
				aid = int(suboperands[A])
				missings.pop(key, None)
				sqls[name_table].append("(%s,%s,%s)")
				params[name_table].extend([aid, KEY, key])
				I[key]=aid
				K[aid]=key
			suboperators=[] 
			suboperands=[]

	# Missing keys with no associated ID
	if missings:
		aid = maxnum('aid', name_table) or I['cor']
		for key, val in missings.items():
			aid += 1
			sqls[name_table].append("(%s,%s,%s)")
			params[name_table].extend([aid, KEY, key])
			I[key]=aid
			K[aid]=key


	# Pull out names and trues
	suboperators=[] 
	suboperands=[]
	for o, operator in enumerate(operators):
		if o==0: continue

		elif OPR[operator]['cont'] != META:
			# Swap in IDs
			if OPR[operator]['form']==AID and isinstance(operands[o], str): operands[o]=I[operands[o]]
			suboperators.append(operator)
			suboperands.append(operands[o])
		
		else:
			# Val=A[C]D]B=String
			if suboperators[W]==I['D=S']:
				if suboperands[B]==KEY: continue # Keys are already done
				params[name_table].extend([suboperands[A], suboperands[B], suboperands[W]])
				sqls[name_table].append('(%s,%s,%s)')

			# V=A[C]D]B=W
			else:
				params[meme_table].extend(suboperands + [suboperators[V], suboperators[W]])
				sqls[meme_table].append('(%s,%s,%s,%s,%s,%s,%s,%s)')

			suboperators=[] 
			suboperands=[]

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
# FIX THIS
def logify (operators: list, operands: list):
	ACs = {}

	# Pull out A[C]D]B logic rules
	suboperators=[] 
	suboperands=[]
	for o, operator in enumerate(operators):
		if o==0: continue
		elif OPR[operator]['cont'] != META:
			suboperators.append(operator)
			suboperands.append(operands[o])
		else:
			if suboperators[V:B+1] == VACDB and suboperands[C]!=I['is']:
				if not ACs.get(suboperands[A]): ACs[suboperands[A]]={}
				if not ACs[suboperands[A]].get(suboperands[C]): ACs[suboperands[A]][suboperands[C]]=[]
				ACs[suboperands[A]][suboperands[C]].append([suboperators, suboperands])
			suboperators=[] 
			suboperands=[]

	# Apply A[C]D]B=t rules to C for X]C]A => X]D]B=t
	o=0
	olen=len(operators)-1
	suboperators=[]
	suboperands=[]
	while o<olen:
		o+=1
		if OPR[operators[o]]['cont'] != META:
			suboperators.append(operators[o])
			suboperands.append(operands[o])
		else:
			if suboperators[V:B+1] == VACDB and suboperands[C]==I['is'] and ACs.get(suboperands[B]) and ACs[suboperands[B]].get(suboperands[D]):
				for logioperators, logioperands in ACs[suboperands[B]][suboperands[D]]:
					operators.extend(VACDB + [logioperators[W], I['END']])
					operands.extend([TRUE, suboperands[A], I['of'], logioperands[D], logioperands[B], logioperands[W], I['END']])
					olen+=1
			suboperators=[] 
			suboperands=[]	


#### MEME FILE ####

def read (file_path):
	output = [[I['opr']],[I['mix']]]
	with open(file_path, 'r', encoding='utf-8') as f:
		for ln, line in enumerate(f, start=1):

			if line.strip() == '' or line.strip().startswith('//'): continue

			operators, operands = delace(line)

			if len(operators)<2: continue
			
			output[0].extend(operators[1:])
			output[1].extend(operands[1:])

	return output[0], output[1]


def write (file_path, operators: list, operands: list):
	with open(file_path, 'w', encoding='utf-8') as file:
		file.write(interlace(operators, operands, {'newline':True}))
