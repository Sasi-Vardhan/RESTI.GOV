from flask import Blueprint, render_template, request, session, redirect, url_for
from deep_translator import GoogleTranslator
from concurrent.futures import ThreadPoolExecutor, as_completed

select_skills_bp = Blueprint('select_skills', __name__, template_folder='templates')

# Language mapping (copied from app.py for consistency)
LANGUAGES = {
    'english': {'code': 'en', 'name': 'English', 'native': 'English'},
    'hindi': {'code': 'hi', 'name': 'Hindi', 'native': 'हिंदी'},
    'tamil': {'code': 'ta', 'name': 'Tamil', 'native': 'தமிழ்'},
    'telugu': {'code': 'te', 'name': 'Telugu', 'native': 'తెలుగు'}
}

# Skill options per category
youth_skills = [
    {
        'key': 'mushroom',
        'name': 'Mushroom Cultivation',
        'description': 'Learn how to cultivate mushrooms in grow bags.',
        'image': 'images/mushroom.jpg'
    },
    {
        'key': 'poultry',
        'name': 'Poultry Farming',
        'description': 'Raise hens and manage feed, vaccination and market sales.',
        'image': 'images/poultry.webp'
    },
    {
        'key': 'mobile_repair',
        'name': 'Mobile Repair',
        'description': 'Diagnose and fix common mobile phone issues.',
        'image': 'images/mobile_repair.jpg'
    }
]

farmer_skills = [
    {
        'key': 'organic_farming',
        'name': 'Organic Farming',
        'description': 'Learn sustainable farming techniques using organic methods.',
        'image': 'images/organic_farming.jpg'
    },
    {
        'key': 'drip_irrigation',
        'name': 'Drip Irrigation',
        'description': 'Master water-efficient irrigation systems for crops.',
        'image': 'images/drip_irrigation.jpg'
    }
]

housewife_skills = [
    {
        'key': 'tailoring',
        'name': 'Tailoring',
        'description': 'Learn sewing and garment-making for small businesses.',
        'image': 'images/tailoring.jpg'
    },
    {
        'key': 'food_processing',
        'name': 'Food Processing',
        'description': 'Create value-added food products like pickles and jams.',
        'image': 'images/food_processing.jpg'
    }
]

# Translation utility
def translate_text(text, lang_code):
    """Translate a single text string using GoogleTranslator."""
    if lang_code == 'en':
        return text
    try:
        return GoogleTranslator(source='en', target=lang_code).translate(text)
    except Exception as e:
        print(f"Translation failed: {text} - {e}")
        return text

def parallel_translate(text_dict, lang_code):
    """Translate a dictionary of texts in parallel."""
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {executor.submit(translate_text, v, lang_code): k for k, v in text_dict.items()}
        results = {}
        for future in as_completed(futures):
            k = futures[future]
            results[k] = future.result()
        return results

@select_skills_bp.route('/select-skills', methods=['GET', 'POST'])
def show_skills():
    sdict=dict(session)
    for key, value in sdict.items():
        if(key != 'L' or key != 'Language' or key != 'category' or key != 'selected_skill'):
            session.pop(key)
    category = session.get('category', 'youth')  # Default to 'youth'
    lang = session.get('language', 'english')
    lang_code = LANGUAGES.get(lang, {'code': 'en'})['code']
    print(category)
    # Select skills based on category
    if category == 'farmer':
        raw_skills = farmer_skills
        heading_key = 'farmer_skills_heading'
    elif category == 'housewife':
        raw_skills = housewife_skills
        heading_key = 'housewife_skills_heading'
    else:  # Default to youth
        raw_skills = youth_skills
        heading_key = 'youth_skills_heading'

    # Prepare texts for translation
    texts_to_translate = {
        'heading': 'Choose a skill to transform your future!' if heading_key == 'youth_skills_heading' else 'Choose your skill',
        'select_button': 'Learn Now',
        'motivation_text': 'For Every skill which you choose to learn will get a Real world scenario, where you need to solve and answer the Questions and Learn from it'
    }
    for i, skill in enumerate(raw_skills):
        texts_to_translate[f'name_{i}'] = skill['name']
        texts_to_translate[f'desc_{i}'] = skill['description']

    # Perform parallel translation
    translated_texts = parallel_translate(texts_to_translate, lang_code)

    # Build translated skills list
    skills = []
    for i, skill in enumerate(raw_skills):
        skills.append({
            'key': skill['key'],
            'name': translated_texts[f'name_{i}'],
            'description': translated_texts[f'desc_{i}'],
            'image': skill['image']
        })

    if request.method == 'POST':
        selected_skill = request.form.get('skill')
        session["selected_skill"]=selected_skill
        print(f"Selected skill: {selected_skill} for category: {category}")
        # Placeholder: Redirect or process the selected skill
        return redirect(url_for('quiz.quiz'))  # Update with desired route

    return render_template('select_skills.html',
                           heading=translated_texts['heading'],
                           skills=skills,
                           select_button=translated_texts['select_button'],
                           motivation_text=translated_texts['motivation_text'],
                           languages=LANGUAGES,
                           current_lang=lang)