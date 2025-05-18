import asyncio
import os
import subprocess
from typing import List

import cv2
from dotenv import load_dotenv
from fastapi import FastAPI, File, UploadFile
from fastapi.responses import HTMLResponse
from openai import OpenAI

load_dotenv()

app = FastAPI()


async def video_to_blog_post(video_path: str) -> str:
    """
    Orchestrates the process of converting a video into a blog post.

    Args:
        video_path (str): Path to the video file.

    Returns:
        str: Path to the generated HTML blog post.
    """

    print("Starting video to blog post process...")

    # Shorten video
    print("Shortening video...")
    try:
        command = f"python jumpcutter.py --input_file {video_path} --output_file shortened_video.mp4"
        subprocess.run(command, shell=True, check=True)
        shortened_video_path = "shortened_video.mp4"
    except Exception as e:
        print(f"Error shortening video: {e}")
        return None

    # Transcribe video
    print("Transcribing video...")
    try:
        import whisper

        model = whisper.load_model("base")
        result = model.transcribe(shortened_video_path)
        transcript = result["text"]
    except Exception as e:
        print(f"Error transcribing video: {e}")
        return None

    # Create blog post
    print("Creating blog post...")
    try:
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        response = client.completions.create(
            model="gpt-4o-mini",
            prompt=f"Create a blog post from the following transcript: {transcript}",
            max_tokens=1024,
        )
        blog_post = response.choices[0].text
    except Exception as e:
        print(f"Error creating blog post: {e}")
        return None

    # Generate photos
    print("Generating photos...")
    output_dir = "photos"
    os.makedirs(output_dir, exist_ok=True)
    try:
        vidcap = cv2.VideoCapture(video_path)
        fps = vidcap.get(cv2.CAP_PROP_FPS)
        frame_interval = int(fps * 10)  # Extract one frame every 10 seconds
        success, image = vidcap.read()
        count = 0
        photo_paths: List[str] = []
        while success:
            if count % frame_interval == 0:
                photo_path = os.path.join(output_dir, f"frame{count}.jpg")
                cv2.imwrite(photo_path, image)
                photo_paths.append(photo_path)
            success, image = vidcap.read()
            count += 1
    except Exception as e:
        print(f"Error generating photos: {e}")
        return None

    # Create HTML blog post
    print("Creating HTML blog post...")
    try:
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

        html_file_path = "video_blog_post.html"
        with open(html_file_path, "w") as f:
            f.write(html_content)

        print(f"Generated HTML blog post: {html_file_path}")
        return html_file_path
    except Exception as e:
        print(f"Error creating HTML blog post: {e}")
        return None


@app.post("/upload")
async def upload_video(video: UploadFile = File(...)):
    """
    Endpoint for uploading a video and converting it to a blog post.

    Args:
        video (UploadFile): The uploaded video file.

    Returns:
        HTMLResponse: An HTML response displaying the generated blog post.
    """
    try:
        # Save the uploaded video to a temporary file
        video_path = f"temp_{video.filename}"
        with open(video_path, "wb") as f:
            f.write(await video.read())

        # Process the video and generate the HTML blog post
        html_path = await video_to_blog_post(video_path)

        # Read the HTML content and return it as a response
        with open(html_path, "r") as f:
            html_content = f.read()

        # Clean up the temporary video file
        os.remove(video_path)

        return {"html_content": html_content}
    except Exception as e:
        return {"error": str(e)}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
