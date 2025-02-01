
# Database configuration constants
DB_HOST = 'localhost'  # Host for MySQL/Poseqres
DB_USER = 'memeuser'  # Username for MySQL/Poseqres
DB_PASSWORD = 'memepswd'  # Password for MySQL/Poseqres
DB_NAME = 'memedb'  # Database name for MySQL/Poseqres
DB_ALRBEQ='alrbeq'
DB_ABS='abs'

# Global dictionary to cache key->id mappings
I = {

	'L1'  : 100,
	'L"'  : 101,
	'L.'  : 102,
	'L='  : 103,
	'L>'  : 104,
	'L<'  : 105,
	'L>=' : 106,
	'L<=' : 107,
	'L!=' : 108,
	'A'   : 109,
	'L'   : 110,
	'LL'  : 111,

	'R1'  : 113,
	'R"'  : 114,
	'R.'  : 115,
	'R='  : 116,
	'R>'  : 117,
	'R<'  : 118,
	'R>=' : 119,
	'R<=' : 120,
	'R!=' : 121,
	'B'   : 122,
	'R'   : 123,
	'RR'  : 124,

	'Or'  : 130,
	'And' : 131,
	'End' : 132,

	'qry' : 188,
	'nam' : 190,
	'opr' : 197,
	'id'  : 198,
	'key' : 199,
	'tit' : 1100,
	'is'  : 1800,
	'of'  : 1802,
	'unk' : 1900,
	'all' : 1901,
	'mix' : 1903,

	'cor'  : 999999
}

# Global dictionary to cache id->key mappings
K = {

	100 : 'L1',
	101 : 'L"',
	102 : 'L.',
	103 : 'L='  ,
	104 : 'L>'  ,
	105 : 'L<'  ,
	106 : 'L>=' ,
	107 : 'L<=' ,
	108 : 'L!=' ,
	109 : 'A'  ,
	110 : 'L'  ,
	111 : 'LL' ,

	113 : 'R1',
	114 : 'R"',
	115 : 'R.',
	116 : 'R='  ,
	117 : 'R>'  ,
	118 : 'R<'  ,
	119 : 'R>=' ,
	120 : 'R<=' ,
	121 : 'R!=' ,
	122 : 'B'  ,
	123 : 'R'  ,
	124 : 'RR' ,

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