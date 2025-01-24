
# Database configuration constants
DB_HOST = 'localhost'  # Host for MySQL/Poseqres
DB_USER = 'memeuser'  # Username for MySQL/Poseqres
DB_PASSWORD = 'memepswd'  # Password for MySQL/Poseqres
DB_NAME = 'memedb'  # Database name for MySQL/Poseqres
DB_TABLE_MEME = 'meme'  # Default table name for memes
DB_TABLE_NAME = 'name'  # Default table name for names
DB_TABLE_LOGI = 'logi'

# Global dictionary to cache key->id mappings
I = {
	'@'    : 1,
	'[a]'  : 1,
	'.'    : 2,
	'[r]'  : 2,
	"'"    : 3,
	'`'    : 3,
	'[i]'  : 3,

	'[b=a]' : 4,
	'[b=b]' : 5,

	':'    : 9,
	'[b]'  : 9,

	'='    : 10,
	'!='   : 11,
	'<'    : 12,
	'>='   : 13,
	'<='   : 14,
	'>'    : 15,

	'f'    : 20,
	't'    : 21,
	'g'	   : 22,
	'#'    : 23,
	'$'    : 24,
	'or'   : 25,

	'=>'    : 28,
	'[q=q]': 28,
	'[a.r]'   : 30,
	'[a`r]'   : 32,
	
	' '	   : 40,
	';'	   : 41,

	'qry'  : 88,

	'nam'  : 90,
	'opr'  : 97,
	'id'   : 98,
	'key'  : 99,
	'tit'  : 100,

	'unk'  : 900,
	'all'  : 901,
	'mix'  : 903,

	'cor'  : 999999
}

# Global dictionary to cache id->key mappings
K = {
	1  : '@',

	2  : '.',
	3  : "'",

	4 : '[b=a]',
	5 : '[b=b]',

	0  : ':',

	10  : '=',
	11 : '!=',
	12 : '<',
	13 : '>=',
	14 : '<=',
	15 : '>',

	20  : 'f',
	21  : 't',
	22 : 'g',
	23 : 'or',
	24 : '#',
	25 : '$',

	28 : '[q=q]',
	30 : '[a.r]',
	32: '[a`r]',

	40 : ' ',
	41 : ';',
	
	88 : 'qry',

	90 : 'nam',
	97 : 'opr',
	98 : 'id',
	99 : 'key',
	100 : 'tit',

	900  : 'unk',
	901 : 'all',
	903 : 'mix',

	999999 : 'cor'
}

NAM = I['nam']
KEY = I['key']
OPER = I['opr']
MIX = I['mix']
ID = I['id']

NAME_OPS = [I['@'], I['.'], I[':'], I['='], I['$']]
TRUE_OPS = [I['@'], I['.'], I[':'], I['='], I['t']]
FLOT_OPS = [I['@'], I['.'], I[':'], I['='], I['#']]
IMPL_OPS = [I['.'], I[':'], I['=>'], I['.'], I[':']]
AREL_OPS = [I['.'], I[':'], I['[a.r]'], I['.']]
BREL_OPS = [I['.'], I[':'], I['[a`r]'], I['.']]


INVERSE = '-1'
NOTFALSE = '!=0'
TRUQNT = 1

SEQ_A = 1
SEQ_R = 2
SEQ_RR = 3
SEQ_B = 4
SEQ_EQL = 5
SEQ_VAL = 6
SEQ_QQ = 7
SEQ_AND = 8
SEQ_END = 9

OPR = {
	None: {
		'long': None,
		'shrt': None,
	},
	I['@']: {
		'long' : '[a]',
		'shrt' : '',
		'frm' : 'aid',
		'seq' : SEQ_A,
	},
	I['`']: {
		'long' : '[i]',
		'shrt' : '`',
		'frm' : 'aid',
		'seq' : SEQ_R,
	},
	I['.']: {
		'long' : '[r]',
		'shrt' : '.',
		'frm' : 'aid',
		'seq' : SEQ_R,
	},
	I['[b=a]'] : {
		'long' : '[b=a]',
		'shrt' : '.',
		'frm' : 'aid',
		'seq' : SEQ_RR,
	},
	I['[b=b]'] : {
		'long' : '[b=b]',
		'shrt' : "'",
		'frm' : 'aid',
		'seq' : SEQ_RR,
	},
	I[':']: {
		'long' : '[b]',
		'shrt' : ':',
		'frm' : 'aid',
		'seq' : SEQ_B,
	},
	I['=']: {
		'long' : '=',
		'shrt' : '=',
		'frm' : 'non',
		'seq' : SEQ_EQL,
	},
	I['!='] : {
		'long' : '!=',
		'shrt' : '!=',
		'frm' : 'non',
		'seq' : SEQ_EQL,
	},
	I['>'] : {
		'long' : '>',
		'shrt' : '>',
		'frm' : 'non',
		'seq' : SEQ_EQL,
	},
	I['>='] : {
		'long' : '>=',
		'shrt' : '>=',
		'frm' : 'non',
		'seq' : SEQ_EQL,
	},
	I['<'] : {
		'long' : '<',
		'shrt' : '<',
		'frm' : 'non',
		'seq' : SEQ_EQL,
	},
	I['<='] : {
		'long' : '<=',
		'shrt' : '<=',
		'frm' : 'non',
		'seq' : SEQ_EQL,
	},
	I['t']: {
		'long' : 't',
		'shrt' : 't',
		'frm' : 'aid',
		'seq' : SEQ_VAL,
	},
	I['f']: {
		'long' : 'f',
		'shrt' : 'f',
		'frm' : 'aid',
		'seq' : SEQ_VAL,
	},
	I['g']: {
		'long' : 'g',
		'shrt' : 'g',
		'frm' : 'aid',
		'seq' : SEQ_VAL,
	},
	I['#']: {
		'long' : '',
		'shrt' : '',
		'frm' : 'dec',
		'seq' : SEQ_VAL,
	},
	I['$']: {
		'long' : '"',
		'shrt' : '"',
		'frm' : 'str',
		'seq' : SEQ_VAL,
	},
	I['[a.r]']: {
		'long' : '[a.r]',
		'shrt' : '[a.r]',
		'frm' : 'non',
		'seq' : SEQ_QQ,
	},
	I['[a`r]']: {
		'long' : '[a`r]',
		'shrt' : '[a`r]',
		'frm' : 'non',
		'seq' : SEQ_QQ,
	},
	I['=>']: {
		'long' : '[q=q]',
		'shrt' : '=>',
		'frm' : 'non',
		'seq' : SEQ_QQ,
	},
	I[' '] : {
		'long' : ' ',
		'shrt' : ' ',
		'frm' : 'non',
		'seq' : SEQ_AND,
	},
	I[';'] : {
		'long' : ';',
		'shrt' : ';',
		'frm' : 'non',
		'seq' : SEQ_END,
	},
}

OPR_CHR = {
	".": 1,
	":": 1,
	"'": 1,
	'`': 1,
	"?": 1,
	"=": 2,
	"!": 2,
	"#": 2,
	">": 2,
	"<": 2,
	"[": 2,
}