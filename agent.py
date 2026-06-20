import json
from database import get_db_connection
from search_service import search_word_sources
from llm_service import generate_word_data


def run_example_search_agent(user_id, command):
    steps = []
    command = (command or '').strip()
    steps.append(f'Command received: {command}')

    if not command:
        return {'success': False, 'error': 'Empty command', 'steps': steps}

    target_word = command.strip()

    if not target_word:
        return {
            'success': False,
            'error': 'Please enter a word.',
            'steps': steps
        }

    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute('SELECT id FROM vocabulary WHERE user_id=%s AND word=%s', (user_id, target_word))
            if cur.fetchone():
                steps.append('Duplicate check: word exists')
                # log failure
                log_entry = {
                    'user_id': user_id,
                    'command': command,
                    'target_word': target_word,
                    'status': 'failed',
                    'steps': json.dumps(steps),
                    'result_summary': 'Duplicate word'
                }
                with conn.cursor() as c2:
                    c2.execute('INSERT INTO agent_logs (user_id, command, target_word, status, steps, result_summary) VALUES (%s, %s, %s, %s, %s, %s)',
                               (log_entry['user_id'], log_entry['command'], log_entry['target_word'], log_entry['status'], log_entry['steps'], log_entry['result_summary']))
                    conn.commit()
                return {'success': False, 'error': 'Duplicate word', 'steps': steps}

    except Exception as e:
        return {'success': False, 'error': 'Database error during duplicate check', 'details': str(e), 'steps': steps}

    # Search Tavily for authentic sources
    steps.append('Searching authentic English sources')
    try:
        source = search_word_sources(target_word)
    except Exception as e:
        steps.append(f'Search error: {e}')
        # log
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute('INSERT INTO agent_logs (user_id, command, target_word, status, steps, result_summary) VALUES (%s, %s, %s, %s, %s, %s)',
                        (user_id, command, target_word, 'failed', json.dumps(steps), f'Search error: {e}'))
            conn.commit()
            conn.close()
        return {'success': False, 'error': 'Search service error', 'details': str(e), 'steps': steps}

    if not source:
        steps.append('No authentic source found')
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute('INSERT INTO agent_logs (user_id, command, target_word, status, steps, result_summary) VALUES (%s, %s, %s, %s, %s, %s)',
                        (user_id, command, target_word, 'failed', json.dumps(steps), 'No authentic source found'))
            conn.commit()
            conn.close()
        return {'success': False, 'error': 'No authentic source found for this word.', 'steps': steps}

    steps.append(f"Real source found: {source.get('source_name')} | {source.get('source_url')}")
    example_sentence = source.get('example_sentence')
    steps.append('Extracting example sentence')

    # Generate word data via LLM
    steps.append('Generating vocabulary data with LLM')
    try:
        llm_data = generate_word_data(target_word, example_sentence)
    except Exception as e:
        llm_data = None
        steps.append(f'LLM error: {e}')

    if not llm_data:
        steps.append('LLM failed to return data')
        status = 'failed'
        result_summary = 'LLM failure'
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute('INSERT INTO agent_logs (user_id, command, target_word, status, steps, result_summary) VALUES (%s, %s, %s, %s, %s, %s)',
                        (user_id, command, target_word, status, json.dumps(steps), result_summary))
            conn.commit()
            conn.close()
        return {'success': False, 'error': 'LLM error', 'steps': steps}

    # Prepare final record values
    record = {
        'word': llm_data.get('word') or target_word,
        'phonetic': llm_data.get('phonetic') or '',
        'part_of_speech': llm_data.get('part_of_speech') or '',
        'chinese_meaning': llm_data.get('chinese_meaning') or '',
        'pinyin': llm_data.get('pinyin') or '',
        'definition': llm_data.get('definition') or '',
        'collocations': llm_data.get('collocations') or '',
        'synonyms': llm_data.get('synonyms') or '',
        'antonyms': llm_data.get('antonyms') or '',
        'example_sentence': example_sentence or '',
        'chinese_translation': llm_data.get('chinese_translation') or '',
        'source_name': source.get('source_name'),
        'source_url': source.get('source_url'),
        'difficulty': llm_data.get('difficulty') or '',
        'ai_explanation': llm_data.get('ai_explanation') or '',
    
    }

    # Save vocabulary and source and agent log
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            insert_sql = '''
                INSERT INTO vocabulary (
                    user_id, word, phonetic, part_of_speech, chinese_meaning, definition,
                    collocations, synonyms, antonyms, example_sentence,
                    chinese_translation, source_name, source_url, difficulty, ai_explanation, pinyin
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            '''
            cur.execute(insert_sql, (
                user_id,
                record['word'],
                record['phonetic'],
                record['part_of_speech'],
                record['chinese_meaning'],
                record['definition'],
                record['collocations'],
                record['synonyms'],
                record['antonyms'],
                record['example_sentence'],
                record['chinese_translation'],
                record['source_name'],
                record['source_url'],
                record['difficulty'],
                record['ai_explanation'],
                record['pinyin']
            ))
            vocab_id = cur.lastrowid

            # Save source
            cur.execute('INSERT INTO sources (source_name, source_url, word) VALUES (%s, %s, %s)',
                        (record['source_name'], record['source_url'], record['word']))

            # Save agent log
            steps.append('Saving to MySQL database')
            cur.execute('INSERT INTO agent_logs (user_id, command, target_word, status, steps, result_summary) VALUES (%s, %s, %s, %s, %s, %s)',
                        (user_id, command, target_word, 'success', json.dumps(steps), f"Saved word id {vocab_id}"))
        conn.commit()
        conn.close()
    except Exception as e:
        return {'success': False, 'error': 'Database error saving vocabulary', 'details': str(e), 'steps': steps}

    result = {
        'success': True,
        'word': record['word'],
        'phonetic': record['phonetic'],
        'part_of_speech': record['part_of_speech'],
        'chinese_meaning': record['chinese_meaning'],
        'definition': record['definition'],
        'collocations': record['collocations'],
        'synonyms': record['synonyms'],
        'antonyms': record['antonyms'],
        'example_sentence': record['example_sentence'],
        'chinese_translation': record['chinese_translation'],
        'source_name': record['source_name'],
        'source_url': record['source_url'],
        'difficulty': record['difficulty'],
        'ai_explanation': record['ai_explanation'],
        'pinyin': record['pinyin'],
        'steps': steps,
    }

    return result
