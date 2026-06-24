# orbit_model.py
import math
from datetime import datetime, timedelta, timezone

# ---------- Constants ----------
R_EARTH = 6371.0          # Earth's mean radius (km)
MU = 398600.44            # Earth's gravitational parameter (km^3/s^2)
DEG = math.pi / 180.0
TWO_PI = 2.0 * math.pi
J2000_EPOCH = datetime(2000, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
JD_J2000 = 2451545.0      # Julian Date of J2000 epoch

# ---------- Time Helpers ----------
def julian_date(utc_dt: datetime) -> float:
    """Return Julian Date for a UTC datetime (UT1 ~ UTC)."""
    # Ensure datetime is in UTC
    if utc_dt.tzinfo is None:
        # Assume naive datetime is UTC
        pass
    else:
        utc_dt = utc_dt.astimezone(timezone.utc)
    # Algorithm from US Naval Observatory (valid for years 1801-2099)
    y, m, d = utc_dt.year, utc_dt.month, utc_dt.day
    if m <= 2:
        y -= 1
        m += 12
    A = y // 100
    B = 2 - A + A // 4
    jd = int(365.25 * (y + 4716)) + int(30.6001 * (m + 1)) + d + B - 1524.5
    # Add fractional day
    day_fraction = (utc_dt.hour + utc_dt.minute / 60.0 + utc_dt.second / 3600.0) / 24.0
    return jd + day_fraction

def gmst_radians(jd: float) -> float:
    """Greenwich Mean Sidereal Time in radians from Julian Date."""
    # Centuries since J2000.0
    T = (jd - JD_J2000) / 36525.0
    # GMST in seconds (approximate formula, good to ~0.1 seconds)
    gmst_sec = (67310.54841 +
                (876600.0 * 3600.0 + 8640184.812866) * T +
                0.093104 * T**2 -
                6.2e-6 * T**3)
    gmst_sec %= 86400.0
    gmst_rad = (gmst_sec / 240.0) * DEG   # 1 hour = 15 deg, 240 seconds per degree?
    # Actually 86400 sec / 2pi rad = 13750.987... ; easier: 2*pi * gmst_sec / 86400
    gmst_rad = TWO_PI * gmst_sec / 86400.0
    return gmst_rad

# ---------- Orbit Mechanics ----------
def mean_motion(altitude_km: float) -> float:
    """Mean angular speed (rad/s) for circular orbit."""
    semi_major_axis = R_EARTH + altitude_km
    return math.sqrt(MU / semi_major_axis**3)

def sat_eci(semi_major: float, inc_rad: float, u_rad: float):
    """Return ECI position (x, y, z) in km."""
    x = semi_major * math.cos(u_rad)
    y = semi_major * math.sin(u_rad) * math.cos(inc_rad)
    z = semi_major * math.sin(u_rad) * math.sin(inc_rad)
    return (x, y, z)

def eci_to_ecef(x_eci, y_eci, z_eci, gmst_rad):
    """Rotate ECI to ECEF by GMST angle."""
    cos_g = math.cos(gmst_rad)
    sin_g = math.sin(gmst_rad)
    x_ecef =  x_eci * cos_g + y_eci * sin_g
    y_ecef = -x_eci * sin_g + y_eci * cos_g
    z_ecef = z_eci
    return (x_ecef, y_ecef, z_ecef)

def station_ecef(lat_deg, lon_deg):
    """Geodetic (lat,lon) -> ECEF (assuming spherical Earth)."""
    lat = lat_deg * DEG
    lon = lon_deg * DEG
    x = R_EARTH * math.cos(lat) * math.cos(lon)
    y = R_EARTH * math.cos(lat) * math.sin(lon)
    z = R_EARTH * math.sin(lat)
    return (x, y, z)

def topocentric_az_el(sat_ecef, site_ecef, lat_deg, lon_deg):
    """Compute azimuth (0=North, clockwise) and elevation from site."""
    dx = sat_ecef[0] - site_ecef[0]
    dy = sat_ecef[1] - site_ecef[1]
    dz = sat_ecef[2] - site_ecef[2]

    lat = lat_deg * DEG
    lon = lon_deg * DEG
    sin_lat = math.sin(lat)
    cos_lat = math.cos(lat)
    sin_lon = math.sin(lon)
    cos_lon = math.cos(lon)

    # ENU unit vectors
    e_E = (-sin_lon, cos_lon, 0.0)
    e_N = (-sin_lat * cos_lon, -sin_lat * sin_lon, cos_lat)
    e_U = (cos_lat * cos_lon, cos_lat * sin_lon, sin_lat)

    east = dx * e_E[0] + dy * e_E[1] + dz * e_E[2]
    north = dx * e_N[0] + dy * e_N[1] + dz * e_N[2]
    up = dx * e_U[0] + dy * e_U[1] + dz * e_U[2]

    range_mag = math.sqrt(east**2 + north**2 + up**2)
    el = math.asin(up / range_mag)
    az = math.atan2(east, north)  # 0 = North, positive eastward
    az %= TWO_PI
    az_deg = az / DEG
    el_deg = el / DEG
    return az_deg, el_deg

# ---------- Pass Prediction ----------
def predict_passes(station_lat, station_lon, alt_km, inc_deg,
                   start_utc, end_utc, M0_deg=0.0):
    """
    Predict satellite passes over a ground station.

    Returns dict:
        passes: list of {rise_utc, set_utc, max_el, duration_sec}
        chart_track: list of {az, el, time} for the best pass (highest max_el)
    """
    inc_rad = inc_deg * DEG
    semi_major = R_EARTH + alt_km
    n = mean_motion(alt_km)
    M0_rad = M0_deg * DEG

    site_ecef = station_ecef(station_lat, station_lon)

    # Time stepping
    delta = timedelta(seconds=10)
    current = start_utc
    prev_el = None
    passes = []
    current_pass = None
    best_pass = None  # pass with highest max_el

    while current <= end_utc:
        # Julian date and GMST
        jd = julian_date(current)
        gmst = gmst_radians(jd)

        # Argument of latitude
        dt_sec = (current - start_utc).total_seconds()
        u = (M0_rad + n * dt_sec) % TWO_PI

        # Satellite ECI then ECEF
        x_eci, y_eci, z_eci = sat_eci(semi_major, inc_rad, u)
        x_ecef, y_ecef, z_ecef = eci_to_ecef(x_eci, y_eci, z_eci, gmst)

        # Elevation
        _, el = topocentric_az_el((x_ecef, y_ecef, z_ecef),
                                  site_ecef,
                                  station_lat, station_lon)

        # Debug: uncomment to check raw el values
        # if dt_sec < 600: print(current, el)

        # Pass detection
        if prev_el is not None:
            if prev_el <= 0 and el > 0:
                # Rise: interpolate exact time
                # Linear interpolation
                frac = -prev_el / (el - prev_el)
                rise_time = current - delta + frac * delta
                current_pass = {
                    'rise_time': rise_time,
                    'max_el': el,
                    'max_el_time': current,
                    'points': []
                }
            elif current_pass is not None and el > current_pass['max_el']:
                current_pass['max_el'] = el
                current_pass['max_el_time'] = current

            if prev_el > 0 and el <= 0 and current_pass is not None:
                # Set: interpolate
                frac = prev_el / (prev_el - el)
                set_time = current - delta + frac * delta
                current_pass['set_time'] = set_time   
                duration = (set_time - current_pass['rise_time']).total_seconds()
                passes.append({
                    'rise_utc': current_pass['rise_time'].isoformat(),
                    'set_utc': set_time.isoformat(),
                    'max_el': current_pass['max_el'],
                    'duration_sec': duration
                })
                # Keep track of best pass
                if best_pass is None or current_pass['max_el'] > best_pass['max_el']:
                    best_pass = current_pass
                current_pass = None

        prev_el = el
        current += delta

    # Build chart track for the best pass (if any)
    chart_track = []
    if best_pass:
        # Sample at 30s intervals from rise-30s to set+30s
        sample_start = best_pass['rise_time'] - timedelta(seconds=30)
        sample_end = best_pass['set_time'] + timedelta(seconds=30)
        t = sample_start
        while t <= sample_end:
            jd = julian_date(t)
            gmst = gmst_radians(jd)
            dt = (t - start_utc).total_seconds()
            u = (M0_rad + n * dt) % TWO_PI
            x_eci, y_eci, z_eci = sat_eci(semi_major, inc_rad, u)
            x_ecef, y_ecef, z_ecef = eci_to_ecef(x_eci, y_eci, z_eci, gmst)
            az, el = topocentric_az_el((x_ecef, y_ecef, z_ecef),
                                       site_ecef,
                                       station_lat, station_lon)
            chart_track.append({
                'az': round(az, 2),
                'el': round(el, 2),
                'time': t.isoformat()
            })
            t += timedelta(seconds=30)

    return {
        'passes': passes,
        'chart_track': chart_track
    }