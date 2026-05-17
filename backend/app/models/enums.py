import enum


class StageType(str, enum.Enum):
    START = "start"
    NORMAL = "normal"
    FINAL = "final"


class TicketPriority(str, enum.Enum):
    P1 = "p1"
    P2 = "p2"
    P3 = "p3"
    P4 = "p4"
    P5 = "p5"


class TicketLinkType(str, enum.Enum):
    BLOCKS = "blocks"
    IS_BLOCKED_BY = "is_blocked_by"
    RELATES_TO = "relates_to"
    DUPLICATES = "duplicates"
    IS_DUPLICATED_BY = "is_duplicated_by"


class SeniorityLevel(str, enum.Enum):
    JUNIOR = "junior"
    MID = "mid"
    SENIOR = "senior"
    LEAD = "lead"


class RoleScope(str, enum.Enum):
    ORG = "org"
    PROJECT = "project"
    BOTH = "both"
