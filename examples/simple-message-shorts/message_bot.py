import os
import pickle
import random
import sys

import google.auth.transport.requests
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from gtts import gTTS
from moviepy.editor import AudioFileClip, ImageClip, concatenate_videoclips
from PIL import Image, ImageDraw, ImageFont


def generate_conversation() -> list[dict[str, str]]:
    conversation = []
    num_messages = random.randint(5, 10)
    participants = ["Alex", "Jamie"]
    for _ in range(num_messages):
        sender = random.choice(participants)
        message = generate_random_message()
        conversation.append({"sender": sender, "message": message})
    return conversation


def generate_random_message() -> str:
    messages = [
        "Hey, are we still on for today?",
        "Absolutely! Can't wait to see you.",
        "Don't forget to bring the documents.",
        "Will do. See you at 3 PM.",
        "Should we grab coffee afterwards?",
        "Sounds like a plan!",
        "Let me know if anything changes.",
        "Did you finish the project?",
        "Yes, I'll send it over tonight.",
        "Thanks for your help!",
    ]
    return random.choice(messages)


def create_message_images(conversation: list[dict[str, str]]) -> list[str]:
    """
    Creates images for each message

    Takes in a list of dictionaries representing the sender (str) & message (str)
        in a conversation

    Returns a list of strings representing image file paths
    """
    images = []
    font = ImageFont.load_default(40)
    background_color = (255, 255, 255)
    text_color = (0, 0, 0)
    width, height = 1080, 1920  # vertical video dimensions for Shorts

    for idx, msg in enumerate(conversation):
        img = Image.new("RGB", (width, height), color=background_color)
        draw = ImageDraw.Draw(img)
        text_position = (50, 100 + idx * 100)
        text_content = f"{msg['sender']}: {msg['message']}"
        draw.text(text_position, text_content, fill=text_color, font=font)
        image_path = f"./image/message_{idx}.png"
        img.save(image_path)
        images.append(image_path)
    return images


def create_voiceover(conversation: list[dict[str, str]]) -> str:
    """
    Creates a voiceover for the conversation

    Takes in a list of dictionaries representing the sender (str) & message (str)
        in a conversation

    Returns a string representing the voiceover file path
    """
    messages_text = " ".join([f"{msg['message']}" for msg in conversation])
    tts = gTTS(text=messages_text, lang="en")
    audio_path = "./audio/voiceover.mp3"
    tts.save(audio_path)
    return audio_path


def create_final_video(image_paths: list[str], audio_path: str) -> str:
    """
    Creates a voiceover for the conversation

    image_paths: a list of strings representing the file paths of the images for the video
    audio_path: a string representing the file path of the voiceover for the video

    Returns a string representing the video file path
    """
    clips = []
    for image_path in image_paths:
        # lengthen clip as time goes on (each iteration) to sync w/ audio
        fill_time = 1.0
        # each image lasts 3 seconds
        clip = (
            ImageClip(image_path).set_duration(2.3 * fill_time)
            # have to change your resize in pillow to use Image.LANCZOS instead of ANTIALIAS
            .resize(height=1920)
        )
        clips.append(clip)
        fill_time += 0.05
    video = concatenate_videoclips(clips, method="compose")
    audio = AudioFileClip(audio_path)
    final_video = video.set_audio(audio)
    video_path = "./video/best_message_leaks_video.mp4"
    final_video.write_videofile(video_path, fps=24)
    return video_path


# YouTube API scopes
SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]


def get_authenticated_service():
    credentials = None
    if os.path.exists("token.pkl"):
        with open("token.pkl", "rb") as token:
            credentials = pickle.load(token)
    if not credentials or not credentials.valid:
        if credentials and credentials.expired and credentials.refresh_token:
            credentials.refresh(google.auth.transport.requests.Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            credentials = flow.run_local_server(port=0)
        with open("token.pkl", "wb") as token:
            pickle.dump(credentials, token)
    return build("youtube", "v3", credentials=credentials)


def upload_video(youtube, file):
    request_body = {
        "snippet": {
            "title": "Best Message Leaks #Shorts",
            "description": "CAT TEST #Shorts",
            "tags": ["leaks", "messages", "shorts"],
            "categoryId": "22",  # People & Blogs
        },
        "status": {
            "privacyStatus": "public",
            "selfDeclaredMadeForKids": False,  # set to true if appropriate
        },
    }

    media_file = MediaFileUpload(file, chunksize=-1, resumable=True, mimetype="video/*")

    request = youtube.videos().insert(
        part="snippet,status", body=request_body, media_body=media_file
    )

    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            print(f"Uploaded {int(status.progress() * 100)}%.")

    print(f"Video uploaded. Video ID: {response.get('id')}")


if __name__ == "__main__":
    conversation = generate_conversation()
    images = create_message_images(conversation)
    audio_file = create_voiceover(conversation)
    video_file = create_final_video(images, audio_file)
    if not os.path.exists("credentials.json"):
        print("Missing credentials.json.")
        sys.exit(1)
    if not os.path.exists(video_file):
        print(f"Missing video file {video_file}.")
        sys.exit(1)
    youtube_client = get_authenticated_service()
    upload_video(youtube_client, video_file)
