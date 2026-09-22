from instagrapi import Client

cl = Client()
url = "https://www.instagram.com/reel/C7X_X11v8-0/"
try:
    pk = cl.media_pk_from_url(url)
    print("Media PK:", pk)
    media = cl.media_info_a1(pk)
    print("Video URL:", media.video_url)
    print("Title/Caption:", media.caption_text[:100] if media.caption_text else "No caption")
except Exception as e:
    print("instagrapi error:", e)
