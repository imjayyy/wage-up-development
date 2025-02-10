from django.utils import timezone
from datetime import datetime as dt
from .models import Profile, Employee
from root.utilities import make_dynamodb_query

class UpdateLastActivityMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        # One-time configuration and initialization.

    def __call__(self, request):
        response = self.get_response(request)

        # Code to be executed for each request/response after
        # the view is called.

        assert hasattr(request,
                       'user'), 'The UpdateLastActivityMiddleware requires authentication middleware to be installed.'

        if request.user.is_authenticated:
            # resp = make_dynamodb_query('createUserAction', {
            #     'input': {
            #         'user_id': request.user.id,
            #         'action': request.path
            #     }
            #
            # })

            print('in the middleware',request.user)

            try:
                print('getting a profile')
                prof = Profile.objects.get(user_id=request.user.id)
                prof.last_activity = timezone.localtime()
                prof.save()
            except:
                print('creating new profile')
                find_prof = Profile.objects.filter(user_id=request.user.id)
                print(find_prof)
                if find_prof.count() < 1:
                    print('creating new')
                    emp = Employee.objects.get(user=request.user.id)
                    prof = Profile.objects.create(user_id=request.user.id, employee=emp)

                elif find_prof.count() == 1:
                    print('one profile found')
                    prof = find_prof[0]
                else:
                    print('multiple profiles found and deleting exes')
                    prof = find_prof[0]
                    [p.delete() for p in find_prof if p != prof]
                prof.last_activity = timezone.localtime()
                prof.save()
        print('middleware done')

        return response
