import json

B = '{{base_url}}'


def test(*lines):
    return {'listen': 'test', 'script': {'type': 'text/javascript', 'exec': list(lines)}}


def pre(*lines):
    return {'listen': 'prerequest', 'script': {'type': 'text/javascript', 'exec': list(lines)}}


def req(name, method, path, body=None, token=None, events=()):
    headers = [{'key': 'Content-Type', 'value': 'application/json'}]
    if token:
        headers.append({'key': 'Authorization', 'value': 'Bearer {{' + token + '}}'})
    r = {'method': method, 'header': headers, 'url': B + path}
    if body is not None:
        r['body'] = {'mode': 'raw', 'raw': json.dumps(body)}
    return {'name': name, 'event': list(events), 'request': r}


def status(code):
    return f'pm.test("Status is {code}", function () {{ pm.response.to.have.status({code}); }});'


items = [
    req('01 Register: success', 'POST', '/api/auth/register/',
        {'username': 'alice_{{suffix}}', 'password': 'securepass', 'email': 'alice@example.com'},
        events=[
            pre("pm.collectionVariables.set('suffix', Date.now());"),
            test(status(201),
                 'var j = pm.response.json();',
                 'pm.test("has access and role user", function () { pm.expect(j.access).to.be.a("string"); pm.expect(j.role).to.eql("user"); });'),
        ]),
    req('02 Register: duplicate username', 'POST', '/api/auth/register/',
        {'username': 'alice_{{suffix}}', 'password': 'securepass', 'email': 'alice@example.com'},
        events=[test(status(400))]),
    req('03 Login: success', 'POST', '/api/auth/login/',
        {'username': 'alice_{{suffix}}', 'password': 'securepass'},
        events=[test(status(200),
                     "pm.collectionVariables.set('token_alice', pm.response.json().access);")]),
    req('04 Login: wrong password', 'POST', '/api/auth/login/',
        {'username': 'alice_{{suffix}}', 'password': 'wrongpass'},
        events=[test(status(401))]),
    req('04b Setup: register Bob', 'POST', '/api/auth/register/',
        {'username': 'bob_{{suffix}}', 'password': 'securepass', 'email': 'bob@example.com'},
        events=[test(status(201),
                     "pm.collectionVariables.set('token_bob', pm.response.json().access);")]),
    req('05 Create alert: success', 'POST', '/api/alerts/',
        {'origin': 'DEL', 'destination': 'BOM', 'threshold_price': '1000.00'}, 'token_alice',
        events=[test(status(201),
                     'var j = pm.response.json();',
                     'pm.test("status is active", function () { pm.expect(j.status).to.eql("active"); });',
                     "pm.collectionVariables.set('alert_id', j.id);")]),
    req('06 List alerts: own alerts only', 'GET', '/api/alerts/', token='token_alice',
        events=[test(status(200),
                     'var j = pm.response.json();',
                     'pm.test("only own alert returned", function () { pm.expect(j.length).to.eql(1); pm.expect(j[0].id).to.eql(Number(pm.collectionVariables.get("alert_id"))); });')]),
    req('07 Delete alert: own alert', 'DELETE', '/api/alerts/{{alert_id}}/', token='token_alice',
        events=[test(status(200),
                     'pm.test("status inactive", function () { pm.expect(pm.response.json().status).to.eql("inactive"); });')]),
    req("08 Delete alert: another user's alert", 'DELETE', '/api/alerts/{{alert_id}}/', token='token_bob',
        events=[test(status(404))]),
    req('09 Price feed: valid route', 'GET', '/api/flights/price/?route=DEL-BOM',
        events=[test(status(200),
                     'var j = pm.response.json();',
                     'pm.test("route and integer price", function () { pm.expect(j.route).to.eql("DEL-BOM"); pm.expect(Number.isInteger(j.price)).to.be.true; });')]),
    req('10 Price feed: unknown route', 'GET', '/api/flights/price/?route=XXX-YYY',
        events=[test(status(404))]),
    req('10b Setup: login as admin (pulse_admin)', 'POST', '/api/auth/login/',
        {'username': 'pulse_admin', 'password': 'adminpass123'},
        events=[test(status(200),
                     "pm.collectionVariables.set('token_admin', pm.response.json().access);")]),
    req('11 Admin summary: as admin', 'GET', '/api/admin/summary/', token='token_admin',
        events=[test(status(200),
                     'var j = pm.response.json();',
                     'pm.test("all stat keys present", function () { ["total_alerts","active_alerts","triggered_alerts","total_notifications","top_routes"].forEach(function (k) { pm.expect(j).to.have.property(k); }); });')]),
    req('12 Admin summary: as regular user', 'GET', '/api/admin/summary/', token='token_alice',
        events=[test(status(403))]),
    req('13 Protected endpoint without token', 'GET', '/api/alerts/',
        events=[test(status(401))]),
]

collection = {
    'info': {
        'name': 'PulseNotify API',
        'schema': 'https://schema.getpostman.com/json/collection/v2.1.0/collection.json',
    },
    'variable': [{'key': 'base_url', 'value': 'http://localhost:8000'}],
    'item': items,
}

with open('PulseNotify.postman_collection.json', 'w', encoding='utf-8') as f:
    json.dump(collection, f, indent=2)
print('Wrote PulseNotify.postman_collection.json')