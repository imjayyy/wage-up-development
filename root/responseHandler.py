import os
import json
from datetime import datetime as dt
class response_tests:
    def __init__(self, **kwargs):
        filename = kwargs.get('filename')
        if filename is not None:
            self.response = self.get_response(kwargs.get('filename'))
        else:
            self.list_responses()


    def get_response(self, filename):
        base_path = "C:\wageup\wageup_repo\.idea\httpRequests"
        response_json = os.path.join(base_path, filename)
        with open(response_json, 'r+') as f:
            d = json.load(f)
        return d

    def list_responses(self):
        base_path = "C:\wageup\wageup_repo\.idea\httpRequests"
        responses = os.listdir(base_path)
        self.response_files = responses
        self.responses = []
        for f in responses:
            if f.endswith('.json'):
                date, status, filetype = f.split('.')
                date = dt.strptime(date, '%Y-%m-%dT%H%M%S')
                if (dt.now() - date).seconds // 60 < 30: # 30 min. ago
                    response = self.get_response(f)
                    self.responses.append({
                        'response': response,
                        'status': status,
                        'date': date
                    })

                    if 'access' in response:
                        self.permissions = response['permission']

r = response_tests()