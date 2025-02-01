# memesql3

These Python scripts receive [Memelang](https://memelang.net/) queries, convert them to SQL, then execute them on a Postgres database. 
* Demo: https://demo.memelang.net/
* Contact: info@memelang.net
* License: Copyright HOLTWORK LLC. Patent pending.


## Files

* *conf.py* database configurations
* *db.py* library for executing Postgres queries
* *main.py* CLI interface for queries and testing
* *memelang.py* library to parse Memelang queries
* *presidents.meme* example terms and relations for the U.S. presidents


## Installation

Installation on Ubuntu:

	# Install packages
	sudo apt install -y git postgresql python3 python3-psycopg2
	systemctl start postgresql
	systemctl enable postgresql
	
	# Download files
	git clone https://github.com/memelang-net/memesql2.git memesql
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
