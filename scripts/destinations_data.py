#!/usr/bin/env python3
"""The destination footprint: twenty-two countries, confirmed by the owner 2026-08-29.

Single source of truth for the country/region list shared by the destinations
index and the country pages. `spine` records which page shape the country takes
(see the spec): 'rite' where there is a church tradition to write about,
'no-building' for beach and resort ceremonies, 'both' where the country
genuinely carries both and the page handles the split internally.
"""

GROUPS = [
    ('Europe and the Mediterranean', [
        ('italy', 'Italy', ['Tuscany', 'the Amalfi Coast', 'Lake Como', 'Puglia', 'Florence'], 'rite'),
        ('france', 'France', ['the Dordogne', 'the Loire Valley', 'the French Riviera', 'Provence'], 'rite'),
        ('spain', 'Spain', ['Ibiza', 'Mallorca', 'Marbella', 'Tenerife'], 'both'),
        ('portugal', 'Portugal', ['the Algarve', 'Sintra', 'Porto', 'Lisbon'], 'rite'),
        ('greece', 'Greece', ['Santorini', 'Rhodes', 'Crete', 'Zakynthos', 'Mykonos'], 'both'),
        ('cyprus', 'Cyprus', ['Paphos', 'Ayia Napa', 'Protaras'], 'both'),
        ('malta', 'Malta', ['Valletta', 'Mdina', 'Gozo'], 'rite'),
        ('croatia', 'Croatia', ['Dubrovnik', 'Hvar', 'Split', 'Istria'], 'rite'),
        ('gibraltar', 'Gibraltar', ['the Rock', 'the Botanic Gardens'], 'rite'),
        # Ireland and Scotland regions set provisionally 2026-08-29 pending owner
        # confirmation — see MANUAL-ACTIONS-REQUIRED.md §14 item 1.
        ('ireland', 'Ireland', ['Dublin', 'County Wicklow', 'the south west', 'the west'], 'rite'),
        ('scotland', 'Scotland', ['Edinburgh', 'the Highlands', 'Loch Lomond', 'Perthshire'], 'rite'),
    ]),
    ('The Americas and the Caribbean', [
        ('united-states', 'United States', ['New York City', 'Florida', 'Las Vegas'], 'both'),
        ('mexico', 'Mexico', ['the Riviera Maya', 'Tulum', 'Cancún'], 'both'),
        ('barbados', 'Barbados', ['St James', 'Christ Church', 'St Peter'], 'rite'),
        ('st-lucia', 'St Lucia', ['Soufrière', 'Rodney Bay'], 'rite'),
        ('jamaica', 'Jamaica', ['Montego Bay', 'Negril', 'Ocho Rios'], 'rite'),
    ]),
    ('The Indian Ocean, Asia and Africa', [
        ('mauritius', 'Mauritius', ['Belle Mare', 'Le Morne', 'Grand Baie'], 'no-building'),
        ('maldives', 'Maldives', ['North Malé Atoll', 'South Ari Atoll'], 'no-building'),
        ('seychelles', 'Seychelles', ['Mahé', 'Praslin', 'La Digue'], 'no-building'),
        ('thailand', 'Thailand', ['Phuket', 'Koh Samui'], 'no-building'),
        ('indonesia', 'Bali', ['Uluwatu', 'Ubud', 'Seminyak'], 'no-building'),
        ('south-africa', 'South Africa', ['Cape Town', 'Franschhoek', 'the Kruger area'], 'both'),
    ]),
]

# Schema.org country names, where they differ from the display name.
SCHEMA_NAME = {'Bali': 'Indonesia', 'St Lucia': 'Saint Lucia', 'Scotland': 'United Kingdom'}

ALL = [c for _, cs in GROUPS for c in cs]


def by_slug(slug):
    for c in ALL:
        if c[0] == slug:
            return c
    raise KeyError(slug)


def regions_phrase(regions):
    """'Tuscany, the Amalfi Coast, Lake Como, Puglia and Florence'"""
    if not regions:
        return ''
    if len(regions) == 1:
        return regions[0]
    return ', '.join(regions[:-1]) + ' and ' + regions[-1]
