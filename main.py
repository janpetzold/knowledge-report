import os
import time
from datetime import datetime, timedelta
from dateutil import parser, tz
import feedparser
import requests
from bs4 import BeautifulSoup
from openai import OpenAI
from dotenv import load_dotenv
import tiktoken

# Verified feeds
# http://feeds.feedburner.com/ThePragmaticEngineer
# https://dev.37signals.com/feed/posts.xml
# https://medium.com/feed/airbnb-engineering
# https://aws.amazon.com/blogs/aws/feed
# https://www.databricks.com/feed
# https://dropbox.tech/feed
# https://blog.digitalocean.com/rss
# https://tech.ebayinc.com/rss
# https://code.facebook.com/posts/rss
# https://blog.research.google/atom.xml
# https://googleonlinesecurity.blogspot.com/atom.xml
# https://www.theguardian.com/info/series/engineering-blog/rss
# https://www.hashicorp.com/blog/feed.xml
# https://www.heise.de/developer/rss/news-atom.xml
# https://www.heise.de/security/rss/news-atom.xml
# https://blog.heroku.com/engineering/feed
# https://medium.com/feed/intel-tech
# https://instagram-engineering.com/feed
# https://medium.engineering/feed
# https://hacks.mozilla.org/feed/
# https://blog.mozilla.org/feed
# https://devblogs.microsoft.com/java/feed/
# https://devblogs.microsoft.com/devops/feed/
# https://medium.com/feed/netflix-techblog
# https://open.nytimes.com/feed
# https://blogs.nvidia.com/feed
# https://developer.okta.com/feed.xml
# https://blog.palantir.com/feed/
# https://medium.com/feed/paypal-tech
# https://medium.com/feed/@Pinterest_Engineering
# https://medium.com/feed/better-practices
# https://developers.redhat.com/blog/feed/atom/
# https://developer.salesforce.com/blogs/feed
# https://shopify.engineering/blog.atom
# https://slack.engineering/feed
# https://developers.soundcloud.com/blog.rss
# https://engineering.atspotify.com/feed
# https://stackoverflow.blog/engineering/feed
# https://stripe.com/blog/feed.rss
# https://www.thoughtworks.com/rss/insights.xml
# https://medium.com/feed/tinder
# https://blog.twitter.com/engineering/feed
# https://medium.com/feed/twitch-news/tagged/engineering
# https://yahooeng.tumblr.com/rss
# https://www.igvita.com/feed/
# https://www.joelonsoftware.com/feed/
# https://martinfowler.com/feed.atom
# http://feeds.hanselman.com/ScottHanselman
# https://android-developers.blogspot.com/atom.xml
# https://developers.googleblog.com/atom.xml
# https://blog.rust-lang.org/feed.xml
# http://blog.samaltman.com/posts.atom
# https://www.forbes.com/innovation/feed2
# http://www.theverge.com/rss/full.xml
# https://techcrunch.com/feed/
# https://feeds.feedburner.com/martinkl?format=xml
# http://news.mit.edu/rss/topic/artificial-intelligence2
# https://openai.com/blog/rss.xml
# http://googleresearch.blogspot.com/atom.xml
# https://towardsdatascience.com/feed
# https://www.amazon.science/index.rss
# https://freakonomics.com/blog/feed
# http://feeds.harvardbusiness.org/harvardbusiness/
#

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

def is_feed_outdated(update_date) -> bool:
    feed_update_date = parser.parse(update_date)
    feed_update_date_utc = feed_update_date.astimezone(tz.tzutc())

    # Get the current datetime in UTC for comparison
    current_date_utc = datetime.now(tz.tzutc())
    thirty_days_ago_utc = current_date_utc - timedelta(days=30)

    if feed_update_date_utc < thirty_days_ago_utc:
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


def analyze_with_openai(url, text):
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
        findings.append({url : response_text})
        print("New finding - URL: " + url)
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

        for finding in list_findings:
            for key, value in finding.items():
                # Process the "value" containing the findings text so it doesn't blow up the layout
                processed_response = ' '.join(value.splitlines()).strip()
                processed_response_quote = "<blockquote>" + processed_response + "</blockquote>"
                file.write(f"| [Link]({key}) | {processed_response_quote} |\n")

        if(len(feed_list_outdated_feeds) > 0):
            file.write("Outdated feeds are:\n\n")
            for url in feed_list_outdated_feeds:
                file.write(f"- {url}\n")

start_time = time.time()

load_dotenv()

feed_list = [
    "http://feeds.feedburner.com/ThePragmaticEngineer",
    "https://dev.37signals.com/feed/posts.xml",
    "https://medium.com/feed/airbnb-engineering",
    "https://aws.amazon.com/blogs/aws/feed",
    "https://www.databricks.com/feed",
    "https://dropbox.tech/feed",
    "https://blog.digitalocean.com/rss",
    "https://tech.ebayinc.com/rss",
    "https://code.facebook.com/posts/rss",
    "https://blog.research.google/atom.xml",
    "https://googleonlinesecurity.blogspot.com/atom.xml",
    "https://www.theguardian.com/info/series/engineering-blog/rss",
    "https://www.hashicorp.com/blog/feed.xml",
    "https://www.heise.de/developer/rss/news-atom.xml",
    "https://www.heise.de/security/rss/news-atom.xml",
    "https://blog.heroku.com/engineering/feed",
    "https://medium.com/feed/intel-tech",
    "https://instagram-engineering.com/feed",
    "https://medium.engineering/feed",
    "https://hacks.mozilla.org/feed/",
    "https://blog.mozilla.org/feed",
    "https://devblogs.microsoft.com/java/feed/",
    "https://devblogs.microsoft.com/devops/feed/",
    "https://medium.com/feed/netflix-techblog",
    "https://open.nytimes.com/feed",
    "https://blogs.nvidia.com/feed",
    "https://developer.okta.com/feed.xml",
    "https://blog.palantir.com/feed/",
    "https://medium.com/feed/paypal-tech",
    "https://medium.com/feed/@Pinterest_Engineering",
    "https://medium.com/feed/better-practices",
    "https://developers.redhat.com/blog/feed/atom/",
    "https://developer.salesforce.com/blogs/feed",
    "https://shopify.engineering/blog.atom",
    "https://slack.engineering/feed",
    "https://developers.soundcloud.com/blog.rss",
    "https://engineering.atspotify.com/feed",
    "https://stackoverflow.blog/engineering/feed",
    "https://stripe.com/blog/feed.rss",
    # "https://www.thoughtworks.com/rss/insights.xml",
    # "https://medium.com/feed/tinder",
    # "https://blog.twitter.com/engineering/feed",
    # "https://medium.com/feed/twitch-news/tagged/engineering",
    # "https://yahooeng.tumblr.com/rss",
    # "https://www.igvita.com/feed/",
    # "https://www.joelonsoftware.com/feed/",
    # "https://martinfowler.com/feed.atom",
    # "http://feeds.hanselman.com/ScottHanselman",
    # "https://android-developers.blogspot.com/atom.xml",
    # "https://developers.googleblog.com/atom.xml",
    # "https://blog.rust-lang.org/feed.xml",
    # "http://blog.samaltman.com/posts.atom",
    # "https://www.forbes.com/innovation/feed2",
    # "http://www.theverge.com/rss/full.xml",
    # "https://techcrunch.com/feed/",
    # "https://feeds.feedburner.com/martinkl?format=xml",
    # "http://news.mit.edu/rss/topic/artificial-intelligence2",
    # "https://openai.com/blog/rss.xml",
    # "http://googleresearch.blogspot.com/atom.xml",
    # "https://towardsdatascience.com/feed",
    # "https://www.amazon.science/index.rss",
    # "https://freakonomics.com/blog/feed",
    # "http://feeds.harvardbusiness.org/harvardbusiness/"
]


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

    if(is_feed_outdated(update_field)):
        feed_list_outdated_feeds.append(feed.href)

    for item in feed.entries:
        feed_all.append(f'{item.link}')

count_urls = 0
count_total_characters = 0
count_total_tokens = 0

# Populate history so we don't analyze the same URLs twice.
get_url_history()

for url in feed_all:
    count_urls = count_urls + 1
    
    # For testing
    #
    # if(count_urls > 3):
    #    break
    
    # Check if this URL was already processed    
    if url in urls_set:
        print(f"{url} has already been analyzed")
    else:
        print(f"{url} is new and will be analyzed")

        # Get the text of the artcle / blog post
        page = requests.get(url).text
        soup = BeautifulSoup(page, "html.parser")
        
        text = soup.getText()
        clean_text = ' '.join(text.split())

        # Count characters and tokens for statistical purposes
        count_total_characters = count_total_characters + len(clean_text)
        count_total_tokens = count_total_tokens + num_tokens_from_string(clean_text)

        # TODO: Find common trailer/footer and remove it to save tokens and focus on content
        print("Processing article " + soup.title.get_text() + ", text length " + str(len(clean_text)))
        #print(clean_text)

        analyze_with_openai(url, clean_text)
        add_url_to_history(url)

end_time = time.time()
rounded_elapsed_time = round((end_time - start_time), 1)

write_markdown(len(feed_list), (count_urls - 1), count_total_characters, count_total_tokens, get_cost_from_tokens(count_total_tokens), findings, rounded_elapsed_time)

# TODO: Send via mail

print(str(count_urls - 1) + " articles in total in this RSS feed with " + str(count_total_characters) + " characters and " + str(count_total_tokens) + " tokens in total leading to costs of approx. $" + str(get_cost_from_tokens(count_total_tokens)))
print(f"Execution of the script took {rounded_elapsed_time} seconds")