# AI-driven knowledge report

This is a helper script created to analyze blogs regarding "interesting" content. Basically feed URLs are collected, articles retrieved and forwarded to OpenAI API for further analysis. In case an article matches the given prompt it is collected.

The resulting data is exported to Markdown file as basic report and sent via mail.

The URL for articles that were already analyzed are stored in a logfile that is read on startup to avoid re-analyzing content that has already been processed. 

## Gettings tarted & some numbers

I just run this on my local machine via

    pip3 install -r requirements.txt
    python3 main.py

A full run for me includes 62 blogs, last time I did this it resulted in A articles with B characters (C tokens) in total. The analysis of these via OpenAI API cost ~$D. The script ran for approx. E minutes.

## Configuration

Everything relevant needs to be supplied via `.env` file in the main folder with the following variables:

    OPENAI_API_KEY=YOUR-API-KEY
    PROMPT=YOUR-PROMPT

The prompt follows the usual format like "You are a scientist and want to..."

It is important that the prompt contains some clear instruction like 

> If you have any findings summarize that briefly with a "Yes, findings - " in the response, otherwise just respond with a clear "No findings".

The parser checks for a "Yes" in the response, otherwise the result is not counted.

## Why Markdown

I wanted a simple report with basic layouting capabilities that is easy to create and Markdown satisifies all that. It can easily be sent as mail attachment and rendered in a ton of readers out there, e.g. http://markdown.pioul.fr/. 

## Why mail

I created this basically to collect interesting blog posts for myself. Since I use email anyway this is a good way to flag it for whenever I have the time to go through it and serves as some kind of backup as well.