from flask import Flask, request, send_file, jsonify
from googleapiclient.discovery import build
import pandas as pd

app = Flask(__name__)

def get_all_video_ids_from_playlists(youtube, playlist_ids):
    all_videos = []
    for playlist_id in playlist_ids:
        next_page_token = None
        while True:
            playlist_request = youtube.playlistItems().list(
                part='contentDetails',
                playlistId=playlist_id,
                maxResults=50,
                pageToken=next_page_token)
            playlist_response = playlist_request.execute()
            all_videos += [item['contentDetails']['videoId'] for item in playlist_response['items']]
            next_page_token = playlist_response.get('nextPageToken')
            if next_page_token is None:
                break
    return all_videos

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
    api_key = data.get('api_key')
    playlist_id = data.get('playlist_id')
    if not api_key or not playlist_id:
        return jsonify({'error': 'api_key and playlist_id are required'}), 400

    try:
        youtube = build('youtube', 'v3', developerKey=api_key)
        video_ids = get_all_video_ids_from_playlists(youtube, [playlist_id])
        if not video_ids:
            return jsonify({'error': 'No videos found in playlist'}), 404

        all_comments = []
        for video_id in video_ids:
            all_comments.extend(get_comments_for_video(youtube, video_id))

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