from app.serializers import PlayerSchema, SingleMatchSchema, DoubleMatchSchema, SimplePlayerSchema, DoubleSummarySchema, SingleSummarySchema, AnnouncementSchema, AnnouncementListSchema
from app.models import Player, SingleMatch, DoubleMatch, Announcements
from app import app, db
from flask import request, jsonify, send_from_directory
from sqlalchemy import exc, or_
from dateutil.parser import parse
from flask_jwt_extended import jwt_required
import os, glob

from pathlib import Path
sfd = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'static')

def get_count(q):
    count_q = q.statement.with_only_columns([db.func.count()]).order_by(None)
    count = q.session.execute(count_q).scalar()
    return count

def err(msg):
    return jsonify({"status":"failure", "error": msg}), 201

@app.errorhandler(404)
def page_not_found(error):
    if "image" in str(request.path):
        return send_from_directory(sfd, 'default.jpeg'), 200
    return jsonify({"status":"failure", "error": "object not found", "path":request.path}), 404

###################################################################################
################################ Announcement APIs ################################
###################################################################################

anns = AnnouncementSchema(strict=False)

@app.route('/api/announcement/list/', methods=['GET'])
def get_announcement_list():
    simple_announcement_schema = AnnouncementListSchema(many=True, strict=False)
    all_announcements = Announcements.query.with_entities(Announcements.id, Announcements.timestamp, Announcements.title).all()
    all_announcements.sort(key=lambda item: item.timestamp, reverse=True)
    return jsonify(simple_announcement_schema.dump(all_announcements).data)

@app.route('/api/announcement/get/<id>', methods=['GET'])
def get_announcement(id):
    announcement = Announcements.query.get_or_404(id)
    return jsonify(anns.dump(announcement).data)

@app.route('/api/announcement/post/', methods=['POST'])
def post_announcement():
    try:
        data, err = anns.load(request.json)
        if err:
            return err
        else:
            db.session.add(data)
            db.session.commit()
    except exc.IntegrityError as e:
        db.session.rollback()
        return err("database integrity error")
    else:
        return {
            "status": "success"
        }

@app.route('/api/announcement/put/<id>', methods=['PUT'])
@jwt_required
def update_announcement(id):
    p = Announcements.query.get_or_404(id)
    fr = dict(filter(lambda e: e[0] in ['timestamp', 'title', 'description'], request.json.items()))
    for key, value in fr.items():
        if value != getattr(p, key):
            setattr(p, key, value)
    db.session.commit()
    return get_announcement(id)

@app.route('/api/announcement/delete/<id>', methods=['DELETE'])
@jwt_required
def delete_announcement(id):
    a = Announcements.query.get_or_404(id)
    db.session.delete(a)
    db.session.commit()
    return {
        "status": "success"
    }

###################################################################################
################################ Player APIs ######################################
###################################################################################

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

@app.route('/api/player/image/get/<id>', methods=['GET'])
def get_player_image(id):
    try:
        filename = glob.glob(os.path.join(app.config['UPLOAD_FOLDER'], str(id) + '*'))[0]
        filename = os.path.basename(filename)
        return send_from_directory(sfd, filename)
    except Exception as e:
        print(e)
        return send_from_directory(sfd, 'default.jpeg')


@app.route('/api/player/image/post/', methods = ['POST'])
def post_player_image():
    if request.files['image']:
        img = request.files['image']
        ext = os.path.splitext(img.filename)[1]
        img_name = request.form['id'] + ext
        saved_path = os.path.join(app.config['UPLOAD_FOLDER'], img_name)
        for filename in glob.glob(os.path.join(app.config['UPLOAD_FOLDER'], request.form['id'] + '*')):
            os.remove(filename)
        img.save(saved_path)
        return {"status": "success"}
    else:
        return {"status": "error"}


@app.route('/api/player/list/', methods=['GET'])
def get_player_list():
    simple_player_schema = SimplePlayerSchema(many=True, strict=False)
    all_players = Player.query.all()
    return jsonify(simple_player_schema.dump(all_players).data)

@app.route('/api/player/get/<id>', methods=['GET'])
def get_player(id):
    ps = PlayerSchema(strict=False)
    squer = get_single_query(id)
    dquer = get_double_query(id)
    ps.context = {
        "dlos" : get_count(dquer[1]),
        "dwin" : get_count(dquer[0]),
        "plos" : get_count(squer[1]),
        "pwin" : get_count(squer[0])
        }
    player = Player.query.get_or_404(id)
    return jsonify(ps.dump(player).data)

@app.route('/api/player/post/', methods=['POST'])
def post_player():
    single_player_schema = SimplePlayerSchema(strict=False)
    player_schema = PlayerSchema(strict=False)
    try:
        data, err = player_schema.load(request.json)
        if err:
            return err
        else:
            db.session.add(data)
            db.session.commit()
    except exc.IntegrityError as e:
        db.session.rollback()
        return err("database integrity error")
    else:
        return jsonify(single_player_schema.dump(data).data)

@app.route('/api/player/put/<id>', methods=['PUT'])
@jwt_required
def update_player(id):
    p = Player.query.get_or_404(id)
    fr = dict(filter(lambda e: e[0] in ['name', 'mobile', 'dob', 'rollno', 'type'], request.json.items()))
    for key, value in fr.items():
        if value != getattr(p, key):
            if key == 'dob':
                setattr(p, key, parse(value))
                continue
            setattr(p, key, value)
    db.session.commit()
    return {"status" : "success"}

@app.route('/api/player/delete/<id>', methods=['DELETE'])
@jwt_required
def delete_player(id):
    id = int(id)
    p = Player.query.get_or_404(id)
    squer = get_single_query(id)
    dquer = get_double_query(id)
    dsw = squer[0].delete(synchronize_session=False)
    dsl = squer[1].delete(synchronize_session=False)
    ddw = dquer[0].delete(synchronize_session=False)
    ddl = dquer[1].delete(synchronize_session=False)
    db.session.delete(p)
    db.session.commit()
    return get_player_list()

###################################################################################
################################ SingleMatch APIs #################################
###################################################################################

singlematch_schema = SingleMatchSchema(strict=False)
singlematches_schema = SingleMatchSchema(many=True, strict=False)

@app.route('/api/singlematch/list/', methods=['GET'])
def get_all_singlematches():
    singlematch_schema = SingleMatchSchema(strict=False)
    s = SingleMatch.query.order_by(SingleMatch.date).all()
    return jsonify(singlematches_schema.dump(s).data)


@app.route('/api/singlematch/list/bymatch/<pid>', methods=['GET'])
def get_singlematch_list_match(pid):
    s = SingleMatch.query.filter(or_(SingleMatch.winner_id == pid, SingleMatch.loser_id == pid))
    singlematchex_schema = SingleSummarySchema(many=True, strict=False)
    singlematchex_schema.context = { "player_id" : pid }
    return jsonify(singlematchex_schema.dump(s).data)

@app.route('/api/singlematch/list/byplayers/', methods=['GET'])
def get_player_by_singlematch():
    w = db.session.query(SingleMatch.winner_id,  SingleMatch.loser_id, db.func.count(SingleMatch.id)).group_by(SingleMatch.winner_id).all()
    l = db.session.query(SingleMatch.winner_id,  SingleMatch.loser_id, db.func.count(SingleMatch.id)).group_by(SingleMatch.loser_id).all()
    mdict = {}
    for match in w:
        mdict[match[0]] = [match[2], 0]
    for match in l:
        val = mdict.setdefault(match[1], [0, 0])
        mdict[match[1]] = list(map(sum, zip(val, [0, match[2]])))
    simple_player_schema = SimplePlayerSchema(strict=False)
    mlist = []
    for key, value in mdict.items():
        p = simple_player_schema.dump(Player.query.get_or_404(int(key))).data
        mlist.append({
            "player": p,
            "wins": value[0],
            "loss": value[1]
        })
    mlist.sort(key=lambda item: (item["wins"]/(item["loss"] + 1), item["wins"]), reverse=True)
    return jsonify(mlist)

@app.route('/api/singlematch/list/byopponent/<pid>', methods=['GET'])
def get_singlematch_list_opponent(pid):
    pid = int(pid)
    q = db.session.query(SingleMatch.winner_id, SingleMatch.loser_id, db.func.count(SingleMatch.id)).filter(or_(SingleMatch.winner_id == pid, SingleMatch.loser_id == pid)).group_by(SingleMatch.winner_id, SingleMatch.loser_id).all()
    ret = {}
    for i in q:
        if i[0] == pid:
            ind = 0
            opponent_id = i[1]
        else:
            ind = 1
            opponent_id = i[0]
        opponent = Player.query.filter(Player.id == opponent_id).first().name
        lis = [0, 0]
        lis[ind] = i[2]
        cur = ret.setdefault(opponent, [0, 0])
        ret[opponent] = list(map(sum, zip(cur, lis)))
    ret = [{"opponent": k, "win":v[0], "loss":v[1]} for k, v in ret.items()]
    return jsonify(ret)
    # singlematchex_schema = SingleSummarySchema(many=True, strict=False)
    # singlematchex_schema.context = { "player_id" : pid , "summary" : q}
    # return jsonify(singlematchex_schema.dump(s).data)


@app.route('/api/singlematch/post/', methods=['POST'])
def post_singlematch():
    sdata, errors = singlematch_schema.load(request.json)
    if errors:
        return err(errors)
    db.session.add(sdata)
    print(sdata)
    try:
        db.session.commit()
    except exc.IntegrityError as e:
        db.session.rollback()
        return err("database integrity error")
    else:
        return jsonify(singlematch_schema.dump(sdata).data)


@app.route('/api/singlematch/put/<id>', methods=['PUT'])
def update_singlematch(id):
    s = SingleMatch.query.get_or_404(id)
    fr = dict(filter(lambda e: e[0] in ['date', 'winner_id', 'loser_id'], request.json.items()))
    for key, value in fr.items():
        if value != getattr(s, key):
            setattr(s, key, value)
    try:
        db.session.commit()
    except exc.IntegrityError as e:
        db.session.rollback()
        return err("database integrity error")
    else:
        return jsonify(singlematch_schema.dump(s).data)

@app.route('/api/singlematch/delete/<id>', methods=['DELETE'])
def delete_singlematch(id):
    s = SingleMatch.query.get_or_404(id)
    db.session.delete(s)
    db.session.commit()
    return get_all_singlematches()

###################################################################################
################################ DoubleMatch APIs #################################
###################################################################################

doublematch_schema = DoubleMatchSchema(strict=False)


@app.route('/api/doublematch/list/', methods=['GET'])
def get_all_doublematches():
    doublematches_schema = DoubleMatchSchema(many=True, strict=False)
    s = DoubleMatch.query.order_by(DoubleMatch.date).all()
    return jsonify(doublematches_schema.dump(s).data)

@app.route('/api/doublematch/list/bymatch/<pid>', methods=['GET'])
def get_doublematch_list_match(pid):
    s = DoubleMatch.query.filter(or_(DoubleMatch.winner1_id == pid, DoubleMatch.loser1_id == pid, DoubleMatch.winner2_id == pid, DoubleMatch.loser2_id == pid)).order_by(DoubleMatch.date.desc()).all()
    doublematchex_schema = DoubleSummarySchema(many=True, strict=False)
    doublematchex_schema.context = { "player_id" : pid }
    return jsonify(doublematchex_schema.dump(s).data)


@app.route('/api/doublematch/list/bypartner/<pid>', methods=['GET'])
def get_doublematch_list_partner(pid):
    pid = int(pid)
    q = db.session.query(DoubleMatch.winner1_id, DoubleMatch.winner2_id, DoubleMatch.loser1_id, DoubleMatch.loser2_id, db.func.count(DoubleMatch.id)).filter(or_(DoubleMatch.winner1_id == pid, DoubleMatch.loser1_id == pid, DoubleMatch.winner2_id == pid, DoubleMatch.loser2_id == pid)).group_by(DoubleMatch.winner1_id, DoubleMatch.winner2_id, DoubleMatch.loser1_id).all()
    ret, vet = {}, {}
    for i in q:
        mp = {
            i[0] : [0, i[1]],
            i[1] : [0, i[0]],
            i[2] : [1, i[3]],
            i[3] : [1, i[2]],
        }
        ind = mp[pid][0]
        partner_id = mp[pid][1]
        partner = Player.query.get_or_404(partner_id).name
        lis = [0, 0]
        lis[ind] = i[4]
        cur = ret.setdefault(partner, [0, 0])
        ret[partner] = list(map(sum, zip(cur, lis)))
        vet[partner] = partner_id
    ret = [ {"partner": k, "win": v[0], "loss": v[1], "self": "/api/player/get/" + str(vet[k])} for k, v in ret.items()]
    return jsonify(ret)


@app.route('/api/doublematch/post/', methods=['POST'])
def post_doublematch():
    sdata, errors = doublematch_schema.load(request.json)
    if errors:
        print(errors)
        return err(errors)
    db.session.add(sdata)
    try:
        db.session.commit()
    except exc.IntegrityError as e:
        db.session.rollback()
        return err("database integrity error")
    else:
        return jsonify(doublematch_schema.dump(sdata).data)


@app.route('/api/doublematch/put/<id>', methods=['PUT'])
def update_doublematch(id):
    s = DoubleMatch.query.get_or_404(id)
    fr = dict(filter(lambda e: e[0] in ['date', 'winner1_id', 'loser1_id', 'winner2_id', 'loser2_id'], request.json.items()))
    for key, value in fr.items():
        if value != getattr(s, key):
            if key == "date":
                setattr(s, key, parse(value))
                continue
            setattr(s, key, value)
    try:
        db.session.commit()
    except exc.IntegrityError as e:
        db.session.rollback()
        return err("database integrity error")
    else:
        return jsonify(doublematch_schema.dump(s).data)

@app.route('/api/doublematch/delete/<id>', methods=['DELETE'])
def delete_doublematch(id):
    s = DoubleMatch.query.get_or_404(id)
    db.session.delete(s)
    db.session.commit()
    return get_all_doublematches()

###################################################################################
################################ DoublePair APIs ##################################
###################################################################################

@app.route('/api/doublepair/list/', methods=['GET'])
def get_all_doublepair():
    doublematches_schema = DoubleMatchSchema(many=True, strict=False)
    w = db.session.query(DoubleMatch.winner1_id, DoubleMatch.winner2_id, DoubleMatch.loser1_id, DoubleMatch.loser2_id, db.func.count(DoubleMatch.id)).group_by(DoubleMatch.winner1_id, DoubleMatch.winner2_id).all()
    l = db.session.query(DoubleMatch.winner1_id, DoubleMatch.winner2_id, DoubleMatch.loser1_id, DoubleMatch.loser2_id, db.func.count(DoubleMatch.id)).group_by(DoubleMatch.loser1_id, DoubleMatch.loser1_id).all()
    import itertools
    key_w = lambda x: '-'.join(sorted([str(x[0]), str(x[1])]))
    key_l = lambda x: '-'.join(sorted([str(x[2]), str(x[3])]))

    main = {}
    for key, group in itertools.groupby(w, key_w):
        ml = list(group)
        twins = 0
        for match in ml:
            twins += match[4]
        main[key] = [twins, 0]

    for key, group in itertools.groupby(l, key_l):
        ml = list(group)
        tloss = 0
        for match in ml:
            tloss += match[4]
        val = main.setdefault(key, [0, 0])
        main[key] = list(map(sum, zip(val, [0, tloss])))

    simple_player_schema = SimplePlayerSchema(strict=False)
    mlist = []
    for key, value in main.items():
        w = key.split('-')
        p1 = simple_player_schema.dump(Player.query.get_or_404(int(w[0]))).data
        p2 = simple_player_schema.dump(Player.query.get_or_404(int(w[1]))).data
        mlist.append({
            "player1" : p1,
            "player2" : p2,
            "wins" : value[0],
            "loss" : value[1],
        })

    mlist.sort(key=lambda item: (item["wins"]/(item["loss"] + 1), item["wins"]), reverse=True)
    return jsonify(mlist)

# @app.route('/api/doublematch/list/bymatch/<pid>', methods=['GET'])
# def get_doublematch_list_match(pid):
#     s = DoubleMatch.query.filter(or_(DoubleMatch.winner1_id == pid, DoubleMatch.loser1_id == pid, DoubleMatch.winner2_id == pid, DoubleMatch.loser2_id == pid))
#     doublematchex_schema = DoubleSummarySchema(many=True, strict=False)
#     doublematchex_schema.context = { "player_id" : pid }
#     return jsonify(doublematchex_schema.dump(s).data)
#
#
# @app.route('/api/doublematch/list/bypartner/<pid>', methods=['GET'])
# def get_doublematch_list_partner(pid):
#     pid = int(pid)
#     q = db.session.query(DoubleMatch.winner1_id, DoubleMatch.winner2_id, DoubleMatch.loser1_id, DoubleMatch.loser2_id, db.func.count(DoubleMatch.id)).filter(or_(DoubleMatch.winner1_id == pid, DoubleMatch.loser1_id == pid, DoubleMatch.winner2_id == pid, DoubleMatch.loser2_id == pid)).group_by(DoubleMatch.winner1_id, DoubleMatch.winner2_id, DoubleMatch.loser1_id).all()
#     ret = {}
#     for i in q:
#         mp = {
#             i[0] : [0, i[1]],
#             i[1] : [0, i[0]],
#             i[2] : [1, i[3]],
#             i[3] : [1, i[2]],
#         }
#         ind = mp[pid][0]
#         partner_id = mp[pid][1]
#         partner = Player.query.filter(Player.id == partner_id).first().name
#         lis = [0, 0]
#         lis[ind] = i[4]
#         cur = ret.setdefault(partner, [0, 0])
#         ret[partner] = list(map(sum, zip(cur, lis)))
#     ret = [ {"partner": k, "win": v[0], "loss": v[1]} for k, v in ret.items()]
#     return jsonify(ret)
#
#
# @app.route('/api/doublematch/post/', methods=['POST'])
# def post_doublematch():
#     sdata, errors = doublematch_schema.load(request.json)
#     if errors:
#         print(errors)
#         return err(errors)
#     db.session.add(sdata)
#     try:
#         db.session.commit()
#     except exc.IntegrityError as e:
#         db.session.rollback()
#         return err("database integrity error")
#     else:
#         return jsonify(doublematch_schema.dump(sdata).data)
#
#
# @app.route('/api/doublematch/put/<id>', methods=['PUT'])
# def update_doublematch(id):
#     s = DoubleMatch.query.get_or_404(id)
#     fr = dict(filter(lambda e: e[0] in ['date', 'winner1_id', 'loser1_id', 'winner2_id', 'loser2_id'], request.json.items()))
#     for key, value in fr.items():
#         if value != getattr(s, key):
#             if key == "date":
#                 setattr(s, key, parse(value))
#                 continue
#             setattr(s, key, value)
#     try:
#         db.session.commit()
#     except exc.IntegrityError as e:
#         db.session.rollback()
#         return err("database integrity error")
#     else:
#         return jsonify(doublematch_schema.dump(s).data)
#
# @app.route('/api/doublematch/delete/<id>', methods=['DELETE'])
# def delete_doublematch(id):
#     s = DoubleMatch.query.get_or_404(id)
#     db.session.delete(s)
#     db.session.commit()
#     return get_all_doublematches()
