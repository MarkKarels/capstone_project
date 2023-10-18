from flask import render_template, jsonify, request
from sqlalchemy import func
import requests
import random

from app import app, scheduler, chatGPT, fetchdata
from datetime import date
from app.model import Roster, Game, Question


@app.route('/')
def quiz():
    fetchdata.fetch_all_game_data_for_season()
    return render_template('index.html')


@app.route('/generate_question', methods=['POST'])
def generate_question_route():
    data = request.get_json()
    selected_team = data.get("team", "Chicago Bears")
    team_alias = fetchdata.get_team_alias(selected_team)

    question_count = Question.query.filter_by(team=selected_team).count()
    print(question_count)
    roster_exists = Roster.query.filter_by(team=team_alias).first()
    if not roster_exists:
        fetchdata.fetch_roster_data(team_alias)

    today = str(date.today())
    for key, value in season2023.items():
        if today >= key:
            try:
                fetchdata.fetch_game_data(value, team_alias)
            except requests.exceptions.HTTPError as err:
                if err.response.status_code == 403:
                    print(f"HTTP 403 error encountered for week {value} and team {team_alias}. Exiting loop.")
                    break
                else:
                    print(
                        f"HTTP error occurred for week {value} and team {team_alias}: {err}")

    if question_count > 5:
        existing_question = Question.query.filter_by(team=selected_team).order_by(func.random()).first()
        question = existing_question.question
        options = [existing_question.option1, existing_question.option2, existing_question.option3,
                   existing_question.option4]
        correct_option = existing_question.answer

    else:
        for i in range(5):
            chatGPT.create_question_from_chatgpt('history', None,None, selected_team)
        existing_question = Question.query.filter_by(team=selected_team).order_by(func.random()).first()
        question = existing_question.question
        options = [existing_question.option1, existing_question.option2, existing_question.option3,
                   existing_question.option4]
        correct_option = existing_question.answer

    return jsonify({
        "question": question,
        "options": options,
        "correct_option": correct_option
    })


@app.route('/fill_question_bank', methods=['POST'])
def fill_question_bank():
    try:
        for i in range(20):
            selected_team = random.choice(teams)
            chatGPT.create_question_from_chatgpt('history', None, None, selected_team)
        return jsonify({'message': 'Question bank filled successfully'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


def start_scheduler():
    scheduler.add_job(id='Fetch NFL Data Job', func=fetchdata.fetch_game_data, args=[4, 'Chicago Bears'],
                      trigger='interval', minutes=5)
    return "Scheduler started", 200


season2023 = {
    '2023-09-11': 1,
    '2023-09-18': 2,
    '2023-09-25': 3,
    '2023-10-02': 4,
    '2023-10-09': 5,
    '2023-10-16': 6,
    '2023-10-23': 7,
    '2023-10-30': 8,
    '2023-11-06': 9,
    '2023-11-13': 10,
    '2023-11-20': 11,
    '2023-11-27': 12,
    '2023-12-04': 13,
    '2023-12-11': 14,
    '2023-12-18': 15,
    '2023-12-25': 16,
    '2024-01-01': 17,
    '2024-01-11': 18
}

teams = [
    'Arizona Cardinals',
    'Los Angeles Rams',
    'San Francisco 49ers',
    'Seattle Seahawks',
    'Tampa Bay Buccaneers',
    'New Orleans Saints',
    'Carolina Panthers',
    'Atlanta Falcons',
    'Dallas Cowboys',
    'New York Giants',
    'Philadelphia Eagles',
    'Washington Football Team',
    'Chicago Bears',
    'Green Bay Packers',
    'Detroit Lions',
    'Minnesota Vikings',
    'Kansas City Chiefs',
    'Las Angeles Chargers',
    'Las Vegas Raiders',
    'Denver Broncos',
    'Houston Texans',
    'Indianapolis Colts',
    'Jacksonville Jaguars',
    'Tennessee Titans',
    'New England Patriots',
    'New York Jets',
    'Miami Dolphins',
    'Buffalo Bills',
    'Pittsburgh Steelers',
    'Baltimore Ravens',
    'Cleveland Browns',
    'Cincinnati Bengals'
]
