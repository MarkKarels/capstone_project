import openai
import spacy
from flask import render_template
from app import app
from app.model import *
import random

app.config.from_object('config')
openai.api_key = app.config['OPENAI_API_KEY']
MODEL_ID = 'gpt-3.5-turbo'
nlp = spacy.load("en_core_web_md")
MAX_CALL = 100
call_count = 0


@app.route('/')
def quiz():
    team = "Chicago Bears"
    difficulty = "medium"
    sub_topics = ["Team History", "Legendary Players", "Championship Seasons", "Coaches and Management", "Stadium and Fan Culture",
                  "Rivalries", "Record Breaking Performances", "Draft Picks", "Off-the-field Moments", "Individual player awards",
                  "Tactics and Play-style", "Founding Facts", "Previous Team Names"]
    chosen_sub_topic = random.choice(sub_topics)
    question, options, correct_option = generate_question(team, difficulty, chosen_sub_topic)

    return render_template('index.html',
                           quiz={"question": question, "options": options, "correct_option": correct_option})


def chatgpt_conversation(prompt):
    response = openai.ChatCompletion.create(
        model=MODEL_ID,
        messages=[{"role": "user",
                   "content": prompt}]
    )

    return response["choices"][0]["message"]["content"]


def generate_question(team, difficulty, chosen_sub_topic):
    global call_count
    global MAX_CALL

    for _ in range(MAX_CALL):
        if call_count >= MAX_CALL:
            print("Reached Max Call Count: Cannot Generate New Question")
            return None, None, None

        call_count += 1
        bears_fact = chatgpt_conversation(
            f"Give me a unique {difficulty} level difficulty multiple choice quiz question about the {team}'s "
            f"{chosen_sub_topic} with four options and the correct answer.")
        question_details = bears_fact.split('\n')
        question_details = [x for x in question_details if x != '']
        print(question_details)

        if len(question_details) <= 5:
            continue

        try:
            if MODEL_ID == 'gpt-4':
                question = question_details[0].split(':')[1].strip()
                options = [option.split(')')[1].strip() if ')' in option else None for option in question_details[1:5]]
                correct_option = question_details[5].split(')')[1].strip()
            else:
                question = question_details[0]
                options = [option.split(')')[1].strip() if ')' in option else None for option in question_details[1:5]]
                correct_option = question_details[5].split(')')[1].strip()

            # Return None if any of the options couldn't be parsed correctly
            if None in options:
                continue

            new_question_check = nlp(question)
            existing_questions = Question.query.with_entities(Question.question).all()
            is_similar = any(new_question_check.similarity(nlp(q[0])) > 0.9 for q in existing_questions)

            if not is_similar:
                db_store(question, options, correct_option, team)
                return question, options, correct_option

        except Exception as e:
            print(f"An error occurred: {e}")

    return None, None, None


def db_store(question, options, correct_option, team):
    row = Question(question=question, option1=options[0], option2=options[1], option3=options[2], option4=options[3],
                   answer=correct_option, team=team)
    db.session.add(row)
    db.session.commit()
