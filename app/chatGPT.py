import random
import re
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
second_call = False


def is_question_definitive(question, answer):
    retry_count = 0
    max_retries = 5
    global second_call

    while retry_count < max_retries:
        try:
            response = chatgpt_conversation(
                f"Is the only correct answer to the question {question} the following: {answer}?"
                f"Please only respond with Yes or No. Do not give further details in your response."
                f"If unsure in any way, please respond with maybe."
            )

            response = clean_string(response.lower())

            if "yes" in response:
                print("")
                print(question + ": This Question Contains Only One Answer")
                second_call = False
                return True, question
            elif "no" in response:
                if not second_call:
                    second_call = True
                    question = can_question_be_reworded(question, answer)
                    return is_question_definitive(question, answer)
                print("")
                print(
                    question
                    + ": This Question Contains MORE THAN One Answer and CANNOT be reworded"
                )
                second_call = False
                return False, question
            else:
                print("")
                print(
                    f"There was an issue with the response from is_question_definitive: Response came back as --> {response}"
                )
                print("")
                second_call = False
                return True, question
        except openai.error.RateLimitError as e:
            print("")
            print(
                f"Rate limit reached in is_question_definitive. Pausing for 30 seconds. Error: {e}"
            )
            time.sleep(15)
            retry_count += 1


def can_question_be_reworded(question, answer):
    response = chatgpt_conversation(
        f"Yes or No? Can the following question be changed to have a single, definitive answer that matches the answer: {answer}? "
        f"Question: {question}"
    )

    response = clean_string(response.lower())

    if "yes" in response:
        question = ask_again(question, answer)
        print(question + ": This Question Has Been Reworded")
        print("")
        return question
    else:
        return question


def ask_again(question, answer):
    return chatgpt_conversation(
        f"Change the following question so that it can have only a single, definitive answer of {answer}: {question} "
        f"Only return the question, do not respond with anything else. "
        f"Do not provide anything else in the response other than the requested information."
        f"Do not number each question. Do not put spaces before or after each question, options, and answer combination."
    )


def is_answer_correct(question, answer):
    retry_count = 0
    max_retries = 5
    global second_call

    while retry_count < max_retries:
        try:
            verify_response = chatgpt_conversation(
                f"Yes or No? The answer to the following question: {question} is: {answer}"
                f"Please only respond with Yes or No. Do not give further details in your response."
                f"If unsure in any way, please respond with maybe."
            )

            verify_response = clean_string(verify_response.lower())

            if "yes" in verify_response:
                print("")
                print(
                    question + ": This Answer Has Been Verified To Be True and Accurate"
                )
                second_call = False
                return True, answer
            elif "no" in verify_response:
                if not second_call:
                    second_call = True
                    answer = is_the_answer_known(question, answer)
                    return is_answer_correct(question, answer)
                print("")
                print(
                    question
                    + ": This Answer Cannot Be Verified As True and Accurate and Will Not Be Used"
                )
                second_call = False
                return False, answer
            else:
                print("")
                print(
                    f"There was an issue with the response from is_answer_correct: Response came back as --> {verify_response}"
                )
                second_call = False
                return True, answer
        except openai.error.RateLimitError as e:
            print("")
            print(
                f"Rate limit reached in is_answer_correct. Pausing for 30 seconds. Error: {e}"
            )
            time.sleep(15)
            retry_count += 1


def is_the_answer_known(question, answer):
    response = chatgpt_conversation(
        f"Yes or No? Do you know the answer to the following question: {question}"
        f"Please only respond with Yes or No. Do not give further details in your response."
        f"If unsure in any way, please respond with maybe."
    )

    response = clean_string(response.lower())

    if "yes" in response:
        answer = provide_correct_answer(question)
        print(question + ": This Question Has A New Answer")
        print("")
        return answer
    else:
        return answer


def provide_correct_answer(question):
    return chatgpt_conversation(
        f"Provide the correct answer to the following question: {question} "
        f"Only return the answer, do not respond with anything else. "
        f"Do not provide anything else in the response other than the requested information."
        f"Do not number each question. Do not put spaces before or after each question, options, and answer combination."
    )


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
                    f"Do not number each question. Do not put spaces before or after each question, options, and answer combination."
                )
                return prompt
            if question_type == "Live Game Play-by-Play":
                prompt = chatgpt_conversation(
                    f"Generate 10 unique multiple choice quiz questions based on this NFL game summary: {summary}. "
                    f"Each question should focus on plays made by the {team}. The summary data is formatted as follows: "
                    f"Quarter: quarter the play occured, Time Left: time left on the clock in the quarter, "
                    f"Play: A detailed summary of the play that occured in the game. Each play is seperated by a "
                    f"- character. Each question should be under 255 characters. "
                    f"Provide 4 options and 1 answer for each question, with the answer being no more than 7 words. "
                    f"Format: question \n option1 \n option2 \n option3 \n option4 \n answer. "
                    f"Maintain this format strictly without additional labels or text."
                    f"Do not provide anything else in the response other than the requested information."
                    f"Do not number each question. Do not put spaces after each question."
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
    if question_type == "History":
        prompt = chatgpt_conversation(
            f"Generate 10 unique multiple choice quiz questions about the {team}'s history, focusing on various aspects about the team. "
            f"Ensure to pull from the entire history of the {team}'s and make each question different from the next. Ask questions ranging in "
            f"difficulty that are definitive with one verified answer only. Verify the correct answer of each question before providing the response."
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
            f"Provide as much detail as possible about the play. Provide the team name(s) of the described play."
            f"Provide the quarter in which the play happened, as well as the time remaining in the quarter."
            f"Focus the questions on big plays from the game (i.e. touchdowns, interceptions, fumbles, "
            f"plays over 10 yards, negative plays, etc.). Construct the question in the form of a quiz game."
            f"Each question should focus on plays made by the {team}."
            f"Each question should be under 255 characters. "
            f"Provide 4 options and 1 answer for each question, with the answer being no more than 7 words. "
            f"Format: question \n option1 \n option2 \n option3 \n option4 \n answer. "
            f"Maintain this format strictly without additional labels or text."
            f"Do not provide anything else in the response other than the requested information."
            f"Do not number each question. Do not put spaces after each question."
        )
        return prompt
    return None


def chatgpt_prompt_num_3(question_type, summary, team):
    global topic

    if question_type == "History":
        prompt = chatgpt_conversation(
            f"Generate 10 unique multiple choice quiz questions about the {team}'s history, focusing on various aspects about the team. "
            f"Ensure to make each question different from the next and verify the answer provided is correct to the question given."
            f"Ask questions with only one, difinitive correct answer. Provide questions that can be used in a quiz game given to fans of the {team}'s. \n\n"
            f"Each question should be under 255 characters. If a date or year is given as an answer, make sure it is when the event occured, not the season "
            f"(i.e. the bears won the Superbowl in the 1985 season, but Superbowl XX occured in 1986. Therefore, the bears won Superbowl XX in 1986). "
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
            f"Each question should focus on plays made by the {team}. The summary data is formatted as follows: "
            f"Quarter: quarter the play occured, Time Left: time left on the clock in the quarter, "
            f"Play: A detailed summary of the play that occured in the game. Each play is seperated by a "
            f"- character. Each question should be under 255 characters. Construct the questions in the form of a quiz game."
            f"Provide as much detail as possible about the play. Only ask questions from big plays that occured "
            f"during the game. Keep the questions to what Actions were performed by what players. "
            f"Provide 4 options and 1 answer for each question, with the answer being no more than 7 words. "
            f"Response Format: question \n option1 \n option2 \n option3 \n option4 \n answer. "
            f"Maintain this format strictly without additional labels or text."
            f"Do not provide anything else in the response other than the requested information."
            f"Do not number each question. Do not put spaces after each question."
        )
        return prompt
    return None


def create_question_with_only_duplicate_check(question_type, game_id, team, week):
    is_similar = False
    existing_questions_for_team = None

    print("Question Type: " + question_type)
    print("Game ID: " + str(game_id))
    print("Team: " + team)
    print("")

    if question_type == "Live Game Play-by-Play":
        game = Game.query.filter_by(id=game_id).first()

        if not game:
            return "Game not found.", 404

        plays = Play.query.filter_by(game_id=game_id).all()

        if not plays:
            return f"No data found.", 404

        summary = ". ".join(
            [
                f"Quarter: {play.quarter}, Time Left: {play.timestamp}, Play: {play.description} - "
                for play in plays
            ]
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

    if len(question_details) <= 6:
        return print("Not enough data to generate a question")

    if question_type == "History":
        history_question_query = HistoryQuestion.query.filter_by(
            team=team
        ).with_entities(HistoryQuestion.question, HistoryQuestion.answer)

        existing_questions_for_team = db.session.execute(
            history_question_query
        ).fetchall()

    elif question_type == "Live Game Play-by-Play":
        live_question_query = LiveQuestion.query.filter_by(team=team).with_entities(
            LiveQuestion.question, LiveQuestion.answer
        )

        existing_questions_for_team = db.session.execute(live_question_query).fetchall()

    for i in range(0, len(question_details), 6):
        question_block = [
            clean_string(item.strip()) for item in question_details[i : i + 6]
        ]
        question, option1, option2, option3, option4, answer = question_block

        print(f"Question: {question}")
        print(f"Option 1: {option1}")
        print(f"Option 2: {option2}")
        print(f"Option 3: {option3}")
        print(f"Option 4: {option4}")
        print(f"Answer: {answer}")
        print("")

        question = question.strip()

        if answer.lower() not in [
            option1.lower(),
            option2.lower(),
            option3.lower(),
            option4.lower(),
        ]:
            row = Formatting(
                question=question,
                answer=answer,
                team=team,
                topic=question_type,
            )
            db.session.add(row)
            db.session.commit()
            print("Answer is not among the options. Adding to the Formatting table.")
            continue

        if existing_questions_for_team is not None:
            is_similar = False
            for q_text, q_answer in existing_questions_for_team:
                if bert_similarity(question, q_text) > 0.875 and answer == q_answer:
                    is_similar = True

            if is_similar:
                row = Duplicate(
                    question=question,
                    answer=answer,
                    team=team,
                    topic=question_type,
                )
                db.session.add(row)
                db.session.commit()
                print("Question added to the duplicate table")
                continue
        if question_type == "History":
            try:
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
                print("Question added to the history table")
                continue
            except Exception as e:
                try:
                    row = Duplicate(
                        question=question,
                        answer=answer,
                        team=team,
                        topic=question_type,
                    )
                    db.session.add(row)
                    db.session.commit()
                    print("Question added to the duplicate table")
                    continue
                except Exception as e:
                    print(f"An error occurred: {e}")
                    print(
                        f"Continue to the next question. {question} will not be added to the database."
                    )
                    continue

        if question_type == "Live Game Play-by-Play":
            try:
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
                print("Question added to the live game play-by-play table")
                continue
            except Exception as e:
                try:
                    row = Duplicate(
                        question=question,
                        answer=answer,
                        team=team,
                        topic=question_type,
                    )
                    db.session.add(row)
                    db.session.commit()
                    print("Question added to the duplicate table")
                    continue
                except Exception as e:
                    print(f"An error occurred: {e}")
                    print(
                        f"Continue to the next question. {question} will not be added to the database."
                    )
                    continue

    return print("All data has been presented accordingly")


def create_question_from_chatgpt(question_type, game_id, team):
    is_similar = False
    existing_questions_for_team = None

    print("Question Type: " + question_type)
    print("Game ID: " + str(game_id))
    print("Team: " + team)
    print("")

    if question_type == "Live Game Play-by-Play":
        game = Game.query.filter_by(id=game_id).first()

        if not game:
            return "Game not found.", 404

        plays = Play.query.filter_by(game_id=game_id).all()

        if not plays:
            return f"No data found.", 404

        summary = ". ".join(
            [
                f"Quarter: {play.quarter} Time Left: {play.timestamp} Play: {play.description}"
                for play in plays
            ]
        )

        print("Calling for Live Game Play-by-Play Questions from ChatGPT")
        print("")

        nfl_fact = chatgpt_prompt_num_3(question_type, summary, team)
    else:
        print("Calling for Team History Questions from ChatGPT")
        print("")

        nfl_fact = chatgpt_prompt_num_3(question_type, None, team)

    question_details = [line for line in nfl_fact.split("\n") if line.strip()]

    print(question_details)
    print("")

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

    elif question_type == "Live Game Play-by-Play":
        live_question_query = LiveQuestion.query.filter_by(team=team).with_entities(
            LiveQuestion.question, LiveQuestion.answer
        )
        accuracy_question_query = Accuracy.query.filter_by(team=team).with_entities(
            Accuracy.question, Accuracy.answer
        )
        vague_question_query = Vague.query.filter_by(team=team).with_entities(
            Vague.question, Vague.answer
        )

        unified_query = union(
            live_question_query,
            accuracy_question_query,
            vague_question_query,
        )
        existing_questions_for_team = db.session.execute(unified_query).fetchall()

    for i in range(0, len(question_details), 6):
        question_block = [
            clean_string(item.strip()) for item in question_details[i : i + 6]
        ]
        question, option1, option2, option3, option4, answer = question_block

        print(f"Question: {question}")
        print(f"Option 1: {option1}")
        print(f"Option 2: {option2}")
        print(f"Option 3: {option3}")
        print(f"Option 4: {option4}")
        print(f"Answer: {answer}")
        print("")

        question = question.strip()

        if answer.lower() not in [
            option1.lower(),
            option2.lower(),
            option3.lower(),
            option4.lower(),
        ]:
            row = Formatting(
                question=question,
                answer=answer,
                team=team,
                topic=question_type,
            )
            db.session.add(row)
            db.session.commit()
            print("Answer is not among the options. Adding to the Formatting table.")
            continue

        if existing_questions_for_team is not None:
            is_similar = False
            for q_text, q_answer in existing_questions_for_team:
                if bert_similarity(question, q_text) > 0.875 and answer == q_answer:
                    is_similar = True

            if is_similar:
                row = Duplicate(
                    question=question,
                    answer=answer,
                    team=team,
                    topic=question_type,
                )
                db.session.add(row)
                db.session.commit()
                print("Question added to the duplicate table")
                continue

        if question_type == "History":
            definitive, question = is_question_definitive(question, answer)

            if not definitive:
                row = Vague(
                    question=question,
                    answer=answer,
                    team=team,
                    topic=question_type,
                )
                db.session.add(row)
                db.session.commit()
                print("Question added to the vague table")
                continue

        if question_type == "History":
            correct, answer = is_answer_correct(question, answer)

            if not correct:
                row = Accuracy(
                    question=question,
                    answer=answer,
                    team=team,
                    topic=question_type,
                )
                db.session.add(row)
                db.session.commit()
                print("Question added to the accuracy table")
                continue

        if question_type == "History":
            try:
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
                print("Question added to the history table")
                continue
            except Exception as e:
                try:
                    row = Duplicate(
                        question=question,
                        answer=answer,
                        team=team,
                        topic=question_type,
                    )
                    db.session.add(row)
                    db.session.commit()
                    print("Question added to the duplicate table")
                    continue
                except Exception as e:
                    print(f"An error occurred: {e}")
                    print(
                        f"Continue to the next question. {question} will not be added to the database."
                    )
                    continue

        if question_type == "Live Game Play-by-Play":
            try:
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
                print("Question added to the live game play-by-play table")
                continue
            except Exception as e:
                try:
                    row = Duplicate(
                        question=question,
                        answer=answer,
                        team=team,
                        topic=question_type,
                    )
                    db.session.add(row)
                    db.session.commit()
                    print("Question added to the duplicate table")
                    continue
                except Exception as e:
                    print(f"An error occurred: {e}")
                    print(
                        f"Continue to the next question. {question} will not be added to the database."
                    )
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
                    if bert_similarity(question, q_text) > 0.875:
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


def clean_string(input_string):
    cleaned_string = re.sub(r"\s+", " ", input_string).strip()
    return cleaned_string
