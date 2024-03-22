# AI-driven knowledge report

This is a helper script created to analyze blogs regarding "interesting" content. Basically feed URLs are collected, articles retrieved and forwarded to OpenAI API for further analysis. In case an article matches the given prompt it is collected.

The resulting data is exported to Markdown file as basic report and sent via mail.

The URL for articles that were already analyzed are stored in a logfile (`history.log`) that is read on startup to avoid re-analyzing content that has already been processed. 

## Gettings tarted & some numbers

I just run this on my local machine via

    pip3 install -r requirements.txt
    python3 main.py

A full run for me includes 62 blogs, last time I executed this it resulted in 1619 articles with almost 20 mio. characters / 4 mio. words (3.8 mio. tokens) in total. The analysis of these via OpenAI API cost ~$1.90. The script ran for approx. 78 minutes.

## Configuration

Everything relevant needs to be supplied via `.env` file in the main folder with the following variables:

    FEEDS=YOUR-FEED-URL1,YOUR-FEED-URL2,...
    OPENAI_API_KEY=YOUR-API-KEY
    PROMPT=YOUR-PROMPT

The prompt follows the usual format like "You are a scientist and want to..."

It is important that the prompt contains some clear instruction like 

> If you have any findings summarize that briefly with a "Yes, findings - " in the response, otherwise just respond with a clear "No findings".

The parser checks for a "Yes" in the response, otherwise the result is not counted and therefore not visible in the generated report.

## Why Markdown

I wanted a simple report with basic layouting capabilities that is easy to create and Markdown satisifies all that. It can easily be sent as mail attachment and rendered in a ton of readers out there, e.g. http://markdown.pioul.fr/. 

## Why mail

I created this basically to collect interesting blog posts for myself. Since I use email anyway this is a good way to flag it for whenever I have the time to go through it and serves as some kind of backup as well.

## TODOs

- [x] externalize feed URLs to .env
- [ ] add title of article to report
- [ ] add sample report to /examples
- [ ] add mail sending
- [ ] eliminate identical headers/tails of articles before analysis
- [ ] ignore posts older than 12 months as additional safety net