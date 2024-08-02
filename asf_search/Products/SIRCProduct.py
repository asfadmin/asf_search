from typing import Dict
from asf_search import ASFProduct, ASFSession


class SIRCProduct(ASFProduct):
    """
    Dataset Documentation Page: https://eospso.nasa.gov/missions/spaceborne-imaging-radar-c
    """

    _base_properties = {
<<<<<<< HEAD
        "groupID": {
            "path": ["AdditionalAttributes", ("Name", "GROUP_ID"), "Values", 0]
        },
        "md5sum": {"path": ["AdditionalAttributes", ("Name", "MD5SUM"), "Values", 0]},
        "pgeVersion": {"path": ["PGEVersionClass", "PGEVersion"]},
        "beamModeType": {
            "path": ["AdditionalAttributes", ("Name", "BEAM_MODE_TYPE"), "Values", 0]
        },
=======
        **ASFProduct._base_properties,
        'groupID': {'path': [ 'AdditionalAttributes', ('Name', 'GROUP_ID'), 'Values', 0]},
        'md5sum': {'path': [ 'AdditionalAttributes', ('Name', 'MD5SUM'), 'Values', 0]},
        'pgeVersion': {'path': ['PGEVersionClass', 'PGEVersion'] },
        'beamModeType': {'path': ['AdditionalAttributes', ('Name', 'BEAM_MODE_TYPE'), 'Values', 0]},
>>>>>>> master
    }

    def __init__(self, args: Dict = {}, session: ASFSession = ASFSession()):
        super().__init__(args, session)
<<<<<<< HEAD

    @staticmethod
    def get_property_paths() -> Dict:
        return {**ASFProduct.get_property_paths(), **SIRCProduct._base_properties}
=======
>>>>>>> master
