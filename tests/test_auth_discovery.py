import json

from catchup import auth, discovery


def test_addresses_are_normalised_like_kofins():
    assert auth.normalize_address("192.0.2.5") == "http://192.0.2.5:8096"
    assert auth.normalize_address("https://jf.example/") == "https://jf.example"
    assert auth.normalize_address("http://user:pw@jf.example:8920/jf/") == "http://jf.example:8920/jf"
    assert auth.normalize_address("  ") == ""


def test_the_auth_header_names_this_client():
    header = auth.build_auth_header("Living room", "dev1", "0.1.0", "tok")
    assert header.startswith('MediaBrowser Client="Catchup Download"')
    assert 'Device="Living%20room"' in header
    assert header.endswith('Token="tok"')


class FakeSocket:
    def __init__(self, replies):
        self.replies = list(replies)
        self.sent = []

    def sendto(self, data, address):
        self.sent.append((data, address))

    def settimeout(self, value):
        pass

    def recvfrom(self, size):
        if self.replies:
            return self.replies.pop(0)
        raise discovery.socket.timeout()

    def close(self):
        pass


def test_discovery_reports_each_server_once():
    reply = json.dumps({"Address": "http://192.0.2.5:8096", "Id": "s1", "Name": "Home"}).encode()
    sock = FakeSocket([(reply, ("192.0.2.5", 7359)), (reply, ("192.0.2.5", 7359))])
    ticks = iter([0.0, 0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.5])
    found = discovery.scan(sock_factory=lambda: sock, clock=lambda: next(ticks))
    assert [f.name for f in found] == ["Home"]
    assert sock.sent[0] == (b"who is JellyfinServer?", ("255.255.255.255", 7359))


def test_the_fallback_address_uses_the_datagrams_source():
    found = discovery.Found("s1", "Home", "http://jf.example:8096", "192.0.2.5")
    assert discovery.fallback_address(found) == "http://192.0.2.5:8096"
