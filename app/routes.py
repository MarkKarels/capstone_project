import random
import torch
import openai
import requests
import json
import os

from flask import render_template, jsonify, request
from transformers import BertTokenizer, BertModel
from sklearn.metrics.pairwise import cosine_similarity
from app import app, scheduler
from app.model import *
from datetime import time

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


@app.route('/start_scheduler', methods=['GET'])
def start_scheduler():
    scheduler.add_job(id='Fetch NFL Data Job', func=fetch_game_data, trigger='interval', minutes=5)
    return "Scheduler started", 200


@app.route('/generate_question', methods=['POST'])
def generate_question_route():
    data = request.get_json()
    selected_team = data.get("team", "Chicago Bears")  # Default to Chicago Bears if no team is provided
    question, options, correct_option = generate_team_history_question(selected_team)

    return jsonify({
        "question": question,
        "options": options,
        "correct_option": correct_option
    })


@app.route("/fetch_team_data", methods=["GET"])
def fetch_team_data():
    try:
        response = requests.get(app.config['SPORTSRADAR_API_ENDPOINT_TEAM'])
        response.raise_for_status()
        data = response.json()

        parsed_data = []
        for conference in data.get("conferences", []):
            for division in conference.get("divisions", []):
                for team in division.get("teams", []):
                    parsed_data.append({
                        "id": team.get("id"),
                        "alias": team.get("alias")
                    })

        directory = 'app/team_data'
        if not os.path.exists(directory):
            os.makedirs(directory)

        with open(os.path.join(directory, '2023_NFL_TEAM_DATA'), 'w') as json_file:
            json.dump(parsed_data, json_file, indent=4)

        print("Data Fetched and saved successfully")
        return "Data Fetched and saved successfully", 200
    except requests.exceptions.RequestException as e:
        print(f"Error: {str(e)}")
        return f"Failed to fetch the data. Error: {str(e)}", 500


@app.route("/fetch_schedule", methods=["GET"])
def fetch_schedule():
    try:
        response = requests.get(app.config['SPORTSRADAR_API_ENDPOINT_SCHEDULE'])
        response.raise_for_status()
        data = response.json()

        parsed_data = []
        for week in data['weeks']:
            week_id = week['id']
            week_title = week['title']
            for game in week['games']:
                game_details = {
                    "Week ID": week_id,
                    "Week Number": week_title,
                    "Game ID": game['id'],
                    "Home Team": game['home']['alias'],
                    "Away Team": game['away']['alias']
                }
                parsed_data.append(game_details)

        directory = 'app/schedule_data'
        if not os.path.exists(directory):
            os.makedirs(directory)

        with open(os.path.join(directory, '2023_NFL_SCHEDULE'), 'w') as json_file:
            json.dump(parsed_data, json_file, indent=4)

        print("Data Fetched and saved successfully")
        return "Data Fetched and saved successfully", 200
    except requests.exceptions.RequestException as e:
        print(f"Error: {str(e)}")
        return f"Failed to fetch the data. Error: {str(e)}", 500


@app.route("/fetch_roster_data/<string:team_alias>", methods=["GET"])
def fetch_roster_data(team_alias):
    # Step 1: Read the "2023_NFL_SCHEDULE" JSON file to get game ID for the given week and team.
    with open("app/team_data/2023_NFL_TEAM_DATA", "r") as json_file:
        team_data = json.load(json_file)

    team_id = None
    for team in team_data:
        if team["alias"] == str(team_alias):
            team_id = team["id"]
            break

    if not team_id:
        return f"No team found for team {team_alias}", 404

    roster_url = f"http://api.sportradar.us/nfl/official/trial/v7/en/teams/{team_id}/full_roster.json?api_key={app.config['SPORTSRADAR_API_KEY']}"
    response = requests.get(roster_url)
    response.raise_for_status()
    roster_data = response.json()

    # Step 2: Extract the players from the roster data
    players = roster_data.get("players", [])

    # Step 3: Filter out players based on their status and add them to the database.
    for player in players:
        if player.get("status") == "ACT":
            roster_entry = Roster.query.filter_by(jerseyNum=player["jersey"], team=team_alias).first()
            if roster_entry:
                # Update attributes if the entry exists
                roster_entry.fullName = player["name"]
                roster_entry.abbrName = player.get("abbr_name", "")
                roster_entry.position = player["position"]
            else:
                # Create a new entry if it doesn't exist
                roster_entry = Roster(
                    jerseyNum=player["jersey"],
                    team=team_alias,
                    fullName=player["name"],
                    abbrName=player.get("abbr_name", ""),
                    position=player["position"]
                )
                db.session.add(roster_entry)

    db.session.commit()  # Commit the changes to the database.

    return f"Roster data fetched and saved to database for team {team_alias}", 200


@app.route("/fetch_game_data/<int:week_number>/<string:team_alias>", methods=["GET"])
def fetch_game_data(week_number, team_alias):
    # Step 1: Read the "2023_NFL_SCHEDULE" JSON file to get game ID for the given week and team.
    with open("app/schedule_data/2023_NFL_SCHEDULE", "r") as json_file:
        schedule_data = json.load(json_file)

    game_id = None
    home_team = None
    away_team = None
    for game in schedule_data:
        if game["Week Number"] == str(week_number) and (game["Home Team"] == team_alias or game["Away Team"] == team_alias):
            game_id = game["Game ID"]
            home_team = game["Home Team"]
            away_team = game["Away Team"]
            break

    if not game_id:
        return f"No game found for week {week_number} and team {team_alias}", 404

    # Check if game already exists in the database
    existing_game = Game.query.filter_by(home_team=home_team, away_team=away_team, week_num=week_number).first()

    if not existing_game:
        # Create new game entry
        game_entry = Game(id=game_id, home_team=home_team, away_team=away_team, week_num=week_number)
        db.session.add(game_entry)
        db.session.commit()

    else:
        game_entry = existing_game

    # Step 2: Use the game ID to get the play-by-play data.
    play_by_play_url = f"http://api.sportradar.us/nfl/official/trial/v7/en/games/{game_id}/pbp.json?api_key={app.config['SPORTSRADAR_API_KEY']}"
    response = requests.get(play_by_play_url)
    response.raise_for_status()
    game_data = response.json()

    # Organize play-by-play data by quarter
    organized_data = {}
    for period in game_data['periods']:
        quarter = period['number']
        plays = []
        for sequence in period['pbp']:
            if 'events' in sequence:
                for event in sequence['events']:
                    if 'clock' in event and 'description' in event:
                        existing_play = Play.query.filter_by(game_id=game_id, quarter=quarter,
                                                             timestamp=event['clock']).first()

                        if existing_play:
                            # Update the existing entry
                            existing_play.description = event['description']
                        else:
                            play_info = Play(
                                game_id=game_id,
                                play_id=get_next_play_id_for_game(game_id),
                                week_num=week_number,
                                quarter=quarter,
                                timestamp=event['clock'],
                                description=event['description']
                            )
                            db.session.add(play_info)

        organized_data[f"Quarter {quarter}"] = plays
    db.session.commit()  # Commit the changes to the database.

    return f"Play-by-play data fetched and saved to database for week {week_number}, team {team_alias}", 200


def get_next_play_id_for_game(game_id):
    last_play = Play.query.filter_by(game_id=game_id).order_by(Play.play_id.desc()).first()
    if last_play:
        return last_play.play_id + 1
    else:
        return 1


def chatgpt_conversation(prompt):
    response = openai.ChatCompletion.create(
        model=MODEL_ID,
        messages=[{"role": "user",
                   "content": prompt}]
    )

    return response["choices"][0]["message"]["content"]


def generate_team_history_question(team):
    global call_count
    global MAX_CALL

    for _ in range(MAX_CALL):
        if call_count >= MAX_CALL:
            print("Reached Max Call Count: Cannot Generate New Question")
            return None, None, None

        difficulty, chosen_sub_topic = generate_history_question_topic()
        print(chosen_sub_topic)
        call_count += 1
        nfl_fact = chatgpt_conversation(
            f"Give me a unique {difficulty} level difficulty multiple choice quiz question about the {team}'s "
            f"{chosen_sub_topic}. Ensure that the question is below 255 characters and each answer is no more than "
            f"7 words. The options provided should be contextually relevant to the question; for example, if asking "
            f"about a defensive record like interceptions, only list players known for playing in defensive positions. "
            f"Avoid opinion/subjective questions and answers, and stick strictly to factual information. Provide four "
            f"options and the correct answer.")
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
                question = question_details[0].split(':')[1].strip()
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
                        break
                    else:
                        # If answers are different, we can continue looking or decide on other logic
                        continue

            if not is_similar:
                db_store(question, options, correct_option, team)
                return question, options, correct_option

        except Exception as e:
            print(f"An error occurred: {e}")

    print('End of the line')
    return None, None, None


@app.route("/generate_play_by_play_question/<string:game_id>/<int:quarter>", methods=["GET"])
def generate_play_by_play_question(game_id, quarter):
    global call_count
    global MAX_CALL

    game = Game.query.filter_by(id=game_id).first()
    if not game:
        return "Game not found.", 404

    quarter_plays = Play.query.filter_by(game_id=game_id, quarter=quarter).all()

    if not quarter_plays:
        return f"No data found for Quarter {quarter}.", 404

    # Convert quarter data to a readable format for ChatGPT
    quarter_summary = ". ".join([f"{play.timestamp} - {play.description}" for play in quarter_plays])

    for _ in range(MAX_CALL):
        if call_count >= MAX_CALL:
            print("Reached Max Call Count: Cannot Generate New Question")
            return None, None, None

        call_count += 1
        nfl_fact = chatgpt_conversation(
            f"Based on the following plays from Quarter {quarter}: \"{quarter_summary}\", generate a unique multiple "
            f"choice quiz question from big plays. Ensure that the question is below 255 characters and each answer is "
            f"no more than 7 words. Provide four options and the correct answer. Please provide as much detail as "
            f"possible including but not limited to time left in quarter. If known, give full player names as options.")

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
        return f"Question Answer Generated", 200
    return None, None, None


def db_store(question, options, correct_option, team):
    row = Question(question=question, option1=options[0], option2=options[1], option3=options[2], option4=options[3],
                   answer=correct_option, team=team)
    db.session.add(row)
    db.session.commit()


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
