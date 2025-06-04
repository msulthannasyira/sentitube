from flask import Flask, request, send_file, jsonify
from googleapiclient.discovery import build
import pandas as pd
import re
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")

app = Flask(__name__)

def extract_video_id(url):
    """
    Ekstrak video ID dari berbagai format link YouTube.
    """
    # Pola umum: https://www.youtube.com/watch?v=VIDEO_ID
    match = re.search(r"(?:v=|\/)([0-9A-Za-z_-]{11})", url)
    if match:
        return match.group(1)
    return None

def get_replies(youtube, parent_id, video_id):
    replies = []
    next_page_token = None
    while True:
        reply_request = youtube.comments().list(
            part="snippet",
            parentId=parent_id,
            textFormat="plainText",
            maxResults=100,
            pageToken=next_page_token
        )
        reply_response = reply_request.execute()
        for item in reply_response.get('items', []):
            comment = item['snippet']
            replies.append({
                'Timestamp': comment['publishedAt'],
                'Username': comment['authorDisplayName'],
                'VideoID': video_id,
                'Comment': comment['textDisplay'],
                'Date': comment.get('updatedAt', comment['publishedAt'])
            })
        next_page_token = reply_response.get('nextPageToken')
        if not next_page_token:
            break
    return replies

def get_comments_for_video(youtube, video_id):
    all_comments = []
    next_page_token = None
    while True:
        comment_request = youtube.commentThreads().list(
            part="snippet",
            videoId=video_id,
            pageToken=next_page_token,
            textFormat="plainText",
            maxResults=100
        )
        comment_response = comment_request.execute()
        for item in comment_response.get('items', []):
            top_comment = item['snippet']['topLevelComment']['snippet']
            all_comments.append({
                'Timestamp': top_comment['publishedAt'],
                'Username': top_comment['authorDisplayName'],
                'VideoID': video_id,
                'Comment': top_comment['textDisplay'],
                'Date': top_comment.get('updatedAt', top_comment['publishedAt'])
            })
            if item['snippet']['totalReplyCount'] > 0:
                all_comments.extend(get_replies(youtube, item['snippet']['topLevelComment']['id'], video_id))
        next_page_token = comment_response.get('nextPageToken')
        if not next_page_token:
            break
    return all_comments

@app.route('/scrape_comments', methods=['POST'])
def scrape_comments():
    data = request.json
    video_url = data.get('video_url')
    if not video_url:
        return jsonify({'error': 'video_url is required'}), 400

    video_id = extract_video_id(video_url)
    if not video_id:
        return jsonify({'error': 'Invalid YouTube video URL'}), 400

    try:
        youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)
        all_comments = get_comments_for_video(youtube, video_id)

        if not all_comments:
            return jsonify({'error': 'No comments found'}), 404

        comments_df = pd.DataFrame(all_comments)
        output_path = 'comments_data.csv'
        comments_df.to_csv(output_path, index=False)
        return send_file(output_path, as_attachment=True)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)