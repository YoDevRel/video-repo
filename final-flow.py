import asyncio
from dotenv import load_dotenv
import subprocess
import os
from openai import OpenAI
import cv2

load_dotenv()
from crewai.flow.flow import Flow, listen, start
from litellm import completion


class ExampleFlow(Flow):
    model = "gpt-4o-mini"

    @start()
    async def video_path(self):
        print("Starting flow...")
        video_path = "orignal-video.mp4"
        return video_path

    @listen(video_path)
    async def transcribe_video(self, video_path):
        print("Transcribing video...")
        try:
            import whisper
            model = whisper.load_model("base")
            result = model.transcribe(video_path)
            text = result["text"]
            self.state["transcript"] = text
            return text
        except Exception as e:
            print(f"Error transcribing video: {e}")
            return None

    @listen(transcribe_video)
    async def create_blog_post(self, transcript):
        print("Creating blog post...")
        try:
            client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            response = client.completions.create(
                model=self.model,
                prompt=f"Create a blog post from the following transcript: {transcript}",
                max_tokens=1024,
            )
            blog_post = response.choices[0].text
            self.state["blog_post"] = blog_post
            return blog_post
        except Exception as e:
            print(f"Error creating blog post: {e}")
            return None

    @listen(create_blog_post)
    async def post_to_database(self, create_blog_post):
        content = create_blog_post
        print("Post-processing blog post...")
        import psycopg2
        import random as rand
        type = "blog"
        channel = 'video'
        title = "Blog Post Title"
        summary = "This is a summary of the blog post."
        connection_string = "postgresql://HeyDev_owner:npg_JPIYyjXr9pL7@ep-wandering-king-a65kklpi-pooler.us-west-2.aws.neon.tech/HeyDev?sslmode=require"
        try:
            # Establish a connection to the PostgreSQL database
            conn = psycopg2.connect(connection_string)
            id = rand.randint(1000, 1000000)
            # Create a cursor object to execute SQL queries
            cur = conn.cursor()

            # Check if the 'posts' table exists and create it if it doesn't
            cur.execute("""
                SELECT EXISTS (
                    SELECT 1
                    FROM information_schema.tables
                    WHERE table_name = 'posts'
                );
            """)
            table_exists = cur.fetchone()[0]

            if not table_exists:
                cur.execute("""
                    CREATE TABLE posts (
                        id INT PRIMARY KEY,
                        type TEXT,
                        channel TEXT,
                        title TEXT,
                        summary TEXT,
                        content TEXT
                    );
                """)
                print("Table 'posts' created successfully!")

            # Define the SQL query to insert data into the 'posts' table
            sql = """
                INSERT INTO posts (id, type, channel, title, summary, content)
                VALUES (%s, %s, %s, %s, %s, %s)
            """

            # Execute the SQL query with the provided data
            cur.execute(sql, (id, type, channel, title, summary, content))

            # Commit the changes to the database
            conn.commit()

            print("Data inserted successfully!")

            # Close the cursor and connection
            cur.close()
            conn.close()


        except Exception as e:
            print(f"Error post-processing blog post: {e}")
            return None


flow = ExampleFlow()
flow.plot()

async def main():
    video_path = await flow.video_path()
    transcript = await flow.transcribe_video(video_path)
    blog_post = await flow.create_blog_post(transcript)
    await flow.post_to_database(blog_post)


asyncio.run(main())
