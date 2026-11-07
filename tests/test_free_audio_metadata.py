import unittest

from magicdrama.audiofirst.free_audio import metadata_candidate


class CommonsMetadataTests(unittest.TestCase):
    def page(self):
        return {'pageid':123,'title':'File:Cafe ambiance.ogg','imageinfo':[{
            'url':'https://upload.wikimedia.org/wikipedia/commons/example.ogg',
            'descriptionurl':'https://commons.wikimedia.org/wiki/File:Cafe_ambiance.ogg',
            'mime':'application/ogg','size':100,
            'extmetadata':{k:{'value':v} for k,v in {
                'LicenseUrl':'http://creativecommons.org/publicdomain/zero/1.0/deed.en',
                'LicenseShortName':'CC0','Artist':'Example creator'}.items()}}]}

    def test_commons_ogg_and_deed_url_are_candidates_not_decoded_acceptance(self):
        candidate=metadata_candidate(self.page())
        self.assertEqual(candidate['license'],'CC0-1.0')
        self.assertEqual(candidate['license_url'],'https://creativecommons.org/publicdomain/zero/1.0/')
        self.assertEqual(candidate['mime'],'application/ogg')

    def test_deed_normalization_does_not_allow_other_licenses_or_hosts(self):
        for url in ('https://creativecommons.org/licenses/by-sa/4.0/deed.en',
                    'https://example.test/publicdomain/zero/1.0/deed.en'):
            page=self.page();page['imageinfo'][0]['extmetadata']['LicenseUrl']['value']=url
            self.assertIsNone(metadata_candidate(page))

    def test_non_audio_mime_and_explicit_restrictions_still_reject(self):
        page=self.page();page['imageinfo'][0]['mime']='video/ogg'
        self.assertIsNone(metadata_candidate(page))
        page=self.page();page['imageinfo'][0]['extmetadata']['Restrictions']={'value':'permission required'}
        self.assertIsNone(metadata_candidate(page))


if __name__=='__main__':unittest.main()
