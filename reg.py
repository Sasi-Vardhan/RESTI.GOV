from flask import Blueprint, render_template, request, redirect, url_for, session
import csv
import os
import logging
import requests

forms=Blueprint("forms",__name__)

GOOGLE_FORM_URL = "https://docs.google.com/forms/d/e/1FAIpQLSde_y_aJGR5bWkyC83iaPvxXU3Ias3PxIwetlVq-YGrToRqSw/formResponse"


@forms.route("/registration", methods=['GET', 'POST'])
def reg():
    if request.method == 'POST':
        print("Got REQ")
        print(session.get('language', 'none'))
        name = request.form.get('name')
        phone = request.form.get('phone')
        city = request.form.get('city')
        lang=session.get('L', 'english')
        category=session.get("category","none")
        skill=session.get("selected_skill","none")
        score=session.get("score",-1)
        if not name or not phone or not city:
            return "All fields are required", 400

        # Send data to Google Form
        form_data = {
            'entry.2072056986': name,
            'entry.291075541': phone,
            'entry.1845336953': city,
            'entry.1489590549':lang,
            'entry.1539002697':category,
            'entry.1861178130':skill,
            'entry.1744027500':score
        }
        try:
            response = requests.post(GOOGLE_FORM_URL, data=form_data)
            if response.status_code != 200:
                session.clear()
                print(f"Failed to submit to Google Form: {response.status_code}")
            else:
                session.clear()
        except requests.RequestException as e:
            print(f"Error submitting to Google Form: {e}")
            session.clear()
        return redirect(url_for('index'))
    
    # Handle GET request (render registration.html)
    return render_template('Registration.html')
# https://docs.google.com/forms/d/e/1FAIpQLSde_y_aJGR5bWkyC83iaPvxXU3Ias3PxIwetlVq-YGrToRqSw/viewform?usp=pp_url
# &entry.2072056986=s&entry.291075541=a&entry.1845336953=s&
# entry.1489590549=i&
# entry.1539002697=h&
# entry.1861178130=a&
# entry.1744027500=r
