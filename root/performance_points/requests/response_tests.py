import json
import os

print(os.getcwd())

from response import response

d = json.loads(response)

def check_time_volume(d):
    total_vol = 0
    for hour in d['hours']:
        # print(hour['sc_dt'])
        total_vol+= hour['volume_pred']
    print(total_vol)

if __name__ == '__main__':
    check_time_volume(d)