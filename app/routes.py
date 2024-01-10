import time
from flask import render_template, jsonify, request
import openai
from app import app, db, scheduler, chatGPT, fetchdata
from app.model import *
from datetime import date
import random
from sqlalchemy import func


@app.route("/", methods=["GET", "POST"])
def index():
    return render_template("index.html")


@app.route("/generateQuestions", methods=["GET", "POST"])
def generateQuestions():
    next_question = True
    global game_id
    global question_type

    while next_question:
        history_question_count = HistoryQuestion.query.count()
        print("History question count: " + str(history_question_count))
        live_question_count = LiveQuestion.query.count()
        print("Live question count: " + str(live_question_count))
        duplicate_question_count_live = Duplicate.query.filter_by(
            topic="Live Game Play-by-Play"
        ).count()
        print("Duplicate question count live: " + str(duplicate_question_count_live))
        duplicate_question_count_history = Duplicate.query.filter_by(
            topic="Team History"
        ).count()
        print(
            "Duplicate question count history: " + str(duplicate_question_count_history)
        )
        if history_question_count >= 50 and live_question_count >= 50:
            next_question = False
            break

        if history_question_count >= 50 or duplicate_question_count_live >= 30:
            question_type = "pbp_current"
            print("Only live questions left.")
        elif live_question_count >= 50 or duplicate_question_count_history >= 30:
            question_type = "history"
            print("Only history questions left.")
        else:
            question_type = random.choice(["history", "pbp_current"])
            print("Both types of questions left." + question_type + " selected.")

        selected_team = random.choice(teams)
        team_alias = fetchdata.get_team_alias(selected_team)

        if question_type == "pbp_current":
            week_number = random.randint(1, 17)
            game_id = fetchdata.get_game_id_from_schedule(team_alias, week_number)
            print("Game ID: " + str(game_id))
            if not game_id:
                print(
                    "No game found for "
                    + selected_team
                    + " in week "
                    + str(week_number)
                )
                continue
        else:
            game_id = None

        try:
            chatGPT.create_question_from_chatgpt(question_type, game_id, selected_team)
        except openai.error.RateLimitError as e:
            print(f"Rate limit reached. Pausing for 30 seconds. Error: {e}")
            time.sleep(30)

    return render_template("generate.html")


@app.route("/generatePlayByPlay", methods=["GET", "POST"])
def generatePlayByPlay():
    if Game.query.count() == 0:
        fetchdata.fetch_all_game_data_for_season()
        print("Schedule data fetched and saved to database.")

    for team in teams:
        team_alias = fetchdata.get_team_alias(team)
        print(team_alias)
        for week_number in range(1, 17):
            game_id_result = (
                Game.query.with_entities(Game.id)
                .filter(
                    (Game.week_num == week_number)
                    & ((Game.home_team == team_alias) | (Game.away_team == team_alias))
                )
                .first()
            )

            if game_id_result:
                game_id = game_id_result[0]
                if not Play.query.filter_by(game_id=game_id).first():
                    print(game_id)
                    fetchdata.fetch_game_data(week_number, game_id, team_alias)
                    print("Play-by-play data fetched and saved to database.")
                else:
                    print("Play-by-play data already exists in database.")

    return render_template("generate.html")


@app.route("/game", methods=["GET", "POST"])
def game():
    return render_template("game.html")


@app.route("/leaderboard", methods=["GET", "POST"])
def leaderboard():
    return render_template("leaderboard.html")


@app.route("/end", methods=["GET", "POST"])
def end():
    return render_template("end.html")


@app.route("/saveHighScore", methods=["POST"])
def save_high_score():
    try:
        data = request.get_json()
        print(f"Received data: {data}")  # Print the received data

        name = data.get("name")
        score = data.get("score")

        if not name or not score:
            print("Missing name or score")
            return jsonify({"error": "Missing name or score"}), 400

        new_score = Score(name=name, score=score)
        db.session.add(new_score)
        db.session.commit()

        print(f"Saved {name} - {score} to the database.")  # Confirm saving
        return jsonify({"message": "Score saved successfully"}), 200

    except Exception as e:
        print(f"An error occurred: {e}")  # Print the exception
        db.session.rollback()  # Rollback in case of an error
        return jsonify({"error": str(e)}), 500


@app.route("/getHighScores", methods=["GET"])
def get_high_scores():
    try:
        scores = Score.query.order_by(Score.score.desc()).limit(10).all()
        print(f"Fetched scores: {scores}")  # Print the fetched scores

        high_scores = [{"name": score.name, "score": score.score} for score in scores]
        return jsonify({"high_scores": high_scores}), 200
    except Exception as e:
        print(f"An error occurred: {e}")  # Print the exception
        return jsonify({"error": "An error occurred while fetching scores"}), 500


@app.route("/api/questions", methods=["GET", "POST"])
def get_questions():
    questions = HistoryQuestion.query.order_by(func.random()).limit(5).all()
    response = []

    for q in questions:
        options = [q.option1, q.option2, q.option3, q.option4]
        try:
            answer_index = options.index(q.answer) + 1
        except ValueError:
            answer_index = None

        response.append(
            {
                "question": q.question,
                "choice1": q.option1,
                "choice2": q.option2,
                "choice3": q.option3,
                "choice4": q.option4,
                "answer": answer_index,
            }
        )
    print(response)
    return jsonify(response)


def initialize_app():
    fetchdata.fetch_all_game_data_for_season()


season2023 = {
    "2023-09-11": 1,
    "2023-09-18": 2,
    "2023-09-25": 3,
    "2023-10-02": 4,
    "2023-10-09": 5,
    "2023-10-16": 6,
    "2023-10-23": 7,
    "2023-10-30": 8,
    "2023-11-06": 9,
    "2023-11-13": 10,
    "2023-11-20": 11,
    "2023-11-27": 12,
    "2023-12-04": 13,
    "2023-12-11": 14,
    "2023-12-18": 15,
    "2023-12-25": 16,
    "2024-01-01": 17,
    "2024-01-11": 18,
}

teams = [
    "Arizona Cardinals",
    "Los Angeles Rams",
    "San Francisco 49ers",
    "Seattle Seahawks",
    "Tampa Bay Buccaneers",
    "New Orleans Saints",
    "Carolina Panthers",
    "Atlanta Falcons",
    "Dallas Cowboys",
    "New York Giants",
    "Philadelphia Eagles",
    "Washington Commanders",
    "Chicago Bears",
    "Green Bay Packers",
    "Detroit Lions",
    "Minnesota Vikings",
    "Kansas City Chiefs",
    "Los Angeles Chargers",
    "Las Vegas Raiders",
    "Denver Broncos",
    "Houston Texans",
    "Indianapolis Colts",
    "Jacksonville Jaguars",
    "Tennessee Titans",
    "New England Patriots",
    "New York Jets",
    "Miami Dolphins",
    "Buffalo Bills",
    "Pittsburgh Steelers",
    "Baltimore Ravens",
    "Cleveland Browns",
    "Cincinnati Bengals",
]
