# FlightRadar24 Scraper

A simple FlightRadar24 web scraper for collecting scheduled and actual plane departures and arrivals for airports.

This project is unfinished and unpolished, but it can scrape the departed and arrived flight numbers for a given airport and date. Since the FlightRadar24 endpoint doesn’t include cancelled flights, the scraper takes a broader approach: it first gathers all departed/arrived flight numbers over a longer period (around one month) for that airport.

Because flight numbers are typically consistent week to week, even if a specific flight was cancelled on the target date, the same flight number usually appears on another day. The scraper then uses those flight numbers to pull flight history data and re-filters it for the given airport and date, effectively reconstructing a complete list of flights, including those that were cancelled.

This is a very hacky solution, but this is the best you can get out of any historical flight data provider without actually paying any subscriptions fees.
