from asf_search import ASFSearchOptions, ASFSession
from asf_search.CMR.translate import get as umm_get
from asf_search.Products import S1Product

class OPERAS1Product(S1Product):
    """
    ASF Dataset Documentation Page: https://asf.alaska.edu/datasets/daac/opera/
    """
    _base_properties = {
        'centerLat': {'path': []}, # Opera products lacks these fields
        'centerLon': {'path': []}, 
        'frameNumber': {'path': []}, 
        'operaBurstID': {'path': ['AdditionalAttributes', ('Name', 'OPERA_BURST_ID'), 'Values', 0]},
        'validityStartDate': {'path': ['TemporalExtent', 'SingleDateTime']},
        'bytes': {'path': ['DataGranule', 'ArchiveAndDistributionInformation']},
        'subswath': {'path': ['AdditionalAttributes', ('Name', 'SUBSWATH_NAME'), 'Values', 0]},
    }

    def __init__(self, args: dict = {}, session: ASFSession = ASFSession()):
        super().__init__(args, session)

        self.baseline = None
        
        self.properties['beamMode'] = umm_get(self.umm, 'AdditionalAttributes', ('Name', 'BEAM_MODE'), 'Values', 0)
        accessUrls = [*umm_get(self.umm, 'RelatedUrls', ('Type', [('GET DATA', 'URL')]), 0), *umm_get(self.umm, 'RelatedUrls', ('Type', [('EXTENDED METADATA', 'URL')]), 0)]
        self.properties['additionalUrls'] = sorted([url for url in list(set(accessUrls)) if not url.endswith('.md5') 
                                        and not url.startswith('s3://') 
                                        and not 's3credentials' in url 
                                        and not url.endswith('.png')
                                        and url != self.properties['url']])
        self.properties['polarization'] = umm_get(self.umm, 'AdditionalAttributes', ('Name', 'POLARIZATION'), 'Values')

        self.properties['operaBurstID'] = umm_get(self.umm, 'AdditionalAttributes', ('Name', 'OPERA_BURST_ID'), 'Values', 0)
        self.properties['bytes'] = {entry['Name']: {'bytes': entry['SizeInBytes'], 'format': entry['Format']} for entry in self.properties['bytes']}
        
        center = self.centroid() 
        self.properties['centerLat'] = center.y
        self.properties['centerLon'] = center.x
        
        self.properties.pop('frameNumber')

        if (processingLevel := self.properties['processingLevel']) in ['RTC', 'RTC-STATIC']:
            self.properties['bistaticDelayCorrection'] = umm_get(self.umm, 'AdditionalAttributes', ('Name', 'BISTATIC_DELAY_CORRECTION'), 'Values', 0)
            if processingLevel == 'RTC':
                self.properties['noiseCorrection'] = umm_get(self.umm, 'AdditionalAttributes', ('Name', 'NOISE_CORRECTION'), 'Values', 0)
                self.properties['postProcessingFilter'] = umm_get(self.umm, 'AdditionalAttributes', ('Name', 'POST_PROCESSING_FILTER'), 'Values', 0)
        
        
    def get_stack_opts(self, opts: ASFSearchOptions = ASFSearchOptions()) -> ASFSearchOptions:
        return opts

    @staticmethod
    def get_property_paths() -> dict:
        return {
            **S1Product.get_property_paths(),
            **OPERAS1Product._base_properties
        }
    
    def is_valid_reference(self):
        return False
    
    def get_sort_keys(self):
        keys = super().get_sort_keys()

        if keys[0] is None:
            keys = self.properties.get('validityStartDate'), keys[1]
        
        return keys