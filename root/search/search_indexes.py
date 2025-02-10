from haystack import indexes
import sys
from accounts.models import *

"""
This is going to handle the API calls from the search icon in the menu
"""


class EmployeeIndex(indexes.SearchIndex, indexes.Indexable):
    text = indexes.CharField(document=True, use_template=True)
    full_name = indexes.CharField(model_attr='full_name', null=True)
    last_name = indexes.CharField(model_attr='last_name', null=True)
    organization = indexes.CharField(model_attr='org_name_help', null=True)
    organization_id = indexes.CharField(model_attr='organization_id', null=True)
    login_id = indexes.CharField(model_attr='login_id', null=True)
    type = indexes.CharField(model_attr='position_type', null=True)
    slug = indexes.CharField(model_attr='slug', null=True)
    email = indexes.CharField(model_attr='user__email', null=True)
    active = indexes.BooleanField(model_attr='active', null=True)
    username = indexes.CharField(model_attr='user__username', null=True)
    displayname = indexes.EdgeNgramField(model_attr='display_name', null=True)

    def get_model(self):
        return Employee

    def get_updated_field(self):
        return "updated_auto"


# class ProfileIndex(indexes.SearchIndex, indexes.Indexable):
#     text = indexes.CharField(document=True, use_template=True)
#     user = indexes.CharField(model_attr='user')
#     displayname = indexes.CharField(model_attr='display_name', null=True)
#     slug = indexes.CharField(model_attr='slug', null=True)
#
#     def get_model(self):
#         return Profile


class OrganizationIndex(indexes.SearchIndex, indexes.Indexable):
    text = indexes.CharField(document=True, use_template=True)
    name = indexes.CharField(model_attr='name')
    real_name = indexes.CharField(model_attr='real_name', null=True)
    type = indexes.CharField(model_attr='type', null=True)
    #displayname = indexes.CharField(model_attr='display_name', null=True)
    slug = indexes.CharField(model_attr='slug')
    displayname = indexes.EdgeNgramField(model_attr='display_name', null=True)

    def get_model(self):
        return Organization

    def get_updated_field(self):
        return "updated"
