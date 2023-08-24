import modal
import etl.shared

image = etl.shared.image.pip_install("youtube-transcript-api==0.6.1", "srt==3.5.3")

stub = modal.Stub(
    name="etl-videos",
    image=image,
    secrets=[
        modal.Secret.from_name("mongodb-guitar"),
    ],
)


def get_transcript(video_id):
    from youtube_transcript_api import YouTubeTranscriptApi

    return YouTubeTranscriptApi.get_transcript(video_id)


def get_chapters(video_id):
    import requests

    base_url = "https://yt.lemnoslife.com"
    request_path = "/videos"

    params = {"id": video_id, "part": "chapters"}

    response = requests.get(base_url + request_path, params=params)
    response.raise_for_status()

    chapters = response.json()["items"][0]["chapters"]["chapters"]
    assert len(chapters) >= 0, "Video has no chapters"

    for chapter in chapters:
        del chapter["thumbnails"]

    return chapters


def add_transcript(chapters, subtitles):
    for ii, chapter in enumerate(chapters):
        next_chapter = chapters[ii + 1] if ii < len(chapters) - 1 else {"time": 1e10}

        text = " ".join(
            [
                seg["text"]
                for seg in subtitles
                if seg["start"] >= chapter["time"]
                and seg["start"] < next_chapter["time"]
            ]
        )

        chapter["text"] = text

    return chapters


def create_documents(chapters, id, video_title):
    base_url = f"https://www.youtube.com/watch?v={id}"
    query_params_format = "&t={start}s"
    documents = []

    for chapter in chapters:
        text = chapter["text"].strip()
        start = chapter["time"]
        url = base_url + query_params_format.format(start=start)

        document = {"text": text, "metadata": {"source": url}}

        document["metadata"]["title"] = video_title
        document["metadata"]["chapter-title"] = chapter["title"]
        document["metadata"]["full-title"] = f"{video_title} - {chapter['title']}"

        documents.append(document)

    return documents


@stub.function(
    retries=modal.Retries(max_retries=3, backoff_coefficient=2.0, initial_delay=5.0)
)
def extract_subtitles(video_info):
    video_id, video_title = video_info["id"], video_info["title"]
    subtitles = get_transcript(video_id)
    chapters = get_chapters(video_id)
    chapters = add_transcript(chapters, subtitles)

    documents = create_documents(chapters, video_id, video_title)

    return documents


@stub.function(
    retries=modal.Retries(max_retries=3, backoff_coefficient=2.0, initial_delay=5.0)
)
def extract_videos(playlist_id):
    import requests

    base_url = "https://yt.lemnoslife.com"
    request_path = "/playlistItems"

    params = {"playlistId": playlist_id, "part": "snippet"}

    response = requests.get(base_url + request_path, params=params)
    response.raise_for_status()

    video_infos = response.json()["items"]
    assert len(video_infos) >= 0, "Playlist has no videos"

    for vid in video_infos:
        vid["title"] = vid["snippet"]["title"]
        vid["id"] = vid["snippet"]["resourceId"]["videoId"]
        del vid["snippet"]
        del vid["kind"]
        del vid["etag"]

    return video_infos


def get_video_infos(json_path):
    """
    Fetch list of videos based on playlist ids in the JSON file.
    """
    import json

    with open(json_path) as f:
        playlist_infos = json.load(f)

    video_infos = etl.shared.flatten(
        extract_videos.map(
            (info["id"] for info in playlist_infos), return_exceptions=True
        )
    )

    return video_infos


@stub.local_entrypoint()
def main(json_path="data/videos.json", collection=None, db=None):
    """Calls the ETL pipeline using a JSON file with YouTube video metadata.

    modal run etl/videos.py --json-path /path/to/json
    """
    video_infos = get_video_infos(json_path)
    documents = (
        etl.shared.flatten(  # each video creates multiple documents, so we flatten
            extract_subtitles.map(video_infos, return_exceptions=True)
        )
    )

    with etl.shared.stub.run():
        chunked_documents = etl.shared.chunk_into(documents, 10)
        list(
            etl.shared.add_to_document_db.map(
                chunked_documents, kwargs={"db": db, "collection": collection}
            )
        )
