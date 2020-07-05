
import requests

from tabulate import tabulate

from teams import TEAMS

# TODO - (cleanup) split into modules for CLI, data, API calls

# TODO - (feature) add CLI args (date, team, list nplays, autorefresh)

# TODO - (feature) add header with teams, weather, stadium, time, record

# TODO - (feature) figure out how live data will look
# current inning
# at bat and pitching
# count
# bases
# game status (don't refresh if final)


def main():

    # cli args data
    team_arg = 'mets'
    date_arg = '2019-09-27'

    # find team id based on pre-fetched config data
    teams = [
        x for x in TEAMS
        if team_arg in x['name'].lower() or team_arg in x['abbr'].lower()
    ]
    if not teams:
        exit(f'Could not find team using search term "{team_arg}"')
    elif len(teams) > 1:
        matches = [f"{x['name']} ({x['abbr']})" for x in teams]
        exit(f'Matched too many teams with search term "{team_arg}" => {matches}')  # noqa:E501
    team = teams[0]

    # find game for team-date combo
    game = find_game(date_arg, team['id'])
    if not game:
        exit(f"Unable to find game on {date_arg} for {team['name']}")

    # get details about game
    game_details = game_data(game['gamePk'])
    live_data = game_details['liveData']

    line_score = line_score_table(live_data)
    box_score = box_score_table(live_data)

    print(tabulate(
        [
            [line_score],
            [box_score]
        ],
        tablefmt='plain',
        stralign='center'
    ))


def box_score_table(live_data):
    box_score = live_data['boxscore']
    return tabulate(
        [
            [
                box_score_batting_table('away', box_score),
                box_score_batting_table('home', box_score)
            ],
            [
                box_score_pitching_table('away', live_data),
                box_score_pitching_table('home', live_data)
            ]
        ],
        tablefmt='fancy_grid'
    )


def box_score_batting_table(team, box_score, table_format='simple'):
    players = box_score['teams'][team]['players']
    lineup = [x for _, x in players.items() if 'battingOrder' in x]
    sorted_lineup = sorted(lineup, key=lambda k: k['battingOrder'])

    def display_order(batter):
        batting_order = int(batter['battingOrder'])
        if not batting_order % 100:
            return int(batting_order / 100)
        return ''

    return tabulate(
        [
            [
                display_order(x),
                x['position']['abbreviation'],
                x['person']['fullName'],
                x['stats']['batting']['atBats'],
                x['stats']['batting']['hits'],
                x['stats']['batting']['runs'],
                x['stats']['batting']['rbi'],
                x['stats']['batting']['baseOnBalls'],
                x['stats']['batting']['strikeOuts']
            ]
            for x in sorted_lineup
        ],
        headers=['#', 'POS', 'Name', 'AB', 'H', 'R', 'RBI', 'BB', 'SO'],
        tablefmt=table_format
    )


def box_score_pitching_table(team, live_data, table_format='simple'):
    # parse live events to find pitchers in game order
    plays = live_data['plays']['allPlays']
    pitcher_ids = {
        x['matchup']['pitcher']['id']: 1
        for x in plays
        if (
            x['about']['isTopInning'] and team == 'home'
            or
            not x['about']['isTopInning'] and team == 'away'
        )
    }.keys()
    pitchers = [
        live_data['boxscore']['teams'][team]['players'][f'ID{x}']
        for x in pitcher_ids
    ]
    return tabulate(
        [
            [
                x['person']['fullName'],
                x['stats']['pitching']['inningsPitched'],
                x['stats']['pitching']['hits'],
                x['stats']['pitching']['runs'],
                x['stats']['pitching']['earnedRuns'],
                x['stats']['pitching']['baseOnBalls'],
                x['stats']['pitching']['strikeOuts']
            ]
            for x in pitchers
        ],
        headers=['Name', 'IP', 'H', 'R', 'ER', 'BB', 'SO'],
        tablefmt=table_format
    )


def line_score_table(live_data, table_format='fancy_grid'):
    box_score = live_data['boxscore']
    line_score = live_data['linescore']

    home_team = box_score['teams']['home']['team']['name']
    home_team_hits = line_score['teams']['home']['hits']
    home_team_runs = line_score['teams']['home']['runs']
    home_team_errors = line_score['teams']['home']['errors']

    away_team = box_score['teams']['away']['team']['name']
    away_team_hits = line_score['teams']['away']['hits']
    away_team_runs = line_score['teams']['away']['runs']
    away_team_errors = line_score['teams']['away']['errors']

    inning_scores = line_score['innings']
    placeholders = ['-'] * (9 - len(inning_scores))
    home_inning_scores = [
        x['home'].get('runs', 'x')  # handle bottom 9th not being played
        for x in inning_scores
    ] + placeholders
    away_inning_scores = [
        x['away']['runs']
        for x in inning_scores
    ] + placeholders

    labels = tabulate(
        [
            [away_team],
            [home_team]
        ],
        headers=[''],
        tablefmt=table_format,
        stralign='left'
    )
    innings = tabulate(
        [
            away_inning_scores,
            home_inning_scores
        ],
        headers=range(1, len(home_inning_scores) + 1),
        tablefmt=table_format,
        numalign='center',
        stralign='center'
    )
    totals = tabulate(
        [
            [away_team_runs, away_team_hits, away_team_errors],
            [home_team_runs, home_team_hits, home_team_errors],
        ],
        headers=['R', 'H', 'E'],
        tablefmt=table_format,
        numalign='right'
    )

    return tabulate(
        [
            [labels, innings, totals]
        ],
        tablefmt='plain'
    )


def find_game(day, team_id):
    url = 'https://statsapi.mlb.com/api/v1/schedule'
    params = {
        'date': day,
        'language': 'en',
        'sportId': 1,
        'teamId': team_id
    }
    response = requests.get(url, params=params)
    data = response.json()
    dates = data['dates']
    if not dates:
        return None
    return dates[0]['games'][-1]


def game_data(game_id):
    url = f'https://statsapi.mlb.com/api/v1.1/game/{game_id}/feed/live'
    response = requests.get(url)
    return response.json()


if __name__ == '__main__':
    main()
