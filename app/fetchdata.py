import requests
import json
import os
from sqlalchemy import or_

from app import app
from app.model import *
import time

app.config.from_object("config")


def fetch_team_data():
    try:
        response = requests.get(app.config["SPORTSRADAR_API_ENDPOINT_TEAM"])
        response.raise_for_status()
        data = response.json()

        parsed_data = []
        for conference in data.get("conferences", []):
            for division in conference.get("divisions", []):
                for team in division.get("teams", []):
                    parsed_data.append(
                        {"id": team.get("id"), "alias": team.get("alias")}
                    )

        directory = "app/team_data"
        if not os.path.exists(directory):
            os.makedirs(directory)

        with open(os.path.join(directory, "2023_NFL_TEAM_DATA"), "w") as json_file:
            json.dump(parsed_data, json_file, indent=4)

        print("Data Fetched and saved successfully")
    except requests.exceptions.RequestException as e:
        print(f"Error: {str(e)}")


def fetch_schedule():
    try:
        response = requests.get(app.config["SPORTSRADAR_API_ENDPOINT_SCHEDULE"])
        response.raise_for_status()
        data = response.json()

        parsed_data = []
        for week in data["weeks"]:
            week_id = week["id"]
            week_title = week["title"]
            for game in week["games"]:
                game_details = {
                    "Week ID": week_id,
                    "Week Number": week_title,
                    "Game ID": game["id"],
                    "Home Team": game["home"]["alias"],
                    "Away Team": game["away"]["alias"],
                }
                parsed_data.append(game_details)

        directory = "app/schedule_data"
        if not os.path.exists(directory):
            os.makedirs(directory)

        with open(os.path.join(directory, "2023_NFL_SCHEDULE"), "w") as json_file:
            json.dump(parsed_data, json_file, indent=4)

        print("Data Fetched and saved successfully")
    except requests.exceptions.RequestException as e:
        print(f"Error: {str(e)}")
        print(f"Failed to fetch the data. Error: {str(e)}")


def fetch_roster_data(team_alias):
    print("Executed Fetch Roster Data Method")
    if team_alias is None:
        print("No team alias provided")
        return
    # Step 1: Read the "2023_NFL_SCHEDULE" JSON file to get game ID for the given week and team.
    with open("app/team_data/2023_NFL_TEAM_DATA", "r") as json_file:
        team_data = json.load(json_file)

    team_id = None
    for team in team_data:
        if team["alias"] == str(team_alias):
            team_id = team["id"]
            break

    if not team_id:
        print(f"No team found for team {team_alias}")

    roster_url = f"http://api.sportradar.us/nfl/official/trial/v7/en/teams/{team_id}/full_roster.json?api_key={app.config['SPORTSRADAR_API_KEY']}"
    response = requests.get(roster_url)
    response.raise_for_status()
    roster_data = response.json()

    # Step 2: Extract the players from the roster data
    players = roster_data.get("players", [])

    # Step 3: Filter out players based on their status and add them to the database.
    for player in players:
        if player.get("status") == "ACT":
            roster_entry = Roster.query.filter_by(
                jerseyNum=player["jersey"], team=team_alias
            ).first()
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
                    position=player["position"],
                )
                db.session.add(roster_entry)

    db.session.commit()  # Commit the changes to the database.

    print(f"Roster data fetched and saved to database for team {team_alias}")


def fetch_all_game_data_for_season():
    """Fetch game data for the entire season."""
    # Load the schedule data from the 2023_NFL_SCHEDULE JSON file
    with open("app/schedule_data/2023_NFL_SCHEDULE", "r") as json_file:
        schedule_data = json.load(json_file)

    for key in team_mapping:
        for game in schedule_data:
            if (
                game["Home Team"] == key
                and not db.session.query(
                    db.exists().where(Game.id == game["Game ID"])
                ).scalar()
            ):
                game_entry = Game(
                    id=game["Game ID"],
                    home_team=game["Home Team"],
                    away_team=game["Away Team"],
                    week_num=game["Week Number"],
                )
                db.session.add(game_entry)
    db.session.commit()


def fetch_game_data(week_number, game_id, team_alias):
    play_by_play_url = f"http://api.sportradar.us/nfl/official/trial/v7/en/games/{game_id}/pbp.json?api_key={app.config['SPORTSRADAR_API_KEY']}"

    retries = 3
    delay = 1
    for i in range(retries):
        try:
            response = requests.get(play_by_play_url)
            response.raise_for_status()
            game_data = response.json()
            break
        except requests.exceptions.RequestException as e:
            print(f"Attempt {i + 1} Error: {str(e)}")
            if i < retries - 1:
                print(f"Waiting for {delay} seconds before retrying...")
                time.sleep(delay)
            else:
                print("Max retries reached. Failed to fetch the data.")
                return

    organized_data = {}
    for period in game_data["periods"]:
        quarter = period["number"]
        plays = []
        for sequence in period["pbp"]:
            if "events" in sequence:
                for event in sequence["events"]:
                    if "clock" in event and "description" in event:
                        existing_play = Play.query.filter_by(
                            game_id=game_id, quarter=quarter, timestamp=event["clock"]
                        ).first()

                        if existing_play:
                            # Update the existing entry
                            existing_play.description = event["description"]
                        else:
                            play_info = Play(
                                game_id=game_id,
                                play_id=get_next_play_id_for_game(game_id),
                                week_num=week_number,
                                quarter=quarter,
                                timestamp=event["clock"],
                                description=event["description"],
                            )
                            db.session.add(play_info)

        organized_data[f"Quarter {quarter}"] = plays
    db.session.commit()  # Commit the changes to the database.

    print(
        f"Play-by-play data fetched and saved to database for week {week_number}, team {team_alias}"
    )


def get_next_play_id_for_game(game_id):
    last_play = (
        Play.query.filter_by(game_id=game_id).order_by(Play.play_id.desc()).first()
    )
    if last_play:
        return last_play.play_id + 1
    else:
        return 1


def get_game_id_from_schedule(team_alias, week_number):
    schedule_path = "app/schedule_data/2023_NFL_SCHEDULE"

    with open(schedule_path, "r") as file:
        schedule_data = json.load(file)

        # Searching for the matching game based on team_alias and week_number
        for game in schedule_data:
            if game["Week Number"] == week_number and (
                game["Home Team"] == team_alias or game["Away Team"] == team_alias
            ):
                return game["Game ID"]

    return None


def get_team_alias(full_team_name):
    """Given a full team name, retrieve its alias."""
    return next(
        (alias for alias, name in team_mapping.items() if name == full_team_name), None
    )


team_mapping = {
    "ARI": "Arizona Cardinals",
    "ATL": "Atlanta Falcons",
    "BAL": "Baltimore Ravens",
    "BUF": "Buffalo Bills",
    "CAR": "Carolina Panthers",
    "CHI": "Chicago Bears",
    "CIN": "Cincinnati Bengals",
    "CLE": "Cleveland Browns",
    "DAL": "Dallas Cowboys",
    "DEN": "Denver Broncos",
    "DET": "Detroit Lions",
    "GB": "Green Bay Packers",
    "HOU": "Houston Texans",
    "IND": "Indianapolis Colts",
    "JAC": "Jacksonville Jaguars",
    "KC": "Kansas City Chiefs",
    "LV": "Las Vegas Raiders",
    "LAC": "Los Angeles Chargers",
    "LA": "Los Angeles Rams",
    "MIA": "Miami Dolphins",
    "MIN": "Minnesota Vikings",
    "NE": "New England Patriots",
    "NO": "New Orleans Saints",
    "NYG": "New York Giants",
    "NYJ": "New York Jets",
    "PHI": "Philadelphia Eagles",
    "PIT": "Pittsburgh Steelers",
    "SF": "San Francisco 49ers",
    "SEA": "Seattle Seahawks",
    "TB": "Tampa Bay Buccaneers",
    "TEN": "Tennessee Titans",
    "WAS": "Washington Commanders",
}
