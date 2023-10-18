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
topic = ''


def is_question_definitive(question, team, answer):
    response = chatgpt_conversation('Yes or No? Does the following question have a single, definitive answer? '
                                    + question)

    if response == 'Yes' or response == 'yes':
        print(question + ': This Question Is Unique')
        return True
    else:
        existing_vague_question = Vague.query.filter_by(question=question).first()
        if not existing_vague_question:
            row = Vague(question=question, answer=answer, team=team, topic=topic)
            db.session.add(row)
            db.session.commit()
            print(question + ': Question added to the vague table')
        return False


def ask_again(question):
    reword_question = chatgpt_conversation(
        f"Can you turn this into a question with only one possible answer?" + question
        + f" Ensure that the question is below 255 characters and each answer is no more than "
        f"7 words. The format of the response should be question \n option1 \n option2 \n option3 \n option4 \n "
        f"answer. do not provide anything else in the response to distinguish what each line represents, only the "
        f"requested information. You must provide a question, 4 options, and an answer.")
    question_details = reword_question.split('\n')
    question = question_details[0].strip()
    options = [option.strip() for option in question_details[1:5]]
    correct_option = question_details[5].strip()
    return question, options, correct_option


def is_answer_correct(question, answer, team):
    verify_response = chatgpt_conversation('Yes or No? Is the answer to ' + question + 'Answer: ' + answer)
    if verify_response == 'Yes' or verify_response == 'yes':
        print(question + ': This Answer Has Been Verified')
        return True
    else:
        existing_accuracy_question = Accuracy.query.filter_by(question=question).first()
        if not existing_accuracy_question:
            row = Accuracy(question=question, answer=answer, team=team, topic=topic)
            db.session.add(row)
            db.session.commit()
            print('Question added to the accuracy table')
        return False


def chatgpt_prompt(question_type, quarter, quarter_summary, team):
    global topic

    if question_type == 'history':
        difficulty, chosen_sub_topic = generate_history_question_topic()
        topic = chosen_sub_topic
        print(chosen_sub_topic)
        prompt = chatgpt_conversation(
            f"Give me a unique {difficulty} level difficulty multiple choice quiz question about the {team}'s "
            f"{chosen_sub_topic}. Ensure that the question is below 255 characters and each answer is no more than "
            f"7 words. The format of the response should be question \n option1 \n option2 \n option3 \n option4 \n "
            f"answer. do not provide anything else in the response to distinguish what each line represents, only the "
            f"requested information. You must provide a question, 4 options, and an answer.")
        print(prompt)
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

    if game_id is not None:
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

        call_count += 1
        question_details = nfl_fact.split('\n')

        if len(question_details) <= 5:
            print('Length Escape')
            continue

        try:
            count = 0
            question = question_details[0].strip()
            options = [option.strip() for option in question_details[1:5]]
            correct_option = question_details[5].strip()

            definitive = is_question_definitive(question, team, correct_option)
            while not definitive and count < 5:
                question, options, correct_option = ask_again(question)
                count += 1
                definitive = is_question_definitive(question, team, correct_option)

            if count >= 5:
                print('Not Definitive Escape')
                break

            correct = is_answer_correct(question, correct_option, team)

            if None in options:
                print('None Escape')
                continue

            existing_questions_for_team = Question.query.filter_by(team=team).with_entities(Question.question,
                                                                                            Question.answer).all()

            is_similar = False

            for q_text, q_answer in existing_questions_for_team:
                if bert_similarity(question, q_text) > 0.90:
                    if correct_option == q_answer:
                        is_similar = True
                    else:
                        continue

            if not is_similar and definitive and correct:
                row = Question(question=question, option1=options[0], option2=options[1], option3=options[2],
                               option4=options[3],
                               answer=correct_option, team=team)
                db.session.add(row)
                db.session.commit()
                break
            else:
                break

        except Exception as e:
            print(f"An error occurred: {e}")


def chatgpt_conversation(prompt):
    response = openai.ChatCompletion.create(
        model=MODEL_ID,
        messages=[{"role": "user",
                   "content": prompt}]
    )

    return response["choices"][0]["message"]["content"]


def generate_history_question_topic():
    difficulty = "medium"
    sub_topics = [
        "Team History",
        "Legendary Players",
        "Championship Seasons",
        "Coaches and Management",
        "Stadium and Fan Culture",
        "Rivalries",
        "Record Breaking Performances",
        "Draft Picks",
        "Current Charity Organizations",
        "Individual player awards",
        "Founding Facts",
        "Previous Team Names",
        "Legendary Teams",
        "Stadium Facts",
        "Hall of Fame Inductees",
        "Memorable Playoff Games",
        "Team Scandals and Controversies",
        "Franchise Records",
        "Community Engagement",
        "Notable Trades and Acquisitions",
        "Behind-the-Scenes Personnel",
        "Media Coverage and Team Perception",
        "Fan Traditions",
        "Retired Jerseys and Team Honors"
    ]
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
