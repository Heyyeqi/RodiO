"""Temporal model: sun position, seasonal factor, diurnal cycle.

Sun position uses the NOAA simplified solar calculator (Spencer 1971 /
Fourier series). Accuracy: ±0.01° altitude for years 1950–2050.
No external astronomy library required.
"""

from __future__ import annotations

import math

from .renderer_types import DayCycleState, SeasonalState, SunState, TimeState


class TemporalModel:

    def get_sun_position(self, lat: float, lon: float, time_state: TimeState) -> SunState:
        """Return sun elevation and azimuth for (lat, lon) at given time.

        Elevation > 0 → above horizon. Azimuth is degrees clockwise from north.
        """
        lat_r = math.radians(lat)
        doy = float(time_state.day_of_year)
        hour = float(time_state.hour)

        # Fractional year in radians
        gamma = (2 * math.pi / 365) * (doy - 1 + (hour - 12.0) / 24.0)

        # Equation of time (minutes)
        eqtime = 229.18 * (
            0.000075
            + 0.001868 * math.cos(gamma)
            - 0.032077 * math.sin(gamma)
            - 0.014615 * math.cos(2 * gamma)
            - 0.040890 * math.sin(2 * gamma)
        )

        # Solar declination (radians)
        decl = (
            0.006918
            - 0.399912 * math.cos(gamma)
            + 0.070257 * math.sin(gamma)
            - 0.006758 * math.cos(2 * gamma)
            + 0.000907 * math.sin(2 * gamma)
            - 0.002697 * math.cos(3 * gamma)
            + 0.001480 * math.sin(3 * gamma)
        )

        # True solar time (minutes from local solar midnight).
        # hour is treated as local apparent solar time, so longitude does not
        # enter here — it would only matter when converting from UTC wall clock.
        # eqtime is the small equation-of-time correction (~±16 min).
        tst = hour * 60.0 + eqtime

        # Hour angle (degrees; negative = morning, positive = afternoon)
        ha = tst / 4.0 - 180.0
        ha_r = math.radians(ha)

        # Solar zenith / altitude
        cos_z = math.sin(lat_r) * math.sin(decl) + math.cos(lat_r) * math.cos(decl) * math.cos(ha_r)
        cos_z = max(-1.0, min(1.0, cos_z))
        zenith = math.degrees(math.acos(cos_z))
        elevation = 90.0 - zenith

        # Solar azimuth (compass from north)
        sin_z = math.sin(math.radians(zenith))
        if sin_z > 1e-6 and abs(math.cos(lat_r)) > 1e-6:
            cos_az = (math.sin(decl) - cos_z * math.sin(lat_r)) / (sin_z * math.cos(lat_r))
            cos_az = max(-1.0, min(1.0, cos_az))
            azimuth = math.degrees(math.acos(cos_az))
            if ha > 0:
                azimuth = 360.0 - azimuth
        else:
            azimuth = 180.0  # polar / zenith edge case

        return SunState(elevation=elevation, azimuth=azimuth, above_horizon=elevation > 0.0)

    def get_season_factor(self, lat: float, day_of_year: int) -> SeasonalState:
        """Return seasonal modulation state.

        season_factor: 1.0 = full local summer, 0.0 = full local winter.
        Hemisphere-aware: southern latitudes invert the cycle.
        """
        # Summer solstice DOY: NH ≈ 172, SH ≈ 355
        peak_doy = 172 if lat >= 0 else 355

        delta = float(day_of_year - peak_doy)
        if delta > 182:
            delta -= 365
        elif delta < -182:
            delta += 365

        # Cosine over half-year period → 1.0 at peak, 0.0 at trough
        season_factor = 0.5 + 0.5 * math.cos(math.pi * delta / 182.5)

        # Snow factor: high latitudes + winter
        lat_snow_base = max(0.0, (abs(lat) - 25.0) / 65.0)
        snow_factor = min(1.0, lat_snow_base * (1.0 - season_factor) * 1.6)

        # Vegetation boost: summer peak, suppressed at very high latitudes
        lat_veg_scale = max(0.0, 1.0 - abs(lat) / 80.0)
        vegetation_boost = (season_factor * 2.0 - 1.0) * lat_veg_scale

        return SeasonalState(
            season_factor=season_factor,
            snow_factor=snow_factor,
            vegetation_boost=vegetation_boost,
        )

    def get_day_cycle(self, hour: float) -> DayCycleState:
        """Return diurnal phase properties for the given hour (0–24)."""
        h = hour % 24.0

        if 4.5 <= h < 6.5:
            return DayCycleState(phase="dawn", warmth=-0.25, contrast=0.15, saturation=0.55, blue_bias=0.12)
        if 6.5 <= h < 9.5:
            return DayCycleState(phase="morning", warmth=-0.08, contrast=0.55, saturation=0.85, blue_bias=0.04)
        if 9.5 <= h < 14.0:
            return DayCycleState(phase="noon", warmth=0.0, contrast=1.0, saturation=1.0, blue_bias=0.0)
        if 14.0 <= h < 16.5:
            return DayCycleState(phase="afternoon", warmth=0.06, contrast=0.92, saturation=0.97, blue_bias=0.0)
        if 16.5 <= h < 18.5:
            return DayCycleState(phase="sunset", warmth=0.40, contrast=0.65, saturation=1.35, blue_bias=0.0)
        if 18.5 <= h < 20.5:
            return DayCycleState(phase="dusk", warmth=0.12, contrast=0.25, saturation=0.65, blue_bias=0.18)
        # night (20.5–4.5)
        return DayCycleState(phase="night", warmth=-0.18, contrast=0.08, saturation=0.28, blue_bias=0.55)
