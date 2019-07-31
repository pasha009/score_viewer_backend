from app import app, db, routes
from app.models import Player, SingleMatch

@app.shell_context_processor
def make_shell_context():
    return {'db': db, 'Player': Player, 'Match': SingleMatch}

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
