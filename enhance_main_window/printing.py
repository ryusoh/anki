def conditionString(cond, string=None, parenthesis=False):
    """If the condition cond holds: return the string if it's not None, else the cond.
    If its not empty, add parenthesis around them
    """
    if not cond:
        return ""
    if string is not None:
        ret = str(string)
    else:
        ret = str(cond)
    if parenthesis:
        ret = f"(+{ret})"
    return ret


def nowLater(first, second=None):
    """A representation for the pair"""
    first = conditionString(first)
    second = conditionString(second, parenthesis=True)
    return first + second
