from app import ma
from app.models import Player, SingleMatch, DoubleMatch, Announcements

class AnnouncementSchema(ma.ModelSchema):
    class Meta:
        fields = ('timestamp', 'title', 'description')
        model = Announcements

class AnnouncementListSchema(ma.ModelSchema):
    class Meta:
        fields = ('id', 'timestamp', 'title')
        model = Announcements


class SimplePlayerSchema(ma.ModelSchema):
    class Meta:
        fields = ('id', 'name', 'image', 'self', 'delete_player', 'update_player')
        model = Player

    image = ma.URLFor("get_player_image", id="<id>")
    self = ma.URLFor("get_player", id="<id>")
    update_player = ma.URLFor("update_player", id="<id>")
    delete_player = ma.URLFor("delete_player", id="<id>")

class PlayerSchema(ma.ModelSchema):

    class Meta:
        fields = ( 'id','password', 'name', 'rollno', 'pwin', 'plos', 'dwin', 'dlos', 'age', 'mobile', 'dob', 'image', 'delete_player', 'update_player', 'type')
        model = Player

    image = ma.URLFor("get_player_image", id="<id>")
    update_player = ma.URLFor("update_player", id="<id>")
    delete_player = ma.URLFor("delete_player", id="<id>")
    pwin = ma.Function(lambda match, context: int(context['pwin']))
    plos = ma.Function(lambda match, context: int(context['plos']))
    dwin = ma.Function(lambda match, context: int(context['dwin']))
    dlos = ma.Function(lambda match, context: int(context['dlos']))

class SingleMatchSchema(ma.ModelSchema):

    class Meta:
        fields = ('id', 'date', 'winner_id', 'loser_id', 'winner_name', 'loser_name', 'update_singles', 'delete_singles')
        model = SingleMatch

    winner_name = ma.Function(lambda match: Player.query.get_or_404(match.winner_id).name)
    loser_name = ma.Function(lambda match: Player.query.get_or_404(match.loser_id).name)

    delete_singles = ma.URLFor("delete_singlematch", id="<id>")
    update_singles = ma.URLFor("update_singlematch", id="<id>")

class SingleSummarySchema(ma.ModelSchema):

    class Meta:
        fields = ('date', 'opponent', 'match_won')
        model = SingleMatch

    w = ma.Function(lambda match: Player.query.get_or_404(match.winner_id).name)
    l = ma.Function(lambda match: Player.query.get_or_404(match.loser_id).name)

    opponent = ma.Method('get_opponent')
    match_won = ma.Method('get_matchwon')

    def get_opponent(self, match):
        pid = int(self.context['player_id'])
        mp = {
            match.winner_id : match.l,
            match.loser_id : match.w
        }
        return mp[pid]

    def get_matchwon(self, match):
        pid = int(self.context['player_id'])
        mp = {
            match.winner_id : True,
            match.loser_id : False
        }
        return mp[pid]


class DoubleMatchSchema(ma.ModelSchema):

    class Meta:
        fields = ('id', 'date', 'winner1_id', 'winner2_id', 'loser1_id', 'loser2_id',
                'winner1_name', 'winner2_name', 'loser1_name', 'loser2_name', 'delete_doubles', 'update_doubles')
        model = DoubleMatch

    winner1_name = ma.Function(lambda match: Player.query.get_or_404(match.winner1_id).name)
    winner2_name = ma.Function(lambda match: Player.query.get_or_404(match.winner2_id).name)
    loser1_name = ma.Function(lambda match: Player.query.get_or_404(match.loser1_id).name)
    loser2_name = ma.Function(lambda match: Player.query.get_or_404(match.loser2_id).name)

    delete_doubles = ma.URLFor("delete_doublematch", id="<id>")
    update_doubles = ma.URLFor("update_doublematch", id="<id>")

class DoubleSummarySchema(ma.ModelSchema):

    class Meta:
        fields = ('date', 'opponent1', 'opponent2', 'partner', 'match_won')
        model = DoubleMatch
        # exclude = ('w1', 'w2', 'l1', 'l2')

    partner = ma.Method('get_partner')
    opponent1 = ma.Method('get_opponent1')
    opponent2 = ma.Method('get_opponent2')
    match_won = ma.Method('get_matchwon')

    def get_matchwon(self, match):
        pid = int(self.context['player_id'])
        mp = {
            match.winner1_id : True,
            match.winner2_id : True,
            match.loser1_id : False,
            match.loser2_id : False,
        }
        return mp[pid]

    def get_partner(self, match):
        pid = int(self.context['player_id'])
        mp = {
            match.winner1_id : match.winner2_id,
            match.winner2_id : match.winner1_id,
            match.loser1_id : match.loser2_id,
            match.loser2_id : match.loser1_id,
        }
        return Player.query.get_or_404(mp[pid]).name

    def get_opponent1(self, match):
        pid = int(self.context['player_id'])
        mp = {
            match.winner1_id : match.loser1_id,
            match.winner2_id : match.loser2_id,
            match.loser1_id : match.winner1_id,
            match.loser2_id : match.winner2_id,
        }
        return Player.query.get_or_404(mp[pid]).name

    def get_opponent2(self, match):
        pid = int(self.context['player_id'])
        mp = {
            match.winner1_id : match.loser2_id,
            match.winner2_id : match.loser1_id,
            match.loser1_id : match.winner2_id,
            match.loser2_id : match.winner1_id,
        }
        return Player.query.get_or_404(mp[pid]).name
