
# Database configuration constants
DB_HOST = 'localhost'  # Host for MySQL/Poseqres
DB_USER = 'memeuser'  # Username for MySQL/Poseqres
DB_PASSWORD = 'memepswd'  # Password for MySQL/Poseqres
DB_NAME = 'memedb'  # Database name for MySQL/Poseqres
DB_ALRBEQ='alrbeq'
DB_ABS='abs'

# Global dictionary to cache key->id mappings
I = {

	'Lint' : 100,
	'Lstr' : 101,
	'Ldec' : 102,
	'L='   : 103,
	'L>'   : 104,
	'L<'   : 105,
	'L>='  : 106,
	'L<='  : 107,
	'L!='  : 108,
	'La'   : 109,
	'Lr'   : 110,
	'Lr2'  : 111,

	'Mid'    : 112,

	'Rint' : 113,
	'Rstr' : 114,
	'Rdec' : 115,
	'R='   : 116,
	'R>'   : 117,
	'R<'   : 118,
	'R>='  : 119,
	'R<='  : 120,
	'R!='  : 121,
	'Ra'   : 122,
	'Rr'   : 123,
	'Rr2'  : 124,

	'Or'   : 130,
	'And'  : 131,
	'End'  : 132,

	'qry'  : 188,
	'nam'  : 190,
	'opr'  : 197,
	'id'   : 198,
	'key'  : 199,
	'tit'  : 1100,
	'is'   : 1800,
	'of'  : 1802,
	'unk'  : 1900,
	'all'  : 1901,
	'mix'  : 1903,

	'cor'  : 999999
}

# Global dictionary to cache id->key mappings
K = {

	100 : 'Lint',
	101 : 'Lstr',
	102 : 'Ldec',
	103 : 'L='  ,
	104 : 'L>'  ,
	105 : 'L<'  ,
	106 : 'L>=' ,
	107 : 'L<=' ,
	108 : 'L!=' ,
	109 : 'La'  ,
	110 : 'Lr'  ,
	111 : 'Lr2' ,

	112 : 'Mid',

	113 : 'Rint',
	114 : 'Rstr',
	115 : 'Rdec',
	116 : 'R='  ,
	117 : 'R>'  ,
	118 : 'R<'  ,
	119 : 'R>=' ,
	120 : 'R<=' ,
	121 : 'R!=' ,
	122 : 'Ra'  ,
	123 : 'Rr'  ,
	124 : 'Rr2' ,

	130 : 'Or' ,
	131 : 'And',
	132 : 'End',


	188 : 'qry',
	190 : 'nam',
	197 : 'opr',
	198 : 'id',
	199 : 'key',
	1100 : 'tit',
	1800 : 'is',
	1802 : 'of',
	1900 : 'unk',
	1901 : 'all',
	1903 : 'mix',

	999999 : 'cor'
}

ALRB = [I['La'], I['Lr'], I['Mid'], I['Ra']]
ALRBES = ALRB + [I['R='], I['Rstr']]

NAM = I['nam']
KEY = I['key']
OPER = I['opr']
MIX = I['mix']
ID = I['id']

LEFT=0
RIGHT=1
AND=2
END=3

VAL=0
EQL=1
AB=2
REL=3

NON=0
NUM=1
DEC=2
AID=3
STR=4


OPR = {
	I['Lint']: {
		'side' : LEFT,
		'func' : VAL
		'form' : NUM,
		'dpth' : 0,
		'pre' : '',
		'str' : '',
		'post' : '',
	},
	I['Lstr']: {
		'side' : LEFT,
		'func' : VAL,
		'form' : STR,
		'dpth' : 0,
		'pre' : '"',
		'str' : '',
		'post' : '"',
	},
	I['Ldec']: {
		'side' : LEFT,
		'func' : VAL
		'form' : DEC,
		'dpth' : 0,
		'pre' : '',
		'str' : '',
		'post' : '',
	},
	I['Rint']: {
		'side' : RIGHT,
		'func' : VAL
		'form' : NUM,
		'dpth' : 0,
		'pre' : '',
		'str' : '',
		'post' : '',
	},
	I['Rstr']: {
		'side' : RIGHT,
		'func' : VAL
		'form' : STR,
		'dpth' : 0,
		'pre' : '',
		'str' : '',
		'post' : '',
	},
	I['Rdec']: {
		'side' : RIGHT,
		'func' : VAL
		'form' : DEC,
		'dpth' : 0,
		'pre' : '',
		'str' : '',
		'post' : '',
	},

	I['L=']: {
		'side' : LEFT,
		'func' : EQL
		'form' : NON,
		'dpth' : 0,
		'pre' : '=',
		'post' : '',
	},
	I['L>']: {
		'side' : LEFT,
		'func' : EQL
		'form' : NON,
		'dpth' : 0,
		'pre' : '',
		'str' : '>',
		'post' : '',
	},
	I['L<']: {
		'side' : LEFT,
		'func' : EQL
		'form' : NON,
		'dpth' : 0,
		'pre' : '',
		'str' : '<',
		'post' : '',
	},
	I['L>=']: {
		'side' : LEFT,
		'func' : EQL
		'form' : NON,
		'dpth' : 0,
		'pre' : '',
		'str' : '>=',
		'post' : '',
	},
	I['L<=']: {
		'side' : LEFT,
		'func' : EQL
		'form' : NON,
		'dpth' : 0,
		'pre' : '',
		'str' : '<=',
		'post' : '',
	},
	I['L!=']: {
		'side' : LEFT,
		'func' : EQL
		'form' : NON,
		'dpth' : 0,
		'pre' : '',
		'str' : '!=',
		'post' : '',
	},
	I['R=']: {
		'side' : RIGHT,
		'func' : EQL
		'form' : NON,
		'dpth' : 0,
		'pre' : '=',
		'post' : '',
	},
	I['R>']: {
		'side' : RIGHT,
		'func' : EQL
		'form' : NON,
		'dpth' : 0,
		'pre' : '',
		'str' : '>',
		'post' : '',
	},
	I['R<']: {
		'side' : RIGHT,
		'func' : EQL
		'form' : NON,
		'dpth' : 0,
		'pre' : '',
		'str' : '<',
		'post' : '',
	},
	I['R>=']: {
		'side' : RIGHT,
		'func' : EQL
		'form' : NON,
		'dpth' : 0,
		'pre' : '',
		'str' : '>=',
		'post' : '',
	},
	I['R<=']: {
		'side' : RIGHT,
		'func' : EQL
		'form' : NON,
		'dpth' : 0,
		'pre' : '',
		'str' : '<=',
		'post' : '',
	},
	I['R!=']: {
		'side' : RIGHT,
		'func' : EQL
		'form' : NON,
		'dpth' : 0,
		'pre' : '',
		'str' : '!=',
		'post' : '',
	},

	I['La']: {
		'side' : LEFT,
		'func' : AB
		'form' : AID,
		'dpth' : 0,
		'pre' : '[',
		'str' : '',
		'post' : '',
	},
	I['Lr2']: {
		'side' : LEFT,
		'func' : REL
		'form' : AID,
		'dpth' : 2,
		'pre' : '[',
		'str' : '',
		'post' : '',
	},
	I['Lr']: {
		'side' : LEFT,
		'func' : REL
		'form' : AID,
		'dpth' : 1,
		'pre' : '[',
		'str' : '',
		'post' : '',
	},
	I['Ra']: {
		'side' : RIGHT,
		'func' : AB
		'form' : AID,
		'dpth' : 0,
		'pre' : ']',
		'str' : '',
		'post' : '',
	},
	I['Rr2']: {
		'side' : RIGHT,
		'func' : REL
		'form' : AID,
		'dpth' : 2,
		'pre' : ']',
		'str' : '',
		'post' : '',
	},
	I['Rr']: {
		'side' : RIGHT,
		'func' : REL
		'form' : AID,
		'dpth' : 1,
		'pre' : ']',
		'str' : '',
		'post' : '',
	},
	I['Mid']: {
		'side' : RIGHT,
		'func' : REL
		'form' : AID,
		'dpth' : 1,
		'pre' : '|',
		'str' : '',
		'post' : '',
	},

	I['And']: {
		'side' : END,
		'func' : AND
		'form' : NON,
		'dpth' : 1,
		'pre' : '',
		'str' : ' ',
		'post' : '',
	},
	I['End']: {
		'side' : END,
		'func' : END
		'form' : NON,
		'dpth' : 1,
		'pre' : '',
		'str' : ';',
		'post' : '',
	},



}

OPR_CHR = {
	";": 1,
	"=": 1,
	"|": 1,
	"!": 2,
	">": 2,
	"<": 2,
	"[": 2,
	"]": 2,
	' ': 2
}

OPSIDE = [
	LEFT: {
		'a' : I['La'],
		'.' : I['Ldec'],
		'1' : I['Lint'],
		'"' : I['Lstr'],
		'=' : I['L='],
		'>' : I['L>'],
		'<' : I['L<'],
		'>=' : I['L>='],
		'<=' : I['L<='],
		'!=' : I['L!='],
		'[' : I['Lr'],
		'|' : I['Mid'],
		']' : I['Mid'],
		' ' : I['And'],
		';' : I['End'],
	}
	RIGHT: {
		'.' : I['Rdec'],
		'1' : I['Rint'],
		'"' : I['Rstr'],
		'=' : I['R='],
		'>' : I['R>'],
		'<' : I['R<'],
		'>=' : I['R>='],
		'<=' : I['R<='],
		'!=' : I['R!='],
		']' : I['Rr'],
		' ' : I['And'],
		';' : I['End'],
	}
]