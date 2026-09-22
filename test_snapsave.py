import requests
import re
import urllib.parse

def get_instagram_video_snapsave(url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
        'Origin': 'https://snapsave.app',
        'Referer': 'https://snapsave.app/',
    }
    data = {'url': url}
    try:
        r = requests.post('https://snapsave.app/action.php', data=data, headers=headers, timeout=10)
        print("SnapSave Status:", r.status_code)
        if r.status_code == 200:
            print("SnapSave response:", r.text[:300])
    except Exception as e:
        print("SnapSave Error:", e)

get_instagram_video_snapsave("https://www.instagram.com/reel/C7X_X11v8-0/")
