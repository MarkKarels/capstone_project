from flask import render_template, jsonify, request
from sqlalchemy import func

from app import app, scheduler, chatGPT, fetchdata
import requests
from app.model import Roster, Game, Question


@app.route('/')
def quiz():
    start_scheduler()
    return render_template('index.html')


@app.route('/generate_question', methods=['POST'])
def generate_question_route():
    data = request.get_json()
    selected_team = data.get("team", "Chicago Bears")
    team_alias = fetchdata.get_team_alias(selected_team)

    question_count = Question.query.filter_by(team=selected_team).count()

    if question_count > 5:
        existing_question = Question.query.filter_by(team=selected_team).order_by(func.random()).first()
        question = existing_question.question
        options = [existing_question.option1, existing_question.option2, existing_question.option3,
                   existing_question.option4]
        correct_option = existing_question.answer

    else:
        for week in range(1, 19):
            roster_exists = Roster.query.filter_by(team=team_alias).first()
            if not roster_exists:
                fetchdata.fetch_roster_data(team_alias)

            game_exists = (Game.query.filter((Game.home_team == team_alias) | (Game.away_team == team_alias)).filter_by
                           (week_num=week).first())
            if not game_exists:
                try:
                    fetchdata.fetch_game_data(week, team_alias)
                except requests.exceptions.HTTPError as err:
                    if err.response.status_code == 403:
                        print(f"HTTP 403 error encountered for week {week} and team {team_alias}. Exiting loop.")
                        break
                    else:
                        print(
                            f"HTTP error occurred for week {week} and team {team_alias}: {err}")
        question, options, correct_option = chatGPT.create_question_from_chatgpt('history', None,
                                                                                 None, selected_team)
        generate_question_route()

    return jsonify({
        "question": question,
        "options": options,
        "correct_option": correct_option
    })


def start_scheduler():
    scheduler.add_job(id='Fetch NFL Data Job', func=fetchdata.fetch_game_data, args=[4, 'Chicago Bears'],
                      trigger='interval', minutes=5)
    return "Scheduler started", 200
