import sqlite3

conn = sqlite3.connect('fraud_db.sqlite')
cur = conn.cursor()
cur.execute('SELECT * FROM fraud_cases ORDER BY id')
rows = cur.fetchall()

print('\n📊 CURRENT DATABASE STATUS:')
print('='*100)
print()

for row in rows:
    status = row[8]
    name = row[1]
    updated = row[11]
    notes = row[9]
    
    print(f"👤 {name:<10} | Status: {status:<20} | Updated: {updated}")
    print(f"   Notes: {notes}")
    print()

print('='*100)
print(f"\n📊 SUMMARY:")
print(f"Total Cases: {len(rows)}")
print(f"✅ Confirmed Safe: {sum(1 for r in rows if r[8] == 'confirmed_safe')}")
print(f"❌ Confirmed Fraud: {sum(1 for r in rows if r[8] == 'confirmed_fraud')}")
print(f"⏳ Pending Review: {sum(1 for r in rows if r[8] == 'pending_review')}")
print(f"🚫 Verification Failed: {sum(1 for r in rows if r[8] == 'verification_failed')}")
print()

conn.close()
