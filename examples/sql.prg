# Consumable SQLite results
CREATE TABLE customers (id AUTONUM, name VARCHAR(40), active LOGICAL DEFAULT ON);
USE customers AS cust;
APPEND name="Ana";
APPEND name="Bea";

N = SQL.SELECT count(*) FROM customers;
? N;

first = SQL.ROW SELECT id, name FROM customers WHERE id=1;
? first.name;

allrows = SQL """
SELECT id, name
FROM customers
ORDER BY id;
""";
BROW allrows;

selected = SQL
SELECT id, name
FROM customers
WHERE active=1
INTO CURSOR active_people
ENDSQL;

BROW active_people;
BROW selected;

Q = SQL.QUERY SELECT name FROM customers WHERE id=:id;
? Q.execute(id=2);
