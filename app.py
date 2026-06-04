from flask import Flask, render_template, request, jsonify
import requests
from datetime import datetime

import db

app = Flask(__name__)

HEADERS = {
    "ET-Client-Name": "student-ruter-app"
}

GEOCODER_URL = "https://api.entur.io/geocoder/v1/autocomplete"
JOURNEY_URL = "https://api.entur.io/journey-planner/v3/graphql"


def minutes_until(iso_time):
    departure_time = datetime.fromisoformat(iso_time)
    now = datetime.now(departure_time.tzinfo)

    diff_seconds = (departure_time - now).total_seconds()
    minutes = max(0, int(diff_seconds // 60))

    if minutes == 0:
        return "Nå"
    return f"{minutes} min"


def find_stop(stop_name):
    params = {
        "text": stop_name,
        "size": 1,
        "lang": "no"
    }

    response = requests.get(GEOCODER_URL, headers=HEADERS, params=params, timeout=10)
    response.raise_for_status()
    data = response.json()

    features = data.get("features", [])
    if not features:
        return None

    props = features[0]["properties"]

    return {
        "id": props.get("id"),
        "name": props.get("name")
    }


def get_departures(stop_id):
    query = """
    query ($stopId: String!) {
      stopPlace(id: $stopId) {
        name
        estimatedCalls(numberOfDepartures: 10) {
          expectedDepartureTime
          destinationDisplay {
            frontText
          }
          serviceJourney {
            line {
              publicCode
            }
          }
        }
      }
    }
    """

    variables = {"stopId": stop_id}

    response = requests.post(
        JOURNEY_URL,
        json={"query": query, "variables": variables},
        headers=HEADERS,
        timeout=10
    )
    response.raise_for_status()
    data = response.json()

    stop_place = data.get("data", {}).get("stopPlace")
    if not stop_place:
        return []

    calls = stop_place.get("estimatedCalls", [])
    departures = []

    for call in calls:
        line = (
            call.get("serviceJourney", {})
            .get("line", {})
            .get("publicCode", "?")
        )
        destination = (
            call.get("destinationDisplay", {})
            .get("frontText", "Ukjent destinasjon")
        )
        expected_time = call.get("expectedDepartureTime")

        if not expected_time:
            continue

        departures.append({
            "line": line,
            "destination": destination,
            "time": minutes_until(expected_time)
        })

    return departures


@app.route("/")
def home():
    return render_template("index.html")

@app.route("/kart")
def kart():
    return render_template("Kart.html")

@app.route("/søk")
def soek():
    return render_template("søk.html")


@app.route("/omoss")
def omoss():

    return render_template("omoss.html")

@app.route("/favoritt")
def favoritt():
    return render_template("favoritt.html")
from flask import request, redirect

@app.route("/favoritt/add", methods=["POST"])
def add_favorite():
    stopp_id = request.form["stopp_id"]
    stopp_navn = request.form["stopp_navn"]
    bruker_id = 1  # senere: hent fra login

    favoritt = favorittstopp(
        stopp_id=stopp_id,
        stopp_navn=stopp_navn,
        bruker_id=bruker_id
    )

    db.session.add(favoritt)
    db.session.commit()

    return redirect("/favoritt")



@app.route("/search", methods=["POST"])
def search():
    stop_name = request.form.get("stop", "").strip()

    if not stop_name:
        return render_template(
            "departures.html",
            stop="",
            stop_id="",
            error="Du må skrive inn et stopp."
        )

    try:
        stop = find_stop(stop_name)

        if not stop:
            return render_template(
                "departures.html",
                stop=stop_name,
                stop_id="",
                error="Fant ikke stoppet."
            )

        return render_template(
            "departures.html",
            stop=stop["name"],
            stop_id=stop["id"],
            error=None
        )

    except requests.RequestException:
        return render_template(
            "departures.html",
            stop=stop_name,
            stop_id="",
            error="Kunne ikke hente data fra API."
        )


@app.route("/departures/<path:stop_id>")
def departures(stop_id):
    try:
        departures_data = get_departures(stop_id)
        return jsonify(departures_data)
    except requests.RequestException:
        return jsonify([]), 500


if __name__ == "__main__":
    app.run(debug=True)
    


