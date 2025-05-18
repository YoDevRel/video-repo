import psycopg2

def post_to_database(id, type, channel, title, summary, content, connection_string):
    try:
        # Establish a connection to the PostgreSQL database
        conn = psycopg2.connect(connection_string)

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

    except (Exception, psycopg2.DatabaseError) as error:
        print("Error:", error)


content = """
Let’s face it. Our attention spans have shrank significantly in the age of social media, and we need to adapt our message accordingly.

When I look around, I see many people still trying to convey their ideas in long, drawn-out speeches. But the truth is, in a world where social media reigns supreme, we need to cater our message to the scrolling masses. This means being concise, engaging, and to the point. 

So how do we do that? First, recognize that you are no longer speaking to a captive audience. Instead, you are addressing random people who may or may not even be interested in what you have to say. This means you need to grab their attention immediately. Start with a strong opening that draws them in, whether it's a powerful statistic, a shocking statement, or a captivating story. 

Next, keep your message brief. The days of long-winded speeches are gone. Aim for short, impactful statements that deliver your message clearly and effectively. Remember, time is of the essence – you have only seconds to make an impression, so make every word count.

Visuals can also enhance your message. Use graphics, images, or videos to help illustrate your points and keep your audience engaged. A well-placed visual can make your message stick even more. 

Finally, inject humor where appropriate. A good laugh can break the ice and make your audience more receptive to your message. Plus, who doesn't love a good pun or one-liner to lighten the mood? 

In conclusion, if you’re preparing a talk or presentation, remember to speak to the scrolling masses. Cater your message to social media consumers by being concise, engaging, and utilizing the right visuals. With these tips, you can capture attention and make a lasting impression in a world that is increasingly fast-paced and easily distracted. 

So, next time you’re crafting your message, think about how you can keep it short and sweet. After all, in our age of shortened attention spans, it’s about delivering a powerful message in as few words as possible. Because let’s face it: the internet is waiting for you to entertain it, inform it, and share it. Let's grab their attention and hold on tight!

**Capturing Attention in the Age of Shortened Attention Spans**

Wow, what an audience! But let's be real for a moment – I don’t really care about what you think of my talk right now. Nope, what I care about is what the internet thinks because they’re the ones who will help me get it to the masses. This is where I believe many people falter; they get too focused on delivering their message to the audience present in front of them, when in reality they should be thinking of the random user scrolling through Facebook or Twitter.

Back in 2009, we might have had “attention spans,” but those days are long gone. We’ve whittled them down to mere seconds in our fast-paced social media world. I can’t even remember the last time I sat through an 18-minute TED Talk. Honestly, it’s been years! 

So, if you’re tasked with giving a TED Talk (or any talk for that matter), the goal should be to keep it quick, engaging, and impactful. I’m delivering mine in under a minute, and I’m at 44 seconds right now. That means I have time for a quick joke – why are balloons so expensive? Inflation!

But in all seriousness, our attention spans have dwindled immensely, and as a result, we need to adjust the way we communicate our ideas for today’s audience. 

Let's look at how we can effectively reach todays attendees:

1. **Address Your Audience with Intent**: You’re not speaking to a captive crowd anymore. You’re talking to random people who may or may not be invested in your message. You need to grab their attention instantly. Start with a strong opening statement – maybe an intriguing statistic or a captivating story that resonates. 

2. **Brevity is Key**: Out with long-winded speeches and in with short, impactful messages. Aim to state your points clearly and effectively, maximizing the few seconds you have to create an impression. Each word should serve a purpose.

3. **Use Visuals**: A picture is worth a thousand words, or so the saying goes! Incorporate engaging visuals, whether it’s graphics, images, or short videos that complement and reinforce your statements. They help solidify your message even more.

4. **Add Humor**: A touch of humor can lighten the mood and connect you with your audience. A well-timed pun or joke can break down barriers and make your audience more open to your message. Plus, who doesn’t appreciate a good laugh?

In conclusion, when preparing a talk or presentation in this digital age, remember to think about how you can cater to the scrolling masses. Make your message concise, engaging, and visually appealing. Speaking to the online audience means delivering a powerful message with as few words as possible.

So, the next time you craft
"""

if __name__ == '__main__':
    # Example usage:
    connection_string = "postgresql://HeyDev_owner:npg_JPIYyjXr9pL7@ep-wandering-king-a65kklpi-pooler.us-west-2.aws.neon.tech/HeyDev?sslmode=require"
    post_to_database(
        id=1,
        type="blog",
        channel="MyChannel",
        title="My Blog Post Title",
        summary="A brief summary of the blog post.",
        content=content,
        connection_string=connection_string
    )
