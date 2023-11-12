from flask import render_template, jsonify, request
from app import app, db, scheduler, chatGPT, fetchdata
from app.model import *
from datetime import date
import random
from sqlalchemy import func


@app.route("/", methods=["GET", "POST"])
def index():
    return render_template("index.html")


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
    questions = Question.query.order_by(func.random()).limit(5).all()
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


@app.route("/getQuestion", methods=["GET", "POST"])
def fill_question_bank():
    try:
        for i in range(32):
            question_type = random.choice(["history", "pbp_current"])
            selected_team = random.choice(teams)
            team_alias = fetchdata.get_team_alias(selected_team)
            print(team_alias)
            roster_exists = Roster.query.filter_by(team=team_alias).first()
            if not roster_exists:
                fetchdata.fetch_roster_data(team_alias)
            week_number = None
            for game_date in sorted(season2023.keys(), reverse=True):
                if date.fromisoformat(game_date) <= date.today():
                    week_number = season2023[game_date]
                    break
            fetchdata.fetch_game_data(week_number, team_alias)

            if question_type == "pbp_current":
                current_week = week_number
                game_id = fetchdata.get_game_id_from_schedule(team_alias, current_week)
                chatGPT.create_question_from_chatgpt(
                    question_type, game_id, selected_team
                )
            else:
                chatGPT.create_question_from_chatgpt(question_type, None, selected_team)
        return jsonify({"message": "Question bank filled successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def start_scheduler():
    scheduler.add_job(
        id="Fill Question Bank",
        func=fill_question_bank,
        trigger="interval",
        seconds=60,
        replace_existing=True,
    )
    return "Scheduler started", 200


def initialize_app():
    fetchdata.fetch_all_game_data_for_season()
    fill_question_bank()
    start_scheduler()


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
    "Washington Football Team",
    "Chicago Bears",
    "Green Bay Packers",
    "Detroit Lions",
    "Minnesota Vikings",
    "Kansas City Chiefs",
    "Las Angeles Chargers",
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
