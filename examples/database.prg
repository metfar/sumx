# sumX channels + SQLite/database demo
CREATE TABLE customers (
 id AUTONUM,
 name VARCHAR(80) NOT NULL,
 notes MEMO,
 balance CURRENCY,
 score FLOAT,
 active LOGICAL DEFAULT ON
);
CREATE TABLE sales (
 id AUTONUM,
 customer_id INTEGER REFERENCES customers(id),
 total CURRENCY
);

# Channel 1 is selected at startup.
USE customers AS cust;
APPEND name="Ana", notes="First record", balance=12.50, score=0.95, active=ON;
APPEND name="Luis", notes="Second record", balance=7.25, score=0.80, active=.T.;

CHANNEL 2;
USE sales AS sal;
APPEND customer_id=1, total=20.00;
APPEND customer_id=1, total=5.50;
APPEND customer_id=2, total=9.25;

# Persistent relationship metadata + an actual SQLite view.
LINK customers.id TO sales.customer_id AS customer_sales;
CREATE VIEW customer_totals AS SQL
SELECT customer_id, SUM(total) AS total
FROM sales
GROUP BY customer_id
ENDSQL;

CHANNEL cust;
BROW;
DISPLAY STRUCTURE;

# Real SQLite, consumed by sumX.
N = SQL.SELECT count(*) FROM customers;
? N;
rows = SQL.SELECT id, name FROM customers ORDER BY id INTO CURSOR people;
BROW people;

CHANNEL 3;
USE customer_totals AS totals;
BROW; # SQLite views are read-only in the editor
CHANNEL cust;
DISPLAY RELATIONS;
DISPLAY VIEWS;
