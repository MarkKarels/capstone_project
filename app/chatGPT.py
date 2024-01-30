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
MODEL_ID = "gpt-4-0125-preview"
MAX_CALL = 100
call_count = 0
global topic


def is_question_definitive(question, answer):
    retry_count = 0
    max_retries = 5

    while retry_count < max_retries:
        try:
            response = chatgpt_conversation(
                f"Yes or No? Is the only answer to {question}, {answer}? "
            )

            if response == "Yes" or response == "yes":
                print(question + ": This Question Contains Only One Answer")
                return True
            elif response == "No" or response == "no":
                print(question + ": This Question Contains MORE THAN One Answer")
                return False
            else:
                print(
                    f"There was an issue with the response from is_question_definitive: Response came back as --> {response}"
                )
                print("")
                return True
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


def is_answer_correct(question, answer, topic):
    retry_count = 0
    max_retries = 5

    while retry_count < max_retries:
        try:
            verify_response = chatgpt_conversation(
                f"Correct or Incorrect? Is the answer to {question}, is {answer}?"
            )

            if verify_response == "Correct" or verify_response == "correct":
                print(
                    question + ": This Answer Has Been Verified To Be True and Accurate"
                )
                return True
            elif verify_response == "Incorrect" or verify_response == "incorrect":
                print(
                    question
                    + ": This Answer Cannot Be Verified As True and Accurate and Will Not Be Used"
                )
                return False
            else:
                print(
                    f"There was an issue with the response from is_answer_correct: Response came back as --> {verify_response}"
                )
                print("")
                return True
        except openai.error.RateLimitError as e:
            print(
                f"Rate limit reached in is_answer_correct. Pausing for 30 seconds. Error: {e}"
            )
            time.sleep(15)
            retry_count += 1


def chatgpt_prompt_num_1(question_type, summary, team, week):
    retry_count = 0
    max_retries = 5

    while retry_count < max_retries:
        try:
            if question_type == "History":
                prompt = chatgpt_conversation(
                    f"Generate 10 unique multiple choice quiz questions about the {team}. "
                    f"Each question should be under 255 characters. "
                    f"Provide 4 options and 1 answer for each question, with the answer being no more than 7 words. "
                    f"Format: question \n option1 \n option2 \n option3 \n option4 \n answer. "
                    f"Maintain this format strictly without additional labels or text."
                    f"Do not provide anything else in the response other than the requested information."
                    f"Do not number each question. Do not put spaces after each question."
                )
                return prompt
            if question_type == "Live Game Play-by-Play":
                prompt = chatgpt_conversation(
                    f"Generate 10 unique multiple choice quiz questions based on this NFL game summary: {summary}. "
                    f"Each question should focus on plays made by the {team}."
                    f"Each question should be under 255 characters. "
                    f"Provide 4 options and 1 answer for each question, with the answer being no more than 7 words. "
                    f"Format: question \n option1 \n option2 \n option3 \n option4 \n answer. "
                    f"Maintain this format strictly without additional labels or text."
                )
                return prompt
            return None
        except openai.error.RateLimitError as e:
            print(
                f"Rate limit reached in chatgpt_prompt_num_1. Pausing for 30 seconds. Error: {e}"
            )
            time.sleep(30)
            retry_count += 1


def chatgpt_prompt_num_2(question_type, summary, team, week):
    global topic

    if question_type == "History":
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
    if question_type == "Live Game Play-by-Play":
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

    if question_type == "History":
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
    if question_type == "Live Game Play-by-Play":
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


def chatgpt_prompt_num_4(question_type, summary, team, week):
    global topic

    if question_type == "History":
        # See if the prompt can change to only ask definitive questions
        prompt = chatgpt_conversation(
            f"Ensure all questions generate are below 255 characters and each answer is no more than 7 words. The format of the response must be "
            f"question \n option1 \n option2 \n option3 \n option4 \n answer. Do not provide anything else in the response to distinguish what each "
            f"line represents, only the requested information. (i.e. don't put question: before asking the question or option1: before displaying the "
            f"option) You must provide a question, 4 options, and an answer. Give me a multiple choice quiz question about the National Football League "
            f"Franchise {team}'s . Use the entire history of the team to generate the question. Choose any subtopic about the team you would like, just "
            f"keep it unique. Ask questions that are difinitive with one verified answer only. Be a specific as possible when constructing the question "
            f"and stick to the described format in the response. Verify the answer is correct by checking yourself prior to responding with the requested "
            f"information. If you cannot verify the answer, provide a new multiple choice question with a topic of your choosing but it must relate to the "
            f"history of the NFL franchise {team}."
        )
        print(prompt)
        return prompt
    if question_type == "Live Game Play-by-Play":
        prompt = chatgpt_conversation(
            f"Ensure all questions generate are below 255 characters and each answer is no more than 7 words. The format of the response must be "
            f"question \n option1 \n option2 \n option3 \n option4 \n answer. Do not provide anything else in the response to distinguish what each "
            f"line represents, only the requested information. (i.e. don't put question: before asking the question or option1: before displaying the "
            f"option) You must provide a question, 4 options, and an answer. Based on the following plays from this National Football League game: "
            f"{summary}, generate a unique multiple choice quiz question from big plays focusing on the team {team}. Please provide as much detail as "
            f"about the play. Provide the team name(s) of the described play. Verify the answer is correct based on the above summary before generating "
            f"the response. If you cannot verify the answer, provide a new multiple-choice question based on the summary provided. Please include the week "
            f"number of the game in the question."
        )
        return prompt
    return None


def create_question_from_chatgpt(question_type, game_id, team, week):
    is_similar = False
    existing_questions_for_team = None

    print("Question Type: " + question_type)
    print("Game ID: " + str(game_id))
    print("Team: " + team)
    print("")

    time.sleep(5)

    if question_type == "Live Game Play-by-Play":
        game = Game.query.filter_by(id=game_id).first()

        if not game:
            return "Game not found.", 404

        plays = Play.query.filter_by(game_id=game_id).all()

        if not plays:
            return f"No data found.", 404

        summary = ". ".join(
            [f"{play.timestamp} - {play.description}" for play in plays]
        )

        print("Calling for Live Game Play-by-Play Questions from ChatGPT")
        print("")

        nfl_fact = chatgpt_prompt_num_1(question_type, summary, team, week)
    else:
        print("Calling for Team History Questions from ChatGPT")
        print("")

        nfl_fact = chatgpt_prompt_num_1(question_type, None, team, None)

    question_details = [line for line in nfl_fact.split("\n") if line.strip()]

    print(question_details)
    print("")

    time.sleep(15)

    if len(question_details) <= 6:
        return print("Not enough data to generate a question")

    if question_type == "History":
        history_question_query = HistoryQuestion.query.filter_by(
            team=team
        ).with_entities(HistoryQuestion.question, HistoryQuestion.answer)
        accuracy_question_query = Accuracy.query.filter_by(team=team).with_entities(
            Accuracy.question, Accuracy.answer
        )
        vague_question_query = Vague.query.filter_by(team=team).with_entities(
            Vague.question, Vague.answer
        )

        unified_query = union(
            history_question_query,
            accuracy_question_query,
            vague_question_query,
        )
        existing_questions_for_team = db.session.execute(unified_query).fetchall()

        # elif question_type == "Live Game Play-by-Play":
        #     live_question_query = LiveQuestion.query.filter_by(team=team).with_entities(
        #         LiveQuestion.question, LiveQuestion.answer
        #     )
        #     accuracy_question_query = Accuracy.query.filter_by(team=team).with_entities(
        #         Accuracy.question, Accuracy.answer
        #     )
        #     vague_question_query = Vague.query.filter_by(team=team).with_entities(
        #         Vague.question, Vague.answer
        #     )

        #     unified_query = union(
        #         live_question_query,
        #         accuracy_question_query,
        #         vague_question_query,
        #     )
        #     existing_questions_for_team = db.session.execute(unified_query).fetchall()

    for i in range(0, len(question_details), 6):
        question_block = question_details[i : i + 6]
        question, option1, option2, option3, option4, answer = question_block
        print(f"Question: {question}")
        print(f"Option 1: {option1}")
        print(f"Option 2: {option2}")
        print(f"Option 3: {option3}")
        print(f"Option 4: {option4}")
        print(f"Answer: {answer}")
        print("")
        time.sleep(10)

        if existing_questions_for_team is not None:
            is_similar = False
            for q_text, q_answer in existing_questions_for_team:
                if bert_similarity(question, q_text) > 0.90:
                    if answer == q_answer:
                        is_similar = True

            if is_similar:
                print("Question is similar to existing question")
                print("")
                continue

            # if is_similar:
            #     row = Duplicate(
            #         question=question,
            #         answer=answer,
            #         team=team,
            #         topic=question_type,
            #     )
            #     db.session.add(row)
            #     db.session.commit()
            #     print("Question added to the duplicate table")

        if question_type == "History":
            # Check if Question is definitive
            definitive = is_question_definitive(question, answer)

        if not definitive:
            print("Question doesn't have a single diffinitive answer, next question")
            print("")
            continue

        #         if not definitive:
        #             row = Vague(
        #                 question=question,
        #                 answer=answer,
        #                 team=team,
        #                 topic=question_type,
        #             )
        #             db.session.add(row)
        #             db.session.commit()
        #             print("Question added to the vague table")
        #             call_count = 0
        #             continue

        if question_type == "History":
            correct = is_answer_correct(question, answer, question_type)

        if not correct:
            print("Answer is not correct, next question")
            print("")
            continue

        #         if not correct:
        #             row = Accuracy(
        #                 question=question,
        #                 answer=answer,
        #                 team=team,
        #                 topic=question_type,
        #             )
        #             db.session.add(row)
        #             db.session.commit()
        #             print("Question added to the accuracy table")
        #             call_count = 0
        #             continue

        if question_type == "History":
            row = HistoryQuestion(
                question=question,
                option1=option1,
                option2=option2,
                option3=option3,
                option4=option4,
                answer=answer,
                team=team,
            )
            db.session.add(row)
            db.session.commit()
            continue

        if question_type == "Live Game Play-by-Play":
            row = LiveQuestion(
                question=question,
                option1=option1,
                option2=option2,
                option3=option3,
                option4=option4,
                answer=answer,
                team=team,
                game_id=game_id,
            )
            db.session.add(row)
            db.session.commit()
            continue

    return print("All data has been presented accordingly")


def create_question_from_chatgpt_old(question_type, game_id, team, week):
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
        nfl_fact = chatgpt_prompt_num_4(question_type, summary, team, week)
    else:
        topic = "Team History"
        nfl_fact = chatgpt_prompt_num_4(question_type, None, team, None)

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

            elif question_type == "Live Game Play-by-Play":
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

            if question_type == "Live Game Play-by-Play":
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
