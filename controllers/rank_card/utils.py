import asyncpg
import imagetext_py as ipy
from PIL import Image, ImageDraw, ImageFont
from PIL.ImageFont import FreeTypeFont

from .models import RankDetail

_COMPLETION_BAR_TOTAL_LENGTH = 325
_COMPLETION_BAR_X_POSITION = 109
_COMPLETION_BAR_HEIGHT = 32

_MEDAL_BOX_WIDTH = 33

_LABEL_X_POSITION = 437
_LABEL_WIDTH = 65

_MISC_DATA_Y_POSITION = 306
_MISC_DATA_HEIGHT = 81
_MISC_DATA_WIDTH = 91

_MAP_COUNT_X_POSITION = 672
_PLAYTEST_COUNT_X_POSITION = 771
_WORLD_RECORDS_COUNT_X_POSITION = 869

_NAME_X_POSITION = _MAP_COUNT_X_POSITION
_NAME_Y_POSITION = 403
_NAME_WIDTH = 289
_NAME_HEIGHT = 41


_COMPLETION_BAR_Y_POSITIONS = {
    "Beginner": 61,
    "Easy": 119,
    "Medium": 176,
    "Hard": 234,
    "Very Hard": 292,
    "Extreme": 349,
    "Hell": 407,
}

_COMPLETION_BAR_COLORS = {
    "Beginner": "#00ff1a",
    "Easy": "#cdff3a",
    "Medium": "#fbdf00",
    "Hard": "#ff9700",
    "Very Hard": "#ff4500",
    "Extreme": "#ff0000",
    "Hell": "#9a0000",
}

_MEDAL_X_POSITIONS = {
    "gold": 518,
    "silver": 564,
    "bronze": 611,
}

RANKS = (
    "Ninja",
    "Jumper",
    "Skilled",
    "Pro",
    "Master",
    "Grandmaster",
    "God",
)

ipy.FontDB.LoadFromDir("./assets")
font = ipy.FontDB.Query("notosans china1 china2 japanese korean")


class RankCardBuilder:
    def __init__(self, data) -> None:
        self._data = data

        self._rank_card = Image.open(f"assets/layer0/{self._data['bg']}.png").convert("RGBA")
        self._draw = ImageDraw.Draw(self._rank_card)
        self._small_font = ImageFont.truetype("assets/Calibri.ttf", 20)
        self._large_font = ImageFont.truetype("assets/Calibri.ttf", 30)
        self._name_font = ImageFont.truetype("assets/Calibri.ttf", 30)

    def create_card(self) -> Image:
        """Create card."""
        self._add_layer1()
        for category in _COMPLETION_BAR_COLORS:
            self._create_completion_bar(
                category,
                self._data[category]["completed"] / self._data[category]["total"],
            )
        self._add_layer2()
        for category in _COMPLETION_BAR_COLORS:
            self._add_completion_labels(
                category,
                self._data[category]["completed"],
                self._data[category]["total"],
            )
        self._add_rank_emblem()
        self._draw_maps_count()
        self._draw_playtests_count()
        self._draw_world_records_count()
        self._draw_name()
        return self._rank_card

    def _add_layer1(self) -> None:
        self._paste_transparent_image("assets/layer1.png")

    def _add_layer2(self) -> None:
        self._paste_transparent_image("assets/layer2.png")

    def _add_completion_labels(self, category: str, completed: int, total: int) -> None:
        y_position = _COMPLETION_BAR_Y_POSITIONS[category]
        text = f"{completed}/{total}"
        position = self._get_center_x_position(_LABEL_WIDTH, _LABEL_X_POSITION, text, self._small_font)
        self._draw.text(
            (position, y_position + _COMPLETION_BAR_HEIGHT // 4),
            text,
            font=self._small_font,
            fill=(255, 255, 255),
        )

    def _create_completion_bar(self, category: str, ratio: float) -> None:
        y_position = _COMPLETION_BAR_Y_POSITIONS[category]
        bar_length = _COMPLETION_BAR_TOTAL_LENGTH * ratio

        for medal in ["gold", "silver", "bronze"]:
            self._add_completion_medals(category, medal)

        if ratio == 0:
            return

        self._draw.rectangle(
            (
                (_COMPLETION_BAR_X_POSITION, y_position),
                (
                    _COMPLETION_BAR_X_POSITION + bar_length,
                    y_position + _COMPLETION_BAR_HEIGHT,
                ),
            ),
            fill=_COMPLETION_BAR_COLORS[category],
        )

    def _add_completion_medals(self, category: str, medal: str) -> None:
        y_position = _COMPLETION_BAR_Y_POSITIONS[category]
        text = f"{self._data[category][medal]}"
        position = self._get_center_x_position(_MEDAL_BOX_WIDTH, _MEDAL_X_POSITIONS[medal], text, self._small_font)

        self._draw.text(
            (position, y_position + _COMPLETION_BAR_HEIGHT // 4),
            text,
            font=self._small_font,
            fill=(255, 255, 255),
        )

    def _add_rank_emblem(self) -> None:
        self._paste_transparent_image(f"assets/layer3/{self._data['rank'].lower()}.png")

    def _paste_transparent_image(self, path: str) -> None:
        layer = Image.open(path).convert("RGBA")
        self._rank_card.paste(layer, None, layer)

    def _draw_maps_count(self) -> None:
        text = f"{self._data['maps']}"
        position = self._get_center_x_position(_MISC_DATA_WIDTH, _MAP_COUNT_X_POSITION, text, self._large_font)
        self._draw.text(
            (position, _MISC_DATA_Y_POSITION + (_MISC_DATA_HEIGHT // 4)),
            text,
            font=self._large_font,
            fill=(255, 255, 255),
        )

    def _draw_playtests_count(self) -> None:
        text = f"{self._data['playtests']}"
        position = self._get_center_x_position(_MISC_DATA_WIDTH, _PLAYTEST_COUNT_X_POSITION, text, self._large_font)
        self._draw.text(
            (position, _MISC_DATA_Y_POSITION + (_MISC_DATA_HEIGHT // 4)),
            text,
            font=self._large_font,
            fill=(255, 255, 255),
        )

    def _draw_world_records_count(self) -> None:
        text = f"{self._data['world_records']}"
        position = self._get_center_x_position(
            _MISC_DATA_WIDTH, _WORLD_RECORDS_COUNT_X_POSITION, text, self._large_font
        )
        self._draw.text(
            (position, _MISC_DATA_Y_POSITION + (_MISC_DATA_HEIGHT // 4)),
            text,
            font=self._large_font,
            fill=(255, 255, 255),
        )

    def _draw_name(self) -> None:
        with ipy.Writer(self._rank_card) as w:
            text = f"{self._data['name']}"
            position = self._get_center_x_position(_NAME_WIDTH, _NAME_X_POSITION, text, self._large_font)
            # noinspection PyTypeChecker
            w.draw_text_wrapped(
                text=text,
                x=position,
                y=_NAME_Y_POSITION + (_NAME_HEIGHT // 4) - 8,
                ax=0,
                ay=0,
                width=500,
                size=30,
                font=font,
                fill=ipy.Paint.Color((255, 255, 255, 255)),
                stroke_color=ipy.Paint.Rainbow((0.0, 0.0), (256.0, 256.0)),
                draw_emojis=True,
            )

    def _get_center_x_position(self, width: int, initial_pos: int, text: str, _font: FreeTypeFont) -> float:
        return (width // 2 - self._draw.textlength(text, _font) // 2) + initial_pos


async def fetch_user_rank_data(
    db: asyncpg.Connection, user_id: int, include_archived: bool, include_beginner: bool
) -> list[RankDetail]:
    """Fetch user rank data."""
    query = """
        WITH unioned_records AS (
            (
                SELECT DISTINCT ON (map_code, user_id)
                    map_code,
                    user_id,
                    record,
                    screenshot,
                    video,
                    verified,
                    message_id,
                    channel_id,
                    completion,
                    NULL AS medal
                FROM records
                ORDER BY map_code, user_id, inserted_at DESC
            )
            UNION ALL
            (
                SELECT DISTINCT ON (map_code, user_id)
                    map_code,
                    user_id,
                    record,
                    screenshot,
                    video,
                    TRUE AS verified,
                    message_id,
                    channel_id,
                    FALSE AS completion,
                    medal
                FROM legacy_records
                ORDER BY map_code, user_id, inserted_at DESC
            )
        ),
        ranges AS (
            SELECT range, name FROM
            (
                VALUES
                    ('[0.0,0.59)'::numrange, 'Beginner', TRUE),
                    ('[0.59,2.35)'::numrange, 'Easy', TRUE),
                    ('[0.0,2.35)'::numrange, 'Easy', FALSE),
                    ('[2.35,4.12)'::numrange, 'Medium', NULL),
                    ('[4.12,5.88)'::numrange, 'Hard', NULL),
                    ('[5.88,7.65)'::numrange, 'Very Hard', NULL),
                    ('[7.65,9.41)'::numrange, 'Extreme', NULL),
                    ('[9.41,10.0]'::numrange, 'Hell', NULL)
            ) AS ranges("range", "name", "includes_beginner")
            WHERE includes_beginner = $3 OR includes_beginner IS NULL
            --($3 IS TRUE OR (includes_beginner = TRUE AND includes_beginner IS NULL))
            -- includes_beginner = $3 OR includes_beginner IS NULL
        ),
        thresholds AS (
            -- Mapping difficulty names to thresholds using VALUES
            SELECT * FROM (
                VALUES
                    ('Easy', 10),
                    ('Medium', 10),
                    ('Hard', 10),
                    ('Very Hard', 10),
                    ('Extreme', 7),
                    ('Hell', 3)
            ) AS t(name, threshold)
        ),
        map_data AS (
            SELECT DISTINCT ON (m.map_code, r.user_id)
                AVG(mr.difficulty) AS difficulty,
                r.verified = TRUE AND r.video IS NOT NULL AND(
                    record <= gold OR medal LIKE 'Gold'
                    ) AS gold,
                r.verified = TRUE AND r.video IS NOT NULL AND(
                    record <= silver AND record > gold OR medal LIKE 'Silver'
                    ) AS silver,
                r.verified = TRUE AND r.video IS NOT NULL AND(
                    record <= bronze AND record > silver OR medal LIKE 'Bronze'
                ) AS bronze
            FROM unioned_records r
            LEFT JOIN maps m ON r.map_code = m.map_code
            LEFT JOIN map_ratings mr ON m.map_code = mr.map_code
            LEFT JOIN map_medals mm ON r.map_code = mm.map_code
            WHERE r.user_id = $1
              AND m.official = TRUE
              AND ($2 IS TRUE OR m.archived = FALSE)
            GROUP BY m.map_code, record, gold, silver, bronze, r.verified, medal, r.user_id, r.video
        ), counts_data AS (
        SELECT
            r.name AS difficulty,
            count(r.name) AS completions,
            count(CASE WHEN gold THEN 1 END) AS gold,
            count(CASE WHEN silver THEN 1 END) AS silver,
            count(CASE WHEN bronze THEN 1 END) AS bronze,
            -- Use threshold for rank comparison
            count(r.name) >= t.threshold AS rank_met,
            count(CASE WHEN gold THEN 1 END) >= t.threshold AS gold_rank_met,
            count(CASE WHEN silver THEN 1 END) >= t.threshold AS silver_rank_met,
            count(CASE WHEN bronze THEN 1 END) >= t.threshold AS bronze_rank_met
        FROM ranges r
        INNER JOIN map_data md ON r.range @> md.difficulty
        INNER JOIN thresholds t ON r.name = t.name
        GROUP BY r.name, t.threshold
        )
        SELECT
            name AS difficulty,
            coalesce(completions, 0) AS completions,
            coalesce(gold, 0) AS gold,
            coalesce(silver, 0) AS silver,
            coalesce(bronze, 0) AS bronze,
            coalesce(rank_met, FALSE) AS rank_met,
            coalesce(gold_rank_met, FALSE) AS gold_rank_met,
            coalesce(silver_rank_met, FALSE) AS silver_rank_met,
            coalesce(bronze_rank_met, FALSE) AS bronze_rank_met
        FROM thresholds t
        LEFT JOIN counts_data cd ON t.name = cd.difficulty
        ORDER BY
        CASE name
            WHEN 'Easy' THEN 1
            WHEN 'Medium' THEN 2
            WHEN 'Hard' THEN 3
            WHEN 'Very Hard' THEN 4
            WHEN 'Extreme' THEN 5
            WHEN 'Hell' THEN 6
        END;
    """
    rows = await db.fetch(query, user_id, include_archived, include_beginner)
    return [RankDetail(**row) for row in rows]


def find_highest_rank(data: list[RankDetail]) -> str:
    """Find the highest rank a user has."""
    highest = "Ninja"
    for row in data:
        if row.rank_met:
            highest = DIFF_TO_RANK[row.difficulty]
    return highest


DIFF_TO_RANK = {
    "Beginner": "Ninja",
    "Easy": "Jumper",
    "Medium": "Skilled",
    "Hard": "Pro",
    "Very Hard": "Master",
    "Extreme": "Grandmaster",
    "Hell": "God",
}
