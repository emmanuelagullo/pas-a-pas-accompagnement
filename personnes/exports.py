"""Cellules textuelles des exports métier, sans interprétation en formules."""
def cellule_csv(valeur):
    valeur = '' if valeur is None else str(valeur)
    return "'" + valeur if valeur.lstrip().startswith(('=', '+', '-', '@', '\t', '\r', '\n')) else valeur
