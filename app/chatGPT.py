import random
import torch
import openai

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


def is_question_vague(question, team, answer):
    response = chatgpt_conversation('Yes or No, is this question vague (as in having more than one possible answer)? '
                                    + question)

    if response == 'No':
        print('Question Is Unique')
    else:
        row = Vague(question=question, answer=answer, team=team)
        db.session.add(row)
        db.session.commit()


def chatgpt_prompt(question_type, quarter, quarter_summary, team):
    if question_type == 'history':
        difficulty, chosen_sub_topic = generate_history_question_topic()
        print(chosen_sub_topic)
        prompt = chatgpt_conversation(
            f"Give me a unique {difficulty} level difficulty multiple choice quiz question about the {team}'s "
            f"{chosen_sub_topic}. Ensure that the question is below 255 characters and each answer is no more than "
            f"7 words. The options provided should be contextually relevant to the question; for example, if asking "
            f"about a defensive record like interceptions, only list players known for playing in defensive positions. "
            f"Avoid opinion/subjective questions and answers, and stick strictly to factual information. You must "
            f"provide four options and the correct answer.")
        return prompt
    if question_type == 'pbp_current':
        prompt = chatgpt_conversation(
            f"Based on the following plays from Quarter {quarter}: \"{quarter_summary}\", generate a unique multiple "
            f"choice quiz question from big plays. Ensure that the question is below 255 characters and each answer is "
            f"no more than 7 words. Provide four options and the correct answer. Please provide as much detail as "
            f"possible including but not limited to time left in quarter. If known, give full player names as options.")
        return prompt
    return None


def create_question_from_chatgpt(question_type, game_id, quarter, team):
    global call_count
    global MAX_CALL
    global nfl_fact

    if game_id:
        game = Game.query.filter_by(id=game_id).first()
        if not game:
            return "Game not found.", 404

        quarter_plays = Play.query.filter_by(game_id=game_id, quarter=quarter).all()

        if not quarter_plays:
            return f"No data found for Quarter {quarter}.", 404

        # Convert quarter data to a readable format for ChatGPT
        quarter_summary = ". ".join([f"{play.timestamp} - {play.description}" for play in quarter_plays])
        nfl_fact = chatgpt_prompt(question_type, quarter, quarter_summary, team)
    else:
        nfl_fact = chatgpt_prompt(question_type, None, None, team)

    for _ in range(MAX_CALL):
        if call_count >= MAX_CALL:
            print("Reached Max Call Count: Cannot Generate New Question")
            return None, None, None

        call_count += 1
        question_details = nfl_fact.split('\n')
        print(question_details)
        unwanted_strings = {
            '',
            'Correct Answer:',
            'Correct Answer: ',
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
            if ':' in question_details[0]:
                question = question_details[0].split(':', 1)[1].strip()
            else:
                question = question_details[0]
            print(question)
            options = [
                option.split(')')[1].strip() if ')' in option else
                option.split('.')[1].strip() if '.' in option else
                option
                for option in question_details[1:5]
            ]
            print(options)
            if ')' in question_details[5]:
                correct_option = question_details[5].split(')')[1].strip()
            elif '.' in question_details[5]:
                correct_option = question_details[5].split('.')[1].strip()
            else:
                correct_option = question_details[5]
            print(correct_option)

            is_question_vague(question, team, correct_option)

            # Return None if any of the options couldn't be parsed correctly
            if None in options:
                print('None Escape')
                continue

            # Fetch both question and answer attributes
            existing_questions_for_team = Question.query.filter_by(team=team).with_entities(Question.question,
                                                                                            Question.answer).all()

            is_similar = False

            for q_text, q_answer in existing_questions_for_team:
                # Check for similarity
                if bert_similarity(question, q_text) > 0.90:
                    # If questions are similar, check if answers are also the same
                    if correct_option == q_answer:
                        is_similar = True
                        print('Question relates to another question in the db with the same answer.')
                        create_question_from_chatgpt(question_type, quarter, quarter_summary, team)
                    else:
                        # If answers are different, we can continue looking or decide on other logic
                        continue

            if not is_similar:
                row = Question(question=question, option1=options[0], option2=options[1], option3=options[2],
                               option4=options[3],
                               answer=correct_option, team=team)
                db.session.add(row)
                db.session.commit()
                return question, options, correct_option

        except Exception as e:
            print(f"An error occurred: {e}")

    print('End of the line')
    return None, None, None


def chatgpt_conversation(prompt):
    response = openai.ChatCompletion.create(
        model=MODEL_ID,
        messages=[{"role": "user",
                   "content": prompt}]
    )

    return response["choices"][0]["message"]["content"]


def generate_history_question_topic():
    difficulty = "medium"
    sub_topics = ["Team History", "Legendary Players", "Championship Seasons", "Coaches and Management",
                  "Stadium and Fan Culture", "Rivalries", "Record Breaking Performances", "Draft Picks",
                  "Current Charity Organizations", "Individual player awards", "Tactics and Play-style",
                  "Founding Facts", "Previous Team Names", "Legendary Teams", "Stadium Facts"]
    chosen_sub_topic = random.choice(sub_topics)

    return difficulty, chosen_sub_topic


def get_bert_embedding(sentence):
    tokens = tokenizer(sentence, return_tensors='pt', truncation=True, padding=True, max_length=512)
    with torch.no_grad():
        output = model(**tokens)
    return output.last_hidden_state[:, 0, :].squeeze().numpy()


def bert_similarity(sent1, sent2):
    emb1 = get_bert_embedding(sent1)
    emb2 = get_bert_embedding(sent2)
    return cosine_similarity([emb1], [emb2])[0][0]