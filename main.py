from flask import Flask, render_template
import requests
from datetime import date, datetime, timedelta
import folium

app = Flask(__name__)

@app.route('/')

def home():
    return render_template('index.html')

@app.route('/calender')
def calender():
    url = 'http://ergast.com/api/f1/2024.json'
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




@app.route('/race/<round>')
def race_details(round):
    url = 'http://ergast.com/api/f1/2024.json'
    response = requests.get(url)
    data = response.json()
    races = data['MRData']['RaceTable']['Races']

    race_details = next((race for race in races if race['round'] == round), None)

    if not race_details:
        return "Race not found", 404

    return render_template('race.html', race=race_details)

@app.route('/drivers')
def drivers_standings():
    url = 'http://ergast.com/api/f1/2024/driverStandings.json'
    response = requests.get(url)
    data = response.json()
    drivers = data['MRData']['StandingsTable']['StandingsLists'][0]['DriverStandings']

    return render_template('drivers.html', drivers=drivers)


if __name__ == '__main__':
    app.run(debug=True)