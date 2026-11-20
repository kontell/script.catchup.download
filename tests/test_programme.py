from datetime import datetime, timezone

from catchup import programme

UTC = timezone.utc


def test_the_guide_path_carries_the_start_in_utc():
    assert programme.guide_start("pvr://guide/0012/2026-11-14 13:40:00.epg") == datetime(
        2026, 11, 14, 13, 40, tzinfo=UTC
    )
    assert programme.guide_start("pvr://channels/tv/All channels/pvr.kofin_1.pvr") is None
    assert programme.guide_start("") is None


def test_only_a_web_image_is_passed_on():
    wrapped = "image://http%3a%2f%2fhost%3a8096%2fItems%2fabc%2fImages%2fPrimary%3ftag%3d1/"
    assert programme.image_url(wrapped) == "http://host:8096/Items/abc/Images/Primary?tag=1"
    assert programme.image_url("https://img.example/p.jpg") == "https://img.example/p.jpg"
    assert programme.image_url("image://special%3a%2f%2fhome%2fx.png/") is None
    assert programme.image_url("") is None


CHANNELS = [
    {"channelid": 1, "label": "ITV 1", "channelnumber": 101, "subchannelnumber": 0},
    {"channelid": 2, "label": "ITV 4", "channelnumber": 104, "subchannelnumber": 0},
    {"channelid": 3, "label": "ITV 1", "channelnumber": 200, "subchannelnumber": 0},
    {"channelid": 4, "label": "BBC One", "channelnumber": 1, "subchannelnumber": 2},
]


def test_the_channel_is_found_by_name_then_number():
    assert programme.find_channel(CHANNELS, "itv 4", "")["channelid"] == 2
    assert programme.find_channel(CHANNELS, "ITV 1", "200")["channelid"] == 3
    assert programme.find_channel(CHANNELS, "ITV 1", "") is None
    assert programme.find_channel(CHANNELS, "Renamed", "1.2")["channelid"] == 4
    assert programme.find_channel(CHANNELS, "Nothing", "999") is None


BROADCAST = {
    "broadcastid": 7,
    "label": "Wales v New Zealand: Nations Championship",
    "title": "Wales v New Zealand: Nations Championship",
    "plot": "Live coverage.",
    "starttime": "2026-11-14 13:40:00",
    "endtime": "2026-11-14 16:30:00",
    "thumbnail": "image://https%3a%2f%2fimg.example%2fp.jpg/",
}


def test_the_broadcast_is_matched_on_its_start():
    start = datetime(2026, 11, 14, 13, 40, tzinfo=UTC)
    other = dict(BROADCAST, starttime="2026-11-14 16:30:00", broadcastid=8)
    assert programme.find_broadcast([other, BROADCAST], start)["broadcastid"] == 7
    assert programme.find_broadcast([other], start) is None


def test_the_request_carries_the_padded_window_and_the_programme():
    request = programme.build_request("ITV 1", "101", BROADCAST, 2, 15)
    assert request == {
        "ChannelName": "ITV 1",
        "ChannelNumber": "101",
        "StartUtc": "2026-11-14T13:38:00Z",
        "EndUtc": "2026-11-14T16:45:00Z",
        "Title": "Wales v New Zealand: Nations Championship",
        "Plot": "Live coverage.",
        "ImageUrl": "https://img.example/p.jpg",
    }
    assert programme.build_request("ITV 1", "101", dict(BROADCAST, endtime="")) is None


def test_a_programme_counts_as_finished_only_once_it_has_ended():
    request = programme.build_request("ITV 1", "101", BROADCAST)
    assert programme.has_finished(request, datetime(2026, 11, 14, 16, 30, tzinfo=UTC))
    assert not programme.has_finished(request, datetime(2026, 11, 14, 16, 29, tzinfo=UTC))
