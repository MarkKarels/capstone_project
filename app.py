from flask import Flask, render_template
import openai

app = Flask(__name__)
app.config.from_object('config')
openai.api_key = app.config['OPENAI_API_KEY']
model_id = 'gpt-3.5-turbo'


@app.route('/')
def quiz():
    bears_fact = chatgpt_conversation("Give me an easy multiple choice quiz question with four options and the correct answer about the Chicago Bears")

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
        elif lines[1] == '' and len(lines) < 8 and lines[5] != '':
            question = lines[0]
            options = [option.split(')')[1].strip() for option in lines[2:6]]
            correct_option = lines[6].split(')')[1].strip()
        elif len(lines) < 8 and lines[5] == '':
            question = lines[0]
            options = [option.split(')')[1].strip() for option in lines[1:5]]
            correct_option = lines[6].split(')')[1].strip()
        else:
            question = lines[0]
            options = [option.split(')')[1].strip() for option in lines[1:5]]
            correct_option = lines[5].split(')')[1].strip()

    return render_template('index.html', quiz={"question": question, "options": options, "correct_option": correct_option})


def chatgpt_conversation(converstaion_log):
    response = openai.ChatCompletion.create(
        model=model_id,
        messages=[{"role": "user",
                   "content": converstaion_log}]
    )

    return response["choices"][0]["message"]["content"]


if __name__ == '__main__':
    app.run(debug=True)
