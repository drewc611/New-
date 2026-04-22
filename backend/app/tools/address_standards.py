"""Publication 28 addressing standards reference tables.

Tables are taken from:
  * Appendix C1 Street Suffix Abbreviations (https://pe.usps.com/text/pub28/28apc_002.htm)
  * Appendix C2 Secondary Unit Designators (https://pe.usps.com/text/pub28/28apc_003.htm)
  * Appendix B Two Letter State and Possession Abbreviations
  * Appendix I Puerto Rico Addresses

The tables are intentionally exhaustive rather than abbreviated because
they drive address parsing accuracy; shrinking them causes silent
mis-standardization.
"""
from __future__ import annotations

# Two-letter USPS state and possession abbreviations (Appendix B).
STATES: set[str] = {
    "AL", "AK", "AS", "AZ", "AR", "CA", "CO", "CT", "DE", "DC", "FM", "FL",
    "GA", "GU", "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MH",
    "MD", "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ", "NM",
    "NY", "NC", "ND", "MP", "OH", "OK", "OR", "PW", "PA", "PR", "RI", "SC",
    "SD", "TN", "TX", "UT", "VT", "VI", "VA", "WA", "WV", "WI", "WY",
    # Military "states"
    "AA", "AE", "AP",
}

# Directionals. Canonical form is the single or two letter USPS abbreviation.
DIRECTIONALS: dict[str, str] = {
    "N": "N", "NORTH": "N",
    "S": "S", "SOUTH": "S",
    "E": "E", "EAST": "E",
    "W": "W", "WEST": "W",
    "NE": "NE", "NORTHEAST": "NE",
    "NW": "NW", "NORTHWEST": "NW",
    "SE": "SE", "SOUTHEAST": "SE",
    "SW": "SW", "SOUTHWEST": "SW",
}

# Street suffixes. Maps any known variant to the USPS standard abbreviation
# from Appendix C1. The abbreviation key is always the primary standardized
# form per Publication 28.
STREET_SUFFIXES: dict[str, str] = {
    # A
    "ALLEE": "ALY", "ALLEY": "ALY", "ALLY": "ALY", "ALY": "ALY",
    "ANEX": "ANX", "ANNEX": "ANX", "ANNX": "ANX", "ANX": "ANX",
    "ARC": "ARC", "ARCADE": "ARC",
    "AV": "AVE", "AVE": "AVE", "AVEN": "AVE", "AVENU": "AVE", "AVENUE": "AVE",
    "AVN": "AVE", "AVNUE": "AVE",
    # B
    "BAYOO": "BYU", "BAYOU": "BYU", "BYU": "BYU",
    "BCH": "BCH", "BEACH": "BCH",
    "BEND": "BND", "BND": "BND",
    "BLF": "BLF", "BLUF": "BLF", "BLUFF": "BLF",
    "BLUFFS": "BLFS",
    "BOT": "BTM", "BOTTM": "BTM", "BOTTOM": "BTM", "BTM": "BTM",
    "BLVD": "BLVD", "BOUL": "BLVD", "BOULEVARD": "BLVD", "BOULV": "BLVD",
    "BR": "BR", "BRANCH": "BR", "BRNCH": "BR",
    "BRDGE": "BRG", "BRG": "BRG", "BRIDGE": "BRG",
    "BRK": "BRK", "BROOK": "BRK",
    "BROOKS": "BRKS",
    "BURG": "BG", "BG": "BG", "BURGS": "BGS", "BGS": "BGS",
    "BYP": "BYP", "BYPA": "BYP", "BYPAS": "BYP", "BYPASS": "BYP", "BYPS": "BYP",
    # C
    "CAMP": "CP", "CP": "CP", "CMP": "CP",
    "CANYN": "CYN", "CANYON": "CYN", "CNYN": "CYN", "CYN": "CYN",
    "CAPE": "CPE", "CPE": "CPE",
    "CAUSEWAY": "CSWY", "CAUSWAY": "CSWY", "CSWY": "CSWY",
    "CEN": "CTR", "CENT": "CTR", "CENTER": "CTR", "CENTR": "CTR",
    "CENTRE": "CTR", "CNTER": "CTR", "CNTR": "CTR", "CTR": "CTR",
    "CENTERS": "CTRS", "CTRS": "CTRS",
    "CIR": "CIR", "CIRC": "CIR", "CIRCL": "CIR", "CIRCLE": "CIR", "CRCL": "CIR", "CRCLE": "CIR",
    "CIRCLES": "CIRS", "CIRS": "CIRS",
    "CLF": "CLF", "CLIFF": "CLF", "CLIFFS": "CLFS", "CLFS": "CLFS",
    "CLB": "CLB", "CLUB": "CLB",
    "COMMON": "CMN", "CMN": "CMN", "COMMONS": "CMNS", "CMNS": "CMNS",
    "COR": "COR", "CORNER": "COR",
    "CORNERS": "CORS", "CORS": "CORS",
    "COURSE": "CRSE", "CRSE": "CRSE",
    "COURT": "CT", "CT": "CT",
    "COURTS": "CTS", "CTS": "CTS",
    "COVE": "CV", "CV": "CV",
    "COVES": "CVS", "CVS": "CVS",
    "CREEK": "CRK", "CK": "CRK", "CR": "CRK", "CRK": "CRK",
    "CRESCENT": "CRES", "CRES": "CRES", "CRSENT": "CRES", "CRSNT": "CRES",
    "CREST": "CRST", "CRST": "CRST",
    "CROSSING": "XING", "CRSSNG": "XING", "XING": "XING",
    "CROSSROAD": "XRD", "XRD": "XRD",
    "CROSSROADS": "XRDS", "XRDS": "XRDS",
    "CURVE": "CURV", "CURV": "CURV",
    # D
    "DALE": "DL", "DL": "DL",
    "DAM": "DM", "DM": "DM",
    "DIV": "DV", "DIVIDE": "DV", "DV": "DV", "DVD": "DV",
    "DR": "DR", "DRIV": "DR", "DRIVE": "DR", "DRV": "DR",
    "DRIVES": "DRS", "DRS": "DRS",
    # E
    "EST": "EST", "ESTATE": "EST",
    "ESTATES": "ESTS", "ESTS": "ESTS",
    "EXP": "EXPY", "EXPR": "EXPY", "EXPRESS": "EXPY", "EXPRESSWAY": "EXPY",
    "EXPW": "EXPY", "EXPY": "EXPY",
    "EXT": "EXT", "EXTENSION": "EXT", "EXTN": "EXT", "EXTNSN": "EXT",
    "EXTS": "EXTS",
    # F
    "FALL": "FALL",
    "FALLS": "FLS", "FLS": "FLS",
    "FERRY": "FRY", "FRRY": "FRY", "FRY": "FRY",
    "FIELD": "FLD", "FLD": "FLD",
    "FIELDS": "FLDS", "FLDS": "FLDS",
    "FLAT": "FLT", "FLT": "FLT",
    "FLATS": "FLTS", "FLTS": "FLTS",
    "FORD": "FRD", "FRD": "FRD",
    "FORDS": "FRDS",
    "FOREST": "FRST", "FORESTS": "FRST", "FRST": "FRST",
    "FORG": "FRG", "FORGE": "FRG", "FRG": "FRG",
    "FORGES": "FRGS",
    "FORK": "FRK", "FRK": "FRK",
    "FORKS": "FRKS", "FRKS": "FRKS",
    "FORT": "FT", "FRT": "FT", "FT": "FT",
    "FREEWAY": "FWY", "FREEWY": "FWY", "FRWAY": "FWY", "FRWY": "FWY", "FWY": "FWY",
    # G
    "GARDEN": "GDN", "GARDN": "GDN", "GDN": "GDN", "GRDEN": "GDN", "GRDN": "GDN",
    "GARDENS": "GDNS", "GDNS": "GDNS", "GRDNS": "GDNS",
    "GATEWAY": "GTWY", "GATEWY": "GTWY", "GATWAY": "GTWY", "GTWAY": "GTWY", "GTWY": "GTWY",
    "GLEN": "GLN", "GLN": "GLN",
    "GLENS": "GLNS",
    "GREEN": "GRN", "GRN": "GRN",
    "GREENS": "GRNS",
    "GROV": "GRV", "GROVE": "GRV", "GRV": "GRV",
    "GROVES": "GRVS",
    # H
    "HARB": "HBR", "HARBOR": "HBR", "HARBR": "HBR", "HBR": "HBR", "HRBOR": "HBR",
    "HARBORS": "HBRS",
    "HAVEN": "HVN", "HVN": "HVN",
    "HT": "HTS", "HTS": "HTS", "HEIGHTS": "HTS",
    "HIGHWAY": "HWY", "HIGHWY": "HWY", "HIWAY": "HWY", "HIWY": "HWY", "HWAY": "HWY", "HWY": "HWY",
    "HILL": "HL", "HL": "HL",
    "HILLS": "HLS", "HLS": "HLS",
    "HLLW": "HOLW", "HOLLOW": "HOLW", "HOLLOWS": "HOLW", "HOLW": "HOLW", "HOLWS": "HOLW",
    # I
    "INLT": "INLT",
    "IS": "IS", "ISLAND": "IS", "ISLND": "IS",
    "ISLANDS": "ISS", "ISLNDS": "ISS", "ISS": "ISS",
    "ISLE": "ISLE", "ISLES": "ISLE",
    # J
    "JCT": "JCT", "JCTION": "JCT", "JCTN": "JCT", "JUNCTION": "JCT", "JUNCTN": "JCT", "JUNCTON": "JCT",
    "JCTNS": "JCTS", "JCTS": "JCTS", "JUNCTIONS": "JCTS",
    # K
    "KEY": "KY", "KY": "KY",
    "KEYS": "KYS", "KYS": "KYS",
    "KNL": "KNL", "KNOL": "KNL", "KNOLL": "KNL",
    "KNLS": "KNLS", "KNOLLS": "KNLS",
    # L
    "LK": "LK", "LAKE": "LK",
    "LKS": "LKS", "LAKES": "LKS",
    "LAND": "LAND",
    "LANDING": "LNDG", "LNDG": "LNDG", "LNDNG": "LNDG",
    "LANE": "LN", "LN": "LN",
    "LGT": "LGT", "LIGHT": "LGT",
    "LIGHTS": "LGTS",
    "LF": "LF", "LOAF": "LF",
    "LCK": "LCK", "LOCK": "LCK",
    "LCKS": "LCKS", "LOCKS": "LCKS",
    "LDG": "LDG", "LDGE": "LDG", "LODG": "LDG", "LODGE": "LDG",
    "LOOP": "LOOP", "LOOPS": "LOOP",
    # M
    "MALL": "MALL",
    "MNR": "MNR", "MANOR": "MNR",
    "MANORS": "MNRS", "MNRS": "MNRS",
    "MEADOW": "MDW",
    "MDW": "MDWS", "MDWS": "MDWS", "MEADOWS": "MDWS", "MEDOWS": "MDWS",
    "MEWS": "MEWS",
    "MILL": "ML",
    "MILLS": "MLS",
    "MISSN": "MSN", "MSSN": "MSN", "MSN": "MSN", "MISSION": "MSN",
    "MOTORWAY": "MTWY", "MTWY": "MTWY",
    "MNT": "MT", "MT": "MT", "MOUNT": "MT",
    "MNTAIN": "MTN", "MNTN": "MTN", "MOUNTAIN": "MTN", "MOUNTIN": "MTN", "MTIN": "MTN", "MTN": "MTN",
    "MNTNS": "MTNS", "MOUNTAINS": "MTNS",
    # N
    "NCK": "NCK", "NECK": "NCK",
    # O
    "ORCH": "ORCH", "ORCHARD": "ORCH", "ORCHRD": "ORCH",
    "OVAL": "OVAL", "OVL": "OVAL",
    "OVERPASS": "OPAS", "OPAS": "OPAS",
    # P
    "PARK": "PARK", "PRK": "PARK", "PARKS": "PARK",
    "PARKWAY": "PKWY", "PARKWY": "PKWY", "PKWAY": "PKWY", "PKWY": "PKWY", "PKY": "PKWY",
    "PARKWAYS": "PKWY", "PKWYS": "PKWY",
    "PASS": "PASS",
    "PASSAGE": "PSGE", "PSGE": "PSGE",
    "PATH": "PATH", "PATHS": "PATH",
    "PIKE": "PIKE", "PIKES": "PIKE",
    "PINE": "PNE",
    "PINES": "PNES", "PNES": "PNES",
    "PL": "PL", "PLACE": "PL",
    "PLAIN": "PLN", "PLN": "PLN",
    "PLAINS": "PLNS", "PLNS": "PLNS",
    "PLAZA": "PLZ", "PLZ": "PLZ", "PLZA": "PLZ",
    "POINT": "PT", "PT": "PT",
    "POINTS": "PTS", "PTS": "PTS",
    "PORT": "PRT", "PRT": "PRT",
    "PORTS": "PRTS", "PRTS": "PRTS",
    "PR": "PR", "PRAIRIE": "PR", "PRR": "PR",
    # R
    "RAD": "RADL", "RADIAL": "RADL", "RADIEL": "RADL", "RADL": "RADL",
    "RAMP": "RAMP",
    "RANCH": "RNCH", "RANCHES": "RNCH", "RNCH": "RNCH", "RNCHS": "RNCH",
    "RAPID": "RPD", "RPD": "RPD",
    "RAPIDS": "RPDS", "RPDS": "RPDS",
    "RST": "RST", "REST": "RST",
    "RDG": "RDG", "RDGE": "RDG", "RIDGE": "RDG",
    "RDGS": "RDGS", "RIDGES": "RDGS",
    "RIV": "RIV", "RIVER": "RIV", "RVR": "RIV", "RIVR": "RIV",
    "RD": "RD", "ROAD": "RD",
    "RDS": "RDS", "ROADS": "RDS",
    "ROUTE": "RTE", "RTE": "RTE",
    "ROW": "ROW",
    "RUE": "RUE",
    "RUN": "RUN",
    # S
    "SHL": "SHL", "SHOAL": "SHL",
    "SHLS": "SHLS", "SHOALS": "SHLS",
    "SHOAR": "SHR", "SHORE": "SHR", "SHR": "SHR",
    "SHOARS": "SHRS", "SHORES": "SHRS", "SHRS": "SHRS",
    "SKYWAY": "SKWY", "SKWY": "SKWY",
    "SPG": "SPG", "SPNG": "SPG", "SPRING": "SPG", "SPRNG": "SPG",
    "SPGS": "SPGS", "SPNGS": "SPGS", "SPRINGS": "SPGS", "SPRNGS": "SPGS",
    "SPUR": "SPUR", "SPURS": "SPUR",
    "SQ": "SQ", "SQR": "SQ", "SQRE": "SQ", "SQU": "SQ", "SQUARE": "SQ",
    "SQRS": "SQS", "SQS": "SQS", "SQUARES": "SQS",
    "STA": "STA", "STATION": "STA", "STATN": "STA", "STN": "STA",
    "STRA": "STRA", "STRAV": "STRA", "STRAVEN": "STRA", "STRAVENUE": "STRA",
    "STRAVN": "STRA", "STRVN": "STRA", "STRVNUE": "STRA",
    "STREAM": "STRM", "STREME": "STRM", "STRM": "STRM",
    "ST": "ST", "STR": "ST", "STREET": "ST", "STRT": "ST",
    "STREETS": "STS", "STS": "STS",
    "SMT": "SMT", "SUMIT": "SMT", "SUMITT": "SMT", "SUMMIT": "SMT",
    # T
    "TER": "TER", "TERR": "TER", "TERRACE": "TER",
    "THROUGHWAY": "TRWY", "TRWY": "TRWY",
    "TRACE": "TRCE", "TRACES": "TRCE", "TRCE": "TRCE",
    "TRACK": "TRAK", "TRACKS": "TRAK", "TRAK": "TRAK", "TRK": "TRAK", "TRKS": "TRAK",
    "TRAFFICWAY": "TRFY", "TRFY": "TRFY",
    "TRAIL": "TRL", "TRAILS": "TRL", "TRL": "TRL", "TRLS": "TRL",
    "TRAILER": "TRLR", "TRLR": "TRLR", "TRLRS": "TRLR",
    "TUNEL": "TUNL", "TUNL": "TUNL", "TUNLS": "TUNL", "TUNNEL": "TUNL", "TUNNELS": "TUNL", "TUNNL": "TUNL",
    "TRNPK": "TPKE", "TURNPIKE": "TPKE", "TURNPK": "TPKE", "TPKE": "TPKE",
    # U
    "UNDERPASS": "UPAS", "UPAS": "UPAS",
    "UN": "UN", "UNION": "UN",
    "UNIONS": "UNS",
    # V
    "VALLEY": "VLY", "VALLY": "VLY", "VLLY": "VLY", "VLY": "VLY",
    "VALLEYS": "VLYS", "VLYS": "VLYS",
    "VDCT": "VIA", "VIA": "VIA", "VIADCT": "VIA", "VIADUCT": "VIA",
    "VIEW": "VW", "VW": "VW",
    "VIEWS": "VWS", "VWS": "VWS",
    "VILL": "VLG", "VILLAG": "VLG", "VILLAGE": "VLG", "VILLG": "VLG", "VILLIAGE": "VLG", "VLG": "VLG",
    "VILLAGES": "VLGS", "VLGS": "VLGS",
    "VILLE": "VL", "VL": "VL",
    "VIS": "VIS", "VIST": "VIS", "VISTA": "VIS", "VST": "VIS", "VSTA": "VIS",
    # W
    "WALK": "WALK", "WALKS": "WALK",
    "WALL": "WALL",
    "WY": "WAY", "WAY": "WAY",
    "WAYS": "WAYS",
    "WELL": "WL",
    "WELLS": "WLS", "WLS": "WLS",
}

# Secondary unit designators from Appendix C2. Values that take a unit
# number are marked with True; those without are marked False (they are
# printed on the line regardless).
SECONDARY_DESIGNATORS_WITH_NUMBER: dict[str, str] = {
    "APARTMENT": "APT", "APT": "APT",
    "BUILDING": "BLDG", "BLDG": "BLDG",
    "DEPARTMENT": "DEPT", "DEPT": "DEPT",
    "FLOOR": "FL", "FL": "FL", "FLR": "FL",
    "HANGAR": "HNGR", "HNGR": "HNGR",
    "KEY": "KEY",
    "LOT": "LOT",
    "OFFICE": "OFC", "OFC": "OFC",
    "PIER": "PIER",
    "POLL": "POLL",
    "ROOM": "RM", "RM": "RM",
    "SLIP": "SLIP",
    "SPACE": "SPC", "SPC": "SPC",
    "STOP": "STOP",
    "SUITE": "STE", "STE": "STE",
    "TRAILER": "TRLR", "TRLR": "TRLR",
    "UNIT": "UNIT",
}

SECONDARY_DESIGNATORS_WITHOUT_NUMBER: dict[str, str] = {
    "BASEMENT": "BSMT", "BSMT": "BSMT",
    "FRONT": "FRNT", "FRNT": "FRNT",
    "LOBBY": "LBBY", "LBBY": "LBBY",
    "LOWER": "LOWR", "LOWR": "LOWR",
    "OFFICE": "OFC",  # when used without a number
    "PENTHOUSE": "PH", "PH": "PH",
    "REAR": "REAR",
    "SIDE": "SIDE",
    "UPPER": "UPPR", "UPPR": "UPPR",
}

SECONDARY_DESIGNATORS: dict[str, str] = {
    **SECONDARY_DESIGNATORS_WITH_NUMBER,
    **SECONDARY_DESIGNATORS_WITHOUT_NUMBER,
}

# Urbanization is used for Puerto Rico addresses (Appendix I). When the
# city has an urbanization, it precedes the delivery address line.
URBANIZATION_PREFIXES: set[str] = {"URB", "URBANIZACION", "URB."}

# Military addressing (Publication 28 Section 26).
MILITARY_LAST_LINE_CODES: dict[str, str] = {
    "APO": "military",  # Army or Air Force
    "FPO": "military",  # Navy or Marines
    "DPO": "military",  # Diplomatic
}
MILITARY_STATES: set[str] = {"AA", "AE", "AP"}

# PO Box and rural/contract prefixes.
PO_BOX_PATTERNS: tuple[str, ...] = (
    "PO BOX", "P O BOX", "P.O. BOX", "POST OFFICE BOX", "BOX",
)

RURAL_ROUTE_PREFIXES: tuple[str, ...] = ("RR", "RURAL ROUTE", "R.R.", "RTE")
HIGHWAY_CONTRACT_PREFIXES: tuple[str, ...] = ("HC", "HIGHWAY CONTRACT")

GENERAL_DELIVERY: str = "GENERAL DELIVERY"
