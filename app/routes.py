import openai
from flask import render_template
from app import app
from app.model import *

app.config.from_object('config')
openai.api_key = app.config['OPENAI_API_KEY']
model_id = 'gpt-3.5-turbo'


@app.route('/')
def quiz():
    bears_fact = chatgpt_conversation(
        "Give me a medium difficulty multiple choice quiz question with four options and the correct answer about the Chicago Bears")
    lines = bears_fact.split('\n')

    print(lines)
    if model_id == 'gpt-4':
        if lines[1] == '' and lines[6] == '':
            question = lines[0].split(':')[1].strip()
            options = [option.split(')')[1].strip() for option in lines[2:6]]
            correct_option = lines[7].split(')')[1].strip()
        elif lines[1] == '' and len(lines) < 8 and lines[5] != '':
            question = lines[0].split(':')[1].strip()
            options = [option.split(')')[1].strip() for option in lines[2:6]]
            correct_option = lines[6].split(')')[1].strip()
        elif len(lines) < 8 and lines[5] == '':
            question = lines[0].split(':')[1].strip()
            options = [option.split(')')[1].strip() for option in lines[1:5]]
            correct_option = lines[6].split(')')[1].strip()
        else:
            question = lines[0].split(':')[1].strip()
            options = [option.split(')')[1].strip() for option in lines[1:5]]
            correct_option = lines[5].split(')')[1].strip()
    else:
        if lines[1] == '' and lines[6] == '':
            question = lines[0]
            options = [option.split(')')[1].strip() for option in lines[2:6]]
            correct_option = lines[7].split(')')[1].strip()
            print("Database Should Be Updated")
            item = Question(question=lines[0], option1=lines[2].split(')')[1].strip(),
                            option2=lines[3].split(')')[1].strip(), option3=lines[4].split(')')[1].strip(),
                            option4=lines[5].split(')')[1].strip(), answer=lines[7].split(')')[1].strip(),
                            team='Chicago Bears')
            db.session.add(item)
            db.session.commit()
        elif lines[1] == '' and len(lines) < 8 and lines[5] != '':
            question = lines[0]
            options = [option.split(')')[1].strip() for option in lines[2:6]]
            correct_option = lines[6].split(')')[1].strip()
            print("Database Should Be Updated")
            item = Question(question=lines[0], option1=lines[2].split(')')[1].strip(),
                            option2=lines[3].split(')')[1].strip(), option3=lines[4].split(')')[1].strip(),
                            option4=lines[5].split(')')[1].strip(), answer=lines[6].split(')')[1].strip(),
                            team='Chicago Bears')
            db.session.add(item)
            db.session.commit()
        elif len(lines) < 8 and lines[5] == '':
            question = lines[0]
            options = [option.split(')')[1].strip() for option in lines[1:5]]
            correct_option = lines[6].split(')')[1].strip()
            print("Database Should Be Updated")
            item = Question(question=lines[0], option1=lines[1].split(')')[1].strip(),
                            option2=lines[2].split(')')[1].strip(), option3=lines[3].split(')')[1].strip(),
                            option4=lines[4].split(')')[1].strip(), answer=lines[6].split(')')[1].strip(),
                            team='Chicago Bears')
            db.session.add(item)
            db.session.commit()
        else:
            question = lines[0]
            options = [option.split(')')[1].strip() for option in lines[1:5]]
            correct_option = lines[5].split(')')[1].strip()
            print("Database Should Be Updated")
            item = Question(question=lines[0], option1=lines[1].split(')')[1].strip(),
                            option2=lines[2].split(')')[1].strip(), option3=lines[3].split(')')[1].strip(),
                            option4=lines[4].split(')')[1].strip(), answer=lines[5].split(')')[1].strip(),
                            team='Chicago Bears')
            db.session.add(item)
            db.session.commit()

    return render_template('index.html',
                           quiz={"question": question, "options": options, "correct_option": correct_option})


def chatgpt_conversation(converstaion_log):
    response = openai.ChatCompletion.create(
        model=model_id,
        messages=[{"role": "user",
                   "content": converstaion_log}]
    )

    return response["choices"][0]["message"]["content"]
