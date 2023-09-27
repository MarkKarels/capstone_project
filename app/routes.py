from flask import render_template, jsonify, request
from app import app, scheduler, chatGPT, fetchdata
import requests
from app.model import Roster, Game


@app.route('/')
def quiz():
    return render_template('index.html')


@app.route('/start_scheduler', methods=['GET'])
def start_scheduler():
    scheduler.add_job(id='Fetch NFL Data Job', func=fetchdata.fetch_game_data(), trigger='interval', minutes=5)
    return "Scheduler started", 200


@app.route('/generate_question', methods=['POST'])
def generate_question_route():
    data = request.get_json()
    selected_team = data.get("team", "Chicago Bears")
    team_alias = fetchdata.get_team_alias(selected_team)

    # Loop through all weeks to check if data exists
    for week in range(1, 19):
        # Check if roster data exists for the selected team for the given week
        roster_exists = Roster.query.filter_by(team=team_alias).first()
        if not roster_exists:
            fetchdata.fetch_roster_data(team_alias)

        # Check if game data exists for the selected team for the given week
        game_exists = Game.query.filter((Game.home_team == team_alias) | (Game.away_team == team_alias)).filter_by(week_num=week).first()
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

    question, options, correct_option = chatGPT.create_question_from_chatgpt('history', None, None, selected_team)

    return jsonify({
        "question": question,
        "options": options,
        "correct_option": correct_option
    })
