#!/usr/bin/python
import psycopg2
import sys
import argparse
import logging


# Get the Table column names and attributes
def get_table_col_names(con, schema_str, table_str):
	col_names = []
	try:
		cur = con.cursor()
		cur.execute(
			"SELECT column_name, ordinal_position, is_nullable, data_type, character_maximum_length, column_default "
			"FROM INFORMATION_SCHEMA.COLUMNS "
			"WHERE table_name = '" + table_str + "' AND table_schema = '" + schema_str + "' "
			"ORDER BY ordinal_position"
		)
		for desc in cur.fetchall():
			col_names.append(desc)
		cur.close()
	except psycopg2.Error as e:
		print e

	return col_names


# Generate a CSV of data to be then inserted in MySQL using LOAD INFILE
def exportCSV(con, table_str):
	try:
		cur = con.cursor()
		io = open("/tmp/pg2mysql_tabledata_%s.csv" % table_str, "w")
		cur.copy_to(io, table_str)
		io.close()
		cur.close()
	except psycopg2.Error as e:
		print e


# Get information about Table Constrains and Keys
def get_table_pkfk(con, table_str):
	col_names = []
	try:
		cur = con.cursor()
		cur.execute("SELECT conname, "
					"pg_catalog.pg_get_constraintdef(r.oid, true) as condef, "
					"r.contype "
					"FROM pg_catalog.pg_constraint r "
					"WHERE r.conrelid = '" + table_str + "'::regclass ORDER BY 1")
		for desc in cur.fetchall():
			col_names.append(desc)
		cur.close()
	except psycopg2.Error as e:
		print e

	return col_names


# Helper for varchar data type writing
def nomax(s):
	if s is None:
		return '255'
	return str(s)


def main():
	logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)

	parser = argparse.ArgumentParser(add_help=False)
	parser.add_argument("-?", "--help", action='store_true')
	parser.add_argument("-h", "--host", default='postgres', help="Specifies the host name of the machine on which the server is running. If the value begins with a slash, it is used as the directory for the Unix-domain socket.")
	parser.add_argument("-p", "--port", default='5432', help="Specifies the TCP port or the local Unix-domain socket file extension on which the server is listening for connections. Defaults to 5432.")
	parser.add_argument("-d", "--dbname", default='postgres', help="Specifies the name of the database to connect to.")
	parser.add_argument("-s", "--schema", default='public', help="Specifies the name of the schema to dump.")
	parser.add_argument("-U", "--user", default='postgres', help="Connect to the database as the user username instead of the default.")
	parser.add_argument("-W", "--password", default='', help="Connect to the database with specified password.")
	args = parser.parse_args()

	if args.help:
		parser.print_help()
		sys.exit(0)

	pg_schema = args.schema

	# Define our connection string
	conn_string = "host='%s' port='%s' dbname='%s' user='%s' password='%s'" % (args.host, args.port, args.dbname, args.user, args.password)
	# get a connection, if a connect cannot be made an exception will be raised here
	conn = psycopg2.connect(conn_string)
	conn.set_session(readonly=True)
	conn.set_client_encoding('UTF-8')

	create_table = ""
	pk_constraints = ""
	uk_constraints = ""
	fk_constraints = ""
	load_data = ""

	psql_types = {
		"smallint": "smallint",
		"integer": "int",
		"bigint": "bigint",
		"smallserial": "smallint auto_increment",
		"serial": "int auto_increment",
		"bigserial": "bigint auto_increment",
		"bytea": "BLOB",
		"date": "date",
		"text": "text",
		"boolean": "bool",
		"character varying": "varchar",
		"character": "char",
		"double precision": "double",
		"timestamp with time zone": "timestamp",
		"timestamp without time zone": "timestamp",
		"time with time zone": "time",
		"time without time zone": "time",
		"timestamp": "timestamp",
		"ARRAY": "text"
	}

	cursor = conn.cursor()
	cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = '%s' and table_type = 'BASE TABLE'" % pg_schema)
	for table in cursor.fetchall():
		tbl = pg_schema + '.' + table[0]
		exportCSV(conn, tbl)
		load_data += "LOAD DATA LOCAL INFILE '/tmp/pg2mysql_tabledata_%s.csv' INTO TABLE %s;\n" % (tbl, tbl)
		create_table += "CREATE TABLE " + table[0] + " (\n"
		logging.debug('Table: %s' % tbl)
		pk_created = False

		columns_list = get_table_col_names(conn, pg_schema, table[0])
		for idx, column in enumerate(columns_list):
			column_name = column[0]
			ordinal_position = column[1]
			is_nullable = column[2] == 'YES'
			data_type = column[3]
			character_maximum_length = column[4]
			column_default = column[5]

			if data_type == "character" and character_maximum_length > 255:
				data_type = "character varying"

			create_table += "   " + column_name
			if not column_default is None and not column_default.startswith('nextval(') and data_type == "text":
				create_table += " varchar(255)"
			else:
				create_table += " " + psql_types.get(data_type, "FIXME(%s)" % data_type)
			if data_type == "character varying" or data_type == "character":
				create_table += "(%s)" % nomax(character_maximum_length)

			if not column_default is None:
				if column_default.startswith('nextval('):
					create_table += " auto_increment primary key"
					pk_created = True
				elif column_default.startswith("('now'::text)::date"):
					pass
				else:
					def_idx = column_default.find("::")
					if def_idx == -1:
						def_idx = len(column_default)
					create_table += " DEFAULT " + column_default[:def_idx]
			if not is_nullable:
				create_table += " NOT NULL"

			logging.debug("%s.%s: %s - %s - %s - %s" % (tbl, column_name, character_maximum_length, column_default, data_type, is_nullable))

			if idx+1 != len(columns_list):
				create_table += ","
			create_table += "\n"
		create_table += ") ENGINE=innodb;\n\n"

		for column in get_table_pkfk(conn, tbl):
			constraint_name = column[0]
			# Delete unnecessary quotes and postgres schema name
			constraint_def = column[1].replace("\"", "").replace(pg_schema + ".", "")
			constraint_type = column[2]

			constraint = ""
			constraint += "ALTER TABLE " + table[0] + "\n"
			constraint += "ADD CONSTRAINT " + constraint_name + "\n"
			constraint += constraint_def + ";\n"

			if constraint_type == 'p':
				if not pk_created:
					pk_constraints += constraint + "\n"
			elif constraint_type == 'u':
				uk_constraints += constraint + "\n"
			else:
				fk_constraints += constraint + "\n"

	conn.close()

	print(create_table)
	print(pk_constraints)
	print(load_data)
	print(uk_constraints)
	print(fk_constraints)


if __name__ == "__main__":
	main()
