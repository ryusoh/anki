
MESSAGE_TEMPLATE = "Studied {card_text} cards in {time_text} today. ({avg_text}s/card)"

def check_custom_text(custom_text):
    # if ("{card_text}" not in custom_text
    #     or "{time_text}" not in custom_text
    #     or "{avg_text}" not in custom_text):
    #     return MESSAGE_TEMPLATE
    return custom_text