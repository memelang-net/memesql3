
# Database configuration constants
DB_HOST = 'localhost'  # Host for MySQL/Postgres
DB_USER = 'memeuser'  # Username for MySQL/Postgres
DB_PASSWORD = 'memepswd'  # Password for MySQL/Postgres
DB_NAME = 'memedb'  # Database name for MySQL/Postgres
DB_TABLE_MEME = 'meme'  # Default table name for memes
DB_TABLE_NAME = 'name'  # Default table name for names
DB_TABLE_IMPL = 'impl'

# Global dictionary to cache key->id mappings
I = {
	'f'    : 0,
	't'    : 1,
	'unk'  : 2,

	'@'    : 3,

	'.'    : 4,
	"'"    : 5,
	'[aa]' : 4,
	'[ab]' : 5,
	'[ba]' : 6,
	'[bb]' : 7,

	':'    : 8,

	'='    : 9,
	'!='   : 10,
	'<'    : 11,
	'>='   : 12,
	'<='   : 13,
	'>'    : 14,

	'g'	   : 20,
	'or'   : 21,
	'#'    : 22,
	'$'    : 23,

	'=>'   : 25,
	'ar'   : 26,
	'br'   : 26,
	'q'    : 29,
	
	' '	   : 30,
	';'	   : 31,

	'qry'  : 88,

	'nam'  : 90,
	'opr'  : 97,
	'id'   : 98,
	'key'  : 99,
	'tit'  : 100,

	'all'  : 901,
	'mix'  : 903,

	'cor'  : 999999
}

# Global dictionary to cache id->key mappings
K = {
	0  : 'f',
	1  : 't',
	2  : 'unk',

	3  : '@',

	4  : '.',
	5  : "'",
	6 : '[ba]',
	7 : '[bb]',

	8  : ':',

	9  : '=',
	10 : '!=',
	11 : '<',
	12 : '>=',
	13 : '<=',
	14 : '>',

	20 : 'g',
	21 : 'or',
	22 : '#',
	23 : '$',

	25 : '=>',
	26 : 'ar',
	27 : 'br',
	29 : 'q',

	30 : ' ',
	31 : ';',
	
	88 : 'qry',

	90 : 'nam',
	97 : 'opr',
	98 : 'id',
	99 : 'key',
	100 : 'tit',

	901 : 'all',
	903 : 'mix',

	999999 : 'cor'
}

NAM = I['nam']
KEY = I['key']
OPER = I['opr']
MIX = I['mix']
ID = I['id']

NAME_OPS = [I['@'], I['.'], I[':'], I['$']]
TRUE_OPS = [I['@'], I['.'], I[':'], I['t']]
FLOT_OPS = [I['@'], I['.'], I[':'], I['#']]
IMPL_OPS = [I['.'], I[':'], I['=>'], I['.'], I[':'], I['=']]


INVERSE = '-1'
NOTFALSE = '!=0'
TRUQNT = 1

OPR = {
	None: {
		'long': None,
		'shrt': None,
		'grp': None,
	},
	I['t']: {
		'long' : '=t',
		'shrt' : '=t',
		'grp' : I['='],
		'frm' : 'aid',
	},
	I['f']: {
		'long' : '=f',
		'shrt' : '=f',
		'grp' : I['='],
		'frm' : 'aid',
	},
	I['g']: {
		'long' : '=g',
		'shrt' : '=g',
		'grp' : I['='],
		'frm' : 'aid',
	},
	I['@']: {
		'long' : '',
		'shrt' : '',
		'grp' : I['@'],
		'frm' : 'aid',
	},
	I["'"]: {
		'long' : '\'',
		'shrt' : '\'',
		'grp' : I['.'],
		'frm' : 'aid',
	},
	I['.']: {
		'long' : '.',
		'shrt' : '.',
		'grp' : I['.'],
		'frm' : 'aid',
	},
	I['[ba]'] : {
		'long' : '[ba]',
		'shrt' : '.',
		'grp' : I['[ba]'],
		'frm' : 'aid',
	},
	I['[bb]'] : {
		'long' : '[bb]',
		'shrt' : "'",
		'grp' : I['[ba]'],
		'frm' : 'aid',
	},
	I[':']: {
		'long' : ':',
		'shrt' : ':',
		'grp' : I[':'],
		'frm' : 'aid',
	},
	I['=']: {
		'long' : '=',
		'shrt' : '=',
		'grp' : I['='],
		'frm' : 'non',
	},
	I['!='] : {
		'long' : '!=',
		'shrt' : '!=',
		'grp' : I['='],
		'frm' : 'non',
	},
	I['>'] : {
		'long' : '>',
		'shrt' : '>',
		'grp' : I['='],
		'frm' : 'non',
	},
	I['>='] : {
		'long' : '>=',
		'shrt' : '>=',
		'grp' : I['='],
		'frm' : 'non',
	},
	I['<'] : {
		'long' : '<',
		'shrt' : '<',
		'grp' : I['='],
		'frm' : 'non',
	},
	I['<='] : {
		'long' : '<=',
		'shrt' : '<=',
		'grp' : I['='],
		'frm' : 'non',
	},
	I[' '] : {
		'long' : ' ',
		'shrt' : ' ',
		'grp' : I[' '],
		'frm' : 'end',
	},
	I[';'] : {
		'long' : ';',
		'shrt' : ';',
		'grp' : I[';'],
		'frm' : 'end',
	},
	I['#']: {
		'long' : '=',
		'shrt' : '=',
		'grp' : I['#'],
		'frm' : 'dec',
	},
	I['$']: {
		'long' : '="',
		'shrt' : '="',
		'grp' : I['$'],
		'frm' : 'str',
	},
	I['=>']: {
		'long' : '=>',
		'shrt' : '=>',
		'grp' : I['=>'],
		'frm' : 'non',
	},
	I['ar']: {
		'long' : '=ar',
		'shrt' : '=ar',
		'grp' : I['='],
		'frm' : 'aid',
	},
	I['br']: {
		'long' : '=br',
		'shrt' : '=br',
		'grp' : I['='],
		'frm' : 'aid',
	},
	I['q']: {
		'long' : '=q',
		'shrt' : '=q',
		'grp' : I['='],
		'frm' : 'aid',
	},
}

OPR_CHR = {
	".": 1,
	":": 1,
	"'": 1,
	"?": 1,
	"=": 2,
	"!": 2,
	"#": 2,
	">": 2,
	"<": 2,
	"[": 2,
}