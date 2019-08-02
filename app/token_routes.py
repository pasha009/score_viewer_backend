from app import app, db
from flask import request, jsonify, url_for
from app.models import Player, RevokedTokenModel, SingleMatch, DoubleMatch
from flask_jwt_extended import (create_access_token, create_refresh_token, jwt_required, jwt_refresh_token_required, get_jwt_identity, get_raw_jwt)
from app.serializers import PlayerSchema
from sqlalchemy import exc, or_
from datetime import timedelta

def get_count(q):
    count_q = q.statement.with_only_columns([db.func.count()]).order_by(None)
    count = q.session.execute(count_q).scalar()
    return count

def get_single_query(id):
    return [ SingleMatch.query.filter(SingleMatch.winner_id == id),
             SingleMatch.query.filter(SingleMatch.loser_id == id) ]

def get_double_query(id):
    return [ DoubleMatch.query.filter(
             or_( DoubleMatch.winner1_id == id,
                  DoubleMatch.winner2_id == id)),
             DoubleMatch.query.filter(
             or_( DoubleMatch.loser1_id == id,
                  DoubleMatch.loser2_id == id) )
            ]

def err(msg, code):
    return jsonify({"status":"error", "error": msg}), code

player_schema = PlayerSchema(strict=False)
expires = timedelta(days=365)

@app.route('/api/player/basic/', methods=['POST'])
@jwt_required
def get_basic_player():
    player = Player.find_by_mobile(request.json['mobile'])
    if not player:
        return err("Mobile not registered", 201)
    ps = PlayerSchema(strict=False)
    squer = get_single_query(player.id)
    dquer = get_double_query(player.id)
    ps.context = {
        "dlos" : get_count(dquer[1]),
        "dwin" : get_count(dquer[0]),
        "plos" : get_count(squer[1]),
        "pwin" : get_count(squer[0])
        }
    dic = ps.dump(player).data
    dic.pop('password')
    dic['status'] = 'success'
    return dic


@app.route('/api/player/registration/', methods=['POST'])
def do_player_registration():
    if Player.find_by_mobile(request.json['mobile']):
        return err('Mobile already registered', 202)
    pload = request.json
    pload['password'] = Player.generate_hash(pload['password'])
    try:
        data, error = player_schema.load(pload)
        if error:
            return err("bad arguments", 201)
        else:
            db.session.add(data)
            db.session.commit()
        access_token = create_access_token(identity = pload['mobile'], expires_delta=expires)
        refresh_token = create_refresh_token(identity = pload['mobile'], expires_delta=expires)
    except exc.IntegrityError as e:
        db.session.rollback()
        return err("database integrity error", 203)
    else:
        return {
                'status': 'success',
                'message': 'Player {} was created'.format(pload['name']),
                'access_token': access_token,
                'refresh_token': refresh_token,
                'mobile': pload['mobile']
            }

@app.route('/api/player/login/', methods=['POST'])
def do_player_login():
    current_player = Player.find_by_mobile(request.json['mobile'])
    if not current_player:
        return err('Mobile not registered', 201)

    pload = request.json
    if Player.verify_hash(pload['password'], current_player.password):
        access_token = create_access_token(identity = pload['mobile'], expires_delta=expires)
        refresh_token = create_refresh_token(identity = pload['mobile'], expires_delta=expires)
        ps = PlayerSchema(strict=False)
        squer = get_single_query(current_player.id)
        dquer = get_double_query(current_player.id)
        ps.context = {
            "dlos" : get_count(dquer[1]),
            "dwin" : get_count(dquer[0]),
            "plos" : get_count(squer[1]),
            "pwin" : get_count(squer[0])
            }
        dic = ps.dump(current_player).data
        dic['access_token'] = access_token
        dic['refresh_token'] = refresh_token
        dic['status'] = "success"
        dic.pop('password')
        print(dic)
        return dic

    return err('Wrong Credentials', 202)


@app.route('/api/player/logout/access/', methods=['POST'])
@jwt_required
def do_player_logout_access():
    jti = get_raw_jwt()['jti']
    try:
        revoked_token = RevokedTokenModel(jti = jti)
        revoked_token.add()
        return {'status': 'success'}
    except:
        return {'message': 'Something went wrong'}, 500


@app.route('/api/player/logout/refresh/', methods=['POST'])
@jwt_refresh_token_required
def do_player_logout_refresh():
    jti = get_raw_jwt()['jti']
    try:
        revoked_token = RevokedTokenModel(jti = jti)
        revoked_token.add()
        return {'message': 'Refresh token has been revoked'}
    except:
        return {'message': 'Something went wrong'}, 500


@app.route('/api/player/tokenrefresh/', methods=['POST'])
@jwt_refresh_token_required
def post(self):
    current_player = get_jwt_identity()
    access_token = create_access_token(identity = current_player,expires_delta=expires)
    return {'access_token': access_token}
