##Deployment

eb create {env-name} --vpc

eb config 
check WSGI route should be root/wsgi.py
https://stackoverflow.com/questions/29395875/deploying-django-to-aws-wsgipath-refers-to-a-file-that-does-not-exist/59201763#59201763

eb console
restart app servers

eb deploy

vpc id: vpc-09b42b8973279a823
subnets: subnet-04168ea834a4997be, subnet-0c0c4b0b7b9d95f55
security group: sg-00d7addb68485078f

create new Route 53


#to deploy: 
```eb deploy```




#API REFERENCE

##Assumptions
All below API assume a proper bearer token is present unless otherwise specified.

##Accounts

###Login

Obviously... no bearer token is needed. This is how you get the token...

```
{
{
	"username": "fake1",
	"password": "faker!"
}
```

LOGIN RESPONSE
```
{
    "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTU1NzUyNDYzNiwianRpIjoiNWZjM2M2NDBiN2M3NDNkNjgxYzkxOGYxNzJkYTZkNTEiLCJ1c2VyX2lkIjoxfQ.pQwsnHrwduJY94Jfj13c_S_HeDyphRnmzEwTYiU73Kk",
    "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNTU3NDQxODM2LCJqdGkiOiI1Yjk5NDFiODVkOTk0ZThlYWZmZThlZGVjYWEzNWUyNyIsInVzZXJfaWQiOjF9.z0alykQ_rDHgCM3d7awy2u-9dLmgyKI13mtKcO6MXVU",
    "id": 1,
    "first_name": "Devin",
    "last_name": "Gonier",
    "user": 1,
    "organization": {
        "id": 10004647,
        "parent": null,
        "name": "Wageup",
        "real_name": "Wageup",
        "type": "Admin",
        "updated": "2019-05-08T21:57:43.658000Z",
        "slug": "wageup",
        "parent_name": "",
        "parent_type": null,
        "display_name": "WageUp",
        "facility_type": null,
        "latest_activity_on": null,
        "zip": null,
        "grandparent": null,
        "employees_under": 10004647
    },
    "position_type": "Admin",
    "permission": [
        {
            "id": 5,
            "name": "invite-children",
            "explanation": "Can invite anyone in own and child organization"
        },
        {
            "id": 8,
            "name": "create-child-employees",
            "explanation": "Can create child employees"
        }
    ],
    "slug": "dgonier",
    "bio": "I like Long Walks on the Beach, and playing with my cat.",
    "display_name": "Devin",
    "viewed_show": false,
    "employee": 7464
}
```

Bad username responds with:

```
No User Data Found
```

Bad Password responds with:
```
{
    "non_field_errors": [
        "No active account found with the given credentials"
    ]
}

```

### Refresh Token

POST to /accounts/refresh/

```
{
    "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTU1NzUyNTI3MiwianRpIjoiODIxMWMxNGRmMmJlNGM0YThmY2E1MmIwMmI0NzQ4YTMiLCJ1c2VyX2lkIjoxfQ.90ZSd2-ZCd40H5YEeNLkLgPdim96ZAd4BS46tnW1i5E"
}
```

RETURNS:

```
{
    "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNTU3NDQ1MzU1LCJqdGkiOiJhNjRiNWI3MTk5NzM0MDM1YjYwYWQxZWM0ZTU2OGQyYSIsInVzZXJfaWQiOjF9.6fT-SFVos535oTNSIC_Zw7BEvHBCMBGOfRfr-gWfBm0"
}
```

### Create User (from invite)

POST to /accounts/create-user/

Params:

* id -- this is the INVITE_ID
* username -- user created username
* password -- user created password

NOTE: management of password length, qualities etc. is done on the front end 
i.e. form validation is managed by the front end, but username checks are done on the back (i.e. uniqueness)


NOTE: User gets emailed a confirmation, then is redirected to the front end again so they can login!
A LOGIN WONT WORK, UNLESS THEY CLICK THE LINK, because they are not active yet!
```
{
	"id": 5,
	"username": "devingon2",
	"password": "test"
}

```

RETURNS:

```
{
    "id": 25976,
    "first_name": "Tom",
    "last_name": "Hanks",
    "user": {
        "id": 25,
        "username": "devingon2",
        "first_name": "Tom",
        "last_name": "Hanks",
        "email": "dgonier@gmail.com",
        "is_staff": false,
        "is_active": false,
        "last_login": null,
        "is_superuser": false,
        "date_joined": "2019-05-09T22:46:07.042707Z"
    },
    "organization": {
        "id": 10004647,
        "parent": null,
        "name": "Wageup",
        "real_name": "Wageup",
        "type": "Admin",
        "updated": "2019-05-08T21:57:43.658000Z",
        "slug": "wageup",
        "parent_name": "",
        "parent_type": null,
        "display_name": "WageUp",
        "facility_type": null,
        "latest_activity_on": null,
        "zip": null,
        "grandparent": null,
        "employees_under": 10004647
    },
    "position_type": "Admin",
    "permission": [],
    "slug": "tom-hanks"
}

```


### Send Invite to Employee

POST to /accounts/invite/

Users can send out invites to "their" employees with this id in a list.
Only need to send the email and corresponding employee. 

User submitting API must have permission based on permission structure.

```
[
    {
        "email": "dgonier@gmail.com",
        "employee": 25976
    },
]

```

RETURNS:

```
{
    "id": 5,
    "employee": 25976,
    "created_by": 1,
    "email": "dgonier@gmail.com",
    "created_on": "2019-05-09",
    "sent_on": "2019-05-09T22:35:12.741680Z",
    "already_used": false,
    "expiration": "2019-07-08",
    "created_by_employee": 25973
}
```

IF NOT ALLOWED... RETURNS:

```
"ACCESS DENIED"
```

###Add employee

Add an employee with the following:

Submit to: /accounts/employee/ as POST

Params:
* organization -- what org id does the employee belong from accounts_organization
* position_type -- check accounts_employee for choices please. if submitter is not admin will throw error!
```
"This position type is new! If this is intentional please post as an Admin employee otherwise please select from the following choices:['Admin', 'Driver', 'Call-Center-Operator', 'Facility-Rep']"
```
* permission -- list of permission ids that correspond to this employee, pass "[]" for no permission, what you can see, who you can invite etc. 

```
[{
	"organization": 10004647,
	"first_name": "Tom",
	"last_name": "Hanks",
	"position_type": "Admin",
	"permission": [1, 2]
}, 
{
	"organization": 10004647,
	"first_name": "Adam",
	"last_name": "Sandler",
	"position_type": "Admin",
	"permission": [6, 7]
}]

```

Returns if succesful:

```
[
    {
        "id": 25992,
        "first_name": "Bob",
        "last_name": "Hanks",
        "organization": 10004647,
        "position_type": "Admin",
        "permission": [
            1,
            2
        ],
        "slug": "10004647-bob-hanks",
        "latest_activity_on": "2019-05-09"
    },
    {
        "id": 25993,
        "first_name": "Adam",
        "last_name": "Sandler",
        "organization": 10004647,
        "position_type": "Admin",
        "permission": [
            6,
            7
        ],
        "slug": "10004647-adam-sandler",
        "latest_activity_on": "2019-05-09"
    }
]
```

OR 

```
"Missing parameters. Please pass at least['organization', 'first_name', 'last_name', 'position_type', 'permission']"
```

###Request Eligible Employees

Submit to: /accounts/invite/ as POST

Params:
* eligible employees -- its just a key, it doesnt matter what value you pass
* only_non_users -- if you want to restrict the list to non-users use this. doesnt matter what value you pass...

```
{
	"eligible_employees": 1,
	"only_non_users": 1
}

```

RETURNS:

```
[
    {
        "id": 25976,
        "first_name": "Tom",
        "last_name": "Hanks",
        "slug": "tom-hanks",
        "position_type": "Admin",
        "organization_id": 10004647,
        "user_id": null,
        "org_name_help": "WageUp (DGC)",
        "username_help": "",
        "permission_help": null,
        "full_name": "Devin Gonier",
        "display_name": "Devin Gonier (WageUp Admin)",
        "data_name": "",
        "updated": "2019-05-08T22:01:30.440000Z",
        "latest_activity_on": "2019-05-08",
        "invited_on": "2019-05-09T22:35:15.905010Z"
    },
    {
        "id": 25992,
        "first_name": "Bob",
        "last_name": "Hanks",
        "slug": "10004647-bob-hanks",
        "position_type": "Admin",
        "organization_id": 10004647,
        "user_id": null,
        "org_name_help": "Wageup",
        "username_help": null,
        "permission_help": null,
        "full_name": "Bob Hanks",
        "display_name": "Bob Hanks (Wageup)",
        "data_name": null,
        "updated": "2019-05-09T16:00:46.082069Z",
        "latest_activity_on": "2019-05-09",
        "invited_on": null
    },
    {
        "id": 25993,
        "first_name": "Adam",
        "last_name": "Sandler",
        "slug": "10004647-adam-sandler",
        "position_type": "Admin",
        "organization_id": 10004647,
        "user_id": null,
        "org_name_help": "Wageup",
        "username_help": null,
        "permission_help": null,
        "full_name": "Adam Sandler",
        "display_name": "Adam Sandler (Wageup)",
        "data_name": null,
        "updated": "2019-05-09T16:00:46.905919Z",
        "latest_activity_on": "2019-05-09",
        "invited_on": null
    }
]
```

## Dashboard

submit to /dashboard/ as post unless otherwise specified

all posts need:
* id or slug -- identifies the object
* a type e.g. Territory, Station, etc. -- helps know where to look i.e. employee, vs org
* a purpose: ("timeseries", "calendar") -- what function are we calling
* parameters -- details of the function specific to each one

### Reference

Just pass "remind_me" as a key in the post, and get a structured response for available metrics

```
{
	"remind_me": 1
}

```

### Timeseries Calls

POST submitted to /dashboard/

parameter notes:

* "metrics" -- a list of metrics we want e.g. volume, tow_volume, etc. call remind me to see options
* "time_type" -- Monthly, Hourly, Daily, etc. 
* "from" -- optional parameter to set a start date
* "to" -- optional parameter to set an end date
* "week_day" -- optional parameter to filter by weekday

INPUT ex.
```
{
 "id": 1649,
 "type": "Station",
 "purpose": "timeseries",
 "parameters": {
   "metrics": ["volume"],
   "time_type": ["Day"],
   "from": "2019-03-01",
   "to": "2019-03-15",
   "week_day": "Mon"
 }
}
```

RESPONSE ex.

```

[
    [
        {
            "groupName": "volume",
            "time_type": "Day",
            "data": [
                {
                    "value": 125,
                    "label": "2019-03-04T00:00:00Z",
                    "value_type": "number"
                },
                {
                    "value": 147,
                    "label": "2019-03-11T00:00:00Z",
                    "value_type": "number"
                }
            ]
        }
    ]
]

```


### Discrete Calls

POST submitted to /dashboard/

parameter notes:
* relation: -- type of relation e.g. children, siblings, self
* metrics -- list of metrics to get
* anon -- 1 or 0 return values without names/links, just dont pass it if you dont want it
* relation_type_only -- restrict returned types to specified value
* gt_rank, lt_rank -- rank less than or greater than for each metric in passed list
* time_type:
    * Prev_Month
    * This_Month
    * MTD_Prev_3_Months
    * YTD
    * MTD_Last_Year
    * This_Calendar_Quarter

INPUT:

```
{
 "slug": "vadc",
 "type": "Market",
 "purpose": "calendar",
 "parameters": {
    "relation": "children",
   "metrics": ["volume", "driver_sat_aaa_mgmt_all_avg", "tow_volume"],
   "time_sync_to": "ops", 
   "anon": 1,
   "relation_type_only": "Territory",
   "gt_rank": ["driver_sat_aaa_mgmt_all_avg"],
   "time_type": ["this_month", "prev_month"]
 }
}

```

RETURN: 

```
[
    {
        "groupName": "this_month",
        "name": "ANON",
        "data": [
            {
                "date": "2019-04-01T00:00:00Z",
                "label": "volume",
                "value": 8518,
                "value_type": "number"
            },
            {
                "date": "2019-04-01T00:00:00Z",
                "label": "driver_sat_aaa_mgmt_all_avg",
                "value": 0.657894736842105,
                "value_type": "percentage",
                "gt_rank": 39
            },
            {
                "date": "2019-04-01T00:00:00Z",
                "label": "tow_volume",
                "value": 4336,
                "value_type": "number"
            }
        ],
        "type": "Territory",
        "id": [
            0,
            "ANON"
        ]
    },
    {
        "groupName": "this_month",
        "name": "ANON",
        "data": [
            {
                "date": "2019-04-01T00:00:00Z",
                "label": "volume",
                "value": 7683,
                "value_type": "number"
            },
            {
                "date": "2019-04-01T00:00:00Z",
                "label": "driver_sat_aaa_mgmt_all_avg",
                "value": 0.8,
                "value_type": "percentage",
                "gt_rank": 27
            },
            {
                "date": "2019-04-01T00:00:00Z",
                "label": "tow_volume",
                "value": 3102,
                "value_type": "number"
            }
        ],
        "type": "Territory",
        "id": [
            0,
            "ANON"
        ]
    },
    
    ...

```

## Training

ALL API REQUESTS MADE TO: /training/


### Get Modules
You can get a list of all the training modules this way:

PURPOSE: "get_modules"

Type: POST

```
{
 "purpose": "get_modules",
 "parameters": {}
}

```

RETURNS:

```
[
    {
        "id": 1,
        "title": "Check ID Certification",
        "description": "This course introduces drivers to the new technology and approach to checking member ids.",
        "icon": null,
        "question_count": 4,
        "pass_threshold": 0.75,
        "date_created": "2019-04-30"
    }
]
```


### Get Events
You can get a list of all the events IN a module this way

PURPOSE: "get_events"

Type: POST

```
{
 "purpose": "get_events",
 "parameters": {
 	"module_id": 1
 }
}

```

RETURNS:

```
[
    {
        "id": 1,
        "multiple_choice": null,
        "event_order": 1,
        "event_type": "html_text",
        "html_text": "<h1>Welcome to the Check ID Certification Course </h1>",
        "video": null,
        "module": 1
    },
    {
        "id": 2,
        "multiple_choice": null,
        "event_order": 2,
        "event_type": "video",
        "html_text": null,
        "video": "https://www.w3schools.com/tags/movie.mp4",
        "module": 1
    },
    {
        "id": 5,
        "multiple_choice": {
            "question": "What is the best gamification platform website?",
            "answer_one": "BunchBall",
            "answer_two": "WageUp",
            "answer_three": "Badgeville",
            "answer_four": "Hoopla",
            "answer_five": "GamEffective"
        },
        "event_order": 3,
        "event_type": "multiple_choice",
        "html_text": null,
        "video": null,
        "module": 1
    },
    {
        "id": 6,
        "multiple_choice": {
            "question": "What is the best gamification platform website?",
            "answer_one": "BunchBall",
            "answer_two": "WageUp",
            "answer_three": "Badgeville",
            "answer_four": "Hoopla",
            "answer_five": "GamEffective"
        },
        "event_order": 4,
        "event_type": "multiple_choice",
        "html_text": null,
        "video": null,
        "module": 1
    },
    {
        "id": 7,
        "multiple_choice": {
            "question": "What is the best gamification platform website?",
            "answer_one": "BunchBall",
            "answer_two": "WageUp",
            "answer_three": "Badgeville",
            "answer_four": "Hoopla",
            "answer_five": "GamEffective"
        },
        "event_order": 5,
        "event_type": "multiple_choice",
        "html_text": null,
        "video": null,
        "module": 1
    },
    {
        "id": 8,
        "multiple_choice": {
            "question": "What is the best gamification platform website?",
            "answer_one": "BunchBall",
            "answer_two": "WageUp",
            "answer_three": "Badgeville",
            "answer_four": "Hoopla",
            "answer_five": "GamEffective"
        },
        "event_order": 6,
        "event_type": "multiple_choice",
        "html_text": null,
        "video": null,
        "module": 1
    }
]
```



### Update User Progress

PURPOSE: "update_user_progress"

You can submit user changes i.e. progress to next state, submit answer this way...

Type: POST

Params:
* reset: will delete current record and start over, dont pass it if you dont need it!
* selection: what answer choice was made, dont pass it if you dont need it!
* module_id: what training module is it
* event_order: what event in the module are we on. i.e. 1 is the first event of the module

NOTE : with reset you need to be on event_order 1 for it to work
```
{
 "purpose": "update_user_progress",
 "parameters": {
 	"module_id": 1,
 	"event_order": 1,
 	"selection": 1,
 	"reset": 1
 }
}
```

RESET PARAM returns: 
```

"current state for this module was deleted. You can start over now!"

```

Standard Change returns i.e. moving from one event to the next without finishing...
```
{
    "id": 26,
    "correct_questions": 0,
    "incorrect_questions": 0,
    "passed": false,
    "final_grade": 0,
    "user": 1,
    "module": 1,
    "last_event": 1
}
```

With selection before finishing...
```
{
    "correct_questions": 1,
    "incorrect_questions": 0,
    "passed": false,
    "final_grade": 0,
    "module": 1,
    "last_event": 5,
    "user": 1
}
```

After finishing returns this:

```
{
    "correct_questions": 4,
    "incorrect_questions": 0,
    "passed": true,
    "final_grade": 1,
    "module": 1,
    "last_event": 8,
    "user": 1
}

```


## Search

## 
