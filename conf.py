
# Database configuration constants
DB_HOST = 'localhost'  # Host for MySQL/Poseqres
DB_USER = 'memeuser'  # Username for MySQL/Poseqres
DB_PASSWORD = 'memepswd'  # Password for MySQL/Poseqres
DB_NAME = 'memedb'  # Database name for MySQL/Poseqres
DB_ALRBEQ='alrbeq'
DB_ABS='abs'

# Global dictionary to cache key->id mappings
I = {

	'L1'  : 10,
	'L"'  : 11,
	'L.'  : 12,
	'L='  : 20,
	'L>'  : 21,
	'L<'  : 22,
	'L>=' : 23,
	'L<=' : 24,
	'L!=' : 25,
	'A'   : 30,
	'LL'  : 31,
	'L'   : 32,

	'R1'  : 40,
	'R"'  : 41,
	'R.'  : 42,
	'R='  : 50,
	'R>'  : 51,
	'R<'  : 52,
	'R>=' : 53,
	'R<=' : 54,
	'R!=' : 55,
	'B'   : 60,
	'RR'  : 61,
	'R'   : 62,

	'Or'  : 70,
	'And' : 71,
	'End' : 79,

	'qry' : 200,
	'nam' : 201,
	'opr' : 202,
	'id'  : 203,
	'key' : 204,
	'tit' : 205,
	'is'  : 206,
	'of'  : 207,
	'unk' : 208,
	'all' : 209,
	'mix' : 210,

	'cor'  : 999999
}

# Global dictionary to cache id->key mappings
K = {

	10 : 'L1',
	11 : 'L"',
	12 : 'L.',
	20 : 'L=',
	21 : 'L>',
	22 : 'L<',
	23 : 'L>=',
	24 : 'L<=',
	25 : 'L!=',
	30 : 'A',
	31 : 'LL',
	32 : 'L',

	40 : 'R1',
	41 : 'R"',
	42 : 'R.',
	50 : 'R=',
	51 : 'R>',
	52 : 'R<',
	53 : 'R>=',
	54 : 'R<=',
	55 : 'R!=',
	60 : 'B',
	61 : 'RR',
	62 : 'R',

	70 : 'Or',
	71 : 'And',
	79 : 'End',

	200 : 'qry',
	201 : 'nam',
	202 : 'opr',
	203 : 'id',
	204 : 'key',
	205 : 'tit',
	206 : 'is',
	207 : 'of',
	208 : 'unk',
	209 : 'all',
	210 : 'mix',

	999999 : 'cor'
}