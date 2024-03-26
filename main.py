import os
import time
from datetime import datetime, timedelta
from dateutil import parser, tz
import feedparser
import requests
from bs4 import BeautifulSoup
from openai import OpenAI
from dotenv import load_dotenv
import base64
from mailersend import emails
import tiktoken

# Most feeds have a "updated" field to indicate last posting but not all
def get_last_update_field_for_feed(feed):
    if(hasattr(feed, "updated")):
        return feed.updated
    elif (hasattr(feed, "feed") & hasattr(feed.feed, "updated")):
        return feed.feed.updated
    elif (hasattr(feed.entries[0], "published")):
        return feed.entries[0].published
    else:
        # Fallback - return something old as indication to check the feed
        return 'Sun, 10 Oct 1982 10:10:00 GMT'
    
def get_publish_field_for_article(item):
    if(hasattr(item, "published") and len(item.published) > 0):
        return item.published
    elif(hasattr(item, "updated") and len(item.updated) > 0):
        return item.updated
    else:
        # Fallback - if it doesn't exist take yesterday to include the article
        return (datetime.now() - timedelta(days=1)).date().isoformat()

def is_feed_outdated(update_date) -> bool:
    feed_update_date = parser.parse(update_date)
    feed_update_date_utc = feed_update_date.astimezone(tz.tzutc())

    # Get the current datetime in UTC for comparison
    current_date_utc = datetime.now(tz.tzutc())
    thirty_days_ago_utc = current_date_utc - timedelta(days=30)

    if feed_update_date_utc < thirty_days_ago_utc:
        return True
    
    return False

def is_article_outdated(publish_date) -> bool:
    article_publish_date = parser.parse(publish_date)
    article_publish_date_utc = article_publish_date.astimezone(tz.tzutc())

    # Get the current datetime in UTC for comparison
    current_date_utc = datetime.now(tz.tzutc())
    one_year_ago_utc = current_date_utc - timedelta(days=366)

    if article_publish_date_utc < one_year_ago_utc:
        return True
    
    return False

def num_tokens_from_string(string: str) -> int:
    encoding = tiktoken.encoding_for_model("gpt-3.5-turbo")
    num_tokens = len(encoding.encode(string))
    return num_tokens

# Pricing for gpt-3.5-turbo-0125 is $0.50 / 1M tokens
def get_cost_from_tokens(num_tokens: int) -> float:
    price = (num_tokens / 1000000) * 0.5
    return round(price, 2)


def analyze_with_openai(item, text):
    # Due to limited context window we need to ignore very large articles
    if(num_tokens_from_string(text) < 16385):
        response = client.chat.completions.create(
            model = "gpt-3.5-turbo-0125",
            temperature = 0.1,
            max_tokens = 64,
            messages = [
                {"role": "system", "content": os.getenv('PROMPT')},
                {"role": "user", "content": text}
            ]
        )

        response_text = response.choices[0].message.content
        if "yes" in response_text.lower():
            #findings.append({url : response_text})
            findings.append({"title": item['title'], "link": item['link'], "text": response_text})
            print("New finding - URL: " + item['link'])
            print(response_text)

def get_url_history():
    with open("history.log", 'r') as file:
        for line in file:
            url = line.strip() 
            if url:
                urls_set.add(url)

def add_url_to_history(url):
    file = open("history.log", "a")
    file.write(url)
    file.write("\n")
    file.close()

def write_markdown(
    number_of_feeds, 
    number_of_articles, 
    number_of_characters, 
    number_of_tokens, 
    openai_costs, 
    list_findings,
    elapsed_time):

    now = datetime.now()
    filename = now.strftime("report_%Y_%m_%d_%H_%M.md")
    datetext = now.strftime("%d.%m.%Y at %H:%M")

    with open(filename, "w") as file:
        file.write("# Knowledge report\n\n")
        file.write(f"This analysis ran on {datetext} in {elapsed_time} seconds.\n\n")
        file.write(f"In total {number_of_feeds} feeds with {number_of_articles} new articles were analyzed. The total number of characters was {number_of_characters}, token count {number_of_tokens}, approximate OpenAI costs ${openai_costs}.\n\n")
        file.write("## Findings\n\n")
        file.write("| URL | Result |\n")
        file.write("| ------ | ------ |\n")

        for item in list_findings:
            # Process the "value" containing the findings text so it doesn't blow up the layout
            processed_response = ' '.join(item['text'].splitlines()).strip()
            processed_response_quote = "<blockquote>" + processed_response + "</blockquote>"
            file.write(f"| [{item['title']}]({item['link']}) | {processed_response_quote} |\n")

        if(len(feed_list_outdated_feeds) > 0):
            file.write("Outdated feeds are:\n\n")
            for url in feed_list_outdated_feeds:
                file.write(f"- {url}\n")
    return filename

def send_mail(report_filename):
    mailer = emails.NewEmail(os.getenv('MAILERSEND_API_KEY'))
    mail_body = {}

    mail_from = {
        "name": "AI",
        "email": os.getenv('MAIL_SENDER')
    }

    recipients = [
        {
            "name": "Reader",
            "email": os.getenv('MAIL_RECIPIENT')
        }
    ]

    attachment = open(report_filename, 'rb')
    att_read = attachment.read()
    att_base64 = base64.b64encode(bytes(att_read))
    attachments = [
        {
            "id": "report",
            "filename": report_filename,
            "content": f"{att_base64.decode('ascii')}",
            "disposition": "attachment"
        }
    ]

    mailer.set_mail_from(mail_from, mail_body)
    mailer.set_mail_to(recipients, mail_body)
    mailer.set_subject("New Knowledge report", mail_body)
    mailer.set_plaintext_content("Read the new findings attached.\n\nPrompt was\n" + os.getenv('PROMPT') + "\n\nFeeds were\n" + os.getenv('FEEDS'), mail_body)
    mailer.set_attachments(attachments, mail_body)

    mailer.send(mail_body)


start_time = time.time()

load_dotenv()

feed_urls = os.getenv('FEEDS')
feed_list = feed_urls.split(",")

# Collect all feeds without update in the last 30 days here
feed_list_outdated_feeds = []

client = OpenAI(
   api_key = os.getenv('OPENAI_API_KEY'),
)

urls_set = set()
feed_all = []
findings = []

for source in feed_list:
    feed = feedparser.parse(source)
    print("Parsing feed " + feed.href)

    update_field = get_last_update_field_for_feed(feed)

    # Add entry for all feeds that have not been updated in the last 30 days to indicate stale feeds
    if(is_feed_outdated(update_field)):
        feed_list_outdated_feeds.append(feed.href)

    # Only check articles of the last year
    for item in feed.entries:
        publish_field = get_publish_field_for_article(item)
        if(is_article_outdated(publish_field) == False):
            feed_all.append({"title": item.title, "link": item.link})

count_urls = 0
count_total_characters = 0
count_total_tokens = 0

# Populate history so we don't analyze the same URLs twice.
get_url_history()

for entry in feed_all:
    count_urls = count_urls + 1
    
    # For testing
    #
    # if(count_urls > 3):
    #    break
    
    # Check if this URL was already processed    
    if entry['link'] in urls_set:
        print(f"{entry['link']} has already been analyzed")
    else:
        print(f"{entry['link']} is new and will be analyzed")

        # Get the text of the article / blog post
        page = requests.get(entry['link']).text
        soup = BeautifulSoup(page, "html.parser")
        
        text = soup.getText()
        clean_text = ' '.join(text.split())

        # Count characters and tokens for statistical purposes
        count_total_characters = count_total_characters + len(clean_text)
        count_total_tokens = count_total_tokens + num_tokens_from_string(clean_text)

        # TODO: Find common trailer/footer and remove it to save tokens and focus on content
        print("Processing article " + soup.title.get_text() + ", text length " + str(len(clean_text)))
        #print(clean_text)

        analyze_with_openai(entry, clean_text)
        #add_url_to_history(entry['url'])

end_time = time.time()
rounded_elapsed_time = round((end_time - start_time), 1)

report_file = write_markdown(len(feed_list), (count_urls - 1), count_total_characters, count_total_tokens, get_cost_from_tokens(count_total_tokens), findings, rounded_elapsed_time)
send_mail(report_file)

print(str(count_urls - 1) + " articles in total in this RSS feed with " + str(count_total_characters) + " characters and " + str(count_total_tokens) + " tokens in total leading to costs of approx. $" + str(get_cost_from_tokens(count_total_tokens)))
print(f"Execution of the script took {rounded_elapsed_time} seconds")