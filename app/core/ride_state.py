from datetime  import datetime,timedelta

def update_route_state(route):
    now = datetime.utcnow()

    if route.status == "SCHEDULED":
        if route.departure_time - timedelta(minutes=15) <= now:
            route.status = "BOARDING"

    if route.status == "BOARDING":
        if now >= route.departure_time:
            route.status == "STARTED"