import time, read_tweets

if __name__ == '__main__':
    limit = 0
    training = True
    while(True):
        try:
            read_tweets.run(limit, training)
        except:
            pass
        finally:
            print('Sleeping for 20 minutes... Zzz.')
            limit = 50
            training = False
            time.sleep(1200)
