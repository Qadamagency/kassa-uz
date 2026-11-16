"""KASSA.UZ Telegram read-only reporting bot for a single-company test deployment.
Run separately alongside the web server with the same SQLite database volume.
Not a multi-tenant production bot.
"""
import json
import os
import sqlite3
import time
from datetime import datetime, timezone
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from zoneinfo import ZoneInfo

DB = os.getenv('KASSA_DB', os.path.join(os.path.dirname(__file__), 'kassa.sqlite3'))
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')
ALLOWED = {int(x.strip()) for x in os.getenv('TELEGRAM_ALLOWED_IDS', '').split(',') if x.strip().isdigit()}
COMPANY = int(os.getenv('KASSA_BOT_COMPANY_ID', '1'))
TZ = ZoneInfo('Asia/Tashkent')

def money(n):
    return f'{int(n):,}'.replace(',', ' ') + ' so‘m'

def report(db=DB, company=COMPANY):
    """Read-only reporting. UTC timestamps filtered using actual Tashkent day boundaries."""
    local = datetime.now(TZ)
    start = local.replace(hour=0, minute=0, second=0, microsecond=0).astimezone(timezone.utc).isoformat()
    end = local.replace(hour=23, minute=59, second=59, microsecond=999999).astimezone(timezone.utc).isoformat()
    with sqlite3.connect(db) as c:
        row = c.execute('''SELECT COUNT(*), COALESCE(SUM(subtotal), 0), COALESCE(SUM(cash_paid-change_given),0), COALESCE(SUM(card_paid),0)
                           FROM sales WHERE company_id=? AND created_at>=? AND created_at<=?''', (company, start, end)).fetchone()
        branches = c.execute('''SELECT b.name, COUNT(s.id), COALESCE(SUM(s.subtotal),0)
                                FROM branches b LEFT JOIN sales s ON s.branch_id=b.id AND s.company_id=?
                                AND s.created_at>=? AND s.created_at<=?
                                WHERE b.company_id=? GROUP BY b.id ORDER BY b.id''',(company,start,end,company)).fetchall()
    lines=[f'📊 KASSA.UZ | {local:%d.%m.%Y}',f'Sotuvlar: {row[0]} ta',f'Jami: {money(row[1])}',f'Naqd (qaytimdan so‘ng): {money(row[2])}',f'Karta (qo‘lda qayd): {money(row[3])}','', '🏬 Filiallar:']
    lines.extend(f'• {name}: {cnt} ta, {money(amount)}' for name,cnt,amount in branches)
    return '\n'.join(lines)

def stock_report(db=DB, company=COMPANY):
    with sqlite3.connect(db) as c:
        rows=c.execute('''SELECT b.name,p.name,COALESCE(s.quantity,0) q FROM branches b
                          JOIN products p ON p.company_id=b.company_id AND p.active=1
                          LEFT JOIN stock s ON s.branch_id=b.id AND s.product_id=p.id
                          WHERE b.company_id=? AND COALESCE(s.quantity,0)<5
                          ORDER BY b.name,p.name LIMIT 35''',(company,)).fetchall()
    return '📦 Kam qolgan mahsulotlar (5 donadan kam):\n' + ('\n'.join(f'• {b}: {p} — {q} dona' for b,p,q in rows) if rows else 'Hozircha aniqlanmadi.')

def telegram(method, params):
    data=urlencode(params).encode()
    req=Request(f'https://api.telegram.org/bot{TOKEN}/{method}', data=data)
    with urlopen(req, timeout=45) as resp:
        obj=json.load(resp)
    if not obj.get('ok'): raise RuntimeError('Telegram API javobi xato')
    return obj.get('result')

def handle_message(message, db=DB):
    user_id=(message.get('from') or {}).get('id')
    chat=message.get('chat') or {}
    if user_id not in ALLOWED or chat.get('type')!='private':
        return None  # Quietly ignore unauthorized and group messages.
    command=(message.get('text') or '').split(maxsplit=1)[0].split('@')[0].lower()
    if command in ('/start','/help','/yordam'):
        return 'Assalomu alaykum! KASSA.UZ test bot.\n/hisobot — bugungi savdo\n/qoldiq — 5 donadan kam mahsulotlar\n/yordam — buyruqlar\n\nBot faqat ko‘rish uchun. Sotuvni web orqali amalga oshiring.'
    if command in ('/hisobot','/report'):
        return report(db, COMPANY)
    if command in ('/qoldiq','/stock'):
        return stock_report(db, COMPANY)
    return 'Buyruq topilmadi. /yordam ni yuboring.'

def main():
    if not TOKEN or not ALLOWED:
        raise SystemExit('TELEGRAM_BOT_TOKEN va TELEGRAM_ALLOWED_IDS majburiy.')
    offset=None
    while True:
        try:
            params={'timeout':25,'allowed_updates':json.dumps(['message'])}
            if offset is not None: params['offset']=offset
            updates=telegram('getUpdates',params)
            for upd in updates:
                offset=upd['update_id']+1
                msg=upd.get('message',{})
                response=handle_message(msg)
                if response:
                    telegram('sendMessage',{'chat_id':msg['chat']['id'],'text':response[:4000]})
        except (HTTPError,URLError,OSError,ValueError,RuntimeError) as exc:
            print(f'Bot connection/report error: {type(exc).__name__}',flush=True)
            time.sleep(5)

if __name__=='__main__': main()
