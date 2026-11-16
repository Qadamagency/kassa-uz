import os, sys, sqlite3, tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import bot

def test_telegram_authorization_and_reports():
    with tempfile.TemporaryDirectory() as d:
        db=Path(d)/'test.sqlite3'
        c=sqlite3.connect(db)
        c.executescript('''CREATE TABLE sales(id INTEGER PRIMARY KEY,company_id INTEGER,branch_id INTEGER,subtotal INTEGER,cash_paid INTEGER,card_paid INTEGER,change_given INTEGER,created_at TEXT);
        CREATE TABLE branches(id INTEGER PRIMARY KEY, company_id INTEGER,name TEXT);
        CREATE TABLE products(id INTEGER PRIMARY KEY,company_id INTEGER,name TEXT,active INTEGER);
        CREATE TABLE stock(branch_id INTEGER,product_id INTEGER,quantity INTEGER);''')
        c.execute("INSERT INTO branches VALUES(1,1,'Demo filial')")
        c.execute("INSERT INTO products VALUES(1,1,'Non',1)")
        c.commit();c.close()
        bot.ALLOWED={111}
        assert bot.handle_message({'from':{'id':222},'chat':{'type':'private','id':222},'text':'/hisobot'},str(db)) is None
        assert bot.handle_message({'from':{'id':111},'chat':{'type':'group','id':-100},'text':'/hisobot'},str(db)) is None
        assert 'Sotuvlar: 0 ta' in bot.handle_message({'from':{'id':111},'chat':{'type':'private','id':111},'text':'/hisobot'},str(db))
        assert 'Non' in bot.stock_report(str(db))
