# memesql3

These Python scripts receive [Memelang v3](https://memelang.net/03/) queries, convert them to SQL, then execute them on a Postgres database. Free public use under the [Memelicense](https://memelicense.net/).  Copyright 2025 HOLTWORK LLC. Patent pending. Contact info@memelang.net.


## Files

* *conf.py* database configurations
* *core.meme* core memelang id-keys to be loaded into the DB
* *main.py* CLI interface for queries and testing
* *memelang.py* library to parse Memelang queries and execute in Postgres
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

	# Create meme and name tables in the DB
	sudo python3 ./main.py tableadd

	# Load core names
	python3 ./main.py file ./core.meme

	# (Optional) load example presidents data
	python3 ./main.py file ./presidents.meme


## Example CLI Usage

Execute a query:

	# python3 ./main.py get "john_adams]spouse]"

Outputs:

	SQL: SELECT * FROM meme m0 WHERE m0.aid='john_adams' AND m0.did='spouse' AND m0.wal!=0
	
	+---------------------+---------------------+---------------------+------------+
	| A                   | R                   | B                   |          Q |
	+---------------------+---------------------+---------------------+------------+
	| john_adams          | spouse              | abigail_adams       |          1 |
	+---------------------+---------------------+---------------------+------------+
