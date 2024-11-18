from flask import Flask, render_template 
import requests
from datetime import date, datetime, timedelta
import folium
from folium.plugins import AntPath
import plotly.graph_objects as go
from flask_caching import Cache

app = Flask(__name__)

# Configure caching
app.config['CACHE_TYPE'] = 'SimpleCache'
app.cache = Cache(app)


@app.route('/')
@app.cache.cached(timeout=3600)  # Cache the route for 1 hour

def home():
    return render_template('index.html')

@app.route('/calender')
def calender():
    url = 'http://ergast.com/api/f1/current.json'
    response = requests.get(url)
    data = response.json()
    races = data['MRData']['RaceTable']['Races']

    # Find the next race
    today = datetime.today().date()
    next_race = None
    for race in races:
        race_date = datetime.strptime(race["date"], "%Y-%m-%d").date()
        if race_date >= today:
            if not next_race or race_date < datetime.strptime(next_race["date"], "%Y-%m-%d").date():
                next_race = race


    #next race time convert
    utc_time = datetime.strptime(next_race['time'], "%H:%M:%SZ")
    offset = timedelta(hours=5, minutes=30)

    local_time = utc_time + offset

    tracks = []
    for race in races:
        track = {
            "name": race['Circuit']['circuitName'],
            "location": f"{race['Circuit']['Location']['locality']}, {race['Circuit']['Location']['country']}",
            "latitude": float(race['Circuit']['Location']['lat']),
            "longitude": float(race['Circuit']['Location']['long'])
        }
        tracks.append(track)

    # Initialize the map centered globally
    world_map = folium.Map(location=[20, 0], zoom_start=2, tiles=None)

    folium.TileLayer(
    tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
    attr="Tiles &copy; Esri &mdash; Source: Esri, DeLorme, NAVTEQ",
    name="ESRI Satellite"
    ).add_to(world_map)

    folium.LayerControl().add_to(world_map)

    #add ant path
    AntPath(
    [[track['latitude'], track['longitude']] for track in tracks],
    color='blue', weight=2.5
    ).add_to(world_map)

    # Add markers for each track
    for track in tracks:
        folium.Marker(
            location=[track["latitude"], track["longitude"]],
            popup=f"<b>{track['name']}</b><br>{track['location']}",
            icon=folium.CustomIcon('static/assets/location-icon.png', icon_size=(30, 30))
        ).add_to(world_map)

    

    # Save the map as an HTML object
    map_html = world_map._repr_html_()  # Render the map as HTML


    return render_template('calender.html', races=races, date=date, datetime=datetime, next_race=next_race, local_time=local_time.time(), map_html=map_html)


def get_driver_points_progress():
    # Fetch driver standings to identify the top 5 drivers
    standings_url = 'http://ergast.com/api/f1/current/driverStandings.json'
    standings_response = requests.get(standings_url)
    standings = standings_response.json()['MRData']['StandingsTable']['StandingsLists'][0]['DriverStandings']
    top5_drivers = [driver['Driver']['driverId'] for driver in standings[:5]]

    if not standings_response.json()['MRData']['StandingsTable']['StandingsLists']:
        return "No standings data available", 404
    standings = standings_response.json()['MRData']['StandingsTable']['StandingsLists'][0]['DriverStandings']


    # Initialize a DataFrame to track cumulative points
    data = {driver: [] for driver in top5_drivers}
    race_names = []

    season_url = 'http://ergast.com/api/f1/current.json'
    season_response = requests.get(season_url)
    season = season_response.json()['MRData']['RaceTable']['Races']

    if not season_response.json()['MRData']['RaceTable']['Races']:
        return "No season data available", 404
    season = season_response.json()['MRData']['RaceTable']['Races']



    for race in season:
        race_name = race['raceName']
        race_round = race['round']
        race_names.append(race_name)

        # Fetch results for this race
        race_url = f'http://ergast.com/api/f1/current/{race_round}/results.json'
        race_results_response = requests.get(race_url)
        race_results = race_results_response.json()
        race_results = race_results['MRData']['RaceTable']['Races']

        if race_results:  # Check if the 'race results' list is not empty
            race_results = race_results[0].get('Results')  # Use get() to avoid KeyError
            if not race_results:  # Check if 'Results' exists
                print(f"No results available for race: {race_name}")
        else:
            print(f"No race data available for round {race_round}")

        race_points = {driver: 0 for driver in top5_drivers}
        #{max_verstappen : 0}

        for result in race_results:
            driver_id = result['Driver']['driverId']
            points = float(result['points'])

            if driver_id in race_points:
                race_points[driver_id] += points

        for driver in top5_drivers:
            previous_points = data[driver][-1] if data[driver] else 0
            data[driver].append(previous_points + race_points[driver])


    return race_names, data

def plot_driver_points_progress_interactive():
    race_names, points_data = get_driver_points_progress()

    fig = go.Figure()
    for driver, points in points_data.items():
        fig.add_trace(go.Scatter(x=race_names, y=points, mode='lines+markers', name=driver))

    fig.update_layout(
        title='Top 5 Drivers - Points Progress',
        xaxis_title='Races',
        yaxis_title='Cumulative Points',
        template='plotly_dark',
        hovermode='x unified'
    )
    return fig.to_html(full_html=False)



@app.route('/race/<round>')
def race_details(round):
    url = 'http://ergast.com/api/f1/current.json'
    response = requests.get(url)
    data = response.json()
    races = data['MRData']['RaceTable']['Races']

    race_details = next((race for race in races if race['round'] == round), None)

    if not race_details:
        return "Race not found", 404

    return render_template('race.html', race=race_details)


@app.route('/drivers')
@app.cache.cached(timeout=3600)  # Cache the route for 1 hour

def drivers_standings():
    url = 'http://ergast.com/api/f1/current/driverStandings.json'
    response = requests.get(url)
    data = response.json()
    drivers = data['MRData']['StandingsTable']['StandingsLists'][0]['DriverStandings']

    graph_html = plot_driver_points_progress_interactive()

    TEAM_STYLES = {
        "red_bull": {
            "background": "linear-gradient(135deg, #001f3f, #00275c 50%, #ff1801);",
            "text_color": "#FFCC00",
            "secondary_color": "#FF004C"
        },
        "mercedes": {
            "background": "linear-gradient(135deg, #000000, #101820 50%, #00d2be);",
            "text_color": "#FFFFFF",
            "secondary_color": "#FFFFFF"
        },
        "ferrari": {
            "background": "linear-gradient(135deg, #ff2800, #ff6b00 70%, #ffce00);",  
            "text_color": "#FFFFFF",
            "secondary_color": "#FFFF00"
        },
        "mclaren": {
            "background": "linear-gradient(135deg, #ff8700, #ffae00 50%, #005aff);", 
            "text_color": "#000000",        
            "secondary_color": "#FFFFFF" 
        }
    }

    leader = drivers[0]
    leader_data = {
        "name": f"{leader['Driver']['givenName']} {leader['Driver']['familyName']}",
        "points": leader['points'],
        "team": leader['Constructors'][0]['name'],
        "driverId": leader['Driver']['driverId'],
        "image": f"static/assets/drivers/{leader['Driver']['driverId']}.jpg",
        "team_id" : leader['Constructors'][0]['constructorId']
    }

    team_style = TEAM_STYLES.get(leader_data['team_id'], {})

    return render_template('drivers.html', drivers=drivers, team_style=team_style, leader=leader_data, graph_html=graph_html)


def get_constructor_points_progress():
    # Fetch constructor standings to identify the top 5 constructors
    standings_url = 'http://ergast.com/api/f1/current/constructorStandings.json'
    standings_response = requests.get(standings_url)
    standings_data = standings_response.json()

    if not standings_data['MRData']['StandingsTable']['StandingsLists']:
        return "No standings data available", 404

    standings = standings_data['MRData']['StandingsTable']['StandingsLists'][0]['ConstructorStandings']
    top5_constructors = [constructor['Constructor']['constructorId'] for constructor in standings[:5]]

    # Initialize a DataFrame-like structure to track cumulative points
    data = {constructor: [] for constructor in top5_constructors}
    race_names = []

    # Fetch the list of races for the current season
    season_url = 'http://ergast.com/api/f1/current.json'
    season_response = requests.get(season_url)
    season_data = season_response.json()

    if not season_data['MRData']['RaceTable']['Races']:
        return "No season data available", 404

    races = season_data['MRData']['RaceTable']['Races']

    for race in races:
        race_name = race['raceName']
        race_round = race['round']
        race_names.append(race_name)

        # Fetch results for this race
        race_url = f'http://ergast.com/api/f1/current/{race_round}/results.json'
        race_results_response = requests.get(race_url)
        race_results_data = race_results_response.json()

        if not race_results_data['MRData']['RaceTable']['Races']:
            print(f"No race data available for round {race_round}")
            continue

        race_results = race_results_data['MRData']['RaceTable']['Races'][0].get('Results', [])
        race_points = {constructor: 0 for constructor in top5_constructors}

        for result in race_results:
            constructor_id = result['Constructor']['constructorId']
            points = float(result['points'])

            if constructor_id in race_points:
                race_points[constructor_id] += points

        # Update cumulative points for each constructor
        for constructor in top5_constructors:
            previous_points = data[constructor][-1] if data[constructor] else 0
            data[constructor].append(previous_points + race_points[constructor])

    return race_names, data

def plot_constructor_points_progress_interactive():
    race_names, points_data = get_constructor_points_progress()

    fig = go.Figure()
    for constructor, points in points_data.items():
        fig.add_trace(go.Scatter(x=race_names, y=points, mode='lines+markers', name=constructor))

    fig.update_layout(
        title='Top 5 Constructors - Points Progress',
        xaxis_title='Races',
        yaxis_title='Cumulative Points',
        template='plotly_dark',
        hovermode='x unified'
    )
    return fig.to_html(full_html=False)


@app.route('/constructors')
@app.cache.cached(timeout=3600)  # Cache the route for 1 hour

def constructor_standings():

    url = 'http://ergast.com/api/f1/current/constructorStandings.json'
    response = requests.get(url)
    data = response.json()
    constructors = data['MRData']['StandingsTable']['StandingsLists'][0]['ConstructorStandings']

    graph_html = plot_constructor_points_progress_interactive()

    TEAM_STYLES = {
        "red_bull": {
            "background": "linear-gradient(135deg, #001f3f, #00275c 50%, #ff1801);",
            "text_color": "#FFCC00",
            "secondary_color": "#FF004C"
        },
        "mercedes": {
            "background": "linear-gradient(135deg, #000000, #101820 50%, #00d2be);",
            "text_color": "#FFFFFF",
            "secondary_color": "#FFFFFF"
        },
        "ferrari": {
            "background": "linear-gradient(135deg, #ff2800, #ff6b00 70%, #ffce00);",  
            "text_color": "#FFFFFF",
            "secondary_color": "#FFFF00"
        },
        "mclaren": {
            "background": "linear-gradient(135deg, #ff8700, #ffae00 50%, #005aff);", 
            "text_color": "#000000",        
            "secondary_color": "#FFFFFF" 
        }
    }

    leader = constructors[0]
    leader_data = {
        "name": f"{leader['Constructor']['name']}",
        "points": leader['points'],
        "wins": leader['wins'],
        "nationality" : leader['Constructor']['nationality'],
        "team_id": leader['Constructor']['constructorId'],
        "image": f"static/assets/teams/{leader['Constructor']['constructorId']}.png",
    }

    team_style = TEAM_STYLES.get(leader_data['team_id'], {})

    return render_template('constructors.html', constructors=constructors, team_style=team_style, leader=leader_data, graph_html=graph_html)



if __name__ == '__main__':
    app.run(debug=True)