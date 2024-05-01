# coding: utf-8
from __future__ import unicode_literals

import re
import json

from math import log10, floor, ceil
from datetime import date, datetime
from urllib.error import HTTPError

from yt_dlp.utils.traversal import traverse_obj
from yt_dlp.extractor.common import InfoExtractor
from yt_dlp.utils import (
    ExtractorError,
    parse_iso8601,
    parse_duration,
    unified_timestamp,
    clean_html,
    sanitize_url,
    urlencode_postdata,
    int_or_none,
    str_or_none,
    url_or_none,
)

#   FIXME   No description found
#           https://r4.err.ee/1609221212/razbor-poljotov


def json_find_match(obj, criteria):
    """
    Searches depth first for an object that matches all
    criteria and returns it. None if nothing is found.
    """
    if not isinstance(criteria, dict):
        raise TypeError('Should be dictionary, but is %s' % type(criteria))
    if isinstance(obj, (tuple, list)):
        for element in obj:
            val = json_find_match(element, criteria)
            if val is not None:
                return val
    elif isinstance(obj, dict):
        failed = False
        for key in criteria:
            if key not in obj or obj[key] != criteria[key]:
                failed = True
        if not failed:
            return obj
        for k in obj:
            val = json_find_match(obj[k], criteria)
            if val is not None:
                return val
    return None


def json_find_value(obj, key):
    """
    Searches depth first for a key (key1.key2...key_n) in json
    structure and returns its value, i.e. that what it points to, or None.
    """
    if isinstance(obj, (tuple, list)):
        for element in obj:
            val = json_find_value(element, key)
            if val is not None:
                return val
    elif isinstance(obj, dict):
        val = json_get_value(obj, key)
        if val is not None:
            return json_get_value(obj, key)
        for k in obj:
            val = json_find_value(obj[k], key)
            if val is not None:
                return val
    return None


def json_has_value(obj, key):
    """
    Checks for existence of value at key1.key2...key_n etc.
    '', (), [], {}, '', 0 are considered as no value, i.e.
    anything that converts to boolean False.
    """
    return json_get_value(obj, key, convert=bool, default=False)


def json_get_value(obj, key, convert=None, default=None):
    """
    Gets value at key1.key2...key_n etc., or a default value.
    Result can be converted by 'convert'.
    """
    for k in key.split('.'):
        if isinstance(obj, dict) and (k in obj) and obj[k]:
            obj = obj[k]
        elif isinstance(obj, (list, tuple)) and k.isdigit() and int(k) < len(obj):
            obj = obj[int(k)]
        else:
            return default
    return obj if not convert else convert(obj)


def string_or_none(v):
    return str(v) if v else None


def timestamp_from_date(date_str):
    months = {'jaanuar': 1,
              'veebruar': 2,
              'märts': 3,
              'aprill': 4,
              'mai': 5,
              'juuni': 6,
              'juuli': 7,
              'august': 8,
              'september': 9,
              'oktoober': 10,
              'november': 11,
              'detsember': 12, }
    # date_format = '%d. %B %Y'
    m = re.search(r'(\d+)\.\s+(\w+)\s+(\d{4})', date_str)
    if not m:
        raise ValueError
    return datetime.timestamp(datetime(m[3], months[m[2]], m[1]))

def padding_width(count):
    """Returns number of positions needed to format indexes <= count."""
    return floor(log10(count)) + 1 if count else 1


def sanitize_title(title):
    """Replaces [/.?!|] with '-', strips dots and spaces, suppresses '*', all
    sorts of quotes and fancy characters. """
    if not title:
        return None
    title = re.sub(r'[*+"\'«»„`´]+', '', title)
    title = re.sub(r'[,;]+', ' ', title)
    title = re.sub(r'\s+', ' ', title)
    title = title.replace(u'\u2014', '-')\
        .strip().strip('.?!:').strip()
    title = re.sub(r'[?!]+', '.', title)
    return ' - '.join(map(lambda s: s.strip(), re.split(r'[/|]+', title)))


class _UglyERRBaseIE(InfoExtractor):
    _GEO_COUNTRIES = ['EE']
    _GEO_BYPASS = False
    _ERR_CHANNELS = ''
    _ERR_EXTRACTOR_ARG_PREFIX = 'UglyERR'
    _ERR_TERMS_AND_CONDITIONS_URL = 'https://info.err.ee/982667/kasutustingimused-ja-kommenteerimine'
    _VALID_URL = ''
    _LANG2ISO639_TBL = {
        'eesti': 'et',
        'vene': 'ru',
        'inglise': 'en',
        'soome': 'fi',
        'saksa': 'de',
    }
    _FORMAT_ID_TBL = {
        'video': {
            'mp4': {
                '180p': '132',
                '288p': '133',
                '396p': '134',
                '480p': '135',
                '720p': '136',
                '1080p': '137',
            },
        },
        'audio': {
            'm4a': {
                '64k': '138',
                '48k': '139',
                '128k': '140',
                '151k': '142',
                '224k': '143',
                '256k': '141',
            },
        },
    }
    _ERR_FORMAT_COUNTERS = {}
    _ERR_URL_SET = set()
    _ERR_HEADERS = {}

    @staticmethod
    def _lang_to_iso639(lang):
        return _UglyERRBaseIE._LANG2ISO639_TBL.get(lang.lower(), lang)

    def _reset_format_counters(self):
        self._ERR_FORMAT_COUNTERS.clear()

    def _next_format_postfix(self, format_id):
        """
        Increments counter associated to format_id, and returns "-counter"
        if counter > 0, otherwise returns an empty string.
        """
        counter = (self._ERR_FORMAT_COUNTERS[format_id] + 1) if (
            format_id in self._ERR_FORMAT_COUNTERS) else 0
        self._ERR_FORMAT_COUNTERS[format_id] = counter
        return '' if counter == 0 else '-%d' % counter

    def _assign_format_id(self, format_desc):
        if (format_desc.get('acodec', 'none') == 'none'
                and format_desc.get('vcodec', 'none') != 'none'):
            key = 'video.%s.%dp' % (
                format_desc['ext'], format_desc['height'])
            if format_id := json_get_value(self._FORMAT_ID_TBL, key):
                return format_id
        return format_desc['format_id']

    def _sanitize_formats_and_subtitles(self, formats, subtitles):
        for fmt in formats:
            if fmt.get('vcodec', 'none') == 'none':
                if fmt.get('language', 'ch') == 'ch':
                    # Chamoru [ch] extremely unlikely, seems to mean
                    # 'original'.
                    fmt['language'] = 'original'
                    fmt['format_note'] = 'Original'
                elif fmt.get('language', None) is None:
                    fmt['language'] = 'unknown'
                    fmt['format_note'] = 'Unknown'
                elif fmt.get('language', '') == 'nl':
                    # Nederlands [nl] seems to mean consistently
                    # 'et for visually impaired'.
                    fmt['language'] = 'et_vis_imp'
                    fmt['format_note'] = 'Eesti vaegnägijatele'

                lst = self._configuration_arg(fmt['language'], ie_key=self._ERR_EXTRACTOR_ARG_PREFIX)
                if lst:
                    fmt['language'] = str(lst[0])

                fmt['format_id'] = '%s%s' % (
                    fmt['language'],
                    self._next_format_postfix(fmt['language']))

            fmt['format_id'] = self._assign_format_id(fmt)

            if fmt.get('vcodec', 'none') != 'none':
                fmt['format_id'] = '%s%s' % (
                    fmt['format_id'],
                    self._next_format_postfix(fmt['format_id']))
                fmt['format_note'] = '%dp' % fmt['height']
                fmt['format'] = '%(format_id)s - %(width)dx%(height)d (%(format_note)s)' % fmt

        subs = {}
        for lang, subtitle in subtitles.items():
            lang = 'et_hearing_impaired' if lang == 'und' else lang
            lst = self._configuration_arg(lang.lower(), ie_key=self._ERR_EXTRACTOR_ARG_PREFIX)
            lang = lst[0] if lst else lang
            subs[lang] = subtitle

        return formats, subs

    def _extract_formats(self, master_url, video_id):
        formats, _ = self._extract_formats_and_subtitles(master_url, video_id)
        return formats

    def _extract_formats_and_subtitles(self, master_url, video_id, headers=None):
        m3u8_formats = []
        m3u8_subtitles = {}
        try:
            m3u8_formats, m3u8_subtitles = self._extract_m3u8_formats_and_subtitles(master_url, video_id, headers=headers)
        except ExtractorError as ex:
            if isinstance(ex.cause, HTTPError) and ex.cause.code == 404:
                self.report_warning(
                    'master url links to nonexistent resource \'%s\'' %
                    master_url)
            raise ex
        return self._sanitize_formats_and_subtitles(m3u8_formats, m3u8_subtitles)

    def _extract_ids(self, url):
        mobj = re.match(type(self)._VALID_URL, url)
        return mobj.groupdict()

    # For debugging use self.write_debug()
    def _dump_json(self, obj, sort_keys=False, msg=None, filename=None):
        """Dumps prettyprinted json structure"""
        if filename:
            with open(filename, mode='a', encoding='utf-8') as f:
                if msg:
                    f.write(f'\n{msg}\n')
                f.write(json.dumps(obj, indent=4, sort_keys=sort_keys))
        else:
            self.to_screen('[debug] ' + (msg if msg else '') + json.dumps(obj, indent=4, sort_keys=sort_keys))


class UglyERRNewsIE(_UglyERRBaseIE):
    IE_DESC = 'err.ee: videos and audio material embedded in news articles'
    _ERR_CHANNELS = r'uudised|kultuur|sport|menu|novaator|news|rus|www'
    _VALID_URL = r'(?P<prefix>(?P<scheme>https?)://(?P<channel>%(channels)s).err.ee)/(?P<id>[^/]*)/(?P<display_id>[^/#?]*)' % {
        'channels': _ERR_CHANNELS
    }
    _TESTS = [{
        # Single video linked to an article
        'url': 'https://sport.err.ee/1608242040/kirt-tuli-lukata-selg-sirgu-ja-oelda-mis-seis-on',
        'md5': '7cc3b40f4d45106896978aa66f3f497e',
        'info_dict': {
            'id': '1608242040',
            'display_id': 'kirt-tuli-lukata-selg-sirgu-ja-oelda-mis-seis-on',
            'ext': 'm4a',
            'title': 'Kirt: tuli lükata selg sirgu ja öelda mis seis on',
            'thumbnail':
            'https://s.err.ee/photo/crop/2020/05/01/775316hc459t24.jpg',
            'description': 'md5:de38c3349a81c988326cc90f38c26f74',
            'upload_date': '20210610',
            'timestamp': 1623322980,
            'categories': ['Kergejõustik'],
            'creator': 'Juhan Kilumets - ERR',
            'tags': ['odavise', 'magnus kirt'],
        }
    }, {
        # Multiple videos in one article
        'url':
        'https://sport.err.ee/1608229491/warneril-jai-9000-punktist-ulinapilt-puudu-lillemets-pustitas-rekordi',
        'info_dict': {
            'id': '1608229491',
            'display_id': 'warneril-jai-9000-punktist-ulinapilt-puudu-lillemets-pustitas-rekordi',
            'title': 'Warneril jäi 9000 punktist ülinapilt puudu Lillemets püstitas rekordi',
            'thumbnail':
            'https://s.err.ee/photo/crop/2021/05/30/1024863h097et24.jpg',
            'description': 'md5:62eb6e3ffc51ce68a3c0c060e26f4c0e',
            'timestamp': 1622376000,
            'creator': 'ERR',
            'categories': ['Kergejõustik'],
            'tags': ['kristjan rosenberg', 'maicel uibo', 'damian warner', 'götzise mitmevõistlus', 'risto lillemets'],
            'upload_date': '20210530',
        },
        'playlist_count': 7,
        'params': {
            'format': 'bestaudio',
        },
    }, {
        # Multiple embedded videos in one article
        'url':
        'https://kultuur.err.ee/1608245691/iggy-pop-annab-tallinnas-kontserdi',
        'info_dict': {
            'id': '1608245691',
            'display_id': 'iggy-pop-annab-tallinnas-kontserdi',
            'title': 'Iggy Pop annab Tallinnas kontserdi',
            'description': 'md5:1635e54e66d7e6ad92d1d74185068791',
            'timestamp': 1623658200,
            'tags': ['iggy pop'],
            'creator': 'ERR',
            'thumbnail': 'https://s.err.ee/photo/crop/2021/06/14/1038456he481t24.jpg',
            'categories': ['Muusika'],
            'upload_date': '20210614',
        },
        'playlist_count': 3,
        'params': {
            'format': 'bestvideo+bestaudio',
        },
    }, {
        # One embedded audio
        'url':
        'https://sport.err.ee/1608243468/jaak-heinrich-jagor-tervisemuredest-treeningutel-on-ule-treenitud',
        'info_dict': {
            'id': '1608243468',
            'display_id': 'jaak-heinrich-jagor-tervisemuredest-treeningutel-on-ule-treenitud',
            'title': 'Jaak-Heinrich Jagor tervisemuredest: treeningutel on üle treenitud',
            'description': 'md5:c4566d404a363836031c9585e8907f0f',
            'timestamp': 1623394980,
            'tags': ['jaak heinrich jagor', 'staadionijutud'],
            'categories': ['Kergejõustik'],
            'upload_date': '20210611',
            'creator': 'ERR',
            'thumbnail': 'https://s.err.ee/photo/crop/2021/06/11/1035948h5a18t24.jpg',
        },
        'playlist_count': 1,
        'params': {
            'format': 'bestaudio',
        },
    }]

    def _extract_entries(self, url_list, video_id):
        for (url, uid) in url_list:
            info = {}
            page = self._download_webpage(url, video_id)
            if not page:
                self.report_warning(f'No video page available for {url}')
                continue
            # FIXME search for dash too
            # hls, hls2, hlsNew and hlsNoSub are available, only hlsNoSub seems to work.
            mobj = re.search(r'(["\'])hlsNoSub\1\s*:\s*(["\'])(?P<master_url>[^\2]+master.m3u8)\2', page)
            if not mobj:
                self.report_warning(f'No master url available for {url}')
                continue
            master_url = mobj.group('master_url').replace('\\', '')
            info['url'] = master_url
            info['formats'] = self._extract_formats(master_url, video_id)
            info['id'] = video_id + '_' + uid
            mobj = re.search(r'(["\'])image\1\s*:\s*(["\'])(?P<image>[^\2]+?\.jpg)\2', page)
            if mobj:
                info['thumbnail'] = mobj.group('image').replace('\\', '')
            yield info

    def _postprocess_entries(self, entries, info, playlist_type='multi_video'):
        count = len(entries)
        err_count = 0
        for entry in entries:
            if 'id' in entry:
                err_count += 1
        if count - err_count > 0 or err_count > 1:
            info['_type'] = playlist_type
        if count == 0:
            raise ExtractorError('No media available')
        if err_count == 1 and count == 1:
            entries[0].pop('id', None)
            info.update(entries[0])
        else:
            p = padding_width(err_count)
            for (idx, entry) in enumerate(filter(lambda d: 'id' in d, entries), start=1):
                entry['title'] = info['title'] + (' - %0' + str(p) + 'd') % idx
                entry['timestamp'] = info['timestamp']
                if (idx == 0) and not entry.get('thumbnail'):
                    entry['thumbnail'] = info.get('thumbnail')
            info['entries'] = entries
        return info

    def _extract_html_metadata(self, webpage):
        info = {}
        info['title'] = (
            self._og_search_title(webpage)
            or self._html_search_meta('twitter:title', webpage)
            or self._html_search_regex(
                r'<head>[^<]*<title>([^|]+)[^<]*?</title>',
                webpage,
                'title',
                flags=re.DOTALL))
        # Sometimes title would still contain suffixes ' | Vikerraadio | ERR '
        info['title'] = info['title'].split('|')[0].strip().strip('.')
        if not info['title']:
            raise ExtractorError('Couldn\'t extract title')
        info['title'] = sanitize_title(info['title'])
        info['description'] = (
            self._html_search_meta('description', webpage)
            or self._og_search_description(webpage)
            or self._html_search_meta('twitter:description', webpage))
        # Sometimes description too would still contain suffixes ' | Vikerraadio | ERR '
        info['description'] = info['description'].split('|')[0].strip()
        info['thumbnail'] = self._og_search_thumbnail(webpage)

        info['creator'] = sanitize_title(self._html_search_meta('author', webpage))
        info['tags'] = self._html_search_meta('keywords', webpage, default=None)
        if info['tags']:
            info['tags'] = info['tags'].split(',')

        info['categories'] = self._html_search_meta(
            'article:section', webpage, default=None)
        if info['categories']:
            info['categories'] = info['categories'].split(',')
        info['timestamp'] = parse_iso8601(
            self._html_search_meta('article:published_time', webpage))
        return info

    def _real_extract(self, url):
        self._reset_format_counters()
        info = dict()
        url_dict = self._extract_ids(url)
        video_id = url_dict['id']
        prefix = url_dict['prefix']
        scheme = url_dict['scheme']
        info['id'] = video_id
        info['display_id'] = url_dict['display_id']
        info['webpage_url'] = url

        webpage = self._download_webpage(url, video_id)

        info.update(self._extract_html_metadata(webpage))

        url_list = []
        entries = []
        mobj = re.findall(r'data-html-src=(["\'])(?P<url>/media/videoBlock/([0-9abcdefABCDEF]+?))(?:\1|\?)', webpage)
        for m in mobj:
            url_list.append((prefix + m[1], m[2]))
        mobj = re.findall(r'<iframe.+?src=(["\'])(?P<url>//.*?/media/embed/([0-9abcdefABCDEF]+?))\1', webpage, flags=re.DOTALL)
        for m in mobj:
            url_list.append((scheme + ':' + m[1], m[2]))
        # Embedded Youtube/Soundcloud
        sites = r'youtube\.com|soundcloud\.com'
        mobj = re.findall(
            r'<iframe.+?src=(["\'])(.*?(?:%(sites)s).+?)\1' % {'sites': sites},
            webpage, flags=re.DOTALL)
        for m in mobj:
            entries.append({'url': m[1], '_type': 'url'})
        # TODO Embedded Twitter and possibly others

        entries.extend(self._extract_entries(url_list, video_id))

        info.update(self._postprocess_entries(entries, info))

        return info


class _UglyERRLoginIE(_UglyERRBaseIE):
    _ERR_API_GET_CONTENT = '%(prefix)s/api/tv/getTvPageData?contentId=%(id)s'
    _ERR_API_GET_CONTENT_FOR_USER = _ERR_API_GET_CONTENT
    _ERR_API_GET_PARENT_CONTENT = '%(prefix)s/api/tv/getCategoryPastShows?parentContentId=%(playlist_id)s&periodStart=0&periodEnd=0&fullData=1'
    _ERR_API_SHOWDATA_KEY = 'mainContent'
    _ERR_API_USE_SEASONLIST = False
    _ERR_CHANNELS = r''
    _ERR_LOGIN_DATA = {}
    _ERR_LOGIN_SUPPORTED = True
    _NETRC_MACHINE = 'err.ee'
    _VALID_URL = ''

    def _real_initialize(self):
        super(_UglyERRLoginIE, self)._real_initialize()

    def _perform_login(self, username, password):
        if not self._ERR_LOGIN_SUPPORTED or not username or not password:
            return
        if self._is_logged_in():
            self.write_debug('Already logged in')
            return
        login_data = self._download_json(
            'https://services.err.ee/api/auth/login', 'UglyERRLogin',
            note='Logging in', errnote='Unable to log in', fatal=False,
            data=urlencode_postdata({
                'pass': password,
                'user': username,
            }))
        if login_data.get('success', False):
            self._ERR_LOGIN_DATA = login_data
            self._set_cookie('.err.ee', 'atlId', login_data['user']['atlId'])
            self._set_cookie('.err.ee', 'allowCookiesV2', 'true')
        else:
            raise ExtractorError('Login failed.', expected=True)

    def _is_logged_in(self):
        return self._ERR_LOGIN_DATA and self._ERR_LOGIN_DATA.get('success', False)

    def _set_headers(self, url_dict):
        self._ERR_HEADERS['Origin'] = '%(prefix)s' % url_dict
        self._ERR_HEADERS['Referer'] = '%(prefix)s/' % url_dict
        self._ERR_HEADERS['x-srh'] = '1'

    def _rewrite_url(self, url):
        """
        Rewrites geoblocked url to contain login token and to always use https
        protocol. Leaves the url unchanged, if not logged in.
        """
        return url if not self._is_logged_in() else re.sub(
            r'https?:(//[^/]+/)',
            r'https:\g<1>%(atlId)s/' % self._ERR_LOGIN_DATA['user'], url)

    def _extract_thumbnails(self, show_data, key, max_side=400, min_side=0):
        """Generator for extracting images from a json structure"""
        if not show_data:
            return
        keys = []
        if isinstance(key, (tuple, list, set)):
            keys.extend(key)
        else:
            keys.append(str(key))
        for k in keys:
            if k not in show_data:
                continue
            # Search for images that have width <= 400
            for photo in show_data[k]:
                for p in photo['photoTypes'].values():
                    if (p['w'] <= max_side and p['h'] <= max_side
                            and p['w'] >= min_side and p['h'] >= min_side):
                        yield {'url': sanitize_url(p['url']),
                               'width': p['w'],
                               'height': p['h']}

    def _merge_thumbnails(self, thumbnails):
        info = {}
        if not isinstance(thumbnails, (list, tuple)):
            thumbnails = list(thumbnails)
        if len(thumbnails) > 1:
            info['thumbnails'] = thumbnails
        elif len(thumbnails) == 1:
            info['thumbnail'] = thumbnails[0]['url']
        return info

    def _extract_medias(self, obj, video_id):
        """Extracts formats, subtitles"""
        info = {}
        formats, subtitles = [], {}
        for media in obj.get('medias') or []:
            info['geoblocked'] = json_get_value(media, 'restrictions.geoBlock', default=False)
            if info['geoblocked'] and not self._is_logged_in():
                # FIXME Is there a way to ignore this restriction only in Estonia?
                self.raise_geo_restricted(
                    msg='This video/audio is geoblocked, you may have to login to access it.')
            info['drm'] = json_get_value(media, 'restrictions.drm', default=False)
            if info['drm']:
                self.report_drm(video_id)
            # media_type can be video/audio, for debugging only
            info['media_type'] = media['type']
            if json_has_value(media, 'headingEt'):
                # A good candidate to extract 'episode', but rarely available.
                info['title'] = media['headingEt']

            if url := traverse_obj(media,
                                   ('src', 'hls', {url_or_none}, {sanitize_url},
                                    {lambda x: self._rewrite_url(x)})):
                fmts, subs = self._sanitize_formats_and_subtitles(
                    *self._extract_m3u8_formats_and_subtitles(
                        url, video_id, 'mp4', m3u8_id='hls', fatal=False))
                formats.extend(fmts)
                self._merge_subtitles(subs, target=subtitles)

            if url := traverse_obj(media, ('src', 'dash', {url_or_none},
                                           {sanitize_url}, {lambda x:
                                                            self._rewrite_url(x)})):
                fmts, subs = self._sanitize_formats_and_subtitles(
                    *self._extract_mpd_formats_and_subtitles(
                        url, video_id, mpd_id='dash', fatal=False))
                formats.extend(fmts)
                self._merge_subtitles(subs, target=subtitles)

        info['formats'] = formats
        info['subtitles'] = subtitles
        return info

    def _extract_entry(self, obj, channel=None, extract_medias=True, extract_thumbnails=True):
        info = {}
        info['_type'] = 'video' if extract_medias else 'url'
        info['content_type'] = obj.get('type')
        info['webpage_url'] = obj.get('canonicalUrl')
        info['id'] = str(obj.get('id'))
        info['display_id'] = obj.get('fancyUrl')
        info['timestamp'] = json_get_value(obj, 'publicStart', int_or_none)
        info['title'] = obj.get('heading')
        info['alt_title'] = json_get_value(obj, 'subHeading', string_or_none)

        if json_get_value(obj, 'rootContent.type') == 'series':
            info['series'] = json_get_value(obj, 'rootContent.heading')
            info['series_type'] = json_get_value(obj, 'rootContent.seriesType')
            # rootContent.seriesType:
            # 1 is monthly,
            # 2, 3 is seasonal,
            # 5 is shortSeriesList.
            if info['series_type'] == 1 and json_has_value(info, 'timestamp'):
                updated = date.fromtimestamp(info['timestamp'])
                info['season'] = updated.strftime('%Y%m')
                info['episode_id'] = updated.strftime('%Y%m%d')
            else:
                info['episode_number'] = obj.get('episode')
                info['season_number'] = obj.get('season')

        if json_has_value(obj, 'lead'):
            info['description'] = clean_html(obj['lead'])
            if json_has_value(obj, 'body'):
                info['description'] = info['description'] + '\n\n' + clean_html(obj['body'])
            if json_has_value(obj, 'originalTitle') or json_has_value(obj, 'country') or (json_has_value(obj, 'year') and int(obj['year']) > 0):
                info['description'] = info['description'] + '\n'
            if json_has_value(obj, 'originalTitle'):
                info['description'] = info['description'] + '\n' + clean_html(obj['originalTitle'])
            if json_has_value(obj, 'country'):
                info['description'] = info['description'] + '\n' + clean_html(obj['country'])
            if json_has_value(obj, 'year') and int(obj['year']) > 0:
                info['description'] = info['description'] + '\n' + clean_html(obj['year'])

        if extract_thumbnails:
            info.update(self._merge_thumbnails(self._extract_thumbnails(obj, 'photos')))

        if extract_medias:
            info.update(self._extract_medias(obj, info['id']))
        else:
            info['url'] = obj.get('canonicalUrl')

        info['license'] = self._ERR_TERMS_AND_CONDITIONS_URL

        if info['content_type'] == 'episode':
            if 'headingFull' in obj:
                # 'headingFull' is only available in PLAYLISTDATA
                info['heading_full'] = obj['headingFull']
                mobj = re.match(r'Osa:\s*\d+(?::\s*(?P<episode>.*?))?\Z', obj['headingFull'])
                if mobj and mobj.group('episode'):
                    info['episode'] = sanitize_title(mobj.group('episode'))
                elif json_has_value(info, 'series'):
                    mobj = re.match(r'(?:%(series)s|(?:[^.:]*))[.:]\s*(?P<episode>.*?)\Z' % info, obj['headingFull'])
                    if mobj and mobj.group('episode'):
                        info['episode'] = sanitize_title(mobj.group('episode'))
                else:
                    mobj = re.match(r'[^.:]*[.:]\s*(?P<episode>.*?)\Z', obj['headingFull'])
                    if mobj and mobj.group('episode'):
                        info['episode'] = sanitize_title(mobj.group('episode'))
            if not json_has_value(info, 'episode') and json_has_value(info, 'series'):
                mobj = re.match(r'(?:%(series)s|(?:[^.:]*))[.:]\s*(?P<episode>.*?)\Z' % info, info['title'])
                if mobj and mobj.group('episode'):
                    info['episode'] = sanitize_title(mobj.group('episode'))
            if not json_has_value(info, 'episode'):
                mobj = re.match(r'[^.:]*[.:]\s*(?P<episode>.*?)\Z', info['title'])
                if mobj and mobj.group('episode'):
                    info['episode'] = sanitize_title(mobj.group('episode'))
            if not json_has_value(info, 'episode') and json_has_value(info, 'series'):
                if info['title'].find(info['series']) == -1:
                    info['episode'] = info['title']
            if not json_has_value(info, 'episode') and obj['subHeading']:
                # 'subHeading' in that format is only available in SHOWDATA
                # Sometimes subHeading can be complex
                # e.g. 'subHeading': 'Hooaeg: 28, Osa: 1044, 2021 Ornitoloogia\u00fching 100'
                mobj = re.match(r'Osa:\s*\d+(?:,\s*(?P<episode>.*?))?\Z', obj['subHeading'])
                if mobj and mobj.group('episode'):
                    info['episode'] = sanitize_title(mobj.group('episode'))

        if info['content_type'] == 'episode':
            # series - episode | episode_nr
            name = []
            if json_has_value(info, 'series'):
                name.append(info['series'])
            if json_has_value(info, 'season_number') and json_has_value(info, 'episode_number'):
                name.append('S%02dE%02d' % (info['season_number'], info['episode_number']))
            elif json_has_value(info, 'season'):
                name.append(info['season'])
            if json_has_value(info, 'episode'):
                name.append(info['episode'])
            elif json_has_value(info, 'alt_title'):
                name.append(info['alt_title'])
            if len(name) > 1:
                info['title'] = ' - '.join(name)
        info['title'] = sanitize_title(info['title'])

        return info

    def _extract_extra(self, obj):
        info = {}
        publisher_data = json_find_value(obj, 'newsArticleStruct')
        if json_has_value(publisher_data, 'datePublished'):
            info['release_timestamp'] = parse_iso8601(publisher_data['datePublished'])

        makers_data = json_find_value(obj, 'makers')
        if json_has_value(makers_data, 'makers'):
            authors = []
            for maker in makers_data:
                authors.append('%s (%s)' % (maker['name'], maker['type'].lower()))
            info['creator'] = ', '.join(authors)

        if json_has_value(obj, 'data.category.name'):
            info['categories'] = json_get_value(obj, 'data.category.name')

        return info

    def _fetch_playlist(self, url_dict, video_id,
                        include_root=False, root_data=None,
                        extract_thumbnails=False, extract_medias=False,
                        playlist_data=None):
        """url_dict should contain playlist_id"""
        info = {}
        reverse_list = True
        if not playlist_data:
            playlist_data = self._api_get_parent_content(url_dict, video_id)

        if 'newestFirst' in playlist_data:
            reverse_list = False if not playlist_data['newestFirst'] else True
        elif 'contentOrder' in playlist_data:
            reverse_list = True if playlist_data['contentOrder'] == 'desc' else False

        entries = []
        channel = url_dict.get('channel', None)
        for item in self._get_playlist_items(url_dict, video_id, playlist_data):
            entry = self._extract_entry(item, channel=channel,
                                        extract_medias=extract_medias,
                                        extract_thumbnails=extract_thumbnails)
            self._ERR_URL_SET.add(entry['webpage_url'])
            entries.append(entry)
        if reverse_list:
            entries = list(reversed(entries))
        # All this reversing is somewhat sloppy and heuristic, but I couldn't
        # quite get my head around how it is supposed to work. However, at this
        # point it should be almost guaranteed that playlist is sorted from
        # oldest to newest.
        info['entries'] = entries
        if include_root:
            if not root_data:
                root_data = json_find_value(playlist_data, 'rootContent')
            info['id'] = str(root_data.get('id'))
            info['display_id'] = root_data.get('url')
            info['title'] = sanitize_title(root_data.get('heading'))
            info['_type'] = 'playlist'
            info['series_type'] = root_data.get('seriesType')
            if json_has_value(root_data, 'lead'):
                info['description'] = clean_html(root_data['lead'])
            elif json_has_value(root_data, 'body'):
                info['description'] = clean_html(root_data['body'])
            info.update(self._merge_thumbnails(
                self._extract_thumbnails(root_data, 'photos')))

        return info

    def _get_request_headers(self, url, request_headers=None):
        headers = {}
        if isinstance(request_headers, str):
            request_headers = [request_headers]
        if request_headers:
            for header in request_headers:
                if header == 'Cookie' and self._ERR_LOGIN_DATA:
                    cookies = []
                    for key, cookie in self._get_cookies(url).items():
                        cookies.append('%s=%s' % (key, cookie.value))
                    headers['Cookie'] = '; '.join(cookies)
                elif header in self._ERR_HEADERS:
                    headers[header] = self._ERR_HEADERS[header]
        return headers

    def _api_get_content(self, url_dict, video_id):
        # Arguments for getTvPageData:
        # * contentId=xxxxxxx
        # * parentContentId=xxxxxxx
        # * categoryDataOnly=boolean
        # * contentOnly=boolean
        api_get_content = self._ERR_API_GET_CONTENT_FOR_USER if self._ERR_LOGIN_DATA\
            else self._ERR_API_GET_CONTENT
        headers = self._get_request_headers(api_get_content % url_dict,
                                            ['Referer', 'Origin', 'x-srh', 'Cookie'])
        return self._download_json(api_get_content % url_dict, video_id, headers=headers)

    def _api_get_parent_content(self, url_dict, video_id):
        headers = self._get_request_headers(self._ERR_API_GET_PARENT_CONTENT % url_dict,
                                            ['Referer', 'Origin', 'x-srh', 'Cookie'])
        return self._download_json(
            self._ERR_API_GET_PARENT_CONTENT % url_dict, video_id,
            headers=headers)

    def _get_playlist_items(self, url_dict, video_id, playlist_data):
        """Generator of playlist items"""
        if 'data' in playlist_data:
            # /api/tv/getCategoryPastShows
            for item in playlist_data['data']:
                yield item
        elif 'items' in playlist_data:
            # SeasonList data source has one major drawback, list items don't
            # contain master urls.
            if playlist_data['type'] == 'monthly':
                for year in playlist_data['items']:
                    for month in year['items']:
                        if 'active' not in month:
                            udict = url_dict.copy()
                            udict['id'] = month['firstContentId']
                            page = self._api_get_content(udict, video_id)
                            month = json_find_match(page, month)
                        for item in month['contents']:
                            yield item
            elif playlist_data['type'] in ['shortSeriesList', 'seasonal']:
                for season in playlist_data['items']:
                    if 'contents' not in season:
                        udict = url_dict.copy()
                        udict['id'] = season['firstContentId']
                        page = self._api_get_content(udict, video_id)
                        season = json_find_match(page, season)
                    for item in season['contents']:
                        yield item

    def _real_extract(self, url):
        self._reset_format_counters()
        info = dict()
        url_dict = self._extract_ids(url)
        if url_dict['id']:
            info['id'] = url_dict['id']
        if url_dict.get('display_id'):
            info['display_id'] = url_dict['display_id']
        # webpage_url may get changed to a canonical url later on
        info['webpage_url'] = url

        self._set_headers(url_dict)

        if url_dict.get('playlist_id'):
            playlist_id = url_dict['playlist_id']
            webpage = self._download_webpage(url, playlist_id)
            mobj = re.search(
                r'<script\s+type=(["\'])text/javascript\1[^>]*>'
                r'.*?window.rootContentId\s+=\s+(?P<playlist_id>\d+;).*?</script>',
                webpage, flags=re.DOTALL)
            if not mobj:
                mobj = re.search(
                    r'"rootContentId"\s*:\s*(?P<playlist_id>\d+)\s*,',
                    webpage, flags=re.DOTALL)
            if not mobj:
                raise ExtractorError('Unable to find playlist\'s numerical id \'rootContentId\'')
            playlist_id = mobj.group('playlist_id')
            url_dict['playlist_id'] = playlist_id
            info.update(self._fetch_playlist(
                url_dict, playlist_id, include_root=True, extract_medias=False, extract_thumbnails=False))
        elif info.get('id'):
            video_id = info['id']
            page = self._api_get_content(url_dict, video_id)
            show_data = json_find_value(page, self._ERR_API_SHOWDATA_KEY)
            playlist_id = str(json_find_value(show_data, 'rootContentId'))
            force_playlist = True if self._configuration_arg(
                'yes_playlist', ie_key=self._ERR_EXTRACTOR_ARG_PREFIX) else False
            if playlist_id and (
                    playlist_id == video_id or force_playlist) and url not in self._ERR_URL_SET:
                # It is a playlist again
                playlist_data = json_find_value(
                    page, 'seasonList') if self._ERR_API_USE_SEASONLIST else None
                url_dict['playlist_id'] = playlist_id
                info.update(self._fetch_playlist(
                    url_dict,
                    video_id,
                    include_root=True,
                    root_data=show_data['rootContent'],
                    playlist_data=playlist_data))
            else:
                # It is an episode
                entry = self._extract_entry(
                    show_data, channel=url_dict.get('channel', None))
                entry.update(self._extract_extra(page))
                info.update(entry)
        else:
            error_msg = 'No id available'
            self.report_warning(error_msg)
            raise ExtractorError(error_msg)

        return info


class UglyERRTVIE(_UglyERRLoginIE):
    IE_DESC = 'etv.err.ee, etv2.err.ee, etvpluss.err.ee, lasteekraan.err.ee'
    _ERR_API_GET_CONTENT = '%(prefix)s/api/tv/getTvPageData?contentId=%(id)s'
    _ERR_API_GET_CONTENT_FOR_USER = _ERR_API_GET_CONTENT
    _ERR_API_GET_PARENT_CONTENT = '%(prefix)s/api/tv/getCategoryPastShows?parentContentId=%(playlist_id)s&periodStart=0&periodEnd=0&fullData=1'
    _ERR_API_SHOWDATA_KEY = 'mainContent'
    _ERR_API_USE_SEASONLIST = False
    _ERR_CHANNELS = r'etv|etv2|etvpluss|lasteekraan'
    _ERR_LOGIN_SUPPORTED = True
    _VALID_URL = r'(?P<prefix>(?P<scheme>https?)://(?P<channel>%(channels)s).err.ee)/(?:(?:(?P<id>\d+)(?:/(?P<display_id>[^/#?]+))?)|(?P<playlist_id>[^/#?]*))(?P<leftover>[/?#].+)?\Z' % {
        'channels': _ERR_CHANNELS
    }
    _TESTS = [{
        # 0 etv.err.ee
        'url': 'https://etv.err.ee/1608179695/osoon',
        'md5': 'f3e007333f44b084a3bbe69a4b8b75e0',
        'info_dict': {
            'id': '1608179695',
            'display_id': 'osoon',
            'ext': 'mp4',
            'title': 'Osoon - S28E1044 - Ornitoloogiaühing 100',
            'episode': 'Ornitoloogiaühing 100',
            'series': 'Osoon',
            'season_number': 28,
            'episode_number': 1044,
            'thumbnail':
            'https://s.err.ee/photo/crop/2019/09/06/681521h8760t8.jpg',
            'description': 'md5:15f239cbbc45900e345850aff2679ddc',
            'upload_date': '20210415',
            'timestamp': 1618518000,
            'season': 'Season 28',
            'content_type': 'episode',
            'geoblocked': False,
            'release_timestamp': 1691211600,
            'drm': False,
            'release_date': '20230805',
            'media_type': 'video',
            'alt_title': 'Ornitoloogiaühing 100',
            'license': 'https://info.err.ee/982667/kasutustingimused-ja-kommenteerimine',
            'series_type': 2,
        },
        'params': {
            'format': 'bestvideo',
            'noplaylist': True,
            'skip_download': 'm3u8',
        },
    }, {
        # 1 etv2.err.ee
        'url': 'https://etv2.err.ee/1027382/tahelaev',
        'md5': 'a4af76897e2462417d503c03d114ca28',
        'info_dict': {
            'id': '1027382',
            'display_id': 'tahelaev',
            'ext': 'mp4',
            'title': 'Teemaõhtu. Ilon Wikland 90 - 202001 - Ilon Wikland osa: 299',
            'episode': 'Ilon Wikland osa: 299',
            'series': 'Teemaõhtu. Ilon Wikland 90',
            'season': '202001',
            'episode_id': '20200123',
            'thumbnail':
            'https://s.err.ee/photo/crop/2014/01/03/260872hb306t8.jpg',
            'description': 'md5:363344e5ff4a1834fac32fd2b11b3487',
            'upload_date': '20200123',
            'timestamp': 1579788000,
            'series_type': 1,
            'drm': False,
            'content_type': 'episode',
            'alt_title': 'Ilon Wikland',
            'license': 'https://info.err.ee/982667/kasutustingimused-ja-kommenteerimine',
            'release_timestamp': 1581276300,
            'release_date': '20200209',
            'geoblocked': False,
            'media_type': 'video',
        },
        'params': {
            'format': 'bestvideo',
            'noplaylist': True,
            'skip_download': 'm3u8',  # Otherwise fails as fragment too short
        },
    }, {
        # 2 etv.err.ee playlist
        '_type': 'playlist',
        'url':
        'https://etv.err.ee/4x4_tsukotka',
        'info_dict': {
            'id': '1608156007',
            'display_id': '4x4_tsukotka',
            'title': '4x4. Tšukotka',
            'series_type': 5,
        },
        'playlist_count': 10,
        'params': {
            'format': 'bestvideo',
        },
    }]


class UglyERRJupiterIE(_UglyERRLoginIE):
    IE_DESC = 'jupiter.err.ee, jupiterpluss.err.ee'
    _ERR_API_GET_CONTENT = 'https://services.err.ee/api/v2/vodContent/getContentPageData?contentId=%(id)s'
    _ERR_API_GET_CONTENT_FOR_USER = 'https://services.err.ee/api/v2/vodContent/getContentPageDataForUser?contentId=%(id)s'
    _ERR_API_USE_SEASONLIST = True
    _ERR_API_SHOWDATA_KEY = 'mainContent'
    _ERR_LOGIN_SUPPORTED = True
    _VALID_URL = r'(?P<prefix>(?P<scheme>https?)://jupiter(pluss)?.err.ee)/(?:(?P<id>\d+)(?:/(?P<display_id>[^/#?]*))?)(?P<leftover>.+)?\Z'
    _TESTS = [{
        # 0 An episode
        'url': 'https://jupiter.err.ee/1103424/paevabiit',
        'md5': '8e95250be144d6f29d7069492e4ddea9',
        'info_dict': {
            'id': '1103424',
            'display_id': 'paevabiit',
            'ext': 'mp4',
            'title': 'Retrodisko - S01E01 - Päevabiit',
            'episode': 'Päevabiit',
            'episode_number': 1,
            'series': 'Retrodisko',
            'thumbnail':
            'https://s.err.ee/photo/crop/2020/06/17/789134h64bct8.jpg',
            'description': 'md5:7fd0a8e066072097a88d6adbc18de35a',
            'upload_date': '20200618',
            'timestamp': 1592474400,
            'drm': False,
            'season_number': 1,
            'series_type': 5,
            'season': 'Season 1',
            'alt_title': 'Päevabiit - Rock ja pop',
            'geoblocked': False,
            'media_type': 'video',
            'content_type': 'episode',
            'license': 'https://info.err.ee/982667/kasutustingimused-ja-kommenteerimine',
        },
        'params': {
            'format': 'bestvideo',
            'noplaylist': True,
            'skip_download': 'm3u8',  # Otherwise fails as fragment too short
        },
    }, {
        # 1 A monthly playlist
        'skip': 'Spare err.ee',
        'url': 'https://jupiter.err.ee/1014230/dzassi-abg-wes-montgomery',
        '_type': 'playlist',
        'info_dict': {
            'id': '1038108',
            'display_id': 'dzassmuusika_abg',
            'title': 'Džässi ABG',
            'series_type': 1,
        },
        'playlist_mincount': 50,
        'params': {
            'noplaylist': False,
        },
    }, {
        # 2 A seasonal playlist
        'url': 'https://jupiter.err.ee/1133173/riigimehed',
        '_type': 'playlist',
        'info_dict': {
            'id': '1133173',
            'display_id': 'riigimehed',
            'title': 'Riigimehed',
            'series_type': 2,
        },
        'playlist_count': 14,
        'params': {
            'format': 'bestvideo',
            'noplaylist': False,
        },
    }, {
        # 3 Another seasonal playlist
        'skip': 'Spare err.ee',
        'url': 'https://jupiter.err.ee/1038446/pealtnagija',
        'md5': 'dd0203a487eb3a15aefdd9ce5132e0c9',
        'info_dict': {
            'id': '1038446',
            'display_id': 'pealtnagija',
            'title': 'Pealtnägija',
            'description': 'md5:62428ca943255a1694d9751f22eacc12',
            'series_type': 2,
        },
        'playlist_mincount': 228,
        'params': {
            'format': 'bestvideo',
            'noplaylist': False,
        },
    }, {
        # 4 A shortSeriesList playlist
        'url': 'https://jupiter.err.ee/1038584/alpimaja',
        'md5': 'dd0203a487eb3a15aefdd9ce5132e0c9',
        'info_dict': {
            'id': '1038584',
            'display_id': 'alpimaja',
            'title': 'Alpimaja',
            'description': 'md5:033da58263dc0bf37f48cdb4355d97b6',
            'series_type': 5,
        },
        'playlist_count': 5,
        'params': {
            'format': 'bestvideo',
            'noplaylist': False,
        },
    }, {
        # 5 An episode
        'url': 'https://jupiterpluss.err.ee/1608841228/kofe',
        'md5': 'b81565b54b9536d426c66eae92bb4b03',
        'info_dict': {
            'id': '1608841228',
            'ext': 'mp4',
            'drm': False,
            'season': '202301',
            'content_type': 'episode',
            'upload_date': '20230105',
            'description': 'md5:b4fca3536262bbe717bf0956a7b66825',
            'series_type': 1,
            'geoblocked': False,
            'series': 'Кофе+',
            'display_id': 'kofe',
            'media_type': 'video',
            'episode': 'Kohv+*',
            'title': 'Кофе - 202301 - Kohv',
            'thumbnail': 'https://s.err.ee/photo/crop/2023/01/20/1755467he7d9t8.jpg',
            'timestamp': 1672936800,
            'episode_id': '20230105',
            'license': 'https://info.err.ee/982667/kasutustingimused-ja-kommenteerimine',
        },
        'params': {
            'format': 'bestvideo',
            'noplaylist': True,
            'skip_download': 'm3u8',  # Otherwise fails as fragment too short
        },
    }, {
        # 6 An episode
        'url': 'https://jupiterpluss.err.ee/1608835006/orbita',
        'md5': '26c09d50117c923b63f8484ce840aba9',
        'info_dict': {
            'id': '1608835006',
            'ext': 'mp4',
            'geoblocked': False,
            'content_type': 'episode',
            'upload_date': '20221229',
            'thumbnail': 'https://s.err.ee/photo/crop/2023/01/14/1748770hab6dt8.png',
            'display_id': 'orbita',
            'episode': 'Orbiit*',
            'episode_id': '20221229',
            'title': 'Орбита - 202212 - Orbiit',
            'season': '202212',
            'series': 'Орбита',
            'drm': False,
            'description': 'md5:89daaaa0c594d29b231638d6c893c7e3',
            'series_type': 1,
            'timestamp': 1672332000,
            'media_type': 'video',
            'license': 'https://info.err.ee/982667/kasutustingimused-ja-kommenteerimine',
        },
        'params': {
            'format': 'bestvideo',
            'noplaylist': True,
            'skip_download': 'm3u8',  # Otherwise fails as fragment too short
        },
    }]


class UglyERRRadioIE(_UglyERRLoginIE):
    IE_DESC = 'vikerraadio.err.ee, klassikaraadio.err.ee, r2.err.ee, r4.err.ee'
    _ERR_API_GET_CONTENT = '%(prefix)s/api/radio/getRadioPageData?contentId=%(id)s'
    _ERR_API_SHOWDATA_KEY = 'pageControlData.mainContent'
    _ERR_CHANNELS = r'vikerraadio|klassikaraadio|r2|r4'
    _ERR_LOGIN_SUPPORTED = False
    _NETRC_MACHINE = None
    _VALID_URL = r'(?P<prefix>(?P<scheme>https?)://(?P<channel>%(channels)s).err.ee)/(?:(?:(?P<id>\d+)(?:/(?P<display_id>[^/#?]+))?)|(arhiiv/?(?P<playlist_id>[^/#?]*)))(?P<leftover>[/?#].+)?\Z' % {
        'channels': _ERR_CHANNELS
    }
    _TESTS = [{
        # 0 vikerraadio.err.ee
        'url': 'https://vikerraadio.err.ee/795251/linnukool-mailopu-helid',
        'md5': 'e46459636cd56e18507faa883970dabf',
        'info_dict': {
            'id': '795251',
            'display_id': 'linnukool-mailopu-helid',
            'ext': 'mp4',
            'title': 'Linnu- ja loomakool - 201506 - Mailõpu helid',
            'episode': 'Mailõpu helid',
            'episode_id': '20150601',
            'series': 'Linnu- ja loomakool',
            'thumbnail':
            'https://s.err.ee/photo/crop/2013/11/14/88329hb0f6t8.jpg',
            'description': 'md5:8b23b696c7cb4b07de566701a87a7851',
            'upload_date': '20150601',
            'timestamp': 1433149200,
            'content_type': 'episode',
            'series_type': 1,
            'release_timestamp': 1433149200,
            'season': '201506',
            'geoblocked': False,
            'media_type': 'audio',
            'release_date': '20150601',
            'license': 'https://info.err.ee/982667/kasutustingimused-ja-kommenteerimine',
            'drm': False,
        },
        'params': {
            'format': 'worstaudio',
            'noplaylist': True,
        },
    }, {
        # 1 klassikaraadio.err.ee
        'url':
        'https://klassikaraadio.err.ee/1608237795/miraaz-carl-friedrich-abel-1723-1787-gambasonaadid',
        'md5': 'd9f43a58c1a16a09e68866289a4ae792',
        'info_dict': {
            'id': '1608237795',
            'display_id': 'miraaz-carl-friedrich-abel-1723-1787-gambasonaadid',
            'ext': 'mp4',
            'title': 'Miraaž - 202106 - Carl Friedrich Abel (1723-1787) - Gambasonaadid',
            'episode': 'Carl Friedrich Abel (1723-1787) - Gambasonaadid',
            'episode_id': '20210609',
            'series': 'Miraaž',
            'thumbnail':
            'https://s.err.ee/photo/crop/2021/06/11/1037268h5e4et8.jpg',
            'description': 'md5:24da2208102bfb8cbdee56317ba0ee5e',
            'upload_date': '20210609',
            'timestamp': 1623243600,
            'content_type': 'episode',
            'series_type': 1,
            'geoblocked': False,
            'release_date': '20210620',
            'release_timestamp': 1624205100,
            'season': '202106',
            'media_type': 'audio',
            'license': 'https://info.err.ee/982667/kasutustingimused-ja-kommenteerimine',
            'drm': False,

        },
        'params': {
            'format': 'worstaudio',
            'noplaylist': True,
        },
    }, {
        # 2 r4.err.ee
        'url': 'https://r4.err.ee/1608218368/razbor-poljotov',
        'md5': 'c7554f8fc4a05997bb50dc038eb68624',
        'info_dict': {
            'id': '1608218368',
            'display_id': 'razbor-poljotov',
            'ext': 'mp4',
            'title': 'Разбор полетов - 202105 - Разбор полётов',
            'episode': 'Разбор полётов',
            'series': 'Разбор полетов',
            'thumbnail':
            'https://s.err.ee/photo/crop/2020/05/17/779446h5ecct8.jpg',
            'description': 'md5:3946e1c4793aa1a2fc867591a097d730',
            'upload_date': '20210531',
            'timestamp': 1622460600,
            'episode_id': '20210531',
            'media_type': 'audio',
            'drm': False,
            'content_type': 'episode',
            'geoblocked': False,
            'release_date': '20210602',
            'series_type': 1,
            'season': '202105',
            'release_timestamp': 1622631900,
            'license': 'https://info.err.ee/982667/kasutustingimused-ja-kommenteerimine',
        },
        'params': {
            'format': 'worstaudio',
            'noplaylist': True,
        },
    }]


class UglyERRArhiivIE(_UglyERRBaseIE):
    IE_DESC = 'arhiiv.err.ee: archived TV and radio shows, movies and documentaries produced in ETV (Estonia)'
    _NETRC_MACHINE = None
    _VALID_URL = r'(?P<prefix>https?://arhiiv\.err\.ee)/(?P<channel>video|audio)/(?:(?:(?:vaata/)?(?P<id>[^/#?]*?))|(?:seeria/(?P<playlist_id>[^/#?]*?)))$'
    _TESTS = [{
        # 0 a video episode
        'url': 'https://arhiiv.err.ee/video/vaata/eesti-aja-lood-okupatsioonid-muusad-soja-varjus',
        'md5': '022a75f157b848de0250fe912b970386',
        'info_dict': {
            'id': 'eesti-aja-lood-okupatsioonid-muusad-soja-varjus',
            'display_id': 'eesti-aja-lood-okupatsioonid-muusad-soja-varjus',
            'ext': 'mp4',
            'title': 'Eesti aja lood. Okupatsioonid - 68 - Muusad sõja varjus',
            'thumbnail':
            'https://arhiiv-images.err.ee/thumbnails/2009/2009-002267-0068_0001_D10_EESTI-AJA-LOOD-OKUPATSIOONID_20240404152529.jpg',
            'description': 'md5:36772936a0982571ce23aa0dad1f6231',
            'upload_date': '20091025',
            'timestamp': 1256428800,
            'series_id': 169,
            'duration': 1642.0,
            'creator': 'md5:060ad59083433a8f9a35e250816c5cfb',
            'series_type': 'monthly',
            'episode_number': 68,
            'media_type': 'video',
            'episode': 'Muusad sõja varjus',
            'series': 'Eesti aja lood. Okupatsioonid',
            'chapters': 'count:35',
            'license': 'https://info.err.ee/982667/kasutustingimused-ja-kommenteerimine',
        },
        'params': {
            'format': 'bestvideo',
            'noplaylist': True,
            'skip_download': 'm3u8',  # Otherwise fails as fragment too short
        },
    }, {
        # 1 a single video
        'url': 'https://arhiiv.err.ee/video/vaata/tallinn-mai-juuni-1976',
        'md5': '95465d45dff2e413a2e19a24eb5c1cc8',
        'info_dict': {
            'id': 'tallinn-mai-juuni-1976',
            'display_id': 'tallinn-mai-juuni-1976',
            'ext': 'mp4',
            'title': 'Tallinn. Mai-juuni 1976',
            'thumbnail':
            'https://arhiiv-images.err.ee/thumbnails/2023/4829h4786_thumb.jpg',
            'upload_date': '19760917',
            'timestamp': 211766400,
            'episode': 'Tallinn. Mai-juuni 1976',
            'media_type': 'video',
            'creator': 'md5:c93c6c13a1b22ed52ea0cf509e74fd4e',
            'duration': 857.0,
            'description': 'md5:b9e4722c4b7d47b0b6de38ef56e1c558',
            'chapters': 'count:12',
            'license': 'https://info.err.ee/982667/kasutustingimused-ja-kommenteerimine',
        },
        'params': {
            'format': 'bestvideo',
            'skip_download': 'm3u8',  # Otherwise fails as fragment too short
        },
    }, {
        # 2 an audio episode
        'url': 'https://arhiiv.err.ee/audio/vaata/linnulaul-linnulaul-34-rukkiraak',
        'md5': 'c156cdaf5883ef198e3152c71e463ffe',
        'info_dict': {
            'id': 'linnulaul-linnulaul-34-rukkiraak',
            'display_id': 'linnulaul-linnulaul-34-rukkiraak',
            'ext': 'mp4',
            'title': 'LINNULAUL 34. Rukkirääk',
            'thumbnail':
            'https://arhiiv-images.err.ee/thumbnails/2022/557h4afd_thumb.jpg',
            'description': 'md5:d41739b0c8e250a3435216afc98c8741',
            'channel': '2002 EESTI RAADIO',
            'timestamp': 1022716800,
            'media_type': 'audio',
            'series': 'Linnulaul',
            'episode': 'LINNULAUL 34. Rukkirääk',
            'series_id': 20876,
            'upload_date': '20020530',
            'duration': 69.0,
            'series_type': 'yearly',
            'license': 'https://info.err.ee/982667/kasutustingimused-ja-kommenteerimine',
        },
        'params': {
            'format': 'worstaudio',
            'noplaylist': True,
        },
    }, {
        # 3 arhiiv.err.ee video playlist
        '_type': 'playlist',
        'url':
        'https://arhiiv.err.ee/video/eesti-nuud-siis-vabariik',
        'info_dict': {
            'id': 'eesti-nuud-siis-vabariik',
            'display_id': 'eesti-nuud-siis-vabariik',
        },
        'playlist_mincount': 39,
        'params': {
            'format': 'bestvideo',
        },
    }, {
        # 4 arhiiv.err.ee video playlist
        # 'skip': 'Spare err.ee',
        '_type': 'playlist',
        'url':
        'https://arhiiv.err.ee/video/seeria/terevisioon',
        'info_dict': {
            'id': 'terevisioon',
            'display_id': 'terevisioon',
        },
        'playlist_mincount': 2247,
        'params': {
            'format': 'bestvideo',
        },
    }, {
        # 5 arhiiv.err.ee audio playlist
        # 'skip': 'Spare err.ee',
        '_type': 'playlist',
        'url':
        'https://arhiiv.err.ee/audio/seeria/paevakaja',
        'info_dict': {
            'id': 'paevakaja',
            'display_id': 'paevakaja',
        },
        'playlist_mincount': 9250,
        'params': {
            'format': 'bestaudio',
        },
    }, {
        # 6 arhiiv.err.ee audio playlist
        '_type': 'playlist',
        'url':
        'https://arhiiv.err.ee/audio/bestikad',
        'info_dict': {
            'id': 'bestikad',
            'display_id': 'bestikad',
        },
        'playlist_mincount': 18,
        'params': {
            'format': 'bestaudio',
        },
    }, {
        # 7 arhiiv.err.ee video playlist
        '_type': 'playlist',
        'url':
        'https://arhiiv.err.ee/video/seeria/liblikavorguga-kamerunis',
        'info_dict': {
            'id': 'liblikavorguga-kamerunis',
            'display_id': 'liblikavorguga-kamerunis',
        },
        'playlist_mincount': 5,
        'params': {
            'format': 'bestvideo',
        },
    }, {
        # 8 arhiiv.err.ee video playlist
        # 'skip': 'Spare err.ee',
        '_type': 'playlist',
        'url':
        'https://arhiiv.err.ee/video/ringvaade-suvel',
        'info_dict': {
            'id': 'ringvaade-suvel',
            'display_id': 'ringvaade-suvel',
        },
        'playlist_mincount': 276,
        'params': {
            'format': 'bestvideo',
        },
    }]

    def _api_get_series(self, url_dict, playlist_id, limit=100, page=1, sort='old'):
        """
        Posted form controls:
            limit = 24|100|500,
            page = 1|2|3|...,
            sort = new|old|abc,
            all = false|true
        """
        data = self._download_json(
            '%(prefix)s/api/v1/series/%(channel)s/%(playlist_id)s' % url_dict, playlist_id,
            data=urlencode_postdata(
                {'limit': limit, 'page': page, 'sort': sort, 'all': 'false'}))['activeList']
        return data

    def _fetch_playlist(self, url_dict, playlist_id):
        info = {}

        limit = 500
        page = 1
        sort = 'old'
        list_data = self._api_get_series(url_dict, playlist_id, page=page, limit=limit, sort=sort)

        if 'seriesId' in list_data:
            info['_type'] = 'playlist'
            info['display_id'] = traverse_obj(list_data, 'url')
            info['id'] = info.get('display_id')
            info['playlist_count'] = traverse_obj(list_data, 'totalCount', {int_or_none})
        else:
            error_msg = 'No playlist id available'
            self.report_warning(error_msg)
            raise ExtractorError(error_msg)

        while True:
            entries = []

            for item in list_data.get('data') or []:
                entry = self._extract_list_entry(item, url_dict)
                entry['series_id'] = info['id']
                self._ERR_URL_SET.add(entry['url'])
                entries.append(entry)
            if 'entries' not in info:
                info['entries'] = []
            info['entries'].extend(entries)
            if page * limit < info['playlist_count']:
                page += 1
                list_data = self._api_get_series(
                    url_dict, playlist_id, page=page, limit=limit, sort=sort)
            else:
                break

        return info

    def _extract_list_entry(self, list_data, url_dict):
        info = dict()
        info['_type'] = 'url'
        info['id'] = list_data.get('url')
        info['media_type'] = list_data.get('type')
        info['timestamp'] = traverse_obj(list_data, ('date', {str_or_none}, {timestamp_from_date}))

        info['url'] = '%(prefix)s/%(channel)s/vaata/%(id)s' % {
            'prefix': url_dict['prefix'],
            'channel': url_dict['channel'],
            'id': info['id']}
        return info

    def _extract_entry(self, page, video_id):
        info = dict()

        info['title'] = traverse_obj(page, ('info', 'title'))
        info['media_type'] = traverse_obj(page, ('info', 'archiveType'))
        info['description'] = traverse_obj(page, ('info', 'synopsis'))
        if (dsc1 := traverse_obj(page, ('info', 'description'))
                and (dsc0 := info.get('description'))):
            info['description'] = dsc0 + '\n\n' + dsc1

        info['webpage_url'] = traverse_obj(page, ('info', 'fullUrl'))
        info['timestamp'] = traverse_obj(page, ('info', 'date', {unified_timestamp}))
        info['series'] = traverse_obj(page, ('seriesList', 'seriesTitle'))
        info['series_type'] = traverse_obj(page, ('seriesList', 'seriesType'))
        info['series_id'] = traverse_obj(page, ('info', 'seriesId'))

        info['episode'] = traverse_obj(page, ('info', 'episode'))
        if ep := info.get('episode'):
            if ep.isdigit():
                info['episode_number'] = int(ep)

        info['thumbnail'] = traverse_obj(page, ('info', 'videoPhotoUrl'))

        if traverse_obj(page, ('metadata', 'data')):
            def traverse_metadata(data):
                prefix = data['label'] + '.' if isinstance(data, dict) and 'label' in data else ''

                if isinstance(data, dict) and 'data' in data:
                    for x in traverse_metadata(data['data']):
                        x['label'] = prefix + x['label']
                        yield x
                elif isinstance(data, list):
                    for x in data:
                        for y in traverse_metadata(x):
                            yield y
                if isinstance(data, dict):
                    if 'label' in data and 'value' in data:
                        yield {'label': data['label'], 'value': data['value']}

            for prop in traverse_metadata(page.get('metadata')):
                label = prop['label'].strip()
                value = prop['value'].strip()
                if not value:
                    continue
                if label.endswith('Sarja pealkiri'):
                    info['series'] = value
                elif label.endswith('Pealkiri'):
                    info['episode'] = value
                elif label.endswith('Osa nr.'):
                    info['episode_number'] = int(value)
                elif label.endswith('Kestus'):
                    info['duration'] = parse_duration(value)
                elif label.endswith('Fonogrammi tootja'):
                    info['channel'] = value
                elif label.endswith('Märksõnad'):
                    # tags can be:
                    #   * simple like 'huumor';
                    #   * complex like 'intervjuud/vestlusringid';
                    #   * weird like 'meedia (raadio, tv, press)'.
                    # See e.g. 'https://arhiiv.err.ee/vaata/homme-on-esimene-aprill'
                    tags = re.sub(r'[(),/]', ' ', clean_html(value)).split()
                    if tags:
                        info['tags'] = sorted(
                            map(lambda s: s.strip().lower(), tags))
                elif label.startswith('Info.Tehnilised andmed.Esinejad'):
                    if 'creator' not in info:
                        info['creator'] = list()
                    info['creator'].extend(
                        map(lambda a: f'{a} (Esineja)', re.split(r'\s*,\s*', value)))
                elif label.startswith('Info.Tegijad'):
                    op = label.split(sep='.')[-1]
                    if 'creator' not in info:
                        info['creator'] = list()
                    info['creator'].append(f'{value} ({op})')

            if 'creator' in info:
                info['creator'] = ', '.join(info['creator'])

        # Demangle title
        if (info.get('series') and info.get('episode_number')
                and info.get('episode') and not info.get('episode').isdigit()):
            info['title'] = f'{info["series"]} - {info["episode_number"]} - {info["episode"]}'

        info['title'] = sanitize_title(info['title'])

        chapters = [{
            'start_time': floor(chapter['beginTime'] / 1000),
            'end_time': ceil(chapter['endTime'] / 1000),
            'title': chapter['content'].strip(),
        } for chapter in traverse_obj(page, ('description', 'data', ...))]
        if chapters:
            info['chapters'] = chapters

        formats, subtitles = [], {}
        if url := traverse_obj(page, ('media', 'src', 'hls', {url_or_none})):
            fmts, subs = self._sanitize_formats_and_subtitles(
                *self._extract_m3u8_formats_and_subtitles(
                    url, video_id, 'mp4', m3u8_id='hls', fatal=False))
            formats.extend(fmts)
            self._merge_subtitles(subs, target=subtitles)

        if url := traverse_obj(page, ('media', 'src', 'dash', {url_or_none})):
            fmts, subs = self._sanitize_formats_and_subtitles(
                *self._extract_mpd_formats_and_subtitles(
                    url, video_id, mpd_id='dash', fatal=False))
            formats.extend(fmts)
            self._merge_subtitles(subs, target=subtitles)

        info['formats'] = formats
        info['subtitles'] = subtitles

        info['license'] = self._ERR_TERMS_AND_CONDITIONS_URL

        return info

    def _real_extract(self, url):
        self._reset_format_counters()
        info = dict()
        url_dict = self._extract_ids(url)
        info['webpage_url'] = url

        if url_dict.get('playlist_id'):
            playlist_id = url_dict['playlist_id']
            info.update(self._fetch_playlist(url_dict, playlist_id))

        elif url_dict.get('id'):
            video_id = info['id'] = url_dict['id']
            info['display_id'] = url_dict['id']

            page = self._download_json(
                '%(prefix)s/api/v1/content/%(channel)s/%(id)s' % url_dict, video_id)
            if traverse_obj(page, ('status', 'error')):
                error_msg = ', '.join(traverse_obj(page, ('status', 'error')))
                self.report_warning(error_msg)
                raise ExtractorError(error_msg)

            playlist_id = traverse_obj(page, ('seriesList', 'seriesUrl'))
            force_playlist = True if self._configuration_arg(
                'yes_playlist', ie_key=self._ERR_EXTRACTOR_ARG_PREFIX) else False
            if playlist_id and (
                    playlist_id == video_id or force_playlist) and url not in self._ERR_URL_SET:
                # It's a playlist again.
                url_dict['playlist_id'] = playlist_id
                info.update(self._fetch_playlist(url_dict, playlist_id))
            else:
                # It's an episode
                info.update(self._extract_entry(page, video_id))
        else:
            error_msg = 'No id available'
            self.report_warning(error_msg)
            raise ExtractorError(error_msg)

        return info
