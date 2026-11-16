"""KASSA.UZ: local development MVP. Not a certified fiscal POS or production SaaS."""
import os, sqlite3, secrets, hashlib, hmac, time, csv, io
from contextlib import contextmanager
from pathlib import Path
from datetime import datetime, timezone
from typing import Literal
from fastapi import FastAPI, HTTPException, Header, Depends
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

BASE = Path(__file__).resolve().parent
DB = os.getenv('KASSA_DB', str(BASE / 'kassa.sqlite3'))
app = FastAPI(title='KASSA.UZ Local MVP', version='0.1.0')
app.mount('/static', StaticFiles(directory=str(BASE / 'static')), name='static')

def now(): return datetime.now(timezone.utc).isoformat()
def pw_hash(value, salt=None):
    salt = salt or secrets.token_hex(16)
    return salt + ':' + hashlib.scrypt(value.encode(),salt=bytes.fromhex(salt),n=16384,r=8,p=1).hex()
def verify(password, encoded):
    try: return hmac.compare_digest(pw_hash(password, encoded.split(':')[0]), encoded)
    except Exception: return False

@contextmanager
def conn(write=False):
    c = sqlite3.connect(DB, timeout=20, isolation_level=None)
    c.row_factory = sqlite3.Row
    c.execute('PRAGMA foreign_keys=ON'); c.execute('PRAGMA busy_timeout=20000')
    try:
        if write: c.execute('BEGIN IMMEDIATE')
        yield c
        if write: c.commit()
    except:
        if write: c.rollback()
        raise
    finally: c.close()

def init_db():
    Path(DB).parent.mkdir(parents=True, exist_ok=True)
    with conn() as c:
        c.executescript('''
        PRAGMA journal_mode=WAL;
        CREATE TABLE IF NOT EXISTS companies(id INTEGER PRIMARY KEY, name TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS branches(id INTEGER PRIMARY KEY, company_id INTEGER NOT NULL REFERENCES companies(id), name TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY, company_id INTEGER NOT NULL REFERENCES companies(id), username TEXT NOT NULL UNIQUE, hash TEXT NOT NULL, role TEXT NOT NULL CHECK(role IN ('owner','cashier','manager')), active INTEGER NOT NULL DEFAULT 1);
        CREATE TABLE IF NOT EXISTS user_branches(user_id INTEGER REFERENCES users(id), branch_id INTEGER REFERENCES branches(id), PRIMARY KEY(user_id,branch_id));
        CREATE TABLE IF NOT EXISTS tokens(token_hash TEXT PRIMARY KEY,user_id INTEGER NOT NULL REFERENCES users(id), expires_at INTEGER NOT NULL);
        CREATE TABLE IF NOT EXISTS products(id INTEGER PRIMARY KEY,company_id INTEGER NOT NULL REFERENCES companies(id),name TEXT NOT NULL,sku TEXT NOT NULL,barcode TEXT NOT NULL,price INTEGER NOT NULL CHECK(price>=0),cost INTEGER NOT NULL CHECK(cost>=0),active INTEGER NOT NULL DEFAULT 1, UNIQUE(company_id,sku),UNIQUE(company_id,barcode));
        CREATE INDEX IF NOT EXISTS idx_products_barcode ON products(company_id,barcode);
        CREATE TABLE IF NOT EXISTS stock(branch_id INTEGER NOT NULL REFERENCES branches(id),product_id INTEGER NOT NULL REFERENCES products(id),quantity INTEGER NOT NULL CHECK(quantity>=0),PRIMARY KEY(branch_id,product_id));
        CREATE TABLE IF NOT EXISTS stock_movements(id INTEGER PRIMARY KEY,company_id INTEGER NOT NULL,branch_id INTEGER NOT NULL,product_id INTEGER NOT NULL,delta INTEGER NOT NULL,kind TEXT NOT NULL,ref_id INTEGER NOT NULL,actor_id INTEGER NOT NULL,created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS purchases(id INTEGER PRIMARY KEY,company_id INTEGER NOT NULL,branch_id INTEGER NOT NULL,supplier TEXT NOT NULL,actor_id INTEGER NOT NULL,created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS purchase_items(purchase_id INTEGER NOT NULL,product_id INTEGER NOT NULL,quantity INTEGER NOT NULL,cost INTEGER NOT NULL);
        CREATE TABLE IF NOT EXISTS cash_sessions(id INTEGER PRIMARY KEY,company_id INTEGER NOT NULL,branch_id INTEGER NOT NULL,actor_id INTEGER NOT NULL,opening_cash INTEGER NOT NULL,closing_cash INTEGER,expected_cash INTEGER,opened_at TEXT NOT NULL,closed_at TEXT);
        CREATE UNIQUE INDEX IF NOT EXISTS one_open_session_per_branch ON cash_sessions(branch_id) WHERE closed_at IS NULL;
        CREATE TABLE IF NOT EXISTS sales(id INTEGER PRIMARY KEY,company_id INTEGER NOT NULL,branch_id INTEGER NOT NULL,actor_id INTEGER NOT NULL,session_id INTEGER NOT NULL,subtotal INTEGER NOT NULL,cash_paid INTEGER NOT NULL,card_paid INTEGER NOT NULL,change_given INTEGER NOT NULL,created_at TEXT NOT NULL,request_key TEXT NOT NULL,UNIQUE(company_id,request_key));
        CREATE TABLE IF NOT EXISTS sale_items(sale_id INTEGER NOT NULL,product_id INTEGER NOT NULL,quantity INTEGER NOT NULL,unit_price INTEGER NOT NULL,unit_cost INTEGER NOT NULL,line_total INTEGER NOT NULL);
        CREATE TABLE IF NOT EXISTS audit_logs(id INTEGER PRIMARY KEY,company_id INTEGER NOT NULL,branch_id INTEGER,actor_id INTEGER NOT NULL,action TEXT NOT NULL,detail TEXT NOT NULL,created_at TEXT NOT NULL);
        ''')

def asdict(row): return dict(row) if row else None

def audit(c,u, action,detail,branch_id=None):
    c.execute('INSERT INTO audit_logs(company_id,branch_id,actor_id,action,detail,created_at) VALUES(?,?,?,?,?,?)',(u['company_id'],branch_id,u['id'],action,detail,now()))

@app.on_event('startup')
def startup(): init_db()

@app.get('/')
def root(): return FileResponse(BASE/'static'/'index.html')

class Login(BaseModel): username:str; password:str
@app.post('/api/login')
def login(data:Login):
    with conn(write=True) as c:
        u=c.execute('SELECT * FROM users WHERE username=? AND active=1',(data.username,)).fetchone()
        if not u or not verify(data.password,u['hash']): raise HTTPException(401,'Login yoki parol xato')
        token=secrets.token_urlsafe(32)
        c.execute('INSERT INTO tokens VALUES(?,?,?)',(hashlib.sha256(token.encode()).hexdigest(),u['id'],int(time.time())+12*3600))
        return {'token':token,'role':u['role'],'username':u['username']}

def current(authorization:str=Header(default='')):
    if not authorization.startswith('Bearer '): raise HTTPException(401,'Tizimga kiring')
    th=hashlib.sha256(authorization[7:].encode()).hexdigest()
    with conn() as c:
        u=c.execute('SELECT users.* FROM users JOIN tokens ON tokens.user_id=users.id WHERE tokens.token_hash=? AND tokens.expires_at>? AND users.active=1',(th,int(time.time()))).fetchone()
        if not u: raise HTTPException(401,'Sessiya tugagan')
        return dict(u)

@app.post('/api/logout')
def logout(authorization:str=Header(default=''), u=Depends(current)):
    with conn(write=True) as c: c.execute('DELETE FROM tokens WHERE token_hash=?',(hashlib.sha256(authorization[7:].encode()).hexdigest(),))
    return {'ok':True}

def branch_access(c,u,branch_id):
    found=c.execute('SELECT 1 FROM branches WHERE id=? AND company_id=?',(branch_id,u['company_id'])).fetchone()
    if not found: raise HTTPException(404,'Filial topilmadi')
    if u['role']!='owner' and not c.execute('SELECT 1 FROM user_branches WHERE user_id=? AND branch_id=?',(u['id'],branch_id)).fetchone():
        raise HTTPException(403,'Filialga kirish taqiqlangan')

def manager(u):
    if u['role'] not in ('owner','manager'): raise HTTPException(403,'Bu amal uchun ruxsat yo‘q')

@app.get('/api/me')
def me(u=Depends(current)):
    with conn() as c:
        branches=c.execute('SELECT b.id,b.name FROM branches b WHERE b.company_id=? AND (?="owner" OR EXISTS(SELECT 1 FROM user_branches ub WHERE ub.branch_id=b.id AND ub.user_id=?)) ORDER BY b.id',(u['company_id'],u['role'],u['id'])).fetchall()
        return {'username':u['username'],'role':u['role'],'company_id':u['company_id'],'branches':[dict(b) for b in branches]}

class ProductIn(BaseModel): name:str=Field(min_length=1,max_length=150); sku:str=Field(min_length=1,max_length=64); barcode:str=Field(min_length=3,max_length=64); price:int=Field(ge=0); cost:int=Field(ge=0)
@app.post('/api/products')
def add_product(data:ProductIn,u=Depends(current)):
    manager(u)
    with conn(write=True) as c:
        try:
            cur=c.execute('INSERT INTO products(company_id,name,sku,barcode,price,cost) VALUES(?,?,?,?,?,?)',(u['company_id'],data.name.strip(),data.sku.strip(),data.barcode.strip(),data.price,data.cost))
        except sqlite3.IntegrityError: raise HTTPException(409,'SKU yoki barcode takrorlangan')
        audit(c,u,'product_created',str(cur.lastrowid)); return {'id':cur.lastrowid}

@app.get('/api/products')
def products(branch_id:int,q:str='',u=Depends(current)):
    with conn() as c:
        branch_access(c,u,branch_id)
        rows=c.execute('''SELECT p.id,p.name,p.sku,p.barcode,p.price,p.cost,p.active,COALESCE(s.quantity,0) quantity FROM products p LEFT JOIN stock s ON s.product_id=p.id AND s.branch_id=? WHERE p.company_id=? AND p.active=1 AND (p.name LIKE ? OR p.sku LIKE ? OR p.barcode LIKE ?) ORDER BY p.id DESC LIMIT 250''',(branch_id,u['company_id'],f'%{q}%',f'%{q}%',f'%{q}%')).fetchall()
        return [{k:v for k,v in dict(r).items() if k!='cost' or u['role']!='cashier'} for r in rows]

class ReceiptItem(BaseModel): product_id:int; quantity:int=Field(gt=0); cost:int=Field(ge=0)
class Receipt(BaseModel): branch_id:int; supplier:str=Field(min_length=1); items:list[ReceiptItem]=Field(min_length=1)
@app.post('/api/receipts')
def receipt(data:Receipt,u=Depends(current)):
    manager(u)
    with conn(write=True) as c:
        branch_access(c,u,data.branch_id)
        cur=c.execute('INSERT INTO purchases(company_id,branch_id,supplier,actor_id,created_at) VALUES(?,?,?,?,?)',(u['company_id'],data.branch_id,data.supplier,u['id'],now()))
        rid=cur.lastrowid
        for item in data.items:
            p=c.execute('SELECT id FROM products WHERE id=? AND company_id=? AND active=1',(item.product_id,u['company_id'])).fetchone()
            if not p: raise HTTPException(400,'Mahsulot topilmadi')
            c.execute('INSERT INTO purchase_items VALUES(?,?,?,?)',(rid,item.product_id,item.quantity,item.cost))
            c.execute('INSERT INTO stock(branch_id,product_id,quantity) VALUES(?,?,?) ON CONFLICT(branch_id,product_id) DO UPDATE SET quantity=quantity+excluded.quantity',(data.branch_id,item.product_id,item.quantity))
            c.execute('INSERT INTO stock_movements(company_id,branch_id,product_id,delta,kind,ref_id,actor_id,created_at) VALUES(?,?,?,?,?,?,?,?)',(u['company_id'],data.branch_id,item.product_id,item.quantity,'receipt',rid,u['id'],now()))
        audit(c,u,'receipt_confirmed',str(rid),data.branch_id)
        return {'id':rid,'ok':True}

class OpenShift(BaseModel): branch_id:int; opening_cash:int=Field(ge=0)
@app.post('/api/shifts/open')
def open_shift(data:OpenShift,u=Depends(current)):
    with conn(write=True) as c:
        branch_access(c,u,data.branch_id)
        try: cur=c.execute('INSERT INTO cash_sessions(company_id,branch_id,actor_id,opening_cash,opened_at) VALUES(?,?,?,?,?)',(u['company_id'],data.branch_id,u['id'],data.opening_cash,now()))
        except sqlite3.IntegrityError: raise HTTPException(409,'Bu filialda ochiq smena mavjud')
        audit(c,u,'shift_opened',str(cur.lastrowid),data.branch_id);return {'id':cur.lastrowid}

@app.get('/api/shifts/current')
def shift_current(branch_id:int,u=Depends(current)):
    with conn() as c:
        branch_access(c,u,branch_id)
        return asdict(c.execute('SELECT * FROM cash_sessions WHERE company_id=? AND branch_id=? AND closed_at IS NULL',(u['company_id'],branch_id)).fetchone())

class CloseShift(BaseModel): branch_id:int; closing_cash:int=Field(ge=0)
@app.post('/api/shifts/close')
def close_shift(data:CloseShift,u=Depends(current)):
    with conn(write=True) as c:
        branch_access(c,u,data.branch_id)
        s=c.execute('SELECT * FROM cash_sessions WHERE branch_id=? AND company_id=? AND closed_at IS NULL',(data.branch_id,u['company_id'])).fetchone()
        if not s: raise HTTPException(409,'Ochiq smena topilmadi')
        if s['actor_id']!=u['id'] and u['role'] not in ('owner','manager'): raise HTTPException(403,'Boshqa kassir smenasi')
        paid=c.execute('SELECT COALESCE(SUM(cash_paid-change_given),0) total FROM sales WHERE session_id=?',(s['id'],)).fetchone()['total']
        expected=s['opening_cash']+paid
        c.execute('UPDATE cash_sessions SET closing_cash=?,expected_cash=?,closed_at=? WHERE id=?',(data.closing_cash,expected,now(),s['id']))
        audit(c,u,'shift_closed',str(s['id']),data.branch_id)
        return {'id':s['id'],'expected_cash':expected,'actual_cash':data.closing_cash,'difference':data.closing_cash-expected}

class SaleItem(BaseModel): product_id:int; quantity:int=Field(gt=0)
class Sale(BaseModel): branch_id:int; items:list[SaleItem]=Field(min_length=1); cash_paid:int=Field(ge=0); card_paid:int=Field(ge=0); request_key:str=Field(min_length=8,max_length=100)
@app.post('/api/sales')
def sale(data:Sale,u=Depends(current)):
    with conn(write=True) as c:
        branch_access(c,u,data.branch_id)
        old=c.execute('SELECT id,subtotal,cash_paid,card_paid,change_given FROM sales WHERE company_id=? AND request_key=?',(u['company_id'],data.request_key)).fetchone()
        if old: return {**dict(old),'duplicate':True}
        s=c.execute('SELECT * FROM cash_sessions WHERE company_id=? AND branch_id=? AND closed_at IS NULL',(u['company_id'],data.branch_id)).fetchone()
        if not s: raise HTTPException(409,'Avval kassa smenasini oching')
        if s['actor_id']!=u['id'] and u['role'] not in ('owner','manager'): raise HTTPException(403,'Bu sizning smenangiz emas')
        combined={}
        for x in data.items: combined[x.product_id]=combined.get(x.product_id,0)+x.quantity
        items=[]; total=0
        for pid,qty in combined.items():
            p=c.execute('SELECT * FROM products WHERE id=? AND company_id=? AND active=1',(pid,u['company_id'])).fetchone()
            if not p: raise HTTPException(404,'Mahsulot topilmadi')
            stock=c.execute('SELECT quantity FROM stock WHERE product_id=? AND branch_id=?',(pid,data.branch_id)).fetchone()
            if not stock or stock['quantity']<qty: raise HTTPException(409,f'{p["name"]}: qoldiq yetarli emas')
            line=p['price']*qty; total+=line;items.append((pid,qty,p['price'],p['cost'],line))
        if data.cash_paid+data.card_paid<total: raise HTTPException(400,'To‘lov yetarli emas')
        change=data.cash_paid+data.card_paid-total
        if change>data.cash_paid: raise HTTPException(400,'Qaytim naqd to‘lovdan ko‘p')
        cur=c.execute('INSERT INTO sales(company_id,branch_id,actor_id,session_id,subtotal,cash_paid,card_paid,change_given,created_at,request_key) VALUES(?,?,?,?,?,?,?,?,?,?)',(u['company_id'],data.branch_id,u['id'],s['id'],total,data.cash_paid,data.card_paid,change,now(),data.request_key))
        sale_id=cur.lastrowid
        for pid,qty,price,cost,line in items:
            updated=c.execute('UPDATE stock SET quantity=quantity-? WHERE branch_id=? AND product_id=? AND quantity>=?',(qty,data.branch_id,pid,qty))
            if updated.rowcount!=1: raise HTTPException(409,'Qoldiq bir vaqtda o‘zgardi')
            c.execute('INSERT INTO sale_items VALUES(?,?,?,?,?,?)',(sale_id,pid,qty,price,cost,line))
            c.execute('INSERT INTO stock_movements(company_id,branch_id,product_id,delta,kind,ref_id,actor_id,created_at) VALUES(?,?,?,?,?,?,?,?)',(u['company_id'],data.branch_id,pid,-qty,'sale',sale_id,u['id'],now()))
        audit(c,u,'sale_confirmed',str(sale_id),data.branch_id)
        return {'id':sale_id,'subtotal':total,'cash_paid':data.cash_paid,'card_paid':data.card_paid,'change_given':change,'duplicate':False}

@app.get('/api/dashboard')
def dashboard(branch_id:int,u=Depends(current)):
    with conn() as c:
        branch_access(c,u,branch_id)
        today=now()[:10]
        sales=c.execute('SELECT COUNT(*) count,COALESCE(SUM(subtotal),0) revenue FROM sales WHERE company_id=? AND branch_id=? AND substr(created_at,1,10)=?',(u['company_id'],branch_id,today)).fetchone()
        stock=c.execute('SELECT COALESCE(SUM(s.quantity),0) units,COUNT(*) products FROM stock s JOIN products p ON p.id=s.product_id WHERE s.branch_id=? AND p.company_id=?',(branch_id,u['company_id'])).fetchone()
        return {'sales_count':sales['count'],'revenue':sales['revenue'],'stock_units':stock['units'],'stock_skus':stock['products']}

@app.get('/api/sales')
def sales(branch_id:int,u=Depends(current)):
    with conn() as c:
        branch_access(c,u,branch_id)
        return [dict(r) for r in c.execute('SELECT id,subtotal,cash_paid,card_paid,change_given,created_at FROM sales WHERE company_id=? AND branch_id=? ORDER BY id DESC LIMIT 100',(u['company_id'],branch_id)).fetchall()]

@app.get('/api/sales.csv')
def sales_csv(branch_id:int,u=Depends(current)):
    with conn() as c:
        branch_access(c,u,branch_id)
        rows=c.execute('SELECT id,subtotal,cash_paid,card_paid,change_given,created_at FROM sales WHERE company_id=? AND branch_id=? ORDER BY id DESC',(u['company_id'],branch_id)).fetchall()
        out=io.StringIO(); writer=csv.writer(out);writer.writerow(['ID','Summa','Naqd','Karta','Qaytim','Sana']);writer.writerows(tuple(r) for r in rows)
        return StreamingResponse(iter([out.getvalue()]),media_type='text/csv; charset=utf-8',headers={'Content-Disposition':'attachment;filename="sales.csv"'})

@app.get('/api/audit')
def audit_list(branch_id:int,u=Depends(current)):
    manager(u)
    with conn() as c:
        branch_access(c,u,branch_id)
        return [dict(r) for r in c.execute('SELECT action,detail,actor_id,created_at FROM audit_logs WHERE company_id=? AND (branch_id=? OR branch_id IS NULL) ORDER BY id DESC LIMIT 100',(u['company_id'],branch_id)).fetchall()]

def seed():
    init_db()
    password=os.getenv('KASSA_ADMIN_PASSWORD')
    if not password or len(password)<12: raise SystemExit('KASSA_ADMIN_PASSWORD kamida 12 belgidan iborat bo‘lishi kerak')
    with conn(write=True) as c:
        if c.execute('SELECT 1 FROM companies LIMIT 1').fetchone():
            print('Database allaqachon mavjud; seed o‘tkazildi');return
        cid=c.execute('INSERT INTO companies(name) VALUES(?)',('Demo kompaniya',)).lastrowid
        branch=c.execute('INSERT INTO branches(company_id,name) VALUES(?,?)',(cid,'Asosiy do‘kon')).lastrowid
        c.execute('INSERT INTO branches(company_id,name) VALUES(?,?)',(cid,'Ikkinchi filial'))
        u=c.execute('INSERT INTO users(company_id,username,hash,role) VALUES(?,?,?,?)',(cid,'owner',pw_hash(password),'owner')).lastrowid
        for name,sku,barcode,price,cost in [('Coca-Cola 1.5L','COLA15','4780000000001',12000,9000),('Non','NON01','4780000000002',5000,3500),('Shokolad','CHOC01','4780000000003',8000,6000)]:
            c.execute('INSERT INTO products(company_id,name,sku,barcode,price,cost) VALUES(?,?,?,?,?,?)',(cid,name,sku,barcode,price,cost))
        print(f'Created company={cid}, branch={branch}, username=owner')

if __name__=='__main__':
    import sys
    if len(sys.argv)>1 and sys.argv[1]=='seed': seed()
    else: print('Run: uvicorn app:app --reload')
