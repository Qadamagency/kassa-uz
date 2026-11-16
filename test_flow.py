import os, tempfile, sys
from pathlib import Path
from fastapi.testclient import TestClient
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import app as a

def test_main_flow():
    with tempfile.TemporaryDirectory() as tmp:
        a.DB = str(Path(tmp)/'test.sqlite3')
        os.environ['KASSA_ADMIN_PASSWORD']='VeryStrongPassword123!'
        a.seed()
        with TestClient(a.app) as client:
            auth=client.post('/api/login',json={'username':'owner','password':os.environ['KASSA_ADMIN_PASSWORD']})
            assert auth.status_code==200, auth.text
            headers={'Authorization':'Bearer '+auth.json()['token']}
            def post(route,body):return client.post('/api'+route,json=body,headers=headers)
            def get(route):return client.get('/api'+route,headers=headers)
            items=get('/products?branch_id=1').json();pid=items[0]['id']
            response=post('/receipts',{'branch_id':1,'supplier':'Supplier','items':[{'product_id':pid,'quantity':30,'cost':3000}]})
            assert response.status_code==200,response.text
            assert next(x for x in get('/products?branch_id=1').json() if x['id']==pid)['quantity']==30
            assert next(x for x in get('/products?branch_id=2').json() if x['id']==pid)['quantity']==0
            assert post('/shifts/open',{'branch_id':1,'opening_cash':50000}).status_code==200
            sale={'branch_id':1,'items':[{'product_id':pid,'quantity':20}],'cash_paid':1000000,'card_paid':0,'request_key':'test-unique-sale-0001'}
            r=post('/sales',sale)
            assert r.status_code==200,r.text
            assert r.json()['subtotal']>0
            assert post('/sales',sale).json()['duplicate'] is True
            assert next(x for x in get('/products?branch_id=1').json() if x['id']==pid)['quantity']==10
            fail=post('/sales',{**sale,'items':[{'product_id':pid,'quantity':11}],'request_key':'test-unique-sale-0002'})
            assert fail.status_code==409
            assert next(x for x in get('/products?branch_id=1').json() if x['id']==pid)['quantity']==10
            r=post('/shifts/close',{'branch_id':1,'closing_cash':50000})
            assert r.status_code==200,r.text
            assert r.json()['expected_cash']==50000+1000000-(1000000-sale_total(items,pid)*20)
            assert get('/dashboard?branch_id=1').json()['sales_count']==1
            assert post('/sales',{**sale,'request_key':'test-unique-sale-0003'}).status_code==409

def sale_total(items,pid):return next(x['price'] for x in items if x['id']==pid)
