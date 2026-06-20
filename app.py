import os
import random
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
from database import init_db, get_db_connection
from flask import jsonify
from agent import run_example_search_agent

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'change_this_secret_key')


with app.app_context():
    init_db()


def login_required(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access that page.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)

    return wrapped


def get_vocabulary_item(word_id):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute('SELECT * FROM vocabulary WHERE id=%s AND user_id=%s', (word_id, session['user_id']))
            return cur.fetchone()
    except Exception:
        return None
    finally:
        conn.close()


def validate_vocabulary_form(form):
    errors = []
    word = form.get('word', '').strip()
    definition = form.get('definition', '').strip()
    part_of_speech = form.get('part_of_speech', '').strip()
    difficulty = form.get('difficulty', '').strip()

    if not word:
        errors.append('Word is required.')
    if not definition:
        errors.append('Definition is required.')
    if not part_of_speech:
        errors.append('Part of speech is required.')
    if not difficulty:
        errors.append('Difficulty is required.')

    return errors


@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm = request.form.get('confirm')

        if not (username and email and password and confirm):
            flash('Please fill all fields.', 'danger')
            return render_template('register.html')

        if password != confirm:
            flash('Passwords do not match.', 'danger')
            return render_template('register.html')

        password_hash = generate_password_hash(password)
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                sql = 'INSERT INTO users (username, email, password_hash) VALUES (%s, %s, %s)'
                cur.execute(sql, (username, email, password_hash))
            conn.commit()
            flash('Registration successful. Please log in.', 'success')
            return redirect(url_for('login'))
        except Exception as err:
            if 'Duplicate' in str(err) or 'duplicate' in str(err).lower():
                flash('Username or email already exists.', 'danger')
            else:
                flash('An error occurred during registration.', 'danger')
        finally:
            conn.close()

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        if not (email and password):
            flash('Please provide both email and password.', 'danger')
            return render_template('login.html')

        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                cur.execute('SELECT id, password_hash FROM users WHERE email=%s', (email,))
                user = cur.fetchone()
            if user and check_password_hash(user['password_hash'], password):
                session['user_id'] = user['id']
                flash('Logged in successfully.', 'success')
                return redirect(url_for('dashboard'))
            flash('Invalid email or password.', 'danger')
        except Exception:
            flash('Database error during login.', 'danger')
        finally:
            conn.close()

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))


@app.route('/dashboard')
@login_required
def dashboard():
    conn = get_db_connection()
    stats = {
        'total_words': 0,
        'learned_today': 0,
        'words_this_week': 0,
        'review_queue': 0,
        'quiz_accuracy': '87%',
        'learning_streak': 5,
        'telegram_status': 'Disconnected',
        'daily_word': 'serendipity',
        'recent_agent': [],
        'latest_words': [],
        'recent_vocab': [],
    }
    try:
        with conn.cursor() as cur:
            cur.execute('SELECT COUNT(*) as total FROM vocabulary WHERE user_id=%s', (session['user_id'],))
            stats['total_words'] = cur.fetchone().get('total', 0)
            cur.execute('SELECT COUNT(*) as today FROM vocabulary WHERE user_id=%s AND DATE(created_at)=CURDATE()', (session['user_id'],))
            stats['learned_today'] = cur.fetchone().get('today', 0)
            cur.execute('SELECT COUNT(*) as week FROM vocabulary WHERE user_id=%s AND created_at >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)', (session['user_id'],))
            stats['words_this_week'] = cur.fetchone().get('week', 0)
            cur.execute('SELECT COUNT(*) as review FROM review_history WHERE user_id=%s', (session['user_id'],))
            stats['review_queue'] = cur.fetchone().get('review', 0)
            cur.execute('SELECT id, command, status, created_at FROM agent_logs WHERE user_id=%s ORDER BY created_at DESC LIMIT 5', (session['user_id'],))
            stats['recent_agent'] = cur.fetchall()
            cur.execute('SELECT word, created_at FROM vocabulary WHERE user_id=%s ORDER BY created_at DESC LIMIT 5', (session['user_id'],))
            stats['latest_words'] = cur.fetchall()
            cur.execute('SELECT word, updated_at FROM vocabulary WHERE user_id=%s ORDER BY updated_at DESC LIMIT 5', (session['user_id'],))
            stats['recent_vocab'] = cur.fetchall()
    except Exception:
        flash('Could not load dashboard stats.', 'warning')
    finally:
        conn.close()

    return render_template('dashboard.html', stats=stats)


@app.route('/vocabulary', methods=['GET', 'POST'])
@login_required
def vocabulary():
    conn = get_db_connection()
    words = []
    search = request.args.get('search', '').strip()
    difficulty = request.args.get('difficulty', '')
    part_of_speech = request.args.get('part_of_speech', '')
    source_filter = request.args.get('source', '')

    query = 'SELECT * FROM vocabulary WHERE user_id=%s'
    params = [session['user_id']]

    if search:
        query += ' AND ('
        query += 'word LIKE %s OR chinese_meaning LIKE %s OR example_sentence LIKE %s OR source_name LIKE %s'
        params.extend([f'%{search}%'] * 4)
        query += ')'
    if difficulty:
        query += ' AND difficulty=%s'
        params.append(difficulty)
    if part_of_speech:
        query += ' AND part_of_speech=%s'
        params.append(part_of_speech)
    if source_filter:
        if source_filter == 'Other':
            query += ' AND source_name NOT IN (%s, %s, %s, %s)'
            params.extend(['Reuters', 'BBC', 'Guardian', 'NPR'])
        else:
            query += ' AND source_name=%s'
            params.append(source_filter)

    query += ' ORDER BY created_at DESC'

    try:
        with conn.cursor() as cur:
            cur.execute(query, tuple(params))
            words = cur.fetchall()
    except Exception:
        flash('Could not load vocabulary.', 'warning')
    finally:
        conn.close()

    return render_template('vocabulary.html', words=words, search=search, difficulty=difficulty, part_of_speech=part_of_speech, source_filter=source_filter)


@app.route('/vocabulary/add', methods=['GET', 'POST'])
@login_required
def add_vocabulary():
    if request.method == 'POST':
        errors = validate_vocabulary_form(request.form)
        word = request.form.get('word', '').strip()

        if errors:
            for error in errors:
                flash(error, 'danger')
            return render_template('vocabulary_add.html', form=request.form)

        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                cur.execute('SELECT id FROM vocabulary WHERE user_id=%s AND word=%s', (session['user_id'], word))
                exists = cur.fetchone()
                if exists:
                    flash('This word already exists in your vocabulary.', 'danger')
                    return render_template('vocabulary_add.html', form=request.form)

                insert_sql = '''
                    INSERT INTO vocabulary (
                        user_id, word, phonetic, part_of_speech, chinese_meaning, definition,
                        collocations, synonyms, antonyms, example_sentence,
                        chinese_translation, source_name, source_url, difficulty, ai_explanation
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                '''
                cur.execute(insert_sql, (
                    session['user_id'],
                    word,
                    request.form.get('phonetic', '').strip(),
                    request.form.get('part_of_speech', '').strip(),
                    request.form.get('chinese_meaning', '').strip(),
                    request.form.get('definition', '').strip(),
                    request.form.get('collocations', '').strip(),
                    request.form.get('synonyms', '').strip(),
                    request.form.get('antonyms', '').strip(),
                    request.form.get('example_sentence', '').strip(),
                    request.form.get('chinese_translation', '').strip(),
                    request.form.get('source_name', '').strip(),
                    request.form.get('source_url', '').strip(),
                    request.form.get('difficulty', '').strip(),
                    request.form.get('ai_explanation', '').strip(),
                ))
            conn.commit()
            flash('Vocabulary added successfully.', 'success')
            return redirect(url_for('vocabulary'))
        except Exception:
            flash('Unable to save vocabulary at this time.', 'danger')
        finally:
            conn.close()

    return render_template('vocabulary_add.html', form={})


@app.route('/vocabulary/<int:word_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_vocabulary(word_id):
    word = get_vocabulary_item(word_id)
    if not word:
        flash('Vocabulary item not found.', 'warning')
        return redirect(url_for('vocabulary'))

    if request.method == 'POST':
        errors = validate_vocabulary_form(request.form)
        updated_word = request.form.get('word', '').strip()

        if errors:
            for error in errors:
                flash(error, 'danger')
            return render_template('vocabulary_edit.html', form=request.form, word_id=word_id)

        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                cur.execute('SELECT id FROM vocabulary WHERE user_id=%s AND word=%s AND id<>%s', (session['user_id'], updated_word, word_id))
                exists = cur.fetchone()
                if exists:
                    flash('Another vocabulary item with this word already exists.', 'danger')
                    return render_template('vocabulary_edit.html', form=request.form, word_id=word_id)

                update_sql = '''
                    UPDATE vocabulary SET
                        word=%s,
                        phonetic=%s,
                        part_of_speech=%s,
                        chinese_meaning=%s,
                        definition=%s,
                        collocations=%s,
                        synonyms=%s,
                        antonyms=%s,
                        example_sentence=%s,
                        chinese_translation=%s,
                        source_name=%s,
                        source_url=%s,
                        difficulty=%s,
                        ai_explanation=%s
                    WHERE id=%s AND user_id=%s
                '''
                cur.execute(update_sql, (
                    updated_word,
                    request.form.get('phonetic', '').strip(),
                    request.form.get('part_of_speech', '').strip(),
                    request.form.get('chinese_meaning', '').strip(),
                    request.form.get('definition', '').strip(),
                    request.form.get('collocations', '').strip(),
                    request.form.get('synonyms', '').strip(),
                    request.form.get('antonyms', '').strip(),
                    request.form.get('example_sentence', '').strip(),
                    request.form.get('chinese_translation', '').strip(),
                    request.form.get('source_name', '').strip(),
                    request.form.get('source_url', '').strip(),
                    request.form.get('difficulty', '').strip(),
                    request.form.get('ai_explanation', '').strip(),
                    word_id,
                    session['user_id'],
                ))
            conn.commit()
            flash('Vocabulary updated successfully.', 'success')
            return redirect(url_for('word_detail', word_id=word_id))
        except Exception:
            flash('Unable to update vocabulary at this time.', 'danger')
        finally:
            conn.close()

    return render_template('vocabulary_edit.html', form=word, word_id=word_id)


@app.route('/vocabulary/<int:word_id>/delete', methods=['POST'])
@login_required
def delete_vocabulary(word_id):
    word = get_vocabulary_item(word_id)
    if not word:
        flash('Vocabulary item not found.', 'warning')
        return redirect(url_for('vocabulary'))

    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute('DELETE FROM vocabulary WHERE id=%s AND user_id=%s', (word_id, session['user_id']))
        conn.commit()
        flash('Vocabulary deleted successfully.', 'success')
    except Exception:
        flash('Unable to delete vocabulary at this time.', 'danger')
    finally:
        conn.close()

    return redirect(url_for('vocabulary'))


@app.route('/vocabulary/<int:word_id>')
@login_required
def word_detail(word_id):
    conn = get_db_connection()
    word = None
    try:
        with conn.cursor() as cur:
            cur.execute('SELECT * FROM vocabulary WHERE id=%s AND user_id=%s', (word_id, session['user_id']))
            word = cur.fetchone()
    except Exception:
        flash('Could not load word details.', 'warning')
    finally:
        conn.close()

    return render_template('word_detail.html', word=word)


@app.route('/search_agent', methods=['GET', 'POST'])
@login_required
def search_agent():
    # Render the search agent page; agent is invoked via AJAX POST to /search-agent/run
    return render_template('search_agent.html')


@app.route('/search-agent/run', methods=['POST'])
@login_required
def run_search_agent():
    command = request.form.get('command') or (request.json and request.json.get('command'))
    if not command:
        return jsonify({'success': False, 'error': 'Empty command'}), 400

    try:
        result = run_example_search_agent(session['user_id'], command)
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'error': 'Agent runtime error', 'details': str(e)}), 500
@app.route('/telegram-agent/run', methods=['POST'])
def telegram_agent_run():
    data = request.get_json() or {}
    command = data.get('command', '').strip()

    user_id = int(os.getenv('TELEGRAM_AGENT_USER_ID', '1'))

    if not command:
        return jsonify({
            'success': False,
            'error': 'Please enter a word.'
        }), 400

    try:
        # query word
        if command.lower().startswith("query "):
            word_to_find = command[6:].strip()

            conn = get_db_connection()
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT word, chinese_meaning, pinyin, phonetic, example_sentence
                    FROM vocabulary
                    WHERE user_id=%s AND LOWER(word)=LOWER(%s)
                    LIMIT 1
                """, (user_id, word_to_find))
                row = cur.fetchone()
            conn.close()

            if not row:
                return jsonify({
                    "success": False,
                    "error": "Word not found in vocabulary."
                })

            return jsonify({
                "success": True,
                "mode": "query",
                "word": row["word"],
                "chinese_meaning": row["chinese_meaning"],
                "pinyin": row["pinyin"],
                "phonetic": row["phonetic"],
                "example_sentence": row["example_sentence"]
            })

        # review command
        if command.lower() == "review":
            conn = get_db_connection()
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT word, chinese_meaning, pinyin, phonetic
                    FROM vocabulary
                    WHERE user_id=%s
                    ORDER BY RAND()
                    LIMIT 1
                """, (user_id,))
                row = cur.fetchone()
            conn.close()

            if not row:
                return jsonify({
                    "success": False,
                    "error": "No vocabulary available."
                })

            return jsonify({
                "success": True,
                "mode": "review",
                "word": row["word"],
                "chinese_meaning": row["chinese_meaning"],
                "pinyin": row["pinyin"],
                "phonetic": row["phonetic"]
            })

        # quiz command
        if command.lower() == "quiz":
            conn = get_db_connection()
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT word, chinese_meaning, pinyin
                    FROM vocabulary
                    WHERE user_id=%s
                    ORDER BY RAND()
                    LIMIT 1
                """, (user_id,))
                question = cur.fetchone()

                cur.execute("""
                    SELECT word
                    FROM vocabulary
                    WHERE user_id=%s AND word != %s
                    ORDER BY RAND()
                    LIMIT 3
                """, (user_id, question["word"] if question else ""))

                wrong_options = cur.fetchall()

            conn.close()

            if not question:
                return jsonify({
                    "success": False,
                    "error": "No vocabulary available for quiz."
                })

            options = [question["word"]] + [item["word"] for item in wrong_options]

            return jsonify({
                "success": True,
                "mode": "quiz",
                "meaning": question["chinese_meaning"],
                "pinyin": question["pinyin"],
                "correct_answer": question["word"],
                "options": options
            })

        # add word
        result = run_example_search_agent(user_id, command)
        return jsonify(result)

    except Exception as e:
        return jsonify({
            'success': False,
            'error': 'Telegram agent runtime error',
            'details': str(e)
        }), 500

@app.route('/review', methods=['GET', 'POST'])
@login_required
def review():
    message = None

    if request.method == 'POST':
        word_id = request.form.get('word_id')
        result = request.form.get('result')

        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO review_history (user_id, vocabulary_id, result)
                VALUES (%s, %s, %s)
            """, (session['user_id'], word_id, result))

            cur.execute("""
                UPDATE vocabulary
                SET review_count = review_count + 1
                WHERE id = %s AND user_id = %s
            """, (word_id, session['user_id']))

        conn.commit()
        conn.close()

        if result == "remembered":
            message = "Saved: You remembered this word."
        else:
            message = "Saved: You need to review this word again."

    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute("""
            SELECT id, word, chinese_meaning, pinyin, definition, example_sentence
            FROM vocabulary
            WHERE user_id = %s
            ORDER BY RAND()
            LIMIT 1
        """, (session['user_id'],))
        word = cur.fetchone()
    conn.close()

    return render_template('review.html', word=word, message=message)


@app.route('/quiz', methods=['GET', 'POST'])
@login_required
def quiz():
    result = None
    correct_answer = None

    if request.method == 'POST':
        user_answer = request.form.get('answer')
        correct_answer = request.form.get('correct_answer')
        meaning = request.form.get('meaning')
        options = request.form.getlist('options')

        if user_answer == correct_answer:
            result = "correct"
        else:
            result = "wrong"

        return render_template(
            'quiz.html',
            result=result,
            correct_answer=correct_answer,
            meaning=meaning,
            options=options
        )

    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute("""
            SELECT word, chinese_meaning, pinyin
            FROM vocabulary
            WHERE user_id=%s AND chinese_meaning IS NOT NULL AND chinese_meaning != ''
            ORDER BY RAND()
            LIMIT 4
        """, (session['user_id'],))
        words = cur.fetchall()
    conn.close()

    if len(words) < 4:
        return render_template('quiz.html', error="Add at least 4 vocabulary words first.")

    correct = random.choice(words)

    return render_template(
        'quiz.html',
        correct_answer=correct['word'],
        meaning=correct['chinese_meaning'],
        pinyin=correct['pinyin'],
        options=[w['word'] for w in words]
    )


@app.route('/statistics')
@login_required
def statistics():
    conn = get_db_connection()
    stats = {
        'total_words': 0,
        'words_by_difficulty': [],
        'words_by_source': [],
        'newest_words': [],
        'oldest_words': [],
        'total_reviews': 0,
        'correct_reviews': 0,
        'accuracy': '0%',
    }
    try:
        with conn.cursor() as cur:
            cur.execute('SELECT COUNT(*) as total FROM vocabulary WHERE user_id=%s', (session['user_id'],))
            stats['total_words'] = cur.fetchone().get('total', 0)
            cur.execute('SELECT difficulty, COUNT(*) as count FROM vocabulary WHERE user_id=%s GROUP BY difficulty ORDER BY FIELD(difficulty, "Beginner", "Intermediate", "Advanced")', (session['user_id'],))
            stats['words_by_difficulty'] = cur.fetchall()
            cur.execute('SELECT source_name, COUNT(*) as count FROM vocabulary WHERE user_id=%s GROUP BY source_name ORDER BY count DESC', (session['user_id'],))
            stats['words_by_source'] = cur.fetchall()
            cur.execute('SELECT word, created_at FROM vocabulary WHERE user_id=%s ORDER BY created_at DESC LIMIT 5', (session['user_id'],))
            stats['newest_words'] = cur.fetchall()
            cur.execute('SELECT word, created_at FROM vocabulary WHERE user_id=%s ORDER BY created_at ASC LIMIT 5', (session['user_id'],))
            stats['oldest_words'] = cur.fetchall()
            cur.execute('SELECT COUNT(*) as reviews FROM review_history WHERE user_id=%s', (session['user_id'],))
            stats['total_reviews'] = cur.fetchone().get('reviews', 0)
            cur.execute("SELECT COUNT(*) as correct FROM review_history WHERE user_id=%s AND result='remembered'", (session['user_id'],))
            stats['correct_reviews'] = cur.fetchone().get('correct', 0)
            if stats['total_reviews'] > 0:
                accuracy = (stats['correct_reviews'] / stats['total_reviews']) * 100
                stats['accuracy'] = f"{int(accuracy)}%"
    except Exception:
        flash('Could not load statistics.', 'warning')
    finally:
        conn.close()

    return render_template('statistics.html', stats=stats)


@app.route('/sources')
@login_required
def sources():
    conn = get_db_connection()
    rows = []
    try:
        with conn.cursor() as cur:
            cur.execute('SELECT source_name, source_url, word, created_at FROM sources ORDER BY source_name ASC, created_at DESC')
            rows = cur.fetchall()
    except Exception:
        flash('Could not load sources.', 'warning')
    finally:
        conn.close()

    return render_template('sources.html', sources=rows)


@app.route('/settings')
@login_required
def settings():
    conn = get_db_connection()
    user = {}
    try:
        with conn.cursor() as cur:
            cur.execute('SELECT id, username, email, role, created_at FROM users WHERE id=%s', (session['user_id'],))
            user = cur.fetchone()
    except Exception:
        flash('Could not load settings.', 'warning')
    finally:
        conn.close()

    return render_template('settings.html', user=user)


if __name__ == '__main__':
    app.run(debug=True)
