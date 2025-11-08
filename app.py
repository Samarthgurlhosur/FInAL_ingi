from flask import Flask, request, jsonify, render_template
import sqlite3, qrcode, io, base64, json, uuid, datetime, os

app = Flask(__name__)

# ---------------- DATABASE ----------------
def get_db():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()

    # Teams table with last_updated column
    conn.execute('''CREATE TABLE IF NOT EXISTS teams (
                        team_id TEXT PRIMARY KEY,
                        team_name TEXT NOT NULL,
                        members TEXT NOT NULL,
                        last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )''')

    # Members table
    conn.execute('''CREATE TABLE IF NOT EXISTS members (
                        member_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        team_id TEXT,
                        member_name TEXT,
                        check_in INTEGER DEFAULT 0,
                        check_out INTEGER DEFAULT 0,
                        snacks INTEGER DEFAULT 0,
                        dinner INTEGER DEFAULT 0
                    )''')

    conn.commit()
    conn.close()

init_db()


# ---------------- ROUTES ----------------
@app.route('/')
def home():
    return render_template('index.html')


# ----------- REGISTER TEAM -----------
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        data = request.json
        team_name = data.get('team_name', '').strip()
        members = [m.strip() for m in data.get('members', []) if m.strip()]

        if not team_name or not members:
            return jsonify({'error': 'Missing team name or members'}), 400

        team_id = str(uuid.uuid4())

        conn = get_db()
        conn.execute('INSERT INTO teams (team_id, team_name, members) VALUES (?, ?, ?)',
                     (team_id, team_name, json.dumps(members)))

        for member in members:
            conn.execute('INSERT INTO members (team_id, member_name) VALUES (?, ?)', (team_id, member))
        conn.commit()

        qr_payload = json.dumps({
            "team_id": team_id,
            "team_name": team_name,
            "members": members
        })

        qr = qrcode.QRCode(version=1, box_size=10, border=4)
        qr.add_data(qr_payload)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")

        buf = io.BytesIO()
        img.save(buf, format='PNG')
        qr_b64 = base64.b64encode(buf.getvalue()).decode('utf-8')
        buf.close()

        return jsonify({'team_id': team_id, 'qr': qr_b64})

    return render_template('register.html')


# ----------- COORDINATOR DASHBOARD -----------
@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')


# ----------- FETCH TEAM & MEMBERS -----------
@app.route('/team/<team_id>')
def get_team(team_id):
    conn = get_db()
    cur = conn.execute('SELECT * FROM teams WHERE team_id = ?', (team_id,))
    team = cur.fetchone()

    if not team:
        return jsonify({'error': 'Team not found'})

    cur2 = conn.execute('SELECT * FROM members WHERE team_id = ?', (team_id,))
    members = [dict(row) for row in cur2.fetchall()]

    return jsonify({'team': dict(team), 'members': members})


# ----------- UPDATE MEMBER STATUS -----------
@app.route('/update_members', methods=['POST'])
def update_members():
    data = request.json
    updates = data['members']
    conn = get_db()

    # Update each member’s status
    for member in updates:
        conn.execute('''UPDATE members SET
                        check_in = ?, snacks = ?, dinner = ?, check_out = ?
                        WHERE member_id = ?''',
                     (member['check_in'], member['snacks'],
                      member['dinner'], member['check_out'], member['member_id']))

    # Also update the team's last_updated timestamp
    team_id = conn.execute(
        'SELECT team_id FROM members WHERE member_id = ?', (updates[0]['member_id'],)
    ).fetchone()['team_id']

    conn.execute('UPDATE teams SET last_updated = ? WHERE team_id = ?',
                 (datetime.datetime.now(), team_id))
    conn.commit()

    return jsonify({'status': 'updated'})


# ----------- ADMIN VIEW (Sorted by latest update) -----------
@app.route('/admin')
def admin():
    conn = get_db()
    cur = conn.execute('SELECT * FROM teams ORDER BY datetime(last_updated) DESC')
    teams = [dict(row) for row in cur.fetchall()]

    teams_data = []
    for t in teams:
        cur2 = conn.execute('SELECT * FROM members WHERE team_id = ?', (t['team_id'],))
        members = [dict(row) for row in cur2.fetchall()]
        teams_data.append({'team': t, 'members': members})

    return render_template('admin.html', teams_data=teams_data)


# ----------- RUN APP -----------
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))  # Dynamic port for Render
    app.run(host='0.0.0.0', port=port, debug=True)
