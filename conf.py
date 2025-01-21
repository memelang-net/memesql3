
# Database configuration constants
DB_HOST = 'localhost'  # Host for MySQL/Postgres
DB_USER = 'memeuser'  # Username for MySQL/Postgres
DB_PASSWORD = 'memepswd'  # Password for MySQL/Postgres
DB_NAME = 'memedb'  # Database name for MySQL/Postgres
DB_TABLE_MEME = 'meme'  # Default table name for memes
DB_TABLE_NAME = 'name'  # Default table name for terms
DB_TABLE_LOGI = 'logi'

# Global dictionary to cache key->aid mappings
K2A = {
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

# Global dictionary to cache aid->key mappings
A2K = {
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


NAM = K2A['nam']
KEY = K2A['key']
OPER = K2A['opr']
MIX = K2A['mix']
ID = K2A['id']


NAME_OPS = [K2A['@'], K2A['.'], K2A[':'], K2A['='], K2A['$']]
MEME_OPS = [K2A['@'], K2A['.'], K2A[':'], K2A['='], K2A['t']]
MEME2_OPS = [K2A['@'], K2A['.'], K2A[':'], K2A['='], K2A['#']]
