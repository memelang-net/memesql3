
# Database configuration constants
DB_HOST = 'localhost'  # Host for MySQL/Poseqres
DB_USER = 'memeuser'  # Username for MySQL/Poseqres
DB_PASSWORD = 'memepswd'  # Password for MySQL/Poseqres
DB_NAME = 'memedb'  # Database name for MySQL/Poseqres
DB_AIRBEQ='airbeq'
DB_ABS='abs'

# Global dictionary to cache key->id mappings
I = {
	'@'    : 1,
	'.'    : 2,
	"'"    : 3,
	'`'    : 3,
	'[.]'  : 4,
	"[']"  : 5,

	':'    : 9,

	'='    : 10,
	'!='   : 11,
	'<'    : 12,
	'>='   : 13,
	'<='   : 14,
	'>'    : 15,
	'#'    : 16,
	'$'    : 17,

	'|'    : 20,
	'&'	   : 21,
	';'	   : 22,

	'f'    : 80,
	't'    : 81,
	'g'	   : 82,
	'qry'  : 88,

	'nam'  : 90,
	'opr'  : 97,
	'id'   : 98,
	'key'  : 99,
	'tit'  : 100,

	'is'   : 800,
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

	4 : '[.]',
	5 : "[']",

	9 : ':',

	10 : '=',
	11 : '!=',
	12 : '<',
	13 : '>=',
	14 : '<=',
	15 : '>',
	16 : '#',
	17 : '$',

	20 : '|',
	21 : '&',
	22 : ';',
	
	80 : 'f',
	81 : 't',
	82 : 'g',
	88 : 'qry',

	90 : 'nam',
	97 : 'opr',
	98 : 'id',
	99 : 'key',
	100 : 'tit',

	800  : 'is',
	900  : 'unk',
	901 : 'all',
	903 : 'mix',

	999999 : 'cor'
}


AIRB = [I['@'], I["'"], I['[.]'], I[':']]

FALQNT=0
TRUQNT=1

NAM = I['nam']
KEY = I['key']
OPER = I['opr']
MIX = I['mix']
ID = I['id']

INVERSE = '-1'

SEQ_A = 1
SEQ_R = 2
SEQ_RR = 3
SEQ_B = 4
SEQ_EQL = 5
SEQ_OR = 6
SEQ_AND = 7
SEQ_END = 8

OPR = {
	None: {
		'long': None,
		'shrt': None,
	},
	I['@']: {
		'long' : '',
		'shrt' : '',
		'frm' : 'aid',
		'seq' : SEQ_A,
	},
	I['\'']: {
		'long' : "'",
		'shrt' : "'",
		'frm' : 'aid',
		'seq' : SEQ_R,
	},
	I['.']: {
		'long' : '.',
		'shrt' : '.',
		'frm' : 'aid',
		'seq' : SEQ_R,
	},
	I['[.]'] : {
		'long' : '[.]',
		'shrt' : '.',
		'frm' : 'aid',
		'seq' : SEQ_RR,
	},
	I["[']"] : {
		'long' : "[']",
		'shrt' : "'",
		'frm' : 'aid',
		'seq' : SEQ_RR,
	},
	I[':']: {
		'long' : ':',
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
		'frm' : 'flt',
		'seq' : SEQ_EQL,
	},
	I['>'] : {
		'long' : '>',
		'shrt' : '>',
		'frm' : 'flt',
		'seq' : SEQ_EQL,
	},
	I['>='] : {
		'long' : '>=',
		'shrt' : '>=',
		'frm' : 'flt',
		'seq' : SEQ_EQL,
	},
	I['<'] : {
		'long' : '<',
		'shrt' : '<',
		'frm' : 'flt',
		'seq' : SEQ_EQL,
	},
	I['<='] : {
		'long' : '<=',
		'shrt' : '<=',
		'frm' : 'flt',
		'seq' : SEQ_EQL,
	},
	I['#']: {
		'long' : '#',
		'shrt' : '#',
		'frm' : 'dec',
		'seq' : SEQ_EQL,
	},
	I['$']: {
		'long' : '"',
		'shrt' : '"',
		'frm' : 'str',
		'seq' : SEQ_EQL,
	},
	I['|'] : {
		'long' : '',
		'shrt' : '',
		'frm' : 'slf',
		'seq' : SEQ_OR,
	},
	I['&'] : {
		'long' : '&',
		'shrt' : '&',
		'frm' : 'slf',
		'seq' : SEQ_AND,
	},
	I[';'] : {
		'long' : ';',
		'shrt' : ';',
		'frm' : 'slf',
		'seq' : SEQ_END,
	},
}

OPR_CHR = {
	".": 1,
	":": 1,
	"'": 1,
	'`': 1,
	";": 1,
	"=": 2,
	"!": 2,
	">": 2,
	"<": 2,
	"[": 1,
}