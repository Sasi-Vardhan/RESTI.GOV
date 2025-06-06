from flask import Blueprint, render_template, request, redirect, url_for, session
import csv
import os
import logging
import requests
import re

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

@quiz_bp.before_request
def clear_session_on_navigation():
    # exempt_endpoints = {'feed.registration', 'quiz.quiz', 'quiz.index', 'static'}
    exempt_endpoints={'quiz.quiz', 'static','forms.reg'}
    if request.endpoint and request.endpoint not in exempt_endpoints:
        session.clear()


def load_quiz_data(skill):
    """Load quiz questions from the corresponding CSV file."""
    if skill not in csv_files:
        logger.error(f"Invalid skill: {skill}")
        return None
    file_path = csv_files[skill]
    if not os.path.exists(file_path):
        logger.error(f"CSV file not found: {file_path}")
        return None
    questions = []
    try:
        with open(file_path, newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                options = row['Options'].split(';')
                if len(options) != 4:
                    logger.warning(f"Skipping malformed row in {file_path}: {row}")
                    continue
                question_data = {
                    'question': row['Question'],
                    'option1': options[0],
                    'option2': options[1],
                    'option3': options[2],
                    'option4': options[3],
                    'correct_answer': row['Correct Answer'],
                    'explanation': row['Explanation Why Correct Answer is Good']
                }
                questions.append(question_data)
        # print(questions)
        return questions
    except Exception as e:
        logger.error(f"Error reading CSV {file_path}: {e}")
        return None

@quiz_bp.route('/quiz', methods=['GET', 'POST'])
def quiz():
    # Check if selected_skill is in session
    if 'selected_skill' not in session or session['selected_skill'] not in SKILL_NAMES:
        logger.info("No selected skill in session, redirecting to index")
        session.clear()  # Clear all session variables
        return redirect(url_for('index'))

    skill = session['selected_skill']
    skill_name = SKILL_NAMES[skill]
    questions = load_quiz_data(skill)

    if not questions:
        session.clear()  # Clear all session variables
        return render_template('error.html', message=f"No quiz found for {skill_name}")

    # Initialize session variables if not already set
    if 'current_question' not in session:
        session['current_question'] = 0
        session['score'] = session.get('score', 0)  # Preserve existing score if any
        session['total_questions'] = len(questions)
        session['answered'] = False
        session['feedback'] = ''
        session['correct_answer'] = ''
        session['explanation'] = ''

    current_question_index = session['current_question']

    if request.method == 'POST':
        if 'answer' in request.form:
            # User submitted an answer
            user_answer = request.form.get('answer').strip()
            print(user_answer)
            correct_answer = questions[current_question_index]['correct_answer']
            print(correct_answer)
            session['answered'] = True
            if user_answer[3:] == correct_answer[3:]:
                print("OK")
                session['score'] = session.get('score', 0) + 1  # Increment score
                session['feedback'] = 'Correct!'
                logger.info(f"Correct answer for question {current_question_index + 1} in {skill}")
            else:
                session['feedback'] = 'Incorrect!'
                logger.info(f"Incorrect answer for question {current_question_index + 1} in {skill}")
            session['correct_answer'] = correct_answer
            session['explanation'] = questions[current_question_index]['explanation']
        elif 'next' in request.form:
            # Move to next question
            session['current_question'] += 1
            session['answered'] = False
            session['feedback'] = ''
            session['correct_answer'] = ''
            session['explanation'] = ''
            if session['current_question'] >= session['total_questions']:
                # Quiz completed, redirect to feed.forms without clearing session
                logger.info(f"Quiz completed for {skill}, score: {session['score']}")
                return redirect(url_for('forms.reg'))
        session.modified = True
        return redirect(url_for('quiz.quiz'))

    # Render current question
    if current_question_index < session['total_questions']:
        question_data = questions[current_question_index]
        # Passing question data to the template for rendering
        return render_template(
            'quiz.html',
            question=question_data,
            question_number=current_question_index + 1,
            total_questions=session['total_questions'],
            skill_name=skill_name,
            answered=session['answered'],
            feedback=session['feedback'],
            correct_answer=session['correct_answer'],
            explanation=session['explanation']
        )

    session.clear()  # Clear all session variables if questions are exhausted
    return redirect(url_for('forms.reg'))

@quiz_bp.route('/index')
def index():
    """Main page, clears all session variables."""
    session.clear()  # Clear all session variables
    logger.info("Cleared all session variables on index access")
    return render_template('index.html', skills=SKILL_NAMES)