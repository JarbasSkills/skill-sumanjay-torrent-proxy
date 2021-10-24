from os.path import join, dirname

import requests
from ovos_plugin_common_play.ocp import MediaType, PlaybackType
from ovos_utils.parse import fuzzy_match
from ovos_workshop.skills.common_play import OVOSCommonPlaybackSkill, \
    ocp_search, ocp_play


class SumanjayTorrentProxySkill(OVOSCommonPlaybackSkill):
    def __init__(self):
        super(SumanjayTorrentProxySkill, self).__init__(
            "SumanjayTorrentProxy")
        self.supported_media = [MediaType.GENERIC, MediaType.MOVIE,
                                MediaType.ADULT]
        self.skill_icon = join(dirname(__file__), "ui", "logo.png")

    @staticmethod
    def calc_score(phrase, torrent, media_type, idx=0, base_score=0):
        removes = ["WEBRip", "x265", "HDR", "DTS", "HD", "BluRay", "uhd",
                   "1080p", "720p", "BRRip", "XviD", "MP3", "2160p",
                   "h264", "AAC", "REMUX", "SDR", "hevc", "x264",
                   "REMASTERED", "SUBBED", "DVDRip"]
        removes = [r.lower() for r in removes]
        clean_name = torrent["title"].replace(".", " ").replace("-", " ")
        clean_name = " ".join([w for w in clean_name.split()
                               if w and w.lower() not in removes])
        score = base_score - idx
        score += fuzzy_match(phrase.lower(), clean_name) * 100
        if media_type == MediaType.MOVIE:
            score += 15
        return score

    @staticmethod
    def search_sumanjay(query):
        url = "https://api.sumanjay.cf/torrent/"
        results = requests.get(url, params={"query": query}).json()
        results = sorted(results, key=lambda k: k["seeder"], reverse=True)
        for r in results:
            if r["nsfw"] or "porn" in r["type"].lower():
                r["type"] = "XXX"
            yield {"title": r["name"],
                   "magnet": r["magnet"],
                   "category": r["type"],
                   "seeders": int(r["seeder"])}

    @ocp_search()
    def search_torrents(self, phrase, media_type):
        base_score = 0
        if self.voc_match(phrase, "torrent"):
            phrase = self.remove_voc(phrase, "torrent")
            base_score = 40

        adult = False
        # no accidental porn results!
        if self.voc_match(phrase, "porn") or media_type == MediaType.ADULT:
            phrase = self.remove_voc(phrase, "porn")
            adult = True

        idx = 0
        for torr in self.search_sumanjay(phrase):
            if adult and torr["category"] != "XXX":
                continue
            elif torr["category"] != "Movies":
                continue
            if torr["seeders"] < 1:
                continue
            score = self.calc_score(phrase, torr, media_type, idx, base_score)
            yield {
                "title": torr["title"],
                "match_confidence": score,
                "media_type": MediaType.VIDEO,
                "uri": torr["magnet"],
                "image": torr.get("image") or self.skill_icon,
                "playback": PlaybackType.SKILL,
                "skill_icon": self.skill_icon,
                "skill_id": self.skill_id
            }
            idx += 1

    @ocp_play()
    def stream_torrent(self, message):
        self.bus.emit(message.forward("skill.peerflix.play", message.data))


def create_skill():
    return SumanjayTorrentProxySkill()
