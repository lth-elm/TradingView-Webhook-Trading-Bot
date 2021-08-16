import requests

DISCORD_ERR_URL = "https://discord.com/api/webhooks/xxxxx"
DISCORD_LOGS_URL = "https://discord.com/api/webhooks/xxxxx"
logs_format = {
	"username": "logs",
	"avatar_url": "https://imgr.search.brave.com/ZYUP1jUoQ5tr1bxChZtL_sJ0LHz7mDhlhkLHxWxhnPM/fit/680/680/no/1/aHR0cHM6Ly9jbGlw/Z3JvdW5kLmNvbS9p/bWFnZXMvZGlzY29y/ZC1ib3QtbG9nby00/LnBuZw",
	"content": ""
}

DISCORD_STUDY_URL = "https://discord.com/api/webhooks/xxxxx"
study_format = {
	"username": "Tradingview Alert",
	"avatar_url": "https://pbs.twimg.com/profile_images/1418656582888525833/p4fZd3KR_400x400.jpg",
	"content": ""
}

def logs(message, error=False):
    print(message)
    try:
        json_logs = logs_format
        json_logs['content'] = message
        requests.post(DISCORD_LOGS_URL, json=json_logs)
        if error:
            requests.post(DISCORD_ERR_URL, json=json_logs)
    except:
        pass

def study_alert(message, chart_url):
    try:
        json_logs = study_format
        json_logs['content'] = ">>> " + message + " \n\n" + chart_url
        requests.post(DISCORD_STUDY_URL, json=json_logs)
    except:
        pass
