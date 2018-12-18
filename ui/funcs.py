# -*- coding: utf-8 -*-

import string

from helpers import setup_logger

from unidecode import unidecode

logger = setup_logger(__name__, "info")

printable_characters = set(string.printable)
replace_characters = {u"ö":u"o"}


def ellipsize(string, length, ellipsis="..."):
    if len(string) <= length:
        return string
    string = string[:(length-len(ellipsis))]
    return string+ellipsis

def format_for_screen(data, screen_width, break_words=False, linebreak=None):
    strings = data.split('\n')
    #Filter \n's
    data = ' \n '.join(strings) #Making sure linebreaks are surrounded by space characters so that when splitting by space you don't have to scan for linebreaks and just can compare
    words = data.split(' ')
    screen_data = []
    current_data = ""
    for word in words:
        #Five cases:
        if not word: #An empty line encountered somehow
            pass
        elif word == '\n': #A linebreak, need to indent them in a way
            screen_data.append(current_data)
            current_data = ""
            if linebreak is not None:
                screen_data.append(linebreak)
        elif len(word) <= screen_width-len(current_data): #Word fits on current line
            current_data += word+" "
        elif not break_words and len(word) <= screen_width:
            screen_data.append(current_data)
            current_data = word+" "
        else:
            space_on_current_line = screen_width-len(current_data)
            screen_data.append(current_data+word[:space_on_current_line])
            word = word[space_on_current_line:]
            current_line = ""
            while word:
                data = word[:screen_width]
                if len(data) == screen_width: #Full line taken
                    screen_data.append(data)
                else:
                    current_data = data+" "
                word = word[screen_width:]
    screen_data.append(current_data)
    return screen_data

ffs = format_for_screen


def add_character_replacement(character, replacement):
    """
    In case a Unicode character isn't replaced in the way you want it replaced,
    use this function to add a special case.
    """
    logger.info(u"Adding char replacement: {} for {}".format(character, replacement))
    if character in replace_characters:
        logger.warning(u"Character {} already set! (to {} )".format(character, replace_characters[character]))
    replace_characters[character] = replacement

acr = add_character_replacement

def replace_filter_ascii(text, replace_characters=replace_characters):
    """
    Replaces non-ASCII characters with their ASCII equivalents if available,
    removes them otherwise. You can add new replacement characters using the
    ``add_character_replacement`` function. The output of this function is ASCII
    printable characters.

    This function is mostly useful because the default PIL font doesn't have many Unicode
    characters (in fact, it's doubtful it has any). So, if you're going to display
    strings with Unicode characters, you'll want to use this function to filter your
    text before displaying.
    """
    if isinstance(text, str) and not isinstance(text, unicode):
        text = text.decode('utf-8')
    # First, developer-added exceptions
    for character, replacement in replace_characters.items():
        if character in text:
            text = text.replace(character, replacement)
    # Then, use the unidecode() function
    text = unidecode(text)
    # Filter all non-printable characters left
    text = filter(lambda x: x in printable_characters, text)
    return text

rfa = replace_filter_ascii
