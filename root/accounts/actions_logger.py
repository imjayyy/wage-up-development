from .models import *
import logging

logger = logging.getLogger('custom')

class ActionsLogger():

    def __init__(self, user, model=None, display=None, action_type=None, url=None, details=[]):
        self.user = user
        self.model = model
        self.action_type = action_type
        self.display = display,
        self.url = url
        print(user, model, display, action_type, url)

        if self.url is None:
            self.url = '/dashboard/'

        if self.display is None:
            self.display = "Action Taken"


        if type(self.display) == list or type(self.display) == tuple:
            self.display = self.display[0]

        self.action = self.writeActiontoDB()

        if len(details) > 0:
            for detail in details:
                for k in ['db_action_type', 'context', 'field', 'from_value', 'to_value']:
                    if k not in detail.keys():
                        detail[k] = None
                detail = UserActionDetails(
                    db_action_type=detail['db_action_type'],
                    db_model = detail['db_model'],
                    db_model_id = detail['db_model_id'],
                    context = detail['context'],
                    parent_action = self.action,
                    field=detail['field'],
                    from_value = detail['from_value'],
                    to_value = detail['to_value'],
                )
                detail.save()


    def writeActiontoDB(self):
        try:
            action = UserActions(
                user=self.user,
                display = self.display,
                type = self.action_type,
                model_name = self.model,
                url = self.url,

            )
            action.save()
            return action

        except Exception as e:
            logger.warning(e)
            print(e)