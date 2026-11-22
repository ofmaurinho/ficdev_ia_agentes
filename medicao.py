"""Registro sanitizado de medições e cálculo de estatísticas sem inventar valores ausentes."""
import csv
import json
import statistics
import hashlib
from pathlib import Path


def salvar_json(path: Path, data):
    """Salva JSON em UTF-8 formatado; o chamador deve fornecer apenas dados sanitizados."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def salvar_csv(path: Path, rows: list[dict]):
    """Salva linhas de benchmark em CSV usando a união de campos observados."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(dict.fromkeys(k for row in rows for k in row))
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def resumo_metricas(rows: list[dict]) -> dict:
    """Calcula mediana, máximos e cauda apenas a partir de valores numéricos existentes."""
    def nums(key):
        return [float(r[key]) for r in rows if isinstance(r.get(key), (int, float))]
    costs, times, tokens = nums("custo_usd"), nums("duracao_segundos"), nums("tokens_total")
    med = statistics.median(costs) if costs else None
    return {"n_execucoes": len(rows), "n_metricas_custo": len(costs),
            "custo_mediano_usd": med, "custo_maximo_usd": max(costs) if costs else None,
            "razao_maximo_mediana": max(costs)/med if costs and med else None,
            "tempo_mediano_s": statistics.median(times) if times else None,
            "tempo_maximo_s": max(times) if times else None,
            "tokens_medianos": statistics.median(tokens) if tokens else None,
            "tokens_maximos": max(tokens) if tokens else None}


def mascarar_identificador(valor: str | None) -> str | None:
    """Produz rótulo irreversível estável para matrícula, usuário ou sessão em relatórios."""
    if not valor:
        return None
    return hashlib.sha256(str(valor).encode("utf-8")).hexdigest()[:12]


def sanitizar_ferramentas(chamadas: list[dict]) -> list[dict]:
    """Masca matrícula nos argumentos de ferramentas para logs e relatórios."""
    output = []
    for call in chamadas:
        args = dict(call.get("argumentos", {}))
        if "matricula" in args:
            args["matricula"] = mascarar_identificador(args["matricula"])
        output.append({"nome": call.get("nome"), "argumentos": args,
                       **({"resultado": call["resultado"]} if "resultado" in call else {})})
    return output
