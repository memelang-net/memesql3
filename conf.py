
# Database configuration constants
DB_HOST = 'localhost'  # Host for MySQL/Poseqres
DB_USER = 'memeuser'  # Username for MySQL/Poseqres
DB_PASSWORD = 'memepswd'  # Password for MySQL/Poseqres
DB_NAME = 'memedb'  # Database name for MySQL/Poseqres
DB_TABLE_MEME='meme'
DB_TABLE_NAME='name'

# Global dictionary to cache key->id mappings
I = {

	'C=?'  : 10, # Left unkown value type
	'C=I'  : 11, # Left integer
	'C=S'  : 12, # Left string
	'C=D'  : 13, # Left decimal
	
	'C>'  : 21,
	'C<'  : 22,
	'C>=' : 23,
	'C<=' : 24,
	'C!=' : 25,
	'A'   : 30,
	'C2'  : 31,
	'C'   : 32,

	'D'   : 62,
	'D2'  : 61,
	'B'   : 60,

	'D>'  : 51,
	'D<'  : 52,
	'D>=' : 53,
	'D<=' : 54,
	'D!=' : 55,

	'D=?'  : 40,
	'D=I'  : 41,
	'D=S'  : 42,
	'D=D'  : 43,

	'C|'  : 70,
	'D|'  : 71,
	'C&'  : 72,
	'D&'  : 73,
	'END' : 79,

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

K = {value: key for key, value in I.items()}
