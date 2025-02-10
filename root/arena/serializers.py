from rest_framework import serializers
from .models import *
from accounts.serializers import *


class CompetitionSerializer(serializers.ModelSerializer):

    class Meta:
        model = Competition
        fields = '__all__'


class ConferenceSerializer(serializers.ModelSerializer):
    competition = CompetitionSerializer(read_only=True)

    class Meta:
        model = Conference
        fields = '__all__'

class DivisionSerializer(serializers.ModelSerializer):
    competition = CompetitionSerializer(read_only=True)
    conference = ConferenceSerializer(read_only=True)

    class Meta:
        model = Division
        fields = '__all__'

class DivisionShortSerializer(serializers.ModelSerializer):

    class Meta:
        model = Division
        fields = ('name', )


class RoundSerializer(serializers.ModelSerializer):
    competition = CompetitionSerializer(read_only=True)

    class Meta:
        model = Round
        fields = '__all__'

class RoundShortSerializer(serializers.ModelSerializer):

    class Meta:
        model=Round
        fields = ('starts', 'ends', 'id')


class TeamSerializer(serializers.ModelSerializer):
    competition = CompetitionSerializer(read_only=True)
    organization_players = ShortOrganizationSerializer(many=True)

    class Meta:
        model = Team
        fields = '__all__'

class TeamShortSerializer(serializers.ModelSerializer):

    class Meta:
        model = Team
        fields = ('id', 'name', 'logo', 'abbreviation', 'display_name')


class ScoreComponentSerializer(serializers.ModelSerializer):

    class Meta:
        model = ScoreComponent
        fields = ('label', 'description')


class MatchScoreComponentSerializer(serializers.ModelSerializer):
    component = ScoreComponentSerializer(read_only=True)


    class Meta:
        model=MatchScoreComponents
        fields = ('component', 'value')

class MatchSerializer(serializers.ModelSerializer):
    round = RoundSerializer(read_only=True)
    conference = ConferenceSerializer(read_only=True)
    teams = TeamSerializer(read_only=True, many=True)


    class Meta:
        model = Match
        fields = '__all__'


class MatchShortSerializer(serializers.ModelSerializer):
    round = RoundShortSerializer(read_only=True)
    division = DivisionShortSerializer(read_only=True)
    teams = TeamShortSerializer(read_only=True, many=True)

    class Meta:
        model = Match
        fields = '__all__'


class MatchScoreSerializer(serializers.ModelSerializer):
    match = MatchShortSerializer(read_only=True)
    team = TeamShortSerializer(read_only=True)

    class Meta:
        model = MatchScores
        fields = '__all__'

class MatchVeryScoreShortSerializer(serializers.ModelSerializer):

    class Meta:
        model = MatchScores
        fields = ('score', 'round', 'quarter', 'team__name')

class MatchResultsMatchSerializer(serializers.ModelSerializer):
    match_winner = serializers.ReadOnlyField(source='winner')

    class Meta:
        model = Match
        fields=('match_winner',)

    # def match_winner(self, obj):
    #     max_score = MatchScores.objects.filter(match_id=obj.id).annotate(maxscore=Max('score')).values('score')
    #     return MatchScores.objets.get(score=max_score, match=obj.id)
    #
    # def match_loser(self, obj):
    #     max_score = MatchScores.objects.filter(match_id=obj.id).annotate(maxscore=Max('score')).values('score')
    #     return MatchScores.objets.filter(match=obj.id).exclude(score=max_score)

class MatchScoreShortSerializer(serializers.ModelSerializer):
    round = RoundSerializer(read_only=True)
    team = TeamShortSerializer(read_only=True)
    match = MatchResultsMatchSerializer(read_only=True)
    score_component = serializers.ReadOnlyField(source='score_components')

    class Meta:
        model=MatchScores
        fields = ('round', 'team', 'score', 'quarter', 'match', 'score_component')


class SkillTreePlayerSerializer(serializers.ModelSerializer):
    class Meta:
        model = SkillTreePlayer
        fields = '__all__'

class HH5Serializer(serializers.ModelSerializer):
    territory = serializers.ReadOnlyField(source='get_driver_territory', read_only=True)
    username = serializers.ReadOnlyField(source='get_driver_username', read_only=True)
    # registration_group = serializers.ReadOnlyField(source='registration_group', read_only=True)

    class Meta:
        model = hh5_drivers_sat_statistics
        fields = ('id',
                'employee_id',
                'station_name',
                'registered',
                'id_name_helper',
                'call_volume',
                'base_size_sat_overall',
                'count_overall_totly_stsfd',
                'count_driver_totly_stsfd',
                'pcnt_overall_totly_stsfd',
                'base_size_driver',
                'pcnt_driver_totly_stsfd',
                'territory',
                'username',
                'registration_group')

class HH5DriverSerializer(serializers.ModelSerializer):
    territory = serializers.ReadOnlyField(source='get_territory', read_only=True)
    class Meta:
        model = hh5_drivers
        fields = '__all__'

# class CombinedMatchScoreSerializer(serializers.ModelSerializer):
#     match_group = serializers.SerializerMethodField()
#
#     def get_match_group(self, obj):
#         return MatchScoreSerializer(obj.match.filter(match=obj.match.filter), many=True).data
#
#     class Meta:
#         model
