import os
import time
import requests
import json
from datetime import datetime, timezone

# I am too lazy to dig up the id mapping, you have to do it yourself :c
AIRPORTS = {
    'AMS':'141',
    'BUD':'506',
}
AIRPORTS_INV = {v: k for k, v in AIRPORTS.items()}

# config.json should contain the used headers for the requests
# {
#     "accessToken":"<token>",
#     "User-Agent":"Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:142.0) Gecko/20100101 Firefox/142.0"
# }
with open('config.json') as f:
    CONFIG = json.load(f)

def GetFlightNumbersByAirportOverMonth(airport, date, force_reload=False):
    return GetFlightNumbersByAirportIdOverMonth(AIRPORTS[airport], date, force_reload=force_reload)

def GetFlightNumbersByAirportIdOverMonth(airport, date, force_reload=False):
    ret = []
    for i in range(29):
        day = str(i+1)
        while len(day) < 2:
            day = '0'+day
        ids = GetFlightNumbersByAirportId(airport, date+'-'+day, force_reload=force_reload)
        for id in ids:
            if id not in ret:
                ret.append(id)
    return ret

def GetFlightNumbersByAirport(airport, date, force_reload=False):
    return GetFlightNumbersByAirportId(AIRPORTS[airport], date, force_reload=force_reload)

def GetFlightNumbersByAirportId(airport, date, force_reload=False):
    os.makedirs('data', exist_ok=True)
    path = 'data/'+airport+'_'+date+'.json'
    if os.path.exists(path) and not force_reload:
        with open(path) as f:
            return json.load(f)
    ret = []
    try:
        results = json.loads(requests.get('https://www.flightradar24.com/api/v1/airport-history/'+airport+'?date='+date+'&eventType=takeoff', headers=CONFIG).text)
        for flight in results['data']:
            if flight['flightNumber'] not in ret and flight['flightNumber'] is not None:
                ret.append(flight['flightNumber'])
        results = json.loads(requests.get('https://www.flightradar24.com/api/v1/airport-history/'+airport+'?date='+date+'&eventType=landed', headers=CONFIG).text)
        for flight in results['data']:
            if flight['flightNumber'] not in ret and flight['flightNumber'] is not None:
                ret.append(flight['flightNumber'])
    except Exception as e:
        print(date)
        print(results)
        raise e
    with open(path, 'w') as f:
        json.dump(ret, f)
    return ret

def GetFlightHistoryByFlightNumber(flightNumber, force_reload=False):
    os.makedirs('data', exist_ok=True)
    path = 'data/'+flightNumber+'.json'
    if os.path.exists(path) and not force_reload:
        with open(path) as f:
            return json.load(f)
    while True:
        results = requests.get('https://www.flightradar24.com/data/flights/'+flightNumber, headers=CONFIG).text
        time.sleep(3)
        if 'Just a moment...' not in results:
            break
        print("Ratelimit hit, waiting 60s!")
        time.sleep(60)

    ret = []
    if 'There is currently no data available for your request' not in results:
        try:
            cutoff = 'data-airline-name="'
            idx = results.index(cutoff)+len(cutoff)
            results = results[idx:]
            airline = results[:results.index('"')]
            cutoff = '<thead><tr><th scope="col" class="visible-xs visible-sm" colspan="20">FLIGHTS HISTORY'
            idx = results.index(cutoff)+len(cutoff)
            results = results[idx:]
            cutoff = '<tbody>'
            idx = results.index(cutoff)+len(cutoff)
            results = results[idx:]
            cutoff = '</tbody>'
            idx = results.index(cutoff)
            results = results[:idx]
            results = results.split('</td></tr>   <tr')
            r = ''
            for r in results:
                if "Landed" not in r and "Canceled" not in r:
                    continue
                cutoff = 'data-timestamp="'
                idx = r.index(cutoff)+len(cutoff)
                r = r[idx:]
                timestamp = int(r[:r.index('"')])
                cutoff = '<label>FROM</label> <span class="details">'
                idx = r.index(cutoff)+len(cutoff)
                r = r[idx:]
                cutoff = 'class="fbold">('
                idx = r.index(cutoff)+len(cutoff)
                r = r[idx:]
                airport_from = r[:r.index(')')]
                cutoff = '<label>TO</label> <span class="details">'
                try:
                    idx = r.index(cutoff)+len(cutoff)
                    r = r[idx:]
                    cutoff = 'class="fbold">('
                    idx = r.index(cutoff)+len(cutoff)
                except:
                    continue
                r = r[idx:]
                airport_to = r[:r.index(')')]
                cutoff = '<td class="hidden-xs hidden-sm">'
                idx = r.index(cutoff)+len(cutoff)
                r = r[idx:]
                aircraft_type = r[:r.index('<')].strip()
                cutoff = 'data-timestamp="'
                idx = r.index(cutoff)+len(cutoff)
                r = r[idx:]
                departure_scheduled = r[:r.index('"')]
                cutoff = 'data-timestamp="'
                idx = r.index(cutoff)+len(cutoff)
                r = r[idx:]
                departure_actual = r[:r.index('"')]
                cutoff = 'data-timestamp="'
                idx = r.index(cutoff)+len(cutoff)
                r = r[idx:]
                arrival_scheduled = r[:r.index('"')]
                if "Landed" in r:
                    cutoff = 'data-timestamp="'
                    idx = r.index(cutoff)+len(cutoff)
                    r = r[idx:]
                    arrival_actual = r[:r.index('"')]
                elif "Canceled" in r:
                    arrival_actual = ""
                ret.append([
                    flightNumber,
                    timestamp,
                    airline,
                    airport_from,
                    airport_to,
                    aircraft_type,
                    departure_scheduled,
                    departure_actual,
                    arrival_scheduled,
                    arrival_actual,
                ])
        except Exception as e:
            print(results)
            print(r)
            print(ret[-1])
            print('https://www.flightradar24.com/data/flights/'+flightNumber)
            raise e
    with open(path, 'w') as f:
        json.dump(ret, f)
    return ret

def GetEventsByAirport(airport, date, force_reload=False, verbose=False):
    return GetEventsByAirportId(AIRPORTS[airport], date, force_reload=force_reload, verbose=verbose)

# Very hacky solution, when requesting GetFlightNumbersByAirportId, cancelled flights are not returned.
# We can try to reconstruct the missing data by getting the flight numbers from a longer period (such as a month)
# for the requested airport, and get the flight history for each flight number, and then re-filter based on the
# requested date.
def GetEventsByAirportId(airport, date, force_reload=False, verbose=False):
    flightNumbers = GetFlightNumbersByAirportIdOverMonth(airport, date[:7], force_reload=force_reload)
    events = []
    dt = datetime.strptime(date, '%Y-%m-%d').replace(tzinfo=timezone.utc)
    date_start = int(dt.timestamp())
    date_end = date_start+24*60*60
    for i in range(len(flightNumbers)):
        if verbose:
            print(str(i+1)+' / '+str(len(flightNumbers)))
        history = GetFlightHistoryByFlightNumber(flightNumbers[i], force_reload=force_reload)
        for h in history:
            if date_start <= h[1] and h[1] <= date_end and (h[3] == AIRPORTS_INV[airport] or h[4] == AIRPORTS_INV[airport]):
                events.append(h)
    events.sort(key=lambda x: x[1], reverse=False)
    return events

def GetCanceledFlightsByAirlineByAirport(airport, date, time_from="00:00", time_until="24:00", landing=True, force_reload=False, verbose=False):
    return GetCanceledFlightsByAirlineByAirportId(AIRPORTS[airport], date, time_from=time_from, time_until=time_until, landing=landing, force_reload=force_reload, verbose=verbose)

def GetCanceledFlightsByAirlineByAirportId(airport, date, time_from="00:00", time_until="24:00", landing=True, force_reload=False, verbose=False):
    dt = datetime.strptime(date, '%Y-%m-%d').replace(tzinfo=timezone.utc)
    date_start = int(dt.timestamp())
    date_end = date_start+int(time_until.split(':')[0])*60*60+int(time_until.split(':')[1])*60
    date_start = date_start+int(time_from.split(':')[0])*60*60+int(time_from.split(':')[1])*60
    events = GetEventsByAirportId(airport, date, force_reload=force_reload, verbose=verbose)
    events = [e for e in events if date_start <= e[1] and e[1] <= date_end and ((landing and e[4] == AIRPORTS_INV[airport]) or (not landing and e[3] == AIRPORTS_INV[airport]))]
    canceled = {}
    canceled_cnt = 0
    flew = {}
    flew_cnt = 0
    for e in events:
        if e[9] == '':
            if e[2] in canceled:
                canceled[e[2]] += 1
            else:
                canceled[e[2]] = 1
            canceled_cnt += 1
        else:
            if e[2] in flew:
                flew[e[2]] += 1
            else:
                flew[e[2]] = 1
            flew_cnt += 1
    all_cnt = canceled_cnt + flew_cnt
    print("Total flights: "+str(all_cnt))
    print("Cancelled: "+str(canceled))

#flight_ids = GetFlightNumbersByAirportOverMonth('BUD', '2025-09')
#print(flight_ids)

#flight_history = GetFlightHistoryByFlightNumber('KL1370')
#print(flight_history)

#events = GetEventsByAirport('BUD', '2025-09-16', verbose=True)
#events = GetEventsByAirport('AMS', '2025-09-16', verbose=True)
#print(events)

print("BUD takeoffs on 2025-09-16")
print("Between 16:00-20:00")
GetCanceledFlightsByAirlineByAirport('BUD', '2025-09-16', time_from="16:00", time_until="20:00", landing=False)
print("All day")
GetCanceledFlightsByAirlineByAirport('BUD', '2025-09-16', landing=False)
print("==========================")
print("BUD landings on 2025-09-16")
print("Between 16:00-20:00")
GetCanceledFlightsByAirlineByAirport('BUD', '2025-09-16', time_from="16:00", time_until="20:00", landing=True)
print("All day")
GetCanceledFlightsByAirlineByAirport('BUD', '2025-09-16', landing=True)
print("==========================")
print("AMS takeoffs on 2025-09-16")
print("Between 16:00-20:00")
GetCanceledFlightsByAirlineByAirport('AMS', '2025-09-16', time_from="16:00", time_until="20:00", landing=False)
print("All day")
GetCanceledFlightsByAirlineByAirport('AMS', '2025-09-16', landing=False)
print("==========================")
print("AMS landings on 2025-09-16")
print("Between 16:00-20:00")
GetCanceledFlightsByAirlineByAirport('AMS', '2025-09-16', time_from="16:00", time_until="20:00", landing=True)
print("All day")
GetCanceledFlightsByAirlineByAirport('AMS', '2025-09-16', landing=True)