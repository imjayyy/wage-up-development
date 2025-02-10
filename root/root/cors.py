from django.http import HttpResponse

class CorsMiddleware(object):
    """adds Access-Control-Allow-Origin: * to all requests"""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response =  self.get_response(request)
        response["Access-Control-Allow-Origin"] = "*"
        response["Access-Control-Allow-Headers"] = "accept, accept-encoding, authorization, content-type, dnt, origin, user-agent, x-csrftoken, x-requested-with"
        return response

    # return options requests before they hit the view
    def process_view(self, request, view_func, view_args, view_kwargs):
        if request.method == 'OPTIONS':
            return HttpResponse("Fire Away", status=200)



