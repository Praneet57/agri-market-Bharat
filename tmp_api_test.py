import urllib.request
import urllib.error
import json

base = 'http://localhost/api/v1'
headers = {'Content-Type': 'application/json'}

login = {'phone': '9000000002', 'password': 'buyer123'}
req = urllib.request.Request(base + '/auth/login', data=json.dumps(login).encode('utf-8'), headers=headers)
with urllib.request.urlopen(req) as resp:
    auth = json.loads(resp.read().decode())
    token = auth['access_token']
print('TOKEN', token[:20])

req = urllib.request.Request(base + '/products/?limit=1', headers={'Authorization': 'Bearer ' + token})
with urllib.request.urlopen(req) as resp:
    products = json.loads(resp.read().decode())
print('PRODUCTS', products)
if not products:
    raise SystemExit('no products')
prod = products[0]

order_payload = {
    'product_id': prod['id'],
    'farmer_id': prod['farmer_id'],
    'quantity_kg': prod['min_order_kg'],
    'price_per_kg': prod['price_per_kg'],
    'delivery_address': 'Test delivery'
}
req = urllib.request.Request(base + '/orders/', data=json.dumps(order_payload).encode('utf-8'), headers={**headers,'Authorization': 'Bearer ' + token})
with urllib.request.urlopen(req) as resp:
    order = json.loads(resp.read().decode())
print('ORDER', order)

req = urllib.request.Request(base + '/payments/create', data=json.dumps({'order_id': order['id']}).encode('utf-8'), headers={**headers,'Authorization': 'Bearer ' + token})
try:
    with urllib.request.urlopen(req) as resp:
        print('PAYMENT', resp.read().decode())
except urllib.error.HTTPError as e:
    print('PAYMENT_STATUS', e.code)
    print(e.read().decode())
