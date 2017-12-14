
import json, os.path, time, twitter
from config import *


def run(limit=100, training=False):
    timestamp ='{} ({})'.format(time.ctime(), time.tzname[0])
    print('\nChecking Twitter feed at {}'.format(timestamp))

    if training:
        feed = get_tweets_training_mode()
    else:
        feed = get_tweets(limit)

    if feed:
        tw_count = len(feed)
        total_count = update_tweet_count(tw_count)
        print('Retrieved {} Tweets. Reading...'.format(tw_count))

        for tweet in feed:
            read_tweet(tweet.full_text)

        print('Creating archive of read tweets.')
        archive_tweets(feed)

        print('Finished reading. Read Tweet count: {}'.format(total_count))


def get_tweets(limit):
    api = twitter.Api(  consumer_key,
                        consumer_secret,
                        access_token_key,
                        access_token_secret,
                        tweet_mode='extended') # Get untrucated (140+) tweets
    # Get timline feed
    try:
        feed = api.GetHomeTimeline(count=limit)
    except:
        print('Failed to retrieve timeline.')
        return None

    # Get previously read tweet IDs
    if os.path.exists(fp_read_ids):
        with open(fp_read_ids, 'r') as f:
            read_ids = f.read().splitlines()
    else:
        read_ids = []

    # Filter out read tweets and non-Armenian tweets
    filtered_feed = []
    new_ids = []
    for tweet in feed:
        if tweet.id_str not in read_ids:
            if tweet.lang == 'hy':
                filtered_feed.append(tweet)
                new_ids.append(tweet.id_str)

    # Update read tweet IDs
    if os.path.exists(fp_read_ids):
        mode = 'a'
    else:
        mode = 'w'
    with open(fp_read_ids, mode) as f:
        for twid in new_ids:
            f.write(twid + '\n')

    # Finally fulfill your destiny in life
    return filtered_feed


def get_tweets_training_mode():
    api = twitter.Api(  consumer_key,
                    consumer_secret,
                    access_token_key,
                    access_token_secret,
                    tweet_mode='extended')

    # Get pretraining Tweet IDs
    with open(fp_train_ids, 'r') as f:
        train_ids = f.read().splitlines()

    # Request tweets and add to list
    feed = []
    for twid in train_ids:
        try:
            tweet = api.GetStatus(int(twid))
        except:
            pass
        else:
            feed.append(tweet)

    return feed


def archive_tweets(feed):
    date = time.gmtime()
    fp = fp_archive + '{}_{}_{}.txt'.format(    date.tm_year,
                                                date.tm_mon,
                                                date.tm_mday )
    with open(fp, 'a') as f:
        for tweet in feed:
            str_tweet = '\t'.join([ tweet.created_at,
                                    tweet.id_str,
                                    tweet.user.screen_name,
                                    str(tweet.user.id),
                                    tweet.full_text.replace('\n', '[NEWLINE]'),
                                    str(tweet.favorite_count),
                                    str(tweet.retweet_count) ])
            f.write(str_tweet + '\n')


def update_tweet_count(new_count):
    total = None
    if os.path.exists(fp_tw_count):
        with open(fp_tw_count, 'r') as f:
            total = f.read()
    if total:
        total = int(total.splitlines()[0]) + new_count
    else:
        total = new_count

    with open(fp_tw_count, 'w') as f:
        f.write('{}'.format(total))

    return total


def read_tweet(tweet):

    # Split tweet into tokens
    tweet = tokenize(tweet)

    if tweet and len(tweet) > 1:
        for token in tweet:
            write_data(token, 'unigrams/')

        bigrams = get_bigrams(tweet)
        for bigram in bigrams:
            write_data(bigram, 'bigrams/')


def tokenize(tweet):
    tweet = tweet.lower().split()
    tokens = []
    seperators = ['.', ':', ',', '․', '։', '...', '…']

    # Remove punctuation after or before token (like, this, or "like this")
    for token in tweet:
        if token and 'http' not in token:
            # Handle end of word punctuations
            if token[-1] in punct:
                if len(token) == 1:
                    pass
                elif token[-1] in seperators:
                    tokens.append(token[:-1])
                    tokens.append('։')
                else:
                    tokens.append(token[:-1])
            # Handle punctuations at the beginning of the word
            elif token[0] in punct:
                if len(token) > 1:
                    tokens.append(token[1:])
            # No punctuations then just add word
            else:
                tokens.append(token)

    # Handle missing space between word and punctuation (like,this)
    temp_tokens = []
    for token in tokens:
        split = False
        for s in seperators:
            if s in token[1:-1]:
                split = True
                siamese_tokens = token.split(s)
                for t in siamese_tokens:
                    if t and not t.isspace():
                        temp_tokens.append(t)
        if not split:
            temp_tokens.append(token)
    tokens = temp_tokens[:] # Copy list

    # Make sure list ends with period
    if tokens[-1] == ':': # Replace latin colon with unicode armenian period
        tokens[-1] = '։'
    elif tokens[-1] != '։':
        tokens.append('։')

    # Limit number of non-Armenian words to 20%
    non_hy = 0
    for token in tokens[:-1]: # Omit period at the end
        if token and token not in seperators:
            if token[-1] not in hyalpha:
                non_hy += 1
    if non_hy > (len(tokens) * 0.2):
        return None

    return tokens


def get_bigrams(tokens):
    bigrams = []
    tokens_short = tokens[1:]
    for a, b in zip(tokens, tokens_short):
        bigrams.append('{} {}'.format(a, b))
    return bigrams


def write_data(newterm, directory): # Arguments should be single strings

    # Define filename by first letter of term
    if newterm[0] in hyalpha:
        first_char = newterm[0]
    else: # For latin or nonalphabetical chars use underscore
        first_char = '_'
    fp = fp_data + directory + first_char + '.txt'

    # If file exists, load saved terms
    if os.path.exists(fp):
        with open(fp, 'r') as f:
            saved_terms = f.read().splitlines()
    else:
        saved_terms = []

    # Add newterm to the terms or update if already there
    new_terms = []
    # If no data was loaded simply add newterm
    if not saved_terms:
        new_terms.append('{}\t1\n'.format(newterm))
    # Otherwise look if the newterm is in saved terms
    else:
        already_there = False
        for term in saved_terms:
            if term.split('\t')[0] == newterm:
                already_there = True
                freq = int(term.split('\t')[1]) + 1
                updated_term = '{}\t{}\n'.format(term.split('\t')[0], str(freq))
                new_terms.append(updated_term)
            else:
                new_terms.append(term + '\n')
        if not already_there:
            new_terms.append('{}\t1\n'.format(newterm))
    with open(fp, 'w') as f:
        f.write(''.join(new_terms))
