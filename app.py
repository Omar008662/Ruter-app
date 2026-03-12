from flask import Flask, render_template, request
import requests

app = Flask(__name__)

headers = {
    "ET-Client-Name": "ruter-student-app"
}

@app.route("/")
def home():
    return render_template("index.html")


@app.route("/search", methods=["POST"])
def search():
    stop_name = request.form["stop"]

    # 1️⃣ Finn stopp
    search_url = f"https://api.entur.io/geocoder/v1/autocomplete?text={stop_name}&size=1"

    r = requests.get(search_url, headers=headers)
    data = r.json()

    if len(data["features"]) == 0:
        return render_template("departures.html", stop=stop_name, departures=[])

    stop_id = data["features"][0]["properties"]["id"]
    stop_name = data["features"][0]["properties"]["name"]

    # 2️⃣ Hent avganger
    query = """
    {
      stopPlace(id: "%s") {
        name
        estimatedCalls(numberOfDepartures: 5) {
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
    """ % stop_id

    url = "https://api.entur.io/journey-planner/v3/graphql"

    r = requests.post(url, json={"query": query}, headers=headers)
    result = r.json()

    departures = []

    try:
        calls = result["data"]["stopPlace"]["estimatedCalls"]

        for call in calls:
            departures.append({
                "line": call["serviceJourney"]["line"]["publicCode"],
                "destination": call["destinationDisplay"]["frontText"],
                "time": call["expectedDepartureTime"]
            })
    except:
        departures = []

    return render_template("departures.html", stop=stop_name, departures=departures)


if __name__ == "__main__":
    app.run(debug=True)