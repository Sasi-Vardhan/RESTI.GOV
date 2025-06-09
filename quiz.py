from flask import Blueprint, render_template, request, redirect, url_for, session
import csv
import os
import logging
from deep_translator import GoogleTranslator
from concurrent.futures import ThreadPoolExecutor, as_completed

quiz_bp = Blueprint('quiz', __name__, template_folder='templates')

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Skill names mapping
SKILL_NAMES = {
    'poultry': 'Poultry Farming',
    'mushroom': 'Mushroom Cultivation',
    'mobile_repair': 'Mobile Repair'
}

# CSV files mapping
csv_files = {
    'poultry': 'data/poultry_quiz.csv',
    'mushroom': 'data/mushroom_quiz.csv',
    'mobile_repair': 'data/mobile_repair_quiz.csv'
}

LANGUAGES = {
    'english': {'code': 'en', 'name': 'English', 'native': 'English'},
    'hindi': {'code': 'hi', 'name': 'Hindi', 'native': 'हिंदी'},
    'tamil': {'code': 'ta', 'name': 'Tamil', 'native': 'தமிழ்'},
    'telugu': {'code': 'te', 'name': 'Telugu', 'native': 'తెలుగు'}
}

@quiz_bp.before_request
def clear_session_on_navigation():
    exempt_endpoints = {'quiz.quiz', 'static', 'forms.reg'}
    if request.endpoint and request.endpoint not in exempt_endpoints:
        session.clear()
        # logger.info("Cleared session on navigation")

def translate_field(field, text, target_lang_code):
    """Translate a single text field to the target language."""
    try:
        if text and target_lang_code != 'en':
            # logger.debug(f"Translating {field}: {text} to {target_lang_code}")
            translated_text = GoogleTranslator(source='en', target=target_lang_code).translate(text)
            return field, translated_text
        return field, text
    except Exception as e:
        # logger.error(f"Translation error for {field}: {text} to {target_lang_code}: {e}")
        return field, text

def translator(questions):
    """Translate all fields of all questions using multithreading."""
    if 'language' not in session or session['language'] not in LANGUAGES:
        # logger.warning(f"No valid language in session, defaulting to English. Session: {session}")
        session['language'] = 'english'
        target_lang_code = 'en'
    else:
        target_lang = LANGUAGES[session['language']]
        target_lang_code = target_lang['code']

    translated_questions = []
    fields_to_translate = ['question', 'option1', 'option2', 'option3', 'option4', 'correct_answer', 'explanation']

    for question_data in questions:
        translated_data = question_data.copy()
        with ThreadPoolExecutor(max_workers=15) as executor:
            futures = [
                executor.submit(translate_field, field, translated_data[field], target_lang_code)
                for field in fields_to_translate if field in translated_data and translated_data[field]
            ]
            for future in as_completed(futures):
                try:
                    field, translated_text = future.result()
                    translated_data[field] = translated_text
                    # logger.debug(f"Translated {field}: {translated_text}")
                except Exception as e:
                    # logger.error(f"Failed to retrieve translation for {field}: {e}")
        translated_questions.append(translated_data)
    return translated_questions

def load_quiz_data(skill):
    """Load quiz questions from the corresponding CSV file and translate them if not cached."""
    if skill not in csv_files:
        # logger.error(f"Invalid skill: {skill}")
        return None
    file_path = csv_files[skill]
    logger.info(f"Resolved CSV file path: {os.path.abspath(file_path)}")
    if not os.path.exists(file_path):
        # logger.error(f"CSV file not found: {file_path}")
        return None

    if 'translated_questions' in session and session.get('current_skill') == skill:
        # logger.info("Using cached translated questions")
        return session['translated_questions']

    questions = []
    try:
        with open(file_path, newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                options = row['Options'].split(';')
                if len(options) != 4:
                    # logger.warning(f"Skipping malformed row in {file_path}: {row}")
                    continue
                question_data = {
                    'question': row['Question'].strip(),
                    'option1': options[0].strip(),
                    'option2': options[1].strip(),
                    'option3': options[2].strip(),
                    'option4': options[2].strip(),  # Fixed: Was using option2 twice
                    'correct_answer': row['Correct Answer'].strip(),
                    'explanation': row['Explanation Why Correct Answer is Good'].strip()
                }
                questions.append(question_data)
                # logger.debug(f"Loaded question: {question_data}")
    except Exception as e:
        # logger.error(f"Error reading CSV {file_path}: {e}")
        return None

    if not questions:
        return None

    logger.info("Translating all questions...")
    translated_questions = translator(questions)

    session['translated_questions'] = translated_questions
    session['current_skill'] = skill
    session.modified = True
    logger.info("Translation complete, cached questions in session")

    return translated_questions

@quiz_bp.route('/quiz', methods=['GET', 'POST'])
def quiz():
    if 'selected_skill' not in session or session['selected_skill'] not in SKILL_NAMES:
        logger.info("No selected skill in session, redirecting to index")
        session.clear()
        return redirect(url_for('index'))

    skill = session['selected_skill']
    skill_name = SKILL_NAMES[skill]

    # Check if translation is in progress
    if 'translated_questions' not in session or session.get('current_skill') != skill:
        questions = load_quiz_data(skill)
        return render_template('loading.html')

    questions = session['translated_questions']

    if not questions:
        session.clear()
        return render_template('error.html', message=f"No quiz found for {skill_name}")

    if 'current_question' not in session:
        session['current_question'] = 0
        session['score'] = session.get('score', 0)
        session['total_questions'] = len(questions)
        session['answered'] = False
        session['feedback'] = ''
        session['correct_answer'] = ''
        session['explanation'] = ''
        session.modified = True
        logger.info(f"Initialized session for quiz: {session}")

    current_question_index = session['current_question']
    logger.debug(f"Current session state: {session}")

    if request.method == 'POST':
        logger.info(f"Received POST request: {request.form}")
        if 'answer' in request.form:
            user_answer = request.form.get('answer', '').strip()
            if not user_answer:
                logger.warning("No answer provided in form submission")
            correct_answer = questions[current_question_index]['correct_answer']
            session['answered'] = True
            if user_answer == correct_answer:
                session['score'] = session.get('score', 0) + 1
                session['feedback'] = 'Correct!'
                logger.info(f"Correct answer for question {current_question_index + 1} in {skill}")
            else:
                session['feedback'] = 'Incorrect!'
                logger.info(f"Incorrect answer for question {current_question_index + 1} in {skill}")
            session['correct_answer'] = correct_answer
            session['explanation'] = questions[current_question_index]['explanation']
        elif 'next' in request.form:
            session['current_question'] += 1
            session['answered'] = False
            session['feedback'] = ''
            session['correct_answer'] = ''
            session['explanation'] = ''
            logger.info(f"Moving to question {session['current_question'] + 1}")
            if session['current_question'] >= session['total_questions']:
                logger.info(f"Quiz completed for {skill}, score: {session['score']}")
                return redirect(url_for('forms.reg'))
        session.modified = True
        # logger.debug(f"Session after POST: {session}")
        return redirect(url_for('quiz.quiz'))

    if current_question_index < session['total_questions']:
        question_data = questions[current_question_index]
        # logger.debug(f"Rendering question {current_question_index + 1}: {question_data}")
        return render_template(
            'quiz.html',
            question=question_data,
            question_number=current_question_index + 1,
            total_questions=session['total_questions'],
            skill_name=skill_name,
            answered=session['answered'],
            feedback=session['feedback'],
            correct_answer=session['correct_answer'],
            explanation=session['explanation'],
            language=session.get("language", "english")
        )

    session.clear()
    return redirect(url_for('forms.reg'))

@quiz_bp.route('/index')
def index():
    """Main page, clears all session variables."""
    session.clear()
    logger.info("Cleared all session variables on index access")
    return render_template('index.html', skills=SKILL_NAMES)
