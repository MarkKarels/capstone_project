import random
import time
from sqlalchemy import union
import torch
import openai

from transformers import BertTokenizer, BertModel
from sklearn.metrics.pairwise import cosine_similarity
from app import app
from app.model import *

tokenizer = BertTokenizer.from_pretrained("bert-base-uncased")
model = BertModel.from_pretrained("bert-base-uncased").eval()
app.config.from_object("config")
openai.api_key = app.config["OPENAI_API_KEY"]
MODEL_ID = "gpt-4"
MAX_CALL = 100
call_count = 0
global topic


def is_question_definitive(question):
    retry_count = 0
    max_retries = 5

    while retry_count < max_retries:
        try:
            response = chatgpt_conversation(
                "Yes or No? Does the following question have a single, definitive answer? "
                + question
            )

            if response == "Yes" or response == "yes":
                print(question + ": This Question Is Unique")
                return True
            else:
                print(question + ": This Question Is NOT Unique")
                return False
        except openai.error.RateLimitError as e:
            print(
                f"Rate limit reached in is_question_definitive. Pausing for 30 seconds. Error: {e}"
            )
            time.sleep(15)
            retry_count += 1


def can_question_be_reworded(question):
    response = chatgpt_conversation(
        "Yes or No? Can you reword the following question to have a single, definitive answer? "
        + question
    )

    if response == "Yes" or response == "yes":
        print(question + ": This Question Can Be Reworded")
        return True
    else:
        return False


def ask_again(question):
    reword_question = chatgpt_conversation(
        f"Can you turn this into a question with only one possible answer?"
        + question
        + f" Ensure that the question is below 255 characters and each answer is no more than "
        f"7 words. The format of the response should be question \n option1 \n option2 \n option3 \n option4 \n "
        f"answer. do not provide anything else in the response to distinguish what each line represents, only the "
        f"requested information. You must provide a question, 4 options, and an answer."
    )
    question_details = reword_question.split("\n")
    question = question_details[0].strip()
    options = [option.strip() for option in question_details[1:5]]
    correct_option = question_details[5].strip()
    return question, options, correct_option


def is_answer_correct(question, answer, topic, summary):
    global verify_response
    retry_count = 0
    max_retries = 5

    while retry_count < max_retries:
        try:
            if topic == "Team History":
                verify_response = chatgpt_conversation(
                    "Yes or No? Given the following question: "
                    + question
                    + " : Can you determine that the Answer is: "
                    + answer
                    + " Yes or No repsonse only."
                )
                print(verify_response)
            else:
                verify_response = chatgpt_conversation(
                    "Yes or No? Take the following question: "
                    + question
                    + " : and search the summary for the follwing answer: "
                    + answer
                    + " Based on the following information: "
                    + summary
                    + " and determing if this question and answer combo can be created from the summary accurately. Yes or No repsonse only."
                )
                print(verify_response)
            if verify_response == "Yes" or verify_response == "yes":
                print(question + ": This Answer Has Been Verified")
                return True
            else:
                print(question + ": This Answer Has NOT Been Verified")
                return False
        except openai.error.RateLimitError as e:
            print(
                f"Rate limit reached in is_answer_correct. Pausing for 30 seconds. Error: {e}"
            )
            time.sleep(15)
            retry_count += 1


def chatgpt_prompt_num_1(question_type, summary, team):
    retry_count = 0
    max_retries = 5

    while retry_count < max_retries:
        try:
            if question_type == "history":
                prompt = chatgpt_conversation(
                    f"Ensure all questions generate are below 255 characters and each answer is no more than "
                    f"7 words. The format of the response must be question \n option1 \n option2 \n option3 \n option4 \n "
                    f"answer. Do not provide anything else in the response to distinguish what each line represents, only the "
                    f"requested information. (i.e. don't put question: before asking the question or option1: before displaying the option) "
                    f"You must provide a question, 4 options, and an answer. "
                    f"Give me a unique multiple choice quiz question about the NFL team {team}'s."
                )
                print(prompt)
                return prompt
            if question_type == "pbp_current":
                prompt = chatgpt_conversation(
                    f"Ensure all questions generate are below 255 characters and each answer is no more than "
                    f"7 words. The format of the response must be question \n option1 \n option2 \n option3 \n option4 \n "
                    f"answer. Do not provide anything else in the response to distinguish what each line represents, only the "
                    f"requested information. (i.e. don't put question: before asking the question or option1: before displaying the option) "
                    f"You must provide a question, 4 options, and an answer. "
                    f"Give me a unique multiple choice quiz question about the following NFL game summary: {summary}"
                )
                print(prompt)
                return prompt
            return None
        except openai.error.RateLimitError as e:
            print(
                f"Rate limit reached in chatgpt_prompt_num_1. Pausing for 30 seconds. Error: {e}"
            )
            time.sleep(30)
            retry_count += 1


def chatgpt_prompt_num_2(question_type, summary, team):
    global topic

    if question_type == "history":
        difficulty, chosen_sub_topic = generate_history_question_topic()
        chosen_topic = chosen_sub_topic
        print(chosen_topic)
        # See if the prompt can change to only ask definitive questions
        prompt = chatgpt_conversation(
            f"Ensure all questions generate are below 255 characters and each answer is no more than "
            f"7 words. The format of the response must be question \n option1 \n option2 \n option3 \n option4 \n "
            f"answer. Do not provide anything else in the response to distinguish what each line represents, only the "
            f"requested information. (i.e. don't put question: before asking the question or option1: before displaying the option) "
            f"You must provide a question, 4 options, and an answer. "
            f"Give me a unique {difficulty} level difficulty multiple choice quiz question about the {team}'s {chosen_topic}. "
            f"Use the entire history of the team to generate the question. Verify the answer is correct."
        )
        print(prompt)
        return prompt
    if question_type == "pbp_current":
        prompt = chatgpt_conversation(
            f"Ensure all questions generate are below 255 characters and each answer is no more than "
            f"7 words. The format of the response must be question \n option1 \n option2 \n option3 \n option4 \n "
            f"answer. Do not provide anything else in the response to distinguish what each line represents, only the "
            f"requested information. (i.e. don't put question: before asking the question or option1: before displaying the option) "
            f"You must provide a question, 4 options, and an answer. "
            f"Based on the following plays from this National Football League game: {summary}, generate a unique multiple choice "
            f"quiz question from big plays. Please provide as much detail as possible including but not limited to which teams were "
            f"playing, which team made the play, what type of play it was, the quarter the play occured, time left in quarter, who "
            f"made the play, and if it resulted in a touchdown, turnover, sack, or firstdown. Provide the team name of the player that "
            f"made the play. Verify the answer is correct."
        )
        return prompt
    return None


def chatgpt_prompt_num_3(question_type, summary, team, week):
    global topic

    if question_type == "history":
        difficulty, chosen_sub_topic = generate_history_question_topic()
        chosen_topic = chosen_sub_topic
        print(chosen_topic)
        # See if the prompt can change to only ask definitive questions
        prompt = chatgpt_conversation(
            f"Ensure all questions generate are below 255 characters and each answer is no more than "
            f"7 words. The format of the response must be question \n option1 \n option2 \n option3 \n option4 \n "
            f"answer. Do not provide anything else in the response to distinguish what each line represents, only the "
            f"requested information. (i.e. don't put question: before asking the question or option1: before displaying the option) "
            f"You must provide a question, 4 options, and an answer. "
            f"Give me a unique {difficulty} level difficulty multiple choice quiz question about the {team}'s "
            f"{chosen_topic}. Use the entire history of the team to generate the question. "
            f"Ask questions that are difinitive with one verified answer only. Be a specific as possible when "
            f"constructing the question and stick to the described format in the response. Verify the answer is correct "
            f"prior to responding with the requested information. If you cannot verify the answer, provide a new multiple "
            f"choice question with a topic of your choosing but it must relate to the history of the NFL team {team}'s."
        )
        print(prompt)
        return prompt
    if question_type == "pbp_current":
        prompt = chatgpt_conversation(
            f"Ensure all questions generate are below 255 characters and each answer is no more than "
            f"7 words. The format of the response must be question \n option1 \n option2 \n option3 \n option4 \n "
            f"answer. Do not provide anything else in the response to distinguish what each line represents, only the "
            f"requested information. (i.e. don't put question: before asking the question or option1: before displaying the option) "
            f"You must provide a question, 4 options, and an answer. "
            f'Based on the following plays from this National Football League game: "{summary}", generate a unique multiple '
            f"choice quiz question from big plays. Please provide as much detail as possible about the play. Provide the team name(s) "
            f"of the descrived play. Verify the answer is correct based on the above summary before generating the response. If you "
            f"cannot verify the answer, provide a new multiple-choice question based on the summary provided. Please include the week number "
            f"of the game in the question. That week number is {week}. Also include that the game year is 2023."
        )
        return prompt
    return None


def create_question_from_chatgpt(question_type, game_id, team, week):
    global call_count
    global MAX_CALL
    global nfl_fact
    global topic
    global is_similar

    print("Question Type: " + question_type)
    print("Game ID: " + str(game_id))
    print("Team: " + team)

    time.sleep(5)

    # Initialize summary with a default value
    summary = ""

    if game_id is not None:
        topic = "Live Game Play-by-Play"
        game = Game.query.filter_by(id=game_id).first()

        if not game:
            return "Game not found.", 404

        plays = Play.query.filter_by(game_id=game_id).all()

        if not plays:
            return f"No data found.", 404

        summary = ". ".join(
            [f"{play.timestamp} - {play.description}" for play in plays]
        )
        nfl_fact = chatgpt_prompt_num_3(question_type, summary, team, week)
    else:
        topic = "Team History"
        nfl_fact = chatgpt_prompt_num_3(question_type, None, team, None)

    for _ in range(MAX_CALL):
        if call_count >= MAX_CALL:
            print("Reached Max Call Count: Cannot Generate New Question")
            break

        call_count += 1
        question_details = nfl_fact.split("\n")
        print(question_details)

        if len(question_details) <= 5:
            print("Length Escape")
            break

        try:
            question = question_details[0].strip()
            options = [option.strip() for option in question_details[1:5]]
            correct_option = question_details[5].strip()
            is_similar = False

            if question_type == "history":
                history_question_query = HistoryQuestion.query.filter_by(
                    team=team
                ).with_entities(HistoryQuestion.question, HistoryQuestion.answer)
                accuracy_question_query = Accuracy.query.filter_by(
                    team=team
                ).with_entities(Accuracy.question, Accuracy.answer)
                vague_question_query = Vague.query.filter_by(team=team).with_entities(
                    Vague.question, Vague.answer
                )

                unified_query = union(
                    history_question_query,
                    accuracy_question_query,
                    vague_question_query,
                )
                existing_questions_for_team = db.session.execute(
                    unified_query
                ).fetchall()

            elif question_type == "pbp_current":
                live_question_query = LiveQuestion.query.filter_by(
                    team=team
                ).with_entities(LiveQuestion.question, LiveQuestion.answer)
                accuracy_question_query = Accuracy.query.filter_by(
                    team=team
                ).with_entities(Accuracy.question, Accuracy.answer)
                vague_question_query = Vague.query.filter_by(team=team).with_entities(
                    Vague.question, Vague.answer
                )

                unified_query = union(
                    live_question_query, accuracy_question_query, vague_question_query
                )
                existing_questions_for_team = db.session.execute(
                    unified_query
                ).fetchall()

            if existing_questions_for_team is not None:
                is_similar = False
                for q_text, q_answer in existing_questions_for_team:
                    if bert_similarity(question, q_text) > 0.90:
                        if correct_option == q_answer:
                            is_similar = True
                            break

                if is_similar:
                    row = Duplicate(
                        question=question,
                        answer=correct_option,
                        team=team,
                        topic=topic,
                    )
                    db.session.add(row)
                    db.session.commit()
                    print("Question added to the duplicate table")
                    call_count = 0
                    break

            if not is_similar:
                if question_type == "history":
                    # Check if Question is definitive
                    definitive = is_question_definitive(question)

                    if not definitive:
                        row = Vague(
                            question=question,
                            answer=correct_option,
                            team=team,
                            topic=topic,
                        )
                        db.session.add(row)
                        db.session.commit()
                        print("Question added to the vague table")
                        call_count = 0
                        break

                # Check if Question is correct via chatGPT
                correct = is_answer_correct(question, correct_option, topic, summary)

                if not correct:
                    row = Accuracy(
                        question=question,
                        answer=correct_option,
                        team=team,
                        topic=topic,
                    )
                    db.session.add(row)
                    db.session.commit()
                    print("Question added to the accuracy table")
                    call_count = 0
                    break

            if question_type == "history":
                row = HistoryQuestion(
                    question=question,
                    option1=options[0],
                    option2=options[1],
                    option3=options[2],
                    option4=options[3],
                    answer=correct_option,
                    team=team,
                )
                db.session.add(row)
                db.session.commit()
                call_count = 0
                break

            if question_type == "pbp_current":
                row = LiveQuestion(
                    question=question,
                    option1=options[0],
                    option2=options[1],
                    option3=options[2],
                    option4=options[3],
                    answer=correct_option,
                    team=team,
                    week=week,
                )
                db.session.add(row)
                db.session.commit()
                call_count = 0
                break

        except Exception as e:
            print(f"An error occurred: {e}")


def chatgpt_conversation(prompt):
    response = openai.ChatCompletion.create(
        model=MODEL_ID, messages=[{"role": "user", "content": prompt}]
    )

    return response["choices"][0]["message"]["content"]


def generate_history_question_topic():
    difficulty = random.choice(["easy", "medium", "hard"])
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
        "Retired Jerseys and Team Honors",
    ]
    chosen_sub_topic = random.choice(sub_topics)

    return difficulty, chosen_sub_topic


def get_bert_embedding(sentence):
    tokens = tokenizer(
        sentence, return_tensors="pt", truncation=True, padding=True, max_length=512
    )
    with torch.no_grad():
        output = model(**tokens)
    return output.last_hidden_state[:, 0, :].squeeze().numpy()


def bert_similarity(sent1, sent2):
    emb1 = get_bert_embedding(sent1)
    emb2 = get_bert_embedding(sent2)
    return cosine_similarity([emb1], [emb2])[0][0]
