import sqlite3
import json

conn = sqlite3.connect('order_db.sqlite')
cur = conn.cursor()

print('\n' + '='*100)
print('ORDER DATABASE - DAY 7 FOOD & GROCERY ORDERING'.center(100))
print('='*100)

# Tables
cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [r[0] for r in cur.fetchall()]
print('\n📋 TABLES:')
for t in tables:
    print(f'  ✓ {t}')

# Catalog Stats
cur.execute('SELECT COUNT(*) FROM catalog')
total_items = cur.fetchone()[0]
cur.execute('SELECT DISTINCT category FROM catalog')
categories = [r[0] for r in cur.fetchall()]

print(f'\n📦 CATALOG OVERVIEW:')
print(f'  Total Items: {total_items}')
print(f'  Categories: {", ".join(categories)}')

# Show all catalog items
print('\n' + '='*100)
print('FULL CATALOG:')
print('='*100)
cur.execute('SELECT id, name, category, price, brand, size, tags FROM catalog ORDER BY category, name')
rows = cur.fetchall()

current_category = None
for row in rows:
    item_id, name, category, price, brand, size, tags_json = row
    if category != current_category:
        current_category = category
        print(f'\n {category.upper()}:')
        print('-'*100)
    
    try:
        tags = json.loads(tags_json or '[]')
        tags_str = ', '.join(tags)
    except:
        tags_str = ''
    
    brand_str = f'({brand})' if brand else ''
    print(f'  {item_id:20} | {name:35} | ₹{price:7.2f} | {size:8} {brand_str:15} | Tags: {tags_str}')

# Orders
cur.execute('SELECT COUNT(*) FROM orders')
order_count = cur.fetchone()[0]
print(f'\nORDERS: {order_count} total')

if order_count > 0:
    print('\n' + '='*100)
    print('RECENT ORDERS:')
    print('='*100)
    cur.execute('SELECT order_id, customer_name, total, status, created_at FROM orders ORDER BY created_at DESC LIMIT 5')
    for o in cur.fetchall():
        print(f'  Order: {o[0]} | Customer: {o[1]} | Total: ₹{o[2]:.2f} | Status: {o[3]} | Created: {o[4]}')

print('\n' + '='*100)
conn.close()
