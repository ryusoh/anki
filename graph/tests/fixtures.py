"""
Test fixtures for graph module tests.

Provides sample Anki notes across multiple decks for testing.
"""

# Sample notes from "English Vocabulary" deck
ENGLISH_NOTES = [
    {
        'guid': 'eng001',
        'mid': 123456,
        'deck': 'English Vocabulary',
        'deck_id': 1001,
        'flds': 'flamboyant::Marked by fancy or extravagant display::etymology: Latin',
        'tags': 'vocab english adjective',
        'mod': 1664855079,
        'csum': 111111,
    },
    {
        'guid': 'eng002',
        'mid': 123456,
        'deck': 'English Vocabulary',
        'deck_id': 1001,
        'flds': 'baroque::A style of architecture and music::flamboyant and ornate',
        'tags': 'vocab english art',
        'mod': 1664855080,
        'csum': 222222,
    },
    {
        'guid': 'eng003',
        'mid': 123456,
        'deck': 'English Vocabulary',
        'deck_id': 1001,
        'flds': 'rococo::An 18th-century artistic style::ornate and delicate',
        'tags': 'vocab english art',
        'mod': 1664855081,
        'csum': 333333,
    },
    {
        'guid': 'eng004',
        'mid': 123456,
        'deck': 'English Vocabulary',
        'deck_id': 1001,
        'flds': 'ornate::Elaborately decorated::highly decorated',
        'tags': 'vocab english adjective',
        'mod': 1664855082,
        'csum': 444444,
    },
    {
        'guid': 'eng005',
        'mid': 123456,
        'deck': 'English Vocabulary',
        'deck_id': 1001,
        'flds': 'style::A manner of doing something::fashion or design',
        'tags': 'vocab english noun',
        'mod': 1664855083,
        'csum': 555555,
    },
]

# Sample notes from "Calculus" deck
CALCULUS_NOTES = [
    {
        'guid': 'calc001',
        'mid': 789012,
        'deck': 'Calculus',
        'deck_id': 2001,
        'flds': 'derivative::Rate of change of a function::denoted as f\'(x) or df/dx',
        'tags': 'math calculus concept',
        'mod': 1664855090,
        'csum': 666666,
    },
    {
        'guid': 'calc002',
        'mid': 789012,
        'deck': 'Calculus',
        'deck_id': 2001,
        'flds': 'integral::Antiderivative of a function::inverse of derivative',
        'tags': 'math calculus concept',
        'mod': 1664855091,
        'csum': 777777,
    },
    {
        'guid': 'calc003',
        'mid': 789012,
        'deck': 'Calculus',
        'deck_id': 2001,
        'flds': 'limit::Value that a function approaches::fundamental to calculus',
        'tags': 'math calculus concept',
        'mod': 1664855092,
        'csum': 888888,
    },
]

# Sample notes from "Biology" deck
BIOLOGY_NOTES = [
    {
        'guid': 'bio001',
        'mid': 345678,
        'deck': 'Biology 101',
        'deck_id': 3001,
        'flds': 'mitochondria::Powerhouse of the cell::produces ATP',
        'tags': 'biology cell organelle',
        'mod': 1664855100,
        'csum': 999999,
    },
    {
        'guid': 'bio002',
        'mid': 345678,
        'deck': 'Biology 101',
        'deck_id': 3001,
        'flds': 'ATP::Energy currency of the cell::produced by mitochondria',
        'tags': 'biology cell energy',
        'mod': 1664855101,
        'csum': 101010,
    },
]

# All notes combined
ALL_NOTES = ENGLISH_NOTES + CALCULUS_NOTES + BIOLOGY_NOTES

# Expected references within English deck only
# Whole-front-field matching: card A's front appears in card B's content
ENGLISH_EXPECTED_EDGES = [
    # "flamboyant" (eng001 front) appears in eng002 back
    {'source': 'eng001', 'target': 'eng002', 'type': 'front_in_back'},
    # "style" (eng005 front) appears in eng002 back ("A style of...")
    {'source': 'eng005', 'target': 'eng002', 'type': 'front_in_back'},
    # "ornate" (eng004 front) appears in eng002 back and eng003 back
    {'source': 'eng004', 'target': 'eng002', 'type': 'front_in_back'},
    {'source': 'eng004', 'target': 'eng003', 'type': 'front_in_back'},
    # "style" (eng005 front) appears in eng003 back ("artistic style")
    {'source': 'eng005', 'target': 'eng003', 'type': 'front_in_back'},
]

# Expected references within Calculus deck only
CALCULUS_EXPECTED_EDGES = [
    # "derivative" (calc001 front) appears in calc002 back
    {'source': 'calc001', 'target': 'calc002', 'type': 'front_in_back'},
]

# Expected references within Biology deck only
BIOLOGY_EXPECTED_EDGES = [
    # "mitochondria" (bio001 front) appears in bio002 back
    {'source': 'bio001', 'target': 'bio002', 'type': 'front_in_back'},
    # "atp" (bio002 front) appears in bio001 back
    {'source': 'bio002', 'target': 'bio001', 'type': 'front_in_back'},
]
