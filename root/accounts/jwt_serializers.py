from django.contrib.auth import authenticate
from django.utils.translation import gettext_lazy as _
from rest_framework import exceptions, serializers

from rest_framework_simplejwt.settings import api_settings
from .models import User
from rest_framework_simplejwt.tokens import RefreshToken, SlidingToken, UntypedToken
from django.db.models import Q

from django.contrib.auth import get_user_model


class CustomAuthentication(object):
    """
    Custom Email Backend to perform authentication via email
    """
    def authenticate(self, username=None, password=None, request=None, email=False, employee__login_id=False):
        try:
            print("SEEING THIS?", username)
            if email:
                user = User.objects.get(email=email)
            elif employee__login_id:
                try:
                    user = User.objects.get(employee__login_id=employee__login_id)
                except:
                    user = User.objects.get(username=employee__login_id)
            else:
                user = User.objects.get(username=username)
            print(user)
            if user.check_password(password):
                return user
        except:
            return None


class PasswordField(serializers.CharField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('style', {})

        kwargs['style']['input_type'] = 'password'
        kwargs['write_only'] = True

        super().__init__(*args, **kwargs)


class TokenObtainSerializer(serializers.Serializer):
    username_field = User.USERNAME_FIELD

    default_error_messages = {
        'no_active_account': _('No active account found with the given credentials')
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        print(args, kwargs)

        if 'email' in kwargs['data']:
            print('using email')
            self.username_field='email'
            self.fields['email'] = serializers.EmailField()
        elif 'employee__login_id' in kwargs['data']:
            print('using email')
            self.username_field='employee__login_id'
            self.fields['employee__login_id'] = serializers.CharField()
        else:
            self.fields[self.username_field] = serializers.CharField()


        self.fields['password'] = PasswordField()
        print(self.fields)

    def validate(self, attrs):
        print("HELLO")
        authenticate_kwargs = {
            self.username_field: attrs[self.username_field],
            'password': attrs['password'],
        }
        try:
            authenticate_kwargs['request'] = self.context['request']
            authenticate_kwargs['self'] = self.context
        except KeyError:
            pass
        print(authenticate_kwargs)
        self.user = CustomAuthentication.authenticate(**authenticate_kwargs)

        # Prior to Django 1.10, inactive users could be authenticated with the
        # default `ModelBackend`.  As of Django 1.10, the `ModelBackend`
        # prevents inactive users from authenticating.  App designers can still
        # allow inactive users to authenticate by opting for the new
        # `AllowAllUsersModelBackend`.  However, we explicitly prevent inactive
        # users from authenticating to enforce a reasonable policy and provide
        # sensible backwards compatibility with older Django versions.
        if self.user is None or not self.user.is_active:
            raise exceptions.AuthenticationFailed(
                self.error_messages['no_active_account'],
                'no_active_account',
            )

        return {}

    @classmethod
    def get_token(cls, user):
        raise NotImplementedError('Must implement `get_token` method for `TokenObtainSerializer` subclasses')


class TokenObtainPairSerializer(TokenObtainSerializer):
    @classmethod
    def get_token(cls, user):
        return RefreshToken.for_user(user)

    def validate(self, attrs):
        print("HELLO")
        data = super().validate(attrs)

        refresh = self.get_token(self.user)

        data['refresh'] = str(refresh)
        data['access'] = str(refresh.access_token)

        return data


class TokenObtainSlidingSerializer(TokenObtainSerializer):
    @classmethod
    def get_token(cls, user):
        return SlidingToken.for_user(user)

    def validate(self, attrs):
        data = super().validate(attrs)

        token = self.get_token(self.user)

        data['token'] = str(token)

        return data


class TokenRefreshSerializer(serializers.Serializer):
    refresh = serializers.CharField()

    def validate(self, attrs):
        refresh = RefreshToken(attrs['refresh'])

        data = {'access': str(refresh.access_token)}

        if api_settings.ROTATE_REFRESH_TOKENS:
            if api_settings.BLACKLIST_AFTER_ROTATION:
                try:
                    # Attempt to blacklist the given refresh token
                    refresh.blacklist()
                except AttributeError:
                    # If blacklist app not installed, `blacklist` method will
                    # not be present
                    pass

            refresh.set_jti()
            refresh.set_exp()

            data['refresh'] = str(refresh)

        return data


class TokenRefreshSlidingSerializer(serializers.Serializer):
    token = serializers.CharField()

    def validate(self, attrs):
        token = SlidingToken(attrs['token'])

        # Check that the timestamp in the "refresh_exp" claim has not
        # passed
        token.check_exp(api_settings.SLIDING_TOKEN_REFRESH_EXP_CLAIM)

        # Update the "exp" claim
        token.set_exp()

        return {'token': str(token)}


class TokenVerifySerializer(serializers.Serializer):
    token = serializers.CharField()

    def validate(self, attrs):
        UntypedToken(attrs['token'])

        return {}
