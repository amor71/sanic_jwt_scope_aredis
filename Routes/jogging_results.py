import datetime
import json
from sanic import response
from sanic.exceptions import SanicException, InvalidUsage, add_status_code
from sanic_jwt.decorators import protected
from jogging.Contectors.darksky import get_weather_condition
from jogging.Routes.auth import retrieve_user
from jogging.Models.jogging_result import JoggingResult


@add_status_code(409)
class Conflict(SanicException):
    pass


@protected()
async def add_jogging_result(request, *args, **kwargs):
    if (
        request.json is None
        or "date" not in request.json
        or "distance" not in request.json
        or "time" not in request.json
        or "location" not in request.json
    ):
        raise InvalidUsage(
            "invalid payload (should be {date, distance, time, location})"
        )

    distance = request.json["distance"]
    if distance <= 0:
        raise InvalidUsage("distance needs to be positive")

    try:
        date = datetime.datetime.strptime(
            request.json["date"], "%Y-%m-%d"
        ).date()
    except ValueError:
        raise InvalidUsage("invalid date (should be 'YYYY-MM-DD')")

    latlong = request.json["location"].split(" ")

    if len(latlong) != 2:
        raise InvalidUsage("invalid location (should be 'LAT LONG')")

    try:
        lat = float(latlong[0])
        long = float(latlong[1])
    except ValueError:
        raise InvalidUsage(
            "invalid location (lat & long should be floating-point)"
        )

    if not (-90.0 <= lat <= 90.0 and -180 <= long <= 180):
        raise InvalidUsage(
            "invalid location (The latitude must be a number between -90 and 90 and the longitude between -180 and 180)"
        )

    try:
        time = int(request.json["time"])
    except ValueError:
        raise InvalidUsage("invalid time (time should be an integer)")

    if time <= 0:
        raise InvalidUsage("invalid time (time should be positive)")

    condition = await get_weather_condition(lat, long, date)

    if condition is None:
        raise InvalidUsage(
            "can't fetch running conditions for that location & time"
        )

    user_id = retrieve_user(request, args, kwargs)["user_id"]

    jog = JoggingResult(
        user_id,
        request.json["location"],
        date,
        distance,
        time,
        json.dumps(condition["data"][0]),
    )
    jog.save()

    return response.HTTPResponse(status=201)


@protected()
async def get_jogging_results(request, *args, **kwargs):
    page = int(request.args["page"][0]) if "page" in request.args else 0
    limit = int(request.args["count"][0]) if "count" in request.args else 10

    if page < 0 or limit <= 0:
        raise InvalidUsage("invalid paging (page >= 0 and count > 0)")

    q_filter = request.args["filter"][0] if "filter" in request.args else None
    user_id = retrieve_user(request, args, kwargs)["user_id"]

    return response.json(
        JoggingResult.load(user_id, q_filter, page, limit), status=200
    )
