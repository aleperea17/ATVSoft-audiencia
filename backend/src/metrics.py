def pct_calificado(calificados: int, total: int) -> float:
    if total <= 0:
        return 0.0
    return round((calificados * 100.0) / total, 1)
