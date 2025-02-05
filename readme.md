# memesql3

These Python scripts receive [Memelang](https://memelang.net/) queries, convert them to SQL, then execute them on a Postgres database. Contact info@memelang.net. Copyright HOLTWORK LLC. Patent pending.

## Memelang

Memelang is a notation for logically encoding all human knowledge. Memelang traverses a knowledge graph using only three novel operators: Condition `[`, Inversion `-`, and Relation `]`; in addition to standard math operators: `=`, `!=`, `<=`, `>=`, `>`, and `<`. The basic syntax describes that some thing `A` has some relation `R` to some other thing `B`:

	A]R]B=V

For example, "Alice's uncle is Bob," where `A=Alice` and `R=uncle`, `B=Bob`, and `V=t` (true). Memelang encodes this relation thusly:

	Alice]uncle]Bob=t

Relations may also indicate a quantity. Whenever the value is a quantity, the `B` must be a unit of that quantity. For example, "Alice's height is 1.6 meters" is encoded:

	Alice]height]meter=1.6

Relations may be chained. For example, we know that an uncle is a parent's brother:

	Alice]parent]brother]Bob=t

Logically, for any true relation, there exists a true inverse relation as well. The inverse relation is indicated by a minus sign:

	A]R]B = B]-R]A

For the example above, Bob's "inverse uncle" is Alice. In English, inverse uncle could be "niece" or "nephew."

	Alice]uncle]Bob = Bob]-uncle]Alice

Inverse relation chains are inverted and reversed:

	Alice]parent]brother]Bob = Bob]-brother]-parent]Alice

The Condition `[` operator can be considered conditional as "if" or "when." The Relation `]` operator can be considered declarative as "then." For example, the relation chain of "if uncle, then parent's brother" is encoded: 

	[uncle]parent]brother]

Note starting a statement with `[` and no `A` indicates a wildcard A. The same goes for the ending `]` indicating a wildcard `B`.

The left side may also encode a quantitative value. For example, "if a person is at least 1 meter tall, then they may ride the rollercoaster" is encoded:

	1.0 >= meter[height]rideRollercoaster]allow = t

A condition may suggest a relation. For example, any kind of product should have a price in USD greater than or equal to one cent.

	product[kind]price]usd >= 0.01

The `meme` table stores memes in the form:

	A[C]R]B = V

To store an *un*conditional statement, the special `C=is` is used. This relation is reflexive such that:

	A[is]A=t
	A[-is]A=t
	A[is]R]B = A[-is]R]B = A]R]B

So `A=Alice` `C=is` `R=uncle` `B=Bob` `E="=t"` `V=1` (true) produces:

	Alice[is]uncle]Bob=t

## Files

* *conf.py* database configurations
* *core.meme* core memelang id-keys to be loaded into the DB
* *db.py* library for executing Postgres queries
* *main.py* CLI interface for queries and testing
* *memelang.py* library to parse Memelang queries
* *presidents.meme* example Memelang data for the U.S. presidents


## Installation

Installation on Ubuntu:

	# Install packages
	sudo apt install -y git postgresql python3 python3-psycopg2
	systemctl start postgresql
	systemctl enable postgresql
	
	# Download files
	git clone https://github.com/memelang-net/memesql3.git memesql
	cd memesql

	# Configure the db.py file according for your Postgres settings
	# Create postgres DB and user from the CLI
	sudo python3 ./main.py dbadd

	# Create meme and term tables in the DB
	sudo python3 ./main.py tableadd

	# Load core terms
	python3 ./main.py file ./core.meme

	# Load example presidents data (optional)
	python3 ./main.py file ./presidents.meme


## Example CLI Usage

Execute a query:

	# python3 ./main.py get "john_adams]spouse]"

Outputs:

	SQL: SELECT * FROM meme m0 WHERE m0.aid='john_adams' AND m0.rid='spouse' AND m0.qnt!=0
	
	+---------------------+---------------------+---------------------+------------+
	| A                   | R                   | B                   |          Q |
	+---------------------+---------------------+---------------------+------------+
	| john_adams          | spouse              | abigail_adams       |          1 |
	+---------------------+---------------------+---------------------+------------+
