import random
import torch
import openai

from flask import render_template, jsonify
from transformers import BertTokenizer, BertModel
from sklearn.metrics.pairwise import cosine_similarity
from app import app
from app.model import *

tokenizer = BertTokenizer.from_pretrained('bert-base-uncased')
model = BertModel.from_pretrained('bert-base-uncased').eval()
app.config.from_object('config')
openai.api_key = app.config['OPENAI_API_KEY']
MODEL_ID = 'gpt-4'
MAX_CALL = 100
call_count = 0


@app.route('/')
def quiz():
    return render_template('index.html')


@app.route('/generate_question', methods=['POST'])
def generate_question_route():
    question, options, correct_option = generate_question()

    return jsonify({
        "question": question,
        "options": options,
        "correct_option": correct_option
    })


def chatgpt_conversation(prompt):
    response = openai.ChatCompletion.create(
        model=MODEL_ID,
        messages=[{"role": "user",
                   "content": prompt}]
    )

    return response["choices"][0]["message"]["content"]


def generate_question():
    global call_count
    global MAX_CALL

    for _ in range(MAX_CALL):
        if call_count >= MAX_CALL:
            print("Reached Max Call Count: Cannot Generate New Question")
            return None, None, None

        team, difficulty, chosen_sub_topic = generate_question_topic()
        print(chosen_sub_topic)
        call_count += 1
        bears_fact = chatgpt_conversation(
            f"Give me a unique {difficulty} level difficulty multiple choice quiz question about the {team}'s "
            f"{chosen_sub_topic} with four options and the correct answer. Keep the questions below 255 characters and"
            f"the answers should be no more than 7 words. Also, try to give realistic options that make sense,"
            f"for example if it asks about a player at a specific position, only list players who played that position"
            f" while leaving out opinion/subjective question and answers, sticking to hard facts.")
        question_details = bears_fact.split('\n')

        unwanted_strings = {
            '',
            'Correct Answer:',
            'Correct Answer: '
            'Answer:',
            'Options:',
            'Options: ',
            'Question:',
            'Question: '
        }

        question_details = [x for x in question_details if x not in unwanted_strings]

        print(question_details)

        if len(question_details) <= 5:
            print('Length Escape')
            continue

        try:
            if MODEL_ID == 'gpt-4':
                question = question_details[0].split(':')[1].strip()
                print(question)
                options = [option.split(')')[1].strip() if ')' in option else option.split('.')[1].strip() if '.' in
                           option else None for option in question_details[1:5]]
                print(options)
                if ')' in question_details[5]:
                    correct_option = question_details[5].split(')')[1].strip()
                elif '.' in question_details[5]:
                    correct_option = question_details[5].split('.')[1].strip()
                else:
                    correct_option = question_details[5]
                print(correct_option)
            else:
                question = question_details[0]
                options = [option.split(')')[1].strip() if ')' in option else None for option in question_details[1:5]]
                correct_option = question_details[5].split(')')[1].strip()

            # Return None if any of the options couldn't be parsed correctly
            if None in options:
                print('None Escape')
                continue

            existing_questions_for_team = Question.query.filter_by(team=team).with_entities(Question.question).all()
            is_similar = any(bert_similarity(question, q[0]) > 0.98 for q in existing_questions_for_team)

            if is_similar:
                print('Question relates to another question in the db')

            if not is_similar:
                db_store(question, options, correct_option, team)
                return question, options, correct_option

        except Exception as e:
            print(f"An error occurred: {e}")

    print('End of the line')
    return None, None, None


def db_store(question, options, correct_option, team):
    row = Question(question=question, option1=options[0], option2=options[1], option3=options[2], option4=options[3],
                   answer=correct_option, team=team)
    db.session.add(row)
    db.session.commit()


def generate_question_topic():
    team = "Chicago Bears"
    difficulty = "medium"
    sub_topics = ["Team History", "Legendary Players", "Championship Seasons", "Coaches and Management",
                  "Stadium and Fan Culture",
                  "Rivalries", "Record Breaking Performances", "Draft Picks", "Off-the-field Moments",
                  "Individual player awards",
                  "Tactics and Play-style", "Founding Facts", "Previous Team Names", "Legendary Teams", "Stadium Facts"]
    chosen_sub_topic = random.choice(sub_topics)

    return team, difficulty, chosen_sub_topic


def get_bert_embedding(sentence):
    tokens = tokenizer(sentence, return_tensors='pt', truncation=True, padding=True, max_length=512)
    with torch.no_grad():
        output = model(**tokens)
    return output.last_hidden_state[:, 0, :].squeeze().numpy()


def bert_similarity(sent1, sent2):
    emb1 = get_bert_embedding(sent1)
    emb2 = get_bert_embedding(sent2)
    return cosine_similarity([emb1], [emb2])[0][0]
