import asyncio
from dotenv import load_dotenv
import subprocess
import os
from openai import OpenAI
import cv2
import traceback

load_dotenv()
from crewai.flow.flow import Flow, listen, start
import litellm
import whisper


class ExampleFlow():
    model = "gpt-4o"

    def __init__(self):
        self.state = {}

    async def video_path(self):
        print("Starting flow...")
        video_path = "orignal-video.mp4"
        return video_path
    
    async def shorten_video(self, video_path):
        print("Shortening video...")
        try:
            # Execute jumpcutter.py as a subprocess
            command = f"python jumpcutter.py --input_file {video_path} --output_file shortened_video.mp4"
            subprocess.run(command, shell=True, check=True, capture_output=True)
            self.state["shortened_video"] = "shortened_video.mp4"
            return "shortened_video.mp4"
        except Exception as e:
            print(f"Error shortening video: {e}")
            traceback.print_exc()
            return None

    async def transcribe_video(self, video_path):
        print("Transcribing video...")
        if video_path is None:
            print("Skipping transcription because video_path is None")
            return None
        try:
            model = whisper.load_model("base")
            result = model.transcribe(video_path)
            text = result["text"]
            self.state["transcript"] = text
            return text
        except Exception as e:
            print(f"Error transcribing video: {e}")
            traceback.print_exc()
            return None

    async def create_blog_post(self, transcript):
        print("Creating blog post...")
        try:
            client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            response = client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": f"Create a blog post from the following transcript: {transcript}"}],
                max_tokens=1024,
            )
            blog_post = response.choices[0].message.content
            self.state["blog_post"] = blog_post
            return blog_post
        except Exception as e:
            print(f"Error creating blog post: {e}")
            traceback.print_exc()
            return None


    async def generate_photos(self, blog_post):
        print("Generating photos...")
        video_path = "orignal-video.mp4"
        output_dir = "photos"
        try:
            os.makedirs(output_dir, exist_ok=True)
            vidcap = cv2.VideoCapture(video_path)
            if not vidcap.isOpened():
                print(f"Error: Could not open video file {video_path}")
                return None
            fps = vidcap.get(cv2.CAP_PROP_FPS)
            # Extract one frame every 10 seconds
            frame_interval = int(fps * 10)
            success, image = vidcap.read()
            count = 0
            photo_paths = []
            while success:
                if count % frame_interval == 0:
                    photo_path = os.path.join(output_dir, f"frame{count}.jpg")
                    cv2.imwrite(photo_path, image)
                    photo_paths.append(photo_path)
                success, image = vidcap.read()
                count += 1
            self.state["photo_paths"] = photo_paths
            return photo_paths
        except Exception as e:
            print(f"Error generating photos: {e}")
            traceback.print_exc()
            return None


    async def create_html_blog_post(self, photo_paths):
        print("Creating HTML blog post...")
        try:
            # Read the blog post from the state
            blog_post = self.state.get("blog_post", "")

            if photo_paths is None:
                print("Skipping HTML creation because photo_paths is None")
                return None

            # Create the HTML content
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Video Blog Post</title>
            </head>
            <body>
                <p>{blog_post}</p>
                <h2>Photos</h2>
                <div>
                    {''.join([f'<img src="{path}" alt="Video Frame" width="300">' for path in photo_paths])}
                </div>
            </body>
            </html>
            """

            # Check if the file exists and delete it if it does
            if os.path.exists("crewai_flow.html"):
                os.remove("crewai_flow.html")

            # Write the HTML content to a file
            with open("crewai_flow.html", "w") as f:
                f.write(html_content)

            return "crewai_flow.html"
        except Exception as e:
            print(f"Error creating HTML blog post: {e}")
            traceback.print_exc()
            return None


flow = ExampleFlow()

async def main():
    video_path = await flow.video_path()
    shortened_video = await flow.shorten_video(video_path)
    transcript = await flow.transcribe_video(shortened_video)
    blog_post = await flow.create_blog_post(transcript)
    photo_paths = await flow.generate_photos(blog_post)
    html_path = await flow.create_html_blog_post(photo_paths)
    print(f"Generated HTML blog post: {html_path}")

asyncio.run(main())
